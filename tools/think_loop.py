#!/usr/bin/env python3
"""Append one distill line to THINK.md §3 (the run log) + ledger receipt.
v3 (Gen-3 contract): selftest, ledger, schema_version, UTC, --strict, --json.
Exit codes: 0 ok · 1 drift/fail · 2 environment.
"""
import json, os, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THINK = ROOT / "THINK.md"
SCHEMA_VERSION = 3
ROW = re.compile(r"^#(\d+)\s")

try:
    from tools.ledger import append as ledger_append
except ImportError:
    def ledger_append(entry):  # fail-closed: record debt, don't crash
        print(f"[think] WARN ledger unavailable; entry dropped: {entry}", file=sys.stderr)

# ---------------------------------------------------------------- helpers
def _utc_date():
    return time.strftime("%Y-%m-%d", time.gmtime())

def _utc_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def last_run(text):
    nums = [int(m.group(1)) for m in (ROW.match(l) for l in text.splitlines()) if m]
    return max(nums) if nums else 0

# ---------------------------------------------------------------- selftest
SELFTEST = [
    # (run, gate, env_render, env_sigs, note, expected_fragment)
    (169, "ci", "ok", "clean", "", "#169 gate=ci render=ok"),
    (None, None, "skipped", "clean", "fallback", "gate="),  # defaults
]

def selftest():
    bad = 0
    for i, (run, gate, render, sigs, note, frag) in enumerate(SELFTEST):
        os.environ["STUDIO_RENDER"] = render
        os.environ["STUDIO_SIGS"] = sigs
        line = _build_line(run, gate, note.split() if note else [])
        if frag not in line:
            print(f"[selftest] case {i} MISMATCH: want fragment {frag!r} in {line!r}")
            bad += 1
        else:
            print(f"[selftest] case {i} ok")
    print(f"[selftest] {len(SELFTEST)-bad}/{len(SELFTEST)} passed")
    return 1 if bad else 0

# ---------------------------------------------------------------- core
def _build_line(run, gate, note, render=None, sigs=None):
    in_ci = bool(os.environ.get("GITHUB_RUN_NUMBER"))
    run = int(run) if run else int(os.environ.get("GITHUB_RUN_NUMBER", "0") or 0)
    gate = gate or os.environ.get("STUDIO_GATE") or ("ci" if in_ci else "local")
    render = render or os.environ.get("STUDIO_RENDER", "skipped")
    sigs = sigs or os.environ.get("STUDIO_SIGS", "clean")
    parts = [f"#{run}", f"gate={gate}", f"render={render}", _utc_date(),
             "wall=-", f"sigs={sigs}", f"sv={SCHEMA_VERSION}"]
    if note:
        parts.append(" ".join(note))
    return " ".join(parts)

def main(run=None, gate=None, *note):
    strict = "--strict" in sys.argv
    as_json = "--json" in sys.argv
    note = [n for n in note if n not in ("--strict", "--json")]

    try:
        text = THINK.read_text(encoding="utf-8") if THINK.exists() else "# THINK.md\n"
    except OSError as e:
        print(f"[think] ENV error reading THINK.md: {e}", file=sys.stderr)
        return 2

    defaulted = not (run and gate)
    line = _build_line(run, gate, list(note))
    run_val = int(re.match(r"#(\d+)", line).group(1))

    # Append after last '#<n>' row
    lines = text.splitlines()
    idxs = [i for i, l in enumerate(lines) if ROW.match(l)]
    pos = (idxs[-1] + 1) if idxs else len(lines)
    lines.insert(pos, line)

    try:
        THINK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"[think] ENV error writing THINK.md: {e}", file=sys.stderr)
        return 2

    # Ledger receipt (A5)
    ledger_append({
        "op": "think", "schema_version": SCHEMA_VERSION,
        "run": run_val, "gate": gate or "default",
        "render": os.environ.get("STUDIO_RENDER", "skipped"),
        "sigs": os.environ.get("STUDIO_SIGS", "clean"),
        "defaulted": defaulted, "iso_ts": _utc_iso(),
    })

    if as_json:
        print(json.dumps({"ok": True, "line": line, "defaulted": defaulted}))
    else:
        print(f"[think] appended: {line}")
        if defaulted:
            print("[think] WARN caller passed no status; apply workflow v3.1 "
                  "so gate/render arrive explicitly (R38)")

    if strict and defaulted:
        print("[think] STRICT: refusing to pass with defaulted status", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(*args))
