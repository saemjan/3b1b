/* COS for exams: the model that joins the Forecaster and the Test machine. Pure JS, no DOM.
   Core (fixed):      Constitution (rules), Soul (fingerprint), Math Brain (gen.js), the forecast engine (ef.js)
   Shell (adaptive):  Memory (papers, attempts), Heart (learning), Internet Teacher (outside opinion)
   Rule: it may change what it knows, remembers and can do. It must not silently change what it is. */
(function (root) {
'use strict';
const EF = root.EF || require('./ef.js');
const CBT = root.CBT || require('./cbt.js');
const GEN = root.GEN || require('./gen.js');
const VERSION = '1.0.0';
const MAXP = 0.95, CAP_ATTEMPTS = 60, KEEP_DETAIL = 10, MAX_FACULTY = 5, MAX_NUDGE = 0.2;
const normKey = EF.normKey;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const uniq = a => [...new Set(a)];

/* ================= BODY: reading papers (text and CSV -> items) ================= */
const KEY_HEAD = /^\s*(?:answer\s*key|answers?|key)\s*:?\s*$/i;
const OPT_LINE = /^\(?\s*([A-Da-d]|[1-4])\s*[\).:]\s*(\S.*)$/;
const ANS_LINE = /^(?:correct\s+)?ans(?:wer)?\s*[:.\-]\s*(\S.*)$/i;
const EXP_LINE = /^(?:explanation|solution|sol|hint)\s*[:.\-]\s*(.*)$/i;
const Q_RES = [
  ['q', /^\s*q(?:uestion)?\s*\.?\s*(\d{1,3})\s*[\)\].:\-–]?\s*(.*)$/i],
  ['dot', /^\s*(\d{1,3})\s*\.\s+(\S.*)$/],
  ['rparen', /^\s*(\d{1,3})\s*\)\s*(\S.*)$/],
  ['paren', /^\s*\(\s*(\d{1,3})\s*\)\s*(\S.*)$/],
  ['brack', /^\s*\[\s*(\d{1,3})\s*\]\s*(\S.*)$/],
];
const keyOf = c => 'ABCD'.indexOf(String(c).toUpperCase()) >= 0 ? String(c).toUpperCase() : 'ABCD'['1234'.indexOf(c)];

/* "B", "(b)", "3", "D. 45 m" or the text of an option  ->  'A'..'D' (or null) */
function normAnswer(val, options) {
  if (val == null) return null;
  const v = String(val).trim();
  const m = v.match(/^\(?\s*([A-Da-d1-4])(?![A-Za-z0-9])/);
  if (m) { const k = keyOf(m[1]); if (!options || options.some(o => o.key === k)) return k; }
  if (options) { const lv = v.toLowerCase(); const hit = options.find(o => o.text.toLowerCase() === lv); if (hit) return hit.key; }
  return null;
}
/* the lines of one question -> stem, options, answer, explanation */
function splitMCQ(lines) {
  const stem = [], opts = [], expl = []; let ansRaw = null, mode = 'stem', m;
  for (const raw of lines) {
    const line = String(raw).trim(); if (!line) continue;
    if ((m = line.match(EXP_LINE))) { mode = 'expl'; if (m[1]) expl.push(m[1].trim()); continue; }
    if ((m = line.match(ANS_LINE))) { ansRaw = m[1]; mode = 'ans'; continue; }
    if (mode !== 'expl' && (m = line.match(OPT_LINE))) {
      const k = keyOf(m[1]);
      if (k === 'ABCD'[opts.length]) { opts.push({ key: k, text: m[2].trim() }); mode = 'opt'; continue; }
    }
    if (mode === 'expl') expl.push(line);
    else if (mode === 'opt' && opts.length) opts[opts.length - 1].text += ' ' + line;
    else if (mode === 'ans') continue;
    else stem.push(line);
  }
  const mcq = opts.length >= 2;
  return {
    stem: (mcq ? stem : lines.map(l => String(l).trim()).filter(Boolean)).join(' '),
    options: mcq ? opts : [], answer: mcq ? normAnswer(ansRaw, opts) : null,
    explanation: expl.join(' ') || null, mcq,
  };
}
/* "1. B  2. C  3. (4)" -> Map(number -> 'A'..'D') */
function parseKeyMap(block) {
  const map = new Map(), re = /(\d{1,3})\s*[.):\-–]?\s*\(?\s*([A-Da-d]|[1-4])(?![A-Za-z0-9])\s*\)?/g; let m;
  while ((m = re.exec(block))) { const n = parseInt(m[1], 10); if (!map.has(n)) map.set(n, keyOf(m[2])); }
  return map;
}
function makeRecord(year, text, extra) {
  text = String(text == null ? '' : text).replace(/\s+/g, ' ').trim().slice(0, 1500);
  if (!year || text.length < 8) return null;
  const rec = { year, text, topic: null, concept: null };
  if (extra) {
    if (extra.topic) rec.topic = String(extra.topic).trim() || null;
    if (extra.concept) rec.concept = String(extra.concept).trim() || null;
    if (extra.options && extra.options.length >= 2) { rec.options = extra.options; rec.answer = extra.answer || null; }
    if (extra.explanation) rec.explanation = extra.explanation;
    if (extra.num) rec.num = extra.num;
  }
  return rec;
}
const yearOf = v => { const m = String(v == null ? '' : v).match(/\b(19[89]\d|20[0-4]\d)\b/); return m ? parseInt(m[1], 10) : null; };

/* a paper (or several, with year headings) as plain text -> items. Understands options, "Answer: B", "Explanation:" and a trailing answer key. */
function parsePapers(text, defaultYear) {
  const lines = String(text || '').replace(/\r/g, '').split('\n');
  const records = [], counts = new Map();
  let year = defaultYear || null, last = 0, style = null, cur = null, blank = true, section = false, noYear = 0;
  let inKey = false, keyBuf = [], keyYear = null;
  const flush = () => {
    if (!cur) return;
    const mc = splitMCQ(cur.lines);
    const rec = makeRecord(cur.year, mc.stem, mc.mcq ? { options: mc.options, answer: mc.answer, explanation: mc.explanation, num: cur.num } : { num: cur.num });
    if (rec) { records.push(rec); counts.set(rec.year, (counts.get(rec.year) || 0) + 1); }
    else if (!cur.year && mc.stem.length >= 8) noYear++;
    cur = null;
  };
  const endKey = () => {
    if (!inKey) return;
    const km = parseKeyMap(keyBuf.join('\n'));
    for (const r of records) if (r.year === keyYear && r.num && r.options && !r.answer) { const a = km.get(r.num); if (a && r.options.some(o => o.key === a)) r.answer = a; }
    inKey = false; keyBuf = [];
  };
  for (const line of lines) {
    if (!line.trim()) { blank = true; continue; }
    const hy = EF.yearFromHeader(line);
    if (inKey && !hy) { keyBuf.push(line); blank = false; continue; }
    if (hy && (blank || !cur)) { endKey(); flush(); year = hy; last = 0; style = null; section = false; blank = false; continue; }
    if (KEY_HEAD.test(line)) { flush(); endKey(); inKey = true; keyYear = year; keyBuf = []; blank = false; continue; }
    if (/^\s*(section|part)\b/i.test(line) && line.length < 60) { flush(); section = true; blank = false; continue; }
    let hit = null;
    for (const [st, re] of Q_RES) {
      const m = line.match(re); if (!m) continue;
      const n = parseInt(m[1], 10); let ok = false;
      if (st === 'q') ok = true;
      else if (style === null) ok = n <= 3;
      else if (st === style) ok = n === last + 1 || (n === 1 && (blank || section) && last >= 3);
      if (ok) { hit = { st, n, rest: m[2] }; break; }
    }
    if (hit) {
      flush();
      if (hit.st !== 'q' || style === null) style = style === null ? hit.st : style;
      last = hit.n; section = false;
      cur = { year, lines: [hit.rest], num: hit.n };
    } else if (cur) cur.lines.push(line.trim());
    blank = false;
  }
  flush(); endKey();
  return { records, counts, noYear };
}

const CSV_ALIAS = {
  year: ['year', 'yr', 'exam year', 'paper year', 'session'],
  text: ['question', 'questions', 'question text', 'text', 'q', 'ques', 'problem', 'statement'],
  topic: ['topic', 'chapter', 'chapter name', 'unit', 'topic name'],
  concept: ['concept', 'subtopic', 'sub topic', 'subconcept'],
  a: ['a', 'option a', 'optiona', 'option 1'], b: ['b', 'option b', 'optionb', 'option 2'],
  c: ['c', 'option c', 'optionc', 'option 3'], d: ['d', 'option d', 'optiond', 'option 4'],
  answer: ['answer', 'correct', 'correct answer', 'ans', 'key'],
  explanation: ['explanation', 'solution'],
};
const hnorm = s => String(s == null ? '' : s).toLowerCase().replace(/[_\-]+/g, ' ').replace(/\s+/g, ' ').trim();
/* CSV rows (header first) -> items. Needs year and question; options, answer and explanation are optional. */
function recordsFromRows(rows) {
  if (!rows.length) return { records: [], error: 'The file is empty.' };
  const cols = {};
  rows[0].forEach((h, i) => { const n = hnorm(h); for (const k in CSV_ALIAS) if (cols[k] === undefined && CSV_ALIAS[k].includes(n)) cols[k] = i; });
  if (cols.year === undefined || cols.text === undefined) return { records: [], error: 'Add a header row with "year" and "question" columns (optional: topic, concept, A, B, C, D, answer, explanation).' };
  const get = (r, k) => cols[k] !== undefined && r[cols[k]] != null ? String(r[cols[k]]).trim() : '';
  const records = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i], options = [];
    ['a', 'b', 'c', 'd'].forEach(k => { const t = get(r, k); if (t) options.push({ key: k.toUpperCase(), text: t }); });
    const ok = options.length >= 2;
    const rec = makeRecord(yearOf(get(r, 'year')), get(r, 'text'), { topic: get(r, 'topic'), concept: get(r, 'concept'), options: ok ? options : null, answer: ok ? normAnswer(get(r, 'answer'), options) : null, explanation: get(r, 'explanation') });
    if (rec) records.push(rec);
  }
  return { records, error: records.length ? undefined : 'No rows with a year and a question were found.' };
}

let _syl = null;
function syllabus(custom) {
  if (custom && custom.trim()) { try { return EF.compileSyllabus(custom); } catch (e) { /* fall through */ } }
  return _syl || (_syl = EF.compileSyllabus(EF.PHYSICS_SYLLABUS));
}
/* give every item without a topic the best-matching syllabus topic */
function autoTag(records, custom) {
  const syl = syllabus(custom);
  return records.map(r => r.topic ? r : Object.assign({}, r, { topic: EF.tagWithSyllabus(r.text, syl) || null }));
}
const SCRIPTS = [[/[ऀ-ॿ]/, 'hi'], [/[ঀ-৿]/, 'bn'], [/[਀-੿]/, 'pa'], [/[઀-૿]/, 'gu'], [/[଀-୿]/, 'or'], [/[஀-௿]/, 'ta'], [/[ఀ-౿]/, 'te'], [/[ಀ-೿]/, 'kn'], [/[ഀ-ൿ]/, 'ml']];
function scriptLang(s) { s = String(s || ''); for (const [re, l] of SCRIPTS) if (re.test(s)) return l; return 'en'; }

/* ================= MEMORY: the bank of papers ================= */
const isTestable = it => !!(it && it.options && it.options.length >= 2 && it.answer && it.options.some(o => o.key === it.answer));
function bankStats(items) {
  const years = uniq(items.map(i => i.year)).sort((a, b) => a - b);
  return { n: items.length, years: years.length, y0: years[0], y1: years[years.length - 1], ready: items.filter(i => i.gen || isTestable(i)).length, topics: uniq(items.map(i => i.topic).filter(Boolean)).length };
}
function bankRows(items) {
  const rows = [['year', 'question', 'topic', 'concept', 'A', 'B', 'C', 'D', 'answer', 'explanation']];
  for (const it of items) { const o = {}; (it.options || []).forEach(x => { o[x.key] = x.text; }); rows.push([it.year, it.text, it.topic || '', it.concept || '', o.A || '', o.B || '', o.C || '', o.D || '', it.answer || '', it.explanation || '']); }
  return rows;
}
function paperRows(qs) {
  const rows = [['question', 'A', 'B', 'C', 'D', 'answer', 'section', 'explanation', 'marks', 'topic', 'chance_pct', 'source']];
  for (const q of qs) { const o = {}; q.options.forEach(x => { o[x.key] = x.text; }); rows.push([q.text, o.A || '', o.B || '', o.C || '', o.D || '', q.answerKey, q.section || '', q.explanation || '', q.marks ? q.marks.correct + '/' + q.marks.wrong : '', q.topic || '', q.p != null ? Math.round(q.p * 100) : '', q.src === 'math' ? 'Math Brain' : 'Paper']); }
  return rows;
}

/* ================= INTERNET TEACHER: outside opinion, treated as unverified ================= */
const WEIGHT = { high: 0.2, medium: 0.1, mid: 0.1, low: 0.05 };
/* one note per line:  Faculty | Topic or phrase | high / medium / low | optional link */
function parseNotes(text) {
  const out = [];
  for (const raw of String(text || '').split('\n')) {
    const line = raw.trim(); if (!line || line[0] === '#') continue;
    const p = line.split('|').map(s => s.trim());
    if (p.length < 3 || !p[0] || !p[1]) continue;
    const w = WEIGHT[p[2].toLowerCase()]; if (w == null) continue;
    out.push({ who: p[0], what: p[1], w, link: p[3] || '' });
  }
  return out;
}
/* A note can lift a rank by at most 20%, from at most 5 faculty. It can reorder the picks, never add one. */
function nudge(picks, text) {
  const notes = parseNotes(text), keep = new Set();
  for (const n of notes) { const k = normKey(n.who); if (keep.size < MAX_FACULTY) keep.add(k); }
  const used = notes.filter(n => keep.has(normKey(n.who)));
  const out = picks.map(p => {
    const hay = normKey((p.topic || '') + ' ' + (p.label || ''));
    const hits = used.filter(n => { const w = normKey(n.what); return w && hay.includes(w); });
    const base = Object.assign({}, p, { p: Math.min(p.p, MAXP) });
    if (!hits.length) return base;
    const who = uniq(hits.map(h => h.who)), delta = Math.min(MAX_NUDGE, Math.max.apply(null, hits.map(h => h.w)) + 0.03 * (uniq(hits.map(h => normKey(h.who))).length - 1));
    return Object.assign(base, { p: Math.min(MAXP, p.p * (1 + delta)), nudge: { delta, who } });
  });
  out.sort((a, b) => b.p - a.p || a.rank - b.rank).forEach((p, i) => { p.rank = i + 1; });
  return { picks: out, used: { faculty: keep.size, notes: used.length, ignored: notes.length - used.length, nudged: out.filter(p => p.nudge).length } };
}

/* ================= BRAIN: from forecast to paper ================= */
const fromItem = it => ({ text: it.text, options: it.options.map(o => ({ key: o.key, text: o.text })), answerKey: it.answer, explanation: it.explanation || null, section: null, marks: null, topic: it.topic || null, src: 'paper', year: it.year });
function fresh(id, R) { const q = GEN.make(id, R); return { text: q.text, options: q.options, answerKey: q.answer, explanation: q.explanation, section: null, marks: null, topic: q.topic, src: 'math', year: null }; }
function isReady(pick, items) { return (pick.refs || []).some(r => items[r] && (items[r].gen || isTestable(items[r]))); }

/* the most probable questions as a paper: the top picks, one question each.
   A concept the Math Brain knows gets fresh numbers and an exact solution; otherwise the latest paper question is used as it stands. */
function assemble(fc, items, o) {
  o = o || {};
  const n = o.n || 20, R = GEN.rng(GEN.hash32('paper|' + (o.receipt || '') + '|' + (o.seed || 1)));
  const questions = [], skipped = [];
  for (const pk of fc.picks) {
    if (questions.length >= n) break;
    const members = (pk.refs || []).map(r => items[r]).filter(Boolean);
    const g = members.find(m => m.gen);
    let q = null;
    if (g) q = fresh(g.gen, R);
    else { const t = members.filter(isTestable).sort((a, b) => b.year - a.year)[0]; if (t) q = fromItem(t); }
    if (!q) { skipped.push({ rank: pk.rank, topic: pk.topic, label: pk.label }); continue; }
    q.p = pk.p; q.rank = pk.rank; q.years = pk.years; q.label = pk.label; q.nudge = pk.nudge || null;
    questions.push(q);
  }
  return { questions, skipped, seed: o.seed || 1 };
}
/* practice on one topic: real paper questions first, topped up with fresh Math Brain questions */
function drill(items, topic, o) {
  o = o || {};
  const n = o.n || 10, R = GEN.rng(GEN.hash32('drill|' + topic + '|' + (o.seed || 1)));
  const real = GEN.shuffle(items.filter(i => i.topic === topic && isTestable(i) && !i.gen), R).slice(0, n).map(fromItem);
  const ids = GEN.TPL.filter(t => t.topic === topic).map(t => t.id), qs = real.slice();
  for (let i = 0; qs.length < n && ids.length; i++) qs.push(fresh(ids[i % ids.length], R));
  return { questions: qs, topic };
}
/* where the next hour pays most: expected questions x marks x what you do not yet know */
function plan(fc, mastery, marks) {
  const mc = marks || 4;
  return (fc ? fc.topics : []).filter(t => t.topic).map(t => {
    const m = mastery && mastery[t.topic], mm = m ? m.m : 0.5;
    return { topic: t.topic, expected: t.expected, trend: t.trend, mastery: mm, tested: !!(m && m.n), n: m ? m.n : 0, stake: t.expected * mc * (1 - mm) };
  }).sort((a, b) => b.stake - a.stake);
}

/* ================= HEART: learn, forget, preserve ================= */
function learn(mastery, rows) {
  const M = JSON.parse(JSON.stringify(mastery || {}));
  for (const r of rows) {
    if (!r.topic || r.outcome === 'unattempted') continue;
    const s = M[r.topic] || (M[r.topic] = { m: 0.5, n: 0 });
    const a = Math.max(0.2, 1 / (s.n + 2));
    s.m = clamp(s.m + a * ((r.outcome === 'correct' ? 1 : 0) - s.m), 0, 1); s.n++;
  }
  return M;
}
/* bounded memory: keep a line per attempt for the last 60, full detail for the last 10; mastery already holds what was learned */
function forget(attempts) {
  const out = attempts.slice(-CAP_ATTEMPTS), cut = out.length - KEEP_DETAIL;
  return out.map((a, i) => { if (i < cut && a.rows) { const b = Object.assign({}, a); delete b.rows; return b; } return a; });
}
function grade(qs, selected) {
  const s = CBT.scoreTest(qs, selected), by = new Map();
  s.rows.forEach(r => {
    const t = qs[r.i].topic; if (!t) return;
    const b = by.get(t) || { topic: t, n: 0, correct: 0, incorrect: 0, unattempted: 0 }; b.n++; b[r.outcome]++; by.set(t, b);
  });
  s.byTopic = [...by.values()].sort((a, b) => (a.correct / a.n) - (b.correct / b.n) || b.n - a.n);
  return s;
}
function attemptRecord(run, score, now) {
  const spent = Object.values(run.spent || {}).reduce((a, b) => a + b, 0);
  return {
    id: now.toString(36), t: now, title: run.title, src: run.src, h: run.h, n: run.qs.length,
    pct: score.max ? Math.max(0, score.total) / score.max * 100 : 0, total: score.total, max: score.max,
    c: score.correct, w: score.incorrect, u: score.unattempted, secs: Math.round(spent),
    rows: score.rows.map(r => [run.qs[r.i].topic || '', r.outcome === 'correct' ? 1 : r.outcome === 'incorrect' ? 0 : -1, Math.round(run.spent[r.i] || 0)]),
  };
}

/* ================= CONSTITUTION and SOUL ================= */
const CONSTITUTION = Object.freeze([
  { id: 'chance', title: 'Chances, not promises', text: 'Every pick shows a chance below 95% and the years it came from. Chances are scaled to match how often top picks really appeared on past papers.' },
  { id: 'tested', title: 'Tested before trusted', text: 'A forecast comes with a test on past papers it never saw. If it does no better than a plain frequency count, it says so.' },
  { id: 'source', title: 'Solutions say where they came from', text: 'Each solution is labelled: computed by the Math Brain, or taken from your paper.' },
  { id: 'opinion', title: 'Opinion nudges, never decides', text: 'Faculty notes can lift a rank by at most 20%, from at most 5 faculty, and cannot add a question the papers do not support.' },
  { id: 'private', title: 'Your data stays here', text: 'Papers, answers and scores are never sent anywhere. Only fonts and file readers are downloaded.' },
  { id: 'bounded', title: 'Memory has a limit', text: 'Old attempts are summarised, not hoarded: a line each for the last 60, full detail for the last 10.' },
].map(Object.freeze));

/* does the forecast beat a plain frequency count on papers it did not see? */
function verdict(fc) {
  const b = fc && fc.backtest;
  if (!b || b.n < 2) return { status: 'info', text: 'Too few papers to test the forecast on past years (it needs about 8).' };
  const d = b.model.precision - b.freq.precision, r = b.model.precision - b.random.precision, pts = x => Math.round(x * 100);
  const pair = pts(b.model.precision) + '% vs ' + pts(b.freq.precision) + '%';
  if (r <= 0.02) return { status: 'warn', text: 'On ' + b.n + ' past papers it did no better than chance. Treat the ranks as rough.' };
  if (d >= 0.02) return { status: 'pass', text: 'On ' + b.n + ' past papers it beat a plain frequency count (' + pair + ').' };
  if (d <= -0.02) return { status: 'warn', text: 'On ' + b.n + ' past papers a plain frequency count did better (' + pts(b.freq.precision) + '% vs ' + pts(b.model.precision) + '%). Treat the ranks as rough.' };
  return { status: 'info', text: 'On ' + b.n + ' past papers it matched a plain frequency count (' + pair + ').' };
}
/* check the live state against the rules; nothing is shown that fails silently */
function audit(c) {
  const picks = c.fc ? c.fc.picks : [], v = verdict(c.fc), res = {};
  const cal = c.fc && c.fc.calibration, calNote = cal ? (cal.tested ? ' Scaled to past papers (\u00d7' + cal.factor.toFixed(2) + ').' : ' Too few papers to test, so shown cautiously.') : '';
  res.chance = !picks.length ? ['info', 'No forecast yet.'] : picks.every(p => p.p <= MAXP && p.years && p.years.length) ? ['pass', picks.length + ' picks, the highest at ' + Math.round(Math.max.apply(null, picks.map(p => p.p)) * 100) + '%.' + calNote] : ['warn', 'Some picks lack a source year or exceed 95%.'];
  res.tested = [v.status, v.text];
  const qs = c.paper ? c.paper.questions : [];
  res.source = !qs.length ? ['info', 'No paper built yet.'] : qs.every(q => q.src === 'math' || q.src === 'paper') ? ['pass', qs.filter(q => q.src === 'math').length + ' computed, ' + qs.filter(q => q.src === 'paper').length + ' from papers.'] : ['warn', 'Some solutions have no source.'];
  const u = c.nudge || { faculty: 0, notes: 0, nudged: 0, ignored: 0 };
  const over = picks.some(p => p.nudge && p.nudge.delta > MAX_NUDGE + 1e-9);
  res.opinion = over || u.faculty > MAX_FACULTY ? ['warn', 'An opinion exceeded its limit.'] : u.notes ? ['pass', u.notes + ' notes from ' + u.faculty + ' faculty, ' + u.nudged + ' ranks nudged' + (u.ignored ? ', ' + u.ignored + ' ignored over the limit.' : '.')] : ['info', 'No faculty notes added.'];
  res.private = ['pass', 'Nothing you enter leaves this device.'];
  const att = c.attempts || [];
  res.bounded = att.length > CAP_ATTEMPTS ? ['warn', att.length + ' attempts held; the limit is ' + CAP_ATTEMPTS + '.'] : ['pass', att.length + ' of ' + CAP_ATTEMPTS + ' attempts held.'];
  return CONSTITUTION.map(r => ({ id: r.id, title: r.title, text: r.text, status: res[r.id][0], note: res[r.id][1] }));
}

/* invariants checked at start-up: every solver against its hand-worked answer, plus marking, reading papers and repeatability.
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
    const r = parsePapers('2020\n1. Find the value of x in the equation\nA) 1\nB) 2\nC) 3\nD) 4\nAnswer: B').records;
    check('Reading a paper: year, options, answer', r.length === 1 && r[0].year === 2020 && r[0].options.length === 4 && r[0].answer === 'B');
  } catch (e) { check('Reading a paper: year, options, answer', false); }
  return { ok: fails.length === 0, passed: total - fails.length, total, failures: fails };
}

async function sha256(str) {
  const subtle = (root.crypto && root.crypto.subtle) || (typeof require === 'function' ? require('crypto').webcrypto.subtle : null);
  if (subtle) { const buf = await subtle.digest('SHA-256', new TextEncoder().encode(str)); return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join(''); }
  let h = 5381; for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
  return ('00000000' + (h >>> 0).toString(16)).slice(-8).repeat(8);
}
const short = h => h.slice(0, 4) + '-' + h.slice(4, 8);
/* the fingerprint of what the engine is: version, rules, every solver, and the code that forecasts, assembles and learns */
async function coreHash() {
  const parts = [VERSION, JSON.stringify(CONSTITUTION), GEN.TPL.map(t => [t.id, t.topic, t.q, t.a, t.X || '', t.e || ''].join(':')).join('|'), JSON.stringify(GEN.VECTORS), selfTest.toString(), EF.analyze.toString(), EF.chooseMethod.toString(), EF.calibrate.toString(), assemble.toString(), drill.toString(), nudge.toString(), learn.toString(), grade.toString()];
  return short(await sha256(parts.join('␞')));
}
/* the receipt of one forecast: same papers + same engine + same settings = same receipt */
async function receipt(core, items, K, notes) {
  const sig = items.map(i => i.year + '|' + i.text + '|' + (i.topic || '')).join('\n');
  return short(await sha256([core, sig, K, normKey(notes || '')].join('␟')));
}

const COS = {
  VERSION, MAXP, MAX_FACULTY, MAX_NUDGE, CAP_ATTEMPTS, KEEP_DETAIL, CONSTITUTION,
  parsePapers, recordsFromRows, splitMCQ, normAnswer, parseKeyMap, autoTag, syllabus, scriptLang,
  isTestable, isReady, bankStats, bankRows, paperRows,
  parseNotes, nudge, assemble, drill, plan, learn, forget, grade, attemptRecord,
  verdict, audit, selfTest, coreHash, receipt, sha256,
};
if (typeof module !== 'undefined' && module.exports) module.exports = COS; else root.COS = COS;
})(typeof window !== 'undefined' ? window : globalThis);
