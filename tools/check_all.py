#!/usr/bin/env python3
"""Saem universal checker.

Rechecks core C, C++, C#, and Python folders for errors.

Checks:
    - C/C++ source patterns and full core build
    - C# source sanity and dotnet build if available
    - Python AST/syntax checks
    - Required project files
    - GitHub workflow presence
    - produces JSON + Markdown + GitHub step summary

Usage:
    python3 tools/check_all.py
    python3 tools/check_all.py --json
    python3 tools/check_all.py --report reports/check_all.json --markdown reports/check_all.md
    python3 tools/check_all.py --github-summary --fail-on-warning
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
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    "__pycache__",
    "build",
    "media",
    "temp_audio",
    "temp_jobs",
    "output_shorts",
    "logs",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    "grown",
}

CPP_DIRS = [
    ROOT / "core" / "src",
    ROOT / "core",
]

CSHARP_DIRS = [
    ROOT / "SaemQcos",
]

PYTHON_DIRS = [
    ROOT,
    ROOT / "saem",
    ROOT / "tools",
    ROOT / "tests",
]

REQUIRED_CORE_FILES = [
    ROOT / "tools" / "build.py",
    ROOT / "core" / "src" / "api.hpp",
    ROOT / "core" / "src" / "api.cpp",
    ROOT / "core" / "src" / "cli.cpp",
    ROOT / "core" / "src" / "json.hpp",
]

IMPORTANT_PYTHON_FILES = [
    ROOT / "batch_runner.py",
    ROOT / "render_universal.py",
    ROOT / "generate_audio.py",
    ROOT / "schema_validator.py",
]

WORKFLOW_CANDIDATES = [
    ROOT / ".github" / "workflows" / "render_shorts.yml",
    ROOT / ".github" / "workflows" / "saem_bot.yml",
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
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "cmd": " ".join(str(c) for c in cmd),
            "stdout": proc.stdout[-100000:],
            "stderr": proc.stderr[-100000:],
        }
    except Exception as e:
        return {
            "ok": False,
            "returncode": -1,
            "cmd": " ".join(str(c) for c in cmd),
            "stdout": "",
            "stderr": str(e),
        }


def is_excluded(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & EXCLUDED_DIR_NAMES)


def balance_check(code: str) -> Tuple[bool, str]:
    """Very small delimiter checker for C/C++/C#.

    It ignores comments and string/char literals in a best-effort way.
    It is not a full parser, but it catches many catastrophic syntax breaks.
    """
    stack: List[str] = []
    i = 0
    n = len(code)

    in_line_comment = False
    in_block_comment = False
    in_string: str | None = None

    pairs = {
        "}": "{",
        "]": "[",
        ")": "(",
    }

    while i < n:
        c = code[i]

        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if c == "*" and i + 1 < n and code[i + 1] == "/":
                in_block_comment = False
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
            in_line_comment = True
            i += 2
            continue

        if c == "/" and i + 1 < n and code[i + 1] == "*":
            in_block_comment = True
            i += 2
            continue

        if c in ("'", '"'):
            in_string = c
            i += 1
            continue

        if c in "{[(":
            stack.append(c)
            i += 1
            continue

        if c in "}])":
            if not stack or stack.pop() != pairs[c]:
                return False, f"unbalanced delimiter near index {i}"
            i += 1
            continue

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
    warnings: List[str] = []

    text = read_text(path)
    if text.startswith("__READ_ERROR__"):
        errors.append(text)
        return errors, warnings

    try:
        ast.parse(text, filename=str(path))
    except SyntaxError as e:
        errors.append(f"SyntaxError at line {e.lineno}: {e.msg}")
        return errors, warnings

    try:
        compile(text, str(path), "exec")
    except Exception as e:
        errors.append(f"Compile error: {e}")

    return errors, warnings


def check_python() -> Dict[str, Any]:
    files: List[Path] = []

    for base in PYTHON_DIRS:
        if not base.exists():
            continue

        if base == ROOT:
            for p in base.glob("*.py"):
                if not is_excluded(p):
                    files.append(p)
        else:
            for p in base.rglob("*.py"):
                if not is_excluded(p):
                    files.append(p)

    files = sorted(set(files), key=lambda p: rel(p))

    all_errors: List[Dict[str, str]] = []
    all_warnings: List[Dict[str, str]] = []

    for f in files:
        errs, warns = check_python_file(f)
        for e in errs:
            all_errors.append({"file": rel(f), "error": e})
        for w in warns:
            all_warnings.append({"file": rel(f), "warning": w})

    return {
        "ok": len(all_errors) == 0,
        "files_checked": len(files),
        "errors": all_errors,
        "warnings": all_warnings,
    }


def check_cpp_text(path: Path, text: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if text.startswith("__READ_ERROR__"):
        errors.append(text)
        return errors, warnings

    ok, why = balance_check(text)
    if not ok:
        errors.append(f"delimiter problem: {why}")

    # Known LLM/compiler-integration failure patterns.
    if re.search(r'Registrar\s*\(\s*"[^"]+"\s*,\s*\{', text):
        errors.append("Registrar appears to be missing a lambda signature: use [](const Json& a) { ... }")

    if re.search(r"auto\s+\w+\s*=\s*&\s*\{", text):
        errors.append("malformed lambda capture: auto x = & { is invalid C++")

    if re.search(r"operator\s+const\s*\{", text):
        errors.append("malformed operator overload: expected operator[]( ... ) const")

    if re.search(r"(?<!')''(?!')", text):
        warnings.append("empty character literal '' detected; this is invalid C++ if not in a comment")

    return errors, warnings


def collect_cpp_files() -> List[Path]:
    files: List[Path] = []

    for base in CPP_DIRS:
        if not base.exists():
            continue
        for ext in ("*.c", "*.cpp", "*.h", "*.hpp", "*.inc"):
            for p in base.rglob(ext):
                if not is_excluded(p):
                    files.append(p)

    return sorted(set(files), key=lambda p: rel(p))


def smoke_test_core() -> Tuple[bool, str]:
    exe_name = "saem_cli.exe" if os.name == "nt" else "saem_cli"
    binary = ROOT / "build" / exe_name

    if not binary.exists():
        return False, f"missing binary: {rel(binary)}"

    r = run_cmd([str(binary), "--source-id"], timeout=30)
    if not r["ok"]:
        return False, r["stderr"] or r["stdout"]

    source_id = r["stdout"].strip()
    if not source_id:
        return False, "saem_cli --source-id returned empty"

    methods = ["gen.topics", "core.methods", "qcos.boot"]
    for i, method in enumerate(methods, start=1):
        payload = json.dumps({"id": i, "method": method, "args": {}})
        r = run_cmd([str(binary)], timeout=60)
        proc = subprocess.run(
            [str(binary)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=60,
        )
        try:
            out = json.loads(proc.stdout.strip())
        except Exception:
            return False, f"{method}: non-JSON response"

        if out.get("ok") is not True:
            return False, f"{method}: {out.get('error', 'unknown failure')}"

    return True, source_id


def check_cpp(skip_build: bool = False) -> Dict[str, Any]:
    files = collect_cpp_files()

    all_errors: List[Dict[str, str]] = []
    all_warnings: List[Dict[str, str]] = []

    for f in files:
        text = read_text(f)
        errs, warns = check_cpp_text(f, text)
        for e in errs:
            all_errors.append({"file": rel(f), "error": e})
        for w in warns:
            all_warnings.append({"file": rel(f), "warning": w})

    build_info: Dict[str, Any] = {"skipped": skip_build}

    if not skip_build:
        build_py = ROOT / "tools" / "build.py"
        if not build_py.exists():
            all_errors.append({"file": "tools/build.py", "error": "missing build script"})
        else:
            b = run_cmd([sys.executable, str(build_py), "all"])
            build_info["build"] = b

            if not b["ok"]:
                all_errors.append(
                    {
                        "file": "tools/build.py",
                        "error": "C/C++ build failed: "
                        + (b["stderr"][-1000:] or b["stdout"][-1000:] or "unknown build failure"),
                    }
                )
            else:
                v = run_cmd([sys.executable, str(build_py), "verify"])
                build_info["verify"] = v
                if not v["ok"]:
                    all_errors.append(
                        {
                            "file": "tools/build.py",
                            "error": "C/C++ verify failed: "
                            + (v["stderr"][-1000:] or v["stdout"][-1000:] or "unknown verify failure"),
                        }
                    )
                else:
                    ok, info = smoke_test_core()
                    build_info["smoke_ok"] = ok
                    build_info["source_id"] = info if ok else None
                    if not ok:
                        all_errors.append({"file": "build/saem_cli", "error": f"core smoke test failed: {info}"})

    return {
        "ok": len(all_errors) == 0,
        "files_checked": len(files),
        "errors": all_errors,
        "warnings": all_warnings,
        "build": build_info,
    }


def check_csharp(skip_dotnet: bool = False) -> Dict[str, Any]:
    files: List[Path] = []

    for base in CSHARP_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.cs"):
            if not is_excluded(p):
                files.append(p)

    files = sorted(set(files), key=lambda p: rel(p))

    all_errors: List[Dict[str, str]] = []
    all_warnings: List[Dict[str, str]] = []

    for f in files:
        text = read_text(f)
        if text.startswith("__READ_ERROR__"):
            all_errors.append({"file": rel(f), "error": text})
            continue

        ok, why = balance_check(text)
        if not ok:
            all_errors.append({"file": rel(f), "error": f"delimiter problem: {why}"})

        if re.search(r"(?<!')''(?!')", text):
            all_warnings.append({"file": rel(f), "warning": "empty character literal '' detected"})

    csproj_files: List[Path] = []
    for base in CSHARP_DIRS:
        if base.exists():
            csproj_files.extend(base.rglob("*.csproj"))

    dotnet_info: Dict[str, Any] = {"skipped": skip_dotnet}

    if not skip_dotnet:
        dotnet = shutil.which("dotnet")
        if not dotnet:
            all_warnings.append(
                {
                    "file": "SaemQcos/",
                    "warning": "dotnet SDK not found; C# compile check skipped",
                }
            )
        elif not csproj_files:
            all_errors.append(
                {
                    "file": "SaemQcos/",
                    "error": "dotnet found but no .csproj file exists; add SaemQcos/SaemQcos.csproj",
                }
            )
        else:
            csproj = csproj_files[0]
            r = run_cmd([dotnet, "build", str(csproj), "-nologo", "-clp:ErrorsOnly"])
            dotnet_info["build"] = r
            if not r["ok"]:
                all_errors.append(
                    {
                        "file": rel(csproj),
                        "error": "dotnet build failed: "
                        + (r["stderr"][-1000:] or r["stdout"][-1000:] or "unknown dotnet failure"),
                    }
                )

    return {
        "ok": len(all_errors) == 0,
        "files_checked": len(files),
        "errors": all_errors,
        "warnings": all_warnings,
        "csproj_files": [rel(p) for p in csproj_files],
        "dotnet": dotnet_info,
    }


def check_project_files() -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    for f in REQUIRED_CORE_FILES:
        if not f.exists():
            errors.append({"file": rel(f), "error": "required core file missing"})

    for f in IMPORTANT_PYTHON_FILES:
        if not f.exists():
            warnings.append({"file": rel(f), "warning": "important Python factory file missing"})

    workflow_ok = any(p.exists() for p in WORKFLOW_CANDIDATES)
    if not workflow_ok:
        warnings.append(
            {
                "file": ".github/workflows/",
                "warning": "no render_shorts.yml or saem_bot.yml workflow found",
            }
        )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def count_errors(phase: Dict[str, Any]) -> int:
    return len(phase.get("errors", []))


def count_warnings(phase: Dict[str, Any]) -> int:
    return len(phase.get("warnings", []))


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("## 🤖 Saem Compiler/Bot Audit")
    lines.append("")
    lines.append(f"Timestamp: `{report['timestamp']}`")
    lines.append("")
    lines.append("| Phase | Files | Errors | Warnings | Status |")
    lines.append("|---|---:|---:|---:|---|")

    for name in ("python", "cpp", "csharp", "project"):
        phase = report["phases"][name]
        files = phase.get("files_checked", "-")
        errs = count_errors(phase)
        warns = count_warnings(phase)
        status = "✅" if phase.get("ok") else "❌"
        lines.append(f"| {name} | {files} | {errs} | {warns} | {status} |")

    lines.append("")
    lines.append(f"Total errors: **{report['errors']}**")
    lines.append(f"Total warnings: **{report['warnings']}**")
    lines.append("")

    def write_items(title: str, key: str) -> None:
        items: List[Dict[str, str]] = []
        for phase_name, phase in report["phases"].items():
            for item in phase.get(key, []):
                item2 = dict(item)
                item2["phase"] = phase_name
                items.append(item2)

        if not items:
            return

        lines.append(f"### {title}")
        lines.append("")
        for item in items[:80]:
            msg = item.get("error") or item.get("warning") or str(item)
            lines.append(f"- `{item.get('file', '?')}` [{item.get('phase')}] {msg}")
        if len(items) > 80:
            lines.append(f"- … {len(items) - 80} more")
        lines.append("")

    write_items("Errors", "errors")
    write_items("Warnings", "warnings")

    return "\n".join(lines)


def write_github_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return

    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(markdown)
            f.write("\n")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Saem universal compiler/bot checker")
    ap.add_argument("--report", default="reports/check_all.json")
    ap.add_argument("--markdown", default="reports/check_all.md")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    ap.add_argument("--github-summary", action="store_true")
    ap.add_argument("--fail-on-warning", action="store_true")
    ap.add_argument("--skip-cpp-build", action="store_true")
    ap.add_argument("--skip-csharp-dotnet", action="store_true")
    args = ap.parse_args()

    report: Dict[str, Any] = {
        "timestamp": now_iso(),
        "phases": {},
        "errors": 0,
        "warnings": 0,
        "ok": False,
    }

    report["phases"]["python"] = check_python()
    report["phases"]["cpp"] = check_cpp(skip_build=args.skip_cpp_build)
    report["phases"]["csharp"] = check_csharp(skip_dotnet=args.skip_csharp_dotnet)
    report["phases"]["project"] = check_project_files()

    total_errors = 0
    total_warnings = 0

    for phase in report["phases"].values():
        total_errors += count_errors(phase)
        total_warnings += count_warnings(phase)

    report["errors"] = total_errors
    report["warnings"] = total_warnings
    report["ok"] = total_errors == 0 and (not args.fail_on_warning or total_warnings == 0)

    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    markdown = render_markdown(report)

    markdown_path = ROOT / args.markdown
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")

    if args.github_summary:
        write_github_summary(markdown)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(markdown)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
