// 進行中的例行賽（NBA.com liveData）→ data/season-source-<季>/live-games.json（賽程檢視 build_games_data.py 用，每次整份覆寫）。
// 用法：node scripts/fetch_live_games.mjs 2026-27
// todaysScoreboard 取 gameStatus==2 且 gameId 開頭 002 的場次，再抓各場 boxscore 的即時球員數據。沒有進行中比賽寫空清單（不沿用舊檔，避免已結束的比賽卡在「進行中」）。
// scoreboard 抓不到或解析失敗 exit 1 且不覆寫舊檔；單場 boxscore 抓不到只丟警告，該場只帶比分、沒有 box。curl／Python 會被 Akamai 擋（403），node fetch 可以。
import fs from 'node:fs';
import path from 'node:path';
const season = process.argv[2] || '2026-27';
const out = path.join('data', `season-source-${season}`, 'live-games.json');
const H = {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'};
async function get(url) {
  const r = await fetch(url, {headers: H, signal: AbortSignal.timeout(30000)});
  if (!r.ok) throw new Error(url + ' HTTP ' + r.status);
  return r.json();
}
// "PT05M21.00S" → "5:21"；比賽沒在計時（節間、中場）回 ''
function clock(s) {
  const m = /^PT(\d+)M(\d+)(?:\.\d+)?S$/.exec(s || '');
  if (!m || (+m[1] === 0 && +m[2] === 0)) return '';
  return `${+m[1]}:${m[2].padStart(2, '0')}`;
}
function periodLabel(p) { return p <= 4 ? `Q${p}` : `OT${p - 4}`; }
const STAT = {pts: 'points', reb: 'reboundsTotal', oreb: 'reboundsOffensive', dreb: 'reboundsDefensive', ast: 'assists', stl: 'steals', blk: 'blocks', tov: 'turnovers', pf: 'foulsPersonal',
  fgm: 'fieldGoalsMade', fga: 'fieldGoalsAttempted', tpm: 'threePointersMade', tpa: 'threePointersAttempted', ftm: 'freeThrowsMade', fta: 'freeThrowsAttempted'};
function pick(st) { const o = {}; for (const [k, v] of Object.entries(STAT)) if (st && st[v] != null) o[k] = st[v]; return o; }
function player(p) {
  const st = p.statistics || {}, mm = /^PT(\d+)M(\d+)/.exec(st.minutes || '');
  const o = {pid: p.personId, name: p.name, starter: p.starter === '1', played: p.played === '1', min: mm ? `${+mm[1]}:${mm[2]}` : '0:00', ...pick(st)};
  if (st.plusMinusPoints != null) o.pm = st.plusMinusPoints;
  return o;
}
const sb = (await get('https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json')).scoreboard;
if (!sb || !Array.isArray(sb.games)) { console.error('scoreboard 格式異常'); process.exit(1); }
const games = [];
for (const g of sb.games) {
  if (g.gameStatus !== 2 || !String(g.gameId).startsWith('002')) continue;
  const clk = clock(g.gameClock), label = periodLabel(g.period);
  const row = {gameId: g.gameId, period: g.period, gameClock: clk, statusText: String(g.gameStatusText || '').trim(),
    status: clk ? `${label} ${clk}` : (String(g.gameStatusText || '').trim() || label),
    home: {teamId: g.homeTeam.teamId, tri: g.homeTeam.teamTricode, score: g.homeTeam.score},
    away: {teamId: g.awayTeam.teamId, tri: g.awayTeam.teamTricode, score: g.awayTeam.score}};
  try {
    const b = (await get(`https://cdn.nba.com/static/json/liveData/boxscore/boxscore_${g.gameId}.json`)).game;
    for (const k of ['home', 'away']) {
      const t = b[k + 'Team'];
      row[k].score = t.score;
      row[k].players = (t.players || []).map(player);
      row[k].team = pick(t.statistics);
    }
  } catch (e) { console.error(`WARNING boxscore ${g.gameId}：${e.message}`); }
  games.push(row);
}
fs.mkdirSync(path.dirname(out), {recursive: true});
fs.writeFileSync(out, JSON.stringify({fetchedAt: new Date().toISOString(), source: 'cdn.nba.com liveData', gameDate: sb.gameDate, games}));
console.log(`live：${games.length} 場進行中 → ${out}`);
