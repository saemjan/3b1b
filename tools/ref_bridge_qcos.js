// ref_bridge_qcos.js — gen-3 ruler (v3)
// Same method names, same JSON text, so C++ and JS diff byte for byte.
// Numbers need no help here: JSON.stringify prints them exactly as
// Number.prototype.toString does, which is what jsnum replays in C++.
//
// CONSTITUTION (carried from v2, all preserved):
//   - canon() rejects integer-like object keys: JS Object.keys() reorders
//     them while C++ Json preserves insertion order. Without this guard,
//     kernel.soul silently diverges (A1).
//   - cog.observe pins bar to 1000 (A4/A5: the caller may not move the
//     moral-certainty bar).
//   - streamU parity contract with util.hpp: seed 0 -> 0x5AEE; streamU(seed,i)
//     applies xs (i+1) times. Verify both hold in C++ or every quantum case drifts.
// Gen-3 additions (non-wire): --selftest witnesses; fail-closed bounds on
// qubit count, amp shape, block indices, and observe probabilities. Guards
// refuse only inputs that previously crashed, hung, or produced garbage —
// corpus behavior is byte-frozen.
'use strict';
const crypto = require('crypto');

const MAX_QUBITS = 20;   // ruler bound: 2^20 amps; refuse unbounded work

const xs = x => { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; return x; };
const streamU = (seed, i) => { let x = (seed >>> 0) || 0x5AEE; for (let t = 0; t <= i; ++t) x = xs(x); return x / 4294967296; };

function applyAmp(v, n, g) {
  const M = 1 << n, ba = 1 << g.a, bb = 1 << g.b, bc = 1 << g.c;
  if (g.kind === 5) { const r = 0.70710678118654752440;
    for (let i = 0; i < M; ++i) if (!(i & ba)) { const x = v[i], y = v[i | ba];
      v[i] = [r*(x[0]+y[0]), r*(x[1]+y[1])]; v[i | ba] = [r*(x[0]-y[0]), r*(x[1]-y[1])]; }
    return v; }
  if (g.kind === 6) { for (let i = 0; i < M; ++i) if (i & ba) v[i] = [-v[i][0], -v[i][1]]; return v; }
  if (g.kind === 7) { for (let i = 0; i < M; ++i) if (i & ba) v[i] = [-v[i][1], v[i][0]]; return v; }
  for (let i = 0; i < M; ++i) { let fire = false, j = 0;
    if (g.kind === 0) { fire = !(i & ba); j = i | ba; }
    else if (g.kind === 1) { fire = !!(i & ba) && !(i & bb); j = i | bb; }
    else if (g.kind === 2) { fire = !!(i & ba) && !!(i & bb) && !(i & bc); j = i | bc; }
    else if (g.kind === 3) { fire = !!(i & ba) && !(i & bb); j = (i & ~ba) | bb; }
    else if (g.kind === 4) { fire = !!(i & ba) && !!(i & bb) && !(i & bc); j = (i & ~bb) | bc; }
    if (fire) { const t = v[i]; v[i] = v[j]; v[j] = t; } }
  return v;
}
// g is self-adjoint for kinds 0..6; only S (kind 7) needs S†: [a,b] -> [b,-a].
function applyAdjoint(v, n, g) {
  if (g.kind === 7) { const M = 1 << n, ba = 1 << g.a;
    for (let i = 0; i < M; ++i) if (i & ba) v[i] = [v[i][1], -v[i][0]]; return v; }
  return applyAmp(v, n, g);
}
function progMove(v, n, i, g, s) {
  const M = 1 << n, c = Math.sqrt(1 - s*s);
  const u0 = v.slice(i*M, (i+1)*M), v0 = v.slice((i+1)*M, (i+2)*M);
  const au = applyAmp(u0.map(z => z.slice()), n, g);
  const av = applyAdjoint(v0.map(z => z.slice()), n, g);
  for (let r = 0; r < M; ++r) {
    v[i*M + r]     = [c*u0[r][0] - s*av[r][0], c*u0[r][1] - s*av[r][1]];
    v[(i+1)*M + r] = [s*au[r][0] + c*v0[r][0], s*au[r][1] + c*v0[r][1]];
  }
  return v;
}
function canon(x) {
  if (x === null) return "null";
  if (typeof x === "boolean") return x ? "true" : "false";
  if (typeof x === "number") return String(x);
  if (typeof x === "string") return JSON.stringify(x);
  if (Array.isArray(x)) return "[" + x.map(canon).join(",") + "]";
  for (const k of Object.keys(x))
    if (/^(0|[1-9][0-9]*)$/.test(k))
      throw new Error("canon: integer-like object key '" + k + "' is forbidden (JS reorders it; C++ does not)");
  return "{" + Object.keys(x).map(k => JSON.stringify(k) + ":" + canon(x[k])).join(",") + "}";
}

// ---- gen-3 fail-closed guards (refuse only previously-undefined inputs) ---
function checkAmp(amp, n) {
  if (!Number.isInteger(n) || n < 1 || n > MAX_QUBITS)
    throw new Error('qcos: qubit count out of bounds (1..' + MAX_QUBITS + ')');
  const M = 1 << n;
  if (!Array.isArray(amp) || amp.length !== M)
    throw new Error('qcos: amp length must be 2^n');
  for (const z of amp)
    if (!Array.isArray(z) || z.length !== 2 || !Number.isFinite(z[0]) || !Number.isFinite(z[1]))
      throw new Error('qcos: amp entries must be finite [re,im] pairs');
}
function validate(method, a) {
  switch (method) {
    case 'quantum.apply': checkAmp(a.amp, a.n); break;
    case 'program.step':  checkAmp(a.amp, a.n);
      if (!Number.isInteger(a.i) || a.i < 0 || (a.i + 2) * (1 << a.n) > a.amp.length)
        throw new Error('qcos: block index out of range');
      if (!Number.isFinite(a.sin) || a.sin < 0 || a.sin > 1)
        throw new Error('qcos: sin must lie in [0,1]'); break;
    case 'program.halt':  checkAmp(a.amp, a.n);
      if (!Number.isInteger(a.k) || a.k < 0 || a.k >= 1 << a.n)
        throw new Error('qcos: halt block out of range'); break;
    case 'cog.observe': {
      const slip = a.slip ?? 0.10, guess = a.guess ?? 0.25;
      if (!(slip > 0 && slip < 1) || !(guess > 0 && guess < 1))
        throw new Error('qcos: slip and guess must lie in (0,1)'); break; }
  }
}

const methods = {
  "stream.u": a => ({ u: streamU(a.seed | 0, a.i | 0) }),
  "quantum.apply": a => ({ amp: applyAmp(a.amp.map(z => z.slice()), a.n, a.gate) }),
  "program.step": a => ({ amp: progMove(a.amp.map(z => z.slice()), a.n, a.i, a.gate, a.sin) }),
  "program.halt": a => { const M = 1 << a.n; let p = 0;
    for (let r = 0; r < M; ++r) { const c = a.amp[a.k*M + r]; p += c[0]*c[0] + c[1]*c[1]; } return { p }; },
  "cog.observe": a => { const slip = a.slip ?? 0.10, guess = a.guess ?? 0.25, p = 1-slip, q = guess;
    const lo = (a.logodds ?? 0) + Math.log(a.correct ? p/q : (1-p)/(1-q));
    return { logodds: lo, shots: (a.shots ?? 0) + 1, p: 1/(1+Math.exp(-lo)),
             moral: Math.abs(lo) >= Math.log(1000) }; },
  "kernel.canon": a => ({ text: canon(a.value) }),
  "kernel.soul": a => ({ hex: crypto.createHash("sha256").update(canon(a.value), "utf8").digest("hex") }),
};

async function dispatch(line) {
  let req, id = null;
  try { req = JSON.parse(line); id = req.id; }
  catch (e) {
    const m = line.match(/"id"\s*:\s*(-?\d+)/);
    if (m) id = Number(m[1]);
    return JSON.stringify({ id, ok: false, error: 'bad request: ' + e.message });
  }
  try {
    const fn = methods[req.method];
    if (!fn) throw new Error('unknown method: ' + req.method);
    const args = req.args || {};
    validate(req.method, args);
    return JSON.stringify({ id, ok: true, result: fn(args) });
  } catch (e) {
    return JSON.stringify({ id, ok: false, error: String(e.message || e) });
  }
}

// ---- self-witnesses (closed-form; byte contract untouched) ----------------
const near = (x, y, eps) => Math.abs(x - y) <= eps;
const SELFTEST = [
  ['canon preserves insertion order', async () =>
    canon({ b: 2, a: 1 }) === '{"b":2,"a":1}'],
  ['canon forbids integer-like keys (A1 guard)', async () => {
    try { canon({ "1": "x" }); return false; } catch (e) { return /integer-like/.test(e.message); } }],
  ['stream.u seed-zero contract (seed 0 == 0x5AEE path)', async () => {
    const a = JSON.parse(await dispatch('{"id":1,"method":"stream.u","args":{"seed":0,"i":3}}'));
    const b = JSON.parse(await dispatch('{"id":2,"method":"stream.u","args":{"i":3}}'));
    return a.ok && b.ok && a.result.u === b.result.u && a.result.u >= 0 && a.result.u < 1; }],
  ['Hadamard on |0>: symmetric, normalized, real', async () => {
    const r = JSON.parse(await dispatch(JSON.stringify({ id: 3, method: 'quantum.apply',
      args: { amp: [[1,0],[0,0]], n: 1, gate: { kind: 5, a: 0, b: 0, c: 0 } } })));
    if (!r.ok) return false;
    const [[x0, y0], [x1, y1]] = r.result.amp;
    return x0 === x1 && y0 === 0 && y1 === 0 && near(x0*x0 + x1*x1, 1, 1e-12); }],
  ['S then S-adjoint is identity', async () => {
    const g = { kind: 7, a: 0, b: 0, c: 0 };
    let v = applyAmp([[0,0],[1,0]], 1, g);
    v = applyAdjoint(v, 1, g);
    return v[0][0] === 0 && v[0][1] === 0 && v[1][0] === 1 && v[1][1] === 0; }],
  ['cog.observe bar pinned at 1000:1 (A4)', async () => {
    const up = JSON.parse(await dispatch(JSON.stringify({ id: 4, method: 'cog.observe',
      args: { correct: true, logodds: 6.5, shots: 0 } })));
    const down = JSON.parse(await dispatch(JSON.stringify({ id: 5, method: 'cog.observe',
      args: { correct: false, logodds: 7.0, shots: 0 } })));
    // 6.5 + ln(0.9/0.25) = 7.7809... > ln(1000) ; 7.0 + ln(0.1/0.75) = 4.9850... < ln(1000)
    return up.ok && down.ok && up.result.moral === true && down.result.moral === false
      && near(up.result.logodds, 6.5 + Math.log(3.6), 1e-12); }],
  ['cog.observe refuses degenerate probabilities', async () => {
    const r = JSON.parse(await dispatch(JSON.stringify({ id: 6, method: 'cog.observe',
      args: { correct: true, slip: 1.0, guess: 0.25 } })));
    return r.ok === false && /slip and guess/.test(r.error); }],
  ['kernel.soul = sha256 . canon composition', async () => {
    const v = { a: [1, 2], b: { c: true } };
    const r = JSON.parse(await dispatch(JSON.stringify({ id: 7, method: 'kernel.soul', args: { value: v } })));
    const want = crypto.createHash('sha256').update(canon(v), 'utf8').digest('hex');
    return r.ok && r.result.hex === want; }],
  ['qubit bound refuses unbounded work (fail-closed)', async () => {
    const r = JSON.parse(await dispatch(JSON.stringify({ id: 8, method: 'quantum.apply',
      args: { amp: [], n: 21, gate: { kind: 5, a: 0, b: 0, c: 0 } } })));
    return r.ok === false && /out of bounds/.test(r.error); }],
  ['malformed line answers with recovered id (A3)', async () => {
    const r = JSON.parse(await dispatch('{"id":999,"method":"stream.u","args":{'));
    return r.ok === false && r.id === 999; }],
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
    const [m, aj] = process.argv.slice(2);
    if (m) { // one-shot CLI mode (frozen v1 behavior)
      (async () => {
        try {
          validate(m, JSON.parse(aj || '{}'));
          console.log(JSON.stringify({ ok: true, result: methods[m](JSON.parse(aj || '{}')) }));
        } catch (e) {
          console.log(JSON.stringify({ ok: false, error: String((e && e.message) || e) }));
        }
      })();
    } else {   // line-protocol door mode
      const rl = require('readline').createInterface({ input: process.stdin });
      rl.on('line', line => {
        if (!line.trim()) return;
        dispatch(line).then(out => process.stdout.write(out + '\n'));
      });
    }
  }
}
module.exports = { methods, dispatch, canon, streamU, SELFTEST };
