# Saem Unified: status and handoff

## START HERE

1. Restore (only if /home/claude/saem-unified is missing): `project_read` the project document `claude/saem-unified-bundle.py.txt`
   (a self-extracting Python file; the tool saves large text to a local file and returns its path), then
   `python3 <that path> /home/claude/saem-unified`. It restores every source file and checks each SHA-256.
   Not in the bundle: `third_party/open-math-harness-src/` (re-attach the user's `open-math-harness-main.zip`, or fetch
   https://github.com/openmathmodel/open-math-harness) and build output (run `make cli`).
2. `cd /home/claude/saem-unified && python3 tools/where.py` shows the real state.
3. Work in this priority order (the user's standing instructions and requests):
   0. DONE (xv6 absorbed 2026-10-27, kernel v0 built and checked 2026-10-30): `docs/knowledge/xv6.md`, `docs/ARCHITECTURE.md` (the one picture),
      study copy `third_party/xv6-riscv-fall19/`, and the code injection `core/c17/` = the zero-heap sovereign kernel: limits, status, sha256/hmac, pool,
      regs (32 working + 64 episodic), wal, journal, gate (Zone 0), seal, core (freeze/quarantine/release/verify). Reference: `docs/KERNEL_C17.md`.
      Check everything in 20 s: `python3 tools/check_c17.py` (18 check groups; strict builds with two compilers, zero-heap and no-float and no-global proofs,
      all tests under AddressSanitizer/UBSan/ThreadSanitizer, cross-checks against hashlib, the C++ SHA-256 and Python's Unicode database).
      The release tool for the constitution seal is `tools/seal.py` (independent Python implementation; the C test compares both).
   a. Constitution. The project instructions (changed 2026-10-26) make the Constitution of Medina the core constitution of our Models.
      Brief: `docs/WORKER_constitution.md`. Do it BEFORE the cos port, because the cos port ports the constitution.
   b. Nucleus injection (user request 2026-10-25): `docs/NX_BRIEF.md`.
   c. C++ ports of the forecast engine and of cbt/cos, then the Python interface: `docs/WORKER_forecast.md`, `WORKER_cos.md`, `WORKER_ui.md`.
      Forecast and UI do not depend on a, b or 0 and can run first (two workers at most at once).
   d. Next kernel pieces: SIR (semantic IR with exact rationals, zero-copy tokenizer into a static arena, independent exact checker), then hooking the
      gate in front of the C++ door (and the zero-global-state refactor of the Registrar), then the C header and C# interop. The Constitution of Medina (item a)
      becomes the sealed articles through `tools/seal.py`.
4. At the end of every burst: `python3 tools/pack.py`, `project_write` the bundle over `claude/saem-unified-bundle.py.txt` and this note over
   `claude/saem-unified-status.md` (ALWAYS an absolute `local_path`, a relative one fails with "no file exists"), update this note, tell the user.

### How the usage limit works here (measured 2026-10-25/26) and what to do about it

The user's plan allows a small amount of work per 5-hour window. In a long chat, the first message of each window re-reads the whole chat.
The first chat is about 340,000 tokens, so on the evening of 2026-10-25 a window allowed 2 or 3 turns before the limit. Parallel workers are
the other big cost: five workers each read about 100,000 tokens in their first 15 seconds and used up a window at once.
So: (1) the user should continue in a NEW chat inside the EdTech AI project, starting with
"Read the project document claude/saem-unified-status.md and continue from it" (about a tenth of the cost per window);
(2) never launch more than two workers at once; give each a narrow scope and tell it to skim, not read whole files.

Read this file first. It exists because every work burst so far ended at the session limit
(about 15 minutes) and the next burst re-read the same files before doing anything.
Do not re-orient from scratch. Read this, run the resume commands, continue.

Last updated: 2026-10-30 (user timezone Asia/Kolkata).

## Priority now (user request 2026-10-25 23:00): absorb Open Math Harness

The user attached `open-math-harness-main.zip` (Rust, Apache-2.0: "Nucleus", a capability-based microkernel for AI agents, with
swarm exploration "Ultramath", Lean-verified proof search, memory, approvals) and asked: extract all its knowledge, convert it to
C, C++ and C#, inject it into our model. Study copy: `third_party/open-math-harness-src/` (notice: `third_party/NOTICE-open-math-harness.md`).
Brief and file ownership for the five workers: `docs/NX_BRIEF.md`. Results: `docs/knowledge/*.md` (what we learned; INDEX.md covers all areas),
`core/src/nx/*.hpp` (C++ modules), `core/tests/nx_*_test.cpp`. The C header (`core/include/`) and C# interop (`interop/csharp/`) come
after the modules exist, from one dedicated worker, together with the JSON methods `nx.*` and the Python exposure.
This comes BEFORE the forecast and cos ports and the Python interface, which stay as briefed in `docs/WORKER_*.md`.

## Project instructions changed again (seen 2026-10-26/27): additions

- "Learn from MIT OCW for computing resources." (the project holds MIT 6.828/6.033/6.042 and Strang material; xv6-riscv arrived 2026-10-27.)
- A standing build prompt: a C17 portable core baseline parsing and translation pipeline with (1) Zone 0 constitutional ethical gate:
  every raw input passes a hard deterministic safety filter first; (2) Semantic IR (SIR): validated instructions become machine-independent
  symbolic logical shapes with zero numerical approximation; (3) zero-heap discipline: no malloc/free, compile-time static arrays,
  `COS_WORKING_LIMIT = 32` active registers. `core/c17/` is that baseline.
- The Constitution of Medina is the core constitution (see item a above).

## Project instructions changed on 2026-10-25 (they now say)

Phase 1 exam prediction and testing model; Phase 2 a parallel ed-tech model ecosystem working like a team; Phase 3 Quantum Cognitive OS.
Every piece of code must converge toward that: isolated modules that can become parallel nodes; thread-safe lock-free routines
(std::atomic); C bindings (extern "C") and C# interop; frontend Python only for orchestration; backend deterministic C/C++/C#;
no external infrastructure; pure deterministic transformations, ZERO GLOBAL STATE, alignas(64), fail closed on the Forbidden Zone.
Known deviation to fix: the Registrar in `core/src/api.cpp` is a global registry (immutable after start-up). Plan: a constant method
table per module plus an instance-based Core handle (`saem_open / saem_call / saem_close`), then update the WORKER briefs.

## What the user asked for (2026-10-01, unchanged)

One product that joins two pages Claude made earlier (they are the design reference, kept in
`/mnt/user-data/uploads/`: `saem-physics-exam-forecaster.html`, `saem-physics-mock-test-1.html`):

1. Forecaster: reads past papers (any years), ranks the most probable topics and questions for the next paper,
   shows the reasons, back-tests itself, says "chances, never promises".
2. Test machine: NTA-style timed mock test (sections, palette, mark for review, negative marking, review with solutions).
3. Together: forecast -> assembled paper (exact solutions from the Math Brain) -> test -> results -> weak topics -> study plan.
4. For teachers and students in India: works offline, on phone, iOS, desktop, Hindi and English.
5. "Design perfectly and give me the Model": the interface looks like the two pages; the Model is the immutable core.

Project rules (EdTech AI project instructions): frontend in Python, backend in C/C++/C#, no dependency on others'
data, models or infrastructure, immutable constitutional core, deterministic, runs on any machine.

## Architecture (decided, do not reopen)

```
reference/src/*.js   JavaScript reference engines = the SPEC. Development only. Never shipped.
        |  differential tests (same JSON requests to both, answers must agree)
core/src/*.cpp,hpp   C++17 core, standard library only. One door: JSON in, JSON out.
        |  api.hpp: Registrar("method.name", handler). saem_cli = JSON lines on stdin/stdout. libsaem = C door `saem_call`.
saem/  (Python)      Frontend: Python standard library only, NO JavaScript. Local web server renders HTML+CSS.
                     Talks to the core through saem/core.py (subprocess to build/saem_cli, or ctypes to libsaem).
```

Why this shape: the JS is the proven behaviour (35 tests); the C++ must equal it number for number; the
Python layer is only screens and storage. Determinism: `-ffp-contract=off -fno-fast-math`, seeded RNG, no clocks in the core.

Constitution (core, fixed): chance not promise (<95% and shows years), tested before trusted (back-test verdict),
solutions say where they came from (Math Brain or paper), opinion nudges at most 20% from at most 5 faculty and
cannot add a question, data stays on the device, memory is bounded (60 attempts, 10 with detail).
Soul = SHA-256 fingerprint of the constitution, the solver table, the vectors and the source id.

## State

| Piece | Spec | C++ | Differential cases |
|---|---|---|---|
| json, numfmt, util, sha256 | n/a | done | n/a |
| Math Brain `gen.*` (36 exact solvers) | gen.js | done | 325/325 agree (`make diff`) |
| api registry, cli, build.py, ref_bridge.js, diff runner | n/a | done | n/a |
| Forecast engine `forecast.*`, `text.tokens` | ef.js | NOT STARTED | none |
| Reading + test machine `mcq.*`, `text.*`, `papers.*`, `clock.fmt` | cbt.js, ef.js, cos.js | NOT STARTED | none |
| COS model `core.*`, `bank.*`, `paper.*`, `study.*`, `test.*`, `forecast.verdict/notes/nudge` | cos.js | NOT STARTED | none |
| Python interface (`saem/`) | reference/app.css, the two HTML pages | NOT STARTED (`saem/` holds only an empty `static/`) | n/a |
| MODEL.md, package, delivery | n/a | not started | n/a |

JS reference: `node --test "reference/test/*.test.js"` -> 35 of 35 pass.

## The truth is in two places, not in this table

- `python3 tools/where.py` looks at the files and asks both engines which methods they serve. Run it first on every resume.
- `docs/PROGRESS_forecast.md`, `PROGRESS_cos.md`, `PROGRESS_ui.md`: one line per milestone, appended by each worker.
- `docs/WORKER_forecast.md`, `WORKER_cos.md`, `WORKER_ui.md`: the complete briefs. Launch a worker with
  "Read docs/WORKER_x.md and do it", and it continues from the last line of its progress file.

## Working rhythm (the user's standing instruction, 2026-10-25)

The session limit allows about 15 minutes of work per 5-hour window, and the user says "Continue" about once a day.
The user wants: save work BEFORE the limit, every time, so the next day continues; deliver a Model, then keep going.
So: (1) update this file and the progress files after each milestone, not at the end; (2) before any long step, write down
what it is; (3) at the end of a burst send the user a snapshot zip (the container is not guaranteed to survive a long break);
(4) save the status note to the EdTech AI project (`claude/saem-unified-status.md`) at the end of each burst.

## Where the specs are

- `docs/PORT_SPEC_forecast.md`: complete brief for porting ef.js (file ownership, methods, fidelity rules, test plan).
- `docs/PORT_SPEC_cos.md`: complete brief for porting cbt.js + cos.js + the reading helpers.
- `tools/ref_bridge.js`: the full list of method names and arguments both engines must serve.
- `reference/app.css`: the stylesheet for the unified interface (sections: header, page furniture, forms, feedback,
  stats and bars, papers, forecast, paper preview, study, rules, test machine, results). Reuse it in `saem/static/`.
- The transcript of the whole session: `/root/.claude/projects/-home-claude/<session>.jsonl`; saved task files in `/root/.claude/tasks/`.

## Resume in 60 seconds

```
cd /home/claude/saem-unified
make diff                        # builds build/saem_cli, runs every case against the JS reference
node --test "reference/test/*.test.js"
ls core/src docs tests/diff/cases saem   # see which ports exist
```

## Decisions made on the way

- Soul in C++ cannot hash JS function text. It hashes VERSION + constitution JSON + solver table + vectors + `source_id()`.
  So `core.hash` and `core.info.id` differ between engines; tests use a regex for them. `core.receipt` and `core.sha256` match exactly.
- No JavaScript in the product. Timer: CSS-only countdown plus `<meta http-equiv=refresh>` auto-submit, deadline enforced by the server.
- Classroom mode: teacher runs the server with `--host 0.0.0.0`; students open the address on the same Wi-Fi or hotspot.
- No claims of knowing the real paper. Demo data is labelled synthetic. Faculty opinion is optional and capped.

## Burst discipline (the lesson)

1. Never spend a burst re-reading. Read this file, not the sources.
2. Write files early and in large pieces. Update the State table the moment something works.
3. Delegate mechanical ports to worker agents with the PORT_SPEC briefs; they start with a small context and cost far less.
4. Save progress notes before starting any long step.
