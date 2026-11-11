// E-135 WinImp core. Engine and input build come from E-086 (screen-core.mjs loadXFlags / makeRunner; e086-hooks.mjs ch1 rule):
// ch1 = doubleThreat physique term removed, long/mid/short weights renormalised. Flag off = legacy arithmetic (same expression).
// computeDraws is the E-102 copy of E-065 computeDraws (only change there: i loop starts at job.sampleStart). Unchanged here.
// Load via ../sim-0.1.0+E086-param-screen/boot.mjs registerE086() BEFORE importing this file.
import {loadXFlags, makeRunner as makeRunner086} from '../sim-0.1.0+E086-param-screen/screen-core.mjs';
import {workloadTeam,opponentTeam,options} from '../player-impact-v29/benchmark.mjs';
export const flagsOf = ch1 => Object.freeze({ch1: !!ch1});
export async function loadX(ch1) {
  const {X} = await loadXFlags(flagsOf(ch1));
  globalThis.__E086 = flagsOf(ch1); // keep the flag set between games too (team building before the first run() call)
  return X;
}
export const makeRunner = ch1 => makeRunner086(flagsOf(ch1));
const score=(g,side)=>side?g.scoreB-g.scoreA:g.scoreA-g.scoreB;
const winOf=d=>d>0?1:d<0?0:.5;
export function computeDraws({run,src},{x,xAvg},job,variant){
 const p=x.players.find(q=>q.playerId===job.id),slot=x.roleMap.get(p.playerId).slot,cap=src.capMinutes,minutes=src.players[p.playerId].supportedMinutes;
 const base=variant==='avg'?xAvg:x,draws=[];
 const opponents=job.opponents??x.opponents.length;
 for(let opponent=0;opponent<opponents;opponent++)for(let i=job.sampleStart??0;i<job.samples;i++){
  const phase=i%2,a=workloadTeam(base,p,slot,minutes,cap,phase),c=workloadTeam(base,base.profiles[slot],slot,minutes,cap,phase),b=opponentTeam(x,x.opponents[opponent],cap,phase);
  const seed=(job.seed+Math.imul(opponent*5+slot,1000003)+Math.imul(i,7919))>>>0;
  let mc=0,mk=0,ec=0,ek=0,wc=0,wk=0;
  for(const side of [0,1]){
   const teams=side?[b.team,a.team]:[a.team,b.team],ctrl=side?[b.team,c.team]:[c.team,b.team],schedules=side?[b.schedule,a.schedule]:[a.schedule,b.schedule];
   const lg=[0,0],lh=[0,0];
   const g=run(...teams,{...options(base,seed,schedules),luckLedger:lg}),h=run(...ctrl,{...options(base,seed,schedules),luckLedger:lh});
   if(g.gameSeconds!==2880||h.gameSeconds!==2880||!g.complete||!h.complete)throw Error('Incomplete game');
   const dg=score(g,side),dh=score(h,side);
   mc+=dg/2;mk+=dh/2;ec+=(dg-(lg[side]-lg[1-side]))/2;ek+=(dh-(lh[side]-lh[1-side]))/2;wc+=winOf(dg)/2;wk+=winOf(dh)/2;
  }
  draws.push([opponent,i,mc,mk,ec,ek,wc,wk].map((v,j)=>j<2?v:Math.round(v*1e6)/1e6));
 }
 return {playerId:p.playerId,name:p.name,variant,slot,minutes:Math.round(minutes*600)/600,draws};
}
