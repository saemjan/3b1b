#!/usr/bin/env python3
"""Builds the Saem core with whatever C++ compiler the machine has.

Stdlib only.

Commands:
    python3 tools/build.py cli
    python3 tools/build.py lib
    python3 tools/build.py all
    python3 tools/build.py id
    python3 tools/build.py verify
    python3 tools/build.py clean

Guarantees:
    - creates build/ and build/obj/ before compiling
    - fails loudly if no core sources exist
    - compiles C sources separately when a C compiler is available
    - builds saem_cli and saemcli from one body
    - builds shared library libsaem.so / libsaem.dylib / saem.dll
    - source_id is SHA-256 over CRLF-normalized core files
"""

import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [
    os.path.join(ROOT, "core", "src"),
    os.path.join(ROOT, "core"),
]

OUT = os.path.join(ROOT, "build")
OBJ = os.path.join(OUT, "obj")

CODE_EXTS = (".cpp", ".c")
ALL_EXTS = (".cpp", ".hpp", ".h", ".inc", ".c")

MAINS = {
    "saem_cli": "cli.cpp",
    "saemcli": "main.cpp",
}

CXX_STD = ["-std=c++17"]
C_STD = ["-std=c11"]
WARN = ["-Wall", "-Wextra", "-Wpedantic", "-Wno-unused-parameter"]
PIC = [] if os.name == "nt" else ["-fPIC"]
EXE = ".exe" if os.name == "nt" else ""


def src_dir():
    for c in CANDIDATES:
        if os.path.isdir(c) and any(
            n.endswith(CODE_EXTS) for n in os.listdir(c)
        ):
            return c
    return None


def core_files():
    d = src_dir()
    if d is None:
        return []

    found = []
    for base, _dirs, names in os.walk(d):
        for n in names:
            if n.endswith(ALL_EXTS):
                found.append(os.path.join(base, n))

    return sorted(
        found,
        key=lambda p: os.path.relpath(p, d).replace(os.sep, "/"),
    )


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


def _newer(target, deps):
    """Return True if target exists and is at least as new as all deps."""
    if not os.path.exists(target):
        return False

    t = os.path.getmtime(target)
    for d in deps:
        if not os.path.exists(d):
            return False
        if t < os.path.getmtime(d):
            return False
    return True


def _obj(src, d):
    rel = os.path.relpath(src, d)
    ext = ".obj" if os.name == "nt" else ".o"
    base = os.path.splitext(rel)[0] + ext
    return os.path.join(OBJ, base)


def _normalize_bytes(data):
    """CRLF-normalize bytes for source_id."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def source_id(files=None):
    if files is None:
        files = core_files()

    if not files:
        raise SystemExit("[build] no core sources (R37)")

    h = hashlib.sha256()

    for path in files:
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        raw = open(path, "rb").read()
        norm = _normalize_bytes(raw)

        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(len(norm)).encode("utf-8"))
        h.update(b"\0")
        h.update(norm)
        h.update(b"\0")

    return h.hexdigest()


def _compile(src, obj, cxx, cc, flags, headers):
    if _newer(obj, [src] + headers):
        return

    os.makedirs(os.path.dirname(obj) or ".", exist_ok=True)

    is_c = src.lower().endswith(".c")
    compiler = cc if is_c and cc else cxx
    std = C_STD if is_c and compiler == cc else CXX_STD

    cmd = [compiler] + std + WARN + PIC + flags + ["-c", src, "-o", obj]
    r = subprocess.run(cmd, capture_output=True, text=True)

    if r.returncode != 0:
        sys.stderr.write(r.stderr[-10000:])
        raise SystemExit("[build] compile failed: " + os.path.basename(src))


def build(kind):
    cxx = find_compiler()
    if not cxx:
        raise SystemExit(
            "[build] No C++ compiler found. Install g++ or clang++, or set CXX."
        )

    cc = find_c_compiler()

    files = core_files()
    if not files:
        raise SystemExit("[build] NO CORE SOURCES under core/src or core/ (R37)")

    d = src_dir()
    sid = source_id(files)

    headers = [p for p in files if not p.lower().endswith(CODE_EXTS)]
    code = [p for p in files if p.lower().endswith(CODE_EXTS)]

    main_names = set(MAINS.values())
    body = [p for p in code if os.path.basename(p) not in main_names]

    if not any(os.path.basename(p).lower() == "cli.cpp" for p in code):
        raise SystemExit("[build] cli.cpp missing: the door has no process (R37)")

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(OBJ, exist_ok=True)

    with open(os.path.join(OUT, "source_id.txt"), "w", encoding="utf-8") as f:
        f.write(sid + "\n")

    print(f"[build] layout={os.path.relpath(d, ROOT)} files={len(files)} cxx={cxx}")

    flags = [f'-DSAEM_SOURCE_ID="{sid}"', "-I", d]

    body_objs = []
    for p in body:
        o = _obj(p, d)
        _compile(p, o, cxx, cc, flags, headers)
        body_objs.append(o)

    if kind in ("cli", "all"):
        for bin_name, main_file in MAINS.items():
            mp = os.path.join(d, main_file)
            if not os.path.exists(mp):
                print(f"[build] skip {bin_name}: {main_file} absent")
                continue

            mo = _obj(mp, d)
            _compile(mp, mo, cxx, cc, flags, headers)

            out = os.path.join(OUT, bin_name + EXE)
            if not _newer(out, body_objs + [mo]):
                cmd = [cxx] + WARN + body_objs + [mo, "-o", out]
                subprocess.run(cmd, check=True)

            print(f"[build] body {sid[:12]} -> {out}")

    if kind in ("lib", "all"):
        lib = os.path.join(OUT, lib_name())

        if sys.platform == "darwin":
            shared = ["-dynamiclib"]
        else:
            shared = ["-shared"]

        if not _newer(lib, body_objs):
            cmd = [cxx] + shared + WARN + body_objs + ["-o", lib]
            subprocess.run(cmd, check=True)

        print(f"[build] body {sid[:12]} -> {lib}")

    return sid


def verify():
    sid = source_id()
    binp = os.path.join(OUT, "saem_cli" + EXE)

    if not os.path.exists(binp):
        raise SystemExit(
            "[verify] binary missing; run: python3 tools/build.py cli"
        )

    r = subprocess.run([binp, "--source-id"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("[verify] saem_cli --source-id failed")

    body = r.stdout.strip()
    if body != sid:
        raise SystemExit(
            f"[verify] STALE binary {body[:12]} != tree {sid[:12]}"
        )

    print(f"[verify] body ok {sid[:12]}")
    return 0


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "all"

    if kind == "clean":
        shutil.rmtree(OUT, ignore_errors=True)
        print("[build] cleaned build/")
        return 0

    if kind == "id":
        print(source_id())
        return 0

    if kind == "verify":
        return verify()

    if kind in ("cli", "lib", "all"):
        build(kind)
        return 0

    raise SystemExit("usage: build.py cli|lib|all|id|verify|clean")


if __name__ == "__main__":
    sys.exit(main())
