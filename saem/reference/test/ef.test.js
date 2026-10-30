const test = require('node:test');
const assert = require('node:assert/strict');
const EF = require('../src/ef.js');
global.EF = EF; global.CBT = require('../src/cbt.js'); global.GEN = require('../src/gen.js');
const GEN = global.GEN;
const COS = require('../src/cos.js');

async function forecast(y0, y1, K) {
  const items = GEN.demoBank(11, y0, y1); items.forEach((r, i) => { r.ref = i; });
  return { items, fc: await EF.analyze(items, { K: K || 40 }, {}) };
}
const mean = a => a.reduce((s, x) => s + x, 0) / a.length;

test('chooseMethod: the simple blend is the default; the learned model needs a clear win', () => {
  const m = p => ({ precision: p });
  assert.equal(EF.chooseMethod(m(0.30), null), 'blend');
  assert.equal(EF.chooseMethod(m(0.30), m(0.31)), 'blend');
  assert.equal(EF.chooseMethod(m(0.30), m(0.319)), 'blend');
  assert.equal(EF.chooseMethod(m(0.30), m(0.32)), 'learned');
  assert.equal(EF.chooseMethod(m(0.30), m(0.25)), 'blend');
  assert.equal(EF.chooseMethod(null, m(0.5)), 'blend');
});

test('calibrate: chances are scaled to how often top picks really appeared', () => {
  const untested = EF.calibrate(null);
  assert.equal(untested.tested, false); assert.equal(untested.factor, 0.75);
  assert.equal(EF.calibrate({ meanP: 0 }).tested, false);
  const c = EF.calibrate({ meanP: 0.4, hitRate: 0.3 });
  assert.equal(c.tested, true); assert.ok(Math.abs(c.factor - 0.75) < 1e-12); assert.equal(c.predicted, 0.4); assert.equal(c.realised, 0.3);
  assert.equal(EF.calibrate({ meanP: 0.4, hitRate: 0.01 }).factor, 0.25, 'never collapses to nothing');
  assert.equal(EF.calibrate({ meanP: 0.2, hitRate: 0.9 }).factor, 1.5, 'never inflates without limit');
});

test('forecast on 30 years: a method, a calibration, honest numbers', async () => {
  const { fc } = await forecast(1997, 2026);
  assert.equal(fc.meta.N, 30); assert.ok(['blend', 'learned'].includes(fc.method));
  const b = fc.backtest;
  assert.equal(b.n, 8); assert.equal(b.method, fc.method); assert.equal(b.per.length, 8);
  assert.equal(b.from, 2019); assert.equal(b.to, 2026);
  assert.ok(b.calibration.tested && b.calibration.factor > 0.25 && b.calibration.factor <= 1.5);
  assert.ok(b.model.precision > 3 * b.random.precision, 'far better than chance');
  assert.ok(b.prior && b.lr, 'both methods are tested and shown');
  assert.ok(b.model === (fc.method === 'learned' ? b.lr : b.prior));
  const ps = fc.picks.map(p => p.p);
  assert.ok(ps.every(p => p > 0 && p <= EF.MAXP));
  for (let i = 1; i < ps.length; i++) assert.ok(ps[i] <= ps[i - 1] + 1e-12, 'ranks follow chances');
  /* the scaled chances sit near what really happened, instead of near the raw score */
  assert.ok(Math.abs(mean(ps) - b.calibration.realised) < 0.12, 'mean chance ' + mean(ps).toFixed(3) + ' vs realised ' + b.calibration.realised.toFixed(3));
  assert.ok(Math.abs(fc.expectedHits - ps.reduce((a, c) => a + c, 0)) < 1e-9);
});

test('forecast is deterministic', async () => {
  const a = await forecast(2006, 2026), b = await forecast(2006, 2026);
  assert.equal(JSON.stringify(a.fc), JSON.stringify(b.fc));
});

test('short history: cautious chances, a plain warning, and no claim of testing', async () => {
  const { fc } = await forecast(2020, 2026);
  assert.equal(fc.meta.N, 7); assert.equal(fc.method, 'blend');
  assert.equal(fc.calibration.tested, false); assert.equal(fc.calibration.factor, 0.75);
  assert.ok(fc.warnings.some(w => /too few to test/.test(w) && /cautious/.test(w)));
  assert.ok(fc.picks.length > 0 && fc.picks.every(p => p.p <= EF.MAXP));
  assert.equal(COS.verdict(fc).status, 'info');
  const rules = COS.audit({ fc, paper: null, attempts: [], nudge: null });
  assert.match(rules.find(r => r.id === 'chance').note, /Too few papers to test/);
});

test('audit: the chance rule reports the calibration it applied', async () => {
  const { fc } = await forecast(1997, 2026);
  const rules = COS.audit({ fc, paper: null, attempts: [], nudge: null });
  assert.match(rules.find(r => r.id === 'chance').note, /Scaled to past papers \(×\d\.\d\d\)/);
});
