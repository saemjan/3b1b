/* Math Brain: exact, deterministic physics question solvers. Pure JS, no DOM.
   Every answer is computed from the numbers in the question, never guessed.
   A template = wording + parameter pools + a solver + typical slips (wrong options) + a worked solution. */
(function (root) {
'use strict';

/* ---------- small helpers ---------- */
function rng(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function hash32(str) { let h = 2166136261; str = String(str); for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
const pick = (R, a) => a[Math.floor(R() * a.length)];
function shuffle(a, R) { const b = a.slice(); for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; }
const SUP = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' };
const sup = n => String(n).split('').map(c => SUP[c]).join('');

/* number -> text: 4 significant figures, scientific form for very large or small values */
function fmt(x) {
  if (typeof x === 'string') return x;
  if (!isFinite(x)) return String(x);
  if (x === 0) return '0';
  const a = Math.abs(x);
  if (a >= 1e5 || a < 1e-3) {
    let e = Math.floor(Math.log10(a)), m = +(x / Math.pow(10, e)).toPrecision(4);
    if (Math.abs(m) >= 10) { m /= 10; e++; }
    return m + ' × 10' + sup(e);
  }
  return String(+x.toPrecision(4));
}
const withUnit = (x, U) => fmt(x) + (U ? (U === '%' || U === '°' ? '' : ' ') + U : '');

const SIN = { 30: 0.5, 37: 0.6, 53: 0.8, 90: 1 }, COS_ = { 30: 0.866, 37: 0.8, 53: 0.6, 90: 0 };
const SH = [['ring', '1/2'], ['disc', '1/3'], ['solid sphere', '2/7'], ['hollow sphere', '2/5']];
const PR = [['√2', 30], ['√3', 60]];
const CR = [['2', 30, '0.5'], ['√2', 45, '0.707'], ['2/√3', 60, '0.866']];
const LG = [['AND', 'gives output 1 only when both inputs are 1'], ['OR', 'gives output 1 when at least one input is 1'], ['NAND', 'gives output 0 only when both inputs are 1'], ['NOR', 'gives output 1 only when both inputs are 0'], ['XOR', 'gives output 1 only when its two inputs differ']];

/* ---------- the 36 templates (12 topics x 3) ----------
   P: independent parameter pools; S: ['k1,k2', [..], [..]] dependent tuples
   q: question text   a: exact answer (number, or option text when o is given)
   U: unit            X: typical slips (wrong options)   o: all option texts (non-numeric answers)
   e: worked solution (receives the params and the formatted answer) */
const T = (id, topic, spec) => Object.assign({ id, topic }, spec);
const TPL = [
  T('K1', 'Kinematics', { P: { v: [10, 20, 30, 40] },
    q: p => `A ball is thrown vertically upward with a speed of ${p.v} m/s. Find the maximum height it reaches. (g = 10 m/s²)`,
    a: p => p.v * p.v / 20, U: 'm', X: p => [p.v * p.v / 10, p.v / 10, p.v * p.v / 40],
    e: (p, A) => `At the top the speed is zero, so H = v²/2g = ${p.v}²/(2 × 10) = ${A}.` }),
  T('K2', 'Kinematics', { P: { v: [10, 20, 25, 50], th: [30, 37, 53] },
    q: p => `A projectile is fired at ${p.v} m/s at ${p.th}° above the horizontal. Find its time of flight. (g = 10 m/s², sin ${p.th}° = ${SIN[p.th]})`,
    a: p => 2 * p.v * SIN[p.th] / 10, U: 's', X: p => [p.v * SIN[p.th] / 10, 2 * p.v / 10, 2 * p.v * SIN[p.th]],
    e: (p, A) => `T = 2v sinθ / g = 2 × ${p.v} × ${SIN[p.th]} / 10 = ${A}.` }),
  T('K3', 'Kinematics', { P: { w: [100, 200, 300, 400], b: [5, 10, 20], c: [2, 3, 4] },
    q: p => `A boat is steered perpendicular to the banks of a river ${p.w} m wide. Its speed in still water is ${p.b} m/s and the current is ${p.c} m/s. How long does it take to cross?`,
    a: p => p.w / p.b, U: 's', X: p => [p.w / Math.hypot(p.b, p.c), p.w / (p.b + p.c), p.w / (p.b - p.c)],
    e: (p, A) => `Only the velocity across the river carries the boat over, so t = ${p.w}/${p.b} = ${A}. The current only drifts it downstream.` }),

  T('L1', 'Laws of Motion', { P: { m: [2, 5, 10, 20], mu: [0.2, 0.25, 0.4, 0.5] },
    q: p => `A block of mass ${p.m} kg slides on a rough horizontal floor. The coefficient of kinetic friction is ${p.mu}. Find the friction force on the block. (g = 10 m/s²)`,
    a: p => p.mu * p.m * 10, U: 'N', X: p => [p.mu * p.m, p.m * 10, p.mu * p.m * 20],
    e: (p, A) => `The normal force is mg = ${p.m} × 10 = ${p.m * 10} N, so f = μN = ${p.mu} × ${p.m * 10} = ${A}.` }),
  T('L2', 'Laws of Motion', { S: ['m1,m2', [1, 3], [2, 3], [3, 5], [2, 6], [4, 6], [1, 4], [3, 7]],
    q: p => `Two blocks of masses ${p.m1} kg and ${p.m2} kg hang from the ends of a light string passing over a smooth pulley. Find the acceleration of the blocks. (g = 10 m/s²)`,
    a: p => (p.m2 - p.m1) * 10 / (p.m1 + p.m2), U: 'm/s²', X: p => [(p.m2 - p.m1) * 10 / p.m2, (p.m1 + p.m2) * 10 / (p.m2 - p.m1), (p.m2 - p.m1) * 10 / p.m1],
    e: (p, A) => `The net pulling force is (m₂ − m₁)g and the whole ${p.m1 + p.m2} kg moves, so a = (${p.m2} − ${p.m1}) × 10 / (${p.m1} + ${p.m2}) = ${A}.` }),
  T('L3', 'Laws of Motion', { P: { m: [50, 60, 70, 80], a: [2, 4, 5] },
    q: p => `A person of mass ${p.m} kg stands on a weighing scale in a lift accelerating upward at ${p.a} m/s². What does the scale read, in newtons? (g = 10 m/s²)`,
    a: p => p.m * (10 + p.a), U: 'N', X: p => [p.m * (10 - p.a), p.m * 10, p.m * p.a],
    e: (p, A) => `In an upward-accelerating lift N − mg = ma, so N = m(g + a) = ${p.m} × (10 + ${p.a}) = ${A}.` }),

  T('W1', 'Work Energy Power', { P: { m: [2, 4, 5, 10], v1: [2, 4, 6], v2: [8, 10, 12] },
    q: p => `A body of mass ${p.m} kg speeds up from ${p.v1} m/s to ${p.v2} m/s. Find the net work done on it.`,
    a: p => 0.5 * p.m * (p.v2 * p.v2 - p.v1 * p.v1), U: 'J', X: p => [0.5 * p.m * Math.pow(p.v2 - p.v1, 2), p.m * (p.v2 * p.v2 - p.v1 * p.v1), 0.5 * p.m * p.v2 * p.v2],
    e: (p, A) => `By the work–energy theorem W = ΔK = ½m(v₂² − v₁²) = ½ × ${p.m} × (${p.v2}² − ${p.v1}²) = ${A}.` }),
  T('W2', 'Work Energy Power', { S: ['k,x', [100, 20], [200, 10], [400, 10], [500, 20], [200, 5], [100, 10]],
    q: p => `A spring of spring constant ${p.k} N/m is compressed by ${p.x} cm. Find the potential energy stored in it.`,
    a: p => 0.5 * p.k * Math.pow(p.x / 100, 2), U: 'J', X: p => [p.k * Math.pow(p.x / 100, 2), 0.5 * p.k * p.x * p.x, 0.5 * p.k * p.x / 100],
    e: (p, A) => `U = ½kx² with x = ${p.x} cm = ${p.x / 100} m, so U = ½ × ${p.k} × (${p.x / 100})² = ${A}.` }),
  T('W3', 'Work Energy Power', { P: { m: [100, 200, 300, 500], h: [10, 20, 30], t: [10, 20, 50] },
    q: p => `A pump raises ${p.m} kg of water through ${p.h} m in ${p.t} s. Find the power it delivers. (g = 10 m/s²)`,
    a: p => p.m * 10 * p.h / p.t, U: 'W', X: p => [p.m * p.h / p.t, p.m * 10 * p.h * p.t, p.m * 10 * p.t / p.h],
    e: (p, A) => `Work = mgh = ${p.m} × 10 × ${p.h} = ${p.m * 10 * p.h} J, and power = work/time = ${p.m * 10 * p.h}/${p.t} = ${A}.` }),

  T('R1', 'Rotational Motion', { P: { m: [2, 4, 10], r: [10, 20, 50] },
    q: p => `Find the moment of inertia of a uniform disc of mass ${p.m} kg and radius ${p.r} cm about an axis through its centre, perpendicular to its plane.`,
    a: p => 0.5 * p.m * Math.pow(p.r / 100, 2), U: 'kg m²', X: p => [p.m * Math.pow(p.r / 100, 2), 0.5 * p.m * p.r * p.r, 0.25 * p.m * Math.pow(p.r / 100, 2)],
    e: (p, A) => `For a disc I = ½MR² with R = ${p.r} cm = ${p.r / 100} m, so I = ½ × ${p.m} × (${p.r / 100})² = ${A}.` }),
  T('R2', 'Rotational Motion', { P: { s: [0, 1, 2, 3] },
    q: p => `A ${SH[p.s][0]} rolls without slipping on a horizontal surface. What fraction of its total kinetic energy is rotational?`,
    o: p => SH.map(x => x[1]), a: p => SH[p.s][1],
    e: (p, A) => `Rolling without slipping: K = ½mv²(1 + k²) where I = mk²R². The rotational share is k²/(1 + k²) = ${A} for a ${SH[p.s][0]}.` }),
  T('R3', 'Rotational Motion', { P: { m: [2, 3, 5], r: [2, 4, 5], v: [3, 4, 6] },
    q: p => `A particle of mass ${p.m} kg moves on a circle of radius ${p.r} m at a constant speed of ${p.v} m/s. Find its angular momentum about the centre of the circle.`,
    a: p => p.m * p.v * p.r, U: 'kg m²/s', X: p => [p.m * p.v * p.r / 2, p.m * p.v / p.r, p.m * p.v * p.v / p.r],
    e: (p, A) => `The velocity is perpendicular to the radius, so L = mvr = ${p.m} × ${p.v} × ${p.r} = ${A}.` }),

  T('G1', 'Gravitation', { P: { n: [4, 9, 16, 25] },
    q: p => `A planet has the same radius as the earth but ${p.n} times its mass. The escape velocity from the earth is 11.2 km/s. What is the escape velocity from the planet?`,
    a: p => 11.2 * Math.sqrt(p.n), U: 'km/s', X: p => [11.2 * p.n, 11.2 / Math.sqrt(p.n), 11.2 * p.n / 2],
    e: (p, A) => `v = √(2GM/R) ∝ √M for the same radius, so v = 11.2 × √${p.n} = ${A}.` }),
  T('G2', 'Gravitation', { P: { f: [[1, 2], [1, 4], [1, 5], [3, 4]] },
    q: p => `Find the acceleration due to gravity at a depth equal to ${p.f[0]}/${p.f[1]} of the earth's radius below its surface. (g at the surface = 10 m/s²)`,
    a: p => 10 * (1 - p.f[0] / p.f[1]), U: 'm/s²', X: p => [10 * p.f[0] / p.f[1], 10 / (1 - p.f[0] / p.f[1]), 10 * (1 - 2 * p.f[0] / p.f[1])],
    e: (p, A) => `Inside the earth g′ = g(1 − d/R) = 10 × (1 − ${p.f[0]}/${p.f[1]}) = ${A}.` }),
  T('G3', 'Gravitation', { P: { n: [4, 16, 25, 64] },
    q: p => `A satellite moves in a circular orbit of radius ${p.n}R about a planet of radius R. A satellite just above the surface moves at 8 km/s. What is the orbital speed of this satellite?`,
    a: p => 8 / Math.sqrt(p.n), U: 'km/s', X: p => [8 / p.n, 8 * Math.sqrt(p.n), 8 / (p.n - 1)],
    e: (p, A) => `Orbital speed v = √(GM/r) ∝ 1/√r, so v = 8/√${p.n} = ${A}.` }),

  T('T1', 'Thermodynamics', { P: { T: [200, 300, 400, 500] },
    q: p => `One mole of an ideal gas expands isothermally at ${p.T} K until its volume doubles. Find the work done by the gas. (R = 8.3 J/mol K, ln 2 = 0.69)`,
    a: p => 8.3 * p.T * 0.69, U: 'J', X: p => [8.3 * p.T, 8.3 * p.T * 2, 8.3 * p.T / 0.69],
    e: (p, A) => `For an isothermal process W = nRT ln(V₂/V₁) = 1 × 8.3 × ${p.T} × 0.69 = ${A}.` }),
  T('T2', 'Thermodynamics', { S: ['a,b', [400, 300], [500, 300], [600, 300], [800, 400], [500, 400], [1000, 600]],
    q: p => `A Carnot engine works between a source at ${p.a} K and a sink at ${p.b} K. Find its efficiency in percent.`,
    a: p => (1 - p.b / p.a) * 100, U: '%', X: p => [p.b / p.a * 100, (p.a - p.b) / p.b * 100, (1 - p.b / p.a) * 50],
    e: (p, A) => `η = 1 − T₂/T₁ = 1 − ${p.b}/${p.a} = ${fmt(1 - p.b / p.a)}, which is ${A}.` }),
  T('T3', 'Thermodynamics', { P: { pr: [100, 200, 300, 400], v: [2, 3, 5] },
    q: p => `On a p–V diagram a gas goes round a rectangular cycle. The pressure side is ${p.pr} kPa and the volume side is ${p.v} litres. Find the net work done by the gas in one cycle.`,
    a: p => p.pr * p.v, U: 'J', X: p => [p.pr * p.v / 2, 2 * p.pr * p.v, p.pr * p.v / 10],
    e: (p, A) => `Net work in a cycle is the enclosed area: ${p.pr} kPa × ${p.v} L = ${A}, since 1 kPa × 1 L = 1 J.` }),

  T('O1', 'Oscillations', { P: { A: [2, 5, 10], w: [2, 5, 10] },
    q: p => `A particle in simple harmonic motion has amplitude ${p.A} cm and angular frequency ${p.w} rad/s. Find its maximum speed.`,
    a: p => p.A * p.w, U: 'cm/s', X: p => [p.A / p.w, p.A * p.w * p.w, p.A * p.w / 2],
    e: (p, A) => `v_max = Aω = ${p.A} × ${p.w} = ${A}.` }),
  T('O2', 'Oscillations', { P: { l: [1, 4, 9, 0.25, 2.25] },
    q: p => `Find the time period of a simple pendulum of length ${p.l} m. (Take g = π² m/s².)`,
    a: p => 2 * Math.sqrt(p.l), U: 's', X: p => [Math.sqrt(p.l), 4 * Math.sqrt(p.l), p.l],
    e: (p, A) => `T = 2π√(l/g) = 2π√(${p.l}/π²) = 2√${p.l} = ${A}.` }),
  T('O3', 'Oscillations', { S: ['m,k', [1, 100], [4, 100], [2, 50], [0.5, 50], [1, 25], [4, 64]],
    q: p => `A block of mass ${p.m} kg attached to a spring of spring constant ${p.k} N/m oscillates on a smooth surface. Find the angular frequency of the oscillation.`,
    a: p => Math.sqrt(p.k / p.m), U: 'rad/s', X: p => [p.k / p.m, Math.sqrt(p.m / p.k), 2 * Math.PI * Math.sqrt(p.m / p.k)],
    e: (p, A) => `ω = √(k/m) = √(${p.k}/${p.m}) = ${A}.` }),

  T('E1', 'Electrostatics', { S: ['q1,q2,d', [4, 1, 20], [3, 1, 30], [5, 2, 30], [6, 2, 20], [8, 2, 40]],
    q: p => `Two like point charges of +${p.q1} μC and +${p.q2} μC are ${p.d} cm apart in air. Find the magnitude of E at the midpoint of the line joining them. (k = 9 × 10⁹ N m²/C²)`,
    a: p => 9e9 * (p.q1 - p.q2) * 1e-6 / Math.pow(p.d / 200, 2), U: 'N/C',
    X: p => [9e9 * (p.q1 + p.q2) * 1e-6 / Math.pow(p.d / 200, 2), 9e9 * (p.q1 - p.q2) * 1e-6 / Math.pow(p.d / 100, 2), 9e9 * p.q1 * 1e-6 / Math.pow(p.d / 200, 2)],
    e: (p, A) => `At the midpoint the two fields point in opposite directions, so E = k(q₁ − q₂)/r² with r = ${p.d / 2} cm = ${p.d / 200} m. E = 9 × 10⁹ × ${p.q1 - p.q2} × 10⁻⁶ / (${p.d / 200})² = ${A}.` }),
  T('E2', 'Electrostatics', { P: { q: [1, 2, 5, 10] },
    q: p => `Find the flux through a closed surface enclosing a charge of ${p.q} μC in vacuum. (ε₀ = 8.85 × 10⁻¹² C²/N m²)`,
    a: p => p.q * 1e-6 / 8.85e-12, U: 'N m²/C', X: p => [p.q * 1e-6 / (4 * Math.PI * 8.85e-12), p.q * 1e-6 / 8.85e-12 * 4 * Math.PI, p.q * 1e-6 / 8.85e-9],
    e: (p, A) => `By Gauss's law Φ = q/ε₀ = ${p.q} × 10⁻⁶ / (8.85 × 10⁻¹²) = ${A}, whatever the shape of the surface.` }),
  T('E3', 'Electrostatics', { P: { pm: [2, 4, 5], E: [1000, 2000, 5000], th: [30, 37, 53, 90] },
    q: p => `A dipole of moment p = ${p.pm} × 10⁻⁶ C m is held in a uniform field of ${p.E} N/C at ${p.th}° to the field. Find the torque on the dipole. (sin ${p.th}° = ${SIN[p.th]})`,
    a: p => p.pm * 1e-6 * p.E * SIN[p.th], U: 'N m', X: p => [p.pm * 1e-6 * p.E * COS_[p.th], p.pm * 1e-6 * p.E, p.pm * 1e-6 * p.E * SIN[p.th] * 2],
    e: (p, A) => `τ = pE sinθ = ${p.pm} × 10⁻⁶ × ${p.E} × ${SIN[p.th]} = ${A}.` }),

  T('C1', 'Current Electricity', { P: { pa: [5, 10, 20], qa: [10, 20, 40], ra: [5, 10, 15, 20] },
    q: p => `A Wheatstone bridge is balanced with P = ${p.pa} Ω, Q = ${p.qa} Ω and R = ${p.ra} Ω, where P/Q = R/S. Find the unknown resistance S.`,
    a: p => p.qa * p.ra / p.pa, U: 'Ω', X: p => [p.pa * p.ra / p.qa, p.pa * p.qa / p.ra, p.qa + p.ra - p.pa],
    e: (p, A) => `At balance P/Q = R/S, so S = QR/P = ${p.qa} × ${p.ra} / ${p.pa} = ${A}.` }),
  T('C2', 'Current Electricity', { S: ['E,r,R', [12, 1, 5], [12, 2, 4], [10, 1, 4], [6, 1, 2], [9, 1, 2], [6, 2, 4]],
    q: p => `A cell of emf ${p.E} V and internal resistance ${p.r} Ω is connected across an external resistor of ${p.R} Ω. Find the terminal voltage of the cell.`,
    a: p => p.E * p.R / (p.R + p.r), U: 'V', X: p => [p.E, p.E * p.r / (p.R + p.r), p.E * (p.R - p.r) / (p.R + p.r)],
    e: (p, A) => `The current is I = E/(R + r) = ${p.E}/(${p.R} + ${p.r}) = ${fmt(p.E / (p.R + p.r))} A, so V = IR = ${fmt(p.E / (p.R + p.r))} × ${p.R} = ${A}.` }),
  T('C3', 'Current Electricity', { P: { R: [2, 5, 10], I: [2, 3, 5], t: [10, 20, 60] },
    q: p => `A heater coil of resistance ${p.R} Ω carries a steady current of ${p.I} A for ${p.t} s. Find the heat produced.`,
    a: p => p.I * p.I * p.R * p.t, U: 'J', X: p => [p.I * p.R * p.t, p.I * p.I * p.R, p.I * p.I * p.t / p.R],
    e: (p, A) => `Joule heating H = I²Rt = ${p.I}² × ${p.R} × ${p.t} = ${A}.` }),

  T('P1', 'Ray Optics', { S: ['u,f', [30, 10], [20, 10], [15, 10], [60, 20], [30, 20], [24, 8], [36, 12]],
    q: p => `A real object is placed ${p.u} cm in front of a concave mirror of focal length ${p.f} cm. Find the distance of the image from the mirror.`,
    a: p => p.u * p.f / (p.u - p.f), U: 'cm', X: p => [p.u * p.f / (p.u + p.f), p.u - p.f, p.u + p.f],
    e: (p, A) => `The mirror formula 1/v + 1/u = 1/f gives 1/v = 1/${p.f} − 1/${p.u}, so v = ${A}, a real image in front of the mirror.` }),
  T('P2', 'Ray Optics', { P: { c: [0, 1, 2, 3] },
    q: p => p.c < 2 ? `An equilateral prism has refractive index ${PR[p.c][0]}. Find its angle of minimum deviation.` : `An equilateral prism shows a minimum deviation of ${PR[p.c - 2][1]}°. Find its refractive index.`,
    o: p => p.c < 2 ? ['30°', '45°', '60°', '75°'] : ['√2', '√3', '1.5', '2'],
    a: p => p.c < 2 ? PR[p.c][1] + '°' : PR[p.c - 2][0],
    e: (p) => { const d = PR[p.c % 2][1], n = PR[p.c % 2][0]; return `At minimum deviation n = sin((A + δ)/2) / sin(A/2), with A = 60°. For δ = ${d}°, n = sin ${(60 + d) / 2}° / sin 30° = ${n}.`; } }),
  T('P3', 'Ray Optics', { P: { c: [0, 1, 2] },
    q: p => `Light travelling in glass meets the glass–air boundary. The refractive index of the glass is ${CR[p.c][0]}. Find the critical angle.`,
    o: p => ['30°', '37°', '45°', '60°'], a: p => CR[p.c][1] + '°',
    e: (p, A) => `sin C = 1/n = 1/${CR[p.c][0]} = ${CR[p.c][2]}, so C = ${A}.` }),

  T('N1', 'Nuclei', { P: { h: [5, 10, 20, 30], k: [1, 2, 3, 4] },
    q: p => `The half-life of a radioactive sample is ${p.h} days. What fraction of the sample remains after ${p.h * p.k} days?`,
    o: p => ['1/2', '1/4', '1/8', '1/16', '1/32'], a: p => '1/' + Math.pow(2, p.k),
    e: (p, A) => `${p.h * p.k} days is ${p.k} half-lives, so the fraction left is (1/2)^${p.k} = ${A}.` }),
  T('N2', 'Nuclei', { P: { d: [0.01, 0.02, 0.03, 0.05, 0.1, 0.2] },
    q: p => `A nucleus has a mass defect of ${p.d} u. Find its binding energy. (1 u = 931.5 MeV/c²)`,
    a: p => p.d * 931.5, U: 'MeV', X: p => [p.d * 931.5 / 2, p.d * 931.5 * 2, p.d * 93.15],
    e: (p, A) => `Binding energy = Δm c² = ${p.d} × 931.5 = ${A}.` }),
  T('N3', 'Nuclei', { P: { l: [0.05, 0.1, 0.2, 0.25, 0.5] },
    q: p => `A nuclide has a decay constant of ${p.l} s⁻¹. Find its mean life.`,
    a: p => 1 / p.l, U: 's', X: p => [0.693 / p.l, p.l, 2 / p.l],
    e: (p, A) => `Mean life τ = 1/λ = 1/${p.l} = ${A}. (The half-life would be 0.693τ.)` }),

  T('S1', 'Semiconductors & Electronics', { P: { g: [0, 1, 2, 3, 4] },
    q: p => `Which logic gate ${LG[p.g][1]}?`,
    o: p => LG.map(x => x[0]), a: p => LG[p.g][0],
    e: (p, A) => `A gate that ${LG[p.g][1]} is the ${A} gate.` }),
  T('S2', 'Semiconductors & Electronics', { P: { b: [0, 1] },
    q: p => `The depletion layer of a p–n junction diode ______ when the diode is ${p.b ? 'reverse' : 'forward'} biased.`,
    o: p => ['becomes narrower', 'becomes wider', 'remains unchanged', 'first widens and then narrows'], a: p => p.b ? 'becomes wider' : 'becomes narrower',
    e: (p) => p.b ? 'Reverse bias pulls majority carriers away from the junction, so the depletion layer widens.' : 'Forward bias pushes majority carriers toward the junction, so the depletion layer narrows.' }),
  T('S3', 'Semiconductors & Electronics', { P: { b: [50, 100, 150, 200], ib: [10, 20, 40, 50] },
    q: p => `In a common-emitter transistor circuit the current gain β is ${p.b} and the base current is ${p.ib} μA. Find the collector current.`,
    a: p => p.b * p.ib / 1000, U: 'mA', X: p => [p.b * p.ib, p.ib / p.b / 1000, (p.b + 1) * p.ib / 1000],
    e: (p, A) => `I_C = βI_B = ${p.b} × ${p.ib} μA = ${p.b * p.ib} μA = ${A}.` }),
];
const BYID = new Map(TPL.map(t => [t.id, t]));
const TOPICS = [...new Set(TPL.map(t => t.topic))];

/* ---------- build one question from a template ---------- */
function params(t, R) {
  if (t.S) { const keys = t.S[0].split(','), row = pick(R, t.S.slice(1)), p = {}; keys.forEach((k, i) => { p[k] = row[i]; }); return p; }
  const p = {}; for (const k in t.P) p[k] = pick(R, t.P[k]); return p;
}
function numericOptions(ans, slips) {
  const seen = new Set([fmt(ans)]), extra = [];
  const add = v => { if (!isFinite(v) || (ans > 0 && v <= 0)) return; const s = fmt(v); if (!seen.has(s)) { seen.add(s); extra.push(v); } };
  (slips || []).forEach(add);
  [2, 0.5, 1.5, 0.75, 4, 0.25, 10, 0.1].forEach(m => add(ans * m));
  return [ans].concat(extra.slice(0, 3));
}
function buildFrom(t, p, R) {
  const text = t.q(p);
  let correct, opts;
  if (t.o) {
    correct = t.a(p);
    const all = t.o(p), rest = shuffle(all.filter(x => x !== correct), R).slice(0, 3);
    opts = [correct].concat(rest);
  } else {
    const ans = t.a(p); correct = withUnit(ans, t.U);
    opts = numericOptions(ans, t.X ? t.X(p) : []).map(v => withUnit(v, t.U));
  }
  const order = shuffle(opts, R);
  const options = order.map((o, i) => ({ key: 'ABCD'[i], text: o }));
  const answer = options.find(o => o.text === correct).key;
  return { text, options, answer, explanation: t.e(p, correct), topic: t.topic, gen: t.id, src: 'math' };
}
/* a fresh question on template `id`; the stream R decides the numbers and the option order */
function make(id, R) { const t = BYID.get(id); return buildFrom(t, params(t, R), R); }
/* the exact answer for given parameters, used to check the solvers against hand-worked values */
function solve(id, p) { const t = BYID.get(id); const a = t.a(p); return typeof a === 'string' ? a : +a; }
function questionWith(id, p, seed) { const t = BYID.get(id); return buildFrom(t, p, rng(seed || 1)); }

/* ---------- synthetic demo papers: 12 topics x 3 concepts across 21 years ---------- */
const KINDS = ['steady', 'cycle', 'rise', 'cycle', 'fade', 'low', 'steady', 'cycle', 'rise', 'low', 'fade', 'steady'];
function demoBank(seed, y0, y1) {
  y0 = y0 || 2006; y1 = y1 || 2026;
  const R = rng(seed || 11), items = [];
  const NQ = ['potential', 'energy', 'momentum', 'period', 'frequency', 'pressure', 'charge', 'current', 'field', 'torque', 'wavelength', 'speed', 'force', 'power', 'flux'];
  const NO = ['uniform rod', 'thin ring', 'metallic sphere', 'copper wire', 'glass block', 'gas cylinder', 'light bulb', 'magnetic needle', 'steel wire', 'iron bar', 'water jet', 'liquid drop', 'wooden cube', 'hollow shell', 'long cylinder'];
  const NC = ['when it is heated by 20 K', 'at a distance of 3 m', 'after 5 s', 'if its length is doubled', 'if its radius is halved', 'when the temperature rises', 'if its mass is increased', 'near the surface', 'in a vacuum chamber', 'under constant force', 'when it moves slowly', 'if it is cut into two equal parts'];
  for (let y = y0; y <= y1; y++) {
    const t = y - y0, span = y1 - y0; let n = 0;
    TPL.forEach((tp, i) => {
      const kind = KINDS[i % 12], per = 3 + (i % 3), ph = i % per; let pr;
      if (kind === 'steady') pr = 0.5; else if (kind === 'low') pr = 0.12;
      else if (kind === 'rise') pr = 0.08 + 0.6 * t / span; else if (kind === 'fade') pr = 0.66 - 0.56 * t / span;
      else pr = ((t - ph) % per === 0) ? 0.85 : 0.05;
      if (R() < pr) {
        let q = make(tp.id, R); items.push(Object.assign({ year: y, concept: null }, q)); n++;
        if (R() < 0.12) { q = make(tp.id, R); items.push(Object.assign({ year: y, concept: null }, q)); n++; }
      }
    });
    while (n < 30) { items.push({ year: y, text: 'Find the ' + pick(R, NQ) + ' of a ' + pick(R, NO) + ' ' + pick(R, NC) + '.', topic: pick(R, TOPICS), concept: null }); n++; }
  }
  return items;
}

/* hand-worked answers, written down independently of the solvers; the app re-checks every solver against them at start-up */
const VECTORS = [
  ['K1', { v: 20 }, 20],
  ['K2', { v: 20, th: 30 }, 2], ['K2', { v: 25, th: 37 }, 3],
  ['K3', { w: 200, b: 10, c: 3 }, 20],
  ['L1', { m: 5, mu: 0.4 }, 20],
  ['L2', { m1: 2, m2: 3 }, 2], ['L2', { m1: 3, m2: 5 }, 2.5],
  ['L3', { m: 60, a: 5 }, 900],
  ['W1', { m: 2, v1: 2, v2: 6 }, 32],
  ['W2', { k: 200, x: 10 }, 1], ['W2', { k: 500, x: 20 }, 10],
  ['W3', { m: 200, h: 20, t: 20 }, 2000],
  ['R1', { m: 4, r: 20 }, 0.08],
  ['R2', { s: 0 }, '1/2'], ['R2', { s: 1 }, '1/3'], ['R2', { s: 2 }, '2/7'], ['R2', { s: 3 }, '2/5'],
  ['R3', { m: 3, r: 4, v: 6 }, 72],
  ['G1', { n: 9 }, 33.6],
  ['G2', { f: [1, 4] }, 7.5],
  ['G3', { n: 16 }, 2],
  ['T1', { T: 300 }, 1718.1],
  ['T2', { a: 500, b: 300 }, 40],
  ['T3', { pr: 200, v: 3 }, 600],
  ['O1', { A: 5, w: 10 }, 50],
  ['O2', { l: 9 }, 6],
  ['O3', { m: 4, k: 100 }, 5],
  ['E1', { q1: 4, q2: 1, d: 20 }, 2.7e6],
  ['E2', { q: 2 }, 225988.7, 0.5],
  ['E3', { pm: 4, E: 2000, th: 37 }, 4.8e-3],
  ['C1', { pa: 10, qa: 20, ra: 15 }, 30],
  ['C2', { E: 12, r: 2, R: 4 }, 8],
  ['C3', { R: 5, I: 3, t: 20 }, 900],
  ['P1', { u: 60, f: 20 }, 30],
  ['P2', { c: 0 }, '30°'], ['P2', { c: 1 }, '60°'], ['P2', { c: 2 }, '√2'], ['P2', { c: 3 }, '√3'],
  ['P3', { c: 1 }, '45°'],
  ['N1', { h: 10, k: 3 }, '1/8'],
  ['N2', { d: 0.1 }, 93.15],
  ['N3', { l: 0.25 }, 4],
  ['S1', { g: 3 }, 'NOR'],
  ['S2', { b: 1 }, 'becomes wider'],
  ['S3', { b: 100, ib: 20 }, 2],
];

const GEN = { VECTORS, TPL, TOPICS, make, solve, questionWith, demoBank, fmt, rng, hash32, shuffle, pick, count: TPL.length };
if (typeof module !== 'undefined' && module.exports) module.exports = GEN; else root.GEN = GEN;
})(typeof window !== 'undefined' ? window : globalThis);
