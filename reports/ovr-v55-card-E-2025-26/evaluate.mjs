// 讀六個 E 系列 ranking.csv + v53 官方 ranking.csv + merged.csv（2K27/RAPM 對照），
// 算 7 人表、Top-10、ρ(2K27)、ρ(RAPM)，套用驗收門檻。唯讀腳本，不寫回任何既有產物。
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

const merged = parseCSV('reports/ovr-v55-2k27-compare/merged.csv');
const mergedByName = new Map(merged.map(r => [r.name, r]));

const TARGET_PLAYERS = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza', 'Neemias Queta', 'Rudy Gobert', 'Jalen Smith'];

function evalRanking(label, path) {
  const rows = parseCSV(path);
  const byName = new Map(rows.map(r => [r.name, r]));
  const rho2k = spearman(rows.filter(r => mergedByName.has(r.name)).map(r => [Number(r.ovr), Number(mergedByName.get(r.name).overall2k)]));
  const rapmRows = rows.filter(r => mergedByName.has(r.name) && Number(mergedByName.get(r.name).pooledPoss) >= 5000);
  const rhoRapm = spearman(rapmRows.map(r => [Number(r.ovr), Number(mergedByName.get(r.name).pooledNet)]));
  const sevenPlayer = TARGET_PLAYERS.map(name => {
    const r = byName.get(name);
    const m = mergedByName.get(name);
    return {name, rank: r ? Number(r.rank) : null, ovr: r ? Number(r.ovr) : null, rank2k: m ? Number(m.rank2k) : null};
  });
  const top10 = rows.filter(r => Number(r.rank) <= 10).sort((a, b) => Number(a.rank) - Number(b.rank))
    .map(r => ({name: r.name, pos: r.pos, rank: Number(r.rank), ovr: Number(r.ovr), isBig: r.pos === 'PF' || r.pos === 'C'}));
  return {label, rho2k, rhoRapm, sevenPlayer, top10, nRapm: rapmRows.length, n: rows.length};
}

const baseline = evalRanking('v53', 'reports/ovr-calibrated-2025-26/ranking.csv');
const variants = ['E1-k1000', 'E1-k1500', 'E1-k2500', 'E2-lam0.4', 'E2-lam0.6', 'E3'].map(v =>
  evalRanking(v, `reports/ovr-v55-card-E-2025-26/card-${v}/ranking.csv`));

function gatesFor(result) {
  const base = Object.fromEntries(baseline.sevenPlayer.map(p => [p.name, p]));
  const cur = Object.fromEntries(result.sevenPlayer.map(p => [p.name, p]));
  const g = {};
  g.karloDrop10 = (cur['Karlo Matković'].rank - base['Karlo Matković'].rank) >= 10;
  g.collinsDrop = cur['John Collins'].rank > base['John Collins'].rank;
  g.stewartDrop = cur['Isaiah Stewart'].rank > base['Isaiah Stewart'].rank;
  g.garzaDrop = cur['Luka Garza'].rank > base['Luka Garza'].rank;
  g.quetaDrop15 = (cur['Neemias Queta'].rank - base['Neemias Queta'].rank) <= 15;
  g.gobertDrop15 = (cur['Rudy Gobert'].rank - base['Rudy Gobert'].rank) <= 15;
  g.jalenSmithRule = cur['Jalen Smith'].rank <= cur['Jalen Smith'].rank2k;
  g.rho2kFloor = result.rho2k >= baseline.rho2k;
  g.rhoRapmFloor = result.rhoRapm >= baseline.rhoRapm;
  const pass = Object.values(g).filter(Boolean).length;
  return {...g, pass, of: Object.keys(g).length};
}

console.log('baseline rho2k', baseline.rho2k.toFixed(4), 'rhoRapm', baseline.rhoRapm.toFixed(4), 'nRapm', baseline.nRapm);
console.log('baseline 7p', JSON.stringify(baseline.sevenPlayer));
console.log('baseline top10', JSON.stringify(baseline.top10.map(p => p.name + '(' + p.pos + ')')));
console.log('---');
for (const v of variants) {
  const g = gatesFor(v);
  console.log(v.label, 'rho2k', v.rho2k.toFixed(4), 'rhoRapm', v.rhoRapm.toFixed(4), 'pass', g.pass + '/' + g.of, JSON.stringify(g));
  console.log('  7p', JSON.stringify(v.sevenPlayer));
  console.log('  top10', JSON.stringify(v.top10.map(p => p.name + '(' + p.pos + ')')));
}
fs.writeFileSync('reports/ovr-v55-card-E-2025-26/evaluation.json', JSON.stringify({baseline, variants: variants.map(v => ({...v, gates: gatesFor(v)}))}, null, 2) + '\n');
