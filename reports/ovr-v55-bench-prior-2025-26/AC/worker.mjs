// v55 variant AC. Identical harness to
// reports/ovr-v54-2025-26/worker.mjs; ovrInput comes from ../input.mjs fixed to card variant 'A'.
import {parentPort} from 'node:worker_threads';
import {ovrInputFor} from '../input.mjs';
import {source,workloadTeam,opponentTeam,options} from '../../player-impact-v29/benchmark.mjs';
import {impactEngine} from '../../player-impact-v53/engine.mjs';
const ovrInput=ovrInputFor('AC');
const run=await impactEngine('rotation-space',{game:true}),src=source(),inputs=new Map();
const score=(g,side)=>side?g.scoreB-g.scoreA:g.scoreA-g.scoreB;
parentPort.on('message',async job=>{try{
 if(!inputs.has(job.variant))inputs.set(job.variant,await ovrInput(job.variant));
 const x=inputs.get(job.variant),p=x.players.find(p=>p.playerId===job.id),slot=x.roleMap.get(p.playerId).slot,cap=src.capMinutes,minutes=src.players[p.playerId].supportedMinutes;
 const draws=[];
 for(let opponent=0;opponent<x.opponents.length;opponent++)for(let i=0;i<job.samples;i++){
  const phase=i%2,a=workloadTeam(x,p,slot,minutes,cap,phase),base=workloadTeam(x,x.profiles[slot],slot,minutes,cap,phase),b=opponentTeam(x,x.opponents[opponent],cap,phase);
  const seed=(job.seed+Math.imul(opponent*5+slot,1000003)+Math.imul(i,7919))>>>0;
  let delta=0,expected=0,oppFga=0,oppTov=0;
  for(const side of [0,1]){
   const teams=side?[b.team,a.team]:[a.team,b.team],baseline=side?[b.team,base.team]:[base.team,b.team],schedules=side?[b.schedule,a.schedule]:[a.schedule,b.schedule];
   const lg=[0,0],lh=[0,0];
   const g=run(...teams,{...options(x,seed,schedules),luckLedger:lg}),h=run(...baseline,{...options(x,seed,schedules),luckLedger:lh});
   if(g.gameSeconds!==2880||h.gameSeconds!==2880||!g.complete||!h.complete)throw Error('Incomplete game');
   delta+=(score(g,side)-score(h,side))/2;
   expected+=((score(g,side)-(lg[side]-lg[1-side]))-(score(h,side)-(lh[side]-lh[1-side])))/2;
   const opp=side?g.statA:g.statB;oppFga+=opp.fga/2;oppTov+=opp.tov/2;
  }
  draws.push([opponent,i,delta,oppFga,oppTov,expected]);
 }
 parentPort.postMessage({job,result:{playerId:p.playerId,name:p.name,variant:job.variant,minutes:Math.round(minutes*600)/600,draws}});
}catch(e){parentPort.postMessage({job,error:e.stack});}});
