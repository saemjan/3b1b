#!/usr/bin/env python3
"""Builds the Saem core with whatever C++ compiler the machine has.
Stdlib only. v3: ONE source dir (core/src, falling back to core/ for old
checkouts); TWO binaries from one body: build/saem_cli (line protocol) and
build/saemcli (legacy subcommands for core_processor.py / math_brain_bridge.py);
plus build/libsaem.so. Zero sources is a loud failure (R37).

    python3 tools/build.py cli|lib|all|id|verify
"""
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [os.path.join(ROOT, "core", "src"), os.path.join(ROOT, "core")]
OUT = os.path.join(ROOT, "build")
STD = ["-std=c++17"]
WARN = ["-Wall", "-Wextra", "-Wpedantic"]
CODE_EXTS = (".cpp", ".c")
ALL_EXTS = (".cpp", ".hpp", ".inc", ".h", ".c")
MAINS = {"saem_cli": "cli.cpp", "saemcli": "main.cpp"}


def src_dir():
    for c in CANDIDATES:
        if os.path.isdir(c) and any(n.endswith(CODE_EXTS) for n in os.listdir(c)):
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
    return sorted(found, key=lambda p: os.path.relpath(p, d).replace(os.sep, "/"))


def source_id(files=None):
    d = src_dir() or CANDIDATES[0]
    h = hashlib.sha256()
    for p in (files if files is not None else core_files()):
        data = open(p, "rb").read().replace(b"\r\n", b"\n")
        rel = os.path.relpath(p, d).replace(os.sep, "/").encode()
        h.update(rel + b"\0" + str(len(data)).encode() + b"\0" + data + b"\0")
    return h.hexdigest()


def find_compiler():
    for name in (os.environ.get("CXX"), "c++", "g++", "clang++"):
        if name and shutil.which(name):
            return name
    return None


def lib_name():
    if sys.platform == "darwin":
        return "libsaem.dylib"
    if sys.platform.startswith("win"):
        return "saem.dll"
    return "libsaem.so"


def _newer(target, deps):
    if not os.path.exists(target):
        return True
    t = os.path.getmtime(target)
    return any(os.path.getmtime(x) > t for x in deps)


def _obj(p, d):
    return os.path.join(OUT, "obj", os.path.relpath(p, d).replace(os.sep, "_") + ".o")


def build(kind):
    cxx = find_compiler()
    if not cxx:
        raise SystemExit("No C++ compiler found. Install g++ or clang++, or set CXX.")
    files = core_files()
    if not files:
        raise SystemExit("[build] NO CORE SOURCES under core/src or core/ (R37)")
    d = src_dir()
    sid = source_id(files)
    headers = [p for p in files if not p.endswith(CODE_EXTS)]
    code = [p for p in files if p.endswith(CODE_EXTS)]
    main_names = set(MAINS.values())
    body = [p for p in code if os.path.basename(p) not in main_names]
    if not any(os.path.basename(p) == "cli.cpp" for p in code):
        raise SystemExit("[build] cli.cpp missing: the door has no process (R37)")
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "source_id.txt"), "w").write(sid + "\n")
    print(f"[build] layout={os.path.relpath(d, ROOT)} files={len(files)} cxx={cxx}")
    flags = ['-DSAEM_SOURCE_ID="%s"' % sid, "-I", d]
    objs = {}
    for p in body:
        o = _obj(p, d)
        if _newer(o, [p] + headers):
            r = subprocess.run([cxx] + STD + WARN + flags + ["-c", p, "-o", o],
                               capture_output=True, text=True)
            sys.stderr.write(r.stderr)
            if r.returncode:
                raise SystemExit("compile failed: " + os.path.basename(p))
        objs[p] = o
    body_objs = list(objs.values())
    if kind in ("cli", "all"):
        for bin_name, main_file in MAINS.items():
            mp = os.path.join(d, main_file)
            if not os.path.exists(mp):
                print(f"[build] skip {bin_name}: {main_file} absent")
                continue
            mo = _obj(mp, d)
            if _newer(mo, [mp] + headers):
                r = subprocess.run([cxx] + STD + WARN + flags + ["-c", mp, "-o", mo],
                                   capture_output=True, text=True)
                sys.stderr.write(r.stderr)
                if r.returncode:
                    raise SystemExit("compile failed: " + main_file)
            out = os.path.join(OUT, bin_name)
            if _newer(out, body_objs + [mo]):
                subprocess.run([cxx] + STD + WARN + body_objs + [mo, "-o", out],
                               check=True)
            print(f"[build] body {sid[:12]} -> {out}")
    if kind in ("lib", "all"):
        lib = os.path.join(OUT, lib_name())
        shared = ["-dynamiclib"] if sys.platform == "darwin" else ["-shared"]
        if _newer(lib, body_objs):
            subprocess.run([cxx] + shared + STD + WARN + body_objs + ["-o", lib],
                           check=True)
        print(f"[build] body {sid[:12]} -> {lib}")
    return sid


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "all"
    if kind == "id":
        if not core_files():
            raise SystemExit("[build] id: no core sources (R37)")
        print(source_id())
        return 0
    if kind == "verify":
        sid = source_id()
        binp = os.path.join(OUT, "saem_cli")
        if not os.path.exists(binp):
            raise SystemExit("[verify] binary missing; run: python3 tools/build.py cli")
        body = subprocess.run([binp, "--source-id"], capture_output=True,
                              text=True).stdout.strip()
        if body != sid:
            raise SystemExit(f"[verify] STALE binary {body[:12]} != tree {sid[:12]}")
        print(f"[verify] body ok {sid[:12]}")
        return 0
    if kind in ("cli", "lib", "all"):
        build(kind)
        return 0
    raise SystemExit("usage: build.py cli|lib|all|id|verify")


if __name__ == "__main__":
    main()
