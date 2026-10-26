#!/usr/bin/env python3
"""parity_line.py — gen-3 R16 gate: C++ core vs JS ruler, line for line.

Constitutional placement:
  A6  the JS bridge is a RULER, never a fallback: both pipes are required.
      Missing core binary, missing node, or missing corpus = ENVIRONMENT
      failure (exit 2), never a silent pass.
  A5  deferrals are priced data, not comments: tests/corpus/deferred.json
      holds [{"method", "reason", "since", "until"}]; a deferral past its
      "until" date fails the gate. The frozen fallback list below carries
      the same pricing so the gate cannot run unpriced.
  A2  no hidden state: corpus and binary paths overridable by env
      (SAEM_PARITY_CORPUS, SAEM_CLI, SAEM_JS_BRIDGE); every run appends a
      receipt to the ledger.

Exit codes: 0 parity holds | 1 mismatch/expired/timeout | 2 environment
Usage:
    python3 tools/parity_line.py [--json] [--corpus PATH]
    python3 tools/parity_line.py --selftest
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORPUS = Path(os.environ.get("SAEM_PARITY_CORPUS",
                             ROOT / "tests" / "corpus" / "requests.jsonl"))
DEFERRED_FILE = ROOT / "tests" / "corpus" / "deferred.json"
ASK_TIMEOUT = float(os.environ.get("SAEM_PARITY_TIMEOUT", "10"))

# frozen fallback pricing (A5): every deferral carries an expiry
FROZEN_DEFERRED = {
    m: {"reason": "scope doc pending", "since": "2026-01-01",
        "until": "2026-12-31"}
    for m in ("papers.parse", "papers.fromRows", "papers.splitMCQ",
              "papers.normAnswer", "papers.keyMap", "papers.autoTag",
              "papers.script", "bank.stats", "bank.rows", "bank.isTestable",
              "paper.rows", "core.hash", "core.info")
}


# ------------------------------------------------------------- environment
def core_cmd():
    env = os.environ.get("SAEM_CLI")
    cands = ([Path(env)] if env else
             [ROOT / "build" / "saem_cli", ROOT / "build" / "saem_cli.exe",
              ROOT / "core" / "build" / "saem_cli",
              ROOT / "core" / "build" / "saem_cli.exe"])
    for c in cands:
        if c.exists():
            return [str(c)]
    return None


def js_cmd():
    bridge = Path(os.environ.get("SAEM_JS_BRIDGE",
                                 ROOT / "tools" / "ref_bridge.js"))
    node = shutil.which("node")
    if node and bridge.exists():
        return [node, str(bridge)]
    return None


class Pipe:
    """One request/response pipe with a hard timeout (no CI hangs)."""

    def __init__(self, cmd, name, env=None):
        self.name = name
        run_env = dict(os.environ)
        if env:
            run_env.update(env)
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True,
                                  bufsize=1, cwd=ROOT, env=run_env)
        self.q = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        for line in self.p.stdout:
            self.q.put(line.rstrip("\n"))

    def ask(self, line, timeout=ASK_TIMEOUT):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f"{self.name} silent for {timeout}s")

    def close(self):
        try:
            self.p.stdin.close()
        except Exception:
            pass
        try:
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


# ---------------------------------------------------------------- deferrals
def load_deferred():
    if DEFERRED_FILE.exists():
        try:
            raw = json.loads(DEFERRED_FILE.read_text(encoding="utf-8"))
            return {e["method"]: e for e in raw if isinstance(e, dict)
                    and e.get("method")}
        except Exception as e:
            print(f"[parity] deferred.json unreadable ({e}); using frozen")
    return dict(FROZEN_DEFERRED)


def _expired(entry, today):
    until = entry.get("until")
    return bool(until) and until < today


# ---------------------------------------------------------------- the gate
def run_parity(core, js, lines, deferred, timeout=ASK_TIMEOUT):
    today = date.today().isoformat()
    rep = {"ok": 0, "deferred": 0, "expired": 0, "mismatch": 0, "timeout": 0,
           "details": []}
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            method = json.loads(raw).get("method", "?")
        except json.JSONDecodeError:
            method = "?"
        try:
            a = core.ask(raw, timeout)
            b = js.ask(raw, timeout)
        except TimeoutError as e:
            rep["timeout"] += 1
            rep["details"].append({"method": method, "verdict": "timeout",
                                   "detail": str(e)})
            continue
        if a == b:
            rep["ok"] += 1
            rep["details"].append({"method": method, "verdict": "ok"})
        elif method in deferred and not _expired(deferred[method], today):
            rep["deferred"] += 1
            rep["details"].append({"method": method, "verdict": "deferred",
                                   "reason": deferred[method].get("reason", ""),
                                   "until": deferred[method].get("until")})
        elif method in deferred:
            rep["expired"] += 1
            rep["details"].append({"method": method, "verdict": "EXPIRED",
                                   "until": deferred[method].get("until"),
                                   "cpp": a, "js": b})
        else:
            rep["mismatch"] += 1
            rep["details"].append({"method": method, "verdict": "MISMATCH",
                                   "cpp": a, "js": b})
    rep["bad"] = rep["mismatch"] + rep["expired"] + rep["timeout"]
    return rep


def _receipt(rep, status):
    try:
        from tools.ledger import append
        append({"gate": "parity_line", "schema_version": 3,
                "status": status, **{k: v for k, v in rep.items()
                                     if k != "details"}})
    except Exception:
        pass


def main():
    as_json = "--json" in sys.argv
    corpus = CORPUS
    if "--corpus" in sys.argv:
        corpus = Path(sys.argv[sys.argv.index("--corpus") + 1])
    if not corpus.exists():
        print(f"[parity] corpus missing: {corpus}")
        _receipt({"ok": 0, "deferred": 0, "expired": 0, "mismatch": 0,
                  "timeout": 0, "bad": 1}, "env")
        return 2
    cc, jc = core_cmd(), js_cmd()
    if cc is None:
        print("[parity] core binary missing (build/ or core/build/, "
              "or set SAEM_CLI)")
        _receipt({"ok": 0, "deferred": 0, "expired": 0, "mismatch": 0,
                  "timeout": 0, "bad": 1}, "env")
        return 2
    if jc is None:
        print("[parity] JS ruler unavailable (node or ref_bridge.js missing); "
              "A6 forbids skipping it")
        _receipt({"ok": 0, "deferred": 0, "expired": 0, "mismatch": 0,
                  "timeout": 0, "bad": 1}, "env")
        return 2

    lines = corpus.read_text(encoding="utf-8").splitlines()
    deferred = load_deferred()
    core, js = Pipe(cc, "core"), Pipe(jc, "js")
    t0 = time.time()
    try:
        rep = run_parity(core, js, lines, deferred)
    finally:
        core.close()
        js.close()
    rep["wall_sec"] = round(time.time() - t0, 1)
    rep["corpus_lines"] = len([l for l in lines if l.strip()])

    for d in rep["details"]:
        tag = d["verdict"]
        if tag == "ok":
            print(f"[parity] {d['method']} ok")
        elif tag == "deferred":
            print(f"[parity] {d['method']} DEFERRED until {d['until']} "
                  f"({d['reason']})")
        else:
            print(f"[parity] {d['method']} {tag}\n  cpp={d.get('cpp')}"
                  f"\n  js ={d.get('js')}{d.get('detail', '')}")
    print(f"[parity] ok={rep['ok']} deferred={rep['deferred']} "
          f"expired={rep['expired']} mismatch={rep['mismatch']} "
          f"timeout={rep['timeout']}")
    if as_json:
        print(json.dumps(rep, ensure_ascii=False))
    _receipt(rep, "pass" if rep["bad"] == 0 else "fail")
    return 1 if rep["bad"] else 0


# ---------------------------------------------------------------- witness
_STUB = '''
import json, os, sys
side = os.environ.get("STUB_SIDE", "a")
for line in sys.stdin:
    req = json.loads(line)
    m, i = req.get("method"), req.get("id")
    if side == "b" and m == "qcos.read":
        ans = {"id": i, "ok": True, "value": 6}
    else:
        ans = {"id": i, "ok": True, "value": 5}
    print(json.dumps(ans, separators=(",", ":")), flush=True)
'''


def selftest():
    import tempfile
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "stub.py"
        stub.write_text(_STUB, encoding="utf-8")
        corpus = Path(td) / "corpus.jsonl"
        corpus.write_text("\n".join(
            json.dumps({"id": i, "method": m, "args": {}})
            for i, m in enumerate(
                ["qcos.boot", "qcos.read", "papers.script", "core.hash"], 1)
        ) + "\n", encoding="utf-8")
        lines = corpus.read_text().splitlines()
        deferred = {"papers.script": {"reason": "scope", "until": "2099-01-01"},
                    "core.hash": {"reason": "canon", "until": "2000-01-01"}}
        cmd = [sys.executable, str(stub)]

        a = Pipe(cmd, "a", env={"STUB_SIDE": "a"})
        b = Pipe(cmd, "b", env={"STUB_SIDE": "a"})
        rep = run_parity(a, b, lines, deferred, timeout=5)
        want("clean-parity", rep["bad"] == 0 and rep["ok"] == 4, str(rep))
        a.close(); b.close()

        a = Pipe(cmd, "a", env={"STUB_SIDE": "a"})
        b = Pipe(cmd, "b", env={"STUB_SIDE": "b"})
        rep = run_parity(a, b, lines, deferred, timeout=5)
        want("drift-caught", rep["mismatch"] == 1, str(rep["details"]))
        want("deferral-priced", rep["deferred"] == 1)
        want("expiry-fails-closed", rep["expired"] == 1 and rep["bad"] == 2)
        a.close(); b.close()
    return checks


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        sys.exit(1 if fails else 0)
    sys.exit(main())
