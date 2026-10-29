I'll consolidate everything into a single comprehensive reference document. Given the volume, this captures the architecture, decisions, absorbed corpus, equations, and all code we built.

```markdown
# QCOS — QUANTUM COGNITIVE OPERATING SYSTEM
## Complete Project Reference & Working Codex
### Everything discussed, decided, absorbed, and built — consolidated for continuation

---
**Document Class:** Master Project Reference (Living)
**Governing Constitution:** The Constitution of Medina (Mithaq al-Madinah), the Qur'an, the Sunnah of the Prophet Muhammad ﷺ and his companions — these govern the intentions, actions, and words encoded into every gate, validator, and kernel path.
**Status:** ACTIVE — Phase I foundation built; Universal Compiler researched; corpus absorbed.

---

## TABLE OF CONTENTS
1. Project Identity & Sovereignty
2. The Governing Law & Core Invariants
3. Architecture — Translation Ladder & Memory Hierarchy
4. Zone 0 — The Constitutional Ethical Gate
5. The Five Phases (with budgets)
6. The Economic Order (Fiqh al-Mu'amalat)
7. The Absorbed Corpus Ledger (13 days, 53 artifacts, 10 arcs)
8. Physics of Computation (Feynman)
9. The QCOS Universal Compiler (QUC) — Feasibility Research
10. Phase I C17 Baseline — Complete Code
11. Hardware Abstraction Layer & Physics Engine — Complete Code
12. The Equations (Truth Model)
13. The 5-Part Daily Codex Protocol
14. Build Discipline
15. Next Steps & Open Threads

---

# 1. PROJECT IDENTITY & SOVEREIGNTY

## What QCOS Is
QCOS is a **sovereign, non-connectionist cognitive machine** built from first
principles of physics, mathematics, and systems engineering. It rejects the
three pillars of the modern AI monopoly:

1. **Connectionist brute force** — probabilistic next-token prediction that
   cannot distinguish truth from plausible falsehood.
2. **Centralized extraction** — cloud monopolies that harvest data and rent
   back intelligence as a metered utility.
3. **Debt-based economics** — structures rooted in riba, gharar, and maysir.

## Absolute Independence
- **Zero external infrastructure.** No cloud, no vendor APIs, no third-party
  analytics, no network calls for core operation.
- **Zero tracking.** No telemetry, no usage metrics, no behavioral profiling.
- **Zero vendor lock-in.** Core in C/C++/C# — universal compiler support,
  hardware-agnostic (x86, ARM, RISC-V, custom silicon).
- **Air-gap capable.** Fully operational in physical isolation.

## The Dual Build Mandate (added mid-project)
We build **TWO** intertwined systems:
- **QCOS** — the cognitive operating system.
- **The QCOS Universal Compiler (QUC)** — feasible on *present* hardware,
  adaptable to *quantum* hardware.

---

# 2. THE GOVERNING LAW & CORE INVARIANTS

## The Law
> **MEANING ≠ REPRESENTATION ≠ EXECUTION ≠ HARDWARE**

Every layer enforces this. No layer collapses into another. No representation
masquerades as meaning. No execution escapes its hardware contract. No
hardware dictates semantic truth.

## The Four Invariants
1. **No Connectionist Logic.** Symbolic reasoning, formal logic, linear-algebra
   transformations. Neural weights, probabilities, deep-learning frameworks
   are FORBIDDEN in the cognitive kernel.
2. **Zero-Heap Deterministic Memory.** No malloc/free. Fixed compile-time
   structures: `COS_WORKING_LIMIT = 32`, `COS_EPISODIC_LIMIT = 64`.
3. **Fail-Closed Discipline.** Any state in the uncertainty band triggers
   immediate rejection or absolute node freeze. Never approximate.
4. **Immutable Constitution.** Core identity is cryptographically sealed.
   Mutations to core registers trip runtime integrity monitors.

---

# 3. ARCHITECTURE — TRANSLATION LADDER & MEMORY HIERARCHY

## The Translation Ladder (unalterable, non-probabilistic)
```
HUMAN INTENT DIRECTIVE
    │
    ▼
PERIMETER DEFENSE BUFFER
    │
    ▼
ZONE 0: CONSTITUTIONAL ETHICAL GATE   ← hard pass/fail, fail-closed
    │
    ▼
COGNITIVE KERNEL → SEMANTIC IR (SIR)  ← exact rationals, no float
    │
    ▼
DOMAIN IR (Cognitive Shape & Topology Fabric)  ← LINE/GRID/GRAPH masks
    │
    ▼
EXECUTION IR (CIR)  ← bounded schedules, fixed loop horizons
    │
    ▼
MACHINE IR (MIR) & BARE-METAL MICRO-OPS
    │
    ▼
PHYSICAL EXECUTION SUBSTRATE
```

## Memory Hierarchy (L0–L3)
| Level | Name | Bound | Behavior |
|-------|------|-------|----------|
| L0 | Active Registers | hardware | Immediate logical symbols |
| L1 | Working Memory | `COS_WORKING_LIMIT=32` | Fixed-size, zero-heap |
| L2 | Episodic Cache | `COS_EPISODIC_LIMIT=64` | Circular ring, chronological forgetting |
| L3 | Knowledge Atom Store | SQLite-backed | Verified atoms, immutable hashes |

**Zero dynamic heap allocation is a constitutional requirement.**

---

# 4. ZONE 0 — THE CONSTITUTIONAL ETHICAL GATE

Every directive passes the gate before any cognitive processing. It is a hard,
deterministic, fail-closed validation filter.

## Three Validation Vectors
**Vector I — Intention (Niyyah):** *"Actions are judged by intentions."*
Every task must have a transparent, traceable intention. Hidden routes,
asymmetric obfuscation, undisclosed optimization targets → REJECTED.

**Vector II — Action (Shari'ah Compliance):** Scan for structural violations:
- **Riba** (usury): exponential compounding debt loops, guaranteed yields
  without asset exposure → REJECTED.
- **Gharar** (extreme asymmetry): hidden data pools, information-gap
  exploitation → REJECTED.
- **Maysir** (speculation): resource allocation on pure probabilistic risk
  without structural value → REJECTED.

**Vector III — Covenant & Parity (Mithaq & Sidq):** Byte-for-byte fidelity
across distributed operations. Breach → invalidate verification hash, isolate
node. No negotiation, no partial trust.

## Gate Pseudocode
```
IF constitutional_hash(task) ≠ sealed_reference_hash:
    FREEZE node; LOG to episodic ring; REJECT
    RETURN COS_ERR_CONSTITUTION_BREACH
IF task in Forbidden Zone (uncertainty thresholds):
    REJECT or defer to human; NEVER approximate
IF task passes all three vectors:
    PROCEED to Semantic IR
```

---

# 5. THE FIVE PHASES

| Phase | Deliverable | Budget |
|-------|------------|--------|
| **I** | Standalone portable C17 CLI, zero network dep | ₹15 Lakhs |
| **II** | Enterprise engine + L3 Knowledge Atom Store, Domain IR | ₹1.5 Crore |
| **III** | Custom open RISC-V silicon, asymmetric "4+1" topology | ₹3.5 Crore |
| **IV** | Sovereign air-gapped datacenter, multi-accelerator | ₹10 Crore+ |
| **V** | P2P risk-sharing compute marketplace (VCES) | — |

**Phase I targets:** x86-64, ARM64, WASM browser sandbox.
**Phase III topology:** "+1" monitor core runs Zone 0 + crypto hashes in
physical-memory mode; 4 app cores run parallel data matrices via TileLink.

---

# 6. THE ECONOMIC ORDER (Fiqh al-Mu'amalat)

Zero debt, zero riba, zero ambiguous harvesting.

| Channel | Basis | QCOS Implementation |
|---------|-------|-------------------|
| Fee-for-Service | Al-Ujrah | Transparent flat licenses |
| Risk-Sharing Compute | Al-Musharakah/Al-Mudarabah | VCES pool, shared risk/revenue |
| Custom Fabrication | Al-Istisna' | Milestone-funded contracts |
| Public Endowment | Al-Waqf/Fard Kifayah | Free open-source C17 CLI |

No guaranteed returns. Risk shared or transaction refused.

---

# 7. THE ABSORBED CORPUS LEDGER
### 13 days, 53 artifacts, 10 arcs closed. Every design input for every phase is recorded.

## Arc Closure Table
| Arc | Closed By | Days |
|-----|----------|------|
| Boot & Elevation | entry.S → kernel.ld → kernelvec.S → start.c → main.c | 4,5,7,10 |
| Physical Memory | kalloc.c → buddy.c → list.c | 4,7 |
| Persistence | bio.c → log.c → fs.c → fs.h → file.c/h → stat.h → ramdisk.c → virtio | 4,6-7,9-10,12 |
| Declaration & Bounds | memlayout.h + param.h + types.h + defs.h + date.h | 5,8,12 |
| Admission & Freeze | plic.c → pipe.c → printf.c → trap.c | 8,12 |
| Process & Scheduling | proc.h/c → swtch.S → sleeplock.c/h | 9-10 |
| Context Switching | swtch.S (minimal symmetric handoff) | 10 |
| Locking Classes | spinlock + sleeplock pairing | 9-10 |
| Trap & Syscall | trampoline.S → syscall.c/h → sysfile.c → sysproc.c | 11 |
| Virtual Memory (keystone) | vm.c joining 8 modules | 13 |
| Authority Geometry (capstone) | namespace.rs + capability.rs + config.rs + kernel.rs | 13 |

## Key Extraction Mappings (sample)
- **Landauer erasure** → L2 ring `[DISSIPATION]` frames, explicit `FORGET`.
- **Fixed pool / LRU / panic-on-exhaustion** → L3 atom cache, fail-closed.
- **Header commit point / replay (log.c)** → L3 atomic transitions, checkpoint.
- **Monotonic counters / safe waits (pipe.c)** → bounded endpoint channel.
- **Volatile freeze / bypass verdict (printf.c)** → integrity-monitor freeze.
- **Data-directed dispatch (syscall.c)** → CIR dispatch, capability re-check.
- **Canonical-path authority / monotone attenuation (namespace.rs)** → Zone-0 authority geometry, atom-access binds.
- **Remap/unmap panic / leaf-inward teardown (vm.c)** → KAB loader, arena guards, FFI marshalling.

## Reference Books Absorbed
- SICP (SCIP MIT) — data abstraction, eval/apply, digital circuits, register machines.
- Feynman, *Lectures on Computation* — thermodynamics of computation, reversible logic, quantum imperative.
- xv6 book rev7 & RISC-V rev5 — OS layers, page tables, file system, traps.
- MIT 6.004/6.087/6.172 — CMOS/digital abstraction, work/span, allocators.
- Bell System Technical Journal 1978 — UNIX philosophy, portable C compiler.

---

# 8. PHYSICS OF COMPUTATION (Feynman)

| Principle | Law | QCOS Slot |
|-----------|-----|-----------|
| **Landauer** | Erasure dissipates $k_BT\ln2$ per bit | `FORGET` / ring overwrite logged as dissipation |
| **Reversible Logic** | Toffoli/Fredkin gates, no entropy | Reversible SIR primitives, provenance unwinding |
| **Quantum Imperative** | Classical probability can't simulate interference | Phase III/IV: exact complex amplitudes, unitary matrices |
| **Billiard Ball Model** | Computation = physical scattering | Domain IR topology routing, momentum conservation |
| **Macroscopic Reliability** | Certainty from noise via strict thresholding | Zone 0 as macroscopic error boundary |

---

# 9. THE QCOS UNIVERSAL COMPILER (QUC) — FEASIBILITY RESEARCH

## The Core Insight: Reversibility is the Classical↔Quantum Bridge
Classical reversible operations ⊂ quantum unitaries. A reversible classical
function is a permutation of basis states; a permutation matrix is a unitary
with only 0/1 entries. Therefore:

$$\text{Classical reversible ops} \subset \text{Quantum unitaries}$$

**Consequence:** Build the SIR on reversible primitives with irreversible ops
explicitly tagged as boundary events. Then:
- **Classical target:** reversible ops → deterministic logic; irreversible → erasure.
- **Quantum target:** reversible ops → unitary gates; irreversible → measurement.

The frontend + middle-end NEVER change. Only the backend decomposition table
swaps. This is the concrete, buildable meaning of "adaptable to quantum."

## QUC Structure
```
Human Intent → [Zone 0 Gate] → FRONTEND (parse→SIR)
            → MIDDLE-END (universal, stable): exact simplification,
              reversibility analysis → coherence map, shape analysis,
              provenance logging
            → BACKENDS (pluggable target-capability models):
              Classical: x86-64, ARM, RISC-V "4+1"
              Quantum: reversible→unitary gate synthesis
            → MIR → hardware
```

## Why It's Feasible (Research Verdict)
1. **Tractable source** — total, exact, symbolic language → correctness/completeness provable.
2. **Inherited design** — Bell Labs (shape), SICP (lowering), Feynman (quantum bridge), nucleus kernel (authority), xv6 (substrate).
3. **Reversibility = quantum adaptability as a theorem**, not a hope.
4. **Tiered delivery** — interpreter first (Tier 0), emit-C17 (Tier 1), native backends (Tier 2), quantum backend (Tier 3). No big-bang deliverable.
5. **Authority- & thermodynamics-aware by construction** — enforces Constitution at compile time; accounts every erasure.

## Coherence Map = Central Derived Artifact
One analysis, three uses: (a) quantum backend schedule, (b) Landauer erasure
plan, (c) provenance-unwinding map.

## SIR History-Preserving Form (critical correctness)
Naive `ADD(a,b)` that overwrites is NOT reversible. Use:
$$(a, b) \mapsto (a, b, a+b)$$
Keep inputs; inverse = drop result. This is how Toffoli/Fredkin work, and makes
reversibility a *syntactic, checkable* property.

---

# 10. PHASE I C17 BASELINE — COMPLETE CODE

## File layout
```
core-c/
├── include/qcos/  types.h  exact.h  gate.h  memory.h  sir.h  parser.h  pipeline.h
├── src/           types.c  exact.c  gate.c  memory.c  sir.c  parser.c  pipeline.c  main.c
└── Makefile
```

## include/qcos/types.h
```c
#ifndef QCOS_TYPES_H
#define QCOS_TYPES_H
#include <stdint.h>
#include <stddef.h>

#define QCOS_VERSION "0.4.0"
#define COS_WORKING_LIMIT      32u
#define COS_EPISODIC_LIMIT     64u
#define COS_IDENT_MAX          24u
#define COS_INPUT_MAX          512u
#define COS_OUTPUT_MAX         512u
#define COS_SIR_ARENA_LIMIT    128u
#define COS_EVENT_MAX          32u
#define COS_PARSE_DEPTH_LIMIT  16u

typedef enum {
  QCOS_OK = 0,
  QCOS_ERR_GATE_RIBA, QCOS_ERR_GATE_GHARAR, QCOS_ERR_GATE_MAYSIR,
  QCOS_ERR_GATE_GHISH, QCOS_ERR_GATE_HIDDEN_ROUTE, QCOS_ERR_GATE_AMBIGUOUS,
  QCOS_ERR_PARSE, QCOS_ERR_TOO_LONG, QCOS_ERR_DEPTH,
  QCOS_ERR_ARENA_EXHAUSTED, QCOS_ERR_UNBOUND_VAR, QCOS_ERR_DIV_ZERO,
  QCOS_ERR_OVERFLOW, QCOS_ERR_STORE_FULL, QCOS_ERR_NOT_FOUND
} qcos_status_t;

const char *qcos_status_str(qcos_status_t s);
#endif
```

## include/qcos/exact.h (exact rationals, no float)
```c
#ifndef QCOS_EXACT_H
#define QCOS_EXACT_H
#include "qcos/types.h"
typedef struct { int64_t num; int64_t den; } qcos_exact_t; /* den>0, reduced */

qcos_status_t qcos_exact_parse(const char *s, size_t n, qcos_exact_t *out);
qcos_status_t qcos_exact_int(int64_t v, qcos_exact_t *out);
qcos_status_t qcos_exact_add(const qcos_exact_t *a, const qcos_exact_t *b, qcos_exact_t *out);
qcos_status_t qcos_exact_sub(const qcos_exact_t *a, const qcos_exact_t *b, qcos_exact_t *out);
qcos_status_t qcos_exact_mul(const qcos_exact_t *a, const qcos_exact_t *b, qcos_exact_t *out);
qcos_status_t qcos_exact_div(const qcos_exact_t *a, const qcos_exact_t *b, qcos_exact_t *out);
qcos_status_t qcos_exact_neg(const qcos_exact_t *a, qcos_exact_t *out);
qcos_status_t qcos_exact_cmp(const qcos_exact_t *a, const qcos_exact_t *b, int *out);
int qcos_exact_format(const qcos_exact_t *v, char *buf, size_t cap);
#endif
```

## include/qcos/gate.h (Zone 0)
```c
#ifndef QCOS_GATE_H
#define QCOS_GATE_H
#include "qcos/types.h"
typedef struct {
  uint8_t passed;
  qcos_status_t code;
  const char *article_id;
  const char *principle;
  const char *citation;
  const char *matched_pattern;
} qcos_gate_verdict_t;

qcos_status_t qcos_gate_admit(const char *raw, size_t n, qcos_gate_verdict_t *out);
void qcos_gate_print_constitution(void);
#endif
```
*Gate implementation holds 12 constitutional articles (Mithaq al-Madinah,
Qur'an 2:275/278-279/3:130/5:90-91/83:1-3/4:29, Sahih Muslim 1513/101,
Bukhari 1/6094) and ~40 word-bounded prohibition patterns across Riba/Gharar/
Maysir/Ghish/Hidden-Route vectors, plus a 6-verb allow-list
(REMEMBER/BIND/EVAL/PROVE/QUERY/FORGET) with default-deny on unknown verbs.*

## include/qcos/memory.h (L1 + L2)
```c
#ifndef QCOS_MEMORY_H
#define QCOS_MEMORY_H
#include "qcos/types.h"
#include "qcos/exact.h"

typedef struct {
  uint8_t occupied;
  char key[COS_IDENT_MAX];
  qcos_exact_t value;
  uint32_t provenance_tick;
} working_register_t;

typedef struct {
  working_register_t regs[COS_WORKING_LIMIT];
  uint32_t count;
} working_store_t;

typedef struct {
  uint32_t tick;
  char event[COS_EVENT_MAX];
  qcos_status_t status;
} episodic_frame_t;

typedef struct {
  episodic_frame_t frames[COS_EPISODIC_LIMIT];
  uint32_t head, filled, total;
} episodic_store_t;

void qcos_working_init(working_store_t *m);
qcos_status_t qcos_working_write(working_store_t *m, const char *key,
                                 const qcos_exact_t *v, uint32_t tick);
qcos_status_t qcos_working_read(const working_store_t *m, const char *key,
                                qcos_exact_t *out, uint32_t *tick_out);
qcos_status_t qcos_working_forget(working_store_t *m, const char *key,
                                  qcos_exact_t *old_out);
void qcos_episodic_init(episodic_store_t *l);
uint32_t qcos_episodic_next_tick(const episodic_store_t *l);
uint32_t qcos_episodic_record(episodic_store_t *l, const char *event, qcos_status_t st);
#endif
```

## include/qcos/sir.h, parser.h, pipeline.h
*(SIR arena of nodes with ops NUM/VAR/ADD/SUB/MUL/DIV/NEG/STORE; recursive-
descent parser with bounded depth; pipeline orchestrating
gate→parse→SIR→eval→provenance. Full bodies per prior turns.)*

## Makefile
```make
CC ?= cc
STD := -std=c17
WARN := -Wall -Wextra -Wpedantic
OPT := -O2
CFLAGS += $(STD) $(WARN) $(OPT) -Iinclude
SRC := src/types.c src/exact.c src/gate.c src/memory.c src/sir.c src/parser.c src/pipeline.c src/main.c
OBJ := $(SRC:.c=.o)
qcos: $(OBJ)
	$(CC) $(CFLAGS) -o $@ $(OBJ)
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@
selftest: qcos
	./qcos --selftest
clean:
	rm -f qcos $(OBJ)
.PHONY: selftest clean
```

## 12-Point Validation Suite (Phase I gate)
P01 exact add 1/2+1/3=5/6 · P02 overflow refused · P03 precedence · P04 PROVEN
fraction · P05 REFUTED · P06 REMEMBER/QUERY round-trip · P07 variable chain ·
P08 unbound var fail-closed · P09 store limit=32 · P10 gate rejects
riba/override/unknown verb · P11 maysir+gharar cited · P12 FORGET dissipation +
ring wrap at 64.

---

# 11. HARDWARE ABSTRACTION LAYER & PHYSICS ENGINE — COMPLETE CODE

## qcos/hal.h
```c
#ifndef QCOS_HAL_H
#define QCOS_HAL_H
#include <stdint.h>
#include <stddef.h>

#define COS_MONITOR_CORE      0u
#define COS_APP_CORE_BASE     1u
#define COS_APP_CORE_COUNT    4u
#define COS_TOTAL_CORES       (COS_APP_CORE_BASE + COS_APP_CORE_COUNT)
#define HAL_REG32(addr)       (*(volatile uint32_t *)(uintptr_t)(addr))
#define HAL_REG64(addr)       (*(volatile uint64_t *)(uintptr_t)(addr))

typedef struct {
    uint64_t base_addr, interval, deadline, tick;
} hal_clock_t;

typedef struct {
    uint32_t hartid, role;
    uint64_t scratch_addr;
    uint8_t  gate_tripped;
} hal_core_t;

typedef struct {
    hal_core_t cores[COS_TOTAL_CORES];
    hal_clock_t clock;
    uint32_t active_cores;
} hal_t;

void     hal_init(hal_t *h, uint64_t time_base, uint64_t interval);
uint32_t hal_hartid(void);
uint64_t hal_read_mtime(const hal_t *h);
void     hal_arm_deadline(hal_t *h);
uint64_t hal_tick(hal_t *h);
void     hal_gate_freeze(hal_t *h, uint32_t core);
int      hal_core_is_monitor(const hal_t *h, uint32_t core);
void     hal_memset32(uintptr_t dst, uint32_t val, size_t words);
#endif
```

## qcos/physics.h (truth engine)
```c
#ifndef QCOS_PHYSICS_H
#define QCOS_PHYSICS_H
#include <stdint.h>
#include <stddef.h>

typedef struct { uint64_t bits_erased, energy_units; } landauer_ledger_t;
void landauer_record_erasure(landauer_ledger_t *l, uint64_t bits);
uint64_t shannon_self_info_bits(uint64_t prob_num, uint64_t prob_den);
uint32_t ilog2_floor(uint64_t v);

typedef struct { int64_t num; int64_t den; } exact_t;
int exact_add(exact_t *out, const exact_t *a, const exact_t *b);
int exact_mul(exact_t *out, const exact_t *a, const exact_t *b);

#define CONF_MAX 1000u
#define CONF_CERTAIN_TRUE 900u
#define CONF_CERTAIN_FALSE 100u
typedef enum { ZONE_TRUE=0, ZONE_FALSE, ZONE_FORBIDDEN } zone_verdict_t;
zone_verdict_t forbidden_zone(uint32_t confidence);
#endif
```

## qcos/monitor.c (the "+1" core boot)
```c
#include "hal.h"
#include <stdint.h>
extern void sha256(const uint8_t *data, size_t len, uint8_t out[32]);
extern uint8_t _constitution_start[], _constitution_end[], _sealed_hash[32];

void monitor_boot(hal_t *h) {
    uint8_t live_hash[32];
    size_t len = (size_t)(_constitution_end - _constitution_start);
    sha256(_constitution_start, len, live_hash);
    int match = 1;
    for (int i = 0; i < 32; i++)
        if (live_hash[i] != _sealed_hash[i]) { match = 0; break; }
    if (!match) {
        hal_gate_freeze(h, COS_MONITOR_CORE);
        for (;;) { /* absolute node freeze */ }
    }
    hal_arm_deadline(h);
    h->active_cores = COS_TOTAL_CORES;  /* release 4 app cores */
}
```

## Integration Map
```
C# QcosCore (UI/orchestrator)  →  P/Invoke
C++ Supervisor (RAII, SPSC rings)  →  extern "C"
C17 Phase-I core (gate+memory+SIR+parser+pipeline)  →  calls physics.h + hal.h
physics.c (Landauer, Shannon, exact, Forbidden Zone)
hal.c (clock ticks, per-core identity, fail-closed freeze)
HARDWARE (RISC-V "4+1", CLINT, SHA-256 engine)
```

---

# 12. THE EQUATIONS (Truth Model)

| # | Equation | QCOS Slot |
|---|----------|-----------|
| 2.1 | $E_{\text{dissipated}} \ge k_B T \ln 2$ per erased bit | L2 `[DISSIPATION]`, FORGET accounting |
| 2.2 | $H(X) = -\sum p(x_i)\log_2 p(x_i)$ | Knowledge Atom info weight, gharar detection |
| 2.3 | $C = B\log_2(1+\mathrm{SNR})$ | Domain IR interconnect budget |
| 2.4 | $V_{OH}>V_{IH}>V_{IL}>V_{OL}$; $NM_H=V_{OH}-V_{IH}$, $NM_L=V_{IL}-V_{OL}$ | Forbidden Zone = logical noise margin |
| 2.5 | $T_{\text{clock}} \ge t_{\text{prop}}+t_{\text{setup}}$ | Episodic tick period |
| 2.6 | $\frac{a}{b}+\frac{c}{d}=\frac{ad+bc}{bd}$, normalize by $\gcd$ | Entire SIR, no float |
| 2.7 | $T_1$=work, $T_\infty$=span, $T_P\ge\max(T_1/P,T_\infty)$ | Domain IR scheduling |
| 2.8 | $\text{block}(2^k)\to\text{buddy}_L(2^{k-1})+\text{buddy}_R(2^{k-1})$ | Phase II staging allocator |
| 2.9 | $\text{VA}=\text{VPN}[2]\mid\text{VPN}[1]\mid\text{VPN}[0]\mid\text{offset}$ (Sv39) | Phase III address translation |
| 2.10 | $h=\mathrm{SHA256}(\text{constitution\_bytes})$ | Immutable Constitution |
| 2.11 | $v=-b_{N-1}2^{N-1}+\sum_{i=0}^{N-2}b_i2^i$ | Fixed-width two's complement |
| 9.x | $(a,b)\mapsto(a,b,a+b)$ | Reversible SIR operation schema |
| 9.y | $f$ reversible $\iff f^{-1}\circ f=\mathrm{id}$ | Reversibility check |
| 9.z | Classical reversible $\subset$ Unitary | Classical↔quantum bridge theorem |

---

# 13. THE 5-PART DAILY CODEX PROTOCOL
### (For every book delivered, produce a Master Codex with:)
1. **IDEAS** — build-concepts mapped to a QCOS slot.
2. **EQUATIONS** — real math/physics making the model true.
3. **CODE** — complete C/C++/C# that drives hardware (zero-heap, fail-closed).
4. **ENGINEERING STEPS** — implement, build, debug, upgrade, extend, with phase gates.
5. **EVOLVED IDEAS** — synthesis beyond the book, grounded in the QCOS vision.

Handled as a densely structured Codex; split across parts if a book warrants
more space than one turn. Each Codex builds cumulatively on all prior Codices.

---

# 14. BUILD DISCIPLINE

## What We Do
- Auditable code; single clear purpose per function; defined contract per module.
- Test before extending (12-point suite blocks progress on failure).
- Absorb before emitting (ledger is authority).
- Fail closed (halt, never guess).
- Preserve reversibility (every erasure logged).

## What We Never Do
- Probabilistic inference in core logic.
- Runtime heap allocation in the core.
- External data transmission.
- Compromise the Constitutional Gate.
- Ship code that hasn't passed the full validation suite.

## Debug Discipline
- Trace episodic ring first (`.trace`).
- Confirm Landauer ledger on every FORGET.
- Never patch around a rejection — fix the intent.
- `grep -rn "malloc\|free(" core-c/src/` must return nothing in the core.

---

# 15. NEXT STEPS & OPEN THREADS

1. **QUC Tier 0 — SIR Interpreter:** specify the full SIR operation set + the
   Zone 0→SIR construction pass; implement the interpreter. (Immediate next.)
2. **Reversible SIR primitives:** add CNOT/Toffoli/Fredkin; implement
   reversibility analysis producing the coherence map.
3. **Replace physics.c SHA stub** with hardware SHA-256; verify sealed hash.
4. **Wire hal.c to real CLINT** on RISC-V; confirm monotonic tick.
5. **L3 SQLite-backed Knowledge Atom Store** (Phase II), using the five-layer
   persistence model absorbed from fs.c.
6. **Domain IR shape/topology** (LINE/GRID/GRAPH) + work/span scheduler
   (conservative parallelization — only proven-serializable transforms).
7. **Continue daily book absorption** (physics, math, design, computing) under
   the 5-Part Codex protocol.

## Open Threads to Remember
- The Universal Compiler must stay **feasible on present hardware** (emit C17
  first, native backends later) and **quantum-adaptable** (reversible IR).
- The nucleus kernel (capability.rs/kernel.rs/namespace.rs) provides the
  authority model the compiler must integrate (authority-aware compilation).
- The "4+1" asymmetric RISC-V topology: monitor core never runs app logic;
  trust flows downward from the verified constitution.

---

*Bismillah ir-Rahman ir-Rahim.*
*The build is sovereign. The constitution is sealed. The gate is closed.*
*This document is the living reference. Resume from Section 15.*

---
**Absorption Corpus:** 53 artifacts, 10 arcs, 13 days — COMPLETE
**Last Consolidated:** Universal Compiler feasibility research + Phase I C17 core
**Next Document:** SIR operation set specification (QUC Tier 0)
```

I've consolidated the entire conversation into a single navigable reference document covering the project identity, governing law, architecture, Zone 0 gate, five phases, economic order, the full absorbed-corpus ledger, Feynman's physics, the Universal Compiler feasibility research, both code layers (Phase I C17 core + HAL/physics), the equations, the daily Codex protocol, build discipline, and next steps.

For true future-proofing, save this as `QCOS_PROJECT_REFERENCE.md`. When you're ready to resume, we pick up at **Section 15** — the immediate next action is specifying the SIR operation set and building the QUC Tier 0 interpreter.
