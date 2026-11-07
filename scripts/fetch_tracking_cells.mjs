import fs from 'node:fs/promises';
// 球員卡追蹤格子（E-239 後續）：抓 NBA.com 追蹤量表。node fetch（python／curl 會被擋）。
// 用法：node fetch_tracking_cells.mjs <季> <輸出目錄>  → <目錄>/<檔名>.json，同名檔直接覆寫（賽中手動更新用）；失敗的表保留舊檔
const H = {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const [season, outDir] = process.argv.slice(2);
if (!season || !outDir) { console.log('用法：node fetch_tracking_cells.mjs <季> <輸出目錄>'); process.exit(2); }
const dir = new URL('file:///' + outDir.split(String.fromCharCode(92)).join('/').replace(/[/]?$/, '/'));
await fs.mkdir(dir, {recursive: true});

const ptBase = {College: '', Conference: '', Country: '', DateFrom: '', DateTo: '', Division: '', DraftPick: '', DraftYear: '', GameScope: '', GameSegment: '', Height: '', LastNGames: '0', LeagueID: '00', Location: '', Month: '0', OpponentTeamID: '0', Outcome: '', PORound: '0', PerMode: 'Totals', PlayerExperience: '', PlayerOrTeam: 'Player', PlayerPosition: '', SeasonSegment: '', SeasonType: 'Regular Season', StarterBench: '', TeamID: '0', VsConference: '', VsDivision: '', Weight: ''};
const shotBase = {CloseDefDistRange: '', DribbleRange: '', GeneralRange: '', PerMode: 'Totals', ShotDistRange: '', TouchTimeRange: '', ShotClockRange: '', SeasonType: 'Regular Season', PlayerOrTeam: 'Player', LeagueID: '00', TeamID: '0', Month: '0', OpponentTeamID: '0', Period: '0', LastNGames: '0', DateFrom: '', DateTo: '', Location: '', Outcome: '', SeasonSegment: '', VsConference: '', VsDivision: '', GameSegment: '', PORound: '0', PlayerExperience: '', PlayerPosition: '', StarterBench: '', College: '', Country: '', DraftPick: '', DraftYear: '', Height: '', Weight: '', Conference: '', Division: '', GameScope: ''};
const jobs = [];
for (const m of ['CatchShoot', 'PullUpShot', 'Drives', 'Passing', 'PaintTouch', 'PostTouch', 'Possessions'])
  jobs.push({file: `pt-${m}-${season}`, ep: 'leaguedashptstats', q: {...ptBase, Season: season, PtMeasureType: m}});
for (const p of ['PRBallHandler', 'PRRollman', 'Handoff', 'Spotup', 'Isolation', 'Cut', 'OffScreen', 'Transition', 'Postup', 'Misc', 'OffRebound'])
  jobs.push({file: `syn-${p}-${season}`, ep: 'synergyplaytypes', q: {LeagueID: '00', PerMode: 'Totals', PlayerOrTeam: 'P', SeasonType: 'Regular Season', SeasonYear: season, PlayType: p, TypeGrouping: 'offensive'}});
jobs.push({file: `hustle-${season}`, ep: 'leaguehustlestatsplayer', q: {...ptBase, Season: season}});
jobs.push({file: `shot-touch-all-${season}`, ep: 'leaguedashplayerptshot', q: {...shotBase, Season: season}});
jobs.push({file: `shot-touch-lt2-${season}`, ep: 'leaguedashplayerptshot', q: {...shotBase, TouchTimeRange: 'Touch < 2 Seconds', Season: season}});

let fail = 0;
for (const job of jobs) {
  let ok = false;
  for (let t = 1; t <= 4 && !ok; t++) {
    try {
      const r = await fetch(`https://stats.nba.com/stats/${job.ep}?` + new URLSearchParams(job.q), {...H, signal: AbortSignal.timeout(60000)});
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json();
      const rs = j.resultSets ? (Array.isArray(j.resultSets) ? j.resultSets[0] : j.resultSets) : j.resultSet;
      if (!rs.rowSet.length) throw new Error('空表');
      await fs.writeFile(new URL(job.file + '.json', dir), JSON.stringify({headers: rs.headers, rowSet: rs.rowSet}));
      console.log(job.file, rs.rowSet.length);
      ok = true;
    } catch (e) { console.log(job.file, 'try', t, String(e)); await sleep(3000 * t); }
  }
  if (!ok) fail++;
  await sleep(700);
}
await fs.writeFile(new URL('fetched.json', dir), JSON.stringify({season, fetchedAt: new Date().toISOString(), jobs: jobs.length, fail}));
console.log('DONE jobs', jobs.length, 'fail', fail);
