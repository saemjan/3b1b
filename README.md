# 🎬 Saem Unified — Feynman Physics Shorts × 🧠 QCOS Core

**Turn Feynman's lectures into narrated, animated shorts — with a constitutional,
self-growing, quantum-cognitive core underneath.**

> Tagline: NEET · JEE · MIT
> Style lineage: 3Blue1Brown's visual elegance · Feynman's narrative voice · Strang's pedagogical clarity
> Formats: 1080×1920 (9:16) and 1920×1080 (16:9) · 30 fps · mastered to −14 LUFS
> Core: C17/C++17/C# · stdlib-only rulers · one door · four tongues · zero hidden state

---

## 0. The Vision — why this repository exists

We are building, in three converging phases, a **thinking teaching machine**:

| Phase | Deliverable | Convergence test |
|---|---|---|
| **1 (now)** | Physics & maths teaching-video model: CSV in → witnessed gates → narrated, animated, mastered MP4 + ledger receipt | every number computed, every look novel, every gate machine-checked |
| **2** | Parallel ed-tech ecosystem: many model-nodes working as one team over the same core | nodes are stateless, receipted, liftable into parallel workers without refactoring |
| **3** | Quantum Cognitive Operating System (QCOS) on a 4+1 RISC-V topology | Zone 0 + crypto on the isolated core; four app cores run bounded data matrices |

**Why the core is C / C++ / C#:** deterministic memory, zero-overhead
abstractions, a stable FFI floor, and native concurrency — so the phase shift
1→2→3 never breaks the foundation. **Python is orchestration edge only**:
it drives gates, ledgers and renderers; it never owns truth.

Every piece of Phase-1 code must already be Phase-2/3-shaped:
stateless pure functions, flat JSON-serializable payloads, C-struct-friendly
data, callable through one IPC door.

---

## 1. The Law — binding for every artifact

**MEANING ≠ REPRESENTATION ≠ EXECUTION ≠ HARDWARE.**

| # | Invariant | What it forbids / demands |
|---|---|---|
| 1 | **No connectionist logic in the core** | symbolic reasoning, formal logic, exact linear algebra only; no weights, no probabilities, no DL frameworks. Belief = integer ledger tally at the 1000:1 bar, never a float |
| 2 | **Zero-heap deterministic memory** | no `malloc/free` in hot paths; fixed compile-time tracking: `COS_WORKING_LIMIT = 32`, `COS_EPISODIC_LIMIT = 64`; exhaustion = refusal, never growth |
| 3 | **Fail-closed discipline** | any uncertainty (non-finite value, cap breach, missing provenance, id-echo mismatch, wrong mode) → immediate task rejection or absolute node freeze; never degrade silently, never guess |
| 4 | **Immutable constitution** | core identity cryptographically sealed (`SAEM_SOURCE_ID`, canon hash); register mutations trip integrity monitors |

**Translation spine (every request, every render, every kernel call):**

```
Human Intent → Zone 0 (constitutional ethical gate)
             → SIR  (Semantic IR: exact rational matrices, no floats)
             → DIR  (Domain IR: masks, populations/Shape, LINE | GRID | GRAPH)
             → CIR  (Execution IR: bounded sequential schedules, fixed horizons)
             → MIR  (Machine IR: bare-metal micro-ops)
```

**Execution protocol:** O(N) deterministic literal scans (no hash tables, no
next-token lookups) · exact tracking provenance at every state transition ·
explicit byte-for-byte buffer copies using hard static structs · no
third-party analytics, networking packages, or probabilistic approximations
inside the core.

**Topologies:** Phase I = pure, standalone, memory-safe C17 local CLI with
zero external dependencies. Phase III = heterogeneous **4+1 RISC-V**: the +1
isolated core runs Zone 0 and crypto hashes in physical-memory mode; four app
cores run parallel data matrices.

---

## 2. The Constitution (articles & caps)

Compiled into the core, fingerprinted by `core.hash`; the canon lives in
**`qcos.cxn`** — one canon, four tongues (C++ / Python / C# / JS).

- **A0** every answer is computed from the numbers in the question, never guessed
- **A1** every number leaving the core prints exactly as the reference engine prints it
- **A2** the door holds no hidden state; state travels in the JSON, in the caller's ledger
- **A3** measurement and overwrite are the only irreversible acts; the core reports the debt
- **A4** no belief is declared without Bernoulli's bar of moral certainty, 1000:1
- **A5** the ledger is append-only; rules without machine checks remain hypotheses
- **A6** the JavaScript bridge is a ruler, never a fallback; the shipped product runs the core alone

Caps (declared once, in `qcos.cxn` and `tools/qcosc.py`'s Checker):

```
COS_WORKING_LIMIT 32   COS_EPISODIC_LIMIT 64   COS_MAX_DELEGATION 8
COS_MAX_ACTIONS   64   COS_NAME_MAX 64         COS_MAX_PROJECT_STOPS 8
```

**Generated files are law-bound:** never edit `*.g.cpp / *.g.py / *.g.cs /
*.gen.js` — edit `qcos.cxn` and re-run `python3 tools/qcosc.py qcos.cxn`.
`tools/qcosc.py --handshake` proves all four tongues agree on method set and
argument order; `--verify` proves disk matches canon.

---

## 3. Architecture map (what exists today)

```
clients ──▶ THE DOOR: build/saem_cli (line protocol) ──▶ saemc gateway (tools/saemc.py)
            │  one registry, call_json never throws, C door saem_call
            ├─ gen.*  core.*  forecast.*  text.*  quantum.*  program.*  rev.*
            ├─ cog.*  kernel.*  qcos.*  grow.*  stream.u
            ├─ CONSTITUTIONAL GATE (fail closed) · L1 working(32) · L2 episodic(64)
            └─ PROVENANCE CHAIN (hash-linked) → IR ladder SIR→DIR→CIR→MIR

VIDEO FACTORY (gates in series; a rejected row never ships):
 content CSV → schema gate → physics-oracle gate → core-id gate → audio gate
 → render gate (manim + engines + genome skin) → visual-QA gate → stitch
 → ledger (render + audio + style + gates receipts)

CONTENT-IN (one ruler everywhere):
 jee_model_engine (26 witnessed concept models) → factory_input / author
 → schema_validator (spoken-word canon) → physics_oracle (SPEC-as-data)

WITNESS LADDER (CI, all exit-coded 0 ok / 1 drift / 2 environment):
 build → verify → handshake → golden_qcos → parity_line → canon_lint
 → engine_check (imports + routing parity + selftests) → check_all → ledger verify
```

Folder map:

| Path | Role |
|---|---|
| `core/src/`, `qcos/` | C/C++ kernel, capability core, canon bindings |
| `tools/` | gates, compilers, witnesses, bot layer (`build.py`, `qcosc.py`, `saemc.py`, `check_all.py`, `engine_check.py`, `canon_lint.py`, `parity_line.py`, `golden_qcos.py`, `qcos_handshake.py`, `ledger.py`, `backend_policy.py`, `style_genome.py`, `style_belief.py`, `style_gate.py`, `factory_input.py`, `author.py`, `extract_feynman.py`, `word_sync.py`, `visual_qa.py`, `physics_oracle.py`, `grow.py`, `think_loop.py`, `auto_fixer.py`) |
| root engines | `physics_simulation.py`, `calculus_engine.py`, `electromagnetics_engine.py`, `geometry_engine.py`, `linear_algebra_engine.py`, `rotational_motion_engine.py`, `fluid_dynamics_engine.py`, `jee_model_engine.py`, `render_universal.py`, `batch_runner.py`, `schema_validator.py`, `generate_audio.py`, `soundscape.py`, `sound_design.py`, `text_normalizer.py` |
| `saem/`, `SaemQcos/` | Python & C# typed clients (generated + facades) |
| `tests/`, `knowledge_base/` | golden fixtures, parity corpora, witnessed curriculum |
| `os.md` | **the synthesis document** — xv6/RISC-V/Euler/Strang/Juhász doctrine → QCOS construction plan P0–P12 |

---

## 4. The Way We Build — the gen-3 contract (from now on, this way)

Every engine, tool, gate, or core file written or upgraded **must** satisfy:

1. **Pure stdlib ruler first.** The correctness core is stdlib-only Python or
   freestanding C; it is *the ruler* everything else is measured against.
2. **Selected libraries only through `tools/backend_policy.py`.**
   probe (importable + API-complete) → witness (parity vs the ruler on a
   frozen fixture) → cost (speedup at current size) → pin (`SAEM_BACKEND`)
   → record (ledger) → degrade (fall back to the ruler, reason recorded).
   numpy/scipy/PIL/TTS/ffmpeg/manim are *devices*, never truth.
3. **Headless-importable.** No manim/numpy/torch import at module top; lazy
   inside route/build functions. `engine_check.py` stub-imports everything.
4. **ROUTE_TABLE v1.** Visual engines expose
   `ROUTE_TABLE: dict[type, callable(scene, spec) -> Mobject|None]`;
   they read `scene.ctx` (StyleContext) for color/stroke/font/placement;
   explicit `spec["color"]` remains the teacher override.
5. **Frozen witnesses.** Every module ships `selftest() -> [(name, ok, detail)]`
   with closed-form rulers (Euler identities, Strang K/T/B/C determinants,
   Rodrigues rotation, Poiseuille profile↔Q, −3 dB at cutoff, …) and a
   `--selftest` CLI that exits non-zero on drift.
6. **Receipts everywhere.** Every run appends a schema-stamped line
   (`schema_version: 3`, gate name, backend, digests, debt) to the append-only
   ledger via `tools/ledger.py`. `clear()` is unconstitutional; `rotate()`
   prices its debt.
7. **Determinism + fail-closed guards.** Same input → same bytes; guards raise
   `ValueError`/return structured errors; unknown input is refused, never
   interpolated.
8. **Degradation, not deception.** A skipped primitive, a missing device, or a
   fallen-back backend is *recorded* in the report and the ledger — never
   silently hidden.
9. **Truth frozen, representation alive** (the Teacher Rule, §6).
10. **One canon per quantity.** Spoken words = `text_normalizer.spoken_word_count`;
    expressions = `calculus_engine.compile_expression`; primitives =
    `schema_validator.KNOWN_PRIMITIVES` ∩ routed set; fingerprints =
    `tools/build.py source_id`. Two rulers for one quantity is a bug.

**New-file checklist** (CI-enforced by `check_all.py` + `engine_check.py`):
docstring stating layer & stance · stdlib-only top imports · validation
helpers · pure ruler functions · optional gated backend · `ROUTE_TABLE` (if
visual) · `selftest()` · `__main__` runner · ledger receipt · no global
mutable state · flat JSON-serializable I/O.

---

## 5. The Gate Ladder — nothing ships unjudged

Per row, in order; a promoted gate's refusal stops the row:

```
Gate 0 schema   (structure, JSON repair, finite-only numbers, spoken-word band,
                 PYQ integrity, clone detection)          --require-schema
Gate 1 oracle   (SPEC-as-data physics validation, engine dry-runs, trust rules) --require-oracle
Gate 2 core     (saem_cli body id == tree id; stale binary fails closed)        --require-core
Gate 3 audio    (chunked XTTS, pure concat, resample, master −14 LUFS, seeded pad)
Gate 4 render   (manim + engines + genome skin; SAEM_SOURCE_ID receipted)
Gate 5 QA       (PPM-ruler frame stats, duration, LUFS; ffmpeg/ffprobe probed)  --require-qa
Ledger          (append-only receipt: gates, backends, genome, digests, debt)
```

Witness phase (CI, required): `engine_check` → `golden_qcos check` →
`parity_line` → `canon_lint` → `qcos_handshake` → `check_all` → `ledger verify`.
Exit codes are law: **0 = truth holds · 1 = drift/fail · 2 = environment**
(missing binary/canon/tool — rebuild or install, never re-record).

---

## 6. The Teacher Rule — never the same lesson twice

- **Style genome** (`tools/style_genome.py`): palette family, hue, layout
  topology, motion grammar, entrance grammar, voice grammar, pace, stroke,
  fonts, 3D camera — derived from `(content, topic, audience, generation)`,
  novel against `logs/style_ledger.jsonl` (distance ≥ 0.35), mutated/bred by
  QA evidence.
- **Beliefs over genes** (`tools/style_belief.py`): log-odds updated per QA
  outcome; a gene value is promoted only past the 1000:1 bar (A4); the next
  batch explores the *least certain* gene (`cog.next` discipline).
- **Novelty gate** (`tools/style_gate.py`): a batch whose genomes repeat a
  recent look fails CI like a physics drift would.
- **Narration rhetoric** follows the genome's voice grammar
  (question-first / picture-first / contrast / story-arc / myth-bust);
  durations retune to *spoken* words, never raw tokens.
- Numbers stay Euler-strict and witnessed; only the *look, order, voice and
  pacing* evolve. Same physics, never the same frame or ear-print twice.

---

## 7. Doctrine library — what we absorbed, where it shows

| Source | Doctrine now enforced in code |
|---|---|
| **xv6 (rev 7)** | layering; two-level locking (structure vs content); bounded buffers everywhere; sleep = lock handoff; monotonic ids; ZOMBIE two-phase completion; claim/complete dispatch; log = single commit point + boot recovery; panic = report + freeze; guard pages; copy-only boundary crossings |
| **RISC-V (rev 5)** | 4+1 topology substrate; M/S privilege delegation as Zone 0 event filter; per-hart arenas & `tp` node address; PLIC per-core enable/threshold; trapframe as provenance record |
| **Euler, *Elements of Algebra*** | exact rational arithmetic as SIR; closed-form identities as witnesses (Vieta, binomial sums, series closed forms) |
| **Strang, *CSE*** | stability guards (dt·ω inside method regions); K/T/B/C difference-matrix determinants as frozen rulers; Simpson/Richardson convergence witnesses; CFL-style fail-closed step budgets |
| **Juhász, *Modern C++ in embedded systems*** | zero-overhead abstractions; constexpr/consteval where the compiler can execute; RAII + lock-free handoff at the C++ seam; no hidden cost in templates |
| **os.md** | the synthesis: substrate inventory, doctrine extraction, spine alignment, and the bit-by-bit construction plan **P0–P12** for the QCOS core |

---

## 8. Working agreements (golden rules, upgraded)

1. **Generators over hand-editing.** Every new video is one new row written by
   a generator (`factory_input`, `author`, `jee_model_engine`); nothing else
   changes. Code is frozen; CSV is fluid.
2. **Validate before rendering; gate before shipping.** `--require-*` flags in
   CI/release runs; warnings are debt, errors are refusals.
3. **LF line endings in CSVs; CRLF breaks JSON-in-CSV.**
4. **One batch = one orientation** for clean QC.
5. **Grown code enters only through quarantine → witness → promotion**
   (`grow.py`); the canon never absorbs an unwitnessed rule.
6. **Back up `saem_voice_sample.wav` separately**; it is not in the repo.
7. **Pin for reproducibility:** `SAEM_BACKEND`, `SAEM_TTS_BACKEND`, seeds and
   genome generations are recorded in every receipt; a replay must reproduce
   bytes.
8. **No hidden state, ever** (A2): paths resolve from repo root or explicit
   env (`SAEM_LEDGER_PATH`, `SAEM_CLI`, `SAEM_PARITY_CORPUS`); temp files live
   in temp dirs and are deleted; ledgers are the only memory.
9. **Receipts are the product's conscience:** if an outcome isn't in the
   ledger, it didn't happen.
10. **Session discipline:** at pause, save state (queue position, upgraded
    files, open witnesses); at resume, re-verify with the daily ritual below.

---

## 9. The daily ritual — verification commands

```bash
# core
python3 tools/build.py all && python3 tools/build.py verify
python3 tools/qcosc.py qcos.cxn --verify && python3 tools/qcosc.py qcos.cxn --handshake
python3 tools/qcos_handshake.py            # four-tongue byte parity
python3 tools/golden_qcos.py check         # resident-state witness
python3 tools/parity_line.py               # C++ core vs JS ruler
python3 tools/canon_lint.py                # canon ↔ Registrar ↔ bridges
python3 tools/engine_check.py --github-summary   # imports + routing parity + all selftests
python3 tools/check_all.py --github-summary      # universal auditor + witness ladder
python3 tools/ledger.py verify && python3 tools/style_gate.py logs/style_ledger.jsonl content_batch.csv

# engines & tools (each exits non-zero on drift)
for m in physics_simulation calculus_engine electromagnetics_engine geometry_engine \
         linear_algebra_engine rotational_motion_engine fluid_dynamics_engine \
         jee_model_engine text_normalizer soundscape sound_design generate_audio \
         schema_validator physics_oracle visual_qa word_sync factory_input author \
         extract_feynman ledger golden_qcos parity_line engine_check check_all \
         canon_lint qcosc saemc qcos_handshake build; do
  python3 $m.py --selftest || echo "DRIFT: $m"; done

# a batch
python3 tools/factory_input.py            # or: python3 tools/author.py --source catalog --retune --yes
python3 batch_runner.py --csv content_batch.csv --require-schema --require-oracle --require-core --require-qa
```

---

## 10. Queue & continuation protocol

**Remaining upgrades (one-by-one ritual: audit table → gen-3 rewrite →
integration notes → verify):**
` the kernel files
`spinlock.c/h`, `vm.c` equivalents for the QCOS core per `os.md` P0–P12.

**Ritual per file:** (1) audit against the gen-3 contract and list defects
with severities; (2) rewrite preserving public API signatures; (3) wire
receipts, witnesses, genome skinning, backend gates; (4) state integration
patches for `batch_runner`/`engine_check`/workflow; (5) give exact verify
commands. Nothing merges without its `selftest()` green.

**Memory protocol:** at every pause, record: phase status, upgraded-file
inventory, open witnesses, queue position, and any canon/cap changes. At
resume, re-run §9 before touching code.

---

## 11. Phase roadmap — convergence checklist

- **Phase 1 exit criteria:** all engines gen-3 & witnessed; gate ladder green
  in CI; style novelty enforced; ledger union complete; curriculum
  (`knowledge_base/`) fully linked to witnessed concept models.
- **Phase 2 exit criteria:** nodes stateless & receipted; SPSC rings between
  workers (virtio semantics: publish → notify → sleep → reclaim, index-as-id,
  in-band status verification); team scheduler = bounded CIR steps; the C#
  and JS clients pass handshake from separate machines.
- **Phase 3 exit criteria:** C17 freestanding kernel boots on RISC-V; Zone 0
  on the +1 core in physical-memory mode; app cores run LINE/GRID/GRAPH
  populations over 32/64-slot arenas; integrity monitor freezes on any
  constitutional breach; `os.md` P0–P12 all witnessed.

---

*Sealed: this README, `qcos.cxn`, and `os.md` are the constitution. Code that
contradicts them is a bug, however convenient. — SaemLabs*
