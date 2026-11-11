// 2026-27 例行賽賽程（NBA.com CDN scheduleLeagueV2）→ data/season-source-<季>/schedule.json（E-208 第二階段：球隊評分的剩餘賽程）。
// 用法：node scripts/fetch_schedule.mjs 2026-27
// 失敗（HTTP 非 200、解析失敗、場數不合理）exit 1 且不覆寫舊檔；呼叫端沿用上次的檔。curl／Python 會被 Akamai 擋（403），node fetch 可以。
import fs from 'node:fs';
import path from 'node:path';
const season = process.argv[2] || '2026-27';
const out = path.join('data', `season-source-${season}`, 'schedule.json');
const r = await fetch('https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json', {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/'}, signal: AbortSignal.timeout(60000)});
if (!r.ok) { console.error('schedule HTTP ' + r.status); process.exit(1); }
const d = await r.json();
const games = [];
const tipoff = {};   // gameId → 開賽 UTC（賽程檢視顯示 UTC+8 用；另放一個 map 是為了不動 games 的四欄格式，team_ratings_daily 照 4 欄解開）
for (const day of d.leagueSchedule.gameDates) for (const g of day.games) {
  if (!String(g.gameId).startsWith('002')) continue;   // 例行賽（001 季前、004 季後、005 附加賽、006 盃賽決賽）
  if (!g.homeTeam.teamId || !g.awayTeam.teamId) continue;   // 盃賽淘汰賽尚未定對手（teamId 0），不是 82 場裡的場次
  if (g.gameDateTimeUTC) tipoff[g.gameId] = g.gameDateTimeUTC;
  games.push([g.gameId, String(g.gameDateEst).slice(0, 10), g.homeTeam.teamId, g.awayTeam.teamId]);
}
if (games.length < 1000) { console.error('schedule 場數異常：' + games.length); process.exit(1); }
fs.mkdirSync(path.dirname(out), {recursive: true});
fs.writeFileSync(out, JSON.stringify({fetchedAt: new Date().toISOString(), source: 'cdn.nba.com scheduleLeagueV2', season: d.leagueSchedule.seasonYear, games, tipoff}));
console.log(`schedule：${games.length} 場例行賽 → ${out}`);
