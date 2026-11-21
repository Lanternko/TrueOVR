// E-087 WinImp core: E-065 core (reports/card-0.1.2+E065-inout-wins/winimp-core.mjs) unchanged except
// (1) engine = v53 + handleShare patch (engine-e087.mjs), (2) real players (candidates and opponent rosters)
// carry p.e087Handle from handle.csv 2025-26 (missing -> 70 at use time; league-average / position-pool
// profiles carry none -> 70), (3) options get handleShare (job.handleShare, default 'off') and optional p0 probe.
import {ovrInput} from '../ovr-v53-2025-26/input.mjs';
import {source,workloadTeam,opponentTeam,options} from '../player-impact-v29/benchmark.mjs';
import {winimpEngine} from './engine-e087.mjs';
import {handleMap,attachHandles,checkMode} from './handle-share.mjs';
export function averageProfiles(x){
 const w=x.profiles.map(p=>p.profileMetadata.minutes),W=w.reduce((a,b)=>a+b,0);
 const avg=(vals)=>{
  const v0=vals[0];
  if(typeof v0==='number')return vals.reduce((s,v,i)=>s+v*w[i],0)/W;
  if(Array.isArray(v0)||v0===null||typeof v0!=='object')return v0;
  return Object.fromEntries(Object.keys(v0).map(k=>[k,vals.every(v=>v&&k in v)?avg(vals.map(v=>v[k])):v0[k]]));
 };
 return x.profiles.map((p,i)=>{const a=avg(x.profiles);return {...a,playerId:p.playerId,pos:p.pos,courtPosition:p.courtPosition??p.pos,name:'全聯盟平均'};});
}
export async function loadX(){
 const x=await ovrInput('both'),map=handleMap('2025-26'),miss=new Set();
 attachHandles(x.players,map,miss);for(const o of x.opponents)attachHandles(o.roster,map,miss);
 if(x.profiles.some(p=>'e087Handle' in p))throw Error('profile carries e087Handle');
 const avgs=averageProfiles(x);
 return {x,xAvg:{...x,profiles:avgs},missing:[...miss]};
}
const score=(g,side)=>side?g.scoreB-g.scoreA:g.scoreA-g.scoreB;
const winOf=d=>d>0?1:d<0?0:.5;
export async function makeRunner({diag=false}={}){
 const run=await winimpEngine({diag}),src=source();
 return {src,run};
}
// variant 'avg' (primary) or 'pos' (side table). Returns draws [opp,i,marginCand,marginCtrl,expCand,expCtrl,winCand,winCtrl].
export function computeDraws({run,src},{x,xAvg},job,variant){
 const mode=checkMode(job.handleShare),extra={handleShare:mode,...(job.probe?{e087Probe:job.probe,eventObserver:job.probe.event}:{})};
 const p=x.players.find(q=>q.playerId===job.id),slot=x.roleMap.get(p.playerId).slot,cap=src.capMinutes,minutes=src.players[p.playerId].supportedMinutes;
 const base=variant==='avg'?xAvg:x,draws=[];
 const opponents=job.opponents??x.opponents.length;
 for(let opponent=0;opponent<opponents;opponent++)for(let i=0;i<job.samples;i++){
  const phase=i%2,a=workloadTeam(base,p,slot,minutes,cap,phase),c=workloadTeam(base,base.profiles[slot],slot,minutes,cap,phase),b=opponentTeam(x,x.opponents[opponent],cap,phase);
  const seed=(job.seed+Math.imul(opponent*5+slot,1000003)+Math.imul(i,7919))>>>0;
  let mc=0,mk=0,ec=0,ek=0,wc=0,wk=0;
  for(const side of [0,1]){
   const teams=side?[b.team,a.team]:[a.team,b.team],ctrl=side?[b.team,c.team]:[c.team,b.team],schedules=side?[b.schedule,a.schedule]:[a.schedule,b.schedule];
   const lg=[0,0],lh=[0,0];
   if(job.probe)job.probe.games+=2;
   const g=run(...teams,{...options(base,seed,schedules),luckLedger:lg,...extra}),h=run(...ctrl,{...options(base,seed,schedules),luckLedger:lh,...extra});
   if(g.gameSeconds!==2880||h.gameSeconds!==2880||!g.complete||!h.complete)throw Error('Incomplete game');
   const dg=score(g,side),dh=score(h,side);
   mc+=dg/2;mk+=dh/2;ec+=(dg-(lg[side]-lg[1-side]))/2;ek+=(dh-(lh[side]-lh[1-side]))/2;wc+=winOf(dg)/2;wk+=winOf(dh)/2;
  }
  draws.push([opponent,i,mc,mk,ec,ek,wc,wk].map((v,j)=>j<2?v:Math.round(v*1e6)/1e6));
 }
 return {playerId:p.playerId,name:p.name,variant,slot,minutes:Math.round(minutes*600)/600,draws};
}
