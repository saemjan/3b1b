# Worker brief: the Constitution of Medina as the core constitution

The project instructions (changed 2026-10-26) say: "The core Constitution of our Models will be the Constitution of Medina by
Prophet Muhammad: the Quran and sunnah of the Prophet Muhammad and his companions that drives his actions, intentions and words."
The model's constitution is its immutable core: it is hashed into the Soul, checked live by `audit()`, and shown on the Rules page.
Today it holds six operational rules (see `CONSTITUTION` in `reference/src/cos.js`). This task makes the Constitution of Medina its source.

## Source and how to use it

The source is the project document `Constitution-Medina.pdf`. Read it with the Projects tool (`project_read`, then Read the saved file in
pieces; `project_search` finds clauses). Use ONLY what the document says. Quote clause numbers as that document numbers them. Do not
invent citations, and do not attribute rulings to sources the document does not contain. Where an article of our model is an interpretation
(a software behaviour derived from a principle), label it "derived", not "stated". Keep the language respectful and plain. The model serves
every student and teacher alike, in every language and board; say so only where the document's principles support it.

## Task

1. Write `docs/CONSTITUTION.md` (under 200 lines):
   a. The document's principles in plain words, each with its clause numbers (for example: keeping covenants and honesty, justice,
      protection of every community and of the weak, mutual aid, consultation and settling disputes, individual responsibility, the
      sanctity of the shared space, each community's own practice). Use only what the text really contains.
   b. Our articles: 8 to 10 articles of the model, each = one principle + the software behaviour that keeps it + how it is checked live
      (audit) and tested. The six existing rules must each find an article: chance not promise, tested before trusted, solutions say where
      they came from, opinion nudges never decides, data stays here, bounded memory. Add what the principles demand that we lack, for
      example: no hidden tracking, a person decides (teacher approval before students see a paper), fairness across languages and boards,
      every action attributable in a journal, refusal to act in the Forbidden Zone.
   c. The Forbidden Zone: which inputs and states make the model refuse or freeze (fail closed), as a short table.
2. Make this the single source in the JS reference: update `CONSTITUTION`, `audit()` and whatever `selfTest()` and `coreHash()` read in
   `reference/src/cos.js` so they implement the new articles. Keep exported names; keep an id where an old rule maps one to one; add new ids.
   An article the running state cannot check yet reports status `info` with a plain note, never a false `pass`.
   Update `reference/test/cos.test.js` and run `node --test "reference/test/*.test.js"` until all tests pass. Touch no other reference file.
3. Make the data shareable with C++: extend `tools/gen_inc.js` to emit `core/src/data/constitution.inc` (the articles as a constant table:
   id, title, text) and run it. The C++ cos port will include it.
4. After each milestone append one line to `docs/PROGRESS_constitution.md` (what is done, what remains). If it exists, continue from its last line.

You own only: `docs/CONSTITUTION.md`, `reference/src/cos.js`, `reference/test/cos.test.js`, `tools/gen_inc.js`,
`core/src/data/constitution.inc`, `docs/PROGRESS_constitution.md`. Do not edit anything else.
You can be cut off at any moment by a usage limit: write `docs/CONSTITUTION.md` first, in one Write call, then do steps 2 and 3.
Be economical: skim, do not re-read files you just wrote, keep tool output short. Final report under 150 words.
