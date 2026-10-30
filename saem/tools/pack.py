#!/usr/bin/env python3
"""Pack the project into ONE self-extracting Python file, so the work survives anything.

    python3 tools/pack.py                  writes build/saem-bundle.py and prints its size and SHA-256
    python3 build/saem-bundle.py OUTDIR    restores every file into OUTDIR (default ./saem-unified), checking the SHA-256 of each
    python3 build/saem-bundle.py --list    shows what is inside

Why: the working folder lives in a container that is not guaranteed to outlive a long break. The bundle is plain text, so it can be
saved as a project document and sent to the user, and it restores byte for byte. Source only: no build output, no third-party copies.
"""
import base64
import hashlib
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIR_PREFIX = ("build", "__pycache__", ".git", "node_modules")
SKIP_PATHS = ("third_party/open-math-harness-src",)
SKIP_EXT = (".pyc", ".o", ".obj", ".so", ".dylib", ".dll", ".exe", ".zip", ".gz", ".png", ".jpg")
MAX_BYTES = 2000000

EXTRACTOR = '''
def main(argv):
    if "--list" in argv:
        for path, digest, _ in DATA:
            print(digest[:12], path)
        return 0
    out = argv[0] if argv else "saem-unified"
    root = os.path.abspath(out)
    bad = 0
    for path, digest, blob in DATA:
        raw = zlib.decompress(base64.b64decode(blob))
        dest = os.path.abspath(os.path.join(root, path))
        if hashlib.sha256(raw).hexdigest() != digest or not dest.startswith(root + os.sep):
            print("REFUSED", path)
            bad += 1
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(raw)
    print("restored %d files into %s%s" % (len(DATA) - bad, root, ("  (%d refused)" % bad) if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def skipped_dir(rel):
    return os.path.basename(rel).startswith(SKIP_DIR_PREFIX) or rel in SKIP_PATHS


def collect():
    found = []
    for base, dirs, names in os.walk(ROOT):
        rel_base = os.path.relpath(base, ROOT).replace(os.sep, "/")
        join = (lambda n: n) if rel_base == "." else (lambda n: rel_base + "/" + n)
        dirs[:] = sorted(d for d in dirs if not skipped_dir(join(d)))
        for n in sorted(names):
            rel, full = join(n), os.path.join(base, n)
            if not rel.endswith(SKIP_EXT) and os.path.getsize(full) <= MAX_BYTES:
                found.append(rel)
    return sorted(found)


def main():
    files = collect()
    out = ['#!/usr/bin/env python3',
           '"""Saem Unified source bundle: %d files. Restore with:  python3 <this file> OUTDIR' % len(files),
           'Made by tools/pack.py. Each file is zlib-compressed, base64 encoded, and checked by SHA-256 when restored."""',
           'import base64, hashlib, os, sys, zlib', 'DATA = [']
    raw_total = 0
    for rel in files:
        with open(os.path.join(ROOT, rel), "rb") as f:
            raw = f.read()
        raw_total += len(raw)
        blob = base64.b64encode(zlib.compress(raw, 9)).decode("ascii")
        chunks = [blob[i:i + 100] for i in range(0, len(blob), 100)] or [""]
        out.append("    (%r, %r," % (rel, hashlib.sha256(raw).hexdigest()))
        for i, c in enumerate(chunks):
            out.append("     %r%s" % (c, ")," if i == len(chunks) - 1 else ""))
    out.append("]")
    text = "\n".join(out) + "\n" + EXTRACTOR
    dest = os.path.join(ROOT, "build", "saem-bundle.py")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    data = text.encode("utf-8")
    print("%d files, %d bytes of source -> %s (%d bytes)" % (len(files), raw_total, dest, len(data)))
    print("sha256 " + hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
