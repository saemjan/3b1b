2026-10-27 design done: docs/knowledge/xv6.md, docs/ARCHITECTURE.md. Code in core/c17 NOT started yet. Next: cos_limits.h, cos_status.h, cos_sha256, cos_pool, cos_regs, cos_journal, cos_gate, cos_seal, cos_core; tests in core/tests/c17_*_test.c; tools/check_c17.py.
2026-10-28 done and tested: cos_limits.h, cos_status.h, cos_sha256 (NIST + RFC 4231 vectors, 11 checks), cos_pool (lock-free, generation handles, 34 checks incl. 4 threads). Next: cos_regs, cos_wal, cos_journal, cos_gate, cos_seal, cos_core, tools/check_c17.py.
2026-10-30 C17 sovereign kernel v0 COMPLETE and checked: `python3 tools/check_c17.py` = 18 check groups, all pass, about 20 s. Added since 10-28: cos_regs (893 checks),
cos_wal (165, power cut at every write), cos_journal (216), cos_gate (77 checks; 21 million UTF-8 buffers vs an independent validator; every code point vs Python's
Unicode database; found and fixed a real gap of 55 Indic/Arabic extension characters that would have refused their joiners), cos_seal (C digest = Python tools/seal.py),
cos_core (186 checks: refuses to start on wrong tables or key or without a first receipt; freeze on one changed byte; quarantine after 8 rejects IN A ROW, survives restart by
replaying the journal, lifted only by a journaled approval whose name passes Zone 0; journal monitor; power cuts at every write; threads). Reference: docs/KERNEL_C17.md.
Next: SIR (semantic IR: exact rationals, zero-copy tokenizer into a static arena, independent exact checker), then hook the gate in front of the C++ door, the C header and
C# interop (verify compiler availability), the Constitution of Medina (docs/WORKER_constitution.md) sealed through tools/seal.py, nucleus injection (docs/NX_BRIEF.md).
