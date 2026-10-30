#!/usr/bin/env python3
"""Builds the Saem core with whatever C++ compiler the machine has. Standard library only.

    python3 tools/build.py cli      build/saem_cli      (the core as a process: JSON lines in, JSON lines out)
    python3 tools/build.py lib      build/libsaem.so    (the core as a library: .dylib on macOS, saem.dll on Windows)
    python3 tools/build.py all      both
    python3 tools/build.py id       print the source id (SHA-256 of every file the core is made of)

Options (for working on one module at a time):
    --only api,cli,gen,ef,ef_api   compile just these files (names without .cpp)
    --out DIR                      put objects and binaries in DIR instead of build/

The source id is the core's body fingerprint. It is compiled into the binary, so the running core can always be
compared with the source it claims to come from (see saem/core.py).
"""
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "core", "src")
OUT = os.path.join(ROOT, "build")
STD = ["-std=c++17"]
WARN = ["-Wall", "-Wextra", "-Wpedantic"]
# the same arithmetic on every machine: no fused multiply-add, no fast-math, so results do not depend on the CPU
FP = ["-ffp-contract=off", "-fno-fast-math"]
EXTS = (".cpp", ".hpp", ".inc", ".h", ".c")


def core_files():
    """Every file that makes up the core, in a fixed order."""
    found = []
    for base, _dirs, names in os.walk(SRC):
        for n in names:
            if n.endswith(EXTS):
                found.append(os.path.join(base, n))
    return sorted(found, key=lambda p: os.path.relpath(p, SRC).replace(os.sep, "/"))


def source_id(files=None):
    """SHA-256 over (relative name, length, bytes) of each core file. Line endings are normalised so Windows checkouts agree."""
    h = hashlib.sha256()
    for p in files or core_files():
        data = open(p, "rb").read().replace(b"\r\n", b"\n")
        rel = os.path.relpath(p, SRC).replace(os.sep, "/").encode()
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
    return any(os.path.getmtime(d) > t for d in deps)


def _compile(cxx, cpp, obj, flags, headers):
    if not _newer(obj, [cpp] + headers):
        return
    os.makedirs(os.path.dirname(obj), exist_ok=True)
    cmd = [cxx] + STD + WARN + flags + ["-c", cpp, "-o", obj]
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode:
        raise SystemExit("compile failed: " + os.path.basename(cpp))


def build(kind, debug=False, quiet=False, only=None, out=None):
    cxx = find_compiler()
    if not cxx:
        raise SystemExit("No C++ compiler found. Install g++ or clang++ (Xcode command line tools on macOS), or set CXX.")
    files = core_files()
    headers = [p for p in files if not p.endswith((".cpp", ".c"))]
    sid = source_id(files)
    OUT_ = os.path.abspath(out) if out else OUT
    os.makedirs(OUT_, exist_ok=True)
    idfile = os.path.join(OUT_, "source_id.txt")
    old = open(idfile).read().strip() if os.path.exists(idfile) else ""
    flags = (["-g", "-O0"] if debug else ["-O2"]) + FP
    flags += ["-DSAEM_SOURCE_ID=\"%s\"" % sid]
    # objects that embed the id are rebuilt when it changes; the rest only when their own sources change
    id_users = {"api.cpp", "cli.cpp"}
    outputs = []
    for target in (["cli", "lib"] if kind == "all" else [kind]):
        objs = []
        shared = target == "lib"
        tflags = flags + (["-fPIC", "-fvisibility=hidden"] if shared and not sys.platform.startswith("win") else [])
        for cpp in [p for p in files if p.endswith(".cpp")]:
            name = os.path.basename(cpp)
            if only and name[:-4] not in only:
                continue
            if shared and name == "cli.cpp":
                continue
            obj = os.path.join(OUT_, "obj", "lib" if shared else "cli", name[:-4] + ".o")
            if name in id_users and old != sid and os.path.exists(obj):
                os.remove(obj)
            _compile(cxx, cpp, obj, tflags, headers)
            objs.append(obj)
        if shared:
            dest = os.path.join(OUT_, lib_name())
            link = [cxx, "-shared", "-o", dest] + objs
        else:
            dest = os.path.join(OUT_, "saem_cli" + (".exe" if sys.platform.startswith("win") else ""))
            link = [cxx, "-o", dest] + objs
        if _newer(dest, objs):
            r = subprocess.run(link, capture_output=True, text=True)
            sys.stderr.write(r.stderr)
            if r.returncode:
                raise SystemExit("link failed: " + dest)
        outputs.append(dest)
    open(idfile, "w").write(sid + "\n")
    if not quiet:
        for o in outputs:
            print(o)
    return outputs


if __name__ == "__main__":
    argv = sys.argv[1:]
    only = out = None
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    what = argv[0] if argv and not argv[0].startswith("--") else "all"
    if what == "id":
        print(source_id())
    elif what in ("cli", "lib", "all"):
        build(what, debug="--debug" in argv, only=only, out=out)
    else:
        raise SystemExit(__doc__)
