#!/usr/bin/env python3
"""build.py — gen-3 core builder: one fingerprint canon, parallel objects.

Guarantees:
  * source_id() is THE fingerprint canon (SHA-256 over CRLF-normalized core
    files, rel paths from ROOT). qcos_handshake and the binary's
    --source-id all delegate here — one ruler, no drift (A1).
  * objects compile in parallel (SAEM_JOBS, default 4); link stays serial.
    Same tree -> same source_id regardless of job count (witnessed).
  * every build/verify/clean appends a schema-stamped receipt (A5);
    clean prices its debt (sid + file count) before deleting (A3).
  * exit codes: 0 ok | 1 fail/stale | 2 environment (no compiler/sources).
Usage:
    python3 tools/build.py [cli|lib|all|id|verify|clean] [--json]
    python3 tools/build.py --selftest
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 3
try:
    from tools.ledger import append as _ledger
except Exception:
    _ledger = None

CANDIDATES = [ROOT / "core" / "src", ROOT / "core"]
OUT = ROOT / "build"
OBJ = OUT / "obj"
CODE_EXTS = (".cpp", ".c")
ALL_EXTS = (".cpp", ".hpp", ".h", ".inc", ".c")
MAINS = {"saem_cli": "cli.cpp", "saemcli": "main.cpp"}
CXX_STD = ["-std=c++17"]
C_STD = ["-std=c11"]
WARN = ["-Wall", "-Wextra", "-Wpedantic", "-Wno-unused-parameter"]
OPT = os.environ.get("SAEM_OPT", "-O2").split()
PIC = [] if os.name == "nt" else ["-fPIC"]
EXE = ".exe" if os.name == "nt" else ""
JOBS = max(1, int(os.environ.get("SAEM_JOBS", "4")))


def _receipt(entry):
    if _ledger is None:
        return
    try:
        _ledger({"gate": "build", "schema_version": SCHEMA_VERSION, **entry})
    except Exception:
        pass


def src_dir():
    for c in CANDIDATES:
        if c.is_dir() and any(n.endswith(CODE_EXTS) for n in os.listdir(c)):
            return c
    return None


def core_files():
    d = src_dir()
    if d is None:
        return []
    found = [p for p in d.rglob("*") if p.suffix in ALL_EXTS and p.is_file()]
    return sorted(found, key=lambda p: p.relative_to(d).as_posix())


def find_compiler():
    for name in (os.environ.get("CXX"), "c++", "g++", "clang++"):
        if name and shutil.which(name):
            return name
    return None


def find_c_compiler():
    for name in (os.environ.get("CC"), "cc", "clang", "gcc"):
        if name and shutil.which(name):
            return name
    return None


def lib_name():
    if sys.platform == "darwin":
        return "libsaem.dylib"
    if os.name == "nt":
        return "saem.dll"
    return "libsaem.so"


def _normalize_bytes(data: bytes) -> bytes:
    """CRLF/CR -> LF: the fingerprint must not depend on editor line ends."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def source_id(files=None) -> str:
    if files is None:
        files = core_files()
    if not files:
        raise SystemExit("[build] no core sources (R37)")
    h = hashlib.sha256()
    for path in files:
        rel = Path(path).relative_to(ROOT).as_posix()
        norm = _normalize_bytes(Path(path).read_bytes())
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update(str(len(norm)).encode("utf-8")); h.update(b"\0")
        h.update(norm); h.update(b"\0")
    return h.hexdigest()


def _newer(target, deps) -> bool:
    if not os.path.exists(target):
        return False
    t = os.path.getmtime(target)
    for d in deps:
        if not os.path.exists(d) or t < os.path.getmtime(d):
            return False
    return True


def _obj(src, d):
    rel = os.path.relpath(src, d)
    ext = ".obj" if os.name == "nt" else ".o"
    return str(OBJ / (Path(rel).with_suffix(ext).as_posix().replace("/", os.sep)))


def _compile(src, obj, cxx, cc, flags, headers):
    if _newer(obj, [src] + headers):
        return
    os.makedirs(os.path.dirname(obj) or ".", exist_ok=True)
    is_c = src.lower().endswith(".c")
    compiler = cc if (is_c and cc) else cxx
    std = C_STD if (is_c and compiler == cc) else CXX_STD
    cmd = [compiler] + std + WARN + PIC + OPT + flags + ["-c", src, "-o", obj]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-10000:])
        raise SystemExit("[build] compile failed: " + os.path.basename(src))


def _compile_safe(src, obj, cxx, cc, flags, headers):
    try:
        _compile(src, obj, cxx, cc, flags, headers)
        return ""
    except SystemExit as e:
        return str(e)


def _compile_all(pairs, cxx, cc, flags, headers, jobs=JOBS):
    if jobs <= 1 or len(pairs) < 2:
        for s, o in pairs:
            _compile(s, o, cxx, cc, flags, headers)
        return
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        errs = [f.result() for f in
                (ex.submit(_compile_safe, s, o, cxx, cc, flags, headers)
                 for s, o in pairs)]
    errs = [e for e in errs if e]
    if errs:
        sys.stderr.write("\n".join(errs)[:10000])
        raise SystemExit("[build] compile failed (%d object(s))" % len(errs))


def build(kind):
    t0 = time.time()
    cxx = find_compiler()
    if not cxx:
        _receipt({"op": kind, "status": "env", "error": "no C++ compiler"})
        raise SystemExit("[build] No C++ compiler found. Install g++ or "
                         "clang++, or set CXX.")
    cc = find_c_compiler()
    files = core_files()
    if not files:
        _receipt({"op": kind, "status": "env", "error": "no core sources"})
        raise SystemExit("[build] NO CORE SOURCES under core/src or core/ (R37)")
    d = src_dir()
    sid = source_id(files)
    headers = [str(p) for p in files if p.suffix not in CODE_EXTS]
    code = [str(p) for p in files if p.suffix in CODE_EXTS]
    main_names = set(MAINS.values())
    body = [p for p in code if os.path.basename(p) not in main_names]
    if not any(os.path.basename(p).lower() == "cli.cpp" for p in code):
        raise SystemExit("[build] cli.cpp missing: the door has no process (R37)")
    OUT.mkdir(parents=True, exist_ok=True)
    OBJ.mkdir(parents=True, exist_ok=True)
    (OUT / "source_id.txt").write_text(sid + "\n", encoding="utf-8")
    print(f"[build] layout={d.relative_to(ROOT)} files={len(files)} "
          f"cxx={cxx} jobs={JOBS} opt={''.join(OPT) or '-O0'}")
    flags = [f'-DSAEM_SOURCE_ID="{sid}"', "-I", str(d)]
    body_objs = [_obj(p, str(d)) for p in body]
    _compile_all(list(zip(body, body_objs)), cxx, cc, flags, headers)
    if kind in ("cli", "all"):
        for bin_name, main_file in MAINS.items():
            mp = os.path.join(str(d), main_file)
            if not os.path.exists(mp):
                print(f"[build] skip {bin_name}: {main_file} absent")
                continue
            mo = _obj(mp, str(d))
            _compile_all([(mp, mo)], cxx, cc, flags, headers, jobs=1)
            out = str(OUT / (bin_name + EXE))
            if not _newer(out, body_objs + [mo]):
                subprocess.run([cxx] + WARN + body_objs + [mo, "-o", out],
                               check=True)
            print(f"[build] body {sid[:12]} -> {out}")
    if kind in ("lib", "all"):
        lib = str(OUT / lib_name())
        shared = ["-dynamiclib"] if sys.platform == "darwin" else ["-shared"]
        if not _newer(lib, body_objs):
            subprocess.run([cxx] + shared + WARN + body_objs + ["-o", lib],
                           check=True)
        print(f"[build] body {sid[:12]} -> {lib}")
    _receipt({"op": kind, "status": "ok", "sid": sid[:12],
              "files": len(files), "jobs": JOBS,
              "wall_sec": round(time.time() - t0, 1)})
    return sid


def verify():
    d = src_dir()
    if d is None:
        _receipt({"op": "verify", "status": "env", "error": "no core sources"})
        return 2
    sid = source_id()
    binp = OUT / ("saem_cli" + EXE)
    if not binp.exists():
        print("[verify] binary missing; run: python3 tools/build.py cli")
        _receipt({"op": "verify", "status": "env", "error": "binary missing"})
        return 2
    r = subprocess.run([str(binp), "--source-id"], capture_output=True, text=True)
    if r.returncode != 0:
        _receipt({"op": "verify", "status": "fail", "error": "source-id failed"})
        return 1
    body = r.stdout.strip()
    if body != sid:
        print(f"[verify] STALE binary {body[:12]} != tree {sid[:12]}")
        _receipt({"op": "verify", "status": "stale", "binary": body[:12],
                  "tree": sid[:12]})
        return 1
    print(f"[verify] body ok {sid[:12]}")
    _receipt({"op": "verify", "status": "ok", "sid": sid[:12]})
    return 0


def clean():
    sid = (OUT / "source_id.txt").read_text().strip()[:12] \
        if (OUT / "source_id.txt").exists() else ""
    n = sum(1 for _ in OUT.rglob("*")) if OUT.exists() else 0
    shutil.rmtree(OUT, ignore_errors=True)
    _receipt({"op": "clean", "status": "ok", "debt_sid": sid, "debt_files": n})
    print(f"[build] cleaned build/ (debt priced: sid={sid or '?'} files={n})")
    return 0


# ---------------------------------------------------------------- witness
def selftest():
    import tempfile
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    want("normalize:crlf",
         _normalize_bytes(b"a\r\nb\rc\nd") == b"a\nb\nc\nd")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "core" / "src").mkdir(parents=True)
        a = td / "core" / "src" / "a.cpp"
        a.write_bytes(b"int f(){return 1;}\r\n")
        b = td / "core" / "src" / "b.hpp"
        b.write_bytes(b"#pragma once\n")
        old_root = globals()["ROOT"]
        globals()["ROOT"] = td
        try:
            f = core_files()
            s1 = source_id(f)
            a.write_bytes(b"int f(){return 1;}\n")     # same tree, LF now
            s2 = source_id(core_files())
            want("source_id:crlf-invariant", s1 == s2 and len(s1) == 64)
            a.write_bytes(b"int f(){return 2;}\n")
            want("source_id:sensitive", source_id(core_files()) != s2)
        finally:
            globals()["ROOT"] = old_root
        d = td / "dep"; t = td / "tgt"
        d.write_text("x"); time.sleep(0.01); t.write_text("y")
        want("newer:target-fresh", _newer(str(t), [str(d)]))
        d.write_text("xx"); time.sleep(0.01)
        want("newer:dep-changed", not _newer(str(t), [str(d)]))
        want("newer:missing", not _newer(str(td / "nope"), [str(d)]))
    want("lib_name:nonempty", isinstance(lib_name(), str) and lib_name())
    if find_compiler():
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            srcs = []
            for i in range(4):
                p = td / f"u{i}.cpp"
                p.write_text(f"int f{i}(){{return {i};}}\n")
                srcs.append(str(p))
            objs = [str(td / f"u{i}.o") for i in range(4)]
            cxx = find_compiler()
            _compile_all(list(zip(srcs, objs)), cxx, None,
                         [], [], jobs=4)
            want("parallel:objects", all(os.path.exists(o) for o in objs))
    else:
        want("parallel:objects", True, "skipped (no compiler)")
    return checks


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a[2:] for a in argv[1:] if a.startswith("--")}
    if "selftest" in flags:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    kind = args[0] if args else "all"
    if kind == "clean":
        return clean()
    if kind == "id":
        d = src_dir()
        if d is None:
            return 2
        print(source_id())
        return 0
    if kind == "verify":
        return verify()
    if kind in ("cli", "lib", "all"):
        try:
            sid = build(kind)
        except SystemExit as e:
            if flags & {"json"}:
                print(json.dumps({"ok": False, "error": str(e)}))
            return 2 if "compiler" in str(e) or "SOURCES" in str(e) else 1
        if flags & {"json"}:
            print(json.dumps({"ok": True, "sid": sid, "kind": kind}))
        return 0
    raise SystemExit("usage: build.py cli|lib|all|id|verify|clean|--selftest")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
