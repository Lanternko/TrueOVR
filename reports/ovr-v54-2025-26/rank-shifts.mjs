// node reports/ovr-v54-2025-26/rank-shifts.mjs
// Top-30 simulation-board rank shifts between v53 and v54, using each version's own v2-shrinkage
// ranking.csv (reports/ovr-v53-shrinkage-2025-26/ranking-v2.csv vs reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv).
import fs from 'node:fs';
const parse = f => {
  const [head, ...lines] = fs.readFileSync(f, 'utf8').trim().split('\n');
  const cols = head.split(',');
  return new Map(lines.map(l => {
    const v = l.split(',');
    return [Number(v[cols.indexOf('playerId')]), Object.fromEntries(cols.map((c, i) => [c, v[i]]))];
  }));
};
const v53 = parse('reports/ovr-v53-shrinkage-2025-26/ranking-v2.csv');
const v54 = parse('reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv');
const rows = [];
for (const [id, b] of v54) {
  const a = v53.get(id);
  if (!a) continue;
  rows.push({playerId: id, name: b.name, pos: b.pos, v53Rank: Number(a.rank), v54Rank: Number(b.rank), shift: Number(a.rank) - Number(b.rank)});
}
const top30 = [...rows].sort((x, y) => Math.abs(y.shift) - Math.abs(x.shift)).slice(0, 30);
fs.writeFileSync('reports/ovr-v54-2025-26/rank-shifts.json', JSON.stringify(top30, null, 1));
console.log(JSON.stringify(top30, null, 1));
