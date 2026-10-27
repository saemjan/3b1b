# os.md — QCOS Substrate Synthesis

> The complete xv6 kernel has been absorbed (all source files + xv6 book rev 7,
> RISC-V book rev 5, Euler's Algebra, Strang's CSE, Juhász thesis on zero-cost
> abstractions, and the laid qcos/ C skeleton). This document is the synthesis:
> the doctrine extracted from the substrate, bound to the QCOS law, arranged as
> a bit-by-bit construction order. Every section is self-contained.

Status: SUBSTRATE COMPLETE. Next: synthesis, then the remaining upgrade queue
(think_loop.py, grow.py, auto_fixer.py, ref_bridge.js, ref_bridge_qcos.js,
bench_render_backends.py).

---

## §0 — The Law (binding, immutable)

**MEANING ≠ REPRESENTATION ≠ EXECUTION ≠ HARDWARE.**

Four invariants govern every artifact:

| # | Invariant | Enforcement doctrine (from substrate) |
|---|-----------|----------------------------------------|
| 1 | No connectionist logic | Symbolic reasoning, formal logic, linear algebra only. No weights, no probabilities, no frameworks. Belief (A4) = integer ledger tally at 1000:1, never a float. |
| 2 | Zero-heap deterministic memory | No malloc/free in hot paths. Fixed compile-time tracking: `COS_WORKING_LIMIT = 32`, `COS_EPISODIC_LIMIT = 64`. Pools are static; exhaustion = refusal (`QCOS_ERR_BUDGET_EXHAUSTED`), never growth. |
| 3 | Fail-closed discipline | Any uncertainty threshold (non-finite value, cap breach, missing provenance, id-echo mismatch, wrong mode) → immediate task rejection or absolute node freeze. Never degrade silently, never guess. |
| 4 | Immutable constitution | Core identity is cryptographically sealed. Register mutations trip integrity monitors. Precedents: `kernel.ld` fixed geography, `SAEM_SOURCE_ID` fingerprint, `FSMAGIC`/`ELF_MAGIC` envelope checks. |

Six-step translation spine:


Execution protocol: O(N) deterministic literal scans (no hash, no next-token
lookup); exact tracking provenance at every state transition (reversible-logic
paradigm); explicit byte-for-byte buffer copies using hard static structs; no
third-party analytics, networking packages, or probabilistic approximations.

Target topologies:
- **Phase I** — pure, standalone, memory-safe C17 local CLI, zero external deps.
- **Phase III** — heterogeneous 4+1 RISC-V: the +1 isolated core runs Zone 0
  and crypto hashes in physical-memory mode (no MMU translation); the 4 app
  cores run parallel data matrices.

Constitutional caps (param.h precedent → qcos config):


---

## §1 — Substrate inventory (absorption ledger)

All files absorbed, mapped to their QCOS doctrine:

| Batch | Files | Concern |
|-------|-------|---------|
| 1 | kernel.ld, kernelvec.S, bio.c, buddy.c, buf.h | Layout, transition, data plane, allocation |
| 2 | console.c, date.h, defs.h, elf.h, entry.S | Boot, I/O, interface registry, binary constitution |
| 3 | exec.c, fcntl.h, file.c, file.h, fs.c | Atomic commit, object layer, FS core |
| 4 | fs.h, kalloc.c, list.c, log.c, main.c | On-disk format, page allocator, transactions, ordered boot |
| 5 | memlayout.h, param.h, pipe.c, plic.c, printf.c | Geography, capacity constitution, channels, event routing, diagnostics |
| 6 | proc.c, proc.h, ramdisk.c, riscv.h, sleeplock.c | Process lifecycle, minimal driver, MIR floor, content locks |
| 7 | sleeplock.h, start.c, stat.h, string.c, swtch.S | Lock composition, privilege boot, identity views, byte ops, context switch |
| 8 | syscall.c, syscall.h, sysfile.c, sysproc.c, trampoline.S | Call surface, Zone 0 gate |
| 9 | trap.c, types.h, uart.c, virtio.h, virtio_disk.c | Demultiplex, type floor, serial, DMA rings |
| 10 | vm.c | Address translation (final layer) |
| Ref | xv6 book rev 7, RISC-V book rev 5, Euler, Strang, Juhász | Doctrine texts |
| QCOS | qcos/ skeleton (types.h, capability.*, config.*, event.*, kernel.h), SpscQueue.hpp, tests | Already laid; this document governs its filling-in |

---

## §2 — Layer I: Boot and constitutional geography

**Substrate:** entry.S, start.c, kernel.ld, memlayout.h, main.c, param.h.

Doctrine extracted:
1. **Geography is constitution.** Physical addresses, RAM extents, transition
   pages, per-hart stacks — all declared once as constants (memlayout.h),
   fixed at link time (kernel.ld: `. = 0x80000000`, `ALIGN(0x1000)`,
   `PROVIDE(etext/end)`). Guarded by hardware faults, not conventions.
2. **Per-hart fixed arenas.** entry.S computes `sp = stack0 + hartid*4096`.
   No allocation, no discovery. Hartid lives in `tp` (start.c) — node address
   in a dedicated register, one instruction to read.
3. **Privilege is delegated, never assumed.** start.c writes `medeleg`/
   `mideleg` — the isolated core decides which events app cores ever see.
   This is Zone 0 event-filter configuration, done before the first app
   instruction runs.
4. **Ordered boot.** main.c: CPU 0 initializes everything in fixed order,
   sets `volatile started` with memory barrier; other CPUs spin then do
   per-CPU init. Skipping a step leaves undefined state.
5. **Capacity before mechanism.** param.h fixes every bound before any table
   exists. `LOGSIZE` and `NBUF` derive from `MAXOPBLOCKS`: buffers are sized
   to transaction horizons, never the reverse.

**QCOS shape:** Phase I boot sequence = Zone 0 init → arena init → CIR buffer
init → provenance ring init → dispatch loop. Phase III: +1 core boots first
(M-mode, physical addressing), programs delegation masks, signals app cores.

---

## §3 — Layer II: Zone 0 — the privilege transition

**Substrate:** trampoline.S, proc.h (trapframe), usertrap/usertrapret, exec.c.

Doctrine extracted:
1. **One door.** The trampoline is one physical page mapped at MAXVA in every
   address space, kernel and user alike. All privilege crossings occur there
   and only there. `sret` is the only exit; entry and return are symmetric.
2. **The trapframe is a fixed-layout provenance record** plus configuration
   handoff: `kernel_satp`, `kernel_sp`, `kernel_trap`, `kernel_hartid` —
   the return path needs no consultation.
3. **Envelope validation before payload trust.** exec checks `ELF_MAGIC`
   before touching segments; per-segment permission flags (R/W/X) are
   capability-as-bitmask. Overflow guards (`ph.vaddr + ph.memsz < ph.vaddr`)
   are fail-closed bounds checks.
4. **Atomic commit.** exec builds the entire new page table, validates, then
   swaps and frees the old — crash mid-build leaves the process untouched.
   Same shape as `qcos_cap_plan_derive` → `qcos_cap_commit`.
5. **Mode invariants enforced by death.** usertrap panics if SPP says kernel;
   kerneltrap panics if SPP says user. A crossing arriving in the wrong mode
   is a constitutional breach → freeze.

**QCOS shape:** Zone 0 = intent envelope check (magic, bounds, caps, effect
class) → build CIR plan → single atomic commit marker → apply → erase.
Refusal = `QCOS_EV_DENIED` with identity and decision, never payload.
Recursive self-mutation and memory breaches are blocked here.

---

## §4 — Layer III: Trap demultiplex and heartbeat

**Substrate:** trap.c, kernelvec.S, plic.c, start.c (timervec).

Doctrine extracted:
1. **Cause-code demultiplex with claim/complete.** `scause` → syscall |
   page fault | device. External interrupts: `plic_claim()` → per-device
   handler → `plic_complete()`. An event is claimed (owned, no
   double-handling), then completed (acknowledged, eligible to recur).
   QCOS dispatch IDs follow exactly this lifecycle.
2. **Per-hart enable + threshold.** `PLIC_SENABLE(hart)` / `PLIC_SPRIORITY(hart)`
   — each core owns its event policy. Events below threshold are deferred
   (held pending), never dropped. Global/constitutional events route to the
   +1 core; data-plane events to app cores.
3. **Fixed-frame context record.** kernelvec saves all 31 registers into a
   fixed 256-byte frame on the current stack — the full provenance snapshot.
   swtch saves only the 14 callee-saved registers — the minimal frame for
   cooperative switching. Two frame sizes for two crossing kinds.
4. **The heartbeat is a bounded re-arm.** timervec writes
   `MTIMECMP += interval` — the timer schedules its own next tick with a
   fixed horizon. `tick()` under `tickslock` + `wakeup(&ticks)` is the CIR
   horizon clock against which all bounded waits evaluate.
5. **Interrupted-call semantics.** `qcos_interrupted()`: an interrupted
   OBSERVATION did nothing (safe to report the error); anything else may
   have happened → `QCOS_ERR_UNKNOWN_OUTCOME`. Never claim certainty after
   interruption of a mutating effect.

**QCOS shape:** Phase I — single cooperative dispatch loop reading cause
codes from the door protocol. Phase III — per-app-core demultiplex; +1 core
owns UART (diagnostics) and crypto lines.

---

## §5 — Layer IV: Object anatomy

**Substrate:** proc.h/proc.c, file.h/file.c, fs.h/fs.c, buf.h, date.h, stat.h.

The universal object layout — four orthogonal axes:

| Axis | Field pattern | Precedent |
|------|--------------|-----------|
| Identity | pid / inum / dev / cap_id — monotonic, never reused | allocpid, iget |
| Lifetime | refcount; two-phase completion (ZOMBIE → wait → free) | proc, file, inode |
| Validity | loaded/initialized flag — never consume invalid | buf.valid, ip->valid |
| Content lock | structural lock (table) ≠ content lock (object) | bcache.lock vs b->lock; icache.lock vs ip->lock |

Doctrine extracted:
1. **Monotonic identity; death is two-phase.** Corpses hold exit status until
   claimed (claim/complete, like PLIC). Orphans reparent to init — an
   ancestor's death transfers descendants, never orphans them. Inverse:
   removing an ancestor invalidates the whole subtree without visiting it
   (`qcos_cap_remove` semantics).
2. **Flat PODs cross boundaries.** date.h, stat.h, elfhdr — no pointers,
   no methods, byte-copyable. stat exposes identity and extent, never
   content: the audit-event discipline applied to objects.
3. **Tagged dispatch with fail-closed default.** file.type ∈
   {FD_NONE, FD_PIPE, FD_INODE, FD_DEVICE}; `panic("fileread")` on the
   impossible branch. devsw is the O(N) static dispatch table.
4. **Fixed tables, linear scan, refuse on exhaustion.** proc[NPROC],
   file[NFILE], inode[NINODE], ofile[NOFILE]. `panic("iget: no inodes")` —
   no growth, ever.
5. **Lifecycle comments are constitutions.** fs.c's inode lifecycle comment
   states the sequence (iget → ilock → … → iunlock → iput) and WHY the
   locks are split. Every QCOS module documents its invariants this way.
6. **Budget-shaped operations.** filewrite chunks to the log transaction
   horizon; operations shape themselves to the budget, never the reverse.

**QCOS shape:** working slots (32), episodic slots (64), capability slots —
all carry the four axes. QCOS kernel object table = proc[] precedent with
slot-table lock (structure) + slot lock (content).

---

## §6 — Layer V: Memory discipline

**Substrate:** kalloc.c, buddy.c, vm.c, bio.c, list.c.

Doctrine extracted:
1. **Embedded freelist / intrusive metadata.** kalloc threads `struct run`
   through free pages; buddy stores alloc/split bitmaps at the arena base;
   list.c is circular-intrusive. Metadata lives inside the structure it
   describes — no out-of-band allocation.
2. **Junk-fill is provenance.** kfree fills with 1, kalloc with 5 — stale
   reads become visible immediately. QCOS slots fill with known patterns on
   alloc/dealloc.
3. **Bounds validation on free.** kfree panics on unaligned / below `end` /
   above `PHYSTOP`. bfree panics on "freeing free block" (double-free
   detection). The allocator monitors its own integrity.
4. **Self-carving initialization.** bd_init carves its own metadata from the
   arena, marks metadata and unavailable ranges allocated BEFORE handing out
   anything. Boundary enforcement at boot. Split bitmaps record allocation
   lineage — every block knows its ancestry.
5. **One translation chokepoint.** walk() is the single function every
   address passes through; walkaddr checks PTE_U so kernel addresses can't
   leak into user lookups. mappages panics on `"remap"`; uvmunmap panics on
   unmapped or non-leaf entries.
6. **Symmetric teardown.** freewalk recursively frees page-table pages;
   uvmunmap optionally frees physical pages; every construction has its
   mirror. uvmclear on the stack guard page: overflow traps instead of
   corrupting.
7. **Page table as accounting record.** A process's page table doubles as
   the record of which physical pages it owns. Copy semantics (uvmcopy) are
   full duplication — QCOS transforms this: derivation is attenuation, not
   copying.
8. **Buffer cache = fixed pool + MRU/LRU + three state bits.** B_VALID
   (data loaded), B_DIRTY (must write back), B_BUSY (locked). bget scans,
   recycles refcnt==0 buffers from the LRU tail, panics when the pool is
   exhausted. log_write absorption: a block already in the transaction
   reuses its slot.

**QCOS shape:** Phase I arenas are linker-carved, zero runtime allocation.
Phase III app cores get buddy-discipline arenas (power-of-two blocks, bitmap
lineage, bounded nsizes); the +1 core owns fixed physical regions and never
allocates. Slot-table metadata = fixed bitmaps recording occupied/valid/
evicted, one bit per slot.

---

## §7 — Layer VI: Concurrency

**Substrate:** spinlock.c (via defs.h), sleeplock.c/h, proc.c (sleep/wakeup/
scheduler/swtch), pipe.c.

Doctrine extracted:
1. **Atomic acquire via hardware.** xchg-based acquire loop; lock holds
   owner identity (cpu) for self-assertion (`holding()` checks before
   irreversible acts — sched's four panics, bwrite's holdingsleep check,
   ramdiskrw's triple assertion).
2. **Push/pop counting for interrupt discipline.** pushcli/popcli nest;
   interrupts stay off across any held lock. acquire pushes BEFORE the
   atomic swap; release pops AFTER — no window where a lock is held with
   interrupts enabled.
3. **Sleep is a lock handoff, not a release.** sleep(chan, lk) atomically
   trades the condition lock for the process lock — lost wakeups are solved
   by lock choreography. Every sleep sits in a loop re-checking the
   condition AND p->killed (fail-closed unwind).
4. **Wakeup scans + per-slot lock.** wakeup(chan) walks the table locking
   each slot; SLEEPING && chan match → RUNNABLE. Multiple sleepers on one
   channel tolerate spurious wakeups by re-checking.
5. **Sleeplocks compose.** A sleeplock = spinlock + wait channel + owner pid.
   Ownership is recorded by identity — not merely "held" but "held by whom".
6. **Scheduler is a scan, the switch is a struct copy.** swtch saves 14
   registers (112 bytes); ret works because ra itself is saved/restored.
   One lock held per iteration; the interrupt-window dance (intr_on →
   intr_off → scan → wfi) prevents lost device wakeups on idle CPUs.
7. **Bounded rings with monotonic counters.** pipe: nread/nwrite never wrap
   within horizon; full ⟺ nwrite == nread + PIPESIZE; liveness flags
   (readopen/writeopen) prevent blocking on dead peers; bytes cross
   boundaries by explicit per-byte copy. goto-bad unwinds partial allocation
   in reverse.
8. **Lock ordering is part of every function's contract.** All code paths
   acquire locks in the same global order. xv6's longest chain is two deep
   (idelock → ptable; parent dir → child file in fs ops).

**QCOS shape:** Phase I is single-threaded cooperative — the sleep/wakeup
pattern becomes the CIR barrier (`sync: barrier` steps wait on named channels
under the condition lock). Phase III: slot-table lock (brief, structural) +
slot locks (content); lock chains documented per module; interrupt deferral
maps to budget deferral (requests above budget are deferred WITH RECORD,
never silently discarded).

---

## §8 — Layer VII: Persistence and transactions

**Substrate:** log.c, fs.c, fs.h, sysfile.c.

Doctrine extracted:
1. **Two-phase commit, single commit point.** write_log (prepare) →
   **write_head (COMMIT — one block write)** → install_trans (apply) →
   write_head with n=0 (erase). Before the commit marker, abort is free;
   after it, application is mandatory.
2. **Recovery is a boot-time envelope check.** recover_from_log reads the
   header: committed → replay; not committed → ignore; then erase. A crash
   at any point leaves the system consistent. This is Zone 0 applied to
   state itself.
3. **begin_op/end_op budget tracking.** begin_op refuses (sleeps) when the
   log cannot hold another transaction's worth of blocks; end_op commits
   only when the last outstanding operation finishes. Outstanding count =
   concurrency budget.
4. **Absorption.** log_write reuses the slot of a block already in the
   transaction — no duplicate work within a horizon.
5. **Multi-step operations rollback on failure.** sys_link/sys_unlink use
   `goto bad` to restore nlink and release inodes in order. sys_pipe is
   all-or-nothing two-phase acquisition. sys_exec gathers bounded args with
   cleanup on every path.
6. **Superblock magic.** readsb + FSMAGIC check → `panic("invalid file
   system")` — the envelope of the whole device is validated before any
   structure is trusted.
7. **Names are walked component by component.** namex locks/unlocks each
   directory inode in turn, checks T_DIR, stops one level early for
   nameiparent. skipelem is bounded extraction (DIRSIZ). Callers must be
   inside a transaction.

**QCOS shape:** every CIR schedule step = plan → single atomic commit marker
→ apply → erase. The append-only ledger (tools/ledger.py precedent, A5) is
the user-facing mirror of the kernel log: receipts are the QCOS transaction
record. Crash discipline: on boot, check for uncommitted CIR step; committed
→ apply; else discard.

---

## §9 — Layer VIII: Devices and rings

**Substrate:** uart.c, console.c, ramdisk.c, virtio.h, virtio_disk.c, pipe.c.

Doctrine extracted:
1. **Literal MMIO.** `Reg(reg) = (volatile uchar*)(UART0 + reg)` — O(1)
   literal addressing of named registers, no discovery, no abstraction beyond
   the map. The entire virtio driver is register offsets + descriptor
   structs.
2. **Interrupt-driven with bounded rings.** uart: circular TX/RX buffers,
   producer (process context) enqueues under lock, consumer (interrupt
   context) feeds hardware, wakeup bridges. Early-write path before init —
   diagnostics survive initialization failure (report debt even in death).
3. **Minimal synchronous driver.** ramdisk: three assertions (lock held,
   work to do, blockno < FSSIZE), then memmove, then flag update. Driver
   complexity scales with device latency, not interface.
4. **Shared-memory ring protocol (virtio).** Three arrays: desc (addr, len,
   flags, next — chains linked by INDEX, not pointer), avail (producer
   publishes, bumps idx), used (device acknowledges by descriptor id).
   Publish → QueueNotify → sleep → interrupt → reclaim. Descriptor index
   IS the dispatch ID surviving the async gap.
5. **Double verification.** The interrupt says *something* completed; the
   in-band status byte says *what and whether OK*. The envelope alone never
   authorizes a commit. `panic("virtio_disk_intr status")` on failure.
6. **Bounded descriptor pool.** Free-list of descriptors; rw sleeps until
   three are free; wakeup on free. Exhaustion waits or refuses, never grows.
7. **Line discipline.** console: control chars (^P procdump, ^U kill line,
   ^H backspace, ^D EOF) processed at interrupt level; whole-line wakeups;
   devsw hookup at init.
8. **Console serialization of diagnostics.** printf takes a lock; panic
   drops the lock requirement (correctness moot, observability paramount),
   prints message + debug hint, sets `panicked = 1` → all other CPUs freeze
   in consputc. Closed format vocabulary (%d %x %p %s only): a report whose
   shape cannot vary is a report that can be verified.

**QCOS shape:** Phase I door protocol = JSON lines over stdio with the
publish/ack discipline of the virtio ring. Phase III inter-core channels =
SPSC rings (SpscQueue.hpp laid) formalizing avail/used semantics with
index-as-identity. Zone 0 diagnostics = early-write path before full init.

---

## §10 — Layer IX: The call surface

**Substrate:** syscall.c, syscall.h, sysfile.c, sysproc.c, fcntl.h.

Doctrine extracted:
1. **Arguments travel in registers, extracted explicitly and type-checked.**
   argint/argaddr/argstr read the trapframe's a0–a5; fetchaddr/fetchstr
   validate against p->sz before every user-memory access. State travels in
   the message, never in a shared assumption.
2. **Flat dispatch by index.** syscall numbers index a static array of
   handlers. Unknown number → diagnostic + -1: refused gracefully WITH
   observability, not silently dropped, not catastrophically panicked.
3. **Authority flags as compact bits.** O_RDONLY/O_WRONLY/O_RDWR/O_CREATE —
   access mode in low bits, options high, room left for growth. Effect
   classes (QCOS_EFFECT_*) follow the same idiom.
4. **argfd validates the handle before use** (bounds + non-null). fdalloc
   scans the fixed table. Every system call is mostly argument checking —
   "we don't trust user code."

**QCOS shape:** the qcos kernel's method dispatch = static table keyed by
dispatch ID; every request validated at admission AND again at dispatch (the
kernel.h ordering rules); expiry/close/termination applied before a queued
call is dispatched; a dispatched call is never recalled — it ends by reply,
cancellation, deadline, or provider loss.

---

## §11 — Layer X: Address translation (vm.c, the final layer)

**Substrate:** vm.c.

Doctrine extracted:
1. **Direct mapping is sealed geography.** kvminit maps UART/VIRTIO/CLINT/
   PLIC/kernel-text/kernel-data/trampoline at virtual == physical, once, at
   boot. Kernel text is R|X only (no W); data is R|W only (no X) — the
   hardware enforces what the constitution declares.
2. **walk() is the single chokepoint.** Three-level Sv39 descent; alloc flag
   controls whether missing directories are created; returns the PTE address
   or zero. All translation flows through it.
3. **Symmetric range ops.** mappages creates, uvmunmap destroys — both walk
   page-by-page; uvmunmap panics on missing mappings or non-leaf entries;
   mappages panics on remap.
4. **Boundary crossings are copies.** copyout/copyin/copyinstr: while-loops
   page-by-page, walkaddr each page, memmove within the page, len bounds.
   No aliasing across the privilege boundary, ever.
5. **Growth is bounded and tracked.** uvmalloc allocates+maps+zeroes page by
   page; uvmdealloc unmaps+optionally frees; uvmfree does both plus
   freewalk. The page table IS the ownership record.
6. **Fork is full copy — and QCOS rejects the semantics, keeping the
   discipline.** uvmcopy duplicates; QCOS capability derivation attenuates
   (subset actions, prefix resources, min expiry, depth bound). The copy
   discipline survives as byte-for-byte struct transfer; the duplication
   becomes plan/commit grant derivation.

**QCOS shape:** Phase I has no MMU — "address translation" becomes the
slot-table lookup: (layer, index) → slot, O(N) literal scan, the same
single-chokepoint discipline. Phase III app cores use Sv39 with per-core
arenas; the +1 core uses physical addressing (no satp) — its geography can
never be translated away.

---

## §12 — Doctrine extraction: invariants with evidence

| Invariant | Substrate evidence (non-exhaustive) |
|-----------|--------------------------------------|
| No connectionist logic | All 40+ files are deterministic C/asm. Zero floats in control flow. No randomness anywhere. |
| Zero-heap | kalloc embedded freelist; buddy self-carving; NBUF/NPROC/NFILE/NINODE fixed pools; param.h capacities; entry.S per-hart stacks; trapframe as fixed frame. |
| Fail-closed | bget/balloc/iget/kfree/sched/bwrite/ilock/ramdiskrw panics; argfd checks; walkaddr PTE_U gate; FSMAGIC/ELF_MAGIC; `panicked=1` freeze; unknown syscall → -1 with diagnostic. |
| Immutable constitution | kernel.ld fixed geography; etext/end self-knowledge; source_id fingerprint; log header as commit marker; trapframe byte offsets fixed by comment; devsw/ syscall table static after init. |
| Provenance at every transition | kernelvec 31-register frame; swtch 14-register frame; buddy split bitmaps; refcounts; log block array; scause_desc strings; ledger receipts (A5). |
| Bounded horizons | timer re-arm; MAXOPBLOCKS chunking; MAXPATH/MAXARG/DIRSIZ; NBUF; descriptor pool NUM=8; sleep loops re-checking condition+killed. |
| Monotonic identity | nextpid under pid_lock; inode numbers; log generations (qcos_generation); dispatch IDs; pipe counters. Never reused within lifetime. |

---

## §13 — Spine alignment

| Spine layer | xv6 precedent | QCOS realization |
|-------------|---------------|------------------|
| **Zone 0** | trampoline + mode panics; ELF/FS magic; log recovery; exec commit | Intent gate: validate envelope → plan → single atomic commit → apply → erase. Blocks recursive self-mutation and memory breaches. |
| **SIR** | defs.h registry; date.h/stat.h flat PODs; types.h floor | Exact rational matrices (int64 num/den pairs). No floats in meaning. Type declarations once, emitted everywhere identically. |
| **DIR** | devsw; syscall table; PLIC routing; file/inode/pipe populations | Execution masks, populations (Shape), topologies LINE \| GRID \| GRAPH. Per-node event policy. |
| **CIR** | sleep/wakeup barriers; swtch; log transactions; timer horizons | Bounded sequential schedules; fixed loop horizons ≤ caps; barrier sync; claim/complete dispatch lifecycle. |
| **MIR** | riscv.h CSR accessors; MMIO macros; string.c byte ops; vm.c walk | Bare-metal micro-ops. C17 freestanding in Phase I; RISC-V bare metal in Phase III. |

---

## §14 — Topology projection

**Phase I (C17 standalone CLI):**
- No interrupts: the dispatch loop is the heartbeat; horizons enforced by
  step counters.
- Arenas linker-carved: 32 working slots, 64 episodic slots, CIR schedule
  buffer, provenance ring — all static structs.
- Door protocol: JSON lines on stdin/stdout (uart precedent: line discipline,
  bounded ring, one answer per request, id echo — A2).
- Fail-closed: bad JSON → error envelope with recovered id (A3 precedent:
  the door must answer, never throw).

**Phase III (4+1 RISC-V):**
- +1 core: M-mode, physical addressing (no satp), owns Zone 0 + crypto
  hashes, programs medeleg/mideleg (event filtering), runs the global
  integrity monitor. Its geography cannot be translated.
- 4 app cores: S-mode, buddy-discipline arenas each, per-core scheduler,
  per-core PLIC enable/threshold.
- Inter-core channels: SPSC rings with virtio semantics (desc/avail/used,
  index-as-identity, in-band status verification).
- Diagnostics: early-write path (uart precedent) — the +1 core can report
  before full init.

---

## §15 — Preserve / Transform / Reject master ledger

**PRESERVE (carry verbatim into QCOS):**
fixed geography; one transition door; per-hart arenas; hartid in tp;
embedded freelists; junk-fill; bounds validation on free; double-free
detection; self-carving init; split bitmap lineage; walk-as-chokepoint;
symmetric teardown; guard pages; copy-only boundary crossings; four-axis
object anatomy; monotonic IDs; two-phase completion; reparenting; sleep =
lock handoff; wakeup scan; push/pop interrupt counting; lock ordering as
contract; commit-point transactions; recovery envelope check; absorption;
goto-bad rollback; claim/complete; bounded rings; early-write diagnostics;
panic = report + freeze; flat dispatch; register-extracted args; capacity
constitution.

**TRANSFORM (keep discipline, change form):**
fork's full copy → attenuated capability derivation;
pipe semantics → door-protocol channels;
virtio rings → inter-core SPSC rings;
devsw → per-endpoint action tables;
proc table → capability/slot tables with QCOS limits (32/64);
log → ledger receipts + CIR commit markers;
PLIC → Zone 0 event router (+1 core) + app-core policies;
sleep/wakeup → CIR barriers;
ELF segments → Zone 0 envelope validation of any artifact;
printf lock → serialized audit-event emission.

**REJECT (never carry):**
runtime heap growth in hot paths; silent degradation; unbounded waits;
probabilistic fallback; connectionist approximation; third-party analytics
or networking in the core; recall of dispatched calls; locks held with
interrupts enabled; aliasing across boundaries; trust without envelope
validation.

---

## §16 — Bit-by-bit synthesis plan

Each piece: self-contained, precedented, witnessed. Build order respects
dependencies; any piece can be resumed independently.

### P0 — MIR floor (partially laid: qcos/types.h)
Seal types.h, add config.h caps (COS_WORKING_LIMIT 32, COS_EPISODIC_LIMIT 64,
max depth 8). **Witness:** compile-time static asserts; qcos_err_string
complete; config_validate rejects zero bounds.
Precedent: types.h, param.h, config.c.

### P1 — Byte primitives
memset/memmove/memcmp/safestrcpy equivalents, O(N), no heap.
**Witness:** overlap cases; safestrcpy guarantees NUL.
Precedent: string.c.

### P2 — Static arena
Fixed slot pools with bitmap provenance (occupied/valid/evicted, one bit per
slot), junk-fill on alloc/dealloc, bounds panic on free, double-free
detection. No malloc. **Witness:** alloc/free cycles deterministic; exhaustion
returns QCOS_ERR_BUDGET_EXHAUSTED; bitmap lineage round-trips.
Precedent: kalloc.c, buddy.c, bio.c.

### P3 — Object slots
Slot struct = {identity, refcount, valid flag, content lock, fixed payload}.
Slot-table lock (structural) vs slot lock (content). **Witness:** two-level
locking; refcount discipline; never consume invalid.
Precedent: buf.h, file.h, proc.h, sleeplock.c.

### P4 — Capability kernel (laid: capability.c)
Already absorbed as qcos/capability.*: attenuated derivation, shared budgets,
ancestor revocation, depth bounds. **Witness:** the six invariant tests in
test_capability.c. Fill remaining kernel.c per P8.
Precedent: capability.c + proc.c discipline.

### P5 — Zone 0 gate
Envelope validation: magic/canonical check → bounds → caps → effect class →
plan → single atomic commit marker → apply → erase. Blocks recursive
self-mutation. **Witness:** malformed envelope answers with recovered id
(A3); interrupt semantics per qcos_interrupted(); committed step replays,
uncommitted discards.
Precedent: trampoline.S, exec.c, log.c recovery.

### P6 — Event and ledger
QCOS_EV_* events: identity and decision only, never payload. Append-only,
serialized emission, early-write path. **Witness:** event round-trip;
rotation preserves history; denial events priced.
Precedent: event.c, printf.c, log.c.

### P7 — Dispatch door
Static method table; O(N) literal scan; claim/complete lifecycle; args from
message only; unknown method → diagnostic + error. **Witness:** test_kernel_ipc
admit→dispatch→reply cycle; malformed line never kills the door.
Precedent: syscall.c, plic.c, uart.c.

### P8 — CIR executor (fills qcos/kernel.c)
Bounded schedules over Shape populations (LINE|GRID|GRAPH); fixed loop
horizons; barriers as condition-lock handoffs; dispatched calls never
recalled; outputs drained in order (qcos_kernel_drain); one lock held per
kernel call (big-lock discipline). **Witness:** schedule steps bounded;
barrier wakeup correctness; drain order preservation.
Precedent: proc.c scheduler/sleep/wakeup, swtch.S, virtio publish/notify.

### P9 — Provenance ring
Every transition records (step, op, keys, pre_hash) into a fixed ring;
qcos.provenance reads it; receipts append to ledger. **Witness:** ring
round-trip; golden_qcos byte-compare (A1).
Precedent: trapframe, buddy split bitmaps, refcounts.

### P10 — SIR core
Exact rational matrices (int64 num/den), no floats in meaning; STRANG
K/T/B/C discipline for difference operators; Euler integer arithmetic.
**Witness:** rational round-trips exact; determinant parity with the C core
(parity_line precedent).
Precedent: defs.h registry + the mathematical corpus.

### P11 — Diagnostic freeze
Structured QCOS_ERR_* + QCOS_EV_PROTOCOL_VIOLATION → report debt → absolute
freeze. Observability survives init failure. **Witness:** panic path emits
record before halt; other cores observe freeze flag.
Precedent: printf.c panic, consputc freeze, uart early write.

### P12 — Phase III projection
4+1 bring-up: +1 core in M-mode physical memory (no satp), delegation masks
as Zone 0 event filter; app cores with P2 arenas + P8 schedulers; SPSC rings
between cores with virtio verification semantics. **Witness:** handshake
across cores (four-tongue precedent: qcos_handshake).
Precedent: start.c, plic.c, virtio_disk.c, SpscQueue.hpp.

---

## §17 — Appendices

### A. File → doctrine index (quick reference)

| File | One-line doctrine |
|------|-------------------|
| kernel.ld | Geography is constitution; PROVIDE self-knowledge |
| entry.S | Per-hart fixed stack; junk-loop freeze on return |
| start.c | Privilege delegated before first app instruction |
| main.c | Ordered boot; volatile started; scheduler never returns |
| memlayout.h | Device map + guard pages + one trampoline page |
| param.h | Every bound declared once, before any table exists |
| trampoline.S | One door both ways; trapframe = config handoff |
| kernelvec.S | Full frame for hostile crossings |
| swtch.S | Minimal frame for cooperative crossings |
| trap.c | Cause-code demux; mode panics; tick heartbeat |
| plic.c | Claim/complete; per-hart policy; defer don't drop |
| printf.c | Locked diagnostics; panic = report + freeze |
| types.h / date.h / stat.h | Small type floor; flat PODs; identity without payload |
| string.c | O(N) byte ops; overlap-safe; safestrcpy over strncpy |
| riscv.h | CSR accessors as literal micro-ops |
| proc.h/proc.c | Four-axis anatomy; monotonic pid; ZOMBIE two-phase |
| spinlock/sleeplock | Owner identity; push/pop; composition |
| pipe.c | Bounded ring; monotonic counters; liveness flags |
| kalloc.c | Embedded freelist; junk fill; bounds panic |
| buddy.c | Power-of-two arena; split lineage; self-carving |
| bio.c/buf.h | Fixed pool; three state bits; MRU recycle |
| list.c | Circular intrusive; panic on empty pop |
| log.c | One commit point; recovery = envelope check; absorption |
| fs.c/fs.h | Layered FS; lifecycle comment as constitution; namex walk |
| file.c/file.h | devsw; tagged dispatch; fdalloc scan |
| exec.c | Magic first; atomic commit; overflow guards |
| sysfile.c | goto-bad rollback; all-or-nothing acquisition |
| sysproc.c | Killed-check in every sleep loop |
| syscall.c | Register-extracted args; flat table; graceful refusal |
| uart.c | Literal MMIO; bounded rings; early-write diagnostics |
| console.c | Line discipline; control chars at interrupt level |
| ramdisk.c | Assert → copy → flag; synchronous minimal driver |
| virtio*.c | Shared rings; index-as-id; double verification |
| vm.c | walk chokepoint; symmetric map/unmap; copy-only crossings |

### B. Constitutional caps table (for qcos/config.c)





### C. Standing witness requirements (every piece)
1. Byte-identical output for identical input (A1).
2. Selftest with frozen golden fixtures (golden_qcos precedent).
3. Malformed input answered, never fatal to the door (A3).
4. Refusals priced in the ledger (A5) with identity + decision, never payload.
5. Exhaustion returns budget error; no path grows a table.
6. Every commit single-point; every teardown symmetric to construction.

### D. Continuation queue
After synthesis begins: think_loop.py, grow.py, auto_fixer.py (bot layer),
then ref_bridge.js, ref_bridge_qcos.js, bench_render_backends.py — all under
this doctrine, all converging on the Phase II team and Phase III 4+1 core.

---
END OF SYNTHESIS — substrate complete; construction order sealed.


