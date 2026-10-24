# 🎬 Feynman Physics Shorts × 🧠 QCOS Core — Saem Unified

**Turn Feynman's lectures into narrated, animated shorts — with a constitutional,
self-growing cognitive core underneath.**

> Tagline: NEET · JEE · MIT
> Style: 3Blue1Brown's visual elegance · Feynman's narrative voice · Strang's pedagogical clarity
> Formats: 1080×1920 (9:16) and 1920×1080 (16:9) · 30 fps · mastered to −14 LUFS
> Core: C++17, standard library only · one door · four languages · zero hidden state

---

## 0. What this repository is

Two bodies, one soul:

1. **The video factory** (Python): CSV in → validated → narrated (XTTS-v2 clone) →
   animated (Manim) → quality-gated → muxed (FFmpeg) → finished MP4 + ledger entry.
2. **The cognitive core** (`core/`, C++17): a deterministic, dependency-free engine that
   computes answers (never guesses), prints numbers exactly as the JavaScript reference
   prints them, runs reversible and quantum cursor machines, tracks beliefs at log-odds
   under Bernoulli's bar of moral certainty, enforces a written constitution, and grows
   its own libraries — only after witnesses approve them.

The constitution (compiled into the core, fingerprinted by `core.hash`):

- **A0** every answer is computed from the numbers in the question, never guessed
- **A1** every number leaving the core prints exactly as the reference engine prints it
- **A2** the door holds no hidden state; state travels in the JSON, in the caller's ledger
- **A3** measurement and overwrite are the only irreversible acts; the core reports the debt
- **A4** no belief is declared without moral certainty, 1000:1
- **A5** the ledger is append-only; rules without machine checks remain hypotheses
- **A6** the JavaScript bridge is a ruler, never a fallback; the shipped product runs the core alone

---

## 1. Architecture map

```
┌──────────────────────────────────────────────┐
 clients ──────────────▶│  THE DOOR (core/src/api.*)                   │
 saem/core.py (Python)  │  named methods, JSON in → JSON out           │
 SaemQcos/Bridge.cs (C#)│  call_json never throws; C door saem_call    │
 ref_bridge.js (JS ruler)└───────────────┬──────────────────────────────┘
 saem_cli (line protocol)                │
                                         ▼
   gen.*  core.*  forecast.*  text.*  quantum.*  program.*  rev.*
   cog.*  kernel.*  qcos.*  grow.*  stream.u
                                         │
                     ┌───────────────────┼────────────────────┐
                     ▼                   ▼                    ▼
            CONSTITUTIONAL GATE   L1 working (32)      PROVENANCE CHAIN
            (fail closed)         L2 episodic (64)     (hash-linked log)
                     │                   │                    │
                     └───────────────────┼────────────────────┘
                                         ▼
                              IR LADDER: intent → SIR → DIR → CIR → MIR
                                         ▼
                              execution (deterministic, auditable)

 VIDEO FACTORY (gates in series; a rejected row never ships):
 content CSV → schema gate → physics-oracle gate → audio gate (XTTS + mastering
 + LUFS) → render gate (Manim + word-synced beats + failure tracking)
 → visual-QA gate (frames + loudness) → FFmpeg stitch → ledger → MP4
```

---

## 2. The cognitive core (`core/src/`)

### 2.1 The door — `api.hpp` / `api.cpp` / `cli.cpp`
Every capability is a named method behind one registry. `call_json` returns
`{"ok":true,"result":…}` or `{"ok":false,"error":"…"}` and **never throws**, because the
C door cannot unwind across languages. `saem_cli` serves the same registry over a line
protocol (one JSON request per line, one answer per line, `id` echoed, flushed per line),
so Python, C#, Node — any host — is an equal client. `--source-id` prints the body
fingerprint compiled into the binary.

### 2.2 The canons — `numfmt.hpp`, `json.hpp`, `util.hpp`, `sha256.hpp`
- `jsnum` / `shortest_digits` / `round_sig`: shortest round-trip decimals, `×10ⁿ` forms,
  `toPrecision` tie-breaking — byte-identical to JavaScript's `Number.toString`.
- `json.hpp`: insertion-ordered objects, JS truthiness (`NaN`, `-0`, `""` falsy),
  safe-default accessors (missing fields never throw).
- `util.hpp`: UTF-8↔UTF-32 with U+FFFD replacement, JS whitespace/line-terminator classes,
  the seeded random stream, the 32-bit hash, `Math.round` parity.
- `sha256.hpp`: dependency-free SHA-256 — the soul fingerprint and receipt digest.

### 2.3 The Math Brain — `gen.hpp` / `gen.cpp`
12 topics, template table in fixed order, deterministic question generation from seeded
streams identical to the JS reference, exact solvers (`solve`), synthetic paper banks
(`demo_bank`: 12 topics × 3 concepts across years), hand-worked `vectors` self-checks.
Euler's conscience: **computed, never guessed.**

### 2.4 Reversible & quantum layers — `rev.hpp`, `qreg.hpp`, `spectral.hpp`
- `rev.hpp`: NOT/CNOT/CCNOT/SWAP/FREDKIN/H/Z/S as classical reversible gates;
  Bennett's compute–copy–uncompute for garbage-free execution (Feynman ch. 5–6).
- `qreg.hpp`: amplitudes over two-state atoms; `QProg` is Feynman's cursor machine —
  k+1 program-counter sites, hops that run gates on the moving branch, beam-splitter
  hops that put **control flow itself** in superposition; halting is an amplitude.
- `spectral.hpp`: true time evolution `e^{-iHt}` of the cursor Hamiltonian by Taylor
  series with scaling-and-squaring (`quantum.evolve`); no matrix ever formed.

### 2.5 Cognition & forecast — `cog.hpp`, `ef.hpp`
- Beliefs at log-odds (Napier's trick: evidence multiplies, so here it adds); declaration
  requires Bernoulli's 1000:1 moral certainty; `Learner` advises (slip/guess model) but
  never publishes; `shots_for` schedules trials to reach the bar.
- Forecast engine: ridge logistic regression, Platt calibration, method choice gated by
  a held-out likelihood ratio at the moral bar, forgetting-curve mastery forecasts,
  verdicts clamped by constitutional caps (`MAXP`, `MAX_NUDGE`, `CAP_ATTEMPTS`,
  `KEEP_DETAIL`, `MAX_FACULTY`). This is the classical baseline the quantum-probability
  research track (THINK H7) must beat on frozen data.

### 2.6 Constitution & QCOS kernel — `cos.hpp`, `kernel.hpp`, `qcos.hpp`
- `cos.hpp`: the articles above, governance caps, `coreHash()` (fingerprint of the
  constitution itself — amend an article and the soul changes), receipts and audits.
- `kernel.hpp`: `canon()` (canonical JSON text built only from the visible reading API),
  the file-clerk blackboard, and a **Landauer ledger**: every overwrite reports the bits
  it erased, in units of kT ln 2.
- `qcos.hpp`: the constitutional gate (fail closed on unknown ops, non-finite numbers,
  key bounds, cap violations, step budgets); the IR ladder
  `lower_sir → lower_dir → lower_cir → lower_mir` (MEANING ≠ REPRESENTATION ≠
  EXECUTION ≠ HARDWARE); L1 working memory (32 latched registers, full = fail, never
  evict); L2 episodic ring (64 ticks); hash-chained provenance (what/where/when/why);
  and the **12-point boot self-test**.

### 2.7 The growth substrate — `grow.c`, `grow_reg.cpp`, `tools/grow.py`
The core learns, writes, and reads — under a court:
- `grow.learn` appends witnessed cases to an append-only, hash-chained TSV store.
- `grow.recall` answers from witnessed cases; ungrown inputs return null, honestly.
- `grow.distill` emits a **quarantined** C++ method file into `grown/` from ≥ N cases.
- `tools/grow.py promote` rebuilds the body, replays every case through the live binary,
  runs the self-test and golden fixtures — and only then lets the file join `core/src/`.
  A refusal deletes the candidate and rebuilds. The canon never absorbs an unwitnessed rule.

### 2.8 Build & body fingerprint — `tools/build.py`, `Makefile.mk`, CMake
- `python3 tools/build.py cli|lib|all|id|verify` — compiler discovery (`$CXX`, c++, g++,
  clang++), `-std=c++17 -Wall -Wextra -Wpedantic`, incremental, cross-platform library
  names, and `source_id`: SHA-256 over (relative path, length, bytes) of every core file,
  CRLF-normalized, compiled in as `SAEM_SOURCE_ID`. `verify` proves the running binary's
  body equals the tree's body.
- `Makefile.mk` is a **clerk, not a kitchen**: every target delegates to `build.py`.
  Two doors may exist; two recipes may not.

---

## 3. Four languages, one truth

| Language | Role | File |
|---|---|---|
| C++17 | the only kernel; all truth | `core/src/*` |
| Python | OS session, ledgers, factory, gardener | `saem/core.py`, `saem/qcos_shell.py`, `tools/grow.py` |
| C# | typed client for .NET hosts | `SaemQcos/Bridge.cs` |
| JavaScript | the ruler (development only) | `tools/ref_bridge.js`, `tools/ref_bridge_qcos.js` |

Parity witnesses: `tests/diff/run.py` (case-by-case C++ vs JS with `tol`, `ignore`,
`regex`, `error` semantics and `null ≡ missing`), `tools/golden_qcos.py` (frozen fixtures
for resident-state methods), `tools/parity_line.py`. A witness that sees zero cases
fails the gate — blindness is not silence.

---

## 4. The video factory

### 4.1 Pipeline with gates (`batch_runner.py`)
```
schema gate → physics-oracle gate → audio gate → render gate → visual-QA gate → stitch → ledger
```
Flags: `--csv --only --chunk --total-chunks --draft --retries --dry-run --format
short|lecture|all --require-oracle --require-qa`. With `--require-*`, a rejected row never
ships; without them the gate warns and the ledger records the warning.

### 4.2 Audio chain (`generate_audio.py`, `soundscape.py`, `text_normalizer.py`)
Normalize (units after numbers, Greek spelled out, scientific notation, LaTeX stripped) →
XTTS-v2 clone (deterministic seed = SHA-256 of `video_id`, temperature 0.65, repetition
penalty 3.0, CPU fallback on CUDA OOM, speaker latent cached per batch) → resample
44.1 kHz → **mastering gate** (DC-remove, HPF 80 Hz, compress 3:1, LPF 12 kHz, −14 LUFS,
peak 0.891) → ambient pad → measured LUFS returned for the ledger.

### 4.3 Render engine (`render_universal.py` + engine modules)
Orientation-aware frames (vertical x∈[−4.5,4.5], y∈[−8,8]; horizontal x∈[−8,8],
y∈[−4.5,4.5]), SaemLabs branding, 60+ routed primitive types across static, motion,
self-animated, and physics-engineered families (`projectile_motion`, `physics_simulation`
RK4, `electromagnetic_wave`, `linear_algebra`, `fluid_dynamics`, `rotational_motion`,
`geometry` 1D/2D/3D, calculus family, interference family, …). Unknown or failing
primitives are skipped with `[WARN]` **and recorded in the render report** — degradation,
not deception. Beats align to word-level timings (`tools/word_sync.py`, stable-ts or
whisper-timestamped) with equal-slice fallback.

### 4.4 The gates
- `tools/physics_oracle.py`: primitives known, LaTeX balanced, required physics fields
  present, values physically reasonable, scenes non-empty.
- `tools/visual_qa.py`: MP4 exists, duration sane, ≥10 of 10 sampled frames non-empty;
  LUFS measurement helper.
- `tools/ledger.py`: append-only render ledger (`logs/render_ledger.jsonl`) with
  `summarize` / `export` / replay-friendly entries — the feedback loop that was missing.

---

## 5. Authoring input

**Generators over hand-editing.** The canonical pattern is a small Python writer that
uses `csv.DictWriter` + `json.dumps` (see `make_batch.py`, `tools/generate_topic_bundle.py`,
`tools/generate_feynman_series.py`, `generate_universal_master_csvs.py`) — escaping is then
guaranteed at every layer.

Schema: 14 required columns
`video_id, concept_type, header_title, tagline, question_text, option_a..d,
correct_answer, equations_json, visual_data_json, audio_script, orientation`
plus optional `beats_json`, `target_duration_sec`. GENERIC rows leave the six PYQ fields
empty (seven consecutive commas). Word-count plausibility: 112–180 words @ 60 s,
337–540 @ 180 s.

Ready-made batches: `examples/feynman_speed_demo.csv`,
`examples/projectile_complete_object.csv`, `examples/physics_simulation_spring_demo.csv`,
`examples/geometry_dimensions_demo.csv`, and the six-video cross-volume batch
(3 vertical concepts + 3 horizontal applications, one per Feynman volume) produced by
`make_batch.py`.

---

## 6. Testing pyramid

1. **Core self-test** — 12 points at boot (`qcos.boot`): SHA-256 vector, Bell pair,
   reversible adder, `jsnum` half-ulp, L1 latch/bounds, L2 wrap, gate allow/deny,
   lowering determinism, exec, provenance chain.
2. **Reference tests** — `make ref-test` (the JS reference's own suite; dev only).
3. **Differential parity** — `make diff` / `tests/diff/run.py`: C++ vs JS case by case.
4. **Golden fixtures** — `tools/golden_qcos.py record|check` for resident-state methods.
5. **Python suite** — `python3 -m pytest -q` (no `|| true`: red fails the run).
6. **Pipeline gates** — oracle + QA + LUFS on every rendered row, recorded in the ledger.

---

## 7. CI — `.github/workflows/render_shorts.yml` (v3)

`validate → build-core (verify + boot) → core-tests (parity + golden + qcos shell) →
engine-tests → generate-validate → render (opt-in, orientation matrix, XTTS + render
caches, --require-oracle --require-qa --resume) → reflect (think-bot ledger commit)`.

Render is opt-in: `[render]` in the commit message, the `render` label, or a manual
dispatch with `render_videos=true` (plus optional `only=` id list). Wall time without
render ≈ 4 minutes. Concurrency-grouped; artifacts retained 7 days; logs 14.

---

## 8. Governance — `THINK.md`

The CODEX loop (PERCEIVE → DIFF → DIAGNOSE → PATCH → VERIFY → DISTILL → CODEX) runs at
every step; §3 run log and §5 KPI ledger are append-only; §2 rules require machine checks
(R1–R29, including: R19 one canon two builders, R22 a blind witness fails the gate,
R23 the constitutional gate fails closed, R24 provenance verifies on every read,
R27 grown code is quarantined until witnessed, R29 promotion stays human until moral
certainty). Hypotheses H1–H8 live in §4 until evidenced; the quantum-cognition track (H7)
must clear gates Q0–Q4 against the classical forecast baseline before it touches
production.

---

## 9. Quick start

```bash
# system: ffmpeg, texlive (+science/fonts), cairo/pango, build-essential, node 22
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cp /path/to/voice.wav saem_voice_sample.wav        # 10–20 s, back it up separately

# core
python3 tools/build.py cli && python3 tools/build.py verify
python3 -m saem.qcos_shell boot                     # 12-point self-test
make test                                           # ref-test + diff + pytest

# factory
python3 schema_validator.py content_batch.csv --require-oracle
python3 batch_runner.py --only <video_id> --draft   # fast preview
python3 batch_runner.py --require-oracle --require-qa

# feedback & growth
python3 -m tools.ledger summarize
python3 tools/grow.py witness gen.format '{"x": 3.14159}'
python3 tools/grow.py distill gen.format 50 && python3 tools/grow.py promote gen.format
```

---

## 10. File inventory (touch map)

| Area | Files | Touch? |
|---|---|---|
| Daily input | `content_batch.csv`, generators | ✅ edit via generators |
| Factory | `batch_runner.py`, `generate_audio.py`, `render_universal.py`, `schema_validator.py`, `soundscape.py`, `text_normalizer.py`, engine modules | 🔵 stable |
| Gates & ledger | `tools/physics_oracle.py`, `tools/visual_qa.py`, `tools/word_sync.py`, `tools/ledger.py` | 🔵 stable |
| Core | `core/src/*` (door, canons, brain, quantum, cognition, constitution, QCOS, growth) | 🔴 court-gated (grow/promote only) |
| Clients | `saem/core.py`, `saem/qcos_shell.py`, `SaemQcos/Bridge.cs` | 🔵 stable |
| Rulers & fixtures | `tools/ref_bridge*.js`, `tests/diff/*`, `tests/golden/*` | 🟡 with run# refs |
| Governance | `THINK.md`, `knowledge/cases.tsv`, `grown/`, `logs/` | 🟡 append-only |

---

## 11. Troubleshooting (top failures)

- **`[verify] STALE binary …`** — rebuild: `python3 tools/build.py cli`.
- **Row/column misalignment** — count the seven-comma gap; regenerate via a Python writer.
- **`[oracle] … unknown primitive`** — typo or unregistered type; the renderer skips and the report records it.
- **MP4 with no audio** — check `temp_audio/<id>_voice.wav` size; scroll for the TTS exception.
- **Render too slow** — `--draft` (480p15 ≈ 10× faster); CI shards with `--chunk/--total-chunks`.
- **Parity mismatch** — read the two lines printed; numbers must match byte-for-byte (A1); last-ulp drift is only allowed inside `tol`.
- **Promotion refused** — the grown file failed a witness; it was deleted and the body rebuilt. Read the ledger entry.

---

## 12. Golden rules

1. Every new video is one new row, written by a generator. Nothing else changes.
2. Code is frozen; CSV is fluid. Editing a `.py` is adding a feature, not making a video.
3. Validate before rendering; gate before shipping (`--require-oracle --require-qa`).
4. LF line endings only in CSVs; CRLF breaks JSON-in-CSV.
5. Back up `saem_voice_sample.wav` separately; it is not in the repo.
6. One batch = one orientation for clean QC.
7. PYQs are math-checked by the oracle and by you before commit.
8. The core grows only through quarantine, witnesses, and promotion. Never by hand.

---

## 13. Why it is built this way (reference corpus)

| Source | What it gave the system |
|---|---|
| Napier, *Constructio* | mantissa/exponent canon; log-domain beliefs (evidence multiplies → here adds) |
| Bernoulli, *Ars Conjectandi* | cases → expectation; moral certainty 1000:1 as the declaration bar |
| Euler, *Elements of Algebra* | algebra as rule-governed operation: answers computed, never guessed |
| Feynman, *Lectures on Computation* | reversible gates & Landauer's bill (ch. 5); cursor machines & halting amplitude (ch. 6); file clerk memory (ch. 1); clocking & jams (ch. 7) |
| Schrödinger, *Collected Papers* | evolution as `e^{-iHt}`; stationary states as the next spectral layer |

---

## 14. Credits & license

Built on Manim Community, Coqui TTS (XTTS-v2), FFmpeg, and Feynman's *Lectures on
Physics* (I–III). Element grammar inspired by 3Blue1Brown. See `LICENSE`.
