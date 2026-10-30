# Worker brief: Port test machine and COS

Hand this text, unchanged, to a worker agent (Agent tool, general-purpose). Before doing anything it should read docs/STATUS.md and its own docs/PROGRESS_*.md file, and continue from the last line there.

You are the worker assigned to PORT THE TEST MACHINE (reference/src/cbt.js), THE COS MODEL (reference/src/cos.js) AND THE READING HELPERS to C++. Project folder: /home/claude/saem-unified. Work autonomously, do not message the user.

Read docs/STATUS.md (short), then docs/PORT_SPEC_cos.md and follow that brief exactly: it is your full assignment (scope, files you own, methods to register, the Soul definition, fidelity rules, build and test commands).

Changes to the brief:
1. Three workers run at once now: you (cbt/cos port), the forecast port (owns ef.*, ef_api.cpp, ef_util.hpp, cases_ef), and the Python interface (owns saem/, app/, tests/test_*.py, tests/e2e_shots.py). The main agent owns api.*, cli.cpp, gen.*, util.hpp, json.hpp, numfmt.hpp, sha256.hpp, tools/*, tests/diff/run.py, Makefile and docs/STATUS.md. Never edit those. Never write into build/. Never run `make clean` or `make all`. Build only into your own folder (build_cos) as the brief says.
2. You can be cut off at any moment by a usage limit. Work in small verified steps: text helpers (parseDelimited, yearFromHeader, normKey, syllabus matcher, tag) first; then cbt (parseMCQText, parseMCQCsv, scoreTest, fmtClock, hashQuestions, demo); then paper reading (splitMCQ, normAnswer, parseKeyMap, parsePapers, recordsFromRows, scriptLang, autoTag); then bank and rows helpers; then nudge, plan, learn, forget, grade, attemptRecord, assemble, drill; then verdict, audit, selfTest, coreHash, receipt, core.info. Compile and run diff cases after each step. After each milestone append one line to docs/PROGRESS_cos.md: what agrees, what remains, the exact command to continue.
3. The JS specs are reference/src/cbt.js, reference/src/cos.js and the reading functions of reference/src/ef.js (detectDelimiter, parseDelimited, yearFromHeader, kwRegex, compileSyllabus, tagWithSyllabus, normKey). Tests that show intended behaviour: reference/test/cos.test.js, reference/test/ef.test.js. For end-to-end diff cases that need a forecast, write fixtures once with node from the JS bridge (tools/ref_bridge.js).

Final report under 200 words, as the brief says.
