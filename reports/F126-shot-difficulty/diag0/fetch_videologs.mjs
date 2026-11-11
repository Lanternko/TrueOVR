// F-126 diag0：逐場逐人抓 shotqualityvideologs，存精簡快取 raw/<gameId>_<pid>.json（可中斷續抓）。
// 用法：node fetch_videologs.mjs [limit]   （limit＝只抓前 N 筆，試通用；RETRY_ERR=1 重抓先前存成 error 的）
// 球員池：card-0.2.10 ranking MIN>=900，name→playerId 照 F-125 noise.py（live/2026-10-31 ranking，缺的用 player-games 的名字補）。
// 場次：data/season-source/player-games.json（2025-26 例行賽 leaguegamelog）。
// 註：Python requests／curl 會被 stats.nba.com 擋（逾時），Node fetch 可以，所以用 Node。
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const rawDir = path.join(here, 'raw'); fs.mkdirSync(rawDir, {recursive: true});
const limit = process.argv[2] ? +process.argv[2] : Infinity;
const retryErr = process.env.RETRY_ERR === '1';
const csv = p => { const [h, ...ls] = fs.readFileSync(path.join(root, p), 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/);
  const H = h.split(','); return ls.map(l => { const c = []; let cur = '', q = false;
    for (const ch of l) { if (ch === '"') q = !q; else if (ch === ',' && !q) { c.push(cur); cur = ''; } else cur += ch; } c.push(cur);
    return Object.fromEntries(H.map((k, i) => [k, c[i]])); }); };
const pool = csv('reports/card-0.2.10/ranking.csv').filter(x => +x.MIN >= 900);
const ins = Object.fromEntries(csv('reports/ovr-inseason-2026-27/live/2026-10-31/ranking.csv').map(x => [x.name, x.playerId]));
const pg = JSON.parse(fs.readFileSync(path.join(root, 'data/season-source/player-games.json'), 'utf8')).data.resultSets[0];
const ix = Object.fromEntries(pg.headers.map((h, i) => [h, i]));
const byName = {}; for (const r of pg.rowSet) byName[r[ix.PLAYER_NAME]] = String(r[ix.PLAYER_ID]);
const pid = {}; for (const x of pool) pid[x.name] = ins[x.name] || byName[x.name];
fs.writeFileSync(path.join(here, 'pool.csv'), 'name,playerId,source\n' + pool.map(x => `"${x.name}",${pid[x.name] || ''},${ins[x.name] ? 'live-ranking' : 'player-games-name'}`).join('\n') + '\n');
const ps = new Set(Object.values(pid).filter(Boolean));
const jobs = pg.rowSet.filter(r => ps.has(String(r[ix.PLAYER_ID])) && +r[ix.FGA] > 0)  // FGA=0 的場次 API 回 500，不抓
  .map(r => [r[ix.GAME_ID], String(r[ix.PLAYER_ID])]).sort();
console.log('pool', pool.length, 'unmapped', pool.filter(x => !pid[x.name]).length, 'jobs', jobs.length);
const H = {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'};
const sleep = ms => new Promise(r => setTimeout(r, ms));
let last = 0, done = 0, skipped = 0, fetched = 0, errs = 0;
async function get(url) {
  let status = 0;
  for (let t = 1; t <= 4; t++) {
    if (status === 500 && t > 2) break;
    const wait = 650 - (Date.now() - last); if (wait > 0) await sleep(wait); last = Date.now();
    try {
      const r = await fetch(url, {headers: H, signal: AbortSignal.timeout(30000)});
      status = r.status;
      if (r.ok) return {status, json: await r.json()};
      if (r.status === 404) break;
    } catch (e) { status = -1; }
    await sleep(3000 * t * t);
  }
  return {status};
}
for (const [gid, p] of jobs) {
  if (fetched + errs >= limit) break;
  const f = path.join(rawDir, `${gid}_${p}.json`);
  if (fs.existsSync(f)) {
    if (!retryErr || !JSON.parse(fs.readFileSync(f, 'utf8')).error) { skipped++; continue; }
  }
  const {status, json} = await get(`https://stats.nba.com/stats/shotqualityvideologs?GameID=${gid}&PlayerID=${p}`);
  if (!json) { errs++; fs.writeFileSync(f, JSON.stringify({gameId: gid, playerId: p, error: status})); }
  else {
    fetched++;
    const o = {gameId: gid, playerId: p};
    for (const k of ['shots', 'avgShotQuality', 'fgPct', 'fgPctAboveExpected', 'avgMadeShotQuality', 'avgMissShotQuality', 'avgDefenderBallDistance']) o[k] = json[k];
    o.shotList = (json.shotList || []).map(s => ({eventNum: s.eventNum, success: s.success, shotType: s.shotType, shotQuality: s.shotQuality}));
    fs.writeFileSync(f, JSON.stringify(o));
  }
  if ((fetched + errs) % 500 === 0) console.log(new Date().toISOString(), 'fetched', fetched, 'errs', errs, 'skipped', skipped, 'of', jobs.length);
}
console.log('END fetched', fetched, 'errs', errs, 'skipped', skipped, 'of', jobs.length);
if (limit === Infinity) fs.writeFileSync(path.join(here, 'FETCH_DONE'), new Date().toISOString());
