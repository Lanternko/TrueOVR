// 2026-27 各比賽日前一天為止的球隊季累積出手位置（leaguedashteamshotlocations，DateTo）。node fetch_loc.mjs <日期…>
import fs from 'node:fs/promises';
const H = {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}};
await fs.mkdir('data/loc', {recursive: true});
for (const d of process.argv.slice(2)) {
  const q = {College:'',Conference:'',Country:'',DateFrom:'',DateTo:d,DistanceRange:'By Zone',Division:'',DraftPick:'',DraftYear:'',GameScope:'',GameSegment:'',Height:'',LastNGames:'0',LeagueID:'00',Location:'',MeasureType:'Base',Month:'0',OpponentTeamID:'0',Outcome:'',PORound:'0',PaceAdjust:'N',PerMode:'Totals',Period:'0',PlayerExperience:'',PlayerPosition:'',PlusMinus:'N',Rank:'N',Season:'2026-27',SeasonSegment:'',SeasonType:'Regular Season',ShotClockRange:'',StarterBench:'',TeamID:'0',VsConference:'',VsDivision:'',Weight:''};
  for (let t = 0; t < 3; t++) {
    try {
      const r = await fetch('https://stats.nba.com/stats/leaguedashteamshotlocations?' + new URLSearchParams(q), {...H, signal: AbortSignal.timeout(60000)});
      if (!r.ok) throw new Error(r.status);
      const j = await r.json(); const rs = j.resultSets;
      await fs.writeFile(`data/loc/${d}.json`, JSON.stringify(rs)); console.log('ok', d, rs.rowSet.length); break;
    } catch (e) { console.log('retry', d, String(e)); await new Promise(r => setTimeout(r, 3000)); }
  }
  await new Promise(r => setTimeout(r, 700));
}
