// Local only (needs the v47 inputs). Chooses the v53 makeDefender scale.
//   node reports/player-impact-v53/calibrate-spread.mjs
// For every 2025-26 player the simulator's own eFG suppression is implied by his v45 fine
// makeDefender logits (league shot mix and make rates below, eFG weight 1.5 for threes):
//   implied = -100 * sum_z share_z * weight_z * p_z (1 - p_z) * makeDefender_z   (eFG points)
// Four-factor RAPM eFG defense (positive = lower eFG allowed) is regressed on it with weight
// min(defensive possessions, 20000). A slope above 1 means the simulator compresses defenders;
// the scale is max(1, slope), written to spread.json with the fit for review.
import fs from 'node:fs';
import {ovrInput} from '../ovr-v47-2025-26/input.mjs';
const MIX = {ra: [0.30, 0.66, 1], paint: [0.16, 0.44, 1], mid: [0.12, 0.42, 1], corner: [0.10, 0.39, 1.5], arc: [0.32, 0.35, 1.5]};
const x = await ovrInput();
const rows = fs.readFileSync('reports/impact-rapm/four-factors.csv', 'utf8').trim().split('\n');
const head = rows[0].trimEnd().split(','), col = k => head.indexOf(k);
const ff = new Map(rows.slice(1).map(l => l.split(',')).map(r => [Number(r[col('playerId')]), {efg: Number(r[col('efg_defense')]), poss: Number(r[col('defensePossessions')])}]));
const pts = [];
for (const p of x.players) {
  const f = ff.get(p.playerId), md = p.fineDefenseMeasurement?.makeDefender;
  if (!f || !md || !(f.poss > 0)) continue;
  const implied = -100 * Object.entries(MIX).reduce((s, [z, [share, pr, w]]) => s + share * w * pr * (1 - pr) * md[z], 0);
  pts.push({name: p.name, implied, rapm: f.efg, w: Math.min(f.poss, 20000)});
}
const sw = pts.reduce((s, q) => s + q.w, 0), mx = pts.reduce((s, q) => s + q.w * q.implied, 0) / sw, my = pts.reduce((s, q) => s + q.w * q.rapm, 0) / sw;
const sxx = pts.reduce((s, q) => s + q.w * (q.implied - mx) ** 2, 0), sxy = pts.reduce((s, q) => s + q.w * (q.implied - mx) * (q.rapm - my), 0);
const syy = pts.reduce((s, q) => s + q.w * (q.rapm - my) ** 2, 0);
const slope = sxy / sxx, corr = sxy / Math.sqrt(sxx * syy);
const sd = (k, m) => Math.sqrt(pts.reduce((s, q) => s + q.w * (q[k] - m) ** 2, 0) / sw);
const out = {players: pts.length, slope, correlation: corr, sdImplied: sd('implied', mx), sdRapm: sd('rapm', my), scale: Math.max(1, slope),
  note: 'RAPM is ridge-shrunk, so the slope is conservative; scale = max(1, slope).'};
fs.writeFileSync('reports/player-impact-v53/spread.json', JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 1));
