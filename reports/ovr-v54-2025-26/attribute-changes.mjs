// node reports/ovr-v54-2025-26/attribute-changes.mjs
// Top-20 long/short card-attribute changes between v53 (fixed 100-attempt pseudo-count) and v54
// (reliability-aware empirical-Bayes), with attempt counts, for reports/ovr-v54-2025-26/report.md.
import fs from 'node:fs';
const read = f => JSON.parse(fs.readFileSync(f));
const readSource = (file, setName) => {
  const doc = read('data/benchmark-source/' + file + '.json');
  const set = setName ? doc.data.resultSets.find(s => s.name === setName) : Array.isArray(doc.data.resultSets) ? doc.data.resultSets[0] : doc.data.resultSets;
  return set.rowSet.map(row => Object.fromEntries(set.headers.map((h, i) => [h, row[i]])));
};
const base = readSource('base');
const shots = read('data/benchmark-source/shots.json');
const shotsSet = Array.isArray(shots.data.resultSets) ? shots.data.resultSets[0] : shots.data.resultSets;
const shotRows = new Map(shotsSet.rowSet.map(r => [r[0], {shortM: r[6] + r[9], shortA: r[7] + r[10]}]));
const fg3 = new Map(base.map(r => [r.PLAYER_ID, {FG3M: r.FG3M, FG3A: r.FG3A}]));

const v53 = Object.fromEntries(read('data/season-league.json').teams.flatMap(t => t.roster).map(p => [p.playerId, p]));
const v54 = Object.fromEntries(read('data/season-league-v54.json').teams.flatMap(t => t.roster).map(p => [p.playerId, p]));

const rows = [];
for (const id of Object.keys(v53)) {
  if (!v54[id]) continue;
  const a = v53[id], b = v54[id];
  const three = fg3.get(Number(id)) || {FG3M: 0, FG3A: 0};
  const rim = shotRows.get(Number(id)) || {shortM: 0, shortA: 0};
  rows.push({
    playerId: Number(id), name: a.name, pos: a.pos,
    longV53: a.long, longV54: b.long, longDelta: b.long - a.long, threeMakes: three.FG3M, threeAttempts: three.FG3A,
    shortV53: a.short, shortV54: b.short, shortDelta: b.short - a.short, rimMakes: rim.shortM, rimAttempts: rim.shortA,
  });
}

const fmt = r => ({playerId: r.playerId, name: r.name, pos: r.pos,
  long: `${r.longV53.toFixed(1)} -> ${r.longV54.toFixed(1)} (${r.longDelta >= 0 ? '+' : ''}${r.longDelta.toFixed(1)})`, threeAttempts: `${r.threeMakes}/${r.threeAttempts}`,
  short: `${r.shortV53.toFixed(1)} -> ${r.shortV54.toFixed(1)} (${r.shortDelta >= 0 ? '+' : ''}${r.shortDelta.toFixed(1)})`, rimAttempts: `${r.rimMakes}/${r.rimAttempts}`});

const topLong = [...rows].sort((x, y) => Math.abs(y.longDelta) - Math.abs(x.longDelta)).slice(0, 20).map(fmt);
const topShort = [...rows].sort((x, y) => Math.abs(y.shortDelta) - Math.abs(x.shortDelta)).slice(0, 20).map(fmt);

fs.writeFileSync('reports/ovr-v54-2025-26/attribute-changes.json', JSON.stringify({topLong, topShort}, null, 1));
console.log(JSON.stringify({topLong, topShort}, null, 1));
