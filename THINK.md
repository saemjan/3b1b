# THINK.md — Cognitive Operating System for saemjan/3b1b
> A self-improving ledger integrating JEE Advanced patterns and EdTech research.
> Rule zero: **a lesson not encoded as an automated check is a lesson lost.**

## 0. Operating protocol (read before EVERY step)
1. Load §1 (model) + §2 (rules) + §5 (KPIs) as preconditions.
2. Execute the step via the CODEX loop (§6).
3. Append §3 (run log) + §5 (KPI row); promote durable lessons to §2 WITH a machine check (I2).
4. §3/§5 append-only. §2 changes need a run#/commit ref.

## 1. Mental model (current truth)
**Three-Engine Architecture** (from research):
1. **Scientific Correctness Engine**: Verify physics equations, dimensional analysis, limiting cases
2. **Learner Model Engine**: Bayesian Knowledge Tracing (BKT) for mastery tracking
3. **Visual Explanation Engine**: Feynman-style "What system? What quantity? What rule?"

**JEE Advanced Patterns** (2007-2025):
- Physics topics: Mechanics (40%), EM (30%), Thermo (15%), Modern (15%)
- Question types: Integer (0-9), MCQ (multiple correct), Match-the-following, Numerical
- Difficulty progression: Classical → Integrated modern physics
- Common themes: Conservation laws, symmetry, dimensional analysis

**Pipeline**: CSV → Three-engine verification → XTTS-v2 TTS → Manim renderer → FFmpeg mux → MP4

## 2. Rules (encoded lessons — every rule needs a machine check)
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
- **R11 Three-engine verification**: Every video passes scientific, learner, visual engines. [tools/batch_runner.py]
- **R12 Trust layer**: Scripts validated for hallucinated physics and citations. [tools/trust_layer.py]
- **R13 JEE pattern coverage**: Content spans all JEE topics proportionally. [knowledge_base/jee_patterns.json]

## 3. Run log (append-only)
- #91 FAIL(11s) BOM incident → R1,R2.
- #92 PASS 1h55m — first autonomous run; 10/10 both orientations; 105MB+84MB artifacts; warnings = vocab+wordband+manim deprecations → R4,R5,R6,R7. New lesson: schema-commit re-triggered full render → R9,R10.
- **#103 PREP** — Integrated JEE Advanced analysis (2007-2025) and EdTech research. Added three-engine architecture, trust layer, JEE question generator. → R11,R12,R13.

- #117 gate=success render=skipped 2026-10-23 wall=– sigs=clean

- #118 gate=success render=cancelled 2026-10-23 wall=– sigs=clean

- #119 gate=success render=skipped 2026-10-24 wall=– sigs=clean

- #120 gate=success render=skipped 2026-10-24 wall=– sigs=clean

- #128 gate=success render=skipped 2026-10-24 wall=– sigs=clean

- #139 gate=success render=skipped 2026-10-24 wall=– sigs=clean

## 4. Open hypotheses
- H1 ManimGX (wgpu) hot primitives ≥10× speed. 
- H2 tts_router (edge drafts / XTTS finals).
- H3 stable-ts ±50ms caption sync. 
- H4 FAISS-grounded LLM authoring + human gate.
- H5 chunked render matrix (5×4 shards). 
- H6 incremental render cache keyed by row hash.
- **H7 Quantum cognitive algorithm**: Test if quantum-probability models predict learner behavior better than BKT/IRT. Requires: (1) frozen dataset, (2) classical baseline, (3) held-out comparison, (4) ethical review.
- **H8 Adaptive difficulty**: Use BKT mastery to adjust question difficulty in real-time.

## 5. KPI ledger
| run | gate | wall | min/video | warnings | artifact MB | engines_passed | note |
|-----|------|------|-----------|----------|-------------|----------------|------|
| 91 | FAIL | – | – | 0 | 0.018 | 0/3 | BOM |
| 92 | PASS | 1h55m | ~10.7(h)/~9.7(v) | 20 | 105+84 | 2/3 | first autonomous; full re-render on schema commit (R9 trigger) |
| 103 | PREP | – | – | – | – | 3/3 | three-engine architecture added |

## 6. CODEX loop (cognitive algorithm — run at EVERY step)
PERCEIVE → DIFF → DIAGNOSE → PATCH → VERIFY → DISTILL → CODEX
1 PERCEIVE gather signals (logs, KPIs, artifacts, intent, **learner mastery data**).
2 DIFF signals vs §1/§2/§5 → anomaly list.
3 DIAGNOSE rank hypotheses by signature specificity (R2); pick one explaining ALL anomalies.
4 PATCH minimal reversible diff at root cause (R3).
5 VERIFY gate green ∧ tests green ∧ KPI ¬worse ∧ **all three engines pass**.
6 DISTILL generalize (anomaly,fix) → candidate rule + KPI row.
7 CODEX append §3/§5; promote to §2 WITH check; next step reloads §2 (compounding).

**Mapping to research**: 
- PERCEIVE/DIFF = System 1 (fast pattern-match)
- DIAGNOSE/PATCH/VERIFY = System 2 (slow check)
- DISTILL/CODEX = Strange loop (system rewrites its own rules)
- **Three engines = Trust architecture** (scientific correctness + learner modeling + visual explanation)

Invariants: 
- I1 no step ends without §3+§5 append 
- I2 rule w/o check stays a §4 hypothesis 
- I3 rollback = git revert
- **I4 all content passes three-engine verification before rendering**

## 7. Trigger contract (renders are expensive — gate them hard)
Render runs IFF (label `render` on push/PR) OR (manual dispatch render_videos=true) OR
(content/*.csv changed AND label `render`). Schema/tooling/docs commits ⇒ validate+test+reflect ONLY.

## 8. JEE Advanced Integration (NEW)
**Question Bank**: `book/advance/` contains 18 years (2007-2025) of JEE Advanced papers.

**Coverage Requirements**:
- Mechanics: 40% of questions (kinematics, newton laws, energy, momentum, rotation, oscillations)
- Electromagnetism: 30% (electrostatics, current electricity, magnetism, EM induction)
- Thermodynamics: 15% (heat transfer, gas laws, processes)
- Modern Physics: 15% (photoelectric, Bohr model, nuclear, dual nature)

**Question Types to Support**:
1. Integer answer (0-9): Single digit response
2. MCQ (one or more correct): Multiple choice with partial marking
3. Match-the-following: Matrix matching questions
4. Numerical value: Decimal answers with tolerance

**Adaptive Difficulty** (using BKT):
- Mastery < 0.3: Easy questions (direct formula application)
- Mastery 0.3-0.7: Medium questions (multi-step reasoning)
- Mastery > 0.7: Hard questions (integration across topics, limiting cases)

**Feynman Method Integration**:
For each JEE concept, generate explanation following:
1. **What system is being studied?** (Define boundaries)
2. **What quantity is being tracked?** (Conserved/monitored quantity)
3. **What rule keeps the accounting consistent?** (Physical law)

Example for "rolling without slipping":
- System: Disc + surface (include friction in system)
- Quantity: Energy (kinetic + rotational + thermal)
- Rule: Work-energy theorem with friction doing zero work (static friction)

## 9. Research Integration: Quantum Cognitive Algorithm (NEW)
**Status**: Research track, NOT production feature.

**Working Hypothesis Q1**: In some learning contexts, response probabilities may depend on question order or contextual framing in a way that classical models (BKT/IRT) capture poorly, and a quantum-probability model may predict held-out behavior better.

**Fair Comparison Protocol**:
1. Define narrowly scoped outcome (e.g., predict next question correctness)
2. Create frozen train/validation/test split by learner and time
3. Compare against strong baselines: BKT, IRT, logistic regression
4. Implement quantum-inspired candidate with documented assumptions
5. Use same held-out data, comparable tuning, documented compute
6. Report: predictive quality, calibration, subgroup performance, robustness, latency, maintainability
7. Repeat across topics and cohorts before claims

**Promotion Gates**:
- Q0: Model specification, intended phenomenon, predicted advantage, failure conditions
- Q1: Reproducibility (reference implementation, synthetic tests, fixed seeds)
- Q2: Offline benchmark (held-out comparison vs classical, confidence intervals)
- Q3: Educational pilot (ethically reviewed, consented, preregistered outcome)
- Q4: Production approval (benefit > complexity + privacy cost, monitoring + rollback exist)

**Decision**: Build with classical models first. Design pluggable interface for quantum research track. Let it win by evidence—or remain research without delaying core platform.

## 10. Implementation Roadmap
**Phase 1 (Current)**: Three-engine architecture + trust layer ✓
**Phase 2 (Next)**: JEE question generator + adaptive difficulty
**Phase 3 (Future)**: Quantum cognition research track + learner analytics dashboard
#176 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#178 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#179 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#180 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#181 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#182 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#183 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#184 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#185 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#191 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#192 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#193 gate=failure render=true 2026-10-24 wall=- sigs=clean ci
#194 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#196 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#199 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#201 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#202 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#203 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#204 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#206 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#207 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#208 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#211 gate=failure render=true 2026-10-24 wall=- sigs=clean ci
#212 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#213 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#214 gate=failure render=true 2026-10-24 wall=- sigs=clean ci
#220 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
#221 gate=failure render=true 2026-10-24 wall=- sigs=clean ci
#222 gate=failure render=false 2026-10-24 wall=- sigs=clean ci
