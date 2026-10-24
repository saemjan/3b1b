#!/usr/bin/env python3
"""R15 candidate: every qcos method matches the JavaScript reference byte
for byte on fixed seeds. Runs in Engine Tests; exit 1 on any mismatch."""
import json, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.qcos_bridge import call_raw, available

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = [
    ("stream.u", {"seed": 7, "i": 3}),
    ("quantum.apply", {"n": 2, "amp": [[1,0],[0,0],[0,0],[0,0]],
                       "gate": {"kind":5,"a":0,"b":0,"c":0}}),
    ("program.step", {"n": 2, "k": 2, "i": 0, "sin": 1.0,
                      "gate": {"kind":5,"a":0,"b":0,"c":0},
                      "amp": [[1,0]] + [[0,0]]*11}),
    ("program.halt", {"n": 2, "k": 2, "amp": [[0,0]]*8 + [[0.7071067811865476,0],[0,0],[0,0],[0.7071067811865476,0]]}),
    ("cog.observe", {"logodds": 0, "shots": 0, "correct": True}),
    ("kernel.canon", {"value": {"b": [1, 2.5, "x"], "a": True}}),
    ("kernel.soul", {"value": {"b": [1, 2.5, "x"], "a": True}}),
]

def js_call(m, a):
    r = subprocess.run(["node", str(ROOT/"tools"/"ref_bridge_qcos.js"), m,
                        json.dumps(a, separators=(",", ":"))],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()

def main():
    if not available():
        print("[parity] libsaem not built; skip"); return 0
    bad = 0
    for m, a in CASES:
        aj = json.dumps(a, separators=(",", ":"))
        cpp, js = call_raw(m, aj), js_call(m, a)
        if cpp != js:
            bad += 1; print(f"[parity] {m} MISMATCH\n  cpp={cpp}\n  js ={js}")
        else:
            print(f"[parity] {m} ok")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
