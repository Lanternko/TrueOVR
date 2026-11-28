// POR 進攻診斷：本季球隊／球員 Synergy 戰術＋球隊追蹤＋四因子。node fetch.mjs
import fs from 'node:fs/promises';
const H = {headers: {'User-Agent': 'Mozilla/5.0', Referer: 'https://www.nba.com/', Origin: 'https://www.nba.com'}};
const S = '2026-27';
const PT = ['Isolation','Transition','PRBallHandler','PRRollman','Postup','Spotup','Handoff','Cut','OffScreen','OffRebound','Misc'];
const ptBase = {College:'',Conference:'',Country:'',DateFrom:'',DateTo:'',Division:'',DraftPick:'',DraftYear:'',GameScope:'',GameSegment:'',Height:'',LastNGames:'0',LeagueID:'00',Location:'',Month:'0',OpponentTeamID:'0',Outcome:'',PORound:'0',PerMode:'Totals',PlayerExperience:'',PlayerPosition:'',SeasonSegment:'',SeasonType:'Regular Season',StarterBench:'',TeamID:'0',VsConference:'',VsDivision:'',Weight:'',Season:S};
const jobs = [];
for (const p of PT) for (const who of ['T','P'])
  jobs.push({file:`syn-${who}-${p}`, ep:'synergyplaytypes', q:{LeagueID:'00',PerMode:'Totals',PlayerOrTeam:who,SeasonType:'Regular Season',SeasonYear:S,PlayType:p,TypeGrouping:'offensive'}});
for (const m of ['CatchShoot','PullUpShot','Drives','Passing','PaintTouch','PostTouch','ElbowTouch','Possessions','SpeedDistance'])
  jobs.push({file:`ptT-${m}`, ep:'leaguedashptstats', q:{...ptBase, PlayerOrTeam:'Team', PtMeasureType:m}});
for (const mt of ['Four Factors','Advanced','Base','Misc','Scoring'])
  jobs.push({file:`team-${mt.replace(' ','')}`, ep:'leaguedashteamstats', q:{...ptBase, MeasureType:mt, PerMode:'PerGame', PaceAdjust:'N', PlusMinus:'N', Rank:'N', Period:'0', ShotClockRange:'', TwoWay:'0', ISTRound:''}});
for (const j of jobs) {
  for (let t = 0; t < 3; t++) {
    try {
      const r = await fetch(`https://stats.nba.com/stats/${j.ep}?` + new URLSearchParams(j.q), {...H, signal: AbortSignal.timeout(60000)});
      if (!r.ok) throw new Error(r.status);
      const d = await r.json(); const rs = (d.resultSets || [d.resultSet])[0];
      await fs.writeFile(`data/${j.file}.json`, JSON.stringify({headers: rs.headers, rowSet: rs.rowSet}));
      console.log('ok', j.file, rs.rowSet.length); break;
    } catch (e) { console.log('retry', j.file, String(e)); await new Promise(r => setTimeout(r, 3000)); }
  }
  await new Promise(r => setTimeout(r, 600));
}
