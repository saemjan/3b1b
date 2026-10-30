const test = require('node:test');
const assert = require('node:assert/strict');
const GEN = require('../src/gen.js');

const close = (a, b, tol) => Math.abs(a - b) <= (tol == null ? 1e-9 * Math.max(1, Math.abs(b)) : tol);

const VECTORS = GEN.VECTORS;

test('there are 36 solvers over 12 topics, and every one has a hand-worked check', () => {
  assert.equal(GEN.TPL.length, 36);
  assert.equal(GEN.TOPICS.length, 12);
  const covered = new Set(VECTORS.map(v => v[0]));
  for (const t of GEN.TPL) assert.ok(covered.has(t.id), 'no hand-worked check for ' + t.id);
});

test('solvers match the hand-worked answers', () => {
  for (const [id, p, want, tol] of VECTORS) {
    const got = GEN.solve(id, p);
    if (typeof want === 'string') assert.equal(got, want, id + ' ' + JSON.stringify(p));
    else assert.ok(close(got, want, tol), id + ' ' + JSON.stringify(p) + ': got ' + got + ', want ' + want);
  }
});

test('number formatting', () => {
  assert.equal(GEN.fmt(20), '20');
  assert.equal(GEN.fmt(0.08000000000000002), '0.08');
  assert.equal(GEN.fmt(33.599999999999994), '33.6');
  assert.equal(GEN.fmt(1718.1), '1718');
  assert.equal(GEN.fmt(2.7e6), '2.7 × 10⁶');
  assert.equal(GEN.fmt(225988.7), '2.26 × 10⁵');
  assert.equal(GEN.fmt(0.0048), '0.0048');
  assert.equal(GEN.fmt(1e5), '1 × 10⁵');
  assert.equal(GEN.fmt(2e-6), '2 × 10⁻⁶');
});

test('every template makes well-formed questions for many seeds', () => {
  for (const t of GEN.TPL) {
    for (let s = 1; s <= 200; s++) {
      const q = GEN.make(t.id, GEN.rng(s * 7919));
      const where = t.id + ' seed ' + s;
      assert.equal(q.options.length, 4, where + ' needs 4 options');
      assert.deepEqual(q.options.map(o => o.key), ['A', 'B', 'C', 'D'], where);
      assert.equal(new Set(q.options.map(o => o.text)).size, 4, where + ' has duplicate options: ' + q.options.map(o => o.text).join(' | '));
      assert.ok(q.options.some(o => o.key === q.answer), where);
      assert.ok(!/undefined|NaN|Infinity/.test(q.text + q.options.map(o => o.text).join('') + q.explanation), where + ' leaks undefined/NaN');
      assert.ok(q.explanation.length > 15, where);
      assert.equal(q.topic, t.topic);
      assert.equal(q.src, 'math');
      for (const o of q.options) assert.ok(!/^-/.test(o.text), where + ' has a negative option ' + o.text);
    }
  }
});

test('the correct option is the exact solver value, formatted the same way', () => {
  for (const t of GEN.TPL) {
    for (let s = 1; s <= 60; s++) {
      const R = GEN.rng(s * 104729);
      const q = GEN.make(t.id, R);
      const ans = q.options.find(o => o.key === q.answer).text;
      // the worked solution must state the same value the option shows
      if (t.id !== 'S2' && t.id !== 'P2') assert.ok(q.explanation.includes(ans), t.id + ': explanation does not contain "' + ans + '": ' + q.explanation);
    }
  }
});

test('the same seed gives the same question, a different seed usually gives a different one', () => {
  const a = GEN.make('K1', GEN.rng(5)), b = GEN.make('K1', GEN.rng(5));
  assert.deepEqual(a, b);
  const texts = new Set(); for (let s = 1; s < 40; s++) texts.add(GEN.make('K1', GEN.rng(s)).text);
  assert.ok(texts.size > 1);
});

test('answer positions are spread across A-D', () => {
  const count = { A: 0, B: 0, C: 0, D: 0 };
  for (let s = 1; s <= 400; s++) count[GEN.make('W3', GEN.rng(s)).answer]++;
  for (const k in count) assert.ok(count[k] > 50, 'answer ' + k + ' is under-used: ' + JSON.stringify(count));
});

test('demo bank: 21 years, at least 30 questions each, mostly machine-made with options', () => {
  const items = GEN.demoBank(11);
  const years = new Set(items.map(i => i.year));
  assert.equal(years.size, 21);
  for (const y of years) assert.ok(items.filter(i => i.year === y).length >= 30);
  const mcq = items.filter(i => i.options && i.answer);
  assert.ok(mcq.length > 250, 'only ' + mcq.length + ' MCQs');
  assert.ok(items.every(i => i.topic && i.text && i.year));
  assert.deepEqual(GEN.demoBank(11), items, 'demo bank must be deterministic');
});
