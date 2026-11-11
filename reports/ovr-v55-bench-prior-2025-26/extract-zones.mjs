// v55: multi-season raw shot-zone + box counts, one entry per (season, playerId).
//
// Zone definitions kept identical to the existing single-season pipelines so that pooling across
// seasons is apples-to-apples:
//   long (3pt), ft  -> box-score totals (FG3M/FG3A, FTM/FTA) -- same source build_season_league.js
//                      uses for 2025-26 and reports/defense-tenth/step4-t0/prepare.mjs uses for
//                      2022-23..2024-25.
//   mid, short      -> 2025-26: NBA shot-location API zones (data/benchmark-source/shots.json),
//                      same as build_season_league.js:13 (shortM=row[6]+row[9], shortA=row[7]+row[10],
//                      midM=row[12], midA=row[13]).
//                   -> 2022-23..2024-25: play-by-play actions, same bucketing as
//                      reports/defense-tenth/step4-t0/prepare.mjs:28 (3pt -> long [not used here, box
//                      score is authoritative for long], area==='Mid-Range' -> mid, else -> short).
//
// All inputs are already cached on disk (data/defense-seventh/<season>/pbp/*.json,
// data/benchmark-source/*.json) -- nothing is fetched by this script.
//
//   node reports/ovr-v55-bench-prior-2025-26/extract-zones.mjs
//
// Writes reports/ovr-v55-bench-prior-2025-26/zones-raw.json:
//   { season: { playerId: {longM,longA,midM,midA,shortM,shortA,ftM,ftA,MIN,GP,heightInches,pos,name} } }
import fs from 'node:fs';

const HISTORICAL = ['2022-23', '2023-24', '2024-25'];
const posOfHeight = h => h <= 75 ? 'PG' : h <= 78 ? 'SG' : h <= 80 ? 'SF' : h <= 82 ? 'PF' : 'C';

function readJSON(path) { return JSON.parse(fs.readFileSync(path, 'utf8')); }

function resultSet(doc, name) {
  const rs = doc.data.resultSets;
  const set = name ? rs.find(s => s.name === name) : (Array.isArray(rs) ? rs[0] : rs);
  return set.rowSet.map(row => Object.fromEntries(set.headers.map((h, i) => [h, row[i]])));
}

function extract2025_26() {
  const base = readJSON('data/benchmark-source/base.json');
  const bio = readJSON('data/benchmark-source/bio.json');
  const shotsDoc = readJSON('data/benchmark-source/shots.json');
  const baseRows = resultSet(base);
  const bioByPlayer = new Map(resultSet(bio).map(r => [r.PLAYER_ID, r]));
  const shotsSet = Array.isArray(shotsDoc.data.resultSets) ? shotsDoc.data.resultSets[0] : shotsDoc.data.resultSets;
  const shotsByPlayer = new Map(shotsSet.rowSet.map(r => [r[0], {
    shortM: r[6] + r[9], shortA: r[7] + r[10], midM: r[12], midA: r[13],
  }]));
  const out = {};
  for (const r of baseRows) {
    const h = Number(bioByPlayer.get(r.PLAYER_ID)?.PLAYER_HEIGHT_INCHES);
    const s = shotsByPlayer.get(r.PLAYER_ID) ?? { shortM: 0, shortA: 0, midM: 0, midA: 0 };
    out[r.PLAYER_ID] = {
      longM: r.FG3M, longA: r.FG3A, ftM: r.FTM, ftA: r.FTA,
      midM: s.midM, midA: s.midA, shortM: s.shortM, shortA: s.shortA,
      MIN: r.MIN, GP: r.GP, heightInches: Number.isFinite(h) ? h : null,
      pos: Number.isFinite(h) ? posOfHeight(h) : null, name: r.PLAYER_NAME,
    };
  }
  return out;
}

function totalsFromLogs(logs) {
  const m = new Map();
  for (const r of logs) {
    const q = m.get(r.PLAYER_ID) ?? { playerId: r.PLAYER_ID, name: r.PLAYER_NAME, GP: 0, MIN: 0, FG3M: 0, FG3A: 0, FTM: 0, FTA: 0 };
    q.GP++; q.MIN += r.MIN ?? 0; q.FG3M += r.FG3M ?? 0; q.FG3A += r.FG3A ?? 0; q.FTM += r.FTM ?? 0; q.FTA += r.FTA ?? 0;
    m.set(r.PLAYER_ID, q);
  }
  return m;
}

function extractHistorical(season) {
  const base = `data/defense-seventh/${season}`;
  const league = readJSON(`${base}/league.json`);
  const playerGames = readJSON(`${base}/player-games.json`);
  const logs = resultSet(playerGames);
  const box = totalsFromLogs(logs);
  const metaByPlayer = new Map(league.teams.flatMap(t => t.roster).map(p => [p.playerId, p]));
  const manifest = readJSON(`${base}/manifest.json`);
  const shots = new Map();
  for (const src of manifest.sources) {
    const pbp = readJSON(src.file);
    for (const a of pbp.data.game.actions) {
      if (a.isFieldGoal !== 1 || !['2pt', '3pt'].includes(a.actionType)) continue;
      if (a.actionType === '3pt') continue; // long comes from box score (FG3M/FG3A), skip here
      const zone = a.area === 'Mid-Range' ? 'mid' : 'short';
      const q = shots.get(a.personId) ?? { midM: 0, midA: 0, shortM: 0, shortA: 0 };
      q[zone + 'A']++; if (a.shotResult === 'Made') q[zone + 'M']++;
      shots.set(a.personId, q);
    }
  }
  const out = {};
  for (const [playerId, b] of box) {
    const meta = metaByPlayer.get(playerId);
    const s = shots.get(playerId) ?? { midM: 0, midA: 0, shortM: 0, shortA: 0 };
    const h = meta ? Number(meta.heightInches) : null;
    out[playerId] = {
      longM: b.FG3M, longA: b.FG3A, ftM: b.FTM, ftA: b.FTA,
      midM: s.midM, midA: s.midA, shortM: s.shortM, shortA: s.shortA,
      MIN: b.MIN, GP: b.GP, heightInches: Number.isFinite(h) ? h : null,
      pos: Number.isFinite(h) ? posOfHeight(h) : null, name: b.name,
    };
  }
  return out;
}

const zones = { '2025-26': extract2025_26() };
for (const season of HISTORICAL) zones[season] = extractHistorical(season);

const summary = Object.fromEntries(Object.entries(zones).map(([season, players]) => [season, {
  players: Object.keys(players).length,
  longA: Object.values(players).reduce((s, p) => s + p.longA, 0),
  shortA: Object.values(players).reduce((s, p) => s + p.shortA, 0),
  midA: Object.values(players).reduce((s, p) => s + p.midA, 0),
  ftA: Object.values(players).reduce((s, p) => s + p.ftA, 0),
}]));
fs.writeFileSync('reports/ovr-v55-bench-prior-2025-26/zones-raw.json', JSON.stringify(zones));
console.log(JSON.stringify(summary, null, 1));
