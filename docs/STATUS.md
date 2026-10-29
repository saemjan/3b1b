# Saem Unified (sir): status and handoff

Read this first, every session. It exists so no work burst re-orients from
scratch: read this, run the resume commands, continue at the named step.
Law lives in VISION.md / README.md / OS.md / qcos.cxn. **This file holds only
volatile state** (step pointer, debts, next action) — by §14 it must never
restate law; if it ever contradicts VISION.md, VISION.md wins and this file
is amended with a §24 log entry.

Last updated: 2026-10-28 (compass landed; step 3–4 code delivered; VISION.md v2.1 patched)
Authoritative live state: `python3 tools/where.py` — it asks the doors and
reads the ledger, so it cannot go stale the way this table can.

## The ask (unchanged since 2026-10-01)
See VISION.md §1: witnessed physics/maths teaching videos now (Phase 1),
parallel ed-tech team next (Phase 2), QCOS on 4+1 RISC-V last (Phase 3).
Immutable core in C/C++/C#; Python is orchestration edge only.

## Architecture (decided, do not reopen)
See VISION.md §3–§8 and OS.md §13–§14. One breath: reference/src/*.js are the
rulers (SPEC, dev-only, never shipped) | core/src is a C17/C++17 one-door JSON
core | saem/ is a stdlib-only Python edge | SaemQcos/ is the C# facade | all
four tongues are emitted by tools/qcosc from qcos.cxn | determinism via seeded
RNG, no clocks in core, -ffp-contract=off -fno-fast-math.

## State snapshot (convenience only — where.py is authoritative)
| Piece | Status |
|---|---|
| gen-3 upgrades: engines, gates, tools, bots, bridges, bench | DONE 2026-10-27 |
| Constitution docs: README/VISION/OS + CONTEXT_ANCHOR merge | DONE 2026-10-27 |
| §21 step 1 — canon artifacts | unwitnessed (user ran, exit lines pending) |
| §21 step 2 — reference/src rulers | BLOCKED on input (needs gen.cpp + ef.hpp + cos.hpp) |
| §21 steps 3–4 — corpus + hygiene | CODE DELIVERED 2026-10-28, pending commit |
| §21 steps 5–27 | queued, in order |
| Resume compass (where.py + STATUS.md) | LANDED 2026-10-28 |

## Open debts (priced, expiring — never hidden)
- parity_line exits 2 (rulers absent) → cured by step 2.
- qcos.schema.json + generated bindings uncommitted → cured by step 1 commit.
- 13 deferred methods expire 2026-12-31 → cure = cos.js constitution hash + papers scope doc.

## Next action (2026-10-29)
User: run `python3 tools/where.py` to confirm compass state; paste step 1's
`[qcosc] in sync…` line + `exit=0` (or say "not run, do it now"); paste
`core/src/gen.cpp`, `core/src/ef.hpp`, `core/src/cos.hpp` (or `ls reference/src`
output if it exists locally).
Assistant: witness step 1; deliver the four JS ruler files with --selftest;
close step 2; update this file and the ledger.
Phase G queued after step 14; COMPILER.md landed v1. 

## Resume commands
python3 tools/where.py
python3 tools/where.py --diff
python3 tools/ledger.py verify
# then say "continue" and the next step's files land.
