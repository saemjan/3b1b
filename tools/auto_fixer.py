#!/usr/bin/env python3
"""Saem Auto-Fixer — pattern-match + Beta-evidence bot.  (Gen-3 v3)
Writes to knowledge/fixer_rules.json AND the main ledger.
Exit codes: 0 ok · 1 drift/fail · 2 environment.
"""
import json, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "knowledge" / "fixer_cases.jsonl"
RULES  = ROOT / "knowledge" / "fixer_rules.json"
SCHEMA_VERSION = 3

try:
    from tools.ledger import append as ledger_append
except ImportError:
    def ledger_append(entry):
        print(f"[fixer] WARN ledger unavailable; entry dropped", file=sys.stderr)

DEFAULT_RULES = [
    {"id":"hash32_ambiguous","sig":r"call of overloaded 'hash32\(const std::string&\)' is ambiguous",
     "file":"core/src/api.cpp","action":"delete_local_hash32","alpha":3,"beta":0,
     "hint":"Remove the local hash32 definition; keep only the one in util.hpp"},
    {"id":"is_digit_u32","sig":r"cannot convert 'saem::u32'.*to 'char32_t'",
     "file":"core/src/cos_api.cpp","action":"fix_yearFromHeader","alpha":2,"beta":0,
     "hint":"Pass char32_t, not u32, to is_digit"},
    {"id":"apply_vs_std_apply","sig":r"incomplete type 'std::tuple_size<saem::Gate>'",
     "file":"core/src/rev.hpp","action":"qualify_apply","alpha":1,"beta":0,
     "hint":"Change apply(...) to saem::apply(...) to avoid collision with std::apply"},
    {"id":"missing_core_methods","sig":r"core\.methods|BLIND -- speaks no methods",
     "file":"core/src/api.cpp","action":"add_core_methods","alpha":4,"beta":0,
     "hint":"Register core.methods Registrar"},
    {"id":"api_registry_g","sig":r"'Registrar' does not name a type",
     "file":"core/src/api_registry.g.cpp","action":"delete_file","alpha":2,"beta":0,
     "hint":"Delete the broken generated fragment"},
]

# ---------------------------------------------------------------- rules I/O
def load_rules():
    if RULES.exists():
        try:
            return json.loads(RULES.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[fixer] ENV corrupt rules file, using defaults: {e}", file=sys.stderr)
            ledger_append({"op":"fixer_rules_corrupt","schema_version":SCHEMA_VERSION})
            return list(DEFAULT_RULES)
    return list(DEFAULT_RULES)

def save_rules(rules):
    RULES.parent.mkdir(parents=True, exist_ok=True)
    RULES.write_text(json.dumps(rules, indent=2), encoding="utf-8")

# ---------------------------------------------------------------- core
def posterior(rule):
    a, b = rule["alpha"], rule["beta"]
    return a / (a + b) if (a + b) > 0 else 0.5

def diagnose(log, rules):
    matches = []
    for r in rules:
        if re.search(r["sig"], log, re.I | re.M):
            matches.append((posterior(r), r))
    matches.sort(key=lambda x: (-x[0], x[1]["id"]))  # deterministic tie-break
    return matches

def propose_patch(rule):
    actions = {
        "delete_local_hash32": "In core/src/api.cpp delete the local hash32 function.",
        "fix_yearFromHeader":  "In cos_api.cpp use static_cast<char32_t>.",
        "qualify_apply":       "In rev.hpp qualify saem::apply.",
        "add_core_methods":    'Register core.methods Registrar in api.cpp.',
        "delete_file":         f"Delete the broken file {rule.get('file')}",
    }
    return actions.get(rule["action"], rule.get("hint", "No concrete patch yet"))

def update_evidence(rules, rule_id, accepted):
    found = False
    for r in rules:
        if r["id"] == rule_id:
            if accepted: r["alpha"] += 1
            else:        r["beta"]  += 1
            found = True
            break
    if not found:
        print(f"[fixer] unknown rule id {rule_id!r}", file=sys.stderr)
        return False
    save_rules(rules)
    return True

def _receipt(op, **kw):
    kw.update({"op": op, "schema_version": SCHEMA_VERSION,
               "iso_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    ledger_append(kw)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------- selftest
SELFTEST = [
    ("hash32_ambiguous", "call of overloaded 'hash32(const std::string&)' is ambiguous", True),
    ("no_match",         "some random error text",                                        False),
]
def selftest():
    bad = 0
    rules = DEFAULT_RULES
    for i, (rid, log, expect) in enumerate(SELFTEST):
        hits = diagnose(log, rules)
        got = any(h[1]["id"] == rid for h in hits) if expect else len(hits) == 0
        if got != expect and rid != "no_match":
            # for no_match we just want zero hits
            pass
        if expect and not any(h[1]["id"] == rid for h in hits):
            print(f"[selftest] case {i} MISMATCH: expected {rid}"); bad += 1
        elif not expect and hits:
            print(f"[selftest] case {i} MISMATCH: unexpected hits"); bad += 1
        else:
            print(f"[selftest] case {i} ok")
    print(f"[selftest] {len(SELFTEST)-bad}/{len(SELFTEST)} passed")
    return 1 if bad else 0

# ---------------------------------------------------------------- main
def main():
    if "--selftest" in sys.argv:
        return selftest()
    if len(sys.argv) < 2:
        print("usage: auto_fixer.py <compile_log.txt> [--accept ID] [--reject ID]")
        return 1

    try:
        log = Path(sys.argv[1]).read_text(errors="replace")
    except FileNotFoundError:
        print(f"[fixer] ENV log file not found: {sys.argv[1]}", file=sys.stderr)
        return 2

    rules = load_rules()

    if "--accept" in sys.argv:
        rid = sys.argv[sys.argv.index("--accept") + 1]
        ok = update_evidence(rules, rid, True)
        _receipt("fixer_accept", rule=rid, ok=ok)
        print(f"[fixer] accepted {rid}" if ok else f"[fixer] accept FAILED {rid}")
        return 0 if ok else 1

    if "--reject" in sys.argv:
        rid = sys.argv[sys.argv.index("--reject") + 1]
        ok = update_evidence(rules, rid, False)
        _receipt("fixer_reject", rule=rid, ok=ok)
        print(f"[fixer] rejected {rid}" if ok else f"[fixer] reject FAILED {rid}")
        return 0 if ok else 1

    ranked = diagnose(log, rules)
    if not ranked:
        _receipt("fixer_diagnose", matched=0)
        print("[fixer] no known pattern matched")
        return 0

    print("=== Saem Auto-Fixer diagnosis ===")
    for score, r in ranked[:3]:
        print(f"\n[{r['id']}] posterior={score:.3f}  α={r['alpha']} β={r['beta']}")
        print(propose_patch(r))
    _receipt("fixer_diagnose", matched=len(ranked), top=ranked[0][1]["id"],
             score=round(ranked[0][0], 4))
    return 0

if __name__ == "__main__":
    sys.exit(main())
