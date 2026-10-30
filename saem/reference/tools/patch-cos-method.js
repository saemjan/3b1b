const fs = require('fs');
const f = '/home/claude/saem-unified/src/cos.js';
let s = fs.readFileSync(f, 'utf8');
function once(a, b) { const n = s.split(a).length - 1; if (n !== 1) throw new Error('expected 1 match, got ' + n + ' for: ' + a.slice(0, 80)); s = s.replace(a, () => b); }
once("text: 'Every pick shows a probability under 95% and the years it came from.'",
     "text: 'Every pick shows a chance below 95% and the years it came from. Chances are scaled to match how often top picks really appeared on past papers.'");
once("res.chance = !picks.length ? ['info', 'No forecast yet.'] : picks.every(p => p.p <= MAXP && p.years && p.years.length) ? ['pass', picks.length + ' picks, the highest at ' + Math.round(Math.max.apply(null, picks.map(p => p.p)) * 100) + '%.'] : ['warn', 'Some picks lack a source year or exceed 95%.'];",
     "const cal = c.fc && c.fc.calibration, calNote = cal ? (cal.tested ? ' Scaled to past papers (\\u00d7' + cal.factor.toFixed(2) + ').' : ' Too few papers to test, so shown cautiously.') : '';\n  res.chance = !picks.length ? ['info', 'No forecast yet.'] : picks.every(p => p.p <= MAXP && p.years && p.years.length) ? ['pass', picks.length + ' picks, the highest at ' + Math.round(Math.max.apply(null, picks.map(p => p.p)) * 100) + '%.' + calNote] : ['warn', 'Some picks lack a source year or exceed 95%.'];");
once("EF.analyze.toString(), assemble.toString(),", "EF.analyze.toString(), EF.chooseMethod.toString(), EF.calibrate.toString(), assemble.toString(),");
fs.writeFileSync(f, s);
console.log('ok');
