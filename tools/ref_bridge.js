// The JavaScript reference engine behind the same door as the C++ core.
// One JSON request per line on stdin; one answer per line on stdout.
// A6: this is the ruler, never the product. Defaults here are pinned to
// the C++ door: make/questionWith seed=1, demoBank seed=11, format x=0.
'use strict';
const path = require('path');
const R = p => require(path.join(__dirname, '..', 'reference', 'src', p));
const EF  = R('ef.js');   global.EF  = EF;
const CBT = R('cbt.js');  global.CBT = CBT;
const GEN = R('gen.js');  global.GEN = GEN;
const COS = R('cos.js');

const seeded = s => GEN.rng(s == null ? 1 : s);
const M = {
  'core.methods': () => Object.keys(M).sort(),
  'core.info': async () => ({
    version: COS.VERSION, id: await COS.coreHash(),
    constitution: COS.CONSTITUTION, maxp: COS.MAXP,
    maxFaculty: COS.MAX_FACULTY, maxNudge: COS.MAX_NUDGE,
    capAttempts: COS.CAP_ATTEMPTS, keepDetail: COS.KEEP_DETAIL,
    templates: GEN.count, topics: GEN.TOPICS }),
  'core.selfTest': () => COS.selfTest(),
  'core.hash': () => COS.coreHash(),
  'core.receipt': ({ core, items, K, notes }) => COS.receipt(core, items, K, notes),
  'core.audit': a => COS.audit(a),
  'core.sha256': ({ s }) => COS.sha256(s),

  'gen.make':         ({ id, seed })   => GEN.make(id, seeded(seed)),
  'gen.questionWith': ({ id, params, seed }) => GEN.questionWith(id, params, seed == null ? 1 : seed),
  'gen.solve':        ({ id, params }) => GEN.solve(id, params),
  'gen.demoBank':     ({ seed, y0, y1 }) => GEN.demoBank(seed == null ? 11 : seed, y0, y1),
  'gen.topics':       () => GEN.TOPICS,
  'gen.templates':    () => GEN.TPL.map(t => ({ id: t.id, topic: t.topic })),
  'gen.format':       ({ x }) => GEN.fmt(x == null ? 0 : x),
  'gen.vectors':      () => GEN.VECTORS,
  'gen.hash32':       ({ s }) => GEN.hash32(s),
};

const rl = require('readline').createInterface({ input: process.stdin });
rl.on('line', async (line) => {
  if (!line.trim()) return;
  let req, id = null;
  try { req = JSON.parse(line); id = req.id; }
  catch (e) {
    const m = line.match(/"id"\s*:\s*(-?\d+)/);
    if (m) id = Number(m[1]);
    process.stdout.write(JSON.stringify({ id, ok: false, error: 'bad request: ' + e.message }) + '\n');
    return;
  }
  try {
    const fn = M[req.method];
    if (!fn) throw new Error('unknown method: ' + req.method);
    const result = await fn(req.args || {});
    process.stdout.write(JSON.stringify({ id, ok: true, result }) + '\n');
  } catch (e) {
    process.stdout.write(JSON.stringify({ id, ok: false, error: String(e.message || e) }) + '\n');
  }
});
