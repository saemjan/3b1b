#!/usr/bin/env python3
"""canon_lint.py — gen-3 canon parity gate: one canon, four tongues.

Constitutional placement:
  A5  a canon method with no core binding is a dangling promise -> ERROR.
      An implementation not yet canonized is a HYPOTHESIS: it enters the
      priced queue (tests/corpus/canon_queue.json, {method, since, until,
      reason}); an expired hypothesis fails the gate.
  A6  the JS bridge is a ruler: every canon method must be reachable from
      ref_bridge.js; missing bridge binding = ERROR. C#/Python bindings are
      coverage warnings (they join the team in Phase 2).
  Fail closed: missing qcos.cxn or missing core/src = exit 2 (environment),
      never a silent "parity ok".
  Cross-gate witness: methods exercised by golden_qcos.SEQUENCE and the
      parity_line corpus must be canonized, else ERROR.

Exit codes: 0 parity holds | 1 dangling/expired/uncanonized | 2 environment
Usage:
    python3 tools/canon_lint.py [--json] [--strict] [--github-summary]
    python3 tools/canon_lint.py --selftest
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_VERSION = 3
CANON_RE = re.compile(r"^@method\s+([\w.]+)", re.M)
QUEUE_FILE = ROOT / "tests" / "corpus" / "canon_queue.json"

# (tongue, base dir, glob, binding regex, severity when a canon method is absent)
TONGUES = [
    ("cpp", ROOT / "core" / "src", "*.cpp",
     re.compile(r'Registrar\s+\w+\s*\(\s*"([\w.]+)"'), "error"),
    ("js", ROOT / "tools", "ref_bridge.js",
     re.compile(r'"([\w.]+)"\s*:\s*(?:async\s*)?\(|case\s+"([\w.]+)"\s*:'), "error"),
    ("cs", ROOT / "SaemQcos", "*.cs",
     re.compile(r'case\s+"([\w.]+)"\s*:'), "warn"),
    ("py", ROOT / "tools", "qcosc.py",
     re.compile(r'"([\w.]+)"\s*:\s*(?:lambda|route_|handle_|self\.)'), "warn"),
]


# ------------------------------------------------------------------ parsers
def parse_canon(text: str):
    return set(CANON_RE.findall(text or ""))


def scan_tongue(base: Path, glob: str, regex):
    found = set()
    if not base.exists():
        return found, False
    paths = [base] if base.is_file() else sorted(base.glob(glob))
    if not paths:
        return found, False
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in regex.finditer(text):
            found.add(m.group(1) or m.group(2))
    return found, True


def load_queue():
    if not QUEUE_FILE.exists():
        return {}
    try:
        raw = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        return {e["method"]: e for e in raw
                if isinstance(e, dict) and e.get("method")}
    except Exception:
        return {}


def witness_methods():
    """Methods the frozen witnesses exercise; they must be canonized."""
    out = set()
    try:
        from tools.golden_qcos import SEQUENCE
        out |= {m for m, _ in SEQUENCE}
    except Exception:
        pass
    corpus = ROOT / "tests" / "corpus" / "requests.jsonl"
    if corpus.exists():
        for line in corpus.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.add(json.loads(line).get("method", "?"))
            except json.JSONDecodeError:
                continue
    return out


# ------------------------------------------------------------------- gate
def collect(root: Path = ROOT, today: str = None):
    root = Path(root)
    canon_path = root / "qcos.cxn"
    src = root / "core" / "src"
    rep = {"schema_version": SCHEMA_VERSION, "gate": "canon_lint",
           "env": "ok", "canon": 0, "tongues": {}, "dangling": [],
           "queue": [], "expired": [], "bridge_missing": [],
           "coverage_warn": [], "witness_uncanonized": [],
           "errors": [], "warnings": []}
    if not canon_path.exists():
        rep["env"] = "missing-canon"
        rep["errors"].append("qcos.cxn missing; gate cannot run (fail closed)")
        return rep
    if not src.exists():
        rep["env"] = "missing-core"
        rep["errors"].append("core/src missing; gate cannot run (fail closed)")
        return rep

    canon = parse_canon(canon_path.read_text(encoding="utf-8"))
    rep["canon"] = len(canon)
    today = today or date.today().isoformat()
    queue = load_queue() if root == ROOT else {}

    tongues = {}
    for name, base, glob, regex, severity in TONGUES:
        base = root / base.relative_to(ROOT) if str(base).startswith(str(ROOT)) else base
        found, present = scan_tongue(base, glob, regex)
        tongues[name] = {"present": present, "bound": len(found & canon),
                         "extra": sorted(found - canon)}
        missing = canon - found
        if not present:
            rep["warnings"].append(f"tongue '{name}' absent; coverage unchecked")
            continue
        if severity == "error":
            if name == "cpp":
                rep["dangling"] = sorted(missing)
                rep["errors"] += [f"canon method '{m}' has no C++ Registrar "
                                  f"(dangling binding)" for m in rep["dangling"]]
            else:
                rep["bridge_missing"] = sorted(missing)
                rep["errors"] += [f"canon method '{m}' unreachable from the JS "
                                  f"ruler (A6)" for m in rep["bridge_missing"]]
        else:
            for m in sorted(missing):
                rep["coverage_warn"].append(f"{name}:{m}")
                rep["warnings"].append(f"tongue '{name}' lacks binding for {m}")
        for x in tongues[name]["extra"]:
            rep["warnings"].append(f"{name} binds '{x}' outside its own file scope")
    rep["tongues"] = tongues

    # priced canonization queue (A5): hypotheses expire
    impl = tongues.get("cpp", {}).get("bound", 0)
    cpp_extra = set()
    for name, base, glob, regex, _sev in TONGUES:
        if name == "cpp":
            found, _ = scan_tongue(base, glob, regex)
            cpp_extra = found - canon
    for m in sorted(cpp_extra):
        e = queue.get(m)
        if e and e.get("until") and e["until"] < today:
            rep["expired"].append(m)
            rep["errors"].append(f"canonization of '{m}' expired on {e['until']}; "
                                 f"canonize it or re-price it in writing")
        else:
            rep["queue"].append(m)
            rep["warnings"].append(
                f"'{m}' implemented but not canonized (hypothesis"
                + (f", until {e['until']}" if e and e.get('until') else "")
                + ")")

    # cross-gate: witnesses may only exercise canonized methods
    for m in sorted(witness_methods() - canon):
        rep["witness_uncanonized"].append(m)
        rep["errors"].append(f"witness corpus exercises '{m}' which the canon "
                             f"does not declare")
    return rep


def receipt(rep, strict=False):
    try:
        from tools.ledger import append
        append({"gate": "canon_lint", "schema_version": SCHEMA_VERSION,
                "status": "pass" if not rep["errors"] else "fail",
                "canon": rep["canon"], "dangling": len(rep["dangling"]),
                "bridge_missing": len(rep["bridge_missing"]),
                "queue": len(rep["queue"]), "expired": len(rep["expired"]),
                "env": rep["env"]})
    except Exception:
        pass


# --------------------------------------------------------------- selftest
_STUB_CANON = """@method qcos.boot
@method qcos.read
@method papers.script
"""
_STUB_CPP = """#include "api.hpp"
void bind() {
  Registrar qcos_boot("qcos.boot", [](const Json& a) { return Json(); });
  Registrar qcos_read("qcos.read", [](const Json& a) { return Json(); });
}
"""
_STUB_JS = """const M = {
  "qcos.boot": (a) => ({}),
  "qcos.read": (a) => ({}),
  "papers.script": (a) => ({}),
};
"""


def selftest():
    import tempfile
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "core" / "src").mkdir(parents=True)
        (root / "tools").mkdir(parents=True)
        want("env-missing-canon", collect(root)["env"] == "missing-canon")
        (root / "qcos.cxn").write_text(_STUB_CANON, encoding="utf-8")
        want("env-missing-core", collect(root)["env"] == "missing-core")
        (root / "core" / "src" / "api.cpp").write_text(_STUB_CPP, encoding="utf-8")
        (root / "tools" / "ref_bridge.js").write_text(_STUB_JS, encoding="utf-8")
        rep = collect(root)
        want("dangling-found", rep["dangling"] == ["papers.script"], str(rep["dangling"]))
        want("bridge-complete", rep["bridge_missing"] == [])
        want("errors-raised", len(rep["errors"]) >= 1)
        want("parse-canon", parse_canon(_STUB_CANON) ==
             {"qcos.boot", "qcos.read", "papers.script"})
        found, present = scan_tongue(root / "core" / "src", "*.cpp", TONGUES[0][3])
        want("scan-cpp", found == {"qcos.boot", "qcos.read"} and present)
    return checks


# -------------------------------------------------------------------- CLI
def main():
    as_json = "--json" in sys.argv
    strict = "--strict" in sys.argv
    if "--selftest" in sys.argv:
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    rep = collect()
    if rep["env"] != "ok":
        print(f"[canon] ENVIRONMENT failure: {rep['env']}")
        for e in rep["errors"]:
            print(f"  - {e}")
        receipt(rep)
        return 2
    for w in rep["warnings"]:
        print(f"[canon] WARN {w}")
    for e in rep["errors"]:
        print(f"[canon] ERROR {e}")
    print(f"[canon] canon={rep['canon']} dangling={len(rep['dangling'])} "
          f"bridge_missing={len(rep['bridge_missing'])} queue={len(rep['queue'])} "
          f"expired={len(rep['expired'])} "
          f"tongues={{{', '.join(f'{k}:{v['bound']}' for k, v in rep['tongues'].items())}}}")
    if as_json:
        print(json.dumps(rep, ensure_ascii=False))
    if "--github-summary" in sys.argv and os.environ.get("GITHUB_STEP_SUMMARY"):
        md = ["## 📜 Canon parity (gen-3)", "",
              f"- canon methods: {rep['canon']}",
              f"- tongues: " + ", ".join(f"{k}={v['bound']}"
                                          for k, v in rep["tongues"].items()),
              f"- ❌ dangling: {rep['dangling'] or 'none'}",
              f"- ❌ bridge-missing: {rep['bridge_missing'] or 'none'}",
              f"-  queue: {rep['queue'] or 'none'} (expired: {rep['expired'] or 'none'})",
              "" if rep["errors"] else "- ✅ canon parity holds"]
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
    receipt(rep, strict)
    if strict and rep["warnings"]:
        return 1
    return 1 if rep["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
