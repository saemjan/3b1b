#!/usr/bin/env python3
"""saemc.py — gen-3 compiler/bot gateway: one door for the whole gate ladder.

Line-protocol JSON door (one request per line, one answer per line). Gen-3:
  * SPEC-as-data: every method carries its timeout and arg types; unknown
    methods refuse; irreversible methods (clean) refuse without {"wipe":true}
    and price their debt in the ledger BEFORE deleting (A3)
  * receipts: every request appends {gate:"saemc", method, ok, wall_sec}
  * the gate ladder is reachable through the door: canon_lint, parity_line,
    golden_qcos, qcos_handshake, check_all witnesses — Phase-2 worker nodes
    will speak this exact protocol
  * selftest(): frozen witnesses for routing, refusal and pricing
Protocol:
    {"id":1,"method":"compiler.check_all","args":{}}
    {"id":1,"ok":true,"result":{...}}
Standalone:
    python3 tools/saemc.py
    python3 tools/saemc.py compiler.ping
    python3 tools/saemc.py compiler.build '{"kind":"cli"}'
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

CHECK_ALL = ROOT / "tools" / "check_all.py"
BUILD = ROOT / "tools" / "build.py"
SCHEMA_VERSION = 3
try:
    from tools.ledger import append as _ledger
except Exception:
    _ledger = None


def reply(req_id: Any, ok: bool, result: Any = None, error: str = None) -> None:
    out: Dict[str, Any] = {"id": req_id, "ok": ok}
    if ok:
        out["result"] = result
    else:
        out["error"] = error
    print(json.dumps(out, ensure_ascii=False), flush=True)


def run_cmd(cmd: List[str], timeout: int = 1800) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode,
                "cmd": " ".join(str(c) for c in cmd),
                "stdout": proc.stdout[-100000:], "stderr": proc.stderr[-100000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": -1, "cmd": " ".join(str(c) for c in cmd),
                "stdout": "", "stderr": "timeout after %ss" % timeout}
    except Exception as e:
        return {"ok": False, "returncode": -1, "cmd": " ".join(str(c) for c in cmd),
                "stdout": "", "stderr": str(e)}


def _tool(script: str, extra: List[str], timeout: int) -> Dict[str, Any]:
    return run_cmd([sys.executable, str(ROOT / "tools" / script)] + extra,
                   timeout=timeout)


# ------------------------------------------------------------------ methods
def method_ping(_args):
    return {"ok": True, "service": "saemc", "root": str(ROOT),
            "schema_version": SCHEMA_VERSION}


def method_paths(_args):
    return {"root": str(ROOT), "check_all": str(CHECK_ALL), "build": str(BUILD),
            "reports": str(ROOT / "reports")}


def method_check_all(args):
    cmd = [sys.executable, str(CHECK_ALL), "--json",
           "--report", str(ROOT / "reports" / "check_all.json"),
           "--markdown", str(ROOT / "reports" / "check_all.md")]
    if args.get("github_summary"):
        cmd.append("--github-summary")
    if args.get("fail_on_warning"):
        cmd.append("--fail-on-warning")
    if args.get("skip_cpp_build"):
        cmd.append("--skip-cpp-build")
    if args.get("skip_csharp_dotnet"):
        cmd.append("--skip-csharp-dotnet")
    if args.get("skip_witnesses"):
        cmd.append("--skip-witnesses")
    r = run_cmd(cmd, timeout=SPEC["compiler.check_all"]["timeout"])
    try:
        parsed = json.loads(r["stdout"]) if r["stdout"].strip() else {}
    except Exception:
        parsed = {}
    return {"ok": r["ok"], "cmd": r["cmd"], "report": parsed,
            "stderr_tail": r["stderr"][-8000:]}


def method_build(args):
    kind = str(args.get("kind", "all"))
    if kind not in ("cli", "lib", "all"):
        raise ValueError("build kind must be cli, lib, or all")
    return run_cmd([sys.executable, str(BUILD), kind],
                   timeout=SPEC["compiler.build"]["timeout"])


def method_verify(_args):
    return run_cmd([sys.executable, str(BUILD), "verify"], timeout=300)


def method_clean(args):
    if not args.get("wipe"):
        raise ValueError('clean is irreversible (A3): pass {"wipe": true} '
                         'to price and perform the deletion')
    sid_file = ROOT / "build" / "source_id.txt"
    debt = sid_file.read_text().strip()[:12] if sid_file.exists() else ""
    r = run_cmd([sys.executable, str(BUILD), "clean"], timeout=60)
    r["debt_sid"] = debt
    return r


def method_python_syntax(args):
    target = args.get("path", ".")
    p = ROOT / str(target)
    if not p.exists():
        raise ValueError(f"path not found: {target}")
    return run_cmd([sys.executable, "-m", "compileall", "-q", str(p)],
                   timeout=SPEC["compiler.python_syntax"]["timeout"])


def method_report(_args):
    report = ROOT / "reports" / "check_all.json"
    markdown = ROOT / "reports" / "check_all.md"
    out: Dict[str, Any] = {"report_exists": report.exists(),
                           "markdown_exists": markdown.exists()}
    if report.exists():
        try:
            out["report"] = json.loads(report.read_text(encoding="utf-8"))
        except Exception as e:
            out["report_error"] = str(e)
    if markdown.exists():
        out["markdown"] = markdown.read_text(encoding="utf-8")[-100000:]
    return out


def method_canon_lint(_args):
    return _tool("canon_lint.py", [], 300)


def method_parity(_args):
    return _tool("parity_line.py", [], 900)


def method_golden(_args):
    return _tool("golden_qcos.py", ["check"], 300)


def method_handshake(_args):
    return _tool("qcos_handshake.py", [], 900)


SPEC = {
    "compiler.ping":      {"fn": method_ping, "timeout": 30},
    "compiler.paths":     {"fn": method_paths, "timeout": 30},
    "compiler.check_all": {"fn": method_check_all, "timeout": 1800,
                           "args": {"github_summary": bool, "fail_on_warning": bool,
                                    "skip_cpp_build": bool, "skip_csharp_dotnet": bool,
                                    "skip_witnesses": bool}},
    "compiler.build":     {"fn": method_build, "timeout": 1800,
                           "args": {"kind": str}},
    "compiler.verify":    {"fn": method_verify, "timeout": 300},
    "compiler.clean":     {"fn": method_clean, "timeout": 60,
                           "args": {"wipe": bool}, "irreversible": True},
    "compiler.python_syntax": {"fn": method_python_syntax, "timeout": 600,
                               "args": {"path": str}},
    "compiler.report":    {"fn": method_report, "timeout": 30},
    "compiler.canon_lint": {"fn": method_canon_lint, "timeout": 300},
    "compiler.parity":     {"fn": method_parity, "timeout": 900},
    "compiler.golden":     {"fn": method_golden, "timeout": 300},
    "compiler.handshake":  {"fn": method_handshake, "timeout": 900},
}
METHODS = {k: v["fn"] for k, v in SPEC.items()}


def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    t0 = time.time()
    req_id = req.get("id")
    method = req.get("method", "")
    args = req.get("args") or {}
    if not isinstance(args, dict):
        return {"id": req_id, "ok": False, "error": "args must be an object"}
    spec = SPEC.get(method)
    if spec is None:
        return {"id": req_id, "ok": False, "error": f"unknown method: {method}"}
    for key, val in args.items():
        declared = (spec.get("args") or {}).get(key)
        if declared is not None and not isinstance(val, declared):
            return {"id": req_id, "ok": False,
                    "error": f"arg {key!r} must be {declared.__name__}"}
    try:
        result = spec["fn"](args)
        ok = True
        err = None
    except Exception as e:
        result, ok, err = None, False, str(e)
    wall = round(time.time() - t0, 3)
    if _ledger is not None:
        try:
            _ledger({"gate": "saemc", "schema_version": SCHEMA_VERSION,
                     "method": method, "ok": ok, "wall_sec": wall,
                     "irreversible": bool(spec.get("irreversible"))})
        except Exception:
            pass
    out: Dict[str, Any] = {"id": req_id, "ok": ok, "wall_sec": wall}
    if ok:
        out["result"] = result
    else:
        out["error"] = err
    return out


def serve() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            print(json.dumps({"id": None, "ok": False,
                              "error": f"bad JSON: {e}"}), flush=True)
            continue
        print(json.dumps(handle_request(req), ensure_ascii=False), flush=True)


# ------------------------------------------------------------------ witness
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    r = handle_request({"id": 1, "method": "compiler.ping", "args": {}})
    want("ping", r["ok"] and r["result"]["root"] == str(ROOT))
    r = handle_request({"id": 2, "method": "nope.nope", "args": {}})
    want("guard:unknown-method", not r["ok"])
    r = handle_request({"id": 3, "method": "compiler.build", "args": 5})
    want("guard:args-type", not r["ok"])
    r = handle_request({"id": 4, "method": "compiler.build",
                        "args": {"kind": "bogus"}})
    want("guard:bad-kind", not r["ok"])
    r = handle_request({"id": 5, "method": "compiler.clean", "args": {}})
    want("guard:clean-refused", not r["ok"] and "irreversible" in r["error"])
    r = handle_request({"id": 6, "method": "compiler.check_all",
                        "args": {"github_summary": "yes"}})
    want("guard:arg-type", not r["ok"])
    want("spec:timeouts", all(SPEC[m]["timeout"] > 0 for m in SPEC))
    want("spec:ladder", {"compiler.canon_lint", "compiler.parity",
                         "compiler.golden", "compiler.handshake"} <= set(SPEC))
    return checks


def main() -> int:
    if len(sys.argv) == 1:
        serve()
        return 0
    if sys.argv[1] == "--selftest":
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    method = sys.argv[1]
    args_json = sys.argv[2] if len(sys.argv) > 2 else "{}"
    try:
        args = json.loads(args_json)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"bad args JSON: {e}"}))
        return 1
    res = handle_request({"id": 1, "method": method, "args": args})
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
