// E-309 (b)：sim 0.1.3（E-166 k=2）同一棵樹，只把每位防守者的出手選擇 logit（v45 choiceDefender.three／paintGivenTwo）
// 換成 rimDet／threeDet 換算值（../data/sim-choice.json，prep_sim.py）。arm 'B'＝原樣（E-166 基準），'Z'＝替換。
// 置中：x.players 以 supportedMinutes 加權，新值平均對齊舊值平均（聯盟出手分布不變）；沒有 rimDet 的人原始值 0（ridge 先驗）。
// 位置平均輪廓（x.profiles）照同位置球員的分鐘加權平均差位移，xAvg 重算。對手名單（x.opponents）是另一份物件，同樣替換。
import fs from 'node:fs';
const C166 = await import('../E166/core166.mjs');
const {averageProfiles} = await import('../E140-foul-on-recal/winimp-core-e140.mjs');
const {source} = await import('../player-impact-v29/benchmark.mjs');
export const {arg, C012, P012, computeDraws} = C166;
export const makeRunner = C166.makeRunner;
const KEYS = ['three', 'paintGivenTwo'];
export async function loadX(arm = 'B') {
  const X0 = await C166.loadX();
  if (arm === 'B') return X0;
  if (arm !== 'Z') throw Error('arm ' + arm);
  const {x} = X0, tab = JSON.parse(fs.readFileSync(new URL('../data/sim-choice.json', import.meta.url))).players;
  const mins = source().players, w = p => mins[p.playerId]?.supportedMinutes ?? 0;
  const raw = id => tab[String(id)] ?? {three: 0, paintGivenTwo: 0};
  const shift = {};
  for (const k of KEYS) {
    let W = 0, mo = 0, mn = 0;
    for (const p of x.players) { const ww = w(p); W += ww; mo += ww * p.fineDefenseMeasurement.choiceDefender[k]; mn += ww * raw(p.playerId)[k]; }
    shift[k] = (mo - mn) / W;
  }
  const val = (id, k) => raw(id)[k] + shift[k];
  const posDelta = {};
  for (const pos of new Set(x.profiles.map(p => p.pos))) {
    const g = x.players.filter(p => p.pos === pos); posDelta[pos] = {};
    for (const k of KEYS) { let W = 0, d = 0; for (const p of g) { const ww = w(p); W += ww; d += ww * (val(p.playerId, k) - p.fineDefenseMeasurement.choiceDefender[k]); } posDelta[pos][k] = W > 0 ? d / W : 0; }
  }
  const put = p => { const cd = {...p.fineDefenseMeasurement.choiceDefender}; for (const k of KEYS) cd[k] = val(p.playerId, k); p.fineDefenseMeasurement = {...p.fineDefenseMeasurement, choiceDefender: cd}; };
  let n = 0;
  for (const p of x.players) { put(p); n++; }
  for (const t of x.opponents) for (const p of t.roster) { if (p.fineDefenseMeasurement?.choiceDefender) put(p); }
  for (const p of x.profiles) { const cd = {...p.fineDefenseMeasurement.choiceDefender}; for (const k of KEYS) cd[k] += posDelta[p.pos][k]; p.fineDefenseMeasurement = {...p.fineDefenseMeasurement, choiceDefender: cd}; }
  if (process.env.E309_DEBUG) console.error(JSON.stringify({arm, n, shift, posDelta}));
  return {x, xAvg: {...x, profiles: averageProfiles(x)}};
}
