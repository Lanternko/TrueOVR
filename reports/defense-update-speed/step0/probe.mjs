// 第 0 步-2：試抓 2024-25 截至某日的累計防守追蹤表（DateTo），並比對季總計，確認端點真的照日期截。
import fs from 'node:fs/promises';
const H = {headers:{'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/'}};
const season='2024-25', dateTo=process.argv[2]||'11/15/2024';
const common = (dt)=>({LeagueID:'00',SeasonType:'Regular Season',PerMode:'Totals',LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',
  PlusMinus:'N',Rank:'N',Period:'0',DateFrom:'',DateTo:dt,Conference:'',Division:'',GameSegment:'',Location:'',Outcome:'',PORound:'',
  PlayerExperience:'',PlayerPosition:'',SeasonSegment:'',ShotClockRange:'',StarterBench:'',VsConference:'',VsDivision:'',College:'',
  Country:'',DraftPick:'',DraftYear:'',Height:'',Weight:'',Season:season,TeamID:'0'});
const jobs = dt=>({
  rim: ['leaguedashptdefend', {...common(dt), MeasureType:'Base', DefenseCategory:'Less Than 6Ft'}],
  three: ['leaguedashptdefend', {...common(dt), MeasureType:'Base', DefenseCategory:'3 Pointers'}],
  hustle: ['leaguehustlestatsplayer', {...common(dt), MeasureType:'Base'}],
  advanced: ['leaguedashplayerstats', {...common(dt), MeasureType:'Advanced'}],
  matchups: ['leagueseasonmatchups', {LeagueID:'00',Season:season,SeasonType:'Regular Season',PerMode:'Totals',DefPlayerID:'',DefTeamID:'',OffPlayerID:'',OffTeamID:'',DateTo:dt}],
});
async function get(ep, p){ const url=`https://stats.nba.com/stats/${ep}?`+new URLSearchParams(p);
  try{ const r=await fetch(url,{...H,signal:AbortSignal.timeout(60000)}); if(!r.ok) return {err:'HTTP '+r.status};
  const d=await r.json(); const s=Array.isArray(d.resultSets)?d.resultSets[0]:d.resultSets; return {s}; }catch(e){return {err:String(e)}} }
const res={season,dateTo,kinds:{}};
for (const [k,[ep,p]] of Object.entries(jobs(dateTo))) {
  const a=await get(ep,p); const b=await get(ep,jobs('')[k][1]);
  const sum=(x,col)=>{ if(!x.s) return null; const i=x.s.headers.indexOf(col); return i<0?null:x.s.rowSet.reduce((t,r)=>t+(+r[i]||0),0); };
  const col={rim:'FGA_LT_06',three:'FG3A',hustle:'CONTESTED_SHOTS_3PT',advanced:'MIN',matchups:'PARTIAL_POSS'}[k];
  res.kinds[k]={ep, cutErr:a.err, rowsCut:a.s?.rowSet.length, rowsFull:b.s?.rowSet.length, sumCut:sum(a,col), sumFull:sum(b,col), col};
  if(a.s) await fs.writeFile(`probe-${k}.json`, JSON.stringify({dateTo, headers:a.s.headers, n:a.s.rowSet.length})+'\n');
  await new Promise(r=>setTimeout(r,1500));
}
// 逐場 matchups（若季累計端點不吃 DateTo 的備案）
const g=await get('boxscorematchupsv3',{GameID:'0022400061',LeagueID:'00',endPeriod:'0',endRange:'0',rangeType:'0',startPeriod:'0',startRange:'0'});
res.boxscorematchupsv3={err:g.err, ok:!!g.s};
const g2=await fetch('https://stats.nba.com/stats/boxscorematchupsv3?GameID=0022400061&LeagueID=00',{...H,signal:AbortSignal.timeout(60000)}).then(r=>r.ok?r.json():{status:r.status}).catch(e=>({e:String(e)}));
res.boxscorematchupsv3_raw=Object.keys(g2).slice(0,5); res.boxscorematchupsv3_sample=JSON.stringify(g2).slice(0,600);
console.log(JSON.stringify(res,null,1));
