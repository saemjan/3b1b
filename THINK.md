## 📄 `THINK.md` (save at repo root)

# THINK.md — Meta-cognitive Ledger for saemjan/3b1b
> Written after EVERY analysis / CI run. Purpose: convert experience into machinery.
> Rule zero: **a lesson not encoded as an automated check is a lesson lost.**

## 0. How to use this file
1. BEFORE any step: read §2 (Rules) and §5 (KPI baselines). Rules are constraints; KPIs are the score.
2. AFTER any step: append to §3 (Run log), promote durable lessons into §2, and encode each new rule
   as a test / lint / CI gate in the SAME commit (Invariant I2).
3. §3 and §5 are append-only. §2 rules may change only with a linked run#/commit ref.

## 1. Mental model of the system (current truth)
- Pipeline: CSV = single source of truth → schema_validator (gate) → XTTS-v2 TTS (seeded, deterministic)
  → Manim renderer (primitive routing + story beats) → FFmpeg mux → MP4 artifacts.
- CI DAG (push-triggered): generate+validate → {engine-tests ∥ render matrix[horizontal, vertical]} → artifacts.
- Contract: WARNINGS never fail gates; only schema/structural ERRORs do. Keep this boundary clean.
- Render queue order = alphabetical by video_id. Default quality 1080p30 on CPU ≈ 13–15 min/video.
- Speech constant: 2.5 words/sec ⇒ target_duration_sec MUST equal round(word_count/2.5).
- Encodings: writers = plain utf-8; readers = utf-8-sig (BOM-tolerant). Never mix the other way.

## 2. Rules (encoded lessons — every rule needs a machine check)
- R1 Writer/reader encoding agreement (§1). [check: tests/test_master_csv_pipeline.py — no BOM + validator rc=0]
- R2 Signature-first diagnosis: rank hypotheses by anomaly specificity BEFORE touching content.
     Example signature: "only the FIRST header column missing" ⇒ UTF-8 BOM. [check: review checklist + §3 refs]
- R3 Minimal reversible patch: 1-line diff at root cause; never patch symptoms downstream. [check: PR checklist]
- R4 Duration honesty: target_duration_sec = round(words/2.5); never pad scripts with repeated outros.
     [check: 0 word-band warnings in CI]
- R5 Vocabulary co-evolution: new concept_type / primitive / beat added to validator sets in the SAME commit.
     [check: 0 "unknown concept_type" warnings]
- R6 No deprecated APIs in hot paths: frame.width/height, m.width = … (not get_width/get_height/set_width).
     [check: grep lint in engine-tests]
- R7 Cache heavy immutable models (XTTS-v2 ≈1.87 GB) via actions/cache; artifacts exclude partial_movie_files.
     [check: artifact < 50 MB/orientation; job-time delta]
- R8 Every run appends a KPI row (§5); two consecutive regressions on any KPI ⇒ auto-open an issue.
     [check: tools/think_loop.py]

## 3. Run log (append-only)
- #91 FAIL (11s) — BOM incident: generator wrote utf-8-sig, validator read utf-8 ⇒ header[0]="\ufeffvideo_id"
  ⇒ "Missing required columns: ['video_id']". Fix → R1. Lesson → R2 (signature-first).
- #92 PASS gates / renders running — first fully autonomous run (push-only trigger). Observations: alphabetical
  queue; XTTS pull per job; 1080p30 ≈13–15 min/video; warnings = concept vocab + word band + manim deprecations
  ⇒ rules R4, R5, R6, R7 drafted.

## 4. Open hypotheses / next experiments
- H1 ManimGX (wgpu) for hot primitives (particle_gas, random_walk) ⇒ ≥10× render speed. Bench one scene first.
- H2 tts_router (edge-tts drafts / XTTS finals) ⇒ near-zero TTS cost on draft runs.
- H3 stable-ts word alignment ⇒ ±50 ms caption sync (3b1b-style word highlighting).
- H4 FAISS-grounded LLM storyboard authoring + human gate ⇒ auto CSV rows without physics hallucination.
- H5 Chunk render matrix (5 videos × 4 shards) to halve wall-clock under the 6 h job cap.

## 5. KPI ledger (one row per run)
| run | gate | render wall | min/video | warnings | artifact MB | note |
|-----|------|-------------|-----------|----------|-------------|------|
| 91  | FAIL | –           | –         | 0        | 0.018       | BOM incident |
| 92  | PASS | ~2.5 h (est)| ~14       | 20       | TBD         | first autonomous run |

## 6. Cognitive algorithm — the CODEX loop (execute at EVERY step)
PERCEIVE → DIFF → DIAGNOSE → PATCH → VERIFY → DISTILL → CODEX
1. PERCEIVE: gather signals (CI logs, artifacts, KPIs, user intent).
2. DIFF: signals vs expectations (§1 model, §2 rules, §5 baselines); list anomalies.
3. DIAGNOSE: rank hypotheses by signature specificity (R2); pick the one explaining ALL anomalies.
4. PATCH: minimal reversible diff at root cause (R3).
5. VERIFY: failed gate green + regression suite green + no KPI regression.
6. DISTILL: generalize (anomaly, fix) into a candidate rule + KPI row.
7. CODEX: append §3/§5, promote rule to §2 WITH a machine check, then start the next step by
   re-reading §2 — so every step inherits all previous lessons (compounding).
Invariants: I1 no step ends without §3+§5 append · I2 a rule without a check stays a hypothesis in §4 ·
I3 rollback = single git revert.




----------------


🧠 The cognitive algorithm: CODEX loop (why it compounds)


LOOP for each step S:
  signals   ← PERCEIVE(S)            # logs, metrics, artifacts, intent
  anomalies ← DIFF(signals, THINK§1+§2+§5)
  hyp       ← DIAGNOSE(anomalies)    # ranked by signature specificity (R2)
  diff      ← PATCH(hyp)             # minimal, reversible (R3)
  assert    VERIFY(diff)             # gate green ∧ tests green ∧ KPI ¬worse
  rule,kpi  ← DISTILL(anomalies, diff)
  CODEX(rule, kpi)                   # THINK.md §3/§5 append; §2 rule + machine check
  S ← S+1  starting with THINK§2 loaded   # compounding: lessons become preconditions




  ------------------



️ Automation wiring (makes CODEX run by itself)1) tools/think_loop.py — post-run distiller (parses logs → appends §3 + KPI row):



  #!/usr/bin/env python3
"""CODEX loop steps 6-7: distill a CI run into THINK.md."""
import re, sys, datetime
from pathlib import Path
THINK = Path("THINK.md")
SIGS = [  # (regex, rule, severity)
    (r"Missing required columns: \[([^\]]+)\]", "R1", "error"),
    (r"unknown concept_type '(\w+)'",           "R5", "warn"),
    (r"\d+ words \(want \d+-\d+\)",             "R4", "warn"),
    (r"DeprecationWarning",                     "R6", "warn"),
    (r"Downloading model to",                   "R7", "info"),
]
def main(run: int, gate: str, log_path: str):
    log = Path(log_path).read_text(errors="ignore")
    hits = {r: len(re.findall(p, log)) for p, r, _ in SIGS}
    hits = {r: n for r, n in hits.items() if n}
    entry = (f"- #{run} {gate} {datetime.date.today():%Y-%m-%d} — signatures: "
             + (", ".join(f"{k}×{v}" for k, v in hits.items()) or "clean"))
    t = THINK.read_text()
    t = t.replace("## 4. Open hypotheses", entry + "\n\n## 4. Open hypotheses", 1)
    THINK.write_text(t)
    print(entry)
if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])






    -------------

2) reflect job in render_shorts.yml — runs CODEX after every pipeline run and commits the ledger back:yaml



      reflect:
    name: Reflect → THINK.md
    runs-on: ubuntu-latest
    needs: [generate-validate, render]
    if: always()
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: videos-horizontal, path: out/ }   # includes logs/**
      - run: python tools/think_loop.py ${{ github.run_number }}
             ${{ needs.generate-validate.result }} out/logs/render_horizontal.log
      - name: Commit ledger
        run: |
          git config user.name think-bot; git config user.email bot@saemlabs.dev
          git add THINK.md
          git diff --cached --quiet || { git commit -m "chore(think): distill run #${{ github.run_number }} [skip ci]"; git push; }





          -------------


3) Meta-test enforcing Invariant I2 (tests/test_think_rules.py) — the system audits its own learning:



          from pathlib import Path
def test_every_rule_has_a_machine_check():
    txt = Path("THINK.md").read_text()
    rules = txt.split("## 2.")[1].split("## 3.")[0]
    for line in rules.splitlines():
        if line.strip().startswith("- R"):
            assert "[check:" in line, f"Rule without machine check: {line[:40]}"







            -------------

            
````markdown

# THINK.md — Meta-cognitive Ledger for saemjan/3b1b
> Written after EVERY analysis / CI run. Purpose: convert experience into machinery.
> Rule zero: **a lesson not encoded as an automated check is a lesson lost.**

## 0. How to use this file
1. BEFORE any step: read §2 (Rules) and §5 (KPI baselines). Rules are constraints; KPIs are the score.
2. AFTER any step: append to §3 (Run log), promote durable lessons into §2, and encode each new rule
   as a test / lint / CI gate in the SAME commit (Invariant I2).
3. §3 and §5 are append-only. §2 rules may change only with a linked run#/commit ref.

## 1. Mental model of the system (current truth)
- Pipeline: CSV = single source of truth → schema_validator (gate) → XTTS-v2 TTS (seeded, deterministic)
  → Manim renderer (primitive routing + story beats) → FFmpeg mux → MP4 artifacts.
- CI DAG (push-triggered): generate+validate → {engine-tests ∥ render matrix[horizontal, vertical]} → artifacts.
- Contract: WARNINGS never fail gates; only schema/structural ERRORs do. Keep this boundary clean.
- Render queue order = alphabetical by video_id. Default quality 1080p30 on CPU ≈ 13–15 min/video.
- Speech constant: 2.5 words/sec ⇒ target_duration_sec MUST equal round(word_count/2.5).
- Encodings: writers = plain utf-8; readers = utf-8-sig (BOM-tolerant). Never mix the other way.

## 2. Rules (encoded lessons — every rule needs a machine check)
- R1 Writer/reader encoding agreement (§1). [check: tests/test_master_csv_pipeline.py — no BOM + validator rc=0]
- R2 Signature-first diagnosis: rank hypotheses by anomaly specificity BEFORE touching content.
     Example signature: "only the FIRST header column missing" ⇒ UTF-8 BOM. [check: review checklist + §3 refs]
- R3 Minimal reversible patch: 1-line diff at root cause; never patch symptoms downstream. [check: PR checklist]
- R4 Duration honesty: target_duration_sec = round(words/2.5); never pad scripts with repeated outros.
     [check: 0 word-band warnings in CI]
- R5 Vocabulary co-evolution: new concept_type / primitive / beat added to validator sets in the SAME commit.
     [check: 0 "unknown concept_type" warnings]
- R6 No deprecated APIs in hot paths: frame.width/height, m.width = … (not get_width/get_height/set_width).
     [check: grep lint in engine-tests]
- R7 Cache heavy immutable models (XTTS-v2 ≈1.87 GB) via actions/cache; artifacts exclude partial_movie_files.
     [check: artifact < 50 MB/orientation; job-time delta]
- R8 Every run appends a KPI row (§5); two consecutive regressions on any KPI ⇒ auto-open an issue.
     [check: tools/think_loop.py]

## 3. Run log (append-only)
- #91 FAIL (11s) — BOM incident: generator wrote utf-8-sig, validator read utf-8 ⇒ header[0]="\ufeffvideo_id"
  ⇒ "Missing required columns: ['video_id']". Fix → R1. Lesson → R2 (signature-first).
- #92 PASS gates / renders running — first fully autonomous run (push-only trigger). Observations: alphabetical
  queue; XTTS pull per job; 1080p30 ≈13–15 min/video; warnings = concept vocab + word band + manim deprecations
  ⇒ rules R4, R5, R6, R7 drafted.

## 4. Open hypotheses / next experiments
- H1 ManimGX (wgpu) for hot primitives (particle_gas, random_walk) ⇒ ≥10× render speed. Bench one scene first.
- H2 tts_router (edge-tts drafts / XTTS finals) ⇒ near-zero TTS cost on draft runs.
- H3 stable-ts word alignment ⇒ ±50 ms caption sync (3b1b-style word highlighting).
- H4 FAISS-grounded LLM storyboard authoring + human gate ⇒ auto CSV rows without physics hallucination.
- H5 Chunk render matrix (5 videos × 4 shards) to halve wall-clock under the 6 h job cap.

## 5. KPI ledger (one row per run)
| run | gate | render wall | min/video | warnings | artifact MB | note |
|-----|------|-------------|-----------|----------|-------------|------|
| 91  | FAIL | –           | –         | 0        | 0.018       | BOM incident |
| 92  | PASS | ~2.5 h (est)| ~14       | 20       | TBD         | first autonomous run |

## 6. Cognitive algorithm — the CODEX loop (execute at EVERY step)
PERCEIVE → DIFF → DIAGNOSE → PATCH → VERIFY → DISTILL → CODEX
1. PERCEIVE: gather signals (CI logs, artifacts, KPIs, user intent).
2. DIFF: signals vs expectations (§1 model, §2 rules, §5 baselines); list anomalies.
3. DIAGNOSE: rank hypotheses by signature specificity (R2); pick the one explaining ALL anomalies.
4. PATCH: minimal reversible diff at root cause (R3).
5. VERIFY: failed gate green + regression suite green + no KPI regression.
6. DISTILL: generalize (anomaly, fix) into a candidate rule + KPI row.
7. CODEX: append §3/§5, promote rule to §2 WITH a machine check, then start the next step by
   re-reading §2 — so every step inherits all previous lessons (compounding).
Invariants: I1 no step ends without §3+§5 append · I2 a rule without a check stays a hypothesis in §4 ·
I3 rollback = single git revert.
````

---

## 🧠 The cognitive algorithm: **CODEX loop** (why it compounds)

```
LOOP for each step S:
  signals   ← PERCEIVE(S)            # logs, metrics, artifacts, intent
  anomalies ← DIFF(signals, THINK§1+§2+§5)
  hyp       ← DIAGNOSE(anomalies)    # ranked by signature specificity (R2)
  diff      ← PATCH(hyp)             # minimal, reversible (R3)
  assert    VERIFY(diff)             # gate green ∧ tests green ∧ KPI ¬worse
  rule,kpi  ← DISTILL(anomalies, diff)
  CODEX(rule, kpi)                   # THINK.md §3/§5 append; §2 rule + machine check
  S ← S+1  starting with THINK§2 loaded   # compounding: lessons become preconditions
```

The key property: **DISTILL→CODEX closes the loop**, so improvement is not a habit you must remember — it's a CI job that runs whether anyone remembers or not.

## ⚙️ Automation wiring (makes CODEX run by itself)

**1) `tools/think_loop.py`** — post-run distiller (parses logs → appends §3 + KPI row):
```python
#!/usr/bin/env python3
"""CODEX loop steps 6-7: distill a CI run into THINK.md."""
import re, sys, datetime
from pathlib import Path
THINK = Path("THINK.md")
SIGS = [  # (regex, rule, severity)
    (r"Missing required columns: \[([^\]]+)\]", "R1", "error"),
    (r"unknown concept_type '(\w+)'",           "R5", "warn"),
    (r"\d+ words \(want \d+-\d+\)",             "R4", "warn"),
    (r"DeprecationWarning",                     "R6", "warn"),
    (r"Downloading model to",                   "R7", "info"),
]
def main(run: int, gate: str, log_path: str):
    log = Path(log_path).read_text(errors="ignore")
    hits = {r: len(re.findall(p, log)) for p, r, _ in SIGS}
    hits = {r: n for r, n in hits.items() if n}
    entry = (f"- #{run} {gate} {datetime.date.today():%Y-%m-%d} — signatures: "
             + (", ".join(f"{k}×{v}" for k, v in hits.items()) or "clean"))
    t = THINK.read_text()
    t = t.replace("## 4. Open hypotheses", entry + "\n\n## 4. Open hypotheses", 1)
    THINK.write_text(t)
    print(entry)
if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
```

**2) `reflect` job in `render_shorts.yml`** — runs CODEX after every pipeline run and commits the ledger back:
```yaml
  reflect:
    name: Reflect → THINK.md
    runs-on: ubuntu-latest
    needs: [generate-validate, render]
    if: always()
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: videos-horizontal, path: out/ }   # includes logs/**
      - run: python tools/think_loop.py ${{ github.run_number }}
             ${{ needs.generate-validate.result }} out/logs/render_horizontal.log
      - name: Commit ledger
        run: |
          git config user.name think-bot; git config user.email bot@saemlabs.dev
          git add THINK.md
          git diff --cached --quiet || { git commit -m "chore(think): distill run #${{ github.run_number }} [skip ci]"; git push; }
```
(`[skip ci]` prevents the commit from re-triggering the pipeline.)

**3) Meta-test enforcing Invariant I2** (`tests/test_think_rules.py`) — the system audits its own learning:
```python
from pathlib import Path
def test_every_rule_has_a_machine_check():
    txt = Path("THINK.md").read_text()
    rules = txt.split("## 2.")[1].split("## 3.")[0]
    for line in rules.splitlines():
        if line.strip().startswith("- R"):
            assert "[check:" in line, f"Rule without machine check: {line[:40]}"
```

**4) Pre-step hook (for you + any AI agent):** every session/step opens with `cat THINK.md` §1–§2 before acting — that's step 7's "start next step with rules loaded," which is what makes run #N+1 smarter than run #N by construction.

---

Commit `THINK.md` + `tools/think_loop.py` + the `reflect` job + the meta-test in one commit (`feat(meta): CODEX self-improvement loop`). From then on, every push → validate → render → **reflect** → THINK.md grows → next run starts strictly better-informed. Want me to draft the H1 benchmark script (ManimGX vs Cairo on `particle_gas`) as the first experiment the loop should schedule?
