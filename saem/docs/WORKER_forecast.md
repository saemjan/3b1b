# Worker brief: Port forecast engine to C++

Hand this text, unchanged, to a worker agent (Agent tool, general-purpose). Before doing anything it should read docs/STATUS.md and its own docs/PROGRESS_*.md file, and continue from the last line there.

You are the worker assigned to PORT THE FORECAST ENGINE (reference/src/ef.js) TO C++. Project folder: /home/claude/saem-unified. Work autonomously, do not message the user.

Read docs/STATUS.md (short), then docs/PORT_SPEC_forecast.md and follow that brief exactly: it is your full assignment (scope, files you own, methods to register, fidelity rules, build and test commands).

Changes to the brief:
1. Three workers run at once now: you (forecast port), the cbt/cos port (owns cbt.*, text.*, cos.*, cos_api.cpp, cases_cbt/cases_text/cases_cos), and the Python interface (owns saem/, app/, tests/test_*.py, tests/e2e_shots.py). The main agent owns api.*, cli.cpp, gen.*, util.hpp, json.hpp, numfmt.hpp, sha256.hpp, tools/*, tests/diff/run.py, Makefile and docs/STATUS.md. Never edit those. Never write into build/. Never run `make clean` or `make all`. Build only into your own folder (build_ef) as the brief says.
2. You can be cut off at any moment by a usage limit. Work in small verified steps: featureTokens, stem, prepare first; then clustering (buildFold, labelFold); then features and hazard; then logistic regression (solve, fitLR, predictLR); then evaluation (pickTop, capsFor, evalFold, chooseMethod, calibrate); then topicForecast, termsLabel, reasonFor; then analyze. Compile and run diff cases after each step. After each milestone append one line to docs/PROGRESS_forecast.md: what agrees, what remains, the exact command to continue.
3. The JS spec is reference/src/ef.js. How cos.js and the tests call it: reference/src/cos.js, reference/test/ef.test.js, reference/test/cos.test.js. Bank generators: gen.demoBank is already in the C++ core.

Final report under 200 words, as the brief says.
