/* CBT engine: MCQ parsing, scoring, demo bank. Pure JS, no DOM. */
(function (root) {
'use strict';

function clean(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }

/* ---------- parsing the plain-text authoring format ---------- */
function newCur() { return { num: null, qLines: [], options: [], answer: null, section: null, marksRaw: null, explLines: [] }; }

function parseAnswerKey(block) {
  const map = new Map();
  const re = /(\d{1,3})\s*[.):\-]?\s*([A-Da-d])\b/g;
  let m;
  while ((m = re.exec(block))) { const n = parseInt(m[1], 10); if (!map.has(n)) map.set(n, m[2].toUpperCase()); }
  return map;
}

function parseMCQText(text) {
  text = String(text || '');
  const lines0 = text.replace(/\r/g, '').split('\n');
  const keyHeadingRe = /^\s*(answer\s*key|answers?|key)\s*:?\s*$/i;
  let bodyLines = lines0, keyMap = new Map();
  for (let i = 0; i < lines0.length; i++) {
    if (keyHeadingRe.test(lines0[i])) { bodyLines = lines0.slice(0, i); keyMap = parseAnswerKey(lines0.slice(i + 1).join('\n')); break; }
  }

  const out = []; let cur = null, mode = 'q', lastNum = 0;
  const qStart = l => l.match(/^q?\.?\s*(\d{1,3})\s*[.):]\s*(\S.*)$/i);
  const isOption = l => l.match(/^\(?([A-Da-d])\)?[.):]\s*(.+)$/);
  const isAnswer = l => l.match(/^ans(?:wer)?\s*[:\-]\s*(.+)$/i);
  const isSection = l => l.match(/^section\s*[:\-]\s*(.+)$/i);
  const isMarks = l => l.match(/^marks?\s*[:\-]\s*(.+)$/i);
  const isExpl = l => l.match(/^explanation\s*[:\-]\s*(.+)$/i);
  const flush = () => { if (cur) { const q = finalize(cur, keyMap); out.push(q); } cur = null; mode = 'q'; };
  for (const raw of bodyLines) {
    const line = raw.trim();
    if (!line) continue;
    if (/^-{3,}$/.test(line)) { flush(); continue; }
    let m;
    if ((m = qStart(line))) {
      const n = parseInt(m[1], 10);
      if (n === lastNum + 1 || (lastNum === 0 && n <= 3)) { flush(); cur = newCur(); cur.num = n; lastNum = n; cur.qLines.push(m[2]); mode = 'q'; continue; }
    }
    if ((m = isOption(line))) { if (!cur) cur = newCur(); cur.options.push({ key: m[1].toUpperCase(), text: clean(m[2]) }); mode = 'q'; continue; }
    if ((m = isAnswer(line))) { if (!cur) cur = newCur(); cur.answer = clean(m[1]); continue; }
    if ((m = isSection(line))) { if (!cur) cur = newCur(); cur.section = clean(m[1]); continue; }
    if ((m = isMarks(line))) { if (!cur) cur = newCur(); cur.marksRaw = clean(m[1]); continue; }
    if ((m = isExpl(line))) { if (!cur) cur = newCur(); mode = 'e'; cur.explLines.push(clean(m[1])); continue; }
    if (cur && (cur.answer || (cur.num && keyMap.has(cur.num))) && cur.options.length >= 2 && mode === 'q') flush();
    if (!cur) cur = newCur();
    if (mode === 'e') cur.explLines.push(line); else cur.qLines.push(line.replace(/^q\.?\s*\d*\s*[.):]?\s*/i, ''));
  }
  flush();
  return out;
}

function parseMarks(raw) {
  if (!raw) return null;
  const m = raw.match(/([+-]?\d+(?:\.\d+)?)\s*[\/,]\s*(-?\d+(?:\.\d+)?)/);
  if (!m) return null;
  return { correct: parseFloat(m[1]), wrong: -Math.abs(parseFloat(m[2])) };
}

function finalize(cur, keyMap) {
  const text = clean(cur.qLines.join(' '));
  const opts = cur.options.filter(o => o.text).sort((a, b) => a.key.localeCompare(b.key));
  const explanation = clean(cur.explLines.join(' '));
  const marks = parseMarks(cur.marksRaw);
  const fromKey = !cur.answer && keyMap && cur.num != null && keyMap.has(cur.num);
  const rawAnswer = cur.answer || (fromKey ? keyMap.get(cur.num) : null);
  let answerKey = null, error = null;
  if (!text) error = 'No question text';
  else if (opts.length < 2) error = 'Fewer than 2 options';
  else if (!rawAnswer) error = 'No answer given (not inline, and none found in an answer key section)';
  else {
    const a = String(rawAnswer).trim();
    if (/^[A-Da-d]$/.test(a)) answerKey = a.toUpperCase();
    else { const hit = opts.find(o => o.text.toLowerCase() === a.toLowerCase()); if (hit) answerKey = hit.key; }
    if (!answerKey) error = 'Answer "' + rawAnswer + '" doesn\u2019t match a letter or option text';
    else if (!opts.some(o => o.key === answerKey)) error = 'Answer ' + answerKey + ' has no matching option';
  }
  return { text, options: opts, answerKey, section: cur.section || null, marks, explanation: explanation || null, error, num: cur.num || null, fromAnswerKey: !!fromKey };
}

/* ---------- CSV ingestion (reuses a small self-contained parser) ---------- */
function parseDelimited(text) {
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  const first = text.split(/\r?\n/, 1)[0] || '';
  const counts = { ',': 0, ';': 0, '\t': 0 };
  let inQ0 = false;
  for (const ch of first) { if (ch === '"') inQ0 = !inQ0; else if (!inQ0 && ch in counts) counts[ch]++; }
  const d = (Object.entries(counts).sort((a, b) => b[1] - a[1])[0] || [','])[0] || ',';
  const rows = []; let row = [], field = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) { if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false; } else field += c; }
    else if (c === '"') inQ = true;
    else if (c === d) { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (c !== '\r') field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows.filter(r => r.some(x => x.trim() !== ''));
}
const CSV_ALIAS = {
  text: ['question', 'text', 'q'], a: ['a', 'optiona', 'option a'], b: ['b', 'optionb', 'option b'],
  c: ['c', 'optionc', 'option c'], d: ['d', 'optiond', 'option d'], answer: ['answer', 'correct', 'correctanswer'],
  section: ['section', 'subject'], explanation: ['explanation', 'solution'], marks: ['marks', 'marking'],
};
function hnorm(s) { return String(s == null ? '' : s).toLowerCase().replace(/[_\-]+/g, ' ').replace(/\s+/g, ' ').trim(); }
function parseMCQCsv(text) {
  const rows = parseDelimited(text);
  if (!rows.length) return { questions: [], error: 'The file is empty.' };
  const header = rows[0].map(hnorm), cols = {};
  header.forEach((h, i) => { for (const key in CSV_ALIAS) if (cols[key] === undefined && CSV_ALIAS[key].includes(h)) cols[key] = i; });
  if (cols.text === undefined || cols.a === undefined || cols.answer === undefined) return { questions: [], error: 'Add columns for question, option A-D, and answer.' };
  const out = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i], get = k => (cols[k] !== undefined ? clean(r[cols[k]]) : '');
    const text = get('text'); if (!text) continue;
    const options = [];
    ['a', 'b', 'c', 'd'].forEach(k => { const t = get(k); if (t) options.push({ key: k.toUpperCase(), text: t }); });
    const cur = { qLines: [text], options, answer: get('answer'), section: get('section') || null, marksRaw: get('marks') || null, explLines: get('explanation') ? [get('explanation')] : [] };
    out.push(finalize(cur));
  }
  return { questions: out };
}

/* ---------- scoring ---------- */
function scoreTest(questions, selected) {
  let total = 0, max = 0, correct = 0, incorrect = 0, unattempted = 0;
  const bySection = new Map();
  const rows = questions.map((q, i) => {
    const m = q.marks || { correct: 4, wrong: -1 };
    max += m.correct;
    const sel = selected[i] || null;
    let outcome = 'unattempted', delta = 0;
    if (sel) {
      if (sel === q.answerKey) { outcome = 'correct'; delta = m.correct; correct++; }
      else { outcome = 'incorrect'; delta = m.wrong; incorrect++; }
    } else unattempted++;
    total += delta;
    const sec = q.section || 'General';
    if (!bySection.has(sec)) bySection.set(sec, { correct: 0, incorrect: 0, unattempted: 0, marks: 0, max: 0 });
    const s = bySection.get(sec); s.marks += delta; s.max += m.correct; s[outcome]++;
    return { i, outcome, delta, selected: sel, marks: m };
  });
  return { total, max, correct, incorrect, unattempted, rows, bySection: [...bySection.entries()].map(([name, v]) => Object.assign({ name }, v)) };
}

function fmtClock(sec) {
  sec = Math.max(0, Math.round(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const pad = n => String(n).padStart(2, '0');
  return h > 0 ? h + ':' + pad(m) + ':' + pad(s) : pad(m) + ':' + pad(s);
}

function hashQuestions(questions) {
  const str = questions.map(q => q.text + '|' + q.answerKey).join('~');
  let h = 5381; for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

/* ---------- demo bank (original questions, not from any real exam) ---------- */
const DEMO_TEXT = [
  'Q1. A stone is dropped from a height of 45 m (g = 10 m/s^2). How long does it take to reach the ground?',
  'A) 2 s', 'B) 3 s', 'C) 4.5 s', 'D) 9 s', 'Answer: B', 'Section: Physics',
  'Explanation: h = (1/2)gt^2, so 45 = 5t^2, t^2 = 9, t = 3 s.', '---',
  'Q2. A block of mass 2 kg on a frictionless surface is pushed with a force of 10 N. Find its acceleration.',
  'A) 2 m/s^2', 'B) 5 m/s^2', 'C) 10 m/s^2', 'D) 20 m/s^2', 'Answer: B', 'Section: Physics',
  'Explanation: a = F/m = 10/2 = 5 m/s^2.', '---',
  'Q3. A 1000 W motor lifts a load through 10 m in 10 s at constant speed. What is the weight of the load?',
  'A) 100 N', 'B) 500 N', 'C) 1000 N', 'D) 10000 N', 'Answer: C', 'Section: Physics',
  'Explanation: Work = Pt = 10000 J = mgh, so mg = 10000/10 = 1000 N.', '---',
  'Q4. The moment of inertia of a solid sphere of mass M and radius R about a diameter is:',
  'A) (1/2)MR^2', 'B) (2/3)MR^2', 'C) (2/5)MR^2', 'D) MR^2', 'Answer: C', 'Section: Physics',
  'Explanation: Standard result for a solid sphere about a diameter is (2/5)MR^2.', '---',
  'Q5. Earth\u2019s escape velocity is about 11.2 km/s. If Earth\u2019s radius were halved with mass unchanged, the new escape velocity would be about:',
  'A) 5.6 km/s', 'B) 11.2 km/s', 'C) 15.8 km/s', 'D) 22.4 km/s', 'Answer: C', 'Section: Physics',
  'Explanation: Escape velocity varies as 1/sqrt(R), so halving R scales v by sqrt(2) \u2248 1.41.', '---',
  'Q6. In an isothermal process, the internal energy of an ideal gas:',
  'A) increases', 'B) decreases', 'C) remains constant', 'D) depends on the pressure', 'Answer: C', 'Section: Physics',
  'Explanation: Internal energy of an ideal gas depends only on temperature, which is constant here.', '---',
  'Q7. For small oscillations, the time period of a simple pendulum depends on:',
  'A) its mass', 'B) its length', 'C) both its mass and length', 'D) its amplitude', 'Answer: B', 'Section: Physics',
  'Explanation: T = 2\u03c0\u221a(L/g) \u2014 independent of mass and (for small angles) amplitude.', '---',
  'Q8. A 4 \u03a9 and a 6 \u03a9 resistor are connected in series across a 10 V battery. Find the current.',
  'A) 0.5 A', 'B) 1 A', 'C) 2 A', 'D) 2.5 A', 'Answer: B', 'Section: Physics',
  'Explanation: I = V/(R1+R2) = 10/10 = 1 A.', '---',
  'Q9. A concave mirror forms a real image twice the size of an object placed 15 cm away. Its focal length is:',
  'A) 5 cm', 'B) 10 cm', 'C) 15 cm', 'D) 20 cm', 'Answer: B', 'Section: Physics',
  'Explanation: v = 2u = 30 cm; 1/f = 1/v + 1/u = 1/30 + 1/15 = 1/10, so f = 10 cm.', '---',
  'Q10. Two equal point charges +q are separated by distance r. The electric field at the midpoint between them is:',
  'A) zero', 'B) kq/r^2', 'C) 2kq/r^2', 'D) 4kq/r^2', 'Answer: A', 'Section: Physics',
  'Explanation: The fields from the two like charges point in opposite directions at the midpoint and cancel.', '---',
  'Q11. A radioactive sample has a half-life of 20 days. What fraction remains after 60 days?',
  'A) 1/2', 'B) 1/4', 'C) 1/8', 'D) 1/16', 'Answer: C', 'Section: Physics',
  'Explanation: 60 days is 3 half-lives, so the remaining fraction is (1/2)^3 = 1/8.', '---',
  'Q12. In a p-n junction diode under forward bias, the width of the depletion region:',
  'A) increases', 'B) decreases', 'C) stays the same', 'D) becomes infinite', 'Answer: B', 'Section: Physics',
  'Explanation: Forward bias opposes the built-in field and narrows the depletion region.', '---',
  'Q13. Two sound waves of frequency 256 Hz and 260 Hz are sounded together. The beat frequency heard is:',
  'A) 2 Hz', 'B) 4 Hz', 'C) 8 Hz', 'D) 258 Hz', 'Answer: B', 'Section: Physics',
  'Explanation: Beat frequency equals the difference of the two frequencies: 260 \u2212 256 = 4 Hz.', '---',
  'Q14. Planck\u2019s constant has the same dimensional formula as:',
  'A) energy', 'B) force', 'C) power', 'D) angular momentum', 'Answer: D', 'Section: Physics',
  'Explanation: [h] = J\u00b7s = kg m^2 s^-1, the same dimensions as angular momentum.', '---',
  'Q15. The magnetic field lines around a long straight current-carrying wire are:',
  'A) straight lines parallel to the wire', 'B) concentric circles around the wire', 'C) radiating outward from the wire', 'D) random', 'Answer: B', 'Section: Physics',
  'Explanation: By the right-hand rule, field lines form concentric circles around the wire.',
].join('\n');

function demoQuestions() { return parseMCQText(DEMO_TEXT); }

const CBT = { parseMCQText, parseMCQCsv, scoreTest, fmtClock, hashQuestions, demoQuestions, DEMO_TEXT };
if (typeof module !== 'undefined' && module.exports) module.exports = CBT; else root.CBT = CBT;
})(typeof window !== 'undefined' ? window : globalThis);
