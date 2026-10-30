// The JavaScript reference engine behind the same door as the C++ core.
//   one JSON request per line on stdin:   {"id":1,"method":"gen.make","args":{"id":"K1","seed":7}}
//   one JSON answer per line on stdout:   {"id":1,"ok":true,"result":{...}}
// Development and tests only: the shipped product never runs JavaScript. This file is the spec the C++ core is held to.
'use strict';
const path = require('path');
const R = p => require(path.join(__dirname, '..', 'reference', 'src', p));
const EF = R('ef.js'); global.EF = EF;
const CBT = R('cbt.js'); global.CBT = CBT;
const GEN = R('gen.js'); global.GEN = GEN;
const COS = R('cos.js');

const seeded = s => GEN.rng(s == null ? 1 : s);
const M = {
  /* ---- the core itself ---- */
  'core.methods': () => Object.keys(M).sort(),
  'core.info': async () => ({ version: COS.VERSION, id: await COS.coreHash(), constitution: COS.CONSTITUTION, maxp: COS.MAXP, maxFaculty: COS.MAX_FACULTY, maxNudge: COS.MAX_NUDGE, capAttempts: COS.CAP_ATTEMPTS, keepDetail: COS.KEEP_DETAIL, templates: GEN.count, topics: GEN.TOPICS }),
  'core.selfTest': () => COS.selfTest(),
  'core.hash': () => COS.coreHash(),
  'core.receipt': ({ core, items, K, notes }) => COS.receipt(core, items, K, notes),
  'core.audit': a => COS.audit(a),
  'core.sha256': ({ s }) => COS.sha256(s),

  /* ---- Math Brain ---- */
  'gen.make': ({ id, seed }) => GEN.make(id, seeded(seed)),
  'gen.questionWith': ({ id, params, seed }) => GEN.questionWith(id, params, seed),
  'gen.solve': ({ id, params }) => GEN.solve(id, params),
  'gen.demoBank': ({ seed, y0, y1 }) => GEN.demoBank(seed, y0, y1),
  'gen.topics': () => GEN.TOPICS,
  'gen.templates': () => GEN.TPL.map(t => ({ id: t.id, topic: t.topic })),
  'gen.format': ({ x }) => GEN.fmt(x),
  'gen.vectors': () => GEN.VECTORS,
  'gen.hash32': ({ s }) => GEN.hash32(s),

  /* ---- reading text ---- */
  'text.parseDelimited': ({ text }) => EF.parseDelimited(text),
  'text.yearFromHeader': ({ line }) => EF.yearFromHeader(line),
  'text.tag': ({ text, custom }) => EF.tagWithSyllabus(text, COS.syllabus(custom)),
  'text.tokens': ({ text }) => EF.featureTokens(text),
  'text.normKey': ({ s }) => EF.normKey(s),
  'papers.parse': ({ text, defaultYear }) => { const r = COS.parsePapers(text, defaultYear); return { records: r.records, counts: r.counts, noYear: r.noYear }; },
  'papers.fromRows': ({ rows }) => COS.recordsFromRows(rows),
  'papers.splitMCQ': ({ lines }) => COS.splitMCQ(lines),
  'papers.normAnswer': ({ val, options }) => COS.normAnswer(val, options),
  'papers.keyMap': ({ block }) => COS.parseKeyMap(block),
  'papers.autoTag': ({ records, custom }) => COS.autoTag(records, custom),
  'papers.script': ({ text }) => COS.scriptLang(text),
  'bank.stats': ({ items }) => COS.bankStats(items),
  'bank.rows': ({ items }) => COS.bankRows(items),
  'bank.isTestable': ({ item }) => COS.isTestable(item),
  'paper.rows': ({ questions }) => COS.paperRows(questions),

  /* ---- the forecast engine ---- */
  'forecast.analyze': ({ items, K, tau, T, excluded }) => EF.analyze(items, { K, tau, T, excluded }, {}),
  'forecast.chooseMethod': ({ prior, lr }) => EF.chooseMethod(prior, lr),
  'forecast.calibrate': ({ chosen }) => EF.calibrate(chosen),
  'forecast.fitLR': ({ rows, ys, lam }) => EF.fitLR(rows, ys, lam),
  'forecast.predictLR': ({ model, x }) => EF.predictLR(model, x),
  'forecast.verdict': ({ fc }) => COS.verdict(fc),
  'forecast.notes': ({ text }) => COS.parseNotes(text),
  'forecast.nudge': ({ picks, notes }) => COS.nudge(picks, notes),

  /* ---- from forecast to paper, practice, and learning ---- */
  'paper.assemble': ({ fc, items, n, seed, receipt }) => COS.assemble(fc, items, { n, seed, receipt }),
  'paper.drill': ({ items, topic, n, seed }) => COS.drill(items, topic, { n, seed }),
  'study.plan': ({ fc, mastery, marks }) => COS.plan(fc, mastery, marks),
  'study.learn': ({ mastery, rows }) => COS.learn(mastery, rows),
  'study.forget': ({ attempts }) => COS.forget(attempts),
  'test.grade': ({ questions, selected }) => COS.grade(questions, selected),
  'test.record': ({ run, score, now }) => COS.attemptRecord(run, score, now),

  /* ---- the test machine ---- */
  'mcq.parseText': ({ text }) => CBT.parseMCQText(text),
  'mcq.parseCsv': ({ text }) => CBT.parseMCQCsv(text),
  'mcq.score': ({ questions, selected }) => CBT.scoreTest(questions, selected),
  'mcq.hash': ({ questions }) => CBT.hashQuestions(questions),
  'mcq.demo': () => CBT.demoQuestions(),
  'mcq.demoText': () => CBT.DEMO_TEXT,
  'clock.fmt': ({ sec }) => CBT.fmtClock(sec),
};

// Map becomes [[k, v], ...]; Set becomes an array; undefined fields vanish and NaN becomes null (as JSON.stringify does).
const replacer = (k, v) => (v instanceof Map ? [...v] : v instanceof Set ? [...v] : v);

async function handle(line) {
  let req;
  try { req = JSON.parse(line); } catch (e) { return { id: null, ok: false, error: 'bad request: ' + e.message }; }
  const f = M[req.method];
  if (!f) return { id: req.id, ok: false, error: 'unknown method: ' + req.method };
  try { return { id: req.id, ok: true, result: await f(req.args || {}) }; }
  catch (e) { return { id: req.id, ok: false, error: String(e && e.message || e) }; }
}

let buf = '', chain = Promise.resolve();
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => {
  buf += chunk;
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i); buf = buf.slice(i + 1);
    if (!line.trim()) continue;
    chain = chain.then(async () => { const out = await handle(line); process.stdout.write(JSON.stringify(out, replacer) + '\n'); });
  }
});
process.stdin.on('end', () => { chain.then(() => { if (buf.trim()) return handle(buf).then(o => process.stdout.write(JSON.stringify(o, replacer) + '\n')); }); });
