import fs from 'node:fs/promises';

// 新秀賽中防守（2026-10-30 使用者：一有數據就更新）：抓整季累計的防守追蹤表，供 live/rookie_defense.py 算 onBall／help。
// 端點與參數同 reports/defense-tenth/step4-t2/fetch.mjs（TeamID 0、PerMode Totals）；整季累計每天會變，所以每次重抓覆寫。
// 用法：node scripts/fetch_defense_tracking.mjs [2026-27] → data/defense-seventh/<季>/tracking/{rim,three,matchups,hustle,advanced}.json
const season = process.argv[2] || '2026-27';
const dir = new URL(`../data/defense-seventh/${season}/tracking/`, import.meta.url);
await fs.mkdir(dir, {recursive:true});
const H = {headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/'}};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const common = {LeagueID:'00',SeasonType:'Regular Season',PerMode:'Totals',LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',
  PlusMinus:'N',Rank:'N',Period:'0',DateFrom:'',DateTo:'',Conference:'',Division:'',GameSegment:'',Location:'',Outcome:'',PORound:'',
  PlayerExperience:'',PlayerPosition:'',SeasonSegment:'',ShotClockRange:'',StarterBench:'',VsConference:'',VsDivision:'',College:'',
  Country:'',DraftPick:'',DraftYear:'',Height:'',Weight:'',Season:season,TeamID:'0'};
const jobs = {
  rim: ['leaguedashptdefend', {...common, MeasureType:'Base', DefenseCategory:'Less Than 6Ft'}],
  three: ['leaguedashptdefend', {...common, MeasureType:'Base', DefenseCategory:'3 Pointers'}],
  hustle: ['leaguehustlestatsplayer', {...common, MeasureType:'Base'}],
  advanced: ['leaguedashplayerstats', {...common, MeasureType:'Advanced'}],
  matchups: ['leagueseasonmatchups', {LeagueID:'00',Season:season,SeasonType:'Regular Season',PerMode:'Totals',DefPlayerID:'',DefTeamID:'',OffPlayerID:'',OffTeamID:''}],
};

async function get(url) {
  for (let t = 1; ; t++) {
    try {
      const r = await fetch(url, {...H, signal:AbortSignal.timeout(60000)});
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = await r.json();
      const s = Array.isArray(d.resultSets) ? d.resultSets[0] : d.resultSets;
      if (!s?.rowSet?.length) throw new Error('Empty dataset');
      return d;
    } catch (e) {
      if (t >= 3) throw e;
      await sleep(5000 * t);
    }
  }
}

const out = {season, rows:{}, failures:[]};
for (const [kind, [ep, params]] of Object.entries(jobs)) {
  const url = `https://stats.nba.com/stats/${ep}?` + new URLSearchParams(params);
  try {
    const data = await get(url);
    const s = Array.isArray(data.resultSets) ? data.resultSets[0] : data.resultSets;
    // 先寫暫存再改名：抓到一半失敗不會留下半新半舊的組合
    await fs.writeFile(new URL(`${kind}.json.tmp`, dir), JSON.stringify({url, season, fetchedAt:new Date().toISOString(), data}) + '\n');
    out.rows[kind] = s.rowSet.length;
  } catch (e) {
    out.failures.push({kind, error:String(e)});
  }
}
if (!out.failures.length)
  for (const kind of Object.keys(jobs)) await fs.rename(new URL(`${kind}.json.tmp`, dir), new URL(`${kind}.json`, dir));
console.log(JSON.stringify(out));
process.exit(out.failures.length ? 1 : 0);
