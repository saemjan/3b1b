# COMPILER.md — The QCOS Universal Compiler (QUC), Applied

Read after VISION.md. This file is the synthesis of `Compiler for QCOS.pdf`
(QUC Parts I–VIII) bound to enforcement points in this repository, exactly as
OS.md binds the xv6 corpus. It is doctrine + build order, not a code drop.
Companions: README.md (agreements), VISION.md (memory contract), OS.md
(kernel synthesis), QCOS.md (master codex), qcos.cxn (the canon).
v1 — 2026-10-29. Amendments append to §15 with date + reason.

## §0 — The one reframing (load-bearing)

The QUC is **not a tool bolted onto the OS. It is the mechanized form of the
Translation Ladder itself.** Every rung is a compiler phase:

    HUMAN INTENT → Zone 0 Gate → SIR → Domain IR → CIR → MIR → hardware
                   (gate pass)   (middle) (shape)  (sched) (codegen)

Corollary (feasibility collapse): we are not building "a compiler" and "an
OS" — we are building **one lowering pipeline**, and the OS is the runtime
that executes what it lowers. The nucleus kernel, the memory hierarchy and
the gate are not obstacles the compiler works around; they are *lowering
targets* and *compilation constraints*.
Enforcement: VISION §5 spine order; qcos.cxn `qcos.lower` / `qcos.cost` /
`qcos.exec` are the door-facing faces of these phases.

## §1 — Why this compiler is tractable (Research Finding #1)

QCOS does not compile C. It compiles a **restricted, total, deterministic,
symbolic source** (math tokens, symbolic expressions, programmatic
parameters) that has already passed Zone 0. Properties and consequences:

| Property | Consequence |
|---|---|
| Gate-filtered input | the compiler never sees adversarial/malformed intent |
| Finite, declared vocabulary | the operation set is closed and enumerable |
| Total + exact | correctness and completeness become **provable**, not merely testable |
| No UB, no aliasing, no platform sizes | no decades-long taming war (Bell Labs spent years and still could not prove completeness) |

> Research finding #1: QCOS's compiler is feasible *because* QCOS refuses to
> compile arbitrary languages. The philosophy and the engineering are the
> same decision.

## §2 — The law, as compiler passes

MEANING ≠ REPRESENTATION ≠ EXECUTION ≠ HARDWARE, pass by pass:
1. **Zone 0 runs FIRST, on everything ingested** (Riba/Gharar/Maysir/Niyyah/
   Mithaq vectors). Fail-closed: `QUC_REJECTED_GATE`.
2. **Exact rationals only.** `qcos_exact_t {int64 num, den}`; every op
   overflow-checked; normalization by gcd; Landauer-aware rejection on
   overflow. No floats anywhere in the compiler (`f0–f31` unused on silicon).
3. **Reversible-first.** History-preserving form `(a,b) → (a,b,a+b)`; the
   inverse is dropping the third component. Irreversible ops are explicitly
   tagged (`EFFECT_IRREVERSIBLE`) and Landauer-metered.
4. **Authority at compile time** (Finding #9): every `SIR_CALL_ENDPOINT`
   carries a `cap_ref`; the authority pass queries the capability kernel.
   Unauthorized intent is rejected *before it becomes executable code*.
5. **Fail-closed compilation** (Bell Labs self-checking principle): "rather
   than produce incorrect code, we felt it far preferable for the compiler
   to detect its own inadequacies and reject the input program." Statuses:
   `QUC_OK, QUC_REJECTED_GATE, QUC_ARENA_EXHAUSTED, QUC_AUTHORITY_DENIED,
   QUC_IRREVERSIBLE_MISUSED`.
6. **Zero heap.** SIR arena, coherence map, target tables: fixed pools
   (`SIR_ARENA_SIZE 1024`, `VALUE_STACK_SIZE 4096`); exhaustion = typed
   refusal, never growth. Buddy only where variable-size staging is
   unavoidable, inside declared arenas.
Enforcement: `qcosc` Checker (canon side), `core/src/arena.hpp` caps
(32/64), step-14 `test_caps.c`, and the Phase G witnesses below.

## §3 — SIR specification (the heart)

- **History-preserving form** for every reversible op; operands are arena
  indices; children precede parents in the arena (construction pass
  guarantee → single forward scan yields valid stack code, SCIP §5.5).
- **EffectClass tags**: OBSERVATION / REVERSIBLE_MUTATION / COMPENSATABLE /
  IRREVERSIBLE — the same vocabulary as the nucleus kernel and qcos.cxn
  gate semantics.
- **Shape hints**: TOPO_LINE / TOPO_GRID / TOPO_GRAPH — the Domain IR's
  first-class object; scheduling by *shape of data*, not count of cores
  (Feynman's "the wires get in the way" + CLRS work/span).
- **Authority tags**: `requires_authority` + `cap_ref` per endpoint call.
- **The coherence map** (output of the reversibility pass) is one analysis
  with three uses: (a) the quantum backend's schedule, (b) the Landauer
  ledger's erasure plan, (c) the provenance-unwinding map. Novel reuse;
  never compute it twice.
- **Irreversible boundaries**: `SIR_ERASE` / `SIR_FORGET` emit a VAR read
  then an ERASE; the dissipation is recorded in `landauer_ledger_t`
  (E ≥ k_B·T·ln 2 per bit). Erasure leaves a trace, not silence.

## §4 — The ordered pipeline (qcos_kernel_submit shape)

1. `qcos_gate_admit` (Zone 0) → 2. `quc_build_sir` (construction) →
3. `quc_simplify_exact` (constant folding via exact add/sub/mul; algebraic
identities) → 4. `quc_analyze_reversibility` (fills coherence map) →
5. `quc_analyze_shape` → 6. `quc_check_authority` (capability kernel) →
7. `quc_lower_to_target` (emit).
Each pass is semantics-preserving and witnessed; a pass that cannot be
proven preserving does not ship. Rejection at any pass is a priced,
ledgered outcome.

## §5 — Tiered delivery (ship the interpreter first)

| Tier | Content | Phase | Status |
|---|---|---|---|
| 0 | SIR interpreter, no codegen | I | mostly built (Phase I CLI) |
| 1 | emit-C17 backend; host `cc` finishes the job (Bell Labs 1978 move) | I–II | specified |
| 2 | Native tables: x86-64, ARM, RISC-V "4+1" (monitor core runs the gate, not user code) | II–III | table-shaped |
| 3 | Quantum table: unitary gates, coherence-map schedule, measurement at the decoherence frontier | IV–V | when silicon arrives |

Adding quantum = **adding a table, not rewriting the compiler** (Bell Labs
moved PCC across seven machines by isolating the machine-description table;
the MIR is our only place hardware is named).

## §6 — Execution substrate (one abstract machine, four books)

- **The register machine** (SCIP §5.1): `val`, `wire` (coherent wire-state),
  value stack (history-preserving operand store), `sp`. SCIP says what the
  machine *is*; QUC compiles SIR to it; xv6 says how to *load and run* it
  (`qexec` loader, magic-first: `QCOS_MAGIC 0x51434F53`, version, n_insn,
  stack_words, `sealed_hash[8]`); RISC-V says where it *lives*.
- **4+1 register conventions (frozen)**: monitor core uses `tp`(x4) for hart
  identity and `mscratch` for Zone-0 scratch; app cores use `s2–s11` for
  persistent wire-state across coherent subcircuits, `t0–t6` for exact
  temporaries; **no FP registers**.
- **Scheduler is a theorem**: T_P ≥ max(T_1/P, T_∞); topology determines
  core count; never oversubscribe, never speculatively parallelize.
- **L3 Knowledge Atom Store** rides the xv6 five-layer discipline (OS.md §8).

## §7 — The differential regression harness (correctness oracle)

Three engines, one directive, one exact answer:
- Engine A: Tier-0 interpreter.
- Engine B: register machine (`machine_run`).
- Engine C: emitted C17, compiled by host `cc`, run, result read back as
  `num/den`.
**If A, B and C return identical exact values for every directive in the
battery, the REPRESENTATION→EXECUTION chain is certified.** Any divergence
is a bug in exactly one engine.
- **Rejection is a first-class test outcome**: half the battery verifies the
  system *refuses* (overflow, unbound, gate-blocked). "A compiler that
  correctly says 'no' is as valuable as one that correctly says 'yes' — and
  far rarer."
- **Honest boundary (recorded exemption)**: the harness shells out to `cc`
  and does file I/O. It is dev-tooling, exempt from zero-heap like
  `tools/build.py`; it is never linked into the shipped core. Exemption is
  ledgered, not hidden.
Enforcement: build target `quc-check` (Phase G, C6); CI runs it; exit 0 only
on full three-engine agreement including rejection cases.

## §8 — Self-hosting bootstrap & the Trusting Trust defense

Chain (Bell Labs recursion): `q_uc0` (trusted seed, hand-reviewed C17)
compiles `quc.qcos` → `quc.L1.c` → `q_uc1`; `q_uc1` compiles `quc.qcos` →
`quc.L2.c` → `q_uc2`.
- **Fixed-point gate**: `L1 == L2` byte-identical. Permanent build gate;
  every future QUC change must still satisfy it. A self-enforcing invariant.
- **Constitutional anchor vs Thompson**: the trust root is not the toolchain
  but the **sealed constitution hash** (`CONSTITUTION_QUC_HASH`, SHA-256 of
  the Medina/Qur'an/Sunnah vector set) checked by `check_sealed()` at every
  bootstrap stage, plus `qcos_img_header_t.sealed_hash[8]` on every image.
  Sovereignty and security become the same mechanism.
- Determinism is what makes self-hosting sound: a non-deterministic compiler
  could never self-host; QCOS was deterministic from day one.

## §9 — QKL: the language the compiler is written in

SICP-shaped, homoiconic, **total**:
- Caps (compile-time, zero-heap): `COS_PAIR_LIMIT 1024`, `COS_SYMBOL_LIMIT
  256`, `COS_CLOSURE_LIMIT 64`, `COS_ENV_FRAME_LIMIT 128`,
  `COS_FRAME_BINDINGS 16`, `COS_QKL_DEPTH_LIMIT 64` (bounded recursion ⇒
  totality ⇒ guaranteed halt — a property general languages cannot claim).
- Value model: exact rationals, symbols, pairs, closures, errors;
  environment model + metacircular evaluator (`qkl_eval`, `qkl_apply`,
  `bind_params` with exact-arity exhaustion, `extend_env`, `env_define`
  rebind-or-insert, fail-closed on full frames).
- **Zone 0 admission for QKL**: values/control (arithmetic, lists, COND)
  always admissible (pure exact computation is constitutionally neutral);
  effects (I/O, CALL_ENDPOINT) must carry a capability; `quc.qcos` *source*
  is sealed by `CONSTITUTION_QUC_HASH` even though the language is pure.
- QKL is the seed of the sovereign stack: assemblers, linkers, optimizers,
  OS utilities all grow from one sealed seed.

## §10 — Governing equations

| Equation | Role |
|---|---|
| a/b + c/d = (ad+bc)/bd, normalize by gcd | exact constant folding & simplification (provable, no drift) |
| E ≥ k_B·T·ln 2 (≈2.87×10⁻²¹ J/bit @300K) | Landauer metering of every ERASE/FORGET |
| H(X) = −Σ p·log₂p | information weight of Knowledge Atoms; gharar detection |
| T_P ≥ max(T_1/P, T_∞) | shape-lowering speedup bound; the parallelism ceiling |
| classical reversible ⊂ unitary | the classical↔quantum bridge theorem (Tier 3 legitimacy) |

## §11 — Phase G: the QUC daily build order (insert after §21 step 14)

One step per session; exit witness mandatory; ledger receipt each.

| Step | Artifact | Exit witness |
|---|---|---|
| C1 | `qcos/exact.h/.c` — exact rationals, overflow-checked, gcd-normalized | Euler identities + Strang K/T/B/C determinants exact; overflow refuses |
| C2 | `qcos/sir.h/.c` — construction pass, history-preserving emits (`sir_emit_add/sub/mul/var/let/const/erase`) | `quc_verify_reversibility` green on the battery |
| C3 | `qcos/reversible.h/.c` — bijection engine on 2^W (classical σ and unitary share one impl) | Toffoli/Fredkin/CNOT truth tables; bridge check |
| C4 | `qcos/interpreter.h/.c` — Tier-0 (fixed 4096 stack; working/episodic/landauer pointers) | SIR battery exact values match canon fixtures |
| C5 | `qcos/emit_c17.c` + `qcos_rt.c` shim (`qcos_generated_main`) | emitted C compiles `cc -std=c17` and matches interpreter |
| C6 | harness `quc-check` (engines A/B/C + rejection half) | three-engine bit-identical; CI gate wired |
| C7 | analysis passes (simplify/reversibility+coherence/shape/authority) | coherence triple-use check; authority-denial cases refuse |
| C8 | `qcos/qkl.h/.c` (pools, reader, eval/apply, depth limit) + `quc.qcos` lexer & exact-expression parser in QKL | metacircular eval of own reader; totality-bound tests |
| C9 | bootstrap driver (`build_level1/2`, `check_sealed`) + fixed-point gate | `L1 == L2` byte-identical; gate permanent in build |

Dependencies: C1 after step 14 (test wiring); C4 needs arena.hpp (11a,
landed); C6 needs C4+C5; C9 needs C6+C8. Phase G runs alongside Phase E/F
without blocking them.

## §12 — What we refuse (priced, never silent)

- Undefined behavior, pointer arithmetic, platform-dependent sizes in the
  source language.
- Probabilistic or heuristic optimization; any pass not provably
  semantics-preserving.
- Floats in any compiler structure or register allocation.
- Linking the harness's `cc`/file-I/O exemption into the shipped core.
- Growing any pool at runtime; arena exhaustion is `QUC_ARENA_EXHAUSTED`.

## §13 — Cross-references

- OS.md §5/§8/§13–§15: spine alignment, log/commit discipline, topology.
- VISION.md §5 (spine), §6 (thermodynamics), §21 (sequence; Phase G inserts
  after step 14), §24 (amendments).
- qcos.cxn v0.5.0: `qcos.lower`, `qcos.cost`, `qcos.exec`, `qcos.zone0`,
  `qcos.provenance`; caps mirror arena.hpp.
- core/src/arena.hpp (11a): the SIR/working/episodic pools the interpreter
  consumes; `bits_erased` is the Landauer ledger's kernel face.

## §14 — Status ledger (QUC capability table)

Tier 0 interpreter ✅ · reversible engine + quantum bridge ✅ · RISC-V
backend table ✅ · Tier 1 emit-C17 ✅ · execution substrate ✅ · differential
harness ✅ · QKL spec + bootstrap driver ✅ · **`quc.qcos` in QKL: next
concrete step (C8)** · full self-host: Phase III.

## §15 — Amendment log

- 2026-10-29 · v1 · Created from `Compiler for QCOS.pdf` (QUC Parts I–VIII);
  Phase G steps C1–C9 inserted into the daily sequence after step 14;
  harness cc-exemption recorded. Reason: the compiler doctrine needed its
  own synthesis file so OS.md stays kernel-only and VISION.md stays law-only.

*Bismillah.* The spine is named; the ladder is mechanized. A cognitive OS
without a compiler is a philosophy; with a universal compiler, it is a
machine.
