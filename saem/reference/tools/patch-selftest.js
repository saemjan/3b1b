const fs = require('fs');
function patch(file, fn) { let s = fs.readFileSync(file, 'utf8'); const once = (a, b) => { const n = s.split(a).length - 1; if (n !== 1) throw new Error(file + ': expected 1 match, got ' + n + ' for: ' + a.slice(0, 70)); s = s.replace(a, () => b); }; fn(once, () => s, v => { s = v; }); fs.writeFileSync(file, s); }

/* 1. gen.js owns the hand-worked table (moved out of the test) */
const test = fs.readFileSync('/home/claude/saem-unified/test/gen.test.js', 'utf8');
const a = test.indexOf('const VECTORS = ['), b = test.indexOf('];', a) + 2;
const table = test.slice(a, b).replace('const VECTORS = [', '/* hand-worked answers, written down independently of the solvers; the app re-checks every solver against them at start-up */\nconst VECTORS = [');
patch('/home/claude/saem-unified/src/gen.js', (once) => {
  once("const GEN = { TPL, TOPICS,", table + "\n\nconst GEN = { VECTORS, TPL, TOPICS,");
});
/* 2. the test uses the shipped table */
patch('/home/claude/saem-unified/test/gen.test.js', (once, get, set) => {
  let s = get();
  const a2 = s.indexOf('/* hand-worked values, written down independently of the solvers */'), b2 = s.indexOf('];', s.indexOf('const VECTORS = [')) + 2;
  s = s.slice(0, a2) + 'const VECTORS = GEN.VECTORS;' + s.slice(b2);
  set(s);
});
/* 3. cos.js: the Soul checks its invariants */
patch('/home/claude/saem-unified/src/cos.js', (once) => {
  once("async function sha256(str) {", `/* invariants checked at start-up: every solver against its hand-worked answer, plus marking, reading papers and repeatability.
   A failure means the engine cannot be trusted: the app stops building papers rather than show a wrong answer. */
function selfTest() {
  const fails = []; let total = 0;
  const check = (name, ok) => { total++; if (!ok) fails.push(name); };
  for (const [id, p, want, tol] of GEN.VECTORS) {
    let got = null; try { got = GEN.solve(id, p); } catch (e) { got = null; }
    check('Math Brain ' + id, typeof want === 'string' ? got === want : typeof got === 'number' && Math.abs(got - want) <= (tol == null ? 1e-9 * Math.max(1, Math.abs(want)) : tol));
  }
  try { const x = GEN.make('K1', GEN.rng(7)), y = GEN.make('K1', GEN.rng(7)); check('Math Brain is repeatable', x.text === y.text && x.answer === y.answer && x.options.filter(o => o.key === x.answer).length === 1); } catch (e) { check('Math Brain is repeatable', false); }
  try {
    const opt = [{ key: 'A', text: 'x' }, { key: 'B', text: 'y' }], mk = a => ({ options: opt, answerKey: a, marks: { correct: 4, wrong: -1 } });
    const g = CBT.scoreTest([mk('A'), mk('A'), mk('B')], { 0: 'A', 1: 'B' });
    check('Marking: +4 right, -1 wrong, 0 skipped', g.total === 3 && g.max === 12 && g.correct === 1 && g.incorrect === 1 && g.unattempted === 1);
  } catch (e) { check('Marking: +4 right, -1 wrong, 0 skipped', false); }
  try {
    const r = parsePapers('2020\\n1. Find the value of x in the equation\\nA) 1\\nB) 2\\nC) 3\\nD) 4\\nAnswer: B').records;
    check('Reading a paper: year, options, answer', r.length === 1 && r[0].year === 2020 && r[0].options.length === 4 && r[0].answer === 'B');
  } catch (e) { check('Reading a paper: year, options, answer', false); }
  return { ok: fails.length === 0, passed: total - fails.length, total, failures: fails };
}

async function sha256(str) {`);
  once("GEN.TPL.map(t => [t.id, t.topic, t.q, t.a, t.X || '', t.e || ''].join(':')).join('|'),", "GEN.TPL.map(t => [t.id, t.topic, t.q, t.a, t.X || '', t.e || ''].join(':')).join('|'), JSON.stringify(GEN.VECTORS), selfTest.toString(),");
  once("verdict, audit, coreHash, receipt, sha256,", "verdict, audit, selfTest, coreHash, receipt, sha256,");
});
/* 4. tests for the self-test */
fs.appendFileSync('/home/claude/saem-unified/test/cos.test.js', `
test('selfTest: passes on the shipped engine and catches a broken solver', () => {
  const ok = COS.selfTest();
  assert.equal(ok.ok, true); assert.equal(ok.failures.length, 0); assert.equal(ok.passed, ok.total); assert.ok(ok.total >= 48, 'one check per hand-worked answer plus four invariants: ' + ok.total);
  const t = GEN.TPL.find(x => x.id === 'K1'), keep = t.a;
  try {
    t.a = p => p.v * p.v / 10; /* a plausible slip: g = 10 dropped the factor 2 */
    const bad = COS.selfTest();
    assert.equal(bad.ok, false); assert.ok(bad.failures.includes('Math Brain K1'), JSON.stringify(bad.failures)); assert.equal(bad.passed, bad.total - bad.failures.length);
  } finally { t.a = keep; }
  assert.equal(COS.selfTest().ok, true, 'restored');
});
`);
console.log('ok');
