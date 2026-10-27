# vision.md — The Sovereign Reference of the QCOS Project (v2)
Read this first. Every session. Every task. Every file.
This document is the master index of everything held in memory: the mission,
the law, the constitution, the absorbed doctrine, the build contract, the
gates, the rituals, the queue, and the daily work order. `README.md` is the
repository-facing constitution; `os.md` is the kernel synthesis; this file is
the memory contract — the checklist run before any work begins.
Companion documents: `README.md` (working agreements), `os.md` (xv6/RISC-V
synthesis + P0–P12 construction plan), `qcos.cxn` (the canon),
`knowledge_base/` (witnessed curriculum), `logs/*.jsonl` (the ledger union).
`CONTEXT_ANCHOR.md` was merged into this file on 2026-10-27 and is retired to
a one-line stub; this file is now the single anchor.

v2 amendment summary (2026-10-27): §2 gains the three validation vectors;
§6 gains information thermodynamics; §16 closes the upgrade queue; §21 (Daily
Sequence), §22 (Economic Constitution), §23 (Pre-Flight), §24 (Amendment Log)
are added. Numbering of §0–§20 is frozen — cross-references never break.

## §0 — Purpose of this file
- Single point of recall. Everything decided, absorbed, or sealed lives
  here as an index entry with its enforcement point in code.
- Session-start gate. §23 (extending §20) is a mandatory checklist; no work
  begins until it is satisfied from memory.
- Drift detector. If a new decision contradicts an entry here, the entry
  is amended explicitly (with date and reason in §24) — never silently
  overridden.

## §1 — The Mission and the Three Phases
We build QCOS: a sovereign, non-connectionist, deterministic cognitive
operating system that teaches physics and mathematics the Feynman/3b1b way,
for NEET · JEE · MIT aspirants.

| Phase | Target | Convergence test | State |
|---|---|---|---|
| I | Pure, standalone, memory-safe C17 CLI, zero external deps; Python orchestration edge for the video factory | every number computed & witnessed; every look novel; every gate machine-checked | in progress — daily order in §21 |
| II | Parallel ed-tech model team: many stateless nodes over one core, SPSC rings, claim/complete dispatch | nodes liftable into parallel workers without refactoring | planned |
| III | 4+1 RISC-V: +1 isolated core (M-mode, physical memory) runs Zone 0 + crypto; 4 app cores run bounded data matrices | bring-up witnesses pass on hardware/QEMU | projected |

Why C / C++ / C# core: deterministic memory, zero-overhead abstractions, a
stable FFI floor, native concurrency — the phase shift 1→2→3 must never break
the foundation. Python never owns truth; it orchestrates, gates, receipts.
Audience promise (the Teacher Rule): same physics, never the same lesson
twice — truth frozen, representation alive (§13).

## §2 — The Ethical Root: Constitution of Medina → Zone 0
The Medina charter is the ethical substrate of the constitutional gate:
one community, explicit covenants, mutual defense, no hidden allegiance.
Zone 0 encodes it as deterministic vectors checked on every intent:
- Niyyah (intention): declared purpose must match the operation; no
  hidden routes, no side channels, no undeclared effects.
- Shari'ah bounds: mechanics of riba (unearned increment), gharar
  (deceptive uncertainty), maysir (gambling on outcomes) are refused —
  in code: no unpriced debt, no silent degradation, no probabilistic fallback.
- Mithaq & Sidq (covenant & truthfulness): byte-for-byte parity across
  all four tongues; a node that cannot prove its words keeps silent
  (fail-closed), never approximates.
Zone 0 sits before SIR in the spine (§5) and blocks recursive self-mutation
and memory breaches absolutely.

### §2.1 — The Three Validation Vectors (compile-time checks, merged from CONTEXT_ANCHOR)
Every intent, parameter, or logical block flowing down the processing fabric
is audited across three explicit passes before it may generate a Semantic IR
token:
I. **The Intention Vector (Niyyah Matrix).** "Actions are judged by
   intentions." The compiler rejects tasks containing hidden execution
   routes, obscure conditional triggers (asymmetric obfuscation), or
   malicious optimization variables. All optimization trajectories must be
   transparently tracked back to their computational source.
II. **The Action Invariant Vector (Shari'ah Compliance).** Immediate,
   automated task rejection if the logic pipeline constructs:
   - Riba (interest/usury): any calculation containing exponential
     compounding debt loops or guaranteed yields without asset exposure.
   - Gharar (extreme asymmetry): processing models that rely on hidden
     data pools or exploit information gaps between processing nodes.
   - Maysir (speculation/gambling): resource allocation strategies based
     purely on probabilistic risk layout without structural value tracking.
III. **The Covenant & Parity Alignment Vector (Mithaq & Sidq).** Data nodes
   must execute explicit, byte-for-byte fidelity across distributed
   operations. A peer instance that alters its execution footprint or
   violates distributed synchronization terms is flagged as a foundational
   breach: its verification hash is invalidated and the node is isolated
   safely (fail-closed freeze, never silent drift).

## §3 — The Law
MEANING ≠ REPRESENTATION ≠ EXECUTION ≠ HARDWARE.
- Meaning = canon (`qcos.cxn`), articles, exact rational mathematics.
- Representation = emitted bindings, genomes, skins, narration rhetoric.
- Execution = CIR schedules, bounded steps, claim/complete dispatch.
- Hardware = C17 freestanding core now; RISC-V 4+1 later.
A change at one layer must never silently mutate another. Parity gates
(`qcosc --handshake`, `parity_line`, `canon_lint`) enforce the separations.

## §4 — The Four Invariants (mechanically enforced)
| # | Invariant | Enforcement |
|---|---|---|
| 1 | No connectionist logic | symbolic/exact only; belief = integer tally at 1000:1 (A4), never float probability; XTTS/ASR/manim are edge devices, their outputs are measured data, never logic |
| 2 | Zero-heap deterministic memory | COS_WORKING_LIMIT 32, COS_EPISODIC_LIMIT 64; static arenas; exhaustion = QCOS_ERR_BUDGET_EXHAUSTED, never growth |
| 3 | Fail-closed discipline | uncertainty (non-finite, cap breach, missing provenance, id-echo mismatch, wrong mode) → task rejection or absolute node freeze; report debt, then halt |
| 4 | Immutable constitution | SAEM_SOURCE_ID + canon hash + handshake + append-only ledger = integrity monitor; mutation trips it |

## §5 — The Translation Spine
Human Intent → Zone 0 (ethical gate, §2)
             → SIR  (Semantic IR: exact rational matrices, int64 num/den, NO floats)
             → DIR  (Domain IR: masks, populations/Shape, topologies LINE|GRID|GRAPH)
             → CIR  (Execution IR: bounded sequential schedules, fixed loop horizons)
             → MIR  (Machine IR: bare-metal micro-ops, C17 now, RISC-V later)
Each lowering is deterministic and auditable; each layer's output is the next
layer's frozen input. Floats may appear only at the render/representation edge.

## §6 — The Execution Protocol
- O(N) deterministic literal scans over arrays; no hash tables, no
  next-token lookups, no learned indices.
- Exact tracking provenance at every state transition — reversible-logic
  paradigm: (step, op, keys, pre_hash) recorded into fixed rings/ledger.
- Information thermodynamics (merged from CONTEXT_ANCHOR): every state
  erasure or eviction is modeled as a physical dissipation boundary
  (Landauer's principle). Forgetting is not arbitrary; it occurs only on
  hard capacity overruns via deterministic replacement policies. Provenance
  is kept as physical garbage state sufficient to reverse the transition
  back to the empty-register baseline.
- Explicit byte-for-byte buffer copies using hard static structs; no
  aliasing across boundaries; copy-only crossings (copyin/copyout doctrine).
- No third-party analytics, networking packages, or probabilistic
  approximations inside the core. Networking exists only at the host edge
  (door protocol), receipted.
- Bounded horizons everywhere: timers re-arm; writes chunk to transaction
  size; loops carry fixed counts; waits re-check condition + killed.

## §7 — The Topologies
- Phase I: freestanding C17 CLI. One cooperative dispatch loop. Linker-
  carved arenas. JSON lines over stdio as the door. Diagnostics survive init
  failure (early-write path).
- Phase III: 4+1 RISC-V. +1 core: M-mode, no MMU (physical memory), owns
  Zone 0, crypto, global event priorities (`medeleg/mideleg` as its filter),
  UART diagnostics. 4 app cores: S-mode, per-core buddy-discipline arenas,
  per-core PLIC enable/threshold, inter-core SPSC rings with virtio semantics
  (publish → notify → sleep → reclaim; index-as-identity; in-band status
  verification — the envelope alone never authorizes a commit).

## §8 — Constitution Articles & Caps
A0 computed, never guessed · A1 numbers print exactly as the ruler
prints them · A2 door holds no hidden state · A3 measurement and
overwrite are the only irreversible acts; debt is reported · A4 no belief
without 1000:1 moral certainty · A5 ledger append-only; unwitnessed rules
are hypotheses · A6 the JS bridge is a ruler, never a fallback.
Caps (declared once in `qcos.cxn`, enforced by `qcosc` Checker):
`WORKING 32 · EPISODIC 64 · MAX_DELEGATION 8 · MAX_ACTIONS 64 · NAME_MAX 64`.
Generated files are law-bound: never edit `*.g.cpp/*.g.py/*.g.cs/*.gen.js`;
edit `qcos.cxn`, re-run `qcosc`. Deferrals and canonization queues are priced
data with expiry dates (`tests/corpus/deferred.json`, `canon_queue.json`).

## §9 — Doctrine Library (absorbed texts → enforced patterns)
| Source | Doctrine now enforced |
|---|---|
| Constitution of Medina | Zone 0 vectors (§2, §2.1); community-as-contract; explicit covenants |
| Euler, Elements of Algebra | exact rational arithmetic; closed-form identities as witnesses (Vieta, binomial sums, series closed forms, continued-fraction exactness) |
| Strang, Computational Science & Engineering | stability guards (dt·ω inside method regions); K/T/B/C difference-matrix determinants as frozen rulers; Simpson/Richardson convergence; CFL-style fail-closed step budgets |
| xv6 book (rev 7) | layering; two-level locking; bounded buffers; sleep = lock handoff; monotonic ids; ZOMBIE two-phase completion; claim/complete; log = single commit point + boot recovery; panic = report + freeze; guard pages; lifecycle comments as constitutions |
| RISC-V book (rev 5) | 4+1 substrate; privilege delegation as event filter; per-hart arenas; `tp` node address; trapframe as provenance record; Sv39 walk as single translation chokepoint |
| Juhász, Modern C in Embedded Systems | zero-overhead abstractions; constexpr/consteval where the compiler can execute; RAII + lock-free handoff at the C++ seam; no hidden cost |
| QCOS master spec | spine, invariants, topologies, execution protocol (§3–§7) |
Full file-by-file extraction lives in `os.md` §1–§15.

## §10 — Substrate Inventory (fully absorbed, kernel complete)
Batches 1–10: kernel.ld, kernelvec.S, bio.c, buddy.c, buf.h · console.c,
date.h, defs.h, elf.h, entry.S · exec.c, fcntl.h, file.c, file.h, fs.c ·
fs.h, kalloc.c, list.c, log.c, main.c · memlayout.h, param.h, pipe.c,
plic.c, printf.c · proc.c, proc.h, ramdisk.c, riscv.h, sleeplock.c ·
sleeplock.h, start.c, stat.h, string.c, swtch.S · syscall.c/h, sysfile.c,
sysproc.c, trampoline.S · trap.c, types.h, uart.c, virtio.h, virtio_disk.c ·
vm.c. Status: COMPLETE. Remaining kernel-side work is synthesis
(`os.md` P0–P12), scheduled in §21 Phase F.
Project-side absorbed & gen-3 upgraded: engines (physics_simulation,
calculus, electromagnetics, geometry, linear_algebra, rotational, fluid,
jee_model_engine), render_universal, audio chain (text_normalizer,
soundscape, sound_design, generate_audio), gates (schema_validator,
physics_oracle, visual_qa, word_sync), factory (factory_input, author,
extract_feynman), witnesses/tools (ledger, golden_qcos, parity_line,
engine_check, check_all, canon_lint, backend_policy, style_genome,
style_belief, style_gate, think_loop, grow, auto_fixer, ref_bridge.js,
ref_bridge_qcos.js, bench_render_backends), core tongues (build, qcosc,
saemc, qcos_handshake).

## §11 — The Gen-3 Contract (how every file is built or upgraded)
- Pure stdlib ruler first — correctness core needs nothing external.
- Selected libraries only via `backend_policy`: probe → witness (parity
  vs ruler on frozen fixture) → cost → pin (`SAEM_BACKEND`) → record →
  degrade (fall back to ruler, reason recorded).
- Headless-importable — no manim/numpy/torch at module top; lazy inside
  route/build functions.
- ROUTE_TABLE v1 for visual engines: `ROUTE_TABLE[type] = fn(scene, spec)`;
  skin from `scene.ctx` (genome); explicit `spec["color"]` = teacher override.
- Frozen witnesses: `selftest() -> [(name, ok, detail)]` with closed-form
  rulers; `--selftest` CLI exits non-zero on drift.
- Receipts: schema-stamped append-only ledger line per run
  (`schema_version: 3`, gate, backend, digests, debt).
- Determinism + fail-closed guards: same input → same bytes; guards raise
  structured errors; unknown input refused, never interpolated.
- Degradation, not deception: skips/fallbacks recorded in report+ledger.
- Truth frozen, representation alive (§13).
- One canon per quantity (§14).
- Stateless & flat: pure functions, JSON-serializable I/O, C-struct-
  friendly payloads — Phase-2 liftable without refactoring.
- New-file checklist (CI-enforced): docstring stating layer & stance ·
  stdlib top imports · validation helpers · pure ruler · optional gated
  backend · ROUTE_TABLE if visual · selftest · `__main__` runner · ledger
  receipt · no global mutable state.

## §12 — The Gate Ladder (nothing ships unjudged)
Gate 0 schema → Gate 1 oracle → Gate 2 core-id → Gate 3 audio
→ Gate 4 render → Gate 5 QA → Ledger receipt
Witness phase: engine_check → golden_qcos → parity_line → canon_lint
→ qcos_handshake → check_all → ledger verify → style_gate
Exit codes are law: 0 truth holds · 1 drift/fail · 2 environment
(rebuild/install; never re-record on 2). Promotions: `--require-schema`,
`--require-oracle`, `--require-core`, `--require-qa`, `--require-routes`,
`--require-novelty`, `--strict`.

## §13 — The Teacher Rule (truth frozen, representation alive)
- Style genome (palette/layout/motion/entrance/voice/pace/stroke/fonts/camera)
  derived per `(content, topic, audience, generation)`; novelty distance
  ≥ 0.35 vs recent ledger genomes; `style_gate` fails clone batches.
- Beliefs over genes: log-odds per QA outcome; promotion only past 1000:1
  (A4); next batch explores the least-certain gene.
- Narration rhetoric follows the genome voice grammar; durations retune to
  spoken words.
- Witnesses, rulers, canon, caps, LUFS/peak targets: frozen forever.
- Looks, order, timbre, pacing, quiz emission: evolve every lesson.

## §14 — The One-Canon Rule (single ruler per quantity)
| Quantity | The ruler |
|---|---|
| Spoken word count | text_normalizer.spoken_word_count |
| Expression policy | calculus_engine.compile_expression |
| Primitive vocabulary | schema_validator.KNOWN_PRIMITIVES ∩ routed set (engine_check parity) |
| Source fingerprint | tools/build.py source_id |
| Number printing | jsnum / canon (A1) |
| Duration band | factory_input.retune_duration (shared by author/schema/oracle) |
Two rulers for one quantity = bug. New quantities get a ruler before use.

## §15 — The Upgrade Ritual (per legacy file handed in)
1. Audit table: purpose + defects vs Gen-3 contract, severity per defect.
2. Gen-3 rewrite: preserve public API signatures; apply §11 in full.
3. Integration notes: patches for `batch_runner` / `engine_check` /
   `check_all` / workflow / ledger union.
4. Verify commands: exact, runnable, exit-coded.
Nothing merges without its `selftest()` green and its parity witnesses closed.

## §16 — The Queue & Roadmap
- Upgrade queue: **CLOSED 2026-10-27.** think_loop.py → grow.py →
  auto_fixer.py → ref_bridge.js → ref_bridge_qcos.js → bench_render_backends.py
  all gen-3, witnessed, receipted.
- Active work order: **§21 The Daily Sequence** (Phases A–F, steps 1–27).
  Kernel synthesis `os.md` P0→P12 is scheduled inside Phase F. Nothing is
  worked outside §21 except an emergency drift fix (which itself becomes a
  ledgered step).
- Phase exits: Phase 1 = all engines gen-3 & witnessed, ladder green,
  novelty enforced, ledger union complete, curriculum fully model-linked.
  Phase 2 = stateless receipted nodes + SPSC rings + team scheduler.
  Phase 3 = C17 kernel boots on RISC-V; Zone 0 on +1 core; monitors freeze
  on breach; P0–P12 witnessed.

## §17 — The Verification Ritual (run before and after every change)
python3 tools/build.py all && python3 tools/build.py verify
python3 tools/qcosc.py qcos.cxn --verify && python3 tools/qcosc.py qcos.cxn --handshake
python3 tools/qcos_handshake.py
python3 tools/golden_qcos.py check
python3 tools/parity_line.py
python3 tools/canon_lint.py
python3 tools/engine_check.py --github-summary
python3 tools/check_all.py --github-summary
python3 tools/ledger.py verify
python3 tools/style_gate.py logs/style_ledger.jsonl content_batch.csv
# per-module: python3 <module>.py --selftest   (all lines ok, exit 0)

## §18 — The Memory Protocol (save / resume)
- At pause: record phase status, upgraded-file inventory, open witnesses,
  queue position (§21 step number), canon/cap changes, and any
  deferred/expiring entries.
- At resume: run §23 checklist, then §17 ritual, then continue at the
  recorded §21 step — never ahead of it.
- Amendments: changes to this file carry date + reason in §24;
  contradictions are resolved explicitly, never by silent edit.

## §19 — The Never-Change List
`qcos.cxn` as single canon · append-only ledger · no hidden state in doors ·
exit-code contract 0/1/2 · frozen witnesses & rulers (§14) · caps (§8) ·
fail-closed on uncertainty · copy-only boundary crossings · monotonic ids ·
degradation always recorded · Medina vectors in Zone 0 · C/C++/C# as the
unbreakable core floor · zero-debt economy (§22).

## §20 — SESSION-START CHECKLIST (mandatory, from memory)
Before writing or upgrading anything, confirm each line:
- [ ] Law recalled: MEANING ≠ REPRESENTATION ≠ EXECUTION ≠ HARDWARE (§3)
- [ ] Four invariants active: no connectionism, zero-heap, fail-closed, sealed constitution (§4)
- [ ] Spine order respected: Zone 0 before SIR before DIR before CIR before MIR (§5)
- [ ] Execution protocol: O(N) scans, provenance per transition, byte-wise copies, no third-party core deps (§6)
- [ ] Topology target known: which phase this artifact must survive (§7)
- [ ] Articles A0–A6 and caps honored; generated files untouched (§8)
- [ ] Doctrine source identified for the pattern being reused (§9, os.md)
- [ ] Gen-3 contract will be satisfied in full (§11)
- [ ] Gate ladder & exit codes will judge the result (§12)
- [ ] Teacher Rule: truth frozen, representation alive (§13)
- [ ] One ruler per quantity; new quantity gets a ruler first (§14)
- [ ] Upgrade ritual steps 1–4 planned for the incoming file (§15)
- [ ] Queue position confirmed; resume point matches saved memory (§16, §18)
- [ ] §17 verification ritual scheduled before and after the change
- [ ] Never-change list scanned for conflicts (§19)
If any box cannot be ticked from memory: re-read the cited section before
proceeding. Work begun without this checklist is out of constitution.

## §21 — THE DAILY SEQUENCE (Master Work Order, effective 2026-10-28)
Protocol: one step per session unless the step says otherwise. Order of a
working session: §23 pre-flight → §17 ritual → the step's work → §17 ritual
→ ledger receipt → stop. A step is DONE only when its exit command returns 0
(exit 2 = environment: fix the environment the same day, never re-record a
witness on 2). Resume contract: say "start step N"; step N begins only after
step N−1's exit is verified. Deletions (🗑) execute only after their parity
witness passes, and each deletion is ledgered as priced debt (A5).

**Phase A — Unblock the witnesses (missing infrastructure)**
1. Generate & commit canon artifacts: `python3 tools/qcosc.py qcos.cxn` →
   commit `qcos.schema.json`, `core/src/api_registry.g.cpp`,
   `saem/client.g.py`, `SaemQcos/Client.g.cs`, `tools/ref_bridge.gen.js`,
   `tests/diff/cases/canon.jsonl`. *Exit: `qcosc qcos.cxn --verify` = 0.*
2. Add `reference/src/{ef,cbt,gen,cos}.js` (ported from core gen/ef/cos,
   each with `--selftest`). *Exit: `node tools/ref_bridge.js --selftest` = 0.*
3. Add `tests/corpus/{requests.jsonl, deferred.json, canon_queue.json}`
   seeded from `golden_qcos.SEQUENCE`. *Exit: `parity_line.py` ≠ 2.*
4. Add `knowledge_base/curriculum` (extract_feynman) + `grown/.gitkeep`;
   fix `.gitignore` (logs/ bench_out/ grown/ media/ reports/ __pycache__).
   *Exit: `extract_feynman.py --selftest` = 0 and check_all project phase green.*
5. Run the full witness ladder once to baseline. *Exit: every §17 command 0
   (or every 2 fixed the same day).*

**Phase B — CI honesty**
6. Fix `.github/workflows/render_shorts.yml`: remove `|| true`, add ladder
   steps, `think_loop --strict`, nightly bench job. *Exit: a deliberate-drift
   commit fails CI loudly (prove once with a seeded bad row).*
7. `Makefile.mk` → thin wrapper over `tools/build.py`; pin `requirements.txt`
   and mark gated-optional libs. *Exit: `make` == build.py path; check_all green.*
8. Grep & fix stale repo name (`3b1b` → `sir`) in workflows/docs/CI strings.
   *Exit: zero hits.*

**Phase C — Canon & caps (QCOS law into the canon)**
9. `qcos.cxn`: add `@cap WORKING 32 / EPISODIC 64`, the `zone0` gate method,
   and `qcos.provenance`. *Exit: canon_lint green.*
10. `qcosc` Checker enforces caps + zone0 presence; regenerate; handshake.
    *Exit: `qcosc qcos.cxn --verify --handshake` = 0.*

**Phase D — Core C constitutional upgrade (os.md P2/P3/P5/P9)**
11. `kernel.hpp`/`qcos.hpp`: static 32/64 pools, slot anatomy
    (identity/refcount/valid/lock), junk-fill on free. *Exit: new core selftests pass.*
12. `qcos_api.cpp`: Zone 0 enforcement, provenance ring, fail-closed
    refusals. *Exit: golden_qcos + parity_line green.*
13. `grow.c`/`grow_reg.cpp`: receipts aligned with `tools/grow.py` v3.
    *Exit: a promote round-trip receipted in the ledger.*
14. Add core selftest binaries `test_caps.c`, `test_zone0.c`,
    `test_provenance.c` wired into build. *Exit: build runs them; all pass.*

**Phase E — Edge consolidation & deletions**
15. `saem/core.py` + `saem/qcos_shell.py` gen-3 (timeouts, id-echo, receipts,
    `--selftest`). *Exit: selftests green.*
16. `SaemQcos/Bridge.cs` arg-order witness vs schema + selftest harness.
    *Exit: dotnet build + witness pass.*
17. `batch_runner.py` on receipted visual_qa/word_sync APIs; style_gate in
    the release path. *Exit: one full batch run receipted end-to-end.*
18. 🗑 Audit → delete `core_processor.py` (after no-reference proof).
    *Exit: deletion receipted; CI green.*
19. 🗑 Delete `generate_universal_master_csvs.*.py` (after factory_input
    covers its seeds). *Exit: same.*
20. 🗑 Freeze → delete `make_batch.py` (after author-catalog parity
    witness). *Exit: same.*
21. Merge `FUTURE_ARCHITECTURE.md` into `os.md`; pointer-ize
    `ARCHITECTURE.md` + `CSV_AUTHORING.md`. *Exit: docs single-sourced; stubs only.*

**Phase F — Phase-2/3 substrate (os.md P0–P12)**
22. Add `qcos/` freestanding C17 skeleton (types/capability/config/event/
    kernel + tests + CMakeLists). *Exit: P0–P4 witnesses green on host.*
23. Add `cpp/include/qcos/{SpscQueue,Kernel,Supervisor}.hpp`. *Exit: compile
    clean + header selftests.*
24. Add C# `QcosNative`/`QcosKernel` + `ExamHarness`. *Exit: dotnet build +
    harness run.*
25. Add `book/INDEX.md` doctrine map. *Exit: every PDF ↔ os.md / §9 line linked.*
26. Schedule P5–P12 as the following daily steps (Zone 0 gate → events/ledger
    → dispatch door → CIR executor → provenance ring → SIR core → diagnostic
    freeze → Phase III projection), each with its own witness before merge.
27. **Phase-1 exit review**: run the convergence test (§16) over the whole
    ladder; ledger the verdict; then open Phase 2 (parallel team nodes).

## §22 — The Economic Constitution (Fiqh al-Mu'amalat, merged from CONTEXT_ANCHOR)
The economic plane contains zero debt structures, speculative interest
tracking (riba), or ambiguous data-harvesting contracts. Value is generated
only through verified exchange channels:
- **Al-Ujrah (fee-for-service):** enterprise runtime licenses sold as flat,
  upfront, explicitly declared transactions with clear delivery metrics; no
  variable billing, no hidden clauses (niza' prevention). Enforcement point:
  the license verifier receipts each issuance into the ledger.
- **Al-Musharakah / Al-Mudarabah (risk-and-reward sharing):** P2P compute
  contributors (VCES matrix) share revenue proportional to verified thread
  execution times; nodes assume identical loss exposure; zero guaranteed
  margins. Enforcement point: the micro-metering ledger (energy-cost logs)
  is the only revenue input.
- **Al-Istisna' (pre-order fabrication):** custom edge firmware/robotics
  funded via transparent milestones linked to physical code deliveries.
  Enforcement point: milestone receipts gate payment events.
- **Al-Waqf / Fard Kifayah (public endowment):** the base portable C17 CLI
  toolchain remains open-source and free, un-manipulated, to the public
  domain.
Conventional-model refusals (already in §2.1): no riba-backed debt lines, no
vague subscription gating, no asymmetric data harvesting, no hallucinatory
performance claims — verifiable math and provenance traces only.

## §23 — Session Pre-Flight (extends §20; run in this order)
1. Tick every box of §20 from memory.
2. Economic vector: confirm today's change introduces no unpriced debt, no
   silent degradation, no probabilistic fallback (§2.1-II, §22).
3. Phase target: state which §21 step number this session executes; confirm
   step N−1's exit was verified (resume contract).
4. Anchor check: `CONTEXT_ANCHOR.md` is a stub; this file is the only anchor.
5. Run §17 ritual (before-state), do the step, run §17 ritual (after-state),
   ledger the outcome with `schema_version: 3` and the step number.
If any line fails: stop, record the debt, fix the precondition — never work
around it.

## §24 — Amendment Log
- 2026-10-27 · v2 · Merged CONTEXT_ANCHOR.md (§2.1 vectors, §6 thermodynamics,
  §22 economy, §23 pre-flight); added §21 Daily Sequence; §16 upgrade queue
  closed; §0/§18/§19 cross-references updated. Reason: single-source the
  constitution and bind daily work to exit-coded steps after the gen-3
  upgrade queue completed.
- Rule: every future amendment appends here with date + reason.
  Contradictions are resolved explicitly in §19 terms, never by silent edit.

Sealed. vision.md + README.md + os.md + qcos.cxn form the constitution of
this project. Code that contradicts them is a bug, however convenient.
— SaemLabs, QCOS Architect
