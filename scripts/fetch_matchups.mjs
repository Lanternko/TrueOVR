import fs from 'node:fs/promises';

// E-110／R-066：抓每場的防守對位（boxscorematchupsv3）與 hustle（boxscorehustlev2），只存用得到的欄位。
// 用法：node scripts/fetch_matchups.mjs [2025-26|2026-27]（預設 2025-26）；已存在的場次跳過，可中斷續抓。
// 場次取自該季 player-games；每日發布（daily_inseason_update.py）會順便跑新賽季。
const season = process.argv[2] || '2025-26';
const src = new URL(season === '2025-26' ? '../data/season-source/player-games.json'
  : `../data/season-source-${season}/player-games.json`, import.meta.url);
const dir = new URL(`../data/matchup-source/${season}/`, import.meta.url);
await fs.mkdir(dir, {recursive:true});
const set = JSON.parse(await fs.readFile(src, 'utf8')).data.resultSets[0];
const gi = set.headers.indexOf('GAME_ID');
const ids = [...new Set(set.rowSet.map(r => r[gi]))].sort();
const H = {headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const MU = ['partialPossessions','playerPoints','matchupTurnovers','matchupAssists','matchupPotentialAssists',
  'matchupFieldGoalsMade','matchupFieldGoalsAttempted','matchupThreePointersMade','matchupThreePointersAttempted',
  'matchupFreeThrowsAttempted','shootingFouls','helpBlocks','switchesOn'];
const HU = ['minutes','contestedShots','deflections','chargesDrawn','looseBallsRecoveredTotal','screenAssists'];

async function get(url) {
  for (let t = 1; ; t++) {
    try {
      const r = await fetch(url, {...H, signal:AbortSignal.timeout(30000)});
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.json();
    } catch (e) {
      if (t >= 3) throw e;
      await sleep(5000 * t);
    }
  }
}
const pick = (o, ks) => Object.fromEntries(ks.map(k => [k, o[k]]));
const teams = b => ['homeTeam','awayTeam'].map(s => b[s]);

const failures = [];
let fetched = 0, skipped = 0, streak = 0;
for (const id of ids) {
  const out = new URL(`${id}.json`, dir);
  try { await fs.access(out); skipped++; continue; } catch {}
  try {
    const m = await get('https://stats.nba.com/stats/boxscorematchupsv3?GameID=' + id);
    await sleep(1200);
    const h = await get('https://stats.nba.com/stats/boxscorehustlev2?GameID=' + id);
    await sleep(1200);
    const matchups = teams(m.boxScoreMatchups).flatMap(t => t.players.flatMap(o => o.matchups.map(d =>
      ({teamId:t.teamId, off:o.personId, def:d.personId, ...pick(d.statistics, MU)}))));
    const hustle = teams(h.boxScoreHustle).flatMap(t => t.players.map(p =>
      ({teamId:t.teamId, personId:p.personId, ...pick(p.statistics, HU)})));
    if (!matchups.length || !hustle.length) throw new Error('empty');
    await fs.writeFile(out, JSON.stringify({gameId:id, fetchedAt:new Date().toISOString(), matchups, hustle}));
    fetched++; streak = 0;
    if (fetched % 50 === 0) console.log(`fetched ${fetched}, skipped ${skipped}, failed ${failures.length}`);
  } catch (e) {
    failures.push({gameId:id, error:String(e.message || e)});
    if (++streak > 20) { console.log('STOP: 連續失敗超過 20 場'); break; }
  }
}
await fs.writeFile(new URL('fetch-failures.json', dir), JSON.stringify(failures, null, 1));
console.log(`DONE games ${ids.length}, fetched ${fetched}, skipped ${skipped}, failed ${failures.length}`);
