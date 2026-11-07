// usage: E208_S=2526|2425 node reports/E208-team-rating/run_mc.mjs <gamesC|gamesD> <variant P|Q> <shard> <nshards> <out.json> [seeds]
// game-level rosters from minutes-<S>.json (rules c / d). Same game/seed rule as run.mjs.
import fs from 'node:fs';
const S_=process.env.E208_S; if(S_!=='2526'&&S_!=='2425')throw Error('E208_S');
const {setup,read,seedOf}=await import(S_==='2526'?'./lib.mjs':'./lib2425.mjs');
const [job,variant,shard,nsh,out,seedsArg]=process.argv.slice(2); const S=Number(seedsArg??20), sh=Number(shard), N=Number(nsh);
const suf=job==='gamesC'?'C':job==='gamesD'?'D':null; if(!suf)throw Error('job');
const L=await setup(variant), res=[]; const inp=read(S_==='2526'?'inputs.json':'inputs-2425.json'), mn=read(`minutes-${S_}.json`);
for(const g of inp.games){ if(g.i%N!==sh)continue; const m_=mn[g.i];
  const th=L.team('H'+g.home,m_['hr'+suf]), ta=L.team('A'+g.away,m_['ar'+suf]), m=[];
  for(let s=0;s<S;s++){ const swap=(s+g.i)&1, r=swap?L.game(ta,th,seedOf(s,g.i)):L.game(th,ta,seedOf(s,g.i)); m.push(swap?r.sb-r.sa:r.sa-r.sb); }
  res.push({i:g.i,m}); }
fs.writeFileSync(out,JSON.stringify({job,variant,shard:sh,N,S,missing:[...L.missing],res}));
console.log('done',job,variant,sh,res.length);
