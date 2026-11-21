import fs from 'node:fs/promises';
const urlFor=(endpoint,season,type,measure='Base',team=0)=>'https://stats.nba.com/stats/'+endpoint+'?'+new URLSearchParams({
  LeagueID:'00',Season:season,SeasonType:type,PerMode:'Totals',MeasureType:measure,TeamID:String(team),
  LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',PlusMinus:'N',Rank:'N',Period:'0'});
async function get(url){
  const r=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/'},signal:AbortSignal.timeout(30000)});
  if(!r.ok)throw new Error(`NBA HTTP ${r.status}`);
  const data=await r.json(),s=data.resultSets?.[0];
  if(!s?.rowSet?.length)throw new Error('No NBA rows');
  return {source:{url,fetchedAt:new Date().toISOString()},rows:s.rowSet.map(row=>Object.fromEntries(s.headers.map((h,i)=>[h,row[i]])))};
}
const contexts=[];
for(const [season,type] of [['2001-02','Regular Season'],['2015-16','Regular Season'],['2016-17','Regular Season'],['2025-26','Regular Season'],['2025-26','Playoffs']]){
  const [base,advanced]=await Promise.all([get(urlFor('leaguedashteamstats',season,type)),get(urlFor('leaguedashteamstats',season,type,'Advanced'))]);
  const sum=k=>base.rows.reduce((s,r)=>s+r[k],0);
  const advancedSum=k=>advanced.rows.reduce((s,r)=>s+r[k],0);
  const n=sum('GP'),orb=sum('OREB'),drb=sum('DREB');
  const entry={season,type,teams:base.rows.length,teamGames:n,
    orebPerGame:orb/n,drebPerGame:drb/n,orebShare:orb/(orb+drb),
    pointsPerGame:sum('PTS')/n,fgPct:sum('FGM')/sum('FGA'),
    twoPct:(sum('FGM')-sum('FG3M'))/(sum('FGA')-sum('FG3A')),
    threePct:sum('FG3M')/sum('FG3A'),ftPct:sum('FTM')/sum('FTA'),
    tovPerGame:sum('TOV')/n,stlPerGame:sum('STL')/n,blkPerGame:sum('BLK')/n,
    pointsPer100:sum('PTS')/advancedSum('POSS')*100,
    pace:advancedSum('POSS')/sum('MIN')*48,
    sources:{base:base.source,advanced:advanced.source},
    teamTotals:base.rows.map(r=>({id:r.TEAM_ID,name:r.TEAM_NAME,games:r.GP,minutes:r.MIN,oreb:r.OREB,dreb:r.DREB,pts:r.PTS,fta:r.FTA,ftm:r.FTM,fga:r.FGA,fgm:r.FGM,tov:r.TOV}))};
  contexts.push(entry);console.log(`${season} ${type}: ORB ${entry.orebPerGame.toFixed(2)} DRB ${entry.drebPerGame.toFixed(2)} share ${(entry.orebShare*100).toFixed(2)}%, PPG ${entry.pointsPerGame.toFixed(1)}, pace ${entry.pace.toFixed(2)}`);
}
const [playoffs,warriors]=await Promise.all([
 get(urlFor('leaguedashplayerstats','2025-26','Playoffs')),
 get(urlFor('leaguedashplayerstats','2016-17','Playoffs','Base',1610612744))]);
const players=(rows)=>rows.map(r=>({name:r.PLAYER_NAME,games:r.GP,mpg:r.MIN/r.GP,ppg:r.PTS/r.GP}));
const result={schemaVersion:1,contexts,
 playoffMinutes:{source:playoffs.source,selection:'Top 10 MPG with >=5 playoff games; not all starters',players:players(playoffs.rows.filter(r=>r.GP>=5)).sort((a,b)=>b.mpg-a.mpg).slice(0,10)},
 warriorsPlayoffMinutes:{source:warriors.source,players:players(warriors.rows)}};
await fs.writeFile(new URL('../data/league-context.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
console.log('Saved data/league-context.json');
