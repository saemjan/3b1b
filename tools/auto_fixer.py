#!/usr/bin/env python3
"""
Saem Auto-Fixer — pattern-matching + evidence-accumulation bot.
Runs after a failed Build Core job. Uses the same Beta-evidence
discipline as the cognitive core.
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "knowledge" / "fixer_cases.jsonl"
RULES  = ROOT / "knowledge" / "fixer_rules.json"

# ---------- known signatures (the ones we already fixed) ----------
DEFAULT_RULES = [
    {
        "id": "hash32_ambiguous",
        "sig": r"call of overloaded 'hash32\(const std::string&\)' is ambiguous",
        "file": "core/src/api.cpp",
        "action": "delete_local_hash32",
        "alpha": 3, "beta": 0,
        "hint": "Remove the local hash32 definition; keep only the one in util.hpp"
    },
    {
        "id": "is_digit_u32",
        "sig": r"cannot convert 'saem::u32'.*to 'char32_t'",
        "file": "core/src/cos_api.cpp",
        "action": "fix_yearFromHeader",
        "alpha": 2, "beta": 0,
        "hint": "Pass char32_t, not u32, to is_digit"
    },
    {
        "id": "apply_vs_std_apply",
        "sig": r"incomplete type 'std::tuple_size<saem::Gate>'",
        "file": "core/src/rev.hpp",
        "action": "qualify_apply",
        "alpha": 1, "beta": 0,
        "hint": "Change apply(...) to saem::apply(...) to avoid collision with std::apply"
    },
    {
        "id": "missing_core_methods",
        "sig": r"core\.methods|BLIND -- speaks no methods",
        "file": "core/src/api.cpp",
        "action": "add_core_methods",
        "alpha": 4, "beta": 0,
        "hint": "Register core.methods Registrar"
    },
    {
        "id": "api_registry_g",
        "sig": r"'Registrar' does not name a type",
        "file": "core/src/api_registry.g.cpp",
        "action": "delete_file",
        "alpha": 2, "beta": 0,
        "hint": "Delete the broken generated fragment"
    },
]

def load_rules():
    if RULES.exists():
        return json.loads(RULES.read_text())
    return DEFAULT_RULES

def save_rules(rules):
    RULES.parent.mkdir(parents=True, exist_ok=True)
    RULES.write_text(json.dumps(rules, indent=2))

def posterior(rule):
    a, b = rule["alpha"], rule["beta"]
    return a / (a + b) if (a + b) > 0 else 0.5

def diagnose(log: str, rules):
    matches = []
    for r in rules:
        if re.search(r["sig"], log, re.I | re.M):
            matches.append((posterior(r), r))
    matches.sort(key=lambda x: -x[0])
    return matches

def propose_patch(rule):
    """Return a human-readable suggestion. Later this can emit a real diff."""
    actions = {
        "delete_local_hash32": (
            "In core/src/api.cpp delete the local function:\n"
            "  uint32_t hash32(const std::string& s) { ... }\n"
            "Keep only the definition in util.hpp."
        ),
        "fix_yearFromHeader": (
            "In cos_api.cpp text.yearFromHeader replace\n"
            "  is_digit(u32(1, char32_t(s[i])))\n"
            "with\n"
            "  is_digit(static_cast<char32_t>(static_cast<unsigned char>(s[i])))"
        ),
        "qualify_apply": (
            "In core/src/rev.hpp line \~50 change\n"
            "  apply(b, gcnot(out, dest));\n"
            "to\n"
            "  saem::apply(b, gcnot(out, dest));"
        ),
        "add_core_methods": (
            "Add to api.cpp (or cos_api.cpp):\n"
            '  const Registrar c0("core.methods", [](const Json&){\n'
            "    Json o = Json::array();\n"
            "    for (const auto& m : saem::methods()) o.push(Json(m));\n"
            "    return o;\n"
            "  });"
        ),
        "delete_file": f"Delete the broken file {rule.get('file')}",
    }
    return actions.get(rule["action"], rule.get("hint", "No concrete patch yet"))

def update_evidence(rules, rule_id, accepted: bool):
    for r in rules:
        if r["id"] == rule_id:
            if accepted:
                r["alpha"] += 1
            else:
                r["beta"] += 1
            break
    save_rules(rules)

def main():
    if len(sys.argv) < 2:
        print("usage: auto_fixer.py <compile_log.txt> [--accept ID] [--reject ID]")
        return 1

    log = Path(sys.argv[1]).read_text(errors="replace")
    rules = load_rules()

    if "--accept" in sys.argv:
        idx = sys.argv.index("--accept")
        update_evidence(rules, sys.argv[idx+1], True)
        print(f"[fixer] accepted {sys.argv[idx+1]}")
        return 0
    if "--reject" in sys.argv:
        idx = sys.argv.index("--reject")
        update_evidence(rules, sys.argv[idx+1], False)
        print(f"[fixer] rejected {sys.argv[idx+1]}")
        return 0

    ranked = diagnose(log, rules)
    if not ranked:
        print("[fixer] no known pattern matched")
        return 0

    print("=== Saem Auto-Fixer diagnosis ===")
    for score, r in ranked[:3]:
        print(f"\n[{r['id']}] posterior={score:.3f}  α={r['alpha']} β={r['beta']}")
        print(propose_patch(r))

    # append to ledger
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({
            "top": ranked[0][1]["id"],
            "score": ranked[0][0],
            "log_hash": hash(log) & 0xFFFFFFFF
        }) + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
