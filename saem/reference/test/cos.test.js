const test = require('node:test');
const assert = require('node:assert/strict');
const EF = require('../src/ef.js');
global.EF = EF; global.CBT = require('../src/cbt.js'); global.GEN = require('../src/gen.js');
const GEN = global.GEN, CBT = global.CBT;
const COS = require('../src/cos.js');

/* ---------------- reading papers ---------------- */
const PAPER = `
2023
1. A ball is thrown vertically upward at 20 m/s. Find the maximum height reached.
A) 10 m
B) 20 m
C) 40 m
D) 45 m
Answer: B
Explanation: h = v^2/2g = 20 m.
2. Two point charges are placed 10 cm apart in air. Find the force between them
when the distance doubles.
(a) 9 N
(b) 18 N
(c) 27 N
(d) 36 N
Ans. (c)
3. Find the moment of inertia of a uniform disc about its central axis.

2022
1. A stone is dropped from 45 m. Find the time taken to reach the ground.
(1) 2 s
(2) 3 s
(3) 4.5 s
(4) 9 s
Answer: 2
2. The unit of magnetic flux is
A. weber
B. tesla
C. henry
D. farad
`;

test('papers: options, answers, explanations and wrapped lines are split out of the stem', () => {
  const { records } = COS.parsePapers(PAPER);
  assert.equal(records.length, 5);
  const [a, b, c, d, e] = records;
  assert.equal(a.year, 2023); assert.equal(a.options.length, 4); assert.equal(a.answer, 'B');
  assert.equal(a.text, 'A ball is thrown vertically upward at 20 m/s. Find the maximum height reached.');
  assert.equal(a.explanation, 'h = v^2/2g = 20 m.');
  assert.equal(b.answer, 'C'); assert.match(b.text, /when the distance doubles\.$/); assert.equal(b.options[2].text, '27 N');
  assert.equal(c.options, undefined); assert.equal(c.answer, undefined); assert.match(c.text, /moment of inertia/);
  assert.equal(d.year, 2022); assert.equal(d.answer, 'B'); assert.deepEqual(d.options.map(o => o.key), ['A', 'B', 'C', 'D']);
  assert.equal(e.options.length, 4); assert.equal(e.answer, null);
  assert.ok(!records.some(r => /Answer|Ans\./.test(r.text)), 'answer lines must not leak into question text');
});

test('papers: a trailing answer key fills in answers for that year only', () => {
  const text = `2021
1. Which law explains why a passenger lurches forward when a bus brakes?
A) Newton's first law
B) Newton's second law
C) Newton's third law
D) Law of gravitation
2. What is the SI unit of power?
A) joule
B) watt
C) newton
D) pascal
Answer Key
1. A
2. B
2020
1. What is the SI unit of energy?
A) joule
B) watt
C) newton
D) pascal`;
  const { records } = COS.parsePapers(text);
  assert.equal(records.length, 3);
  assert.deepEqual(records.map(r => r.answer), ['A', 'B', undefined].map(x => x === undefined ? null : x));
  assert.equal(records[2].year, 2020);
});

test('papers: answer written as option text, and lines that merely start with "Answer" in a stem', () => {
  const { records } = COS.parsePapers(`2019
1. Find the escape speed of a body from the earth.
A) 7.9 km/s
B) 11.2 km/s
C) 3 km/s
D) 22.4 km/s
Answer: 11.2 km/s
2. Answer the following by choosing the best option for the unit of resistance.
A) ohm
B) mho
C) henry
D) farad
Answer: A`);
  assert.equal(records[0].answer, 'B');
  assert.match(records[1].text, /^Answer the following/);
  assert.equal(records[1].answer, 'A');
});

test('papers: needs a year, and keeps working without options', () => {
  const r = COS.parsePapers('1. Find the moment of inertia of a uniform ring about its axis.\n2. State Gauss law and use it for a charged sphere.');
  assert.equal(r.records.length, 0); assert.equal(r.noYear, 2);
  const s = COS.parsePapers('1. Find the moment of inertia of a uniform ring about its axis.', 2018);
  assert.equal(s.records.length, 1); assert.equal(s.records[0].year, 2018);
});

test('normAnswer', () => {
  const opts = [{ key: 'A', text: '10 m' }, { key: 'B', text: '20 m' }, { key: 'C', text: '40 m' }, { key: 'D', text: '45 m' }];
  assert.equal(COS.normAnswer('b', opts), 'B'); assert.equal(COS.normAnswer('(c)', opts), 'C'); assert.equal(COS.normAnswer('3', opts), 'C');
  assert.equal(COS.normAnswer('D. 45 m', opts), 'D'); assert.equal(COS.normAnswer('40 m', opts), 'C');
  assert.equal(COS.normAnswer('Both', opts), null); assert.equal(COS.normAnswer('20', opts), null); assert.equal(COS.normAnswer('', opts), null);
  assert.equal(COS.normAnswer('E', opts), null);
});

test('csv: year + question with optional options, answer, explanation', () => {
  const rows = EF.parseDelimited('Year,Question,Topic,A,B,C,D,Answer,Explanation\n2020,"Find the speed after 3 s, starting from rest at 2 m/s2",Kinematics,3,6,9,12,B,v = at\n2019,Define the term torque in your own words,Rotational Motion,,,,,,\n');
  const { records, error } = COS.recordsFromRows(rows);
  assert.equal(error, undefined); assert.equal(records.length, 2);
  assert.equal(records[0].answer, 'B'); assert.equal(records[0].options.length, 4); assert.equal(records[0].topic, 'Kinematics'); assert.equal(records[0].explanation, 'v = at');
  assert.equal(records[1].options, undefined);
  assert.match(COS.recordsFromRows(EF.parseDelimited('question,A,B\nx,1,2')).error, /year/);
});

test('language of a question comes from its script', () => {
  assert.equal(COS.scriptLang('A ball is thrown'), 'en'); assert.equal(COS.scriptLang('गेंद को ऊपर फेंका'), 'hi');
  assert.equal(COS.scriptLang('நேரம்'), 'ta'); assert.equal(COS.scriptLang('সময়'), 'bn');
});

/* ---------------- forecast -> paper ---------------- */
async function demoForecast() {
  const items = GEN.demoBank(11); items.forEach((r, i) => { r.ref = i; });
  const fc = await EF.analyze(items, { K: 40 }, {});
  return { items, fc };
}

test('nudge: opinion lifts ranks within its limits and never adds a pick', async () => {
  const { fc } = await demoForecast();
  const base = new Map(fc.picks.map(p => [p.refs[0], p.p]));
  const none = COS.nudge(fc.picks, '');
  assert.equal(none.picks.length, fc.picks.length); assert.equal(none.used.nudged, 0);
  const notes = ['Dr Rao | Rotational Motion | high', 'Ms Iyer | Rotational Motion | medium', 'Mr Das | Kinematics | low', '# a comment', 'badline', 'X | Optics | enormous'].join('\n');
  const r = COS.nudge(fc.picks, notes);
  assert.equal(r.picks.length, fc.picks.length, 'must not add or drop picks');
  assert.deepEqual(r.picks.map(p => p.rank), r.picks.map((p, i) => i + 1));
  for (const p of r.picks) {
    assert.ok(p.p <= COS.MAXP + 1e-12);
    const b = base.get(p.refs[0]);
    assert.ok(p.p >= Math.min(b, COS.MAXP) - 1e-12, 'an opinion never lowers a rank');
    if (p.nudge) { assert.ok(p.nudge.delta <= COS.MAX_NUDGE + 1e-12); assert.ok(p.p <= Math.min(COS.MAXP, b * (1 + COS.MAX_NUDGE)) + 1e-9, 'lift is at most 20%'); }
    else assert.ok(Math.abs(p.p - Math.min(b, COS.MAXP)) < 1e-12, 'a pick with no note keeps its probability');
  }
  const rot = r.picks.filter(p => p.topic === 'Rotational Motion' && p.nudge);
  assert.ok(rot.length > 0); assert.ok(Math.abs(rot[0].nudge.delta - 0.2) < 1e-9, 'high + a second independent faculty is still capped at 20%');
  assert.equal(r.used.faculty, 3); assert.equal(r.used.notes, 3);
  // more than five faculty: the extras are ignored
  const many = [1, 2, 3, 4, 5, 6, 7].map(i => 'Faculty ' + i + ' | Nuclei | high').join('\n');
  const m = COS.nudge(fc.picks, many);
  assert.equal(m.used.faculty, 5); assert.equal(m.used.notes, 5); assert.equal(m.used.ignored, 2);
  for (const p of m.picks) if (p.nudge) assert.ok(p.nudge.delta <= COS.MAX_NUDGE + 1e-12);
});

test('assemble: demo forecast -> a paper of fresh, exact questions on the most probable concepts', async () => {
  const { items, fc } = await demoForecast();
  const a = COS.assemble(fc, items, { n: 20, seed: 1, receipt: 'abcd-1234' });
  assert.equal(a.questions.length, 20);
  for (const q of a.questions) {
    assert.equal(q.options.length, 4); assert.ok(q.options.some(o => o.key === q.answerKey));
    assert.equal(q.src, 'math'); assert.ok(q.explanation); assert.ok(q.p > 0 && q.p <= COS.MAXP); assert.ok(q.topic);
  }
  assert.deepEqual(a.questions.map(q => q.rank), a.questions.map(q => q.rank).slice().sort((x, y) => x - y));
  const b = COS.assemble(fc, items, { n: 20, seed: 1, receipt: 'abcd-1234' });
  assert.deepEqual(a.questions.map(q => q.text), b.questions.map(q => q.text), 'same forecast + same set number = same paper');
  const c = COS.assemble(fc, items, { n: 20, seed: 2, receipt: 'abcd-1234' });
  assert.notDeepEqual(a.questions.map(q => q.text), c.questions.map(q => q.text), 'a new set number gives new numbers');
  assert.deepEqual(a.questions.map(q => q.topic), c.questions.map(q => q.topic), 'but the same concepts');
});

test('assemble: real papers are used as they stand, and concepts without options are skipped', async () => {
  const mk = (year, text, topic, withOpts) => Object.assign({ year, text, topic, concept: null }, withOpts ? { options: [{ key: 'A', text: 'one' }, { key: 'B', text: 'two' }, { key: 'C', text: 'three' }, { key: 'D', text: 'four' }], answer: 'B', explanation: 'because' } : {});
  const items = [];
  for (let y = 2010; y <= 2024; y++) {
    items.push(mk(y, 'Find the moment of inertia of a uniform disc about its central axis year ' + (y % 3), 'Rotational Motion', y % 2 === 0));
    items.push(mk(y, 'Derive the expression for the escape velocity of a satellite from the earth', 'Gravitation', false));
    items.push(mk(y, 'A ball is thrown vertically upward find the maximum height reached in flight', 'Kinematics', true));
  }
  items.forEach((r, i) => { r.ref = i; });
  const fc = await EF.analyze(items, { K: 10 }, {});
  const a = COS.assemble(fc, items, { n: 10, seed: 1, receipt: 'x' });
  assert.ok(a.questions.length >= 2);
  assert.ok(a.questions.every(q => q.src === 'paper' && q.year >= 2010));
  assert.ok(a.skipped.length >= 1, 'the Gravitation concept has no options and must be skipped');
  assert.ok(!a.questions.some(q => q.topic === 'Gravitation'));
  const rot = a.questions.find(q => q.topic === 'Rotational Motion');
  assert.equal(rot.year, 2024, 'latest testable paper question');
});

test('drill: real questions first, then fresh Math Brain questions on the same topic', () => {
  const real = [1, 2, 3].map(i => ({ year: 2020 + i, text: 'Real kinematics question number ' + i, topic: 'Kinematics', options: [{ key: 'A', text: 'a' }, { key: 'B', text: 'b' }], answer: 'A' }));
  const d = COS.drill(real, 'Kinematics', { n: 8, seed: 1 });
  assert.equal(d.questions.length, 8); assert.equal(d.questions.filter(q => q.src === 'paper').length, 3); assert.equal(d.questions.filter(q => q.src === 'math').length, 5);
  assert.ok(d.questions.every(q => q.topic === 'Kinematics'));
  const e = COS.drill([], 'Nuclei', { n: 6, seed: 3 });
  assert.equal(e.questions.length, 6); assert.ok(e.questions.every(q => q.topic === 'Nuclei' && q.src === 'math'));
  assert.deepEqual(COS.drill([], 'Nuclei', { n: 6, seed: 3 }).questions.map(q => q.text), e.questions.map(q => q.text));
  assert.equal(COS.drill([], 'Underwater Basket Weaving', { n: 5 }).questions.length, 0);
});

/* ---------------- Heart ---------------- */
test('learn: mastery moves toward what happened, ignores skipped and untagged questions', () => {
  let m = COS.learn({}, [{ topic: 'Kinematics', outcome: 'correct' }]);
  assert.ok(Math.abs(m.Kinematics.m - 0.75) < 1e-9); assert.equal(m.Kinematics.n, 1);
  m = COS.learn(m, [{ topic: 'Kinematics', outcome: 'incorrect' }, { topic: 'Nuclei', outcome: 'unattempted' }, { topic: '', outcome: 'correct' }, { topic: null, outcome: 'correct' }]);
  assert.ok(m.Kinematics.m < 0.75); assert.equal(m.Kinematics.n, 2); assert.equal(m.Nuclei, undefined);
  let x = {}; for (let i = 0; i < 40; i++) x = COS.learn(x, [{ topic: 'T', outcome: 'correct' }]);
  assert.ok(x.T.m > 0.95 && x.T.m <= 1);
  let y = {}; for (let i = 0; i < 40; i++) y = COS.learn(y, [{ topic: 'T', outcome: 'incorrect' }]);
  assert.ok(y.T.m < 0.05 && y.T.m >= 0);
  const before = JSON.stringify(m); COS.learn(m, [{ topic: 'Kinematics', outcome: 'correct' }]); assert.equal(JSON.stringify(m), before, 'learn must not mutate its input');
});

test('forget: a line per attempt for the last 60, full detail for the last 10', () => {
  const att = Array.from({ length: 75 }, (_, i) => ({ id: 'a' + i, t: i, pct: i, rows: [['K', 1, 3]] }));
  const out = COS.forget(att);
  assert.equal(out.length, 60); assert.equal(out[0].id, 'a15'); assert.equal(out[59].id, 'a74');
  assert.equal(out.filter(a => a.rows).length, 10); assert.ok(out.slice(-10).every(a => a.rows)); assert.ok(out.slice(0, 50).every(a => !a.rows));
  assert.equal(COS.forget(att.slice(0, 5)).length, 5); assert.ok(COS.forget(att.slice(0, 5)).every(a => a.rows));
});

test('plan: more marks at stake where a topic is likely and not yet mastered', () => {
  const fc = { topics: [{ topic: 'A', expected: 3, trend: 'flat' }, { topic: 'B', expected: 3, trend: 'up' }, { topic: 'C', expected: 1, trend: 'down' }, { topic: null, expected: 9 }] };
  const p = COS.plan(fc, { A: { m: 0.9, n: 5 }, B: { m: 0.2, n: 4 } }, 4);
  assert.deepEqual(p.map(x => x.topic), ['B', 'C', 'A']);
  assert.ok(Math.abs(p[0].stake - 3 * 4 * 0.8) < 1e-9); assert.equal(p.find(x => x.topic === 'C').tested, false); assert.equal(p.find(x => x.topic === 'C').mastery, 0.5);
});

test('grade: negative marking, topics ordered weakest first', () => {
  const qs = [
    { text: 'q1', options: [{ key: 'A', text: 'x' }, { key: 'B', text: 'y' }], answerKey: 'A', topic: 'K', marks: { correct: 4, wrong: -1 } },
    { text: 'q2', options: [{ key: 'A', text: 'x' }, { key: 'B', text: 'y' }], answerKey: 'B', topic: 'K', marks: { correct: 4, wrong: -1 } },
    { text: 'q3', options: [{ key: 'A', text: 'x' }, { key: 'B', text: 'y' }], answerKey: 'A', topic: 'N', marks: { correct: 4, wrong: -1 } },
    { text: 'q4', options: [{ key: 'A', text: 'x' }, { key: 'B', text: 'y' }], answerKey: 'A', topic: null, marks: { correct: 4, wrong: -1 } },
  ];
  const g = COS.grade(qs, { 0: 'A', 1: 'A', 2: 'A' });
  assert.equal(g.total, 4 - 1 + 4); assert.equal(g.max, 16); assert.equal(g.correct, 2); assert.equal(g.incorrect, 1); assert.equal(g.unattempted, 1);
  assert.deepEqual(g.byTopic.map(t => [t.topic, t.n, t.correct]), [['K', 2, 1], ['N', 1, 1]]);
  const rec = COS.attemptRecord({ title: 't', src: 'forecast', h: 'h', qs, spent: { 0: 10.4, 1: 5 } }, g, 1700000000000);
  assert.equal(rec.n, 4); assert.equal(rec.secs, 15); assert.deepEqual(rec.rows[1], ['K', 0, 5]); assert.deepEqual(rec.rows[3], ['', -1, 0]);
});

/* ---------------- Constitution and Soul ---------------- */
test('verdict: honest about whether the forecast beats a plain frequency count', () => {
  const bt = (m, f, r, n) => ({ backtest: { n: n == null ? 8 : n, model: { precision: m }, freq: { precision: f }, random: { precision: r } } });
  assert.equal(COS.verdict(bt(0.4, 0.3, 0.07)).status, 'pass');
  assert.equal(COS.verdict(bt(0.3, 0.3, 0.07)).status, 'info');
  assert.equal(COS.verdict(bt(0.25, 0.3, 0.07)).status, 'warn');
  assert.equal(COS.verdict(bt(0.08, 0.07, 0.07)).status, 'warn');
  assert.equal(COS.verdict({ backtest: null }).status, 'info'); assert.equal(COS.verdict(null).status, 'info');
  assert.equal(COS.verdict(bt(0.4, 0.3, 0.07, 1)).status, 'info');
});

test('audit: six rules, each with a live status', async () => {
  const { items, fc } = await demoForecast();
  const nd = COS.nudge(fc.picks, 'A | Nuclei | high');
  fc.picks = nd.picks;
  const paper = COS.assemble(fc, items, { n: 10, seed: 1, receipt: 'r' });
  const rules = COS.audit({ fc, paper, attempts: [], nudge: nd.used });
  assert.equal(rules.length, 6); assert.deepEqual(rules.map(r => r.id), ['chance', 'tested', 'source', 'opinion', 'private', 'bounded']);
  assert.ok(rules.every(r => ['pass', 'warn', 'info'].includes(r.status) && r.note && r.title && r.text));
  assert.equal(rules.find(r => r.id === 'chance').status, 'pass'); assert.equal(rules.find(r => r.id === 'source').status, 'pass'); assert.equal(rules.find(r => r.id === 'opinion').status, 'pass');
  const empty = COS.audit({ fc: null, paper: null, attempts: [], nudge: null });
  assert.equal(empty.find(r => r.id === 'chance').status, 'info');
  const bad = COS.audit({ fc: { picks: [{ p: 0.99, years: [2020] }], backtest: null }, paper: null, attempts: new Array(61).fill(0), nudge: null });
  assert.equal(bad.find(r => r.id === 'chance').status, 'warn'); assert.equal(bad.find(r => r.id === 'bounded').status, 'warn');
  assert.throws(() => { 'use strict'; COS.CONSTITUTION[0].title = 'changed'; }, TypeError);
  assert.throws(() => { 'use strict'; COS.CONSTITUTION.push({}); }, TypeError);
});

test('soul: the core fingerprint and the forecast receipt are stable and sensitive', async () => {
  const c1 = await COS.coreHash(), c2 = await COS.coreHash();
  assert.match(c1, /^[0-9a-f]{4}-[0-9a-f]{4}$/); assert.equal(c1, c2);
  const items = GEN.demoBank(11);
  const r1 = await COS.receipt(c1, items, 40, ''), r2 = await COS.receipt(c1, items, 40, '');
  assert.equal(r1, r2); assert.match(r1, /^[0-9a-f]{4}-[0-9a-f]{4}$/);
  assert.notEqual(r1, await COS.receipt(c1, items, 30, ''), 'K changes the receipt');
  assert.notEqual(r1, await COS.receipt(c1, items, 40, 'A | Nuclei | high'), 'notes change the receipt');
  assert.notEqual(r1, await COS.receipt(c1, items.slice(1), 40, ''), 'papers change the receipt');
  assert.notEqual(r1, await COS.receipt('0000-0000', items, 40, ''), 'the core changes the receipt');
});

test('bank helpers', () => {
  const items = GEN.demoBank(11); const st = COS.bankStats(items);
  assert.equal(st.years, 21); assert.equal(st.y0, 2006); assert.equal(st.y1, 2026); assert.ok(st.ready > 200 && st.ready < st.n); assert.equal(st.topics, 12);
  const rows = COS.bankRows(items.slice(0, 3)); assert.equal(rows.length, 4); assert.equal(rows[0].length, 10);
  const back = COS.recordsFromRows(rows); assert.equal(back.records.length, 3); assert.equal(back.records[0].answer, items[0].answer);
  assert.equal(back.records[0].options.length, 4);
});

test('an exported paper can be read back by the Mock Test parser', async () => {
  const { items, fc } = await demoForecast();
  const paper = COS.assemble(fc, items, { n: 5, seed: 1, receipt: 'r' });
  const rows = COS.paperRows(paper.questions);
  assert.equal(rows[0].join(','), 'question,A,B,C,D,answer,section,explanation,marks,topic,chance_pct,source');
  const csv = rows.map(r => r.map(v => { v = v == null ? '' : String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(',')).join('\r\n');
  const parsed = CBT.parseMCQCsv(csv);
  assert.equal(parsed.questions.length, 5); assert.ok(parsed.questions.every(q => !q.error), JSON.stringify(parsed.questions.filter(q => q.error)));
  assert.equal(parsed.questions[0].answerKey, paper.questions[0].answerKey);
});

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
