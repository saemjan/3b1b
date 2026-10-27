// ref_bridge.js — gen-3 ruler (v2)
// The JavaScript reference engine behind the same door as the C++ core.
// One JSON request per line on stdin; one answer per line on stdout.
//
// CONSTITUTION:
//   A1  wire format is FROZEN: parity_line.py compares full lines byte-for-byte.
//       Nothing in this file may change output bytes for corpus inputs.
//   A3  the door answers every line, even malformed ones; never throws.
//   A6  this is the ruler, never the product. Defaults pinned to the C++ door:
//       make/questionWith seed=1, demoBank seed=11, format x=0.
// Gen-3 additions (non-wire): --selftest witnesses, guarded startup, no silent
// require-death. node tools/ref_bridge.js --selftest  (exit 0 truth / 1 drift).
'use strict';
const path = require('path');

let EF, CBT, GEN, COS, loadError = null;
try {
  const R = p => require(path.join(__dirname, '..', 'reference', 'src', p));
  EF  = R('ef.js');
  CBT = R('cbt.js');
  GEN = R('gen.js');
  COS = R('cos.js');
  // reference/src modules historically read these off global; kept as a
  // documented load-time contract (debt J2 recorded, not hidden).
  global.EF = EF; global.CBT = CBT; global.GEN = GEN;
} catch (e) {
  loadError = e; // surfaced on stderr; selftest reports DRIFT, never stdout
}

const seeded = s => GEN ? GEN.rng(s == null ? 1 : s) : null;

const M = loadError ? {} : {
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

// One line in -> one line out. Async because core.info is async; output
// bytes are identical to the frozen v1 handler.
async function dispatch(line) {
  let req, id = null;
  try { req = JSON.parse(line); id = req.id; }
  catch (e) {
    const m = line.match(/"id"\s*:\s*(-?\d+)/);
    if (m) id = Number(m[1]);
    return JSON.stringify({ id, ok: false, error: 'bad request: ' + e.message });
  }
  try {
    const fn = M[req.method];
    if (!fn) throw new Error('unknown method: ' + req.method);
    const result = await fn(req.args || {});
    return JSON.stringify({ id, ok: true, result });
  } catch (e) {
    return JSON.stringify({ id, ok: false, error: String(e.message || e) });
  }
}

// ---- self-witnesses (closed-form; never touch the wire contract) ---------
const SELFTEST = [
  ['ruler loads (reference/src present)', async () => loadError === null],
  ['roster sorted and self-listing', async () => {
    const r = JSON.parse(await dispatch('{"id":1,"method":"core.methods","args":{}}'));
    return r.ok && Array.isArray(r.result) && r.result.includes('core.methods')
      && JSON.stringify(r.result) === JSON.stringify([...r.result].sort());
  }],
  ['unknown method refused, door stays open', async () => {
    const r = JSON.parse(await dispatch('{"id":2,"method":"no.such","args":{}}'));
    return r.ok === false && r.id === 2 && /unknown method/.test(r.error);
  }],
  ['malformed line answers with recovered id (A3)', async () => {
    const r = JSON.parse(await dispatch('{"id":999,"method":"gen.make","args":{'));
    return r.ok === false && r.id === 999;
  }],
  ['gen.format default pinned (x=0) and deterministic', async () => {
    const a = JSON.parse(await dispatch('{"id":3,"method":"gen.format","args":{}}'));
    const b = JSON.parse(await dispatch('{"id":4,"method":"gen.format","args":{}}'));
    return a.ok && b.ok && JSON.stringify(a.result) === JSON.stringify(b.result);
  }],
  ['gen.hash32 deterministic on frozen input', async () => {
    const q = '{"id":5,"method":"gen.hash32","args":{"s":"saem"}}';
    const a = JSON.parse(await dispatch(q)), b = JSON.parse(await dispatch(q));
    return a.ok && b.ok && JSON.stringify(a.result) === JSON.stringify(b.result);
  }],
];

async function selftest() {
  let bad = 0;
  for (let i = 0; i < SELFTEST.length; i++) {
    const [name, fn] = SELFTEST[i];
    let ok = false;
    try { ok = await fn(); } catch (e) { ok = false; }
    if (!ok) bad++;
    console.log(`[selftest] ${ok ? 'ok' : 'case ' + i + ' DRIFT'}: ${name}`);
  }
  console.log(`[selftest] ${SELFTEST.length - bad}/${SELFTEST.length} passed`);
  return bad ? 1 : 0;
}

if (require.main === module) {
  if (process.argv.includes('--selftest')) {
    selftest().then(c => process.exit(c));
  } else {
    if (loadError)
      process.stderr.write('[ref_bridge] load debt: ' + loadError.message + '\n');
    const rl = require('readline').createInterface({ input: process.stdin });
    rl.on('line', line => {
      if (!line.trim()) return;
      dispatch(line).then(out => process.stdout.write(out + '\n'));
    });
  }
}
module.exports = { dispatch, M, SELFTEST };
