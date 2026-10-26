#!/usr/bin/env python3
"""check_all.py — gen-3 universal compiler/bot auditor + witness orchestrator.

Phases are flat-dict pure runners (Phase-2 parallel-node ready):
  python_static   AST/compile + the fatal-typo class (`from future import`)
  cpp_static      delimiter balance + known LLM/compiler-integration failures
  cpp_build       tools/build.py all|verify + core smoke (--source-id, 3 methods)
  csharp_static   delimiter balance; dotnet build when the SDK is present
  js_syntax       node --check on the JS rulers (A6 health), recorded degrade
  project_files   required core files, factory files, workflow presence
  witnesses       shells out to every gen-3 gate: engine_check, golden_qcos
                  check, parity_line, canon_lint, ledger verify (exit 2 = env,
                  recorded as degradation, never a silent pass)

Receipts (A5): one append-only ledger entry per run; JSON + Markdown +
GitHub step summary, schema_version 3.
Exit codes: 0 clean | 1 errors (or warnings with --fail-on-warning)
Usage:
    python3 tools/check_all.py [--json] [--github-summary] [--fail-on-warning]
        [--skip-cpp-build] [--skip-csharp-dotnet] [--skip-witnesses]
    python3 tools/check_all.py --selftest
"""
from __future__ import annotations

import argparse
import ast
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 3

EXCLUDED_DIR_NAMES = {
    ".git", ".github", "__pycache__", "build", "media", "temp_audio",
    "temp_jobs", "output_shorts", "logs", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "grown", "reports",
}
CPP_DIRS = [ROOT / "core" / "src", ROOT / "core"]
CSHARP_DIRS = [ROOT / "SaemQcos"]
PYTHON_DIRS = [ROOT, ROOT / "saem", ROOT / "tools", ROOT / "tests"]
REQUIRED_CORE_FILES = [
    ROOT / "tools" / "build.py",
    ROOT / "core" / "src" / "api.hpp",
    ROOT / "core" / "src" / "api.cpp",
    ROOT / "core" / "src" / "cli.cpp",
    ROOT / "core" / "src" / "json.hpp",
    ROOT / "qcos.cxn",
]
IMPORTANT_PYTHON_FILES = [
    ROOT / "batch_runner.py", ROOT / "render_universal.py",
    ROOT / "generate_audio.py", ROOT / "schema_validator.py",
    ROOT / "jee_model_engine.py",
]
WORKFLOW_CANDIDATES = [
    ROOT / ".github" / "workflows" / "render_shorts.yml",
    ROOT / ".github" / "workflows" / "saem_bot.yml",
]
JS_RULERS = [ROOT / "tools" / "ref_bridge.js",
             ROOT / "tools" / "ref_bridge_qcos.js"]
FATAL_TYPO = re.compile(r"^\s*from\s+future\s+import", re.M)
WITNESS_CMDS = [
    ("engine_check", [sys.executable, str(ROOT / "tools" / "engine_check.py")]),
    ("golden_qcos", [sys.executable, str(ROOT / "tools" / "golden_qcos.py"), "check"]),
    ("parity_line", [sys.executable, str(ROOT / "tools" / "parity_line.py")]),
    ("canon_lint", [sys.executable, str(ROOT / "tools" / "canon_lint.py")]),
    ("ledger_verify", [sys.executable, str(ROOT / "tools" / "ledger.py"), "verify"]),
]


def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace(os.sep, "/")
    except Exception:
        return str(path)


def run_cmd(cmd: List[str], cwd: Path = ROOT, timeout: int = 1800) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True,
                              text=True, timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode,
                "cmd": " ".join(str(c) for c in cmd),
                "stdout": proc.stdout[-100000:], "stderr": proc.stderr[-100000:]}
    except Exception as e:
        return {"ok": False, "returncode": -1, "cmd": " ".join(str(c) for c in cmd),
                "stdout": "", "stderr": str(e)}


def is_excluded(path: Path) -> bool:
    return bool(set(path.parts) & EXCLUDED_DIR_NAMES)


# ------------------------------------------------------------- static rules
def balance_check(code: str) -> Tuple[bool, str]:
    """Best-effort delimiter checker ignoring comments and literals."""
    stack: List[str] = []
    i, n = 0, len(code)
    in_line = in_block = False
    in_string: str | None = None
    pairs = {"}": "{", "]": "[", ")": "("}
    while i < n:
        c = code[i]
        if in_line:
            if c == "\n":
                in_line = False
            i += 1
            continue
        if in_block:
            if c == "*" and i + 1 < n and code[i + 1] == "/":
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_string is not None:
            if c == "\\":
                i += 2
                continue
            if c == in_string:
                in_string = None
            i += 1
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            in_line = True
            i += 2
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            in_block = True
            i += 2
            continue
        if c in ("'", '"'):
            in_string = c
            i += 1
            continue
        if c in "{[(":
            stack.append(c)
        elif c in "}])":
            if not stack or stack.pop() != pairs[c]:
                return False, f"unbalanced delimiter near index {i}"
        i += 1
    if stack:
        return False, "unclosed delimiter at end of file"
    return True, ""


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"__READ_ERROR__ {e}"


def check_python_file(path: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    text = read_text(path)
    if text.startswith("__READ_ERROR__"):
        return [text], []
    if FATAL_TYPO.search(text):
        errors.append("fatal typo: 'from future import' must be "
                      "'from __future__ import'")
    try:
        ast.parse(text, filename=str(path))
        compile(text, str(path), "exec")
    except SyntaxError as e:
        errors.append(f"SyntaxError at line {e.lineno}: {e.msg}")
    except Exception as e:
        errors.append(f"Compile error: {e}")
    return errors, []


def check_cpp_text(text: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if text.startswith("__READ_ERROR__"):
        return [text], []
    ok, why = balance_check(text)
    if not ok:
        errors.append(f"delimiter problem: {why}")
    if re.search(r'Registrar\s*\(\s*"[^"]+"\s*,\s*\{', text):
        errors.append("Registrar missing lambda signature: use "
                      "[](const Json& a) { ... }")
    if re.search(r"auto\s+\w+\s*=\s*&\s*\{", text):
        errors.append("malformed lambda capture: auto x = & { is invalid C++")
    if re.search(r"operator\s+const\s*\{", text):
        errors.append("malformed operator overload: expected operator[]( ... ) const")
    if re.search(r"(?<!')''(?!')", text):
        warnings.append("empty character literal '' detected")
    return errors, warnings


# ------------------------------------------------------------------ phases
def phase_python() -> Dict[str, Any]:
    files: List[Path] = []
    for base in PYTHON_DIRS:
        if not base.exists():
            continue
        it = base.glob("*.py") if base == ROOT else base.rglob("*.py")
        files += [p for p in it if not is_excluded(p)]
    files = sorted(set(files), key=rel)
    errs, warns = [], []
    for f in files:
        e, w = check_python_file(f)
        errs += [{"file": rel(f), "error": x} for x in e]
        warns += [{"file": rel(f), "warning": x} for x in w]
    return {"ok": not errs, "files_checked": len(files),
            "errors": errs, "warnings": warns}


def phase_cpp_static() -> Dict[str, Any]:
    files: List[Path] = []
    for base in CPP_DIRS:
        if not base.exists():
            continue
        for ext in ("*.c", "*.cpp", "*.h", "*.hpp", "*.inc"):
            files += [p for p in base.rglob(ext) if not is_excluded(p)]
    files = sorted(set(files), key=rel)
    errs, warns = [], []
    for f in files:
        e, w = check_cpp_text(read_text(f))
        errs += [{"file": rel(f), "error": x} for x in e]
        warns += [{"file": rel(f), "warning": x} for x in w]
    return {"ok": not errs, "files_checked": len(files),
            "errors": errs, "warnings": warns}


def smoke_test_core() -> Tuple[bool, str]:
    exe = ROOT / "build" / ("saem_cli.exe" if os.name == "nt" else "saem_cli")
    if not exe.exists():
        return False, f"missing binary: {rel(exe)}"
    r = run_cmd([str(exe), "--source-id"], timeout=30)
    if not r["ok"] or not r["stdout"].strip():
        return False, (r["stderr"] or r["stdout"] or "empty source-id")
    source_id = r["stdout"].strip()
    for i, method in enumerate(["gen.topics", "core.methods", "qcos.boot"], 1):
        proc = subprocess.run(
            [str(exe)], input=json.dumps({"id": i, "method": method, "args": {}}),
            capture_output=True, text=True, timeout=60)
        try:
            out = json.loads(proc.stdout.strip())
        except Exception:
            return False, f"{method}: non-JSON response"
        if out.get("ok") is not True:
            return False, f"{method}: {out.get('error', 'unknown failure')}"
    return True, source_id


def phase_cpp_build(skip: bool) -> Dict[str, Any]:
    errs: List[Dict[str, str]] = []
    info: Dict[str, Any] = {"skipped": skip}
    if skip:
        return {"ok": True, "errors": errs, "warnings": [], "build": info}
    build_py = ROOT / "tools" / "build.py"
    if not build_py.exists():
        return {"ok": False, "errors": [{"file": "tools/build.py",
                                        "error": "missing build script"}],
                "warnings": [], "build": info}
    b = run_cmd([sys.executable, str(build_py), "all"])
    info["build"] = {"ok": b["ok"]}
    if not b["ok"]:
        errs.append({"file": "tools/build.py",
                     "error": "C/C++ build failed: "
                              + (b["stderr"][-1000:] or b["stdout"][-1000:])})
        return {"ok": False, "errors": errs, "warnings": [], "build": info}
    v = run_cmd([sys.executable, str(build_py), "verify"])
    info["verify"] = {"ok": v["ok"]}
    if not v["ok"]:
        errs.append({"file": "tools/build.py",
                     "error": "verify failed: "
                              + (v["stderr"][-1000:] or v["stdout"][-1000:])})
        return {"ok": False, "errors": errs, "warnings": [], "build": info}
    ok, sid = smoke_test_core()
    info["smoke_ok"], info["source_id"] = ok, (sid if ok else None)
    if not ok:
        errs.append({"file": "build/saem_cli", "error": f"smoke test failed: {sid}"})
    return {"ok": not errs, "errors": errs, "warnings": [], "build": info}


def phase_csharp(skip_dotnet: bool) -> Dict[str, Any]:
    files: List[Path] = []
    for base in CSHARP_DIRS:
        if base.exists():
            files += [p for p in base.rglob("*.cs") if not is_excluded(p)]
    files = sorted(set(files), key=rel)
    errs, warns = [], []
    for f in files:
        text = read_text(f)
        if text.startswith("__READ_ERROR__"):
            errs.append({"file": rel(f), "error": text})
            continue
        ok, why = balance_check(text)
        if not ok:
            errs.append({"file": rel(f), "error": f"delimiter problem: {why}"})
    csproj = [p for base in CSHARP_DIRS if base.exists()
              for p in base.rglob("*.csproj")]
    info: Dict[str, Any] = {"skipped": skip_dotnet}
    if not skip_dotnet:
        dotnet = shutil.which("dotnet")
        if not dotnet:
            warns.append({"file": "SaemQcos/",
                          "warning": "dotnet SDK not found; compile check skipped"})
        elif not csproj:
            errs.append({"file": "SaemQcos/",
                          "error": "dotnet found but no .csproj exists"})
        else:
            r = run_cmd([dotnet, "build", str(csproj[0]), "-nologo", "-clp:ErrorsOnly"])
            info["build"] = {"ok": r["ok"]}
            if not r["ok"]:
                errs.append({"file": rel(csproj[0]),
                             "error": "dotnet build failed: "
                                      + (r["stderr"][-1000:] or r["stdout"][-1000:])})
    return {"ok": not errs, "files_checked": len(files), "errors": errs,
            "warnings": warns, "csproj_files": [rel(p) for p in csproj],
            "dotnet": info}


def phase_js_syntax() -> Dict[str, Any]:
    node = shutil.which("node")
    if not node:
        return {"ok": True, "errors": [], "files_checked": 0,
                "warnings": [{"file": "tools/", "warning":
                              "node absent; JS ruler syntax unchecked (A6 degrade)"}]}
    errs, warns = [], []
    for j in JS_RULERS:
        if not j.exists():
            warns.append({"file": rel(j), "warning": "ruler file missing"})
            continue
        r = run_cmd([node, "--check", str(j)], timeout=120)
        if not r["ok"]:
            errs.append({"file": rel(j),
                         "error": "node --check failed: " + r["stderr"][-800:]})
    return {"ok": not errs, "errors": errs, "warnings": warns,
            "files_checked": len(JS_RULERS)}


def phase_project() -> Dict[str, Any]:
    errs, warns = [], []
    for f in REQUIRED_CORE_FILES:
        if not f.exists():
            errs.append({"file": rel(f), "error": "required core file missing"})
    for f in IMPORTANT_PYTHON_FILES:
        if not f.exists():
            warns.append({"file": rel(f), "warning": "important factory file missing"})
    if not any(p.exists() for p in WORKFLOW_CANDIDATES):
        warns.append({"file": ".github/workflows/",
                      "warning": "no render_shorts.yml or saem_bot.yml found"})
    return {"ok": not errs, "errors": errs, "warnings": warns}


def phase_witnesses(skip: bool) -> Dict[str, Any]:
    if skip:
        return {"ok": True, "errors": [], "warnings":
                [{"file": "tools/", "warning": "witness phase skipped by flag"}],
                "runs": []}
    errs, warns, runs = [], [], []
    for name, cmd in WITNESS_CMDS:
        r = run_cmd(cmd, timeout=900)
        runs.append({"gate": name, "returncode": r["returncode"]})
        if r["returncode"] == 0:
            continue
        if r["returncode"] == 2:
            warns.append({"file": f"tools/{name}",
                          "warning": f"environment degradation (exit 2): "
                                     + (r["stderr"][-400:] or r["stdout"][-400:])})
        else:
            errs.append({"file": f"tools/{name}",
                         "error": f"witness gate failed (exit {r['returncode']}): "
                                  + (r["stdout"][-800:] or r["stderr"][-800:])})
    return {"ok": not errs, "errors": errs, "warnings": warns, "runs": runs}


# ----------------------------------------------------------------- report
def render_markdown(report: Dict[str, Any]) -> str:
    lines = ["## 🤖 Saem Compiler/Bot Audit (gen-3)", "",
             f"Timestamp: `{report['timestamp']}`  ",
             f"Schema: v{report['schema_version']}", "",
             "| Phase | Files | Errors | Warnings | Status |",
             "|---|---:|---:|---:|---|"]
    for name, phase in report["phases"].items():
        files = phase.get("files_checked", "-")
        e = len(phase.get("errors", []))
        w = len(phase.get("warnings", []))
        lines.append(f"| {name} | {files} | {e} | {w} | "
                     f"{'✅' if phase.get('ok') else '❌'} |")
    lines += ["", f"Total errors: **{report['errors']}**",
              f"Total warnings: **{report['warnings']}**", ""]
    for key, title in (("errors", "Errors"), ("warnings", "Warnings")):
        items = [{"phase": pn, **it} for pn, ph in report["phases"].items()
                 for it in ph.get(key, [])]
        if not items:
            continue
        lines += [f"### {title}", ""]
        for it in items[:80]:
            msg = it.get("error") or it.get("warning") or str(it)
            lines.append(f"- `{it.get('file', '?')}` [{it.get('phase')}] {msg}")
        if len(items) > 80:
            lines.append(f"- … {len(items) - 80} more")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Saem universal auditor (gen-3)")
    ap.add_argument("--report", default="reports/check_all.json")
    ap.add_argument("--markdown", default="reports/check_all.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--github-summary", action="store_true")
    ap.add_argument("--fail-on-warning", action="store_true")
    ap.add_argument("--skip-cpp-build", action="store_true")
    ap.add_argument("--skip-csharp-dotnet", action="store_true")
    ap.add_argument("--skip-witnesses", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0

    t0 = time.time()
    phases = {
        "python": phase_python(),
        "cpp": phase_cpp_static(),
        "cpp_build": phase_cpp_build(args.skip_cpp_build),
        "csharp": phase_csharp(args.skip_csharp_dotnet),
        "js": phase_js_syntax(),
        "project": phase_project(),
        "witnesses": phase_witnesses(args.skip_witnesses),
    }
    total_e = sum(len(p.get("errors", [])) for p in phases.values())
    total_w = sum(len(p.get("warnings", [])) for p in phases.values())
    report = {"schema_version": SCHEMA_VERSION, "timestamp": now_iso(),
              "phases": phases, "errors": total_e, "warnings": total_w,
              "ok": total_e == 0 and (not args.fail_on_warning or total_w == 0),
              "wall_sec": round(time.time() - t0, 1)}

    rp = ROOT / args.report
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = render_markdown(report)
    mp = ROOT / args.markdown
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(md, encoding="utf-8")
    if args.github_summary and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(md + "\n")
    try:
        from tools.ledger import append
        append({"gate": "check_all", "schema_version": SCHEMA_VERSION,
                "status": "pass" if report["ok"] else "fail",
                "errors": total_e, "warnings": total_w,
                "witness_runs": phases["witnesses"].get("runs", []),
                "wall_sec": report["wall_sec"]})
    except Exception:
        pass
    print(json.dumps(report, indent=2) if args.json else md)
    return 0 if report["ok"] else 1


# --------------------------------------------------------------- selftest
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    ok, _ = balance_check("int f(){ if (a[0]=='}') { return 1; } }")
    want("balance:strings-comments", ok)
    ok, why = balance_check("void f() { int x[3; }")
    want("balance:broken", not ok, why)
    ok, _ = balance_check("char c = '{'; // } ) ]")
    want("balance:char-literal", ok)
    e, _ = check_python_file(ROOT / "tools" / "ledger.py")
    want("python:clean-file", e == [], str(e[:1]))
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.py"
        bad.write_text("from future import annotations\nx=1\n", encoding="utf-8")
        e, _ = check_python_file(bad)
        want("python:fatal-typo-caught", any("fatal typo" in x for x in e), str(e))
    e, w = check_cpp_text('Registrar r("m", { });')
    want("cpp:registrar-lambda", any("lambda" in x for x in e))
    ph = phase_witnesses(skip=True)
    want("witness:skip-recorded", ph["ok"] and ph["warnings"])
    rep = {"schema_version": 3, "timestamp": now_iso(),
           "phases": {"python": {"ok": True, "errors": [], "warnings": []}},
           "errors": 0, "warnings": 0, "ok": True, "wall_sec": 0.1}
    want("markdown:deterministic", render_markdown(rep) == render_markdown(rep))
    return checks


if __name__ == "__main__":
    sys.exit(main())
