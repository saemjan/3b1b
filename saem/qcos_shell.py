#!/usr/bin/env python3
"""The QCOS shell: Python layer of the c/c++/c#/python architecture.

Spawns saem_cli (the OS session), drives the constitutional kernel through
the line protocol, and keeps the L3 ledger on disk: an append-only record
of every latch/exec with wall-clock time, plus periodic snapshots. The
ledger is the machine cousin of THINK.md §3 -- replay it and the session
returns exactly.

    python3 -m saem.qcos_shell boot
    python3 -m saem.qcos_shell latch mass '{"m": 2.0}'
    python3 -m saem.qcos_shell lower '{"want":"combine","a":"mass","b":"h","dst":"e"}'
    python3 -m saem.qcos_shell exec '{"steps":[...]}'
    python3 -m saem.qcos_shell provenance
    python3 -m saem.qcos_shell replay
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "build" / "saem_cli"
LEDGER = ROOT / "logs" / "qcos_ledger.jsonl"


class Qcos:
    """One saem_cli process = one OS session."""

    def __init__(self, cli=CLI):
        self.p = subprocess.Popen([str(cli)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)
        self._id = 0

    def call(self, method, **args):
        self._id += 1
        self.p.stdin.write(json.dumps(
            {"id": self._id, "method": method, "args": args},
            ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise SystemExit("core closed the door")
        env = json.loads(line)
        if env.get("id") != self._id:
            raise SystemExit("core answered a different question")
        if not env.get("ok"):
            raise ValueError(env.get("error", "unknown failure"))
        return env["result"]

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def log_append(entry):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry["wall"] = time.time()
    entry["iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(entry["wall"]))
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_read():
    if not LEDGER.exists():
        return []
    out = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def cmd_boot(q):
    r = q.call("qcos.boot")
    print(json.dumps(r, indent=2))
    log_append({"op": "boot", "self_ok": r["self"]["ok"],
                "constitution": r["constitution"]})
    return 0 if r["self"]["ok"] else 1


def cmd_latch(q, key, value_json):
    r = q.call("qcos.latch", key=key, value=json.loads(value_json))
    log_append({"op": "latch", "key": key, "value": json.loads(value_json),
                "hash": r["hash"]})
    print(json.dumps(r))
    return 0 if r["ok"] else 1


def cmd_read(q, key):
    print(json.dumps(q.call("qcos.read", key=key)))
    return 0


def cmd_lower(q, intent_json):
    r = q.call("qcos.lower", **json.loads(intent_json))
    print(json.dumps(r, indent=2))
    log_append({"op": "lower", "cir": r["cir"]})
    return 0


def cmd_exec(q, cir_json):
    r = q.call("qcos.exec", cir=json.loads(cir_json))
    log_append({"op": "exec", "cir": json.loads(cir_json),
                "ok": r["ok"], "hash": r["hash"]})
    print(json.dumps(r, indent=2))
    return 0 if r["ok"] else 1


def cmd_provenance(q):
    r = q.call("qcos.provenance")
    print(json.dumps(r, indent=2))
    return 0 if r["verify"] else 1


def cmd_snapshot(q):
    r = q.call("qcos.snapshot")
    log_append({"op": "snapshot", "working": r["working"], "prov": r["prov"]})
    print(json.dumps(r, indent=2))
    return 0


def cmd_replay(q):
    """Re-apply every latch in the ledger to a fresh session and compare."""
    entries = [e for e in log_read() if e.get("op") == "latch"]
    for e in entries:
        r = q.call("qcos.latch", key=e["key"], value=e["value"])
        if not r["ok"]:
            print(f"[replay] FAIL at {e.get('iso')}: {e['key']}")
            return 1
    snap = q.call("qcos.snapshot")
    snaps = [e for e in log_read() if e.get("op") == "snapshot"]
    if snaps:
        want = json.dumps(snaps[-1]["working"], sort_keys=True)
        got = json.dumps(snap["working"], sort_keys=True)
        if want != got:
            print("[replay] working memory diverged from last snapshot")
            return 1
    print(f"[replay] ok: {len(entries)} latches reproduced")
    return 0


def main():
    ap = argparse.ArgumentParser(description="QCOS shell")
    ap.add_argument("cmd", choices=["boot", "latch", "read", "lower", "exec",
                                    "provenance", "snapshot", "replay"])
    ap.add_argument("a1", nargs="?")
    ap.add_argument("a2", nargs="?")
    a = ap.parse_args()
    with Qcos() as q:
        if a.cmd == "boot":
            return cmd_boot(q)
        if a.cmd == "latch":
            return cmd_latch(q, a.a1, a.a2)
        if a.cmd == "read":
            return cmd_read(q, a.a1)
        if a.cmd == "lower":
            return cmd_lower(q, a.a1)
        if a.cmd == "exec":
            return cmd_exec(q, a.a1)
        if a.cmd == "provenance":
            return cmd_provenance(q)
        if a.cmd == "snapshot":
            return cmd_snapshot(q)
        if a.cmd == "replay":
            return cmd_replay(q)
    return 1


if __name__ == "__main__":
    sys.exit(main())
