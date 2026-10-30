# The C17 sovereign kernel (`core/c17/`): reference

Status 2026-10-30: v0 complete and checked (`python3 tools/check_c17.py`, about 20 seconds, 18 check groups, all passing).
It is the "+1" sovereign core of the 4+1 plan: it decides what may enter and keeps the receipts. The C++ engines (Math Brain, forecast,
test machine) are the "4" workers and sit behind it. Design reasons: `docs/ARCHITECTURE.md`. What xv6 taught: `docs/knowledge/xv6.md`.

## Rules, each one enforced by a check and not by a promise

| Rule | Where it is enforced |
|---|---|
| Zero heap: no malloc/free, no allocation of any kind | `check_c17.py`: objects import only memcpy/memmove/memset/memcmp/strlen; sources contain no malloc/free/alloca |
| Zero global state | `check_c17.py`: no writable data symbol, no `.data`/`.bss` in any object. All state is in memory the caller hands in |
| Zero numerical approximation | `check_c17.py`: no float/double/math in sources; builds with `-mgeneral-regs-only` (the compiler refuses FP and vector registers) |
| Capacities are numbers in one header | `cos_limits.h` (`COS_WORKING_LIMIT 32`, `COS_EPISODIC_RING 64`, ...); every limit is part of the seal |
| Freestanding | only `stdint stddef stdbool stdalign stdatomic string` headers; stack use per function at most 2 KB (`-Wstack-usage`) |
| C ABI | every header is valid C17 alone and C++17 together, opaque types, `extern "C"` |
| Lock-free hot paths | pool (tagged Treiber stack), counters, freeze flag, quarantine mask: atomics, each hot field on its own cache line; only the cold journal append takes a tiny `atomic_flag` lock |

## Modules (bottom to top)

| File | What it is | Tests (checks) |
|---|---|---|
| `cos_limits.h`, `cos_status.h`, `cos_le.h` | all capacities; one status enum (0..11 equal `saem::nx::Err`); explicit little-endian read/write | compiled everywhere |
| `cos_sha256.*` | SHA-256, HMAC-SHA-256, constant-time compare, hex | 11 NIST/RFC vectors; equals Python hashlib/hmac on 596 inputs; equals the C++ engine's SHA-256 on 1,422 inputs |
| `cos_pool.*` | fixed pool; handle = generation<<32 or index, so a stale or forged handle is refused (`COS_E_STALE`, `COS_E_INVALID`), double free detected; `retries` counts failed CAS (the contention number) | 34, incl. 4 threads |
| `cos_regs.*` | L1: 32 registers, one cache line each, LRU with pins; L2: 64-slot episodic ring with free-running counters; a full table is an answer (`COS_E_FULL`), never a crash | 893 |
| `cos_blockdev.h` | the only door to storage: read, write, flush callbacks the caller fills | RAM device with power cut and torn writes (`tests/c17_ramdev.h`) |
| `cos_wal.*` | write-ahead redo log, up to 30 blocks per atomic transaction, header block is the commit point | 165, a power cut at every write, 3 tear modes, a crash during recovery, a lying device |
| `cos_journal.*` | append-only records chained by SHA-256, every append one WAL transaction; `verify` walks the whole chain | 216, tamper, swap, power cuts, 3 concurrent writers |
| `cos_gate.*` | Zone 0: pure function `cos_gate_scan(bytes, n, max_len, flags)` | 77 checks, 21 million UTF-8 buffers against an independent validator, every code point against Python's Unicode database, 200k+200k random strings, 20k random JSON nests, 4 threads |
| `cos_seal.*` | digest of limits + build id + constitution articles + method table; tag = HMAC(key, digest) | digest and tag equal `tools/seal.py` (independent Python), every byte and field changes the digest |
| `cos_core.*` | the handle: gate + seal + quarantine + freeze + journal | 186, see below |

## One call

```c
size_t n = cos_core_bytes();                        /* about 17.8 KB: core + journal, the caller provides it, 64-byte aligned */
CosConfig cfg = { .seal = {articles, na, methods, nm, "build-id"}, .expected_digest = ..., .expected_tag = ...,
                  .key = key, .keylen = 32, .journal_dev = dev, .format_journal = false, .tick = now };
CosCore *core;
if (cos_core_open(mem, n, &cfg, &core) != COS_OK) { /* refuses to start: the tables are not the signed ones, or the journal is broken */ }
CosVerdict v = cos_core_gate(core, METHOD_ID, bytes, len, tick);
if (v.zone != COS_ZONE_ACCEPT) { /* v.status, v.rule, v.offset say exactly why; nothing reached the engines */ }
```

`cos_core_gate` order: frozen? then the seal intact? (a changed byte freezes) then known method? then quarantined? then Zone 0 scan.
`tools/seal.py` builds the digest and tag from a JSON spec at release time; the core only verifies.

## The three failure levels as implemented

| Level | Verdict zone | What triggers it in code | What lifts it |
|---|---|---|---|
| Reject | `COS_ZONE_REJECT` | unknown method; too long; invalid UTF-8; NUL, control, bidi, invisible, joiner, private-use, noncharacter; JSON brackets unbalanced or deeper than 32 | nothing: the next request is judged alone |
| Quarantine | `COS_ZONE_QUARANTINE` | 8 rejects IN A ROW from one method (an accepted input clears the count); journaled | `cos_core_release(core, method, "Teacher name", tick)`: the name passes Zone 0, the RELEASE record is written FIRST, then the method opens. It survives restarts (replayed from the journal) |
| Freeze | `COS_ZONE_FREEZE` | the sealed tables changed (checked on every call); `cos_core_verify` finds a broken journal chain; `cos_core_freeze` by the caller; the first reason wins and is journaled once | only a restart: `cos_core_open` re-verifies the seal and the whole chain |

No receipt, no action: `open`, `release` and `audit` fail if the journal cannot be written. A broken journal device does not freeze the gate
(rejecting bad input needs no receipt) but every action that needs a receipt returns `COS_E_IO` until the core is reopened.
Audit kinds below `COS_EV_USER` (256) belong to the core and cannot be forged through `cos_core_audit`.

## Zone 0 decisions (so nobody has to rediscover them)

- Strict UTF-8 (Unicode Table 3-7): no overlong forms, no surrogates, nothing above U+10FFFF.
- Refused: NUL; C0 controls except tab, LF, CR; DEL and C1; direction overrides, embeddings, isolates (U+202A-202E, U+2066-2069); zero-width space,
  word joiner and invisible operators (U+200B, U+2060-2064), BOM (U+FEFF, even at offset 0), U+180E, tag characters and variation selectors 17-256;
  private use; noncharacters; the replacement character and annotation marks.
- ZWJ and ZWNJ are accepted only right after a character of the Indian scripts (U+0900-0DFF, U+A8E0-A8FF) or the Arabic script (U+0600-06FF,
  0750-077F, 0870-08FF, FB50-FDFF, FE70-FEFE), so Hindi, Bengali, Tamil ... Urdu and Persian pass; emoji ZWJ sequences are refused on purpose.
  `check_c17.py` proves it against Python's Unicode database: every assigned BMP character of those scripts accepts a joiner (found and fixed
  55 characters that the first version missed).
- Accepted on purpose: LRM, RLM, Arabic letter mark (real Urdu text has them), soft hyphen (PDF text extraction has it), U+2028/2029, variation
  selectors 1-16. Unassigned code points are accepted: the gate carries no Unicode table, so it does not go stale when Unicode grows.
- The gate checks representation only. What the text means is decided later, by the Semantic IR and the engines.

## Honest limits (read before trusting anything)

1. The seal is software. HMAC is symmetric, so whoever can read the key on a device can forge the tag; and an attacker who can write
   arbitrary memory can corrupt the core's own fields. Real immutability is the RISC-V PMP lock of phase 3; Ed25519 signatures come in phase 2.
2. Quarantine is per method, not per source. In classroom mode one student could quarantine a method for everybody until a teacher releases it.
   Phase 2 adds a source dimension.
3. Rolling the journal device back to an older complete image after a restart cannot be detected from the device alone (the running core does
   detect it); keep the count and head hash elsewhere (`cos_journal_head`).
4. The journal is finite: when it is full, receipts fail with `COS_E_FULL`, which blocks actions. Rotation and archival are not designed yet.
5. The seal is re-hashed on every call, for instant lockout: about 3.5 microseconds for a tiny constitution, about 200 microseconds for 40 KB
   (about 5,000 calls per second per thread). Measure with the real constitution; if it matters, check the seal every N calls (a limit that
   would itself be sealed).
6. Needs 64-bit compare-and-swap (x86-64, ARMv8, RV64 with the A extension).
7. C# interop is not written yet and cannot be compiled in this environment.

## How to run

```
python3 tools/check_c17.py            full check, about 20 s
python3 tools/check_c17.py --quick    tests at -O2 only
python3 tools/seal.py digest|tag|emit-c SPEC.json    the release tool
```
