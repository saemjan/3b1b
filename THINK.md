# THINK.md — Cognitive Operating System for saemjan/3b1b
> A self-improving ledger. Rule zero: **a lesson not encoded as an automated check is a lesson lost.**
> Influences: Feynman (first-principles explanation), SICP (abstraction barriers/contracts),
> GEB (strange loops — the system observes and rewrites itself), Kahneman (S1 intuition gated by S2 checks),
> Taleb (antifragility — every CI stressor must leave the system stronger).

## 0. Operating protocol (read before EVERY step)
1. Load §1 (model) + §2 (rules) + §5 (KPIs) as preconditions.
2. Execute the step via the CODEX loop (§6).
3. Append §3 (run log) + §5 (KPI row); promote durable lessons to §2 WITH a machine check (I2).
4. §3/§5 append-only. §2 changes need a run#/commit ref.

## 1. Mental model (current truth)
CSV = single source of truth → schema_validator (gate) → XTTS-v2 TTS (seeded) → Manim renderer
(primitive routing + story beats) → FFmpeg mux → MP4. CI DAG: generate+validate → {engine-tests ∥
render matrix[horizontal,vertical]} → reflect(CODEX) → artifacts. WARNINGS never fail gates; only
structural ERRORs do. Render order = alphabetical by video_id. Speech = 2.5 words/sec. Encodings:
writers utf-8, readers utf-8-sig. Trigger policy: render ONLY on explicit intent or content diff (§7).

## 2. Rules (each needs a machine check — I2)
- R1 encoding agreement (writer utf-8 / reader utf-8-sig). [tests/test_master_csv_pipeline.py]
- R2 signature-first diagnosis (rank by anomaly specificity). [review checklist + §3 refs]
- R3 minimal reversible patch at root cause. [PR template]
- R4 duration honesty: target_duration_sec = round(words/2.5). [0 word-band warnings]
- R5 vocabulary co-evolution (concept/primitive/beat sets in same commit). [0 "unknown concept_type"]
- R6 no deprecated APIs in hot paths (frame.width, m.width=…). [grep lint in engine-tests]
- R7 cache XTTS-v2 (~1.87GB); exclude partial_movie_files from artifacts. [artifact<50MB/orientation]
- R8 KPI row every run; 2 consecutive regressions ⇒ auto-issue. [tools/think_loop.py]
- R9 render is opt-in / content-gated, NEVER schema/tooling-gated. [workflow path filters + label gate]
- R10 input via interactive authoring (CLI/web), never hand-edited CSV. [tools/author.py exists + tested]

## 3. Run log (append-only)
- #91 FAIL(11s) BOM incident → R1,R2.
- #92 PASS 1h55m — first autonomous run; 10/10 both orientations; 105MB+84MB artifacts; warnings = vocab+wordband+manim deprecations → R4,R5,R6,R7. New lesson: schema-commit re-triggered full render → R9,R10.

## 4. Open hypotheses
- H1 ManimGX (wgpu) hot primitives ≥10× speed. H2 tts_router (edge drafts / XTTS finals).
- H3 stable-ts ±50ms caption sync. H4 FAISS-grounded LLM authoring + human gate.
- H5 chunked render matrix (5×4 shards). H6 incremental render cache keyed by row hash.

## 5. KPI ledger
| run | gate | wall | min/video | warnings | artifact MB | note |
|-----|------|------|-----------|----------|-------------|------|
| 91 | FAIL | – | – | 0 | 0.018 | BOM |
| 92 | PASS | 1h55m | ~10.7(h)/~9.7(v) | 20 | 105+84 | first autonomous; full re-render on schema commit (R9 trigger) |

## 6. CODEX loop (cognitive algorithm — run at EVERY step)
PERCEIVE → DIFF → DIAGNOSE → PATCH → VERIFY → DISTILL → CODEX
1 PERCEIVE gather signals (logs, KPIs, artifacts, intent).
2 DIFF signals vs §1/§2/§5 → anomaly list.
3 DIAGNOSE rank hypotheses by signature specificity (R2); pick one explaining ALL anomalies.
4 PATCH minimal reversible diff at root cause (R3).
5 VERIFY gate green ∧ tests green ∧ KPI ¬worse.
6 DISTILL generalize (anomaly,fix) → candidate rule + KPI row.
7 CODEX append §3/§5; promote to §2 WITH check; next step reloads §2 (compounding).
Mapping to influences: PERCEIVE/DIFF = S1 fast pattern-match; DIAGNOSE/PATCH/VERIFY = S2 slow check;
DISTILL/CODEX = strange loop (system rewrites its own rules); antifragile = each stressor adds a rule.
Invariants: I1 no step ends without §3+§5 append · I2 rule w/o check stays a §4 hypothesis · I3 rollback = git revert.

## 7. Trigger contract (renders are expensive — gate them hard)
Render runs IFF (label `render` on push/PR) OR (manual dispatch render_videos=true) OR
(content/*.csv changed AND label `render`). Schema/tooling/docs commits ⇒ validate+test+reflect ONLY.
See .github/workflows/render_shorts.yml `should_render` output.
