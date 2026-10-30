/* One-time patch: the blend is the default ranking; the learned model must beat it by a margin; shown chances are calibrated on past papers. */
const fs = require('fs');
const f = '/home/claude/saem-unified/src/ef.js';
let s = fs.readFileSync(f, 'utf8');
function once(a, b) { const n = s.split(a).length - 1; if (n !== 1) throw new Error('expected 1 match, got ' + n + ' for: ' + a.slice(0, 80)); s = s.replace(a, () => b); }

/* 1. constants */
once("const tick = () => new Promise(r => setTimeout(r, 0));",
"const tick = () => new Promise(r => setTimeout(r, 0));\nconst MAXP = 0.95, LR_MARGIN = 0.02, MIN_TESTED = 4, SHRINK = 0.75, MIN_PAPERS = 11;");

/* 2. evalFold: score both methods, keep what calibration needs */
const a = s.indexOf('function evalFold(data, folds, fk, K) {');
const b = s.indexOf('/* ---------- topic weightage forecast ---------- */');
if (a < 0 || b < a) throw new Error('evalFold markers');
s = s.slice(0, a) + `function evalFold(data, folds, fk, K) {
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

` + s.slice(b);

/* 3. analyze: warnings, back-test summary, method, calibration, final ranking */
once("  if (N < 8) warnings.push('Only ' + N + ' papers: too few to test the model on past papers, and the forecast is rough. 15–20 papers works best.');",
     "  if (N < MIN_PAPERS) warnings.push('Only ' + N + ' papers: too few to test the forecast on past papers, so the chances shown are cautious estimates. 15–20 papers works best.');");

const c = s.indexOf("  const agg = key =>");
const d = s.indexOf("  const tf = topicForecast(data, T);");
if (c < 0 || d < c) throw new Error('analyze markers');
s = s.slice(0, c) + `  const agg = key => ({ precision: mean(evals.map(e => e[key].precision)), coverage: mean(evals.map(e => e[key].coverage)), meanP: mean(evals.map(e => e[key].meanP || 0)), hitRate: mean(evals.map(e => e[key].hitRate || 0)) });
  const tested = evals.length >= MIN_TESTED;
  const priorAgg = evals.length ? agg('prior') : null, lrAgg = tested && evals.every(e => e.lr) ? agg('lr') : null;
  const method = tested ? chooseMethod(priorAgg, lrAgg) : 'blend';
  const chosen = method === 'learned' ? lrAgg : priorAgg, cal = calibrate(tested ? chosen : null);
  const useKey = method === 'learned' ? 'lr' : 'prior';
  const backtest = evals.length ? { n: evals.length, from: data.years[evals[0].k], to: data.years[N - 1], method, model: chosen, prior: priorAgg, lr: lrAgg, random: agg('random'), freq: agg('freq'), recency: agg('recency'), novel: mean(evals.map(e => e.novel)), calibration: cal, per: evals.map(e => ({ year: data.years[e.k], precision: (e[useKey] || e.prior).precision, random: e.random.precision })) } : null;
  if (hooks.progress) await hooks.progress(N - j0 + 2, N - j0 + 2, 'final');

  const finalFold = folds.find(f => f.k === N), model = method === 'learned' ? trainOn(folds.filter(f => f.y)) : null;
  const P = finalFold.feats.map(ft => Math.min(MAXP, (model ? predictLR(model, ft.x) : priorP(ft)) * cal.factor));
` + s.slice(d);

once("    meta: { years: data.years,", "    method, calibration: cal,\n    meta: { years: data.years,");

/* 4. exports */
once("analyze, kwRegex, fitLR, predictLR, normKey };", "analyze, chooseMethod, calibrate, kwRegex, fitLR, predictLR, normKey, MAXP, LR_MARGIN };");

fs.writeFileSync(f, s);
console.log('ok', s.split('\n').length, 'lines');
