# xv6-RISC-V (MIT 6.S081, Fall 2019, lab edition): what it teaches the Saem / QCOS core

Read on 2026-10-27 from the user's attachment `xv6-riscv-fall19.zip`. Study copy: `third_party/xv6-riscv-fall19/` (MIT licence,
Kaashoek, Morris, Cox). Size: kernel 6,867 lines of C and assembly, user programs 5,408 lines, 22 system calls.
This is the lab edition: it adds `buddy.c`, `list.c`, `sys_ntas` (lock-contention counters), two disks, and the lab tests
(`kalloctest`, `bcachetest`, `cowtest`, `mmaptest`, `alarmtest`, `symlinktest`, `uthread`) with their graders.

Read in full: param.h, memlayout.h, spinlock.c, kalloc.c, buddy.c, list.c, bio.c, sleeplock.c, log.c, proc.h, proc.c, start.c, main.c,
entry.S, kernel.ld, swtch.S, syscall.c/h, trap.c, printf.c, pipe.c, exec.c, vm.c, buf.h, fs.h, file.c, virtio_disk.c, fs.c (first 420 lines).
Skimmed: riscv.h, sh.c (parser), console.c, uthread.c, usertests.c (names), kalloctest.c, bcachetest.c, the Makefile and graders.
NOT read in detail: trampoline.S, kernelvec.S, sysfile.c, sysproc.c, uart.c, plic.c, string.c, mkfs.c, the rest of fs.c (directories,
path lookup), the bodies of the cow/lazy/mmap/symlink tests. Nothing below depends on them.

## 1. What it is, in one paragraph

A complete multi-core Unix in about 7,000 lines of plain C with no `malloc` anywhere in the kernel. Every table has a compile-time
size (`param.h`: NPROC 10, NCPU 8, NOFILE 16, NFILE 100, NINODE 50, NBUF 30, LOGSIZE 30, MAXARG 32, MAXPATH 128). The only dynamic
resource is 4096-byte pages from a free list. One door leads in (a trap, then a constant table of 22 functions). Every field says
which lock protects it. Crash safety comes from one small layer (a redo log) that the layers above never need to know about.

## 2. The ideas worth keeping (each with where to see it)

1. **A full table is an answer, not a crash.** `allocproc` returns 0 when all NPROC slots are used, `filealloc` returns 0, `kalloc`
   returns 0, and the caller turns that into -1. (xv6 still panics when its own internal tables run out: `bget: no buffers`,
   `iget: no inodes`, `balloc: out of blocks`, `too big a transaction`. That is acceptable in a teaching OS and not in a product a
   student uses offline. We return `Err::Full` everywhere and decide per level what to do, see 4.)
2. **Capacity is a number printed at build time.** With no heap, the worst-case memory of the whole kernel is `sizeof` of its tables.
   `COS_WORKING_LIMIT = 32` and the 64-slot episodic ring belong in one header, with `_Static_assert` on every derived size.
3. **One narrow door with a constant table.** `usertrap()` calls `syscall()`, which indexes `static uint64 (*syscalls[])(void)` by
   the number in a7. Out of range or empty slot: print and return -1. Nothing else enters the kernel. This is the Zone 0 gate.
4. **Never trust a raw pointer or length.** `argint/argaddr/argstr` fetch; `fetchaddr` checks `addr < p->sz`; `copyin/copyout/copyinstr`
   walk the caller's page table (`walkaddr` demands PTE_V and PTE_U) and never dereference the caller's address; `copyinstr` is bounded
   and fails when no NUL is found. `exec` checks ELF magic, `memsz >= filesz`, `vaddr+memsz` overflow, page alignment, `argc < MAXARG`,
   and that the stack never underflows.
5. **Commit last, free everything on any failure.** `exec` builds the whole new image on the side (`goto bad` frees it) and only at the
   end swaps `p->pagetable`, `p->sz`, `epc`, `sp`. The log's header write is likewise the single commit point.
6. **Poison what you free.** `kfree` fills the page with 1s, `kalloc` with 5s, so a stale pointer or an unread allocation shows at
   once. We add what xv6 lacks: a generation number in every handle, so a stale handle is refused, not just ugly.
7. **Every field names its protector.** `proc.h`: "p->lock must be held when using these ... these are private to the process, so
   p->lock need not be held." `fs.c` spends 60 lines of comment on the rules for `icache.lock`, `ip->ref`, `ip->lock`, `ip->valid`.
   `acquire` panics on a double acquire, `release` panics if not held, `sched()` checks four invariants before switching
   (holds p->lock, noff == 1, state != RUNNING, interrupts off). Invariants are executable, not just written.
8. **Lost wakeups are the classic bug.** `sleep(chan, lk)` takes `p->lock` BEFORE releasing `lk`, so a `wakeup` (which scans the table
   taking each `p->lock`) cannot slip between "check the condition" and "go to sleep". Lock-free code has the same bug under another
   name; the cure there is a sequence number compared after publishing, never "check then wait".
9. **A task is a five-state machine in a fixed table.** UNUSED, SLEEPING, RUNNABLE, RUNNING, ZOMBIE. `kill` only sets a flag (and wakes
   a sleeper); the victim dies itself when it next crosses the boundary (`usertrap` checks `p->killed`). A finished task stays
   ZOMBIE holding its status until the parent `wait`s; orphans are adopted by `init` (`reparent`). Nothing is lost, nothing is
   killed at an unsafe point. `procdump` takes no locks "to avoid wedging a stuck machine further": a diagnostic path must not depend
   on the thing that may be broken.
10. **The buffer cache is our L1.** `bio.c`: NBUF buffers in one doubly linked list, head.next = most recently used. `bget` finds the
    block (refcnt++) or recycles the LEAST recently used buffer with refcnt 0. `brelse` moves a buffer to the front when its refcount
    reaches 0. `bpin/bunpin` keep a block in the cache while the log needs it. 32 working registers with LRU spill is this structure.
11. **The pipe is our L2.** `pipe.c`: a 512-byte ring with two ever-growing counters. Full: `nwrite == nread + PIPESIZE`. Empty:
    `nread == nwrite`. Slot: `n % PIPESIZE`. No wrap ambiguity, and the same idiom is lock-free with 64-bit counters.
12. **Write-ahead log: all-or-nothing storage in 237 lines.** `begin_op/end_op` bracket an operation; `log_write` records block numbers
    (absorbing repeats) and pins the buffer; `commit` = write blocks to the log, write the header (the commit point), copy to home
    locations, zero the header. `recover_from_log` at boot repeats the copy, which is safe to repeat. Admission control:
    `begin_op` sleeps while `lh.n + (outstanding+1)*MAXOPBLOCKS > LOGSIZE`, so a transaction can never overflow the log.
    Group commit: the commit runs only when no operation is outstanding. Layering: blocks, log, inodes, directories, names; each
    layer calls only the one below.
13. **Reference counts with two meanings.** An inode is freed only when its in-memory `ref` is 1 (the caller's) AND its on-disk `nlink`
    is 0 (`iput`). Every release that might free must be inside a transaction.
14. **Boot order is a protocol.** `main()`: hart 0 initialises the world in a fixed order, runs `__sync_synchronize()`, sets `started = 1`;
    other harts spin on `started`, fence, then do only their per-hart setup. A release-store / acquire-load handshake, in C17 terms.
15. **Panic freezes the machine on purpose.** `panic` turns off printf locking (so it cannot deadlock on its own message), prints, sets
    `panicked`, and every `consputc` then spins forever. That is "fail-closed freeze" in 10 lines.
16. **The image is checked before it is trusted.** `fsinit` reads the superblock and panics unless `magic == FSMAGIC`; `mkfs` builds the
    image offline. The same shape fits a sealed knowledge-and-constitution image.
17. **Ownership hand-off with hardware.** `virtio_disk.c`: `b->disk = 1` means "the device owns this buffer". The driver publishes
    a descriptor index in the `avail` ring, fences, then increments `avail[1]`; the device answers through the `used` ring. Free
    running 16-bit indices, masks, barriers: a real lock-free single-producer ring shared with another processor. This is the
    pattern for node-to-node and node-to-accelerator messages in Phase 2 and 3.
18. **Parsing without allocating.** `sh.c`: `gettoken(&s, es, &q, &eq)` returns a token class and start/end pointers INTO the input;
    `peek`, then recursive descent (`parseline`, `parsepipe`, `parseexec`), then `nulterminate` writes the NULs in place. Fixed
    `MAXARGS`. (xv6's shell mallocs its nodes; we put them in a static arena. See `cos_arena` in ARCHITECTURE.md.)
19. **The allocator that lives in its own memory.** `buddy.c`: power-of-two blocks over a caller-given range; per size, a free list, an
    `alloc` bit array and a `split` bit array; the tables are carved from the start of the same range and marked allocated
    (`bd_mark_data_structures`); `bd_free` merges with the buddy while the buddy is free. A fixed arena with a hard ceiling.
    That is the path to running our C++ engines under a fixed memory budget (`std::pmr` over such an arena).
20. **Scalability is measured, with a budget.** The lock lab: `sys_ntas` reports failed test-and-set counts. `kalloctest` test0 passes only
    if fewer than 10 happen; test1 checks conservation (after exhausting memory, at most 1000 pages of 32768 are missing).
    `bcachetest` requires fewer than 500. So: a number, a threshold, and a conservation law.
21. **The test suite is adversarial and isolated.** `usertests.c` (2,197 lines) names each bug class: `kernmem` (a program reads kernel
    memory and must be killed), `validatetest` and `badarg` (garbage pointers into every call), `sbrkfail`, `mem`, `forkfork`
    (resource exhaustion), `exitiputtest`, `reparent`, `concreate`, `bigdir`, `fourteen` (name-length limit). Each test runs in a
    forked child, so one crash cannot hide the rest; the only success line is `ALL TESTS PASSED`.

## 3. Map: xv6 piece to Saem piece

| xv6 | Saem / QCOS piece | Where |
|---|---|---|
| param.h | all capacities in one header with static asserts | `core/c17/cos_limits.h` |
| kalloc.c free list, poison | fixed pool, lock-free free list, generation handles | `cos_pool` |
| bio.c LRU, pin | 32 working registers, LRU, spill to the ring | `cos_regs` |
| pipe.c counters | 64-slot episodic ring | `cos_regs` (ring), `nx::ring` (MPMC) |
| log.c | crash-safe, hash-chained journal (attempts, atoms, audit) | `cos_journal` |
| syscall.c, copyin | Zone 0 gate: constant method table, bounded input checks | `cos_gate` |
| exec.c | build aside, commit last (SIR compile, paper assembly) | `cos_sir` (next) |
| spinlock.c counters | contention counters, `nts` budget tests | `cos_pool` tests |
| proc.c state machine, kill flag, reparent | job table for parallel nodes (Phase 2) | later, `nx` |
| printf.c panic | freeze flag in the core handle, checked at every entry | `cos_gate` |
| fsinit magic, mkfs | sealed image: magic, version, SHA-256 | `cos_seal` |
| sh.c parser | zero-copy tokenizer into a static arena | `cos_sir` (next) |
| buddy.c | fixed arena with a ceiling, for variable-size data | later |
| virtio rings | node-to-node and node-to-device messages | Phase 2/3 |
| usertests, lock-lab graders | adversarial tests in isolation, contention and conservation checks | every module test |

## 4. Where xv6 is weaker than we need (and what we do instead)

- It has ONE failure level: panic. A student on a phone must not lose a session because one input was odd. We use three:
  Reject (one request, with a reason code), Quarantine (one module or source stays out until a person re-approves it),
  Freeze (the whole core, only when the seal, the journal chain or an internal invariant is broken). The Forbidden Zone maps to these.
- It uses global state everywhere (`proc[]`, `bcache`, `kmem`, `nlock`). We keep all state in one caller-owned `CosCore` handle.
- It protects against crashes, not tampering. We chain the journal with SHA-256.
- It uses coarse spinlocks (the lab exists because `kmem` and `bcache` have one lock each). We prefer single ownership plus atomics,
  and keep one tiny `atomic_flag` lock for cold paths.
- It has no capabilities: any holder of a descriptor may use it. Nucleus (see `docs/knowledge/kernel.md`) supplies that.

## 5. RISC-V facts for Phase 3 (custom silicon, the "4+1" layout)

- Every hart enters at 0x80000000 in M-mode with its own 4 KB stack: `sp = stack0 + 4096*(mhartid+1)` (`entry.S`). `start()` sets
  mstatus.MPP to S, `mepc = main`, `satp = 0`, delegates all traps (`medeleg = mideleg = 0xffff`), arms the CLINT timer, puts the hart
  id in `tp`, and executes `mret`. Kernel text is mapped read-execute, data read-write (no page is both). Kernel stacks sit apart with
  an unmapped guard page each (`KSTACK(p)`). Page tables are Sv39: three levels of 512 eight-byte entries.
- Proposal (not in xv6): the fifth hart, the sovereign one, never executes `mret`. It stays in M-mode, runs the gate and the monitor,
  and owns the constitution region. The four worker harts drop to S-mode and run engines. PMP entries with the L bit set cannot be
  changed even by M-mode until a system reset (RISC-V privileged spec v1.10, section 3.6: "Locked PMP entries may only be unlocked with
  a system reset"; checked in `doc/riscv-privileged-v1.10.pdf`). That is "immutable core" enforced by the silicon, not by convention.
  Workers talk to the sovereign hart through virtio-style rings (idea 17).

## 6. What we do not take

The file system (inodes, directories, paths), the page-table code, the console and UART drivers, the shell, and the trampoline are
teaching a general-purpose OS. We take their discipline, not their features. The Saem model stores a few hundred question atoms and
sixty attempts, not a directory tree.

## 7. Open questions

- Which block device does `cos_journal` write to on phones (a file with `fsync`, a SQLite page, raw flash)? It is a callback table,
  so the answer is per platform. Phase 2 puts SQLite behind it (L3 knowledge atoms).
- A real signature needs a public-key scheme. Phase 1 uses SHA-256 seals plus an HMAC; Ed25519 comes with Phase 2.
