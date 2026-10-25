#!/usr/bin/env python3
"""golden_qcos.py — gen-3 frozen witness for resident-state qcos.* methods.

The JS bridge remains the ruler for bridge calls (A6); resident-state
methods are witnessed by replaying a frozen sequence against a freshly
spawned saem_cli and comparing every answer byte-for-byte (A1).

Golden file v2 (JSON) carries provenance so drift is ATTRIBUTED:
  {"version": 2, "cli": ..., "core_source_id": ..., "recorded_iso": ...,
   "sequence": [{"method", "args", "expect"} ...]}
Legacy plain-line goldens still check, flagged RECORD_AGAIN.

check() exit codes: 0 exact match; 1 answer drift; 2 environment
(missing binary) or STALE core (source id mismatch -> rebuild, don't
re-record).  SAEM_GOLDEN_ALLOW_STALE=1 downgrades stale to a warning.

Commands: record | check | --selftest (tool witness via a stub core).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


# ------------------------------------------------------------- environment
def cli_cmd():
    env = os.environ.get("SAEM_CLI")
    cands = ([Path(env)] if env else
             [ROOT / "build" / "saem_cli", ROOT / "build" / "saem_cli.exe"])
    for c in cands:
        if c.exists():
            return [str(c)]
    return None


def core_source_id(cmd):
    try:
        r = subprocess.run(cmd + ["--source-id"], capture_output=True,
                           text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def run_sequence(cmd):
    """Spawn core, replay SEQUENCE, collect one answer line per step."""
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True, bufsize=1)
    except OSError as e:
        raise RuntimeError(f"cannot spawn core: {e}")
    out = []
    try:
        for i, (method, args) in enumerate(SEQUENCE, 1):
            proc.stdin.write(json.dumps({"id": i, "method": method,
                                         "args": args},
                                        separators=(",", ":")) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError(f"core closed stdout at step {i} ({method})")
            out.append(line.rstrip("\n"))
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return out


# ------------------------------------------------------------------ record
def record(cmd=None, gold=GOLD):
    cmd = cmd or cli_cmd()
    if not cmd:
        print("[golden] core binary missing; nothing recorded")
        return 2
    lines = run_sequence(cmd)
    if len(set(lines)) == 1:
        print("[golden] suspicious: every answer identical; refusing to record")
        return 1
    sid = core_source_id(cmd)
    gold = {"version": 2, "cli": os.path.basename(cmd[-1]),
            "core_source_id": sid,
            "recorded_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime()),
            "sequence": [{"method": m, "args": a, "expect": l}
                         for (m, a), l in zip(SEQUENCE, lines)]}
    Path(gold).parent.mkdir(parents=True, exist_ok=True)
    Path(gold).write_text(json.dumps(gold, indent=2) + "\n", encoding="utf-8")
    print(f"[golden] recorded {len(lines)} answers (core={sid or '?'}) -> {gold}")
    return 0


# ------------------------------------------------------------------- check
def _load(gold):
    p = Path(gold)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and obj.get("version") == 2:
            return obj
    except json.JSONDecodeError:
        pass
    return {"version": 1, "lines": [l for l in text.splitlines() if l.strip()]}


def check(cmd=None, gold=GOLD):
    g = _load(gold)
    if g is None:
        print("[golden] no golden file; run: python3 tools/golden_qcos.py record")
        return 2
    cmd = cmd or cli_cmd()
    if not cmd:
        print("[golden] core binary missing")
        return 2
    try:
        got = run_sequence(cmd)
    except RuntimeError as e:
        print(f"[golden] {e}")
        return 2

    if g["version"] == 2:
        sid_now = core_source_id(cmd)
        sid_gold = g.get("core_source_id")
        if sid_now and sid_gold and sid_now != sid_gold:
            allow = os.environ.get("SAEM_GOLDEN_ALLOW_STALE") == "1"
            msg = (f"[golden] STALE core: binary={sid_now[:12]} "
                   f"golden={sid_gold[:12]} -> rebuild, do NOT re-record")
            if not allow:
                print(msg)
                return 2
            print(msg + " (allowed by env)")
        seq = g["sequence"]
        bad = 0
        if len(seq) != len(got):
            print(f"[golden] length mismatch {len(seq)} vs {len(got)}")
            bad += 1
        for step, line in zip(seq, got):
            if step["expect"] != line:
                bad += 1
                print(f"[golden] {step['method']} DRIFT\n  want={step['expect']}"
                      f"\n  got ={line}")
            else:
                print(f"[golden] {step['method']} ok")
        return 1 if bad else 0

    # legacy v1: plain lines
    print("[golden] legacy golden format; RECORD_AGAIN after this check")
    bad = 0
    for (m, _a), want, line in zip(SEQUENCE, g["lines"], got):
        if want != line:
            bad += 1
            print(f"[golden] {m} DRIFT\n  want={want}\n  got ={line}")
    if len(g["lines"]) != len(got):
        bad += 1
    return 1 if bad else 0


# ---------------------------------------------------------------- selftest
_STUB = '''
import json, os, sys
mode = os.environ.get("STUB_MODE", "ok")
for line in sys.stdin:
    req = json.loads(line)
    m, i = req["method"], req["id"]
    if m == "qcos.gate":
        ans = {"id": i, "ok": False, "reason": "non-finite"}
    elif m == "qcos.exec":
        ans = {"id": i, "ok": True, "dst": "c", "value": 5}
    elif m == "qcos.read":
        ans = {"id": i, "ok": True, "value": 999 if mode == "drift" else 5}
    elif m == "qcos.cost":
        ans = {"id": i, "ok": True, "steps": 3}
    elif m == "qcos.provenance":
        ans = {"id": i, "ok": True, "source": "stub"}
    else:
        ans = {"id": i, "ok": True, "boot": 1}
    print(json.dumps(ans, separators=(",", ":")), flush=True)
'''


def selftest():
    import tempfile
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "stub_core.py"
        stub.write_text(_STUB, encoding="utf-8")
        gold = Path(td) / "qcos.json"
        cmd = [sys.executable, str(stub)]

        want("record", record(cmd, gold) == 0 and gold.exists())
        g = json.loads(gold.read_text(encoding="utf-8"))
        want("provenance-stamped", g["version"] == 2
             and len(g["sequence"]) == len(SEQUENCE))
        want("check-clean", check(cmd, gold) == 0)
        os.environ["STUB_MODE"] = "drift"
        try:
            want("check-catches-drift", check(cmd, gold) == 1)
        finally:
            os.environ.pop("STUB_MODE", None)
        want("missing-binary-exit-2",
             check([str(Path(td) / "nope")], gold) == 2)
    return checks


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    if len(sys.argv) < 2 or sys.argv[1] not in ("record", "check"):
        print("usage: golden_qcos.py [record|check|--selftest]")
        return 1
    return record() if sys.argv[1] == "record" else check()


if __name__ == "__main__":
    sys.exit(main())
