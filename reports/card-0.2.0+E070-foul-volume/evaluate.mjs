// E-070 複本：只改 CANDIDATES（card 0.2.0 與 E070 候選）與輸出路徑；門檻與函式未改。
// E-060 複本（自 E-059 evaluate.mjs，只加 E060 候選與改輸出路徑；門檻未改）
// E-059 複本（自 E-058 evaluate.mjs，只改候選與輸出路徑；門檻未改）
// E-058 複本：v61 evaluate.mjs，只改候選（v61 基準 vs E058）與輸出路徑；門檻未改。
// v61：複本自 reports/ovr-v60-drive-split-2025-26/evaluate.mjs（候選改為 v58 H1-m0、v60 拆分卡、v61 拉回卡，輸出路徑改到 v61；門檻與函式未改）。以下為 v60 原說明：
// v60：複本自 reports/ovr-v58-card-2025-26/evaluate.mjs，唯一差異是候選清單（v58 H1-m0 對 v60 拆分卡與敏感度版本）與輸出路徑；門檻與函式未改。
// v58 評估腳本：讀 H1–H4 候選 ranking.csv + E2-λ0.4／F2-γ0.5／v53／v57 G3-δ0.25 四個基準 +
// merged.csv（2K27）+ rapm.csv（pooledD/pooledNet），套用 v58 preregistration.md 第四節沿用的
// 19 項硬門檻 + 回報項 19-23。唯讀腳本，只寫 reports/card-0.1.1+E059-onball-contest/evaluation.json。
import fs from 'node:fs';
import crypto from 'node:crypto';

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
const BIG = new Set(['PF', 'C']);
const WING = new Set(['SF']);
const GUARD = new Set(['PG', 'SG']);
const ALLOWED_BIGS = new Set(['Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren']);

const merged = parseCSV('reports/ovr-v55-2k27-compare/merged.csv');
const mergedByName = new Map(merged.map(r => [r.name, r]));
const rapmRaw = parseCSV('reports/impact-rapm/rapm.csv');
// rapm.csv 有大量 name 空白的列（非本卡片球員，無法對應，共 295 列，其中 64 列 pooledPoss>=5000）。
// 比照 diagnose.py 的 `{r['name']: r for r in rows}`（Python dict，同名/同為空白時最後一列覆蓋前面），
// 用 name 去重再建池，否則空白列會擠占排名名次，與 diagnose.py、本文件鎖定的 RAPM 名次數字不一致
// （已用腳本核對：去重後 Gobert=29、Jones=14、Smart=30、Jalen Smith=65、Mobley=47、Chet=8、
// Embiid=10、Gordon=21，與 preregistration.md 第一節寫死的數字逐一相符；不去重則分別是
// 32/15/34/69/…，不符）。
const rapmDedupByName = new Map();
for (const r of rapmRaw) rapmDedupByName.set(r.name, r);
const rapm = [...rapmDedupByName.values()];
const rapmByName = rapmDedupByName;
const rapmPool = rapm.filter(r => Number(r.pooledPoss) >= EVAL_POSS);
const rapmNetRankMap = new Map([...rapmPool].sort((a, b) => Number(b.pooledNet) - Number(a.pooledNet)).map((r, i) => [r.name, i + 1]));
const rapmDRankMap = new Map([...rapmPool].sort((a, b) => Number(b.pooledD) - Number(a.pooledD)).map((r, i) => [r.name, i + 1]));

const SEVEN_PLAYERS = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza', 'Neemias Queta', 'Rudy Gobert', 'Jalen Smith'];
const WING_NAMED = ['Herbert Jones', 'Alex Caruso', 'Marcus Smart'];

function rank2k(name) {
  const m = mergedByName.get(name);
  return m && m.rank2k ? Number(m.rank2k) : null;
}
function gateRef(name) {
  const vals = [rank2k(name), rapmNetRankMap.get(name) ?? null].filter(v => v != null);
  return vals.length ? Math.max(...vals) : null;
}

function evalRanking(label, path) {
  const rows = parseCSV(path);
  const byName = new Map(rows.map(r => [r.name, r]));
  const rho2k = spearman(rows.filter(r => mergedByName.has(r.name) && mergedByName.get(r.name).rank2k).map(r => [Number(r.ovr), Number(mergedByName.get(r.name).overall2k)]));
  const rapmRows = rows.filter(r => rapmByName.has(r.name) && Number(rapmByName.get(r.name).pooledPoss) >= EVAL_POSS);
  const rhoRapm = spearman(rapmRows.map(r => [Number(r.ovr), Number(rapmByName.get(r.name).pooledNet)]));
  const rhoDef = spearman(rapmRows.map(r => [Number(r.ovr), Number(rapmByName.get(r.name).pooledD)]));
  const sevenPlayer = SEVEN_PLAYERS.map(name => {
    const r = byName.get(name);
    return {name, rank: r ? Number(r.rank) : null, ovr: r ? Number(r.ovr) : null, rank2k: rank2k(name), rapmRank: rapmNetRankMap.get(name) ?? null};
  });
  const wingNamed = WING_NAMED.map(name => {
    const r = byName.get(name);
    return {name, rank: r ? Number(r.rank) : null, rank2k: rank2k(name), rapmRank: rapmNetRankMap.get(name) ?? null, ref: gateRef(name)};
  });
  const top10 = rows.filter(r => Number(r.rank) <= 10).sort((a, b) => Number(a.rank) - Number(b.rank))
    .map(r => ({name: r.name, pos: r.pos, rank: Number(r.rank), ovr: Number(r.ovr), isBig: BIG.has(r.pos)}));
  const top10Bigs = top10.filter(r => r.isBig);
  const extraBigs = top10Bigs.filter(r => !ALLOWED_BIGS.has(r.name)).map(r => ({
    name: r.name, rank: r.rank, rank2k: rank2k(r.name), rapmNetRank: rapmNetRankMap.get(r.name) ?? null,
  }));
  return {label, rho2k, rhoRapm, rhoDef, sevenPlayer, wingNamed, top10, top10Bigs: top10Bigs.map(r => r.name),
          extraBigsStrict: extraBigs, n: rows.length, nRapm: rapmRows.length, byName};
}

const v53 = evalRanking('v53', 'reports/ovr-calibrated-2025-26/ranking.csv');
const e2 = evalRanking('E2-lam0.4', 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv');
const f2 = evalRanking('F2-gamma0.5', 'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv');
const g3 = evalRanking('G3-delta0.25', 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv');

// RAPM pooledD 前30，用 E2 的 pos 分組（候選不改變球員 pos，三個候選/基準 pos 一致）
const pooledDTop30 = [...rapmPool].sort((a, b) => Number(b.pooledD) - Number(a.pooledD)).slice(0, 30)
  .map(r => ({name: r.name, pos: e2.byName.get(r.name)?.pos}))
  .filter(r => r.pos);
const wingGuard14 = pooledDTop30.filter(r => WING.has(r.pos) || GUARD.has(r.pos));
const big16 = pooledDTop30.filter(r => BIG.has(r.pos));

function gatesFor(result) {
  const v53map = Object.fromEntries(v53.sevenPlayer.map(p => [p.name, p]));
  const cur = Object.fromEntries(result.sevenPlayer.map(p => [p.name, p]));
  const wn = Object.fromEntries(result.wingNamed.map(p => [p.name, p]));
  const g = {};
  const detail = {};

  g.karloDrop10 = (cur['Karlo Matković'].rank - v53map['Karlo Matković'].rank) >= 10;
  g.collinsDrop = cur['John Collins'].rank > v53map['John Collins'].rank;
  g.stewartDrop = cur['Isaiah Stewart'].rank > v53map['Isaiah Stewart'].rank;
  g.garzaDrop = cur['Luka Garza'].rank > v53map['Luka Garza'].rank;
  const quetaRef = Math.max(cur['Neemias Queta'].rank2k, cur['Neemias Queta'].rapmRank);
  g.quetaGate = cur['Neemias Queta'].rank <= quetaRef;
  const gobertRef = Math.max(cur['Rudy Gobert'].rank2k, cur['Rudy Gobert'].rapmRank);
  g.gobertGate = cur['Rudy Gobert'].rank <= gobertRef;
  g.jalenSmithGate = cur['Jalen Smith'].rank <= 220;

  // 第 8/9 項：地板提高到 F2-γ0.5 水準（本腳本自己量到的數字，而非報告文字裡的歷史數字）
  g.rho2kFloor = result.rho2k >= f2.rho2k - 0.005;
  g.rhoRapmFloor = result.rhoRapm >= f2.rhoRapm - 0.005;

  // 第 10 項：側翼+後衛 14 人裡通過 rank<=max(2K27,RAPM) 的人數 >= 10
  const wgDetail = wingGuard14.map(p => {
    const r = result.byName.get(p.name);
    const rank = r ? Number(r.rank) : null;
    const ref = gateRef(p.name);
    const pass = rank != null && ref != null && rank <= ref;
    return {name: p.name, pos: p.pos, rank, ref, pass};
  });
  const wgPassCount = wgDetail.filter(d => d.pass).length;
  g.wingGuard10of14 = wgPassCount >= 10;
  detail.wingGuard14 = wgDetail;
  detail.wingGuardPassCount = wgPassCount;

  g.herbertJonesGate = wn['Herbert Jones'].rank <= wn['Herbert Jones'].ref;
  g.carusoGate = wn['Alex Caruso'].rank <= wn['Alex Caruso'].ref;
  g.marcusSmartGate = wn['Marcus Smart'].rank <= wn['Marcus Smart'].ref;

  // 第 14 項：長人組（PF/C）16 人不得退步，>=14/16
  const bigDetail = big16.map(p => {
    const r = result.byName.get(p.name);
    const rank = r ? Number(r.rank) : null;
    const ref = gateRef(p.name);
    const pass = rank != null && ref != null && rank <= ref;
    return {name: p.name, pos: p.pos, rank, ref, pass};
  });
  const bigPassCount = bigDetail.filter(d => d.pass).length;
  g.big14of16 = bigPassCount >= 14;
  detail.big16 = bigDetail;
  detail.bigPassCount = bigPassCount;

  // 第 15-18 項：前十長人
  g.top10BigsMax5 = result.top10Bigs.length <= 5;
  g.noMobleyTop10 = !result.top10.some(r => r.name === 'Evan Mobley');
  g.noGordonTop10 = !result.top10.some(r => r.name === 'Aaron Gordon');
  g.allFourStayTop10 = [...ALLOWED_BIGS].every(name => result.top10.some(r => r.name === name));

  // 第 20 項：rhoDef 下限（不得低於 E2 基準），計入 19 項硬門檻
  g.rhoDefFloorE2 = result.rhoDef >= e2.rhoDef - 1e-9;

  const hardKeys = ['karloDrop10', 'collinsDrop', 'stewartDrop', 'garzaDrop', 'quetaGate', 'gobertGate',
    'jalenSmithGate', 'rho2kFloor', 'rhoRapmFloor', 'wingGuard10of14', 'herbertJonesGate', 'carusoGate',
    'marcusSmartGate', 'big14of16', 'top10BigsMax5', 'noMobleyTop10', 'noGordonTop10', 'allFourStayTop10',
    'rhoDefFloorE2'];
  const pass = hardKeys.filter(k => g[k]).length;

  // 第 19 項：觀察項，嚴格版「前十長人恰為四人」
  const strictFour = result.top10Bigs.length === 4 && result.top10Bigs.every(n => ALLOWED_BIGS.has(n));
  detail.strictFourBigsTop10 = strictFour;
  detail.extraBigsBeyondFour = result.extraBigsStrict;

  return {...g, hardKeys, pass, of: hardKeys.length, quetaRef, gobertRef, ...detail};
}

const v53Gates = gatesFor(v53);
const e2Gates = gatesFor(e2);
const f2Gates = gatesFor(f2);
const g3Gates = gatesFor(g3);

const CANDIDATES = [
  ['card-0.2.0', 'reports/card-0.2.0/ranking.csv'],
  ['E070', 'reports/card-0.2.0+E070-foul-volume/primary/ranking.csv'],
].map(([label, path]) => fs.existsSync(path) ? evalRanking(label, path) : null).filter(Boolean);

function capInfo(label) {
  return null;
}

console.log('v53  rho2k', v53.rho2k.toFixed(4), 'rhoRapm', v53.rhoRapm.toFixed(4), 'rhoDef', v53.rhoDef.toFixed(4));
console.log('E2-lam0.4  rho2k', e2.rho2k.toFixed(4), 'rhoRapm', e2.rhoRapm.toFixed(4), 'rhoDef', e2.rhoDef.toFixed(4), 'gates', e2Gates.pass + '/' + e2Gates.of);
console.log('F2-gamma0.5 rho2k', f2.rho2k.toFixed(4), 'rhoRapm', f2.rhoRapm.toFixed(4), 'rhoDef', f2.rhoDef.toFixed(4), 'gates', f2Gates.pass + '/' + f2Gates.of);
console.log('G3-delta0.25 rho2k', g3.rho2k.toFixed(4), 'rhoRapm', g3.rhoRapm.toFixed(4), 'rhoDef', g3.rhoDef.toFixed(4), 'gates', g3Gates.pass + '/' + g3Gates.of);
console.log('---');
const candResults = [];
for (const c of CANDIDATES) {
  const g = gatesFor(c);
  console.log(c.label, 'rho2k', c.rho2k.toFixed(4), 'rhoRapm', c.rhoRapm.toFixed(4), 'rhoDef', c.rhoDef.toFixed(4),
    'pass', g.pass + '/' + g.of, 'top10Bigs', JSON.stringify(c.top10Bigs), 'wgPass', g.wingGuardPassCount + '/14',
    'bigPass', g.bigPassCount + '/16', 'strictFour', g.strictFourBigsTop10);
  candResults.push({...c, gates: g});
}

// sha256 of data/season-league.json（第 21 項，純回報）
const sha256 = fs.existsSync('data/season-league.json')
  ? crypto.createHash('sha256').update(fs.readFileSync('data/season-league.json')).digest('hex')
  : null;
console.log('data/season-league.json sha256:', sha256);

fs.writeFileSync('reports/card-0.2.0+E070-foul-volume/evaluation.json', JSON.stringify({
  baselines: {
    v53: {rho2k: v53.rho2k, rhoRapm: v53.rhoRapm, rhoDef: v53.rhoDef, gates: v53Gates},
    'E2-lam0.4': {rho2k: e2.rho2k, rhoRapm: e2.rhoRapm, rhoDef: e2.rhoDef, top10: e2.top10, top10Bigs: e2.top10Bigs, gates: e2Gates},
    'F2-gamma0.5': {rho2k: f2.rho2k, rhoRapm: f2.rhoRapm, rhoDef: f2.rhoDef, top10: f2.top10, top10Bigs: f2.top10Bigs, gates: f2Gates},
    'G3-delta0.25': {rho2k: g3.rho2k, rhoRapm: g3.rhoRapm, rhoDef: g3.rhoDef, top10: g3.top10, top10Bigs: g3.top10Bigs, gates: g3Gates},
  },
  candidates: candResults.map(c => ({
    label: c.label, rho2k: c.rho2k, rhoRapm: c.rhoRapm, rhoDef: c.rhoDef, n: c.n, nRapm: c.nRapm,
    sevenPlayer: c.sevenPlayer, wingNamed: c.wingNamed, top10: c.top10, top10Bigs: c.top10Bigs,
    extraBigsStrict: c.extraBigsStrict, gates: c.gates, cap: capInfo(c.label),
  })),
  wembanyamaRank: {
    f2: f2.top10.find(r => r.name === 'Victor Wembanyama')?.rank ?? null,
    e2: e2.top10.find(r => r.name === 'Victor Wembanyama')?.rank ?? null,
    g3: g3.top10.find(r => r.name === 'Victor Wembanyama')?.rank ?? null,
    candidates: Object.fromEntries(candResults.map(c => [c.label, c.byName.get('Victor Wembanyama') ? Number(c.byName.get('Victor Wembanyama').rank) : null])),
  },
  dataSeasonLeagueSha256: sha256,
}, null, 2) + '\n');
