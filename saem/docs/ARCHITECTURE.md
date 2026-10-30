# Saem / QCOS architecture: the one picture

Written 2026-10-27, updated 2026-10-30 (the sovereign kernel v0 is built: see `docs/KERNEL_C17.md`). Marks: [done] exists and is tested, [next] is the next piece to build, [later] is planned. `python3 tools/where.py` is the truth about files; `python3 tools/check_c17.py` is the truth about the kernel.

## 1. The axiom, made structural

MEANING is not REPRESENTATION is not EXECUTION is not HARDWARE. Each level has its own code and a narrow interface to the next.

| Level | In our code | Rule |
|---|---|---|
| Meaning | the constitution articles; the semantic IR (SIR) [next] | machine-independent; exact integers and rationals; no floating point |
| Representation | bytes, JSON text, IR nodes | a request is only bytes until the gate accepts it |
| Execution | the sovereign kernel (C17) and the engines (C++17) | pure functions of (state, input, ticks); no clock, no RNG, no environment reads |
| Hardware | a platform table the caller fills: block device, tick source, threads | the core calls out through the table and knows no operating system |

## 2. Layers and the one door

```
 Python frontend  saem/              screens, files, routing. Standard library only. Decides nothing about truth.
        |  JSON text (saem_cli pipe now; C ABI through ctypes later)
 +------v-----------------------------------------------------------------------------+
 | SOVEREIGN KERNEL   core/c17/   C17, ZERO HEAP, static tables, atomics   [done] |   the "+1" core in the 4+1 plan
 |   cos_gate (Zone 0) -> [cos_sir: next] -> monitor -> cos_journal -> cos_seal         |
 |   cos_regs (32 working, 64 episodic)   cos_pool (lock-free, generation handles)      |
 +------+-----------------------------------------------------------------------------+
        |  only requests the gate accepted, as bounded typed arguments
 +------v-----------------------------------------------------------------------------+
 | ENGINES            core/src/   C++17, deterministic, standard library only           |   the "4" worker cores
 |   Math Brain (gen) [done]  Forecast (ef) [next]  Test machine (cbt) [next]  COS (cos) [next]   |
 +------+-----------------------------------------------------------------------------+
        |  C ABI (extern "C": saem_open / saem_call / saem_close), C# P/Invoke in interop/csharp/
```

A call: bytes -> gate -> engine -> independent check where one exists -> journal -> reply.
A reply is either `{"ok":true,"result":...}` or `{"ok":false,"error":"...","zone":"reject|quarantine|freeze"}`. There is no third form.

## 3. The Forbidden Zone has three outcomes

xv6 has one failure level (panic). A student on a phone must not lose a session because one input was odd, so we separate scope.

| Outcome | Scope | Triggers (examples) | Lifted by |
|---|---|---|---|
| Reject | one request | invalid UTF-8; invisible or direction-changing characters; too long; too deep; unknown method; a generated question whose exact recheck disagrees with its answer; a forecast whose back-test does not beat the plain baselines (shown as "no reliable forecast", never as a ranking) | nothing to lift; the next request is judged on its own |
| Quarantine | one method or source | repeated rejects from it; a failed verification | a person's approval (teacher), recorded in the journal |
| Freeze | the whole core | the constitution seal does not match; the journal chain is broken; an internal invariant broke (double free, corrupt generation) | a restart that re-verifies the seal |

## 4. Zero heap and zero global state, as checks not promises

- The sovereign kernel never allocates. The caller gives it memory: `cos_core_bytes()`, then `cos_core_open(mem, len, &config, &core)`. All capacities are
  compile-time constants in one header (`COS_WORKING_LIMIT 32`, episodic ring 64), with `_Static_assert` on every derived size.
- `tools/check_c17.py` fails if any c17 object imports malloc, calloc, realloc or free, if any c17 source contains `float` or `double`
  (zero numerical approximation), or if any object has a writable global symbol other than a documented constant.
- The engines move to handles (`saem_open/saem_call/saem_close`) and constant method tables; the global `Registrar` is a known deviation.
  Variable-size data later goes through a fixed arena (xv6's buddy allocator idea, with `std::pmr` in C++), so the memory ceiling is a number.

## 5. Concurrency

- A node owns its registers (L1, L2): one writer, no locks. Nodes talk through lock-free rings (sequence-numbered, free-running counters).
- Shared hot fields live on their own cache line (`alignas(64)`): the freeze flag, counters, pool head. Publication is release, reading is acquire.
- The pool is a tagged Treiber stack (index plus a counter in one 64-bit word) with a generation per slot, so reuse cannot confuse a stale handle.
- Contention is measured, as in the xv6 lock lab: failed compare-and-swap counts, a conservation check (every slot allocatable again afterwards).
- The journal has one writer at a time (a tiny `atomic_flag` lock, cold path). In the 4+1 hardware plan the sovereign core is that single writer.

## 6. Where each source feeds the design

| Source | Gives us | Lands in |
|---|---|---|
| xv6-RISC-V (`docs/knowledge/xv6.md`) | fixed tables, one door, commit-last, redo log, LRU cache, rings, boot protocol, adversarial tests | `core/c17/*` |
| Open Math Harness / Nucleus (`docs/NX_BRIEF.md`) | capabilities, bounded queues, journal, approvals, verification bound to a digest, memory levels | `core/src/nx/*` |
| Constitution of Medina (project document) | the content of the immutable core: articles, the Forbidden Zone, fairness among communities | `docs/CONSTITUTION.md` [next], sealed by `cos_seal` [done] |
| Project rules (instructions) | phases, invariants, Zone 0, SIR, 32 registers | this file, `cos_limits.h` |
| MIT OCW material in the project | method: read, build intuition, then the simplest sufficient code | every module's first comment |

## 7. Phases

1. Portable core baseline (now): C17 sovereign kernel plus C++17 engines on a phone or laptop, offline.
2. Parallel ed-tech team: each engine becomes a node with its own registers; rings between nodes; L3 knowledge atoms in SQLite behind the journal's block-device table.
3. Quantum Cognitive OS on open RISC-V "4+1": four worker harts in S-mode, one sovereign hart in M-mode holding the constitution under locked PMP entries (RISC-V privileged spec 3.6: locked entries change only at reset).
4. Air-gapped sovereign datacentre. 5. Peer-to-peer, debt-free compute marketplace under Halal trade terms (Al-Ujrah, Al-Musharakah, Al-Istisna').

## 8. Honest limits

- A software seal detects accidental or one-copy tampering. Real immutability is the hardware lock of phase 3. HMAC needs a provisioned key; a public-key signature (Ed25519) comes with phase 2.
- C# interop will be written without a compiler in this environment unless one can be installed: labelled unverified until compiled.
- The Python frontend, the forecast engine and the test machine still run on the JavaScript reference until their C++ ports and the interface are finished.
