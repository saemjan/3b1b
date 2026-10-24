// Same method names, same JSON text, so C++ and JS diff byte for byte.
// Numbers need no help here: JSON.stringify prints them exactly as
// Number.prototype.toString does, which is what jsnum replays in C++.
//
// v2: (a) removed the dead Object.assign in progMove (it set kind to
//     itself); S-adjoint is now explicit. (b) canon() rejects integer-like
//     object keys, because JS Object.keys() reorders them while the C++
//     Json preserves insertion order — without this guard, kernel.soul
//     silently diverges. (c) cog.observe pins bar to 1000 (A4/A5: the
//     caller may not move the moral-certainty bar).
const crypto = require("crypto");

const xs = x => { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; return x; };
// Parity contract with util.hpp: seed 0 -> 0x5AEE; streamU(seed,i) applies
// xs (i+1) times. Verify both hold in C++ or every quantum case drifts.
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

// g is self-adjoint for kinds 0..6 (NOT/CNOT/CCNOT/SWAP/FREDKIN/H/Z);
// only S (kind 7) needs its adjoint S† = diag(1,-i): [a,b] -> [b,-a].
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
    v[i*M + r]       = [c*u0[r][0] - s*av[r][0], c*u0[r][1] - s*av[r][1]];
    v[(i+1)*M + r]   = [s*au[r][0] + c*v0[r][0], s*au[r][1] + c*v0[r][1]];
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
if (require.main === module) {
  const [m, aj] = process.argv.slice(2);
  try { console.log(JSON.stringify({ ok: true, result: methods[m](JSON.parse(aj || "{}")) })); }
  catch (e) { console.log(JSON.stringify({ ok: false, error: String((e && e.message) || e) })); }
}
module.exports = methods;
