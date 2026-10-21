#!/usr/bin/env python3
"""Meta-tests for the THINK.md cognitive operating system (CODEX guardrails).

Enforces:
  I1  every run leaves a §3 log entry + §5 KPI row      (structural + functional checks)
  I2  every §2 rule carries a [check: …] marker pointing at a REAL artifact
  I3  rollback = single revert                           (policy; not testable here)
Plus direct code-level truth for landed rules (R1, R9, R11), visible debt
via non-strict xfail (R6), and a functional test of tools/think_loop.py.

Stdlib + pytest only. No network.   Run: pytest tests/test_think_rules.py -q
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THINK = ROOT / "THINK.md"

RULE_RE = re.compile(r"^-\s+(R\d+)\b(?P<body>.*)$")
MARKER_RE = re.compile(r"\[check:\s*(?P<check>[^\]]+)\]")
PATH_RE = re.compile(r"((?:tests|tools|\.github)/[A-Za-z0-9_./-]+)")


@pytest.fixture(scope="module")
def think_text() -> str:
    assert THINK.exists(), "THINK.md missing at repo root — ledger not committed (I1/I2)"
    return THINK.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def section2(think_text: str) -> str:
    return think_text.split("## 2.", 1)[1].split("## 3.", 1)[0]


@pytest.fixture(scope="module")
def rules(section2: str) -> dict:
    out = {}
    for ln in section2.splitlines():
        m = RULE_RE.match(ln.strip())
        if m:
            out[m.group(1)] = m.group("body")
    return out


# ───────────────────────── I2: rule markers ─────────────────────────
def test_every_rule_has_check_marker(rules):
    missing = [rid for rid, body in rules.items() if "[check:" not in body]
    assert not missing, f"rules without [check:] marker (I2 violation): {missing}"


def test_rule_ids_unique_and_ascending(rules):
    ids = [int(r[1:]) for r in rules]
    assert len(ids) == len(set(ids)), "duplicate rule ids in §2"
    assert ids == sorted(ids), "rule ids must ascend — rules are append-only"


def test_check_markers_point_at_real_artifacts(rules):
    """A marker naming a file that doesn't exist = a rule with no real check."""
    dangling = []
    for rid, body in rules.items():
        m = MARKER_RE.search(body)
        assert m, f"{rid}: malformed [check:] marker"
        for p in PATH_RE.findall(m.group("check")):
            if not (ROOT / p).exists():
                dangling.append(f"{rid} → {p}")
    assert not dangling, (
        "checks referencing missing artifacts — land them or fix the marker: "
        + "; ".join(dangling))


# ─────────────────── ledger structure (I1 scaffolding) ───────────────────
def test_required_sections_present_and_ordered(think_text):
    heads = ["## 0.", "## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7."]
    pos = [think_text.find(h) for h in heads]
    assert all(p >= 0 for p in pos), f"missing sections: {[h for h, p in zip(heads, pos) if p < 0]}"
    assert pos == sorted(pos), "THINK.md sections out of order"


def test_run_log_not_empty(think_text):
    log = think_text.split("## 3.", 1)[1].split("## 4.", 1)[0]
    assert re.search(r"^-\s+#\d+", log, re.M), "§3 run log has no entries (I1)"


def test_kpi_table_well_formed(think_text):
    kpi = think_text.split("## 5.", 1)[1].split("## 6.", 1)[0]
    rows = [ln for ln in kpi.splitlines() if ln.strip().startswith("|")]
    assert len(rows) >= 3, "KPI ledger needs header + separator + ≥1 data row"
    ncols = rows[0].count("|")
    assert all(r.count("|") == ncols for r in rows), "KPI row column-count drift"


def test_codex_loop_and_invariants_intact(think_text):
    s6 = think_text.split("## 6.", 1)[1]
    for token in ["PERCEIVE", "DIFF", "DIAGNOSE", "PATCH", "VERIFY",
                  "DISTILL", "CODEX", "I1", "I2", "I3"]:
        assert token in s6, f"§6 lost '{token}' — cognitive algorithm mutated"


# ───────────── direct code truth for LANDED rules ─────────────
def test_r1_encoding_contract():
    gen = (ROOT / "tools/generate_universal_master_csvs.py").read_text(encoding="utf-8")
    val = (ROOT / "schema_validator.py").read_text(encoding="utf-8")
    assert "utf-8-sig" not in gen, "R1: generator must write plain utf-8"
    assert "utf-8-sig" in val, "R1: validator must read BOM-tolerant utf-8-sig"


def test_r9_render_is_opt_in():
    wf = (ROOT / ".github/workflows/render_shorts.yml").read_text(encoding="utf-8")
    assert "outputs.render == 'true'" in wf, "R9: render job must sit behind the intent gate"
    assert "workflow_dispatch" in wf and "render_videos" in wf, "R9: manual opt-in input missing"


def test_r11_all_workflows_parse():
    yaml = pytest.importorskip("yaml")
    for wf in sorted((ROOT / ".github/workflows").glob("*.yml")):
        yaml.safe_load(wf.read_text(encoding="utf-8"))  # would have caught the L148 flow-mapping bug


# ───────────── known debt: visible, never hidden ─────────────
@pytest.mark.xfail(strict=False,
                   reason="R6 debt: manim deprecations at render_universal.py:601-603 pending patch")
def test_r6_no_deprecated_manim_calls():
    src = (ROOT / "render_universal.py").read_text(encoding="utf-8")
    bad = set(re.findall(r"\b(get_width|get_height|set_width)\(", src))
    assert not bad, f"R6: deprecated manim calls remain: {bad}"


# ───────────── functional: the distiller itself (CODEX 6-7) ─────────────
def test_think_loop_distills_signatures(tmp_path):
    think_copy = tmp_path / "THINK.md"
    think_copy.write_text(THINK.read_text(encoding="utf-8"))
    log = tmp_path / "run.log"
    log.write_text(
        "[WARN] Row 2 (x): unknown concept_type 'MECHANICS'\n"
        "[WARN] Row 2 (x): 259 words (want 337-540).\n"
        "DeprecationWarning: get_width\n"
        "Done in 107.3 min — 10 ok, 0 failed, 0 skipped\n")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/think_loop.py"), "999", "PASS", str(log)],
        cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = think_copy.read_text(encoding="utf-8")
    assert "- #999 PASS" in out, "think_loop did not append a §3 entry"
    entry_line = out.split("- #999", 1)[1].splitlines()[0]
    for sig in ("R5", "R4", "R6"):
        assert sig in entry_line, f"signature {sig} not distilled into the entry"
    assert out.index("- #999") < out.index("## 4."), "entry must land inside §3 (before §4)"
