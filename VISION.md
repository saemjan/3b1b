# vision.md — The Sovereign Reference of the QCOS Project

> **Read this first. Every session. Every task. Every file.**
> This document is the master index of everything held in memory: the mission,
> the law, the constitution, the absorbed doctrine, the build contract, the
> gates, the rituals, and the queue. `README.md` is the repository-facing
> constitution; `os.md` is the kernel synthesis; **this file is the memory
> contract** — the checklist run before any work begins.

Companion documents: `README.md` (working agreements), `os.md` (xv6/RISC-V
synthesis + P0–P12 construction plan), `qcos.cxn` (the canon),
`knowledge_base/` (witnessed curriculum), `logs/*.jsonl` (the ledger union).

---

## §0 — Purpose of this file

1. **Single point of recall.** Everything decided, absorbed, or sealed lives
   here as an index entry with its enforcement point in code.
2. **Session-start gate.** §20 is a mandatory checklist; no work begins until
   it is satisfied from memory.
3. **Drift detector.** If a new decision contradicts an entry here, the entry
   is amended explicitly (with date and reason) — never silently overridden.

---

## §1 — The Mission and the Three Phases

We build **QCOS**: a sovereign, non-connectionist, deterministic cognitive
operating system that teaches physics and mathematics the Feynman/3b1b way,
for NEET · JEE · MIT aspirants.

| Phase | Target | Convergence test | State |
|---|---|---|---|
| **I** | Pure, standalone, memory-safe **C17 CLI**, zero external deps; Python orchestration edge for the video factory | every number computed & witnessed; every look novel; every gate machine-checked | **in progress** |
| **II** | Parallel **ed-tech model team**: many stateless nodes over one core, SPSC rings, claim/complete dispatch | nodes liftable into parallel workers without refactoring | planned |
| **III** | **4+1 RISC-V**: +1 isolated core (M-mode, physical memory) runs Zone 0 + crypto; 4 app cores run bounded data matrices | bring-up witnesses pass on hardware/QEMU | projected |

**Why C / C++ / C# core:** deterministic memory, zero-overhead abstractions,
stable FFI floor, native concurrency — the phase shift 1→2→3 must never break
the foundation. **Python never owns truth**; it orchestrates, gates, receipts.

**Audience promise (the Teacher Rule):** same physics, never the same lesson
twice — truth frozen, representation alive (§13).

---

## §2 — The Ethical Root: Constitution of Medina → Zone 0

The Medina charter is the ethical substrate of the constitutional gate:
one community, explicit covenants, mutual defense, no hidden allegiance.
Zone 0 encodes it as deterministic vectors checked on every intent:

- **Niyyah (intention):** declared purpose must match the operation; no
  hidden routes, no side channels, no undeclared effects.
- **Shari'ah bounds:** mechanics of riba (unearned increment), gharar
  (deceptive uncertainty), maysir (gambling on outcomes) are refused —
  in code: no unpriced debt, no silent degradation, no probabilistic fallback.
- **Mithaq & Sidq (covenant & truthfulness):** byte-for-byte parity across
  all four tongues; a node that cannot prove its words keeps silent
  (fail-closed), never approximates.

Zone 0 sits before SIR in the spine (§5) and blocks recursive self-mutation
and memory breaches absolutely.

---

## §3 — The Law

**MEANING ≠ REPRESENTATION ≠ EXECUTION ≠ HARDWARE.**

- Meaning = canon (`qcos.cxn`), articles, exact rational mathematics.
- Representation = emitted bindings, genomes, skins, narration rhetoric.
- Execution = CIR schedules, bounded steps, claim/complete dispatch.
- Hardware = C17 freestanding core now; RISC-V 4+1 later.

A change at one layer must never silently mutate another. Parity gates
(`qcosc --handshake`, `parity_line`, `canon_lint`) enforce the separations.

---

## §4 — The Four Invariants (mechanically enforced)

| # | Invariant | Enforcement |
|---|---|---|
| 1 | **No connectionist logic** | symbolic/exact only; belief = integer tally at 1000:1 (A4), never float probability; XTTS/ASR/manim are edge devices, their outputs are measured data, never logic |
| 2 | **Zero-heap deterministic memory** | `COS_WORKING_LIMIT 32`, `COS_EPISODIC_LIMIT 64`; static arenas; exhaustion = `QCOS_ERR_BUDGET_EXHAUSTED`, never growth |
| 3 | **Fail-closed discipline** | uncertainty (non-finite, cap breach, missing provenance, id-echo mismatch, wrong mode) → task rejection or absolute node freeze; report debt, then halt |
| 4 | **Immutable constitution** | `SAEM_SOURCE_ID` + canon hash + handshake + append-only ledger = integrity monitor; mutation trips it |

---

## §5 — The Translation Spine

```
Human Intent → Zone 0 (ethical gate, §2)
             → SIR  (Semantic IR: exact rational matrices, int64 num/den, NO floats)
             → DIR  (Domain IR: masks, populations/Shape, topologies LINE|GRID|GRAPH)
             → CIR  (Execution IR: bounded sequential schedules, fixed loop horizons)
             → MIR  (Machine IR: bare-metal micro-ops, C17 now, RISC-V later)
```

Each lowering is deterministic and auditable; each layer's output is the next
layer's frozen input. Floats may appear only at the render/representation edge.

---

## §6 — The Execution Protocol

- **O(N) deterministic literal scans** over arrays; no hash tables, no
  next-token lookups, no learned indices.
- **Exact tracking provenance at every state transition** — reversible-logic
  paradigm: (step, op, keys, pre_hash) recorded into fixed rings/ledger.
- **Explicit byte-for-byte buffer copies** using hard static structs; no
  aliasing across boundaries; copy-only crossings (copyin/copyout doctrine).
- **No third-party analytics, networking packages, or probabilistic
  approximations** inside the core. Networking exists only at the host edge
  (door protocol), receipted.
- **Bounded horizons everywhere:** timers re-arm; writes chunk to transaction
  size; loops carry fixed counts; waits re-check condition + killed.

---

## §7 — The Topologies

- **Phase I:** freestanding C17 CLI. One cooperative dispatch loop. Linker-
  carved arenas. JSON lines over stdio as the door. Diagnostics survive init
  failure (early-write path).
- **Phase III:** 4+1 RISC-V. +1 core: M-mode, no MMU (physical memory), owns
  Zone 0, crypto, global event priorities (`medeleg/mideleg` as its filter),
  UART diagnostics. 4 app cores: S-mode, per-core buddy-discipline arenas,
  per-core PLIC enable/threshold, inter-core SPSC rings with virtio semantics
  (publish → notify → sleep → reclaim; index-as-identity; in-band status
  verification — the envelope alone never authorizes a commit).

---

## §8 — Constitution Articles & Caps

- **A0** computed, never guessed · **A1** numbers print exactly as the ruler
  prints them · **A2** door holds no hidden state · **A3** measurement and
  overwrite are the only irreversible acts; debt is reported · **A4** no belief
  without 1000:1 moral certainty · **A5** ledger append-only; unwitnessed rules
  are hypotheses · **A6** the JS bridge is a ruler, never a fallback.
- Caps (declared once in `qcos.cxn`, enforced by `qcosc` Checker):
  `WORKING 32 · EPISODIC 64 · MAX_DELEGATION 8 · MAX_ACTIONS 64 · NAME_MAX 64`.
- **Generated files are law-bound:** never edit `*.g.cpp/*.g.py/*.g.cs/*.gen.js`;
  edit `qcos.cxn`, re-run `qcosc`. Deferrals and canonization queues are priced
  data with expiry dates (`tests/corpus/deferred.json`, `canon_queue.json`).

---

## §9 — Doctrine Library (absorbed texts → enforced patterns)

| Source | Doctrine now enforced |
|---|---|
| **Constitution of Medina** | Zone 0 vectors (§2); community-as-contract; explicit covenants |
| **Euler, *Elements of Algebra*** | exact rational arithmetic; closed-form identities as witnesses (Vieta, binomial sums, series closed forms, continued-fraction exactness) |
| **Strang, *Computational Science & Engineering*** | stability guards (dt·ω inside method regions); K/T/B/C difference-matrix determinants as frozen rulers; Simpson/Richardson convergence; CFL-style fail-closed step budgets |
| **xv6 book (rev 7)** | layering; two-level locking; bounded buffers; sleep = lock handoff; monotonic ids; ZOMBIE two-phase completion; claim/complete; log = single commit point + boot recovery; panic = report + freeze; guard pages; lifecycle comments as constitutions |
| **RISC-V book (rev 5)** | 4+1 substrate; privilege delegation as event filter; per-hart arenas; `tp` node address; trapframe as provenance record; Sv39 walk as single translation chokepoint |
| **Juhász, *Modern C in Embedded Systems*** | zero-overhead abstractions; constexpr/consteval where the compiler can execute; RAII + lock-free handoff at the C++ seam; no hidden cost |
| **QCOS master spec** | spine, invariants, topologies, execution protocol (§3–§7) |

Full file-by-file extraction lives in `os.md` §1–§15.

---

## §10 — Substrate Inventory (fully absorbed, kernel complete)

Batches 1–10: kernel.ld, kernelvec.S, bio.c, buddy.c, buf.h · console.c,
date.h, defs.h, elf.h, entry.S · exec.c, fcntl.h, file.c, file.h, fs.c ·
fs.h, kalloc.c, list.c, log.c, main.c · memlayout.h, param.h, pipe.c,
plic.c, printf.c · proc.c, proc.h, ramdisk.c, riscv.h, sleeplock.c ·
sleeplock.h, start.c, stat.h, string.c, swtch.S · syscall.c/h, sysfile.c,
sysproc.c, trampoline.S · trap.c, types.h, uart.c, virtio.h, virtio_disk.c ·
vm.c. **Status: COMPLETE.** Remaining kernel-side work is synthesis
(`os.md` P0–P12), not absorption.

Project-side absorbed & gen-3 upgraded: engines (physics_simulation,
calculus, electromagnetics, geometry, linear_algebra, rotational, fluid,
jee_model_engine), render_universal, audio chain (text_normalizer,
soundscape, sound_design, generate_audio), gates (schema_validator,
physics_oracle, visual_qa, word_sync), factory (factory_input, author,
extract_feynman), witnesses/tools (ledger, golden_qcos, parity_line,
engine_check, check_all, canon_lint, backend_policy, style_genome,
style_belief, style_gate), core tongues (build, qcosc, saemc,
qcos_handshake).

---

## §11 — The Gen-3 Contract (how every file is built or upgraded)

1. **Pure stdlib ruler first** — correctness core needs nothing external.
2. **Selected libraries only via `backend_policy`**: probe → witness (parity
   vs ruler on frozen fixture) → cost → pin (`SAEM_BACKEND`) → record →
   degrade (fall back to ruler, reason recorded).
3. **Headless-importable** — no manim/numpy/torch at module top; lazy inside
   route/build functions.
4. **ROUTE_TABLE v1** for visual engines: `ROUTE_TABLE[type] = fn(scene, spec)`;
   skin from `scene.ctx` (genome); explicit `spec["color"]` = teacher override.
5. **Frozen witnesses**: `selftest() -> [(name, ok, detail)]` with closed-form
   rulers; `--selftest` CLI exits non-zero on drift.
6. **Receipts**: schema-stamped append-only ledger line per run
   (`schema_version: 3`, gate, backend, digests, debt).
7. **Determinism + fail-closed guards**: same input → same bytes; guards raise
   structured errors; unknown input refused, never interpolated.
8. **Degradation, not deception**: skips/fallbacks recorded in report+ledger.
9. **Truth frozen, representation alive** (§13).
10. **One canon per quantity** (§14).
11. **Stateless & flat**: pure functions, JSON-serializable I/O, C-struct-
    friendly payloads — Phase-2 liftable without refactoring.

New-file checklist (CI-enforced): docstring stating layer & stance · stdlib
top imports · validation helpers · pure ruler · optional gated backend ·
ROUTE_TABLE if visual · selftest · `__main__` runner · ledger receipt · no
global mutable state.

---

## §12 — The Gate Ladder (nothing ships unjudged)

```
Gate 0 schema → Gate 1 oracle → Gate 2 core-id → Gate 3 audio
→ Gate 4 render → Gate 5 QA → Ledger receipt
Witness phase: engine_check → golden_qcos → parity_line → canon_lint
→ qcos_handshake → check_all → ledger verify → style_gate
```
Exit codes are law: **0 truth holds · 1 drift/fail · 2 environment**
(rebuild/install; never re-record on 2). Promotions: `--require-schema`,
`--require-oracle`, `--require-core`, `--require-qa`, `--require-routes`,
`--require-novelty`, `--strict`.

---

## §13 — The Teacher Rule (truth frozen, representation alive)

- Style genome (palette/layout/motion/entrance/voice/pace/stroke/fonts/camera)
  derived per `(content, topic, audience, generation)`; novelty distance
  ≥ 0.35 vs recent ledger genomes; `style_gate` fails clone batches.
- Beliefs over genes: log-odds per QA outcome; promotion only past 1000:1
  (A4); next batch explores the least-certain gene.
- Narration rhetoric follows the genome voice grammar; durations retune to
  **spoken** words.
- Witnesses, rulers, canon, caps, LUFS/peak targets: **frozen forever**.
  Looks, order, timbre, pacing, quiz emission: **evolve every lesson**.

---

## §14 — The One-Canon Rule (single ruler per quantity)

| Quantity | The ruler |
|---|---|
| Spoken word count | `text_normalizer.spoken_word_count` |
| Expression policy | `calculus_engine.compile_expression` |
| Primitive vocabulary | `schema_validator.KNOWN_PRIMITIVES` ∩ routed set (`engine_check` parity) |
| Source fingerprint | `tools/build.py source_id` |
| Number printing | `jsnum`/canon (A1) |
| Duration band | `factory_input.retune_duration` (shared by author/schema/oracle) |

Two rulers for one quantity = bug. New quantities get a ruler before use.

---

## §15 — The Upgrade Ritual (per legacy file handed in)

1. **Audit table**: purpose + defects vs Gen-3 contract, severity per defect.
2. **Gen-3 rewrite**: preserve public API signatures; apply §11 in full.
3. **Integration notes**: patches for `batch_runner` / `engine_check` /
   `check_all` / workflow / ledger union.
4. **Verify commands**: exact, runnable, exit-coded.
Nothing merges without its `selftest()` green and its parity witnesses closed.

---

## §16 — The Queue & Roadmap

**Upgrade queue (next):** `think_loop.py` → `grow.py` → `auto_fixer.py` →
`ref_bridge.js` → `ref_bridge_qcos.js` → `bench_render_backends.py`.
**Then:** kernel synthesis `os.md` P0→P12 (MIR floor → byte primitives →
static arena → object slots → capability kernel → Zone 0 → events/ledger →
dispatch door → CIR executor → provenance ring → SIR core → diagnostic
freeze → Phase III projection).
**Phase exits:** Phase 1 = all engines gen-3 & witnessed, ladder green,
novelty enforced, ledger union complete, curriculum fully model-linked.
Phase 2 = stateless receipted nodes + SPSC rings + team scheduler.
Phase 3 = C17 kernel boots on RISC-V; Zone 0 on +1 core; monitors freeze on
breach; P0–P12 witnessed.

---

## §17 — The Verification Ritual (run before and after every change)

```bash
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
```

---

## §18 — The Memory Protocol (save / resume)

- **At pause:** record phase status, upgraded-file inventory, open witnesses,
  queue position, canon/cap changes, and any deferred/expiring entries.
- **At resume:** run §20 checklist, then §17 ritual, then continue queue.
- **Amendments:** changes to this file carry date + reason; contradictions
  are resolved explicitly in §19 terms, never by silent edit.

---

## §19 — The Never-Change List

`qcos.cxn` as single canon · append-only ledger · no hidden state in doors ·
exit-code contract 0/1/2 · frozen witnesses & rulers (§14) · caps (§8) ·
fail-closed on uncertainty · copy-only boundary crossings · monotonic ids ·
degradation always recorded · Medina vectors in Zone 0 · C/C++/C# as the
unbreakable core floor.

---

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

**If any box cannot be ticked from memory: re-read the cited section before
proceeding. Work begun without this checklist is out of constitution.**

---

*Sealed. vision.md + README.md + os.md + qcos.cxn form the constitution of
this project. Code that contradicts them is a bug, however convenient.*
*— SaemLabs, QCOS Architect*
