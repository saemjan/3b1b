/* Exam Forecaster engine — pure JS, no DOM. Works in browsers and Node. */
(function (root) {
'use strict';

/* ---------- helpers ---------- */
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const sigmoid = z => 1 / (1 + Math.exp(-z));
const logit = p => { p = clamp(p, 1e-4, 1 - 1e-4); return Math.log(p / (1 - p)); };
const mean = a => a.length ? a.reduce((s, x) => s + x, 0) / a.length : 0;
const median = a => { if (!a.length) return 0; const b = [...a].sort((x, y) => x - y), m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
function rng(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const tick = () => new Promise(r => setTimeout(r, 0));
const MAXP = 0.95, LR_MARGIN = 0.02, MIN_TESTED = 4, SHRINK = 0.75, MIN_PAPERS = 11;
const normKey = s => String(s == null ? '' : s).toLowerCase().replace(/\s+/g, ' ').trim();

/* ---------- reading files ---------- */
function detectDelimiter(text) {
  const first = text.split(/\r?\n/, 1)[0] || '';
  const counts = { ',': 0, ';': 0, '\t': 0 };
  let inQ = false;
  for (const ch of first) { if (ch === '"') inQ = !inQ; else if (!inQ && ch in counts) counts[ch]++; }
  const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return best[1] > 0 ? best[0] : ',';
}
function parseDelimited(text) {
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  const d = detectDelimiter(text), rows = [];
  let row = [], field = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false; }
      else field += c;
    } else if (c === '"') inQ = true;
    else if (c === d) { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (c !== '\r') field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows.filter(r => r.some(x => x.trim() !== ''));
}
const ALIAS = {
  year: ['year', 'yr', 'exam year', 'paper year', 'session'],
  text: ['question', 'questions', 'question text', 'text', 'q', 'ques', 'problem', 'statement'],
  topic: ['topic', 'chapter', 'chapter name', 'unit', 'topic name'],
  concept: ['concept', 'subtopic', 'sub topic', 'subconcept'],
};
const hnorm = s => String(s == null ? '' : s).toLowerCase().replace(/[_\-]+/g, ' ').replace(/\s+/g, ' ').trim();
function mapColumns(header) {
  const cols = {};
  header.forEach((h, i) => { const n = hnorm(h); for (const key in ALIAS) if (cols[key] === undefined && ALIAS[key].includes(n)) cols[key] = i; });
  return cols;
}
const yearOf = v => { const m = String(v == null ? '' : v).match(/\b(19[89]\d|20[0-4]\d)\b/); return m ? parseInt(m[1], 10) : null; };
function makeRecord(year, text, topic, concept) {
  text = String(text == null ? '' : text).replace(/\s+/g, ' ').trim().slice(0, 1500);
  if (!year || text.length < 8) return null;
  return { year, text, topic: topic && String(topic).trim() ? String(topic).trim() : null, concept: concept && String(concept).trim() ? String(concept).trim() : null };
}
function recordsFromRows(rows) {
  if (!rows.length) return { records: [], error: 'The file is empty.' };
  const cols = mapColumns(rows[0]);
  if (cols.year === undefined || cols.text === undefined) return { records: [], error: 'Add a header row with "year" and "question" columns (optional: "topic", "concept").' };
  const records = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    const rec = makeRecord(yearOf(r[cols.year]), r[cols.text], cols.topic !== undefined ? r[cols.topic] : null, cols.concept !== undefined ? r[cols.concept] : null);
    if (rec) records.push(rec);
  }
  return { records };
}
function recordsFromObjects(arr) {
  const records = [];
  for (const o of arr) {
    if (!o || typeof o !== 'object') continue;
    const keys = Object.keys(o), cols = mapColumns(keys);
    if (cols.year === undefined || cols.text === undefined) continue;
    const rec = makeRecord(yearOf(o[keys[cols.year]]), o[keys[cols.text]], cols.topic !== undefined ? o[keys[cols.topic]] : null, cols.concept !== undefined ? o[keys[cols.concept]] : null);
    if (rec) records.push(rec);
  }
  return { records, error: records.length ? undefined : 'No objects with "year" and "question" fields were found.' };
}
function yearFromHeader(line) {
  const s = line.trim();
  if (!s || s.length > 60) return null;
  const m = s.match(/\b(19[89]\d|20[0-4]\d)\b/);
  if (!m) return null;
  const rest = s.replace(m[0], ' ').toLowerCase().replace(/[^a-z\s]/g, ' ')
    .replace(/\b(year|paper|papers|exam|examination|session|question|questions|neet|ug|jee|main|mains|advanced|aipmt|cbse|board|class|xii|xi|th|shift|set|code|physics|chemistry|biology|maths|mathematics|final|memory|based|of|the|for|and|in|to|from|held|on)\b/g, ' ')
    .replace(/\s+/g, '');
  return /^[a-e]?$/.test(rest) ? parseInt(m[1], 10) : null;
}
const Q_RES = [
  ['q', /^\s*q(?:uestion)?\s*\.?\s*(\d{1,3})\s*[\)\].:\-–]?\s*(.*)$/i],
  ['dot', /^\s*(\d{1,3})\s*\.\s+(\S.*)$/],
  ['rparen', /^\s*(\d{1,3})\s*\)\s*(\S.*)$/],
  ['paren', /^\s*\(\s*(\d{1,3})\s*\)\s*(\S.*)$/],
  ['brack', /^\s*\[\s*(\d{1,3})\s*\]\s*(\S.*)$/],
];
function parsePaperText(text, defaultYear) {
  const lines = text.replace(/\r/g, '').split('\n');
  const records = [], counts = new Map();
  let year = defaultYear || null, last = 0, style = null, cur = null, blank = true, section = false, noYear = 0;
  const flush = () => {
    if (!cur) return;
    const rec = makeRecord(cur.year, cur.text, null, null);
    if (rec) { records.push(rec); counts.set(rec.year, (counts.get(rec.year) || 0) + 1); }
    else if (!cur.year && cur.text.trim().length >= 8) noYear++;
    cur = null;
  };
  for (const line of lines) {
    if (!line.trim()) { blank = true; continue; }
    const hy = yearFromHeader(line);
    if (hy && (blank || !cur)) { flush(); year = hy; last = 0; style = null; section = false; blank = false; continue; }
    if (/^\s*(section|part)\b/i.test(line) && line.length < 60) { flush(); section = true; blank = false; continue; }
    let hit = null;
    for (const [st, re] of Q_RES) {
      const m = line.match(re);
      if (!m) continue;
      const n = parseInt(m[1], 10);
      let ok = false;
      if (st === 'q') ok = true;
      else if (style === null) ok = n <= 3;
      else if (st === style) ok = n === last + 1 || (n === 1 && (blank || section) && last >= 3);
      if (ok) { hit = { st, n, rest: m[2] }; break; }
    }
    if (hit) {
      flush();
      if (hit.st !== 'q' || style === null) style = style === null ? hit.st : style;
      last = hit.n; section = false;
      cur = { year, text: hit.rest };
    } else if (cur) cur.text += ' ' + line.trim();
    blank = false;
  }
  flush();
  return { records, counts, noYear };
}

/* ---------- topic labels from a syllabus list ---------- */
function kwRegex(kw) {
  let s = kw.trim().toLowerCase().replace(/['’`]/g, '');
  const wild = s.endsWith('*'); if (wild) s = s.slice(0, -1);
  const esc = s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '[\\s\\-]+');
  return new RegExp('(?:^|[^a-z0-9])' + esc + (wild ? '[a-z]*' : '(?:s|es)?') + '(?![a-z0-9])', 'i');
}
function compileSyllabus(text) {
  const out = [];
  for (const raw of String(text || '').split(/\n/)) {
    const line = raw.trim(); if (!line || line[0] === '#') continue;
    const i = line.indexOf(':'); if (i < 1) continue;
    const name = line.slice(0, i).trim();
    const kws = line.slice(i + 1).split(',').map(x => x.trim()).filter(Boolean);
    kws.push(name);
    out.push({ name, kws: kws.map(k => ({ re: kwRegex(k), w: 1 + 0.6 * (k.trim().split(/\s+/).length - 1) })) });
  }
  return out;
}
function tagWithSyllabus(text, syl) {
  const t = ' ' + String(text).toLowerCase().replace(/['’`]/g, '') + ' ';
  let best = null, bs = 0;
  for (const s of syl) { let sc = 0; for (const k of s.kws) if (k.re.test(t)) sc += k.w; if (sc > bs) { bs = sc; best = s.name; } }
  return best;
}
const PHYSICS_SYLLABUS = `Units & Measurement: dimension*, significant figures, least count, vernier, screw gauge, order of magnitude, percentage error, absolute error, physical quantity, si unit
Vectors: vector, scalar product, dot product, cross product, vector product, resultant, unit vector, components of, angle between
Kinematics: displacement, velocity-time, position-time, uniformly accelerated, uniform acceleration, free fall, freely falling, projectile, time of flight, maximum height, relative velocity, average speed, distance travelled, dropped from, thrown vertically, thrown upward, river, boat, swimmer
Circular Motion: circular motion, centripetal, angular velocity, banking, banked, conical pendulum, vertical circle, uniform circular, radial acceleration, tangential acceleration
Laws of Motion: newtons law, newtons second, friction, coefficient of friction, inclined plane, pulley, atwood, tension in, normal reaction, pseudo force, lift accelerating, elevator, apparent weight, limiting friction, impulse, recoil
Work Energy Power: work done, kinetic energy, potential energy, work energy theorem, power of, conservative force, spring compressed, mechanical energy, watt, horsepower, work by friction
Rotational Motion: moment of inertia, torque, angular momentum, centre of mass, center of mass, radius of gyration, rolling, without slipping, rotational kinetic, parallel axis, perpendicular axis, angular acceleration, disc, coefficient of restitution, elastic collision, inelastic collision, linear momentum
Gravitation: gravitation*, gravitational, escape velocity, escape speed, orbital velocity, kepler*, satellite, acceleration due to gravity, geostationary, orbit, planet, mass of earth
Mechanical Properties of Solids: youngs modulus, stress, strain, elastic, bulk modulus, shear modulus, modulus of rigidity, poissons ratio, hookes law, elongation, breaking stress, elastic potential energy, stretched wire
Mechanical Properties of Fluids: fluid, pressure, buoyan*, archimedes, bernoulli, viscosity, viscous, terminal velocity, surface tension, capillar*, stokes, streamline, torricelli, pascal, manometer, excess pressure, soap bubble, poiseuille, reynolds, floating, submerged
Thermal Properties of Matter: specific heat, latent heat, calorimetr*, thermal expansion, coefficient of linear, coefficient of volume, thermal conductivity, conduction, convection, stefan, newtons law of cooling, cooling, wien, black body, blackbody, heat transfer, celsius, fahrenheit, thermal stress, melting, steam
Thermodynamics: thermodynamic*, first law, second law, isotherm*, adiabat*, isobaric, isochoric, carnot, efficiency of, heat engine, refrigerator, coefficient of performance, entropy, cyclic process, pv diagram, p-v diagram, internal energy, work done by gas, reversible, free expansion
Kinetic Theory: kinetic theory, rms speed, root mean square, mean free path, degrees of freedom, equipartition, ideal gas, gas equation, molar specific heat, monoatomic, diatomic, mean kinetic energy, boyles law, charles law
Oscillations: simple harmonic, shm, oscillat*, time period, simple pendulum, spring mass, angular frequency, amplitude, damped, restoring force, physical pendulum, torsional pendulum, spring constant
Waves & Sound: wave, sound, stationary wave, standing wave, doppler, beats, organ pipe, closed pipe, open pipe, resonance tube, vibrating string, transverse wave, longitudinal wave, harmonic, overtone, intensity level, decibel, superposition, sonometer, node, antinode, wavelength, progressive wave
Electrostatics: electric field, electric charge, coulomb, gauss*, electric flux, dipole, electric potential, equipotential, point charge, charged sphere, charged ring, charged conductor, line charge, electric lines, charge distribution, uniformly charged
Capacitors: capacitor, capacitance, dielectric, parallel plate, energy stored in, combination of capacitors, charging of capacitor, common potential
Current Electricity: resistance, resistivity, resistor, ohms law, kirchhoff*, wheatstone, meter bridge, potentiometer, drift velocity, emf, internal resistance, battery, ammeter, voltmeter, shunt, electric power, heating effect, joule, colour code, conductivity, mobility, current density, filament, fuse, post office box, terminal voltage
Magnetic Effects of Current: magnetic field, biot savart, biot-savart, amperes law, solenoid, toroid, lorentz force, cyclotron, moving coil galvanometer, galvanometer, current carrying wire, current carrying conductor, current loop, magnetic moment, straight wire, circular loop, force between parallel
Magnetism & Matter: bar magnet, magnetic dipole, diamagnet*, paramagnet*, ferromagnet*, earths magnetic, magnetic declination, angle of dip, hysteresis, susceptibility, permeability, curie, magnetic poles, neutral point, magnetic meridian, retentivity, coercivity
Electromagnetic Induction: faraday*, lenz*, induced emf, self inductance, mutual inductance, eddy current, motional emf, induced current, magnetic flux, generator, inductor, sliding rod
Alternating Current: alternating, ac circuit, lcr, lc circuit, rms value, reactance, impedance, resonant frequency, power factor, transformer, wattless, choke, step up, step down, peak value, ac source
Electromagnetic Waves: electromagnetic wave, electromagnetic spectrum, displacement current, gamma rays, microwave, radio wave, ultraviolet, infrared, maxwell, poynting, em wave, speed of light
Ray Optics: lens, mirror, refraction, reflection, focal length, refractive index, total internal reflection, prism, critical angle, telescope, microscope, magnifying power, power of lens, image distance, real image, virtual image, optical instrument, dispersion, rainbow, myopia, hypermetropia, lens maker, minimum deviation, apparent depth, concave, convex, plane mirror, glass slab
Wave Optics: interfer*, youngs double slit, double slit, diffract*, polaris*, brewster, fringe, coherent, huygens, single slit, path difference, malus, resolving power, optical path, monochromatic, polaroid, unpolarised
Dual Nature of Radiation & Matter: photoelectric, work function, threshold frequency, stopping potential, de broglie, photon, davisson, matter wave, photocurrent, momentum of photon
Atoms: bohr, hydrogen atom, rutherford, spectral series, lyman, balmer, paschen, energy level, orbit radius, alpha particle scattering, ionization energy, hydrogen spectrum, electron transition, excited state, ground state
Nuclei: radioactiv*, half life, half-life, decay, binding energy, mass defect, nuclear, fission, fusion, alpha decay, beta decay, activity of, becquerel, mean life, decay constant, radius of nucleus, mass number, nuclear reactor
Semiconductors & Electronics: semiconductor, p-n junction, pn junction, diode, transistor, logic gate, rectifier, zener, n-type, p-type, band gap, energy band, led, photodiode, amplifier, nand, nor gate, boolean, truth table, forward bias*, reverse bias*, depletion, doping, common emitter
Communication Systems: modulation, amplitude modulation, frequency modulation, antenna, bandwidth, carrier wave, sky wave, ground wave, demodulation, communication system, transmitter, receiver, modulation index, space wave, optical fibre, satellite communication`;

/* ---------- text -> vectors ---------- */
const STOP = new Set(('a an the of in on at to for from by with and or but if then than as is are was were be been being this that these those it its into onto over under between among about above below up down out off per each any all both either neither not no nor so such can could may might will would shall should must do does did done has have had having which what when where who whom whose why how ' +
  'find calculate determine given following statement statements correct incorrect true false option options choose answer value values assertion reason select match column list question also only one two three four ' +
  'kg cm mm km ms hz ev mev nm ml gm kj mj ma mv kv sec seconds metre meter metres meters unit units').split(' '));
function stem(w) {
  if (w.length > 5 && w.endsWith('ies')) return w.slice(0, -3) + 'y';
  if (w.length > 5 && w.endsWith('ing')) return w.slice(0, -3);
  if (w.length > 4 && w.endsWith('ed')) return w.slice(0, -2);
  if (w.length > 4 && w.endsWith('es')) return w.slice(0, -2);
  if (w.length > 3 && w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);
  return w;
}
function featureTokens(text, surf) {
  const words = (String(text).toLowerCase().replace(/['’`]/g, '').match(/[a-z\u0900-\u097f]{2,}/g)) || [];
  const uni = [];
  for (const w of words) {
    if (STOP.has(w)) continue;
    const s = stem(w); uni.push(s);
    if (surf) { let m = surf.get(s); if (!m) surf.set(s, m = new Map()); m.set(w, (m.get(w) || 0) + 1); }
  }
  const toks = uni.slice();
  for (let i = 0; i + 1 < uni.length; i++) toks.push(uni[i] + '_' + uni[i + 1]);
  return toks;
}
function makeVec(toks, idf) {
  const tf = new Map();
  for (const t of toks) tf.set(t, (tf.get(t) || 0) + 1);
  const v = new Map(); let n2 = 0;
  for (const [t, c] of tf) { const w = (1 + Math.log(c)) * idf(t); v.set(t, w); n2 += w * w; }
  const n = Math.sqrt(n2) || 1;
  for (const [t, w] of v) v.set(t, w / n);
  return v;
}
function dot(a, b) { if (a.size > b.size) { const t = a; a = b; b = t; } let s = 0; for (const [t, w] of a) { const x = b.get(t); if (x) s += w * x; } return s; }

/* ---------- data prep ---------- */
function prepare(records, excluded, warnings) {
  const surf = new Map();
  let recs = records.filter(r => r.year && r.text);
  const yearsAll = [...new Set(recs.map(r => r.year))].sort((a, b) => a - b);
  const sizeAll = new Map(yearsAll.map(y => [y, 0]));
  for (const r of recs) sizeAll.set(r.year, sizeAll.get(r.year) + 1);
  const used = new Set();
  const isExcl = t => { if (!t) return false; const k = normKey(t); for (const e of excluded) if (e.length >= 3 && k.includes(e)) { used.add(e); return true; } return false; };
  recs = recs.filter(r => !isExcl(r.topic));
  for (const e of excluded) if (!used.has(e)) warnings.push('"' + e + '" matched no topic, so nothing was removed for it.');
  const years = [...new Set(recs.map(r => r.year))].sort((a, b) => a - b);
  const yi = new Map(years.map((y, i) => [y, i]));
  const qs = recs.map((r, i) => ({ id: i, p: yi.get(r.year), year: r.year, text: r.text, topic: r.topic || null, concept: r.concept || null, ref: r.ref, toks: featureTokens(r.text, surf) }));
  const byPaper = years.map(() => []);
  for (const q of qs) byPaper[q.p].push(q);
  const sizes = byPaper.map(a => a.length), sizesPre = years.map(y => sizeAll.get(y));
  const med = median(sizes);
  years.forEach((y, i) => { if (med >= 10 && sizes[i] < 0.4 * med) warnings.push(y + ' has only ' + sizes[i] + ' questions (typical: ' + Math.round(med) + '). Check that paper was read correctly.'); });
  return { years, N: years.length, qs, byPaper, sizes, sizesPre, surf };
}

/* ---------- concept clustering ---------- */
function buildFold(data, k, tau) {
  const hist = []; for (let p = 0; p < k; p++) for (const q of data.byPaper[p]) hist.push(q);
  const df = new Map();
  for (const q of hist) for (const t of new Set(q.toks)) df.set(t, (df.get(t) || 0) + 1);
  const nDoc = hist.length;
  const idf = t => Math.log((1 + nDoc) / (1 + (df.get(t) || 0))) + 1;
  const clusters = [], byTopic = new Map(), byLabel = new Map();
  const addCluster = (q, v, label) => {
    const c = { id: clusters.length, topic: q.topic, label: label || null, sum: new Map(v), norm2: 1, members: [q], pres: new Uint8Array(data.N) };
    c.pres[q.p] = 1; clusters.push(c);
    const key = q.topic || ''; if (!byTopic.has(key)) byTopic.set(key, []); byTopic.get(key).push(c);
    return c;
  };
  const addMember = (c, q, v) => { c.norm2 += 2 * dot(v, c.sum) + 1; for (const [t, w] of v) c.sum.set(t, (c.sum.get(t) || 0) + w); c.members.push(q); c.pres[q.p] = 1; };
  const best = (v, topic) => { let bc = null, bs = 0; for (const c of byTopic.get(topic || '') || []) { const s = dot(v, c.sum) / Math.sqrt(c.norm2); if (s > bs) { bs = s; bc = c; } } return { c: bc, s: bs }; };
  for (const q of hist) {
    const v = makeVec(q.toks, idf);
    if (q.concept) {
      const key = (q.topic || '') + '||' + normKey(q.concept);
      let c = byLabel.get(key);
      if (!c) { c = addCluster(q, v, q.concept); byLabel.set(key, c); } else addMember(c, q, v);
      continue;
    }
    const r = best(v, q.topic);
    if (r.c && r.s >= tau) addMember(r.c, q, v); else addCluster(q, v, null);
  }
  return { k, tau, clusters, idf, best, byLabel };
}
function labelFold(data, fold) {
  const y = new Uint8Array(fold.clusters.length), assigned = [];
  let matched = 0;
  for (const q of data.byPaper[fold.k]) {
    let c = null;
    if (q.concept) c = fold.byLabel.get((q.topic || '') + '||' + normKey(q.concept)) || null;
    if (!c) { const r = fold.best(makeVec(q.toks, fold.idf), q.topic); if (r.c && r.s >= fold.tau) c = r.c; }
    if (c) { y[c.id] = 1; matched++; assigned.push(c.id); } else assigned.push(-1);
  }
  fold.y = y; fold.assigned = assigned; fold.matchedQs = matched; fold.nQs = assigned.length;
}

/* ---------- features ---------- */
function topicShares(data, k) {
  const m = new Map();
  for (let p = 0; p < k; p++) {
    const qs = data.byPaper[p], n = qs.length || 1, cnt = new Map();
    for (const q of qs) { const t = q.topic || ''; cnt.set(t, (cnt.get(t) || 0) + 1); }
    for (const [t, c] of cnt) { if (!m.has(t)) m.set(t, new Array(k).fill(0)); m.get(t)[p] = c / n; }
  }
  return m;
}
function ewMean(arr, h) { let sw = 0, s = 0; const k = arr.length; for (let i = 0; i < k; i++) { const w = Math.pow(0.5, (k - 1 - i) / h); sw += w; s += w * arr[i]; } return sw ? s / sw : 0; }
function topicMomentum(data, k) {
  const out = new Map();
  for (const [t, arr] of topicShares(data, k)) out.set(t, clamp(Math.log((ewMean(arr, 3) + 0.005) / (mean(arr) + 0.005)), -1, 1));
  return out;
}
const G_MAX = 25;
const newHaz = () => ({ obs: new Float64Array(G_MAX + 2), hit: new Float64Array(G_MAX + 2), n: 0, h: 0 });
function hazAt(hz, g) {
  const p0 = hz.n ? hz.h / hz.n : 0.1; let o = 0, h = 0;
  for (let d = -1; d <= 1; d++) { const gg = g + d; if (gg >= 1 && gg <= G_MAX) { o += hz.obs[gg]; h += hz.hit[gg]; } }
  return (h + 5 * p0) / (o + 5);
}
function clusterFeat(c, k, hh, hz, mom) {
  const idx = []; for (let i = 0; i < k; i++) if (c.pres[i]) idx.push(i);
  const n = idx.length, f = idx[0], last = idx[n - 1], e = k - 1 - f;
  const rAll = (n - 1 + 0.2) / (e + 2);
  let sw = 0, sa = 0;
  for (let i = f + 1; i < k; i++) { const w = Math.pow(0.5, (k - 1 - i) / hh); sw += w; sa += w * c.pres[i]; }
  const pEw = (sa + 0.1) / (sw + 1);
  const g = Math.min(G_MAX, k - last);
  let miss = 1;
  for (let t = 1; t < n; t++) { const G = idx[t] - idx[t - 1]; miss *= 1 - 0.8 * Math.exp(-((g - G) * (g - G)) / 0.72); }
  const bump = n > 1 ? 1 - miss : 0;
  c.idx = idx; c.n = n; c.gap = k - last;
  return { x: [logit(rAll), logit(pEw), logit(hazAt(hz, g)), bump, mom.get(c.topic || '') || 0, Math.log(n), Math.log(1 + e)], rAll, pEw, g };
}

/* ---------- logistic regression (ridge, Newton) ---------- */
function solve(A, b) {
  const n = b.length, M = A.map((r, i) => [...r, b[i]]);
  for (let i = 0; i < n; i++) {
    let p = i; for (let r = i + 1; r < n; r++) if (Math.abs(M[r][i]) > Math.abs(M[p][i])) p = r;
    [M[i], M[p]] = [M[p], M[i]];
    const d = M[i][i] || 1e-9;
    for (let r = i + 1; r < n; r++) { const f = M[r][i] / d; for (let c = i; c <= n; c++) M[r][c] -= f * M[i][c]; }
  }
  const x = new Array(n).fill(0);
  for (let i = n - 1; i >= 0; i--) { let s = M[i][n]; for (let c = i + 1; c < n; c++) s -= M[i][c] * x[c]; x[i] = s / (M[i][i] || 1e-9); }
  return x;
}
function fitLR(rows, ys, lam) {
  const n = rows.length, d = rows[0].length, mu = new Array(d).fill(0), sd = new Array(d).fill(0);
  for (const r of rows) for (let j = 0; j < d; j++) mu[j] += r[j] / n;
  for (const r of rows) for (let j = 0; j < d; j++) sd[j] += (r[j] - mu[j]) * (r[j] - mu[j]) / n;
  for (let j = 0; j < d; j++) sd[j] = Math.sqrt(sd[j]) || 1;
  const Z = rows.map(r => [1].concat(r.map((x, j) => (x - mu[j]) / sd[j])));
  const D = d + 1, w = new Array(D).fill(0);
  w[0] = logit(ys.reduce((s, y) => s + y, 0) / n);
  for (let it = 0; it < 40; it++) {
    const g = new Array(D).fill(0), H = Array.from({ length: D }, () => new Array(D).fill(0));
    for (let i = 0; i < n; i++) {
      const z = Z[i]; let s = 0; for (let j = 0; j < D; j++) s += w[j] * z[j];
      const p = sigmoid(s), r = p * (1 - p) + 1e-9;
      for (let j = 0; j < D; j++) { g[j] += (ys[i] - p) * z[j]; for (let l = 0; l <= j; l++) H[j][l] += r * z[j] * z[l]; }
    }
    for (let j = 1; j < D; j++) { g[j] -= lam * w[j]; H[j][j] += lam; }
    for (let j = 0; j < D; j++) { for (let l = j + 1; l < D; l++) H[j][l] = H[l][j]; H[j][j] += 1e-6; }
    const dl = solve(H, g); let step = 0;
    for (let j = 0; j < D; j++) { const s = clamp(dl[j], -3, 3); w[j] += s; step = Math.max(step, Math.abs(s)); }
    if (step < 1e-5) break;
  }
  return { w, mu, sd };
}
function predictLR(m, x) { let s = m.w[0]; for (let j = 0; j < x.length; j++) s += m.w[j + 1] * (x[j] - m.mu[j]) / m.sd[j]; return sigmoid(s); }
const priorP = f => clamp(0.5 * f.rAll + 0.5 * f.pEw + 0.15 * f.x[3], 0.001, 0.95);
function trainOn(folds) {
  const rows = [], ys = [];
  for (const f of folds) if (f.y) f.feats.forEach((ft, i) => { rows.push(ft.x); ys.push(f.y[i]); });
  const pos = ys.reduce((s, y) => s + y, 0);
  if (rows.length < 60 || pos < 10 || pos > rows.length - 10) return null;
  return fitLR(rows, ys, 2);
}

/* ---------- selection & evaluation ---------- */
function pickTop(items, K, capFn) {
  const sorted = items.slice().sort((a, b) => b.p - a.p || a.i - b.i), cnt = new Map(), out = [];
  for (const it of sorted) {
    const key = it.topic || '', cap = capFn ? capFn(it.topic) : Infinity, c = cnt.get(key) || 0;
    if (c >= cap) continue;
    cnt.set(key, c + 1); out.push(it);
    if (out.length >= K) break;
  }
  return out;
}
function capsFor(data, k, T) {
  const lam = new Map();
  for (const [t, arr] of topicShares(data, k)) lam.set(t, ewMean(arr, 4) * T);
  return t => Math.max(2, Math.ceil(lam.get(t || '') || 0) + 1);
}
function evalFold(data, folds, fk, K) {
  const trained = trainOn(folds.filter(f => f.k < fk.k));
  const T = median(data.sizes.slice(Math.max(0, fk.k - 3), fk.k));
  const cap = capsFor(data, fk.k, T), nC = fk.clusters.length;
  const score = (vals, useCap) => {
    const items = vals.map((p, i) => ({ i, p, topic: fk.clusters[i].topic }));
    const top = pickTop(items, K, useCap ? cap : null), set = new Set(top.map(t => t.i));
    let hits = 0, sp = 0; for (const t of top) { hits += fk.y[t.i]; sp += t.p; }
    let cov = 0; for (const a of fk.assigned) if (a >= 0 && set.has(a)) cov++;
    return { precision: top.length ? hits / K : 0, coverage: fk.nQs ? cov / fk.nQs : 0, meanP: top.length ? sp / top.length : 0, hitRate: top.length ? hits / top.length : 0 };
  };
  const pos = fk.y.reduce((s, y) => s + y, 0), kk = Math.min(K, nC);
  return {
    k: fk.k,
    prior: score(fk.feats.map(priorP), true),
    lr: trained ? score(fk.feats.map(ft => predictLR(trained, ft.x)), true) : null,
    freq: score(fk.feats.map(f => f.rAll), false),
    recency: score(fk.feats.map(f => f.pEw), false),
    random: { precision: nC ? pos * kk / nC / K : 0, coverage: nC && fk.nQs ? (fk.matchedQs / fk.nQs) * kk / nC : 0 },
    novel: fk.nQs ? 1 - fk.matchedQs / fk.nQs : 0,
  };
}
/* The simple frequency-and-recency blend ranks the picks. The learned model replaces it only if it wins on past papers by a clear margin. */
function chooseMethod(prior, lr) { return prior && lr && lr.precision >= prior.precision + LR_MARGIN ? 'learned' : 'blend'; }
/* Scale the shown chances so the top picks' average chance equals how often they really appeared on past papers. Ranking is unchanged. */
function calibrate(chosen) {
  if (!chosen || !(chosen.meanP > 0)) return { factor: SHRINK, tested: false };
  return { factor: clamp(chosen.hitRate / chosen.meanP, 0.25, 1.5), tested: true, predicted: chosen.meanP, realised: chosen.hitRate };
}

/* ---------- topic weightage forecast ---------- */
function topicForecast(data, T) {
  const N = data.N, sh = topicShares(data, N), topics = [...sh.keys()];
  const cands = {
    mean: a => mean(a), ew3: a => ewMean(a, 3), ew6: a => ewMean(a, 6), last: a => a[a.length - 1],
    blend: a => 0.5 * ewMean(a, 4) + 0.5 * mean(a),
    trend: a => {
      const L = Math.min(a.length, 8), y = a.slice(-L), xm = (L - 1) / 2, ym = mean(y); let num = 0, den = 0;
      y.forEach((v, i) => { num += (i - xm) * (v - ym); den += (i - xm) * (i - xm); });
      return Math.max(0, ym + 0.5 * (den ? num / den : 0) * ((L + 1) / 2));
    },
  };
  const avgSize = mean(data.sizes), errs = {};
  const jStart = Math.max(3, N - 10);
  for (const name in cands) {
    let tot = 0, cnt = 0;
    for (let j = jStart; j < N; j++) { let e = 0; for (const t of topics) e += Math.abs(cands[name](sh.get(t).slice(0, j)) - sh.get(t)[j]); tot += e; cnt++; }
    errs[name] = cnt ? tot / cnt * avgSize / 2 : NaN;
  }
  let bestName = 'blend';
  if (N >= 6) bestName = Object.keys(errs).reduce((a, b) => errs[b] < errs[a] ? b : a);
  const raw = topics.map(t => Math.max(0, cands[bestName](sh.get(t)))), tot = raw.reduce((s, x) => s + x, 0) || 1;
  const rows = topics.map((t, i) => {
    const arr = sh.get(t), lam = raw[i] / tot * T, counts = arr.map((s, p) => s * data.sizes[p]);
    const rec = ewMean(arr, 3), all = mean(arr) + 1e-9, ratio = rec / all;
    return { topic: t || null, expected: lam, pAny: 1 - Math.exp(-lam), trend: lam >= 0.6 && ratio > 1.25 ? 'up' : ratio < 0.8 ? 'down' : 'flat', recent: mean(counts.slice(-5)), overall: mean(counts) };
  }).sort((a, b) => b.expected - a.expected);
  return { rows, model: bestName, mae: errs[bestName], maeLast: errs.last, maeMean: errs.mean, errs };
}

/* ---------- explanations ---------- */
function termsLabel(c, surf) {
  const arr = [...c.sum].filter(([t]) => !t.includes('_')).sort((a, b) => b[1] - a[1]).slice(0, 3);
  return arr.map(([t]) => { const m = surf.get(t); if (!m) return t; let b = t, bc = -1; for (const [w, n] of m) if (n > bc) { b = w; bc = n; } return b; }).join(', ');
}
function reasonFor(c, N) {
  const idx = c.idx, n = idx.length, g = N - idx[n - 1];
  const gaps = []; for (let i = 1; i < n; i++) gaps.push(idx[i] - idx[i - 1]);
  const recent3 = idx.filter(i => i >= N - 3).length;
  if (n >= 3) {
    const mg = median(gaps), spread = Math.max(...gaps) - Math.min(...gaps);
    if (spread <= 2 && Math.abs(g - mg) <= 1) { const rmg = Math.round(mg); return { tag: 'due', text: 'Comes back about every ' + rmg + (rmg === 1 ? ' paper' : ' papers') + '; last seen ' + g + (g === 1 ? ' paper ago' : ' papers ago') }; }
  }
  if (recent3 >= 2) return { tag: 'hot', text: 'Asked in ' + recent3 + ' of the last 3 papers' };
  if (n / N >= 0.4) return { tag: 'staple', text: 'Asked in ' + n + ' of ' + N + ' papers' };
  if (n >= 2 && g >= 4) return { tag: 'overdue', text: 'Not seen for ' + g + ' papers' };
  return { tag: 'watch', text: n === 1 ? 'Seen once before' : 'Seen ' + n + ' times' };
}

/* ---------- main ---------- */
async function analyze(records, opts, hooks) {
  opts = opts || {}; hooks = hooks || {};
  const K = opts.K || 40, tau = opts.tau || 0.35, HH = 5, warnings = [];
  const excluded = (opts.excluded || []).map(normKey).filter(Boolean);
  const data = prepare(records, new Set(excluded), warnings);
  const N = data.N;
  if (N < 3) throw new Error('Need at least 3 different years of papers (found ' + N + ').');
  if (N < MIN_PAPERS) warnings.push('Only ' + N + ' papers: too few to test the forecast on past papers, so the chances shown are cautious estimates. 15–20 papers works best.');
  const T = opts.T || Math.max(1, Math.round(median(data.sizesPre.slice(-3))));
  const j0 = 3, folds = [], haz = newHaz();
  for (let k = j0; k <= N; k++) {
    if (hooks.progress) await hooks.progress(k - j0 + 1, N - j0 + 2, k);
    const fold = buildFold(data, k, tau), mom = topicMomentum(data, k);
    fold.feats = fold.clusters.map(c => clusterFeat(c, k, HH, haz, mom));
    if (k < N) {
      labelFold(data, fold);
      fold.feats.forEach((f, i) => { haz.obs[f.g]++; haz.n++; if (fold.y[i]) { haz.hit[f.g]++; haz.h++; } });
    }
    folds.push(fold);
  }
  const evals = [];
  for (let k = Math.max(j0 + 4, N - 8); k < N; k++) { evals.push(evalFold(data, folds, folds.find(f => f.k === k), K)); if (hooks.tick) await hooks.tick(); }
  const agg = key => ({ precision: mean(evals.map(e => e[key].precision)), coverage: mean(evals.map(e => e[key].coverage)), meanP: mean(evals.map(e => e[key].meanP || 0)), hitRate: mean(evals.map(e => e[key].hitRate || 0)) });
  const tested = evals.length >= MIN_TESTED;
  const priorAgg = evals.length ? agg('prior') : null, lrAgg = tested && evals.every(e => e.lr) ? agg('lr') : null;
  const method = tested ? chooseMethod(priorAgg, lrAgg) : 'blend';
  const chosen = method === 'learned' ? lrAgg : priorAgg, cal = calibrate(tested ? chosen : null);
  const useKey = method === 'learned' ? 'lr' : 'prior';
  const backtest = evals.length ? { n: evals.length, from: data.years[evals[0].k], to: data.years[N - 1], method, model: chosen, prior: priorAgg, lr: lrAgg, random: agg('random'), freq: agg('freq'), recency: agg('recency'), novel: mean(evals.map(e => e.novel)), calibration: cal, per: evals.map(e => ({ year: data.years[e.k], precision: (e[useKey] || e.prior).precision, random: e.random.precision })) } : null;
  if (hooks.progress) await hooks.progress(N - j0 + 2, N - j0 + 2, 'final');

  const finalFold = folds.find(f => f.k === N), model = method === 'learned' ? trainOn(folds.filter(f => f.y)) : null;
  const P = finalFold.feats.map(ft => Math.min(MAXP, (model ? predictLR(model, ft.x) : priorP(ft)) * cal.factor));
  const tf = topicForecast(data, T);
  const lam = new Map(tf.rows.map(r => [r.topic || '', r.expected]));
  const cap = t => Math.max(2, Math.ceil(lam.get(t || '') || 0) + 1);
  const items = P.map((p, i) => ({ i, p, topic: finalFold.clusters[i].topic })).filter(it => it.p >= 0.02);
  const top = pickTop(items, K, cap);
  if (top.length < K) warnings.push('Only ' + top.length + ' concepts have at least a 2% chance, so the list is shorter than ' + K + '.');
  const picks = top.map((it, r) => {
    const c = finalFold.clusters[it.i], anchor = c.members[c.members.length - 1], others = [];
    for (let m = c.members.length - 2; m >= 0 && others.length < 2; m--) if (c.members[m].p !== anchor.p && !others.some(o => o.year === c.members[m].year)) others.push({ year: c.members[m].year, text: c.members[m].text });
    return { rank: r + 1, topic: c.topic, label: c.label || termsLabel(c, data.surf), p: it.p, n: c.n, years: c.idx.map(i => data.years[i]), reason: reasonFor(c, N), anchor: { year: anchor.year, text: anchor.text }, others, refs: c.members.map(m => m.ref) };
  });
  const totalQ = data.qs.length;
  return {
    method, calibration: cal,
    meta: { years: data.years, N, nQuestions: totalQ, T, K, tau, targetYear: data.years[N - 1] + 1, topics: tf.rows.filter(r => r.topic).length, concepts: finalFold.clusters.length },
    backtest, topics: tf.rows, topicModel: { name: tf.model, mae: tf.mae, maeLast: tf.maeLast, maeMean: tf.maeMean },
    picks, expectedHits: picks.reduce((s, p) => s + p.p, 0), warnings,
  };
}

const EF = { parseDelimited, yearFromHeader, compileSyllabus, tagWithSyllabus, PHYSICS_SYLLABUS, featureTokens, analyze, chooseMethod, calibrate, kwRegex, fitLR, predictLR, normKey, MAXP, LR_MARGIN };
if (typeof module !== 'undefined' && module.exports) module.exports = EF; else root.EF = EF;
})(typeof window !== 'undefined' ? window : globalThis);
