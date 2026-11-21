// E-069 m3: E-065 WinImp (same file, same seeds) with E-069 handle/pass/creation fields injected and options.e069 set.
// E-065 WinImp: candidate plays his 2025-26 minutes; other four slots and his off-court minutes are the
// all-position minute-weighted league-average profile. Control: same minutes, average profile instead of him.
// Side table (position variant): teammates = position-pool profiles (reports/ovr-v53-2025-26/worker.mjs design).
import {ovrInput} from '../../ovr-v53-2025-26/input.mjs';
import {source,workloadTeam,opponentTeam,options} from '../../player-impact-v29/benchmark.mjs';
import {impactEngine} from '../../player-impact-v53/engine.mjs';
import fs from 'node:fs';
import {interpolate} from '../../../src/probability_model.js';
import {CURVE_TOV} from '../../../src/constants.js';
const M70=70,csvRows=f=>{const [h,...r]=fs.readFileSync(f,'utf8').replace(/^﻿/,'').trim().split(/\r?\n/);const k=h.split(',');return r.map(l=>Object.fromEntries(l.split(',').map((v,i)=>[k[i],v])));};
const rel=a=>interpolate(a,CURVE_TOV)/interpolate(M70,CURVE_TOV);
export const E069=JSON.parse(fs.readFileSync('reports/handle-E069/sim/e069-cfg.json','utf8'));
function inject(x){
 const hand=new Map(csvRows('reports/handle-E069/handle.csv').filter(r=>r.season==='2025-26').map(r=>[r.playerId,r]));
 const card=new Map(csvRows('reports/card-0.2.0/ranking.csv').map(r=>[r.name,Number(r.creation)]));
 const miss={handle:0,pass:0,creation:0},set=p=>{
  const h=hand.get(String(p.playerId));
  const handle=h&&Number.isFinite(Number(h.handle))?Number(h.handle):(miss.handle++,M70);
  const passSec=h&&Number.isFinite(Number(h.passSec))?Number(h.passSec):(miss.pass++,M70);
  const cr=card.get(p.name),creation=Number.isFinite(cr)?cr:(miss.creation++,M70);
  p.handle=handle;p.e069Handle=handle;p.e069Creation=creation;p.e069HandleRel=rel(handle);p.e069PassRel=rel(passSec);};
 const pool=(p)=>{p.e069Handle=M70;p.e069Creation=M70;p.e069HandleRel=1;p.e069PassRel=1;};
 for(const p of x.players)set(p);
 for(const o of x.opponents)for(const p of o.roster)set(p);
 for(const p of x.profiles)pool(p);   // position-pool profiles are the league-average (70) player
 x.e069Missing=miss;return x;
}
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
 const x=inject(await ovrInput('both'));
 const avgs=averageProfiles(x);
 return {x,xAvg:{...x,profiles:avgs}};
}
const score=(g,side)=>side?g.scoreB-g.scoreA:g.scoreA-g.scoreB;
const winOf=d=>d>0?1:d<0?0:.5;
export async function makeRunner(){
 const run=await impactEngine('rotation-space',{game:true}),src=source();
 return {src,run};
}
// variant 'avg' (primary) or 'pos' (side table). Returns draws [opp,i,marginCand,marginCtrl,expCand,expCtrl,winCand,winCtrl].
export function computeDraws({run,src},{x,xAvg},job,variant){
 const p=x.players.find(q=>q.playerId===job.id),slot=x.roleMap.get(p.playerId).slot,cap=src.capMinutes,minutes=src.players[p.playerId].supportedMinutes;
 const base=variant==='avg'?xAvg:x,draws=[];
 const mkOpt=(b,seed,sch)=>({...options(b,seed,sch),e069:E069});
 const opponents=job.opponents??x.opponents.length;
 for(let opponent=0;opponent<opponents;opponent++)for(let i=0;i<job.samples;i++){
  const phase=i%2,a=workloadTeam(base,p,slot,minutes,cap,phase),c=workloadTeam(base,base.profiles[slot],slot,minutes,cap,phase),b=opponentTeam(x,x.opponents[opponent],cap,phase);
  const seed=(job.seed+Math.imul(opponent*5+slot,1000003)+Math.imul(i,7919))>>>0;
  let mc=0,mk=0,ec=0,ek=0,wc=0,wk=0;
  for(const side of [0,1]){
   const teams=side?[b.team,a.team]:[a.team,b.team],ctrl=side?[b.team,c.team]:[c.team,b.team],schedules=side?[b.schedule,a.schedule]:[a.schedule,b.schedule];
   const lg=[0,0],lh=[0,0];
   const g=run(...teams,{...mkOpt(base,seed,schedules),luckLedger:lg}),h=run(...ctrl,{...mkOpt(base,seed,schedules),luckLedger:lh});
   if(g.gameSeconds!==2880||h.gameSeconds!==2880||!g.complete||!h.complete)throw Error('Incomplete game');
   const dg=score(g,side),dh=score(h,side);
   mc+=dg/2;mk+=dh/2;ec+=(dg-(lg[side]-lg[1-side]))/2;ek+=(dh-(lh[side]-lh[1-side]))/2;wc+=winOf(dg)/2;wk+=winOf(dh)/2;
  }
  draws.push([opponent,i,mc,mk,ec,ek,wc,wk].map((v,j)=>j<2?v:Math.round(v*1e6)/1e6));
 }
 return {playerId:p.playerId,name:p.name,variant,slot,minutes:Math.round(minutes*600)/600,draws};
}
