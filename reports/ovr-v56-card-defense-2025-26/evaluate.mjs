// 讀 F1/F2 候選 ranking.csv + E2-λ0.4 基準 + v53 官方 ranking.csv + merged.csv（2K27/RAPM 對照）+
// rapm.csv（pooledD，算 rhoDef），套用 preregistration.md 鎖定的驗收門檻。唯讀腳本，不改既有產物。
import fs from 'node:fs';

function parseCSV(path) {
  const rows = fs.readFileSync(path, 'utf8').replace(/\r\n/g, '\n').trim().split('\n');
  const head = rows[0].split(',');
  return rows.slice(1).map(l => {
    const c = l.split(',');
    return Object.fromEntries(head.map((h, i) => [h, c[i]]));
  });
}
function spearman(pairs) {
  const n = pairs.length;
  const rankOf = arr => {
    const idx = arr.map((v, i) => i).sort((a, b) => arr[a] - arr[b]);
    const r = new Array(n);
    let i = 0;
    while (i < n) {
      let j = i;
      while (j + 1 < n && arr[idx[j + 1]] === arr[idx[i]]) j++;
      const avg = (i + j) / 2 + 1;
      for (let k = i; k <= j; k++) r[idx[k]] = avg;
      i = j + 1;
    }
    return r;
  };
  const xs = pairs.map(p => p[0]), ys = pairs.map(p => p[1]);
  const rx = rankOf(xs), ry = rankOf(ys);
  const mx = rx.reduce((a, b) => a + b, 0) / n, my = ry.reduce((a, b) => a + b, 0) / n;
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) { num += (rx[i] - mx) * (ry[i] - my); dx += (rx[i] - mx) ** 2; dy += (ry[i] - my) ** 2; }
  return num / Math.sqrt(dx * dy);
}

const EVAL_POSS = 5000;
const merged = parseCSV('reports/ovr-v55-2k27-compare/merged.csv');
const mergedByName = new Map(merged.map(r => [r.name, r]));
const rapm = parseCSV('reports/impact-rapm/rapm.csv');
const rapmByName = new Map(rapm.map(r => [r.name, r]));
const rapmPool = rapm.filter(r => Number(r.pooledPoss) >= EVAL_POSS);
const rapmNetRankMap = new Map([...rapmPool].sort((a, b) => Number(b.pooledNet) - Number(a.pooledNet)).map((r, i) => [r.name, i + 1]));

const TARGET_PLAYERS = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza', 'Neemias Queta', 'Rudy Gobert', 'Jalen Smith'];

function evalRanking(label, path) {
  const rows = parseCSV(path);
  const byName = new Map(rows.map(r => [r.name, r]));
  const rho2k = spearman(rows.filter(r => mergedByName.has(r.name) && mergedByName.get(r.name).rank2k).map(r => [Number(r.ovr), Number(mergedByName.get(r.name).overall2k)]));
  const rapmRows = rows.filter(r => rapmByName.has(r.name) && Number(rapmByName.get(r.name).pooledPoss) >= EVAL_POSS);
  const rhoRapm = spearman(rapmRows.map(r => [Number(r.ovr), Number(rapmByName.get(r.name).pooledNet)]));
  const rhoDef = spearman(rapmRows.map(r => [Number(r.ovr), Number(rapmByName.get(r.name).pooledD)]));
  const sevenPlayer = TARGET_PLAYERS.map(name => {
    const r = byName.get(name);
    const m = mergedByName.get(name);
    const rr = rapmNetRankMap.get(name) ?? null;
    return {name, rank: r ? Number(r.rank) : null, ovr: r ? Number(r.ovr) : null, rank2k: m ? Number(m.rank2k) : null, rapmRank: rr};
  });
  const top10 = rows.filter(r => Number(r.rank) <= 10).sort((a, b) => Number(a.rank) - Number(b.rank))
    .map(r => ({name: r.name, pos: r.pos, rank: Number(r.rank), ovr: Number(r.ovr), isBig: r.pos === 'PF' || r.pos === 'C'}));
  return {label, rho2k, rhoRapm, rhoDef, sevenPlayer, top10, nRapm: rapmRows.length, n: rows.length};
}

const v53 = evalRanking('v53', 'reports/ovr-calibrated-2025-26/ranking.csv');
const e2 = evalRanking('E2-lam0.4', 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv');

const candidates = [
  ['F1-beta0.5', 'reports/ovr-v56-card-defense-2025-26/card-F1-beta0.5/ranking.csv'],
  ['F1-beta1.0', 'reports/ovr-v56-card-defense-2025-26/card-F1-beta1.0/ranking.csv'],
  ['F2-gamma0.5', 'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv'],
  ['F2-gamma1.0', 'reports/ovr-v56-card-defense-2025-26/card-F2-gamma1.0/ranking.csv'],
  ['F3-beta0.5-gamma0.5', 'reports/ovr-v56-card-defense-2025-26/card-F3/ranking.csv'],
].map(([label, path]) => fs.existsSync(path) ? evalRanking(label, path) : null).filter(Boolean);

function gatesFor(result) {
  const v53map = Object.fromEntries(v53.sevenPlayer.map(p => [p.name, p]));
  const cur = Object.fromEntries(result.sevenPlayer.map(p => [p.name, p]));
  const g = {};
  g.karloDrop10 = (cur['Karlo Matković'].rank - v53map['Karlo Matković'].rank) >= 10;
  g.collinsDrop = cur['John Collins'].rank > v53map['John Collins'].rank;
  g.stewartDrop = cur['Isaiah Stewart'].rank > v53map['Isaiah Stewart'].rank;
  g.garzaDrop = cur['Luka Garza'].rank > v53map['Luka Garza'].rank;
  const quetaRef = Math.max(cur['Neemias Queta'].rank2k, cur['Neemias Queta'].rapmRank);
  g.quetaGate = cur['Neemias Queta'].rank <= quetaRef;
  const gobertRef = Math.max(cur['Rudy Gobert'].rank2k, cur['Rudy Gobert'].rapmRank);
  g.gobertGate = cur['Rudy Gobert'].rank <= gobertRef;
  g.jalenSmithGate = cur['Jalen Smith'].rank <= 220;
  // 用本腳本自己量到的 E2-λ0.4 基準（而非舊報告文字裡的歷史數字 0.4746/0.5290）當地板，
  // 確保基準與候選用同一套 evaluate.mjs 算出，口徑一致；報告會列出兩者差異。
  g.rho2kFloor = result.rho2k >= e2.rho2k - 0.005;
  g.rhoRapmFloor = result.rhoRapm >= e2.rhoRapm - 0.005;
  const pass = Object.values(g).filter(Boolean).length;
  return {...g, pass, of: Object.keys(g).length, quetaRef, gobertRef};
}

console.log('v53  rho2k', v53.rho2k.toFixed(4), 'rhoRapm', v53.rhoRapm.toFixed(4), 'rhoDef', v53.rhoDef.toFixed(4), 'nRapm', v53.nRapm);
console.log('E2-lam0.4 (official baseline) rho2k', e2.rho2k.toFixed(4), 'rhoRapm', e2.rhoRapm.toFixed(4), 'rhoDef', e2.rhoDef.toFixed(4));
console.log('E2-lam0.4 7p', JSON.stringify(e2.sevenPlayer));
console.log('E2-lam0.4 top10', JSON.stringify(e2.top10.map(p => p.name + '(' + p.pos + ')')));
console.log('E2-lam0.4 gates', JSON.stringify(gatesFor(e2)));
console.log('---');
for (const c of candidates) {
  const g = gatesFor(c);
  console.log(c.label, 'rho2k', c.rho2k.toFixed(4), 'rhoRapm', c.rhoRapm.toFixed(4), 'rhoDef', c.rhoDef.toFixed(4), 'pass', g.pass + '/' + g.of, JSON.stringify(g));
  console.log('  7p', JSON.stringify(c.sevenPlayer));
  console.log('  top10', JSON.stringify(c.top10.map(p => p.name + '(' + p.pos + ')')));
}
fs.writeFileSync('reports/ovr-v56-card-defense-2025-26/evaluation.json', JSON.stringify({
  v53, e2: {...e2, gates: gatesFor(e2)},
  candidates: candidates.map(c => ({...c, gates: gatesFor(c)})),
}, null, 2) + '\n');
