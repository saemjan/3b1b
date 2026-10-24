#!/usr/bin/env python3
"""Canon lint: qcos.cxn <-> Registrar parity.

Errors  : canon declares a method with no Registrar implementation
          (a dangling binding in some tongue).
Warnings: a Registrar exists but is not in the canon yet
          (canonization queue; per A5 these are hypotheses).

    python3 tools/canon_lint.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "qcos.cxn"
SRC = ROOT / "core" / "src"

def canon_methods():
    if not CANON.exists():
        return set()
    return set(re.findall(r"^@method\s+([\w.]+)", CANON.read_text(encoding="utf-8"), re.M))

def impl_methods():
    names = set()
    pat = re.compile(r'Registrar\s+\w+\s*\(\s*"([\w.]+)"')
    for p in sorted(SRC.glob("*.cpp")):
        names.update(pat.findall(p.read_text(encoding="utf-8")))
    return names

def main():
    canon, impl = canon_methods(), impl_methods()
    dangling = sorted(canon - impl)
    queue = sorted(impl - canon)

    print(f"[canon] canon={len(canon)} implemented={len(impl)}")
    ok = True
    if dangling:
        ok = False
        print("[canon] ERROR declared but not implemented:")
        for m in dangling:
            print(f"  - {m}")
    if queue:
        print("[canon] WARN implemented but not canonized (hypotheses, A5):")
        for m in queue:
            print(f"  - {m}")
    if not ok:
        return 1
    print("[canon] parity ok" if not queue else "[canon] parity ok with queue")
    return 0

if __name__ == "__main__":
    sys.exit(main())
