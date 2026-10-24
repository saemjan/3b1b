#!/usr/bin/env python3
"""Golden fixtures for the QCOS layer: record once, compare forever.

qcos.* methods are resident-state methods, so their witness is not the JS
bridge but a frozen sequence: spawn a fresh saem_cli, run the sequence,
compare every answer byte for byte against tests/golden/qcos.json.

    python3 tools/golden_qcos.py record   # after reviewing a kernel change
    python3 tools/golden_qcos.py check    # gate; exit 1 on any drift
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "build" / "saem_cli"
GOLD = ROOT / "tests" / "golden" / "qcos.json"

CIR = {"shape": "LINE", "steps": [
    {"step": 0, "op": "latch", "key": "a", "value": 2, "sync": "barrier"},
    {"step": 1, "op": "latch", "key": "b", "value": 3, "sync": "barrier"},
    {"step": 2, "op": "add", "a": "a", "b": "b", "dst": "c", "sync": "barrier"}]}

SEQUENCE = [
    ("qcos.boot", {}),
    ("qcos.gate", {"op": "latch", "args": {"x": 1e999}}),
    ("qcos.lower", {"want": "store", "key": "m", "value": 5}),
    ("qcos.exec", {"cir": CIR}),
    ("qcos.read", {"key": "c"}),
    ("qcos.cost", {"cir": CIR}),
    ("qcos.provenance", {}),
]


def run_sequence():
    p = subprocess.Popen([str(CLI)], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True, bufsize=1)
    out = []
    try:
        for i, (method, args) in enumerate(SEQUENCE, 1):
            p.stdin.write(json.dumps({"id": i, "method": method, "args": args},
                                     separators=(",", ":")) + "\n")
            p.stdin.flush()
            out.append(p.stdout.readline().rstrip("\n"))
    finally:
        p.stdin.close()
        p.wait(timeout=10)
    return out


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("record", "check"):
        print("usage: golden_qcos.py [record|check]")
        return 1
    got = run_sequence()
    if sys.argv[1] == "record":
        GOLD.parent.mkdir(parents=True, exist_ok=True)
        GOLD.write_text("\n".join(got) + "\n", encoding="utf-8")
        print(f"[golden] recorded {len(got)} answers to {GOLD}")
        return 0
    want = GOLD.read_text(encoding="utf-8").splitlines()
    bad = 0
    for i, (w, g) in enumerate(zip(want, got)):
        name = SEQUENCE[i][0]
        if w != g:
            bad += 1
            print(f"[golden] {name} DRIFT\n  want={w}\n  got ={g}")
        else:
            print(f"[golden] {name} ok")
    if len(want) != len(got):
        bad += 1
        print(f"[golden] length mismatch {len(want)} vs {len(got)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
