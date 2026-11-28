// 診斷腳本（唯讀）：列出 RAPM pooledD 前 30 名（pooledPoss>=5000）在 E2-λ0.4 卡片、2K27、RAPM pooledNet 的名次對照。
import fs from 'node:fs';

function parseCSV(path) {
  const rows = fs.readFileSync(path, 'utf8').replace(/\r\n/g, '\n').trim().split('\n');
  const head = rows[0].split(',');
  return rows.slice(1).map(l => {
    const c = l.split(',');
    return Object.fromEntries(head.map((h, i) => [h, c[i]]));
  });
}

const EVAL_POSS = 5000;
const rapm = parseCSV('reports/impact-rapm/rapm.csv');
const merged = parseCSV('reports/ovr-v55-2k27-compare/merged.csv');
const card = parseCSV('reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv');

const mergedByName = new Map(merged.map(r => [r.name, r]));
const cardByName = new Map(card.map(r => [r.name, r]));

const pool = rapm.filter(r => Number(r.pooledPoss) >= EVAL_POSS);
const byNetDesc = [...pool].sort((a, b) => Number(b.pooledNet) - Number(a.pooledNet));
const rapmNetRank = new Map(byNetDesc.map((r, i) => [r.name, i + 1]));
const byDDesc = [...pool].sort((a, b) => Number(b.pooledD) - Number(a.pooledD));

const top30D = byDDesc.slice(0, 30).map((r, i) => {
  const m = mergedByName.get(r.name);
  const c = cardByName.get(r.name);
  return {
    pooledDRank: i + 1,
    name: r.name,
    pos: c ? c.pos : (m ? m.pos : ''),
    pooledD: Number(r.pooledD),
    pooledNet: Number(r.pooledNet),
    rapmNetRank: rapmNetRank.get(r.name) ?? null,
    cardRank: c ? Number(c.rank) : null,
    cardOvr: c ? Number(c.ovr) : null,
    rank2k: m && m.rank2k ? Number(m.rank2k) : null,
    creation: m ? Number(m.creation) : null,
    help: c ? Number(c.help) : null,
    onBall: c ? Number(c.onBall) : null,
    rebound: c ? Number(c.rebound) : null,
    short: c ? Number(c.short) : null,
  };
});

console.log('name,pos,pooledDRank,pooledD,pooledNet,rapmNetRank,cardRank,cardOvr,rank2k,creation,help,onBall,rebound,short');
for (const r of top30D) {
  console.log([r.name, r.pos, r.pooledDRank, r.pooledD.toFixed(2), r.pooledNet.toFixed(2), r.rapmNetRank, r.cardRank, r.cardOvr, r.rank2k, r.creation, r.help, r.onBall, r.rebound, r.short].join(','));
}

const gapSummary = top30D.map(r => ({
  name: r.name,
  cardRank: r.cardRank,
  bestOutsideRank: Math.min(...[r.rapmNetRank, r.rank2k].filter(x => x != null)),
  gap: r.cardRank != null ? r.cardRank - Math.min(...[r.rapmNetRank, r.rank2k].filter(x => x != null)) : null,
}));
fs.writeFileSync('reports/ovr-v56-card-defense-2025-26/diagnose-top30-pooledD.json', JSON.stringify({evalPoss: EVAL_POSS, top30D, gapSummary}, null, 2) + '\n');
console.log('---gapSummary (cardRank - min(rapmNetRank,rank2k)), positive = 卡片比其他兩個指標都低估---');
for (const g of gapSummary.sort((a, b) => (b.gap ?? -999) - (a.gap ?? -999))) {
  console.log(g.name, 'cardRank=' + g.cardRank, 'bestOutside=' + g.bestOutsideRank, 'gap=' + g.gap);
}
