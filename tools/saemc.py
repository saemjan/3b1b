#!/usr/bin/env python3
"""Saem compiler gateway.

A small line-protocol JSON door for compiler/bot integration.

Protocol:
    one JSON request per line:
        {"id":1,"method":"compiler.check_all","args":{}}

    one JSON answer per line:
        {"id":1,"ok":true,"result":{...}}

Methods:
    compiler.ping
    compiler.paths
    compiler.check_all
    compiler.build
    compiler.verify
    compiler.clean
    compiler.python_syntax
    compiler.report

Standalone:
    python3 tools/saemc.py
    python3 tools/saemc.py compiler.ping
    python3 tools/saemc.py compiler.check_all '{}'
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
CHECK_ALL = ROOT / "tools" / "check_all.py"
BUILD = ROOT / "tools" / "build.py"


def reply(req_id: Any, ok: bool, result: Any = None, error: str | None = None) -> None:
    out: Dict[str, Any] = {"id": req_id, "ok": ok}
    if ok:
        out["result"] = result
    else:
        out["error"] = error
    print(json.dumps(out, ensure_ascii=False), flush=True)


def run_cmd(cmd: List[str], timeout: int = 3600) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "cmd": " ".join(cmd),
            "stdout": proc.stdout[-100000:],
            "stderr": proc.stderr[-100000:],
        }
    except Exception as e:
        return {
            "ok": False,
            "returncode": -1,
            "cmd": " ".join(cmd),
            "stdout": "",
            "stderr": str(e),
        }


def method_ping(_args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "saemc",
        "root": str(ROOT),
    }


def method_paths(_args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "root": str(ROOT),
        "check_all": str(CHECK_ALL),
        "build": str(BUILD),
        "reports": str(ROOT / "reports"),
    }


def method_check_all(args: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(CHECK_ALL),
        "--json",
        "--report",
        str(ROOT / "reports" / "check_all.json"),
        "--markdown",
        str(ROOT / "reports" / "check_all.md"),
    ]

    if args.get("github_summary"):
        cmd.append("--github-summary")

    if args.get("fail_on_warning"):
        cmd.append("--fail-on-warning")

    if args.get("skip_cpp_build"):
        cmd.append("--skip-cpp-build")

    if args.get("skip_csharp_dotnet"):
        cmd.append("--skip-csharp-dotnet")

    r = run_cmd(cmd)

    try:
        parsed = json.loads(r["stdout"]) if r["stdout"].strip() else {}
    except Exception:
        parsed = {}

    return {
        "ok": r["ok"],
        "cmd": r["cmd"],
        "report": parsed,
        "stderr_tail": r["stderr"][-8000:],
    }


def method_build(args: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(args.get("kind", "all"))
    if kind not in ("cli", "lib", "all"):
        raise ValueError("build kind must be cli, lib, or all")

    return run_cmd([sys.executable, str(BUILD), kind])


def method_verify(_args: Dict[str, Any]) -> Dict[str, Any]:
    return run_cmd([sys.executable, str(BUILD), "verify"])


def method_clean(_args: Dict[str, Any]) -> Dict[str, Any]:
    return run_cmd([sys.executable, str(BUILD), "clean"])


def method_python_syntax(args: Dict[str, Any]) -> Dict[str, Any]:
    target = args.get("path", ".")
    p = ROOT / str(target)
    if not p.exists():
        raise ValueError(f"path not found: {target}")

    return run_cmd([sys.executable, "-m", "compileall", "-q", str(p)])


def method_report(_args: Dict[str, Any]) -> Dict[str, Any]:
    report = ROOT / "reports" / "check_all.json"
    markdown = ROOT / "reports" / "check_all.md"

    out: Dict[str, Any] = {
        "report_exists": report.exists(),
        "markdown_exists": markdown.exists(),
    }

    if report.exists():
        try:
            out["report"] = json.loads(report.read_text(encoding="utf-8"))
        except Exception as e:
            out["report_error"] = str(e)

    if markdown.exists():
        out["markdown"] = markdown.read_text(encoding="utf-8")[-100000:]

    return out


METHODS = {
    "compiler.ping": method_ping,
    "compiler.paths": method_paths,
    "compiler.check_all": method_check_all,
    "compiler.build": method_build,
    "compiler.verify": method_verify,
    "compiler.clean": method_clean,
    "compiler.python_syntax": method_python_syntax,
    "compiler.report": method_report,
}


def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    req_id = req.get("id")
    method = req.get("method", "")
    args = req.get("args") or {}

    if not isinstance(args, dict):
        return {
            "id": req_id,
            "ok": False,
            "error": "args must be an object",
        }

    fn = METHODS.get(method)
    if fn is None:
        return {
            "id": req_id,
            "ok": False,
            "error": f"unknown method: {method}",
        }

    try:
        result = fn(args)
        return {
            "id": req_id,
            "ok": True,
            "result": result,
        }
    except Exception as e:
        return {
            "id": req_id,
            "ok": False,
            "error": str(e),
        }


def serve() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception as e:
            print(
                json.dumps({"id": None, "ok": False, "error": f"bad JSON: {e}"}),
                flush=True,
            )
            continue

        print(json.dumps(handle_request(req), ensure_ascii=False), flush=True)


def main() -> int:
    if len(sys.argv) == 1:
        serve()
        return 0

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
