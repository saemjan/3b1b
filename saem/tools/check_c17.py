#!/usr/bin/env python3
"""One command that checks the whole C17 sovereign kernel (core/c17/).

    python3 tools/check_c17.py            everything (about a minute on two cores)
    python3 tools/check_c17.py --quick    compile, structure checks, cross-checks, and the tests at -O2 only

What it proves, so the design rules are checks and not promises:
  compile     every source builds with -Werror under gcc (strict + extra warnings, incl. no VLA/alloca, stack use per function <= 2 KB) and clang,
              and with -mgeneral-regs-only (the compiler itself refuses floating point and vector registers)
  headers     every header stands alone in C17 and also parses as C++17 (extern "C" boundary)
  zero heap   the objects import nothing but memcpy/memset/memcmp/memmove/strlen (and the compiler's stack check); no malloc, free, stdio, math;
              the sources contain no malloc/free/alloca and include only freestanding headers
  zero float  no float/double/math in the sources (comments and strings stripped)
  no globals  no writable data symbols and no .data/.bss in any object: all state lives in memory the caller hands in
  tests       all seven test programs at -O0, -O2, -O3, gcc+clang, under AddressSanitizer+UBSan, and the threaded ones under ThreadSanitizer
  cross-checks C SHA-256/HMAC against Python's hashlib/hmac on thousands of inputs; against the C++ engine's SHA-256; the constitution seal
              digest against tools/seal.py (inside the core test); the Zone 0 gate against Python's Unicode database for every code point
Exit code 0 only if everything passes.
"""
import argparse
import concurrent.futures as cf
import glob
import hashlib
import hmac
import os
import random
import re
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C17 = os.path.join(ROOT, "core", "c17")
TESTS = os.path.join(ROOT, "core", "tests")
BUILD = os.path.join(ROOT, "build_c17")
OBJ = os.path.join(BUILD, "obj")
sys.path.insert(0, os.path.join(ROOT, "tools"))

STRICT = ["-std=c17", "-Wall", "-Wextra", "-Wpedantic", "-Werror"]
EXTRA = ["-Wvla", "-Walloca", "-Wundef", "-Wcast-align", "-Wpointer-arith", "-Wdouble-promotion", "-Wfloat-equal", "-Wconversion", "-Wshadow",
         "-Wstrict-prototypes", "-Wmissing-prototypes", "-Wcast-qual", "-Wformat=2", "-Wnull-dereference", "-Wduplicated-cond", "-Wlogical-op",
         "-Wstack-usage=2048"]
INC = ["-I" + C17, "-I" + TESTS, "-I" + BUILD]
ALLOWED_UNDEFINED = {"memcpy", "memmove", "memset", "memcmp", "strlen", "__stack_chk_fail"}
ALLOWED_SYSTEM_HEADERS = {"stdint.h", "stddef.h", "stdbool.h", "stdalign.h", "stdatomic.h", "string.h"}
FORBIDDEN_CALLS = ["malloc", "calloc", "realloc", "free", "aligned_alloc", "posix_memalign", "memalign", "valloc", "strdup", "alloca", "mmap", "sbrk", "brk"]

# test program -> (test source, kernel sources it needs, uses threads)
PROGRAMS = {
    "sha256": ("c17_sha256_test.c", ["cos_sha256.c"], False),
    "pool": ("c17_pool_test.c", ["cos_pool.c"], True),
    "regs": ("c17_regs_test.c", ["cos_regs.c"], False),
    "wal": ("c17_wal_test.c", ["cos_wal.c", "cos_sha256.c"], False),
    "journal": ("c17_journal_test.c", ["cos_journal.c", "cos_wal.c", "cos_sha256.c"], True),
    "gate": ("c17_gate_test.c", ["cos_gate.c"], True),
    "core": ("c17_core_test.c", ["cos_core.c", "cos_gate.c", "cos_seal.c", "cos_journal.c", "cos_wal.c", "cos_sha256.c"], True),
}

results = []  # (ok, title, detail)


def record(ok, title, detail=""):
    results.append((ok, title, detail))
    print("%s  %s" % ("ok  " if ok else "FAIL", title), flush=True)
    if detail and not ok:
        for line in detail.strip().splitlines()[:40]:
            print("      " + line, flush=True)


def run(cmd, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("timeout", 900)
    return subprocess.run(cmd, **kw)


def kernel_sources():
    return sorted(glob.glob(os.path.join(C17, "*.c")))


def kernel_headers():
    return sorted(glob.glob(os.path.join(C17, "*.h")))


# ---------------------------------------------------------------- source text rules
def strip_c(src):
    """Comments removed, string and character literal contents blanked; newlines kept so line numbers stay right."""
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("\n" * src.count("\n", i, j) or " ")
            i = j
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src[i] in "\"'":
            q = src[i]
            j = i + 1
            while j < n and src[j] != q:
                j += 2 if src[j] == "\\" else 1
            out.append(q + q)
            i = j + 1
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


FLOAT_WORDS = re.compile(r"\b(float|double|_Complex|_Imaginary)\b")
FLOAT_LITERAL = re.compile(r"(?<![\w.])(\d+\.\d*|\.\d+|\d+[eE][+-]?\d+)(?![\w.])")
HEX_LITERAL = re.compile(r"\b0[xX][0-9a-fA-F']+[uUlL]*\b")
CALL_WORDS = re.compile(r"\b(" + "|".join(FORBIDDEN_CALLS) + r")\b")
INCLUDE = re.compile(r"^\s*#\s*include\s*<([^>]+)>", re.M)


def check_source_rules():
    bad = []
    files = kernel_sources() + kernel_headers()
    for path in files:
        code = strip_c(open(path, encoding="utf-8").read())
        name = os.path.relpath(path, ROOT)
        for m in INCLUDE.finditer(open(path, encoding="utf-8").read()):
            if m.group(1) not in ALLOWED_SYSTEM_HEADERS:
                bad.append("%s: includes <%s>; the kernel may use only %s" % (name, m.group(1), ", ".join(sorted(ALLOWED_SYSTEM_HEADERS))))
        nohex = HEX_LITERAL.sub("0", code)
        for lineno, line in enumerate(nohex.splitlines(), 1):
            if FLOAT_WORDS.search(line) or FLOAT_LITERAL.search(line):
                bad.append("%s:%d: floating point: %s" % (name, lineno, line.strip()))
            m = CALL_WORDS.search(line)
            if m:
                bad.append("%s:%d: forbidden call %s: %s" % (name, lineno, m.group(1), line.strip()))
    record(not bad, "sources: %d files, no float/double, no malloc/free/alloca, only freestanding includes" % len(files), "\n".join(bad))


# ---------------------------------------------------------------- compile and structure
def compile_one(src, extra, cc="gcc", out=None):
    cmd = [cc] + STRICT + ["-O2"] + extra + INC + ["-c", src, "-o", out or os.devnull]
    p = run(cmd)
    return p.returncode == 0, (p.stderr or "")[:1500]


def check_compile():
    os.makedirs(OBJ, exist_ok=True)
    srcs = kernel_sources()
    jobs = []
    with cf.ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        for s in srcs:
            b = os.path.basename(s)[:-2]
            jobs.append(("gcc strict", s, ex.submit(compile_one, s, [], "gcc", os.path.join(OBJ, b + ".o"))))
            jobs.append(("gcc extra", s, ex.submit(compile_one, s, EXTRA, "gcc")))
            jobs.append(("clang", s, ex.submit(compile_one, s, ["-Wconversion", "-Wshadow"], "clang")))
            jobs.append(("general-regs-only", s, ex.submit(compile_one, s, ["-mgeneral-regs-only"], "gcc")))
    errors = []
    for kind, s, fut in jobs:
        ok, err = fut.result()
        if not ok:
            errors.append("[%s] %s\n%s" % (kind, os.path.basename(s), err))
    record(not errors, "compile: %d sources x (gcc strict, gcc +extra warnings and 2 KB stack limit, clang, -mgeneral-regs-only)" % len(srcs), "\n".join(errors))


def check_headers():
    errors = []
    for h in kernel_headers():
        name = os.path.basename(h)
        p = run(["gcc", "-std=c17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "-x", "c", "-", "-I" + C17], input='#include "%s"\n' % name)
        if p.returncode != 0:
            errors.append("C17 alone: %s\n%s" % (name, p.stderr[:600]))
    tu = "".join('#include "%s"\n' % os.path.basename(h) for h in kernel_headers()) + "int main(void) { return 0; }\n"
    p = run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-fsyntax-only", "-x", "c++", "-", "-I" + C17], input=tu)
    if p.returncode != 0:
        errors.append("C++17 together\n" + p.stderr[:800])
    record(not errors, "headers: %d stand alone in C17 and parse together as C++17" % len(kernel_headers()), "\n".join(errors))


def nm(args, obj):
    p = run(["nm"] + args + [obj])
    return [ln.split() for ln in p.stdout.splitlines() if ln.strip()]


def check_objects():
    objs = sorted(glob.glob(os.path.join(OBJ, "*.o")))
    defined, undefined, writable, sections = set(), {}, [], []
    for o in objs:
        base = os.path.basename(o)
        for parts in nm(["--defined-only"], o):
            if len(parts) == 3:
                _, t, name = parts
                defined.add(name)
                if t in "DdBbCcGgSsVvWw":
                    writable.append("%s: writable symbol %s (type %s)" % (base, name, t))
        for parts in nm(["-u"], o):
            undefined.setdefault(parts[-1], []).append(base)
        sz = run(["size", "-A", o]).stdout
        for ln in sz.splitlines():
            f = ln.split()
            if len(f) >= 2 and f[1].isdigit() and int(f[1]) > 0 and re.match(r"^\.(data|bss|tbss|tdata|init_array|fini_array)(\.|$)", f[0]) \
                    and not f[0].startswith(".data.rel.ro"):
                sections.append("%s: section %s has %s bytes" % (base, f[0], f[1]))
    heap = []
    for name, users in sorted(undefined.items()):
        if name in defined or name in ALLOWED_UNDEFINED:
            continue
        heap.append("%s imports %s" % (", ".join(users), name))
    record(not heap, "zero heap: %d objects import only memcpy/memmove/memset/memcmp/strlen and each other (no malloc, free, stdio, math)" % len(objs),
           "\n".join(heap))
    record(not writable and not sections, "no global state: no writable data symbol and no .data/.bss section in any kernel object",
           "\n".join(writable + sections))


# ---------------------------------------------------------------- tests
def build_and_run(name, variant):
    test, srcs, threads = PROGRAMS[name]
    cc = "clang" if variant == "clang-O2" else "gcc"
    flags = {"O0": ["-O0"], "O2": ["-O2"], "O3": ["-O3"], "clang-O2": ["-O2"],
             "asan": ["-O1", "-g", "-fsanitize=address,undefined", "-fno-sanitize-recover=all"],
             "tsan": ["-O1", "-g", "-fsanitize=thread"]}[variant]
    exe = os.path.join(BUILD, "t_%s_%s" % (name, variant))
    cmd = [cc] + STRICT + flags + (["-pthread"] if threads else []) + INC + [os.path.join(TESTS, test)] + [os.path.join(C17, s) for s in srcs] + ["-o", exe]
    p = run(cmd)
    if p.returncode != 0:
        return False, "build failed\n" + p.stderr[:1500]
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=1:abort_on_error=0", TSAN_OPTIONS="halt_on_error=1")
    q = run([exe], env=env)
    tail = (q.stdout + q.stderr).strip().splitlines()
    last = tail[-1] if tail else ""
    ok = q.returncode == 0 and re.search(r"\b0 failed\b", last) is not None
    return ok, "\n".join(tail[-12:])


def seal_vector():
    """Generate the C text of the seal test vector from the JSON spec with the independent Python tool."""
    import seal
    os.makedirs(BUILD, exist_ok=True)
    spec = seal.load_spec(os.path.join(TESTS, "vectors", "seal_vector.json"))
    key = "QCOS-TEST-KEY-NOT-FOR-RELEASE-0001".encode()
    text = seal.emit_c(spec, "TV", key, "core/tests/vectors/seal_vector.json")
    with open(os.path.join(BUILD, "seal_vector.inc"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def check_tests(quick):
    variants = ["O2"] if quick else ["O0", "O2", "O3", "clang-O2", "asan", "tsan"]
    jobs = []
    with cf.ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        for name, (_, _, threads) in PROGRAMS.items():
            for v in variants:
                if v == "tsan" and not threads:
                    continue
                jobs.append((name, v, ex.submit(build_and_run, name, v)))
    table = {}
    for name, v, fut in jobs:
        ok, detail = fut.result()
        table.setdefault(name, []).append((v, ok, detail))
    for name in PROGRAMS:
        rows = table.get(name, [])
        ok = all(r[1] for r in rows)
        record(ok, "test %-8s %s" % (name, " ".join("%s%s" % (v, "" if o else "(FAIL)") for v, o, _ in rows)),
               "\n".join("[%s]\n%s" % (v, d) for v, o, d in rows if not o))


# ---------------------------------------------------------------- cross-checks
def build_dump():
    exe = os.path.join(BUILD, "c17_dump")
    p = run(["gcc", "-std=c17", "-O2", "-Wall", "-Wextra", "-Werror"] + INC +
            [os.path.join(TESTS, "c17_dump.c"), os.path.join(C17, "cos_gate.c"), os.path.join(C17, "cos_sha256.c"), "-o", exe])
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return exe


def check_hash(dump):
    rng = random.Random(20261030)
    lines, want = [], []
    sizes = list(range(0, 140)) + [191, 192, 255, 256, 257, 1000, 4096, 10000]
    keys = [None, b"k", bytes(range(32)), bytes(range(64)), bytes(range(65)), bytes(range(131)), bytes(200)]
    for n in sizes:
        msg = bytes(rng.getrandbits(8) for _ in range(n))
        for key in keys[: 1 + (n % 7)]:
            lines.append("%s %s" % ("-" if key is None else key.hex(), msg.hex()))
            want.append((hashlib.sha256(msg).hexdigest(), "-" if key is None else hmac.new(key, msg, hashlib.sha256).hexdigest()))
    p = run([dump, "hash"], input="\n".join(lines) + "\n")
    got = [tuple(ln.split()) for ln in p.stdout.splitlines()]
    bad = [i for i, (g, w) in enumerate(zip(got, want)) if g != w]
    ok = p.returncode == 0 and len(got) == len(want) and not bad
    record(ok, "cross-check: C SHA-256 and HMAC-SHA-256 equal Python hashlib/hmac on %d inputs (lengths 0..10000, keys 0..200 bytes)" % len(want),
           "returncode %s, %d of %d lines, first mismatch at %s" % (p.returncode, len(got), len(want), bad[:3]))


def check_cpp_sha():
    exe = os.path.join(BUILD, "sha_vs_cpp")
    o = os.path.join(BUILD, "cos_sha256_for_cpp.o")  # not in obj/: that directory holds exactly the kernel objects that get inspected
    p = run(["gcc", "-std=c17", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + C17, "-c", os.path.join(C17, "cos_sha256.c"), "-o", o])
    if p.returncode == 0:
        p = run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + C17, os.path.join(TESTS, "c17_sha256_vs_cpp.cpp"), o, "-o", exe])
    if p.returncode != 0:
        record(False, "cross-check: C SHA-256 vs the C++ engine's SHA-256", "build failed\n" + p.stderr[:1200])
        return
    q = run([exe])
    record(q.returncode == 0, "cross-check: C SHA-256 equals the C++ engine's SHA-256 (all lengths 0..700, split and bursty updates)", q.stdout + q.stderr)


SCRIPT_PREFIXES = ("DEVANAGARI", "COMBINING DEVANAGARI", "BENGALI", "GURMUKHI", "GUJARATI", "ORIYA", "TAMIL", "TELUGU", "KANNADA", "MALAYALAM", "SINHALA", "ARABIC")
RULE = dict(none=0, length=1, utf8=2, nul=3, control=4, bidi=5, invisible=6, joiner=7, private=8, nonchar=9)


def check_unicode(dump):
    p = run([dump, "gate"])
    parts = p.stdout.split("\n")
    n = 0x110000
    if p.returncode != 0 or len(parts) < 3 or len(parts[0]) != n or len(parts[1]) != n or len(parts[2]) != n:
        record(False, "cross-check: Zone 0 gate against the Unicode database", "dump failed: %s lengths %s" % (p.returncode, [len(x) for x in parts]))
        return
    alone = [int(c, 16) for c in parts[0]]
    after_zwj = [int(c, 16) for c in parts[1]]
    after_zwnj = [int(c, 16) for c in parts[2]]
    errors = []

    def want(cp, rule, why):
        if alone[cp] != rule and len(errors) < 40:
            errors.append("U+%04X (%s): gate says %d, expected %d" % (cp, why, alone[cp], rule))

    bidi = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))
    invisible = {0x200B, 0xFEFF, 0x180E} | set(range(0x2060, 0x2065)) | set(range(0xE0000, 0xE0080)) | set(range(0xE0100, 0xE01F0))
    accepted_cf, unassigned_accepted, cats = [], 0, {}
    for cp in range(n):
        c = unicodedata.category(chr(cp))
        if cp in bidi:
            want(cp, RULE["bidi"], "bidi control")
        elif cp in invisible:
            want(cp, RULE["invisible"], "invisible")
        elif cp in (0x200C, 0x200D):
            want(cp, RULE["joiner"], "joiner with nothing before it")
        elif c == "Cs":
            want(cp, RULE["utf8"], "surrogate")
        elif c == "Cc":
            want(cp, RULE["none"] if cp in (9, 10, 13) else (RULE["nul"] if cp == 0 else RULE["control"]), "control")
        elif 0xFDD0 <= cp <= 0xFDEF or (cp & 0xFFFE) == 0xFFFE or cp == 0xFFFD or 0xFFF9 <= cp <= 0xFFFC:
            want(cp, RULE["nonchar"], "noncharacter or damaged-text marker")
        elif c == "Co":
            want(cp, RULE["private"], "private use")
        else:
            want(cp, RULE["none"], "category " + c)
            if c == "Cf":
                accepted_cf.append(cp)
            if c == "Cn":
                unassigned_accepted += 1
        cats[c] = cats.get(c, 0) + 1
    record(not errors, "cross-check: Zone 0 gate agrees with Python's Unicode database (Unicode %s) on all 1,114,112 code points" % unicodedata.unidata_version,
           "\n".join(errors))

    # Hindi, Bengali, Tamil ... Urdu and Persian must never lose their joiners: every assigned BMP letter, mark, digit or sign of these scripts
    # accepts a ZWJ and a ZWNJ right after it
    missed = []
    covered = 0
    for cp in range(0x10000):
        try:
            name = unicodedata.name(chr(cp))
        except ValueError:
            continue
        if name.startswith(SCRIPT_PREFIXES) and alone[cp] == RULE["none"]:
            covered += 1
            if after_zwj[cp] != 0 or after_zwnj[cp] != 0:
                missed.append("U+%04X %s" % (cp, name))
    record(not missed and covered > 1500, "cross-check: ZWJ and ZWNJ are accepted after all %d assigned BMP characters of the Indian and Arabic scripts" % covered,
           "%d refused, e.g. %s" % (len(missed), "; ".join(missed[:8])))
    # a joiner after anything else is refused (checked on a sample of assigned characters of other scripts)
    leaked = [cp for cp in range(0x10000) if alone[cp] == 0 and unicodedata.category(chr(cp)) in ("Lu", "Ll", "Nd", "Zs", "Sm", "Sc", "Po")
              and not (0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or 0x0870 <= cp <= 0x08FF or 0x0900 <= cp <= 0x0DFF or 0xA8E0 <= cp <= 0xA8FF
                       or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFE) and after_zwj[cp] == 0]
    record(not leaked, "cross-check: a joiner after Latin, Greek, Cyrillic, CJK, digits, spaces and symbols is refused", "%d accepted, e.g. %s" % (len(leaked), leaked[:8]))
    print("      info: %d format characters (Cf) are accepted on purpose (soft hyphen, Arabic number signs, LRM/RLM, ...); %d unassigned code points are "
          "accepted because the gate carries no Unicode table" % (len(accepted_cf), unassigned_accepted), flush=True)


def check_seal_tool():
    import seal
    errors = []

    def must_fail(mutate, what):
        spec = {"build_id": "b", "articles": [{"id": 1, "title": "t", "text": "x"}, {"id": 2, "title": "u", "text": "y"}],
                "methods": [{"id": 1, "name": "a.b", "flags": ["json"], "max_len": 5}, {"id": 2, "name": "c.d"}]}
        mutate(spec)
        try:
            seal.digest(spec)
            errors.append("accepted: " + what)
        except seal.SpecError:
            pass

    must_fail(lambda s: s["articles"][0].__setitem__("text", "a\x00b"), "NUL inside text (the C core would stop reading at it)")
    must_fail(lambda s: s["articles"][1].__setitem__("id", 1), "duplicate article id")
    must_fail(lambda s: s["methods"][1].__setitem__("id", 1), "duplicate method id")
    must_fail(lambda s: s["methods"].reverse(), "method ids not increasing")
    must_fail(lambda s: s["methods"][0].__setitem__("flags", ["nope"]), "unknown flag")
    must_fail(lambda s: s["methods"][0].__setitem__("name", "Bad Name"), "bad method name")
    must_fail(lambda s: s["methods"][0].__setitem__("id", 256), "method id above 255")
    must_fail(lambda s: s.__setitem__("build_id", ""), "empty build id")
    must_fail(lambda s: s["articles"][0].__setitem__("title", "\ud800"), "lone surrogate in text")
    # the limits parsed from the header are the ones the compiler sees
    prog = "#include <stdio.h>\n#include \"cos_limits.h\"\nint main(void){printf(\"%u %u %u %u %u %u %u %u %u\\n\"," + ",".join(
        "(unsigned)" + n for n in seal.LIMIT_NAMES) + ");return 0;}\n"
    src = os.path.join(BUILD, "limits_probe.c")
    open(src, "w").write(prog)
    exe = os.path.join(BUILD, "limits_probe")
    p = run(["gcc", "-std=c17", "-I" + C17, src, "-o", exe])
    if p.returncode != 0:
        errors.append("limits probe did not build: " + p.stderr[:300])
    else:
        got = [int(x) for x in run([exe]).stdout.split()]
        if got != seal.read_limits():
            errors.append("tools/seal.py reads limits %s but the compiler sees %s" % (seal.read_limits(), got))
    record(not errors, "tools/seal.py: refuses malformed specs (9 cases) and reads the same nine limits the compiler sees", "\n".join(errors))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true", help="tests at -O2 only")
    args = ap.parse_args()
    os.makedirs(OBJ, exist_ok=True)
    check_source_rules()
    check_compile()
    check_headers()
    check_objects()
    check_seal_tool()
    seal_vector()
    dump = build_dump()
    check_hash(dump)
    check_cpp_sha()
    check_unicode(dump)
    check_tests(args.quick)
    bad = [r for r in results if not r[0]]
    print("\n%s: %d of %d checks passed" % ("ALL OK" if not bad else "FAILED", len(results) - len(bad), len(results)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
