import fs from 'node:fs/promises';

// ovr_history 歷史日去洩漏（2026-11-08）：抓 NBA.com「截至某天」的季累計表（DateTo＝那天），讓逐日重算不會讀到之後的比賽。
// 表與參數同 scripts/fetch_defense_tracking.mjs（rim／three／hustle／advanced）、fetch_possessions.mjs（Possessions）、
// 本季 bio.json（leaguedashplayerbiostats）；只多帶 DateFrom=''、DateTo=<那天>。檔案格式與原檔相同（{url, season, fetchedAt, data}），模型照原路徑讀。
// 對位 matchups（leagueseasonmatchups 不吃日期）、Synergy 擋拆、引力不在這裡：前者由 ovr_history 從逐場對位檔加總，後兩者只用當天存下的快照。
// 用法：node scripts/fetch_asof.mjs <季> <YYYY-MM-DD> <輸出夾> → <輸出夾>/{tracking/{rim,three,hustle,advanced}.json, possessions.json, bio.json}
// 全部成功才改名寫入；失敗 exit 1、不留半套。
const [season, day, outDir] = process.argv.slice(2);
if (!season || !/^\d{4}-\d{2}-\d{2}$/.test(day || '') || !outDir) {
  console.error('用法：node scripts/fetch_asof.mjs <季> <YYYY-MM-DD> <輸出夾>');
  process.exit(2);
}
const [y, m, d] = day.split('-');
const dateTo = `${m}/${d}/${y}`;
const H = {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const common = {LeagueID:'00',Season:season,SeasonType:'Regular Season',PerMode:'Totals',PlayerOrTeam:'Player',TeamID:'0',LastNGames:'0',Month:'0',
  OpponentTeamID:'0',PaceAdjust:'N',PlusMinus:'N',Rank:'N',Period:'0',DateFrom:'',DateTo:dateTo,Conference:'',Division:'',GameSegment:'',Location:'',
  Outcome:'',PORound:'',PlayerExperience:'',PlayerPosition:'',SeasonSegment:'',StarterBench:'',VsConference:'',VsDivision:'',College:'',Country:'',
  DraftPick:'',DraftYear:'',Height:'',Weight:''};
const jobs = {
  'tracking/rim': ['leaguedashptdefend', {...common, MeasureType:'Base', DefenseCategory:'Less Than 6Ft'}],
  'tracking/three': ['leaguedashptdefend', {...common, MeasureType:'Base', DefenseCategory:'3 Pointers'}],
  'tracking/hustle': ['leaguehustlestatsplayer', {...common, MeasureType:'Base'}],
  'tracking/advanced': ['leaguedashplayerstats', {...common, MeasureType:'Advanced'}],
  'possessions': ['leaguedashptstats', {...common, PtMeasureType:'Possessions'}],
  'bio': ['leaguedashplayerbiostats', {LeagueID:'00',Season:season,SeasonType:'Regular Season',PerMode:'Totals',MeasureType:'Base',TeamID:'0',
    LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',PlusMinus:'N',Rank:'N',Period:'0',DateFrom:'',DateTo:dateTo}],
};

async function get(url) {
  for (let t = 1; ; t++) {
    try {
      const r = await fetch(url, {...H, signal: AbortSignal.timeout(60000)});
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json();
      const s = Array.isArray(j.resultSets) ? j.resultSets[0] : j.resultSets;
      if (!s?.rowSet?.length) throw new Error('空表');
      return j;
    } catch (e) {
      if (t >= 3) throw e;
      await sleep(5000 * t);
    }
  }
}

const dir = outDir.replace(/[\\/]+$/, '');
await fs.mkdir(`${dir}/tracking`, {recursive: true});
const out = {season, day, rows: {}, failures: []};
for (const [name, [ep, params]] of Object.entries(jobs)) {
  const url = `https://stats.nba.com/stats/${ep}?` + new URLSearchParams(params);
  try {
    const data = await get(url);
    const s = Array.isArray(data.resultSets) ? data.resultSets[0] : data.resultSets;
    await fs.writeFile(`${dir}/${name}.json.tmp`, JSON.stringify({url, season, fetchedAt: new Date().toISOString(), data}) + '\n');
    out.rows[name] = s.rowSet.length;
  } catch (e) {
    out.failures.push({name, error: String(e)});
  }
}
for (const name of Object.keys(jobs)) {
  if (out.failures.length) await fs.rm(`${dir}/${name}.json.tmp`, {force: true});
  else await fs.rename(`${dir}/${name}.json.tmp`, `${dir}/${name}.json`);
}
console.log(JSON.stringify(out));
process.exit(out.failures.length ? 1 : 0);
