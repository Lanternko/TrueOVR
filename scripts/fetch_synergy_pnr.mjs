import fs from 'node:fs/promises';

// inseason 0.2.13（E-258）：每天抓 NBA.com Synergy 擋拆持球（PRBallHandler，整季累計，進攻端），供 live/pnr_live.py 算賽中 pnr。
// 端點與參數同 E-239 抓過去季的 synergyplaytypes（PerMode=Totals、PlayerOrTeam=P、例行賽）。
// 用法：node scripts/fetch_synergy_pnr.mjs [2026-27] → data/defense-seventh/<季>/synergy-pnr.json（{url, season, fetchedAt, resultSets}）
// 失敗（HTTP 錯誤、空表、缺欄位）exit 1，不覆寫上次成功的檔。
const season = process.argv[2] || '2026-27';
const dir = new URL(`../data/defense-seventh/${season}/`, import.meta.url);
await fs.mkdir(dir, {recursive: true});
const q = new URLSearchParams({LeagueID: '00', PerMode: 'Totals', PlayerOrTeam: 'P', SeasonType: 'Regular Season',
  SeasonYear: season, PlayType: 'PRBallHandler', TypeGrouping: 'offensive'});
const url = `https://stats.nba.com/stats/synergyplaytypes?${q}`;
const H = {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const NEED = ['PLAYER_ID', 'TEAM_ID', 'POSS', 'PTS', 'SCORE_POSS_PCT'];
let rs, err;
for (let t = 1; t <= 3; t++) {
  try {
    const r = await fetch(url, {...H, signal: AbortSignal.timeout(60000)});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    const s = (j.resultSets || [])[0];
    if (!s || !s.rowSet || !s.rowSet.length) throw new Error('空表');
    const miss = NEED.filter(k => !s.headers.includes(k));
    if (miss.length) throw new Error('缺欄位 ' + miss.join(','));
    rs = [{name: s.name, headers: s.headers, rowSet: s.rowSet}];
    break;
  } catch (e) {
    err = e;
    await sleep(5000 * t);
  }
}
if (!rs) {
  console.log(JSON.stringify({season, ok: false, error: String(err)}));
  process.exit(1);
}
const tmp = new URL('synergy-pnr.json.tmp', dir);
await fs.writeFile(tmp, JSON.stringify({url, season, fetchedAt: new Date().toISOString(), resultSets: rs}) + '\n');
await fs.rename(tmp, new URL('synergy-pnr.json', dir));
console.log(JSON.stringify({season, ok: true, n: rs[0].rowSet.length}));
