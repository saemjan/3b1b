# Architecture (implemented map)

Status doc. For proposals see FUTURE_ARCHITECTURE.md; for rules and KPIs
see THINK.md; for the operational contract see README.md.

## Video factory (Python)
content CSV → schema gate (schema_validator.py) → physics-oracle gate
(tools/physics_oracle.py v2, includes narration trust) → audio gate
(generate_audio.py: XTTS-v2 + resample + soundscape mastering + LUFS) →
render gate (render_universal.py: orientation-aware frames, beat timeline
with word-sync fallback, failure-tracked primitives, render report) →
visual-QA gate (tools/visual_qa.py: frames + loudness) → FFmpeg stitch
(batch_runner.py) → ledger (tools/ledger.py) → output_shorts/<id>_final.mp4

## Cognitive core (core/src, C++17, stdlib only)
Door: api.* + cli.cpp (line protocol; --source-id). Canons: numfmt, json,
util, sha256. Math Brain: gen.*. Reversible/quantum: rev, qreg (cursor
machine), spectral (e^{-iHt}). Cognition: cog (Bernoulli log-odds), ef
(ridge-LR forecast under constitutional caps). Constitution: cos (articles
A0–A6, caps, coreHash, receipts). QCOS kernel: qcos (gate fail-closed, IR
ladder SIR→DIR→CIR→MIR, L1=32, L2=64, provenance chain, 12-point self-test).
Growth: grow.c + grow_reg.cpp (learn/recall/distill; quarantine in grown/).
Build: tools/build.py (body fingerprint), Makefile.mk (clerk), CMake wrapper.

## Clients (one door, four tongues)
saem/core.py + saem/qcos_shell.py (Python), SaemQcos/Bridge.cs (C#),
tools/ref_bridge.js + ref_bridge_qcos.js (JS ruler, dev only).

## Witnesses
tools/build.py verify (body), qcos.boot (self-test), tests/diff/run.py
(C++ vs JS), tools/golden_qcos.py (frozen fixtures), pytest (engines),
oracle + QA + LUFS (pipeline), ledger (feedback).

## CI (.github/workflows/render_shorts.yml v3)
validate → build-core → core-tests → engine-tests → generate-validate →
render (opt-in matrix) → reflect (think-bot). Render gate: [render] tag,
`render` label, or dispatch render_videos=true.

## Known debt (THINK §4)
- render_universal v2 duplicates engine numerics internally; v3 must import
  the engine modules (single canon).
- visual transitions (visual_kit) removed with v2 renderer; return as grown
  primitives.
