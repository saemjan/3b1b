#!/usr/bin/env python3
"""Where are we? Prints the real state of the project in about 40 lines, so nobody has to re-read the sources.

    python3 tools/where.py          files, which methods the C++ core serves compared with the reference, worker progress
    python3 tools/where.py --diff   also run the differential tests

The State table in docs/STATUS.md can go stale when a work burst is cut off by the session limit.
This script cannot: it looks at the files and asks both engines.
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def methods(cmd):
    """Ask an engine (a process that speaks JSON lines) which methods it serves."""
    try:
        p = subprocess.run(cmd, input='{"id":1,"method":"core.methods"}\n', capture_output=True, text=True, timeout=60, cwd=ROOT)
        return set(json.loads(p.stdout.splitlines()[0])["result"])
    except Exception:
        return None


def line_count(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def main():
    print("== files (lines) ==")
    for pat in ("core/src/*.cpp", "core/src/*.hpp", "saem/*.py", "saem/static/*", "tests/test_*.py", "tests/diff/cases/*.jsonl", "docs/*.md"):
        found = sorted(glob.glob(os.path.join(ROOT, pat)))
        if found:
            print("%s\n    %s" % (pat, "  ".join("%s %d" % (os.path.basename(f), line_count(f)) for f in found)))

    ref = methods(["node", os.path.join(ROOT, "tools", "ref_bridge.js")])
    cc = methods([os.path.join(ROOT, "build", "saem_cli")])
    print("\n== methods ==")
    if ref is None:
        print("the reference bridge did not answer (is node installed?)")
    if cc is None:
        print("build/saem_cli is missing: run  python3 tools/build.py cli")
    if ref and cc is not None:
        print("C++ core serves %d of %d reference methods (binary may be older than the sources)" % (len(ref & cc), len(ref)))
        groups = {}
        for m in sorted(ref - cc):
            g, _, rest = m.partition(".")
            groups.setdefault(g, []).append(rest)
        for g in sorted(groups):
            print("  missing %s.{%s}" % (g, ",".join(groups[g])))
        extra = sorted(cc - ref)
        if extra:
            print("  only in C++: " + ", ".join(extra))

    print("\n== worker progress (last 3 lines of each docs/PROGRESS_*.md) ==")
    files = sorted(glob.glob(os.path.join(ROOT, "docs", "PROGRESS_*.md")))
    if not files:
        print("none yet")
    for f in files:
        with open(f, encoding="utf-8") as fh:
            tail = fh.read().strip().splitlines()[-3:]
        print("%s:" % os.path.basename(f))
        for t in tail:
            print("   " + t[:200])

    if "--diff" in sys.argv:
        print("\n== differential tests ==")
        subprocess.call([sys.executable, os.path.join(ROOT, "tests", "diff", "run.py")], cwd=ROOT)


if __name__ == "__main__":
    main()
