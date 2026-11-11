// 賽中 C4 即時資料抓取（2026-27）。只新增檔案，不動 v4/v5 工具。
// 用法：node scripts/fetch_inseason_2026_27.js [季別=2026-27]
// 輸出 data/defense-seventh/<季別>/{player-games,team-games,bio}.json 與 pbp/<GAME_ID>.json（已抓過的不重抓）。
// 不抓 four-factors / v3-league / dependence / shot-origin：C4 對目標季只讀 box、bio、pbp 投籃位置；
// 壓迫（pressure）等被凍結的屬性不需要 four-factors（見 reports/ovr-inseason-2026-27/live/README.md）。
import fs from 'node:fs';
const season=process.argv[2]??'2026-27',root=`data/defense-seventh/${season}`,src=`data/season-source-${season}`;
fs.mkdirSync(root+'/pbp',{recursive:true});
const headers={'User-Agent':'Mozilla/5.0',Referer:'https://www.nba.com/'};
for(const n of ['player-games','team-games'])fs.copyFileSync(`${src}/${n}.json`,`${root}/${n}.json`);
const rows=d=>{const s=Array.isArray(d.resultSets)?d.resultSets[0]:d.resultSets;return s.rowSet.map(r=>Object.fromEntries(s.headers.map((k,i)=>[k,r[i]])));};
async function getJson(url,valid){let last;for(let i=0;i<3;i++)try{const r=await fetch(url,{headers,signal:AbortSignal.timeout(25000)});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();if(!valid(d))throw Error('Invalid response');return d;}catch(e){last=e;}throw last;}
// bio（每次重抓：賽中球員增加）
const tq=new URLSearchParams({LeagueID:'00',Season:season,SeasonType:'Regular Season',PerMode:'Totals',MeasureType:'Base',TeamID:'0',LastNGames:'0',Month:'0',OpponentTeamID:'0',PaceAdjust:'N',PlusMinus:'N',Rank:'N',Period:'0'});
const burl='https://stats.nba.com/stats/leaguedashplayerbiostats?'+tq;
const bdata=await getJson(burl,x=>(x.resultSets?.[0]??x.resultSets)?.rowSet?.length>0);
fs.writeFileSync(root+'/bio.json',JSON.stringify({url:burl,season,fetchedAt:new Date().toISOString(),data:bdata})+'\n');
console.log('bio',rows(bdata).length);
// 現役名單（含傷兵、還沒出賽的人；bio 只有已出賽）。抓不到不擋流程，run_c4_live 退回只列已出賽
const rurl='https://stats.nba.com/stats/commonallplayers?'+new URLSearchParams({LeagueID:'00',Season:season,IsOnlyCurrentSeason:'1'});
try{const rdata=await getJson(rurl,x=>(x.resultSets?.[0]??x.resultSets)?.rowSet?.length>300);
 fs.writeFileSync(root+'/roster.json',JSON.stringify({url:rurl,season,fetchedAt:new Date().toISOString(),data:rdata})+'\n');
 console.log('roster',rows(rdata).length);}catch(e){console.log('roster failed',String(e));}
// pbp
const games=[...new Set(rows(JSON.parse(fs.readFileSync(`${root}/team-games.json`)).data).map(r=>r.GAME_ID))].sort();
const homeAway=new Map();for(const r of rows(JSON.parse(fs.readFileSync(`${root}/team-games.json`)).data)){homeAway.set(r.GAME_ID,[...(homeAway.get(r.GAME_ID)??[]),r.PTS]);}
const fail=[];let ok=0,cached=0;
for(const id of games){const file=`${root}/pbp/${id}.json`;if(fs.existsSync(file)){cached++;continue;}
 const url='https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_'+id+'.json';
 try{const d=await getJson(url,x=>x.game?.gameId===id&&x.game.actions.length>=100);
  const e=d.game.actions.findLast(a=>a.scoreHome!==''&&a.scoreAway!=='');const pts=homeAway.get(id).slice().sort((a,b)=>a-b),got=[+e.scoreHome,+e.scoreAway].sort((a,b)=>a-b);
  if(pts[0]!==got[0]||pts[1]!==got[1])throw Error('score mismatch '+pts+' vs '+got);
  fs.writeFileSync(file,JSON.stringify({url,season,fetchedAt:new Date().toISOString(),data:d})+'\n');ok++;}catch(e){fail.push({id,error:String(e)});}}
console.log(JSON.stringify({season,games:games.length,fetched:ok,cached,failures:fail}));
if(fail.length)process.exitCode=1;
