import fs from 'node:fs/promises';

// inseason 0.2.12（R-139、E-203）：每天抓 NBA.com tracking 持球時間（leaguedashptstats，PtMeasureType=Possessions，整季累計），供 live/tov_live.py 算賽中 tovSkill 的持球分鐘。
// 參數同 reports/handle-E069/fetch-tracking.mjs（DateFrom／DateTo 空＝整季）；寫法同 scripts/fetch_gravity.mjs。
// 用法：node scripts/fetch_possessions.mjs [2026-27] → data/defense-seventh/<季>/possessions.json（{url, season, fetchedAt, data}，data 為 NBA.com 原樣 resultSets）
// 失敗（HTTP 錯誤、空表、缺欄位）exit 1，不覆寫上次成功的檔。
const season = process.argv[2] || '2026-27';
const dir = new URL(`../data/defense-seventh/${season}/`, import.meta.url);
await fs.mkdir(dir, {recursive: true});
const params = {LeagueID: '00', Season: season, SeasonType: 'Regular Season', PerMode: 'Totals', PlayerOrTeam: 'Player', PtMeasureType: 'Possessions', TeamID: '0', LastNGames: '0', Month: '0', OpponentTeamID: '0', PaceAdjust: 'N', PlusMinus: 'N', Rank: 'N', Period: '0', DateFrom: '', DateTo: '', Conference: '', Division: '', GameSegment: '', Location: '', Outcome: '', PORound: '', PlayerExperience: '', PlayerPosition: '', SeasonSegment: '', StarterBench: '', VsConference: '', VsDivision: '', College: '', Country: '', DraftPick: '', DraftYear: '', Height: '', Weight: ''};
const url = 'https://stats.nba.com/stats/leaguedashptstats?' + new URLSearchParams(params);
const H = {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const NEED = ['PLAYER_ID', 'TIME_OF_POSS', 'TOUCHES'];
let data, err;
for (let t = 1; t <= 3; t++) {
  try {
    const r = await fetch(url, {...H, signal: AbortSignal.timeout(60000)});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    const rs = Array.isArray(j.resultSets) ? j.resultSets[0] : j.resultSets;
    if (!rs?.rowSet?.length) throw new Error('空表');
    const miss = NEED.filter(k => !rs.headers.includes(k));
    if (miss.length) throw new Error('缺欄位 ' + miss.join(','));
    data = j;
    break;
  } catch (e) {
    err = e;
    await sleep(5000 * t);
  }
}
if (!data) {
  console.log(JSON.stringify({season, ok: false, error: String(err)}));
  process.exit(1);
}
const rs0 = Array.isArray(data.resultSets) ? data.resultSets[0] : data.resultSets;
const tmp = new URL('possessions.json.tmp', dir);
await fs.writeFile(tmp, JSON.stringify({url, season, fetchedAt: new Date().toISOString(), data}) + '\n');
await fs.rename(tmp, new URL('possessions.json', dir));
console.log(JSON.stringify({season, ok: true, n: rs0.rowSet.length}));
