// E-208 harness. Run from repo root. Engine: sim 0.1.4 (v53 impactEngine chain via E120 makeRunner), options() unchanged.
import fs from 'node:fs';
import {loadX, makeRunner} from '../E120-foul-defense/winimp-core-e120.mjs';
import {options} from '../player-impact-v29/benchmark.mjs';
const here=new URL('.',import.meta.url);
export const read=f=>JSON.parse(fs.readFileSync(new URL(f,here),'utf8'));
const P7=['drive','ft','mid','pass','rebound','short','tovSkill'];
const clamp=v=>Math.max(0,Math.min(120,v));
export async function setup(variant){
  const {x,xAvg}=await loadX(); const {run}=await makeRunner();
  const byId=new Map(x.players.map(p=>[p.playerId,p]));
  const avg=xAvg.profiles[2]; // SF-labelled league minutes-weighted average profile (replacement for unknown players)
  let delta=null, fwd=null;
  if(variant==='Q'){
    const pp=read('pprime-day0-2425.json'); delta=new Map();
    pp.pids.forEach((id,i)=>{const d={};for(const a of P7){const v0=pp.day0[a][i],v1=pp.end[a][i];if(Number.isFinite(v0)&&Number.isFinite(v1))d[a]=v0-v1;}delta.set(id,d);});
  }
  if(variant==='F'){fwd=read('forward-inputs.json'); fwd.newSet=new Set(fwd.newPlayers);}
  const cache=new Map(), missing=new Set();
  const profile=pid=>{
    if(cache.has(pid))return cache.get(pid);
    let p=byId.get(pid);
    if(variant==='F'&&(fwd.newSet.has(pid)||!p)){
      const d=fwd.deltas[pid]; p={...avg,playerId:pid,name:'new'+pid}; missing.add(pid);
      if(d)for(const a of fwd.attrs)p[a]=clamp(avg[a]+d[a]);
    }else if(!p){p={...avg,playerId:pid,name:'unknown'+pid};missing.add(pid);}
    else if(variant==='Q'&&delta.has(pid)){p={...p};const d=delta.get(pid);for(const a of Object.keys(d))p[a]=clamp(p[a]+d[a]);}
    else if(variant==='F'){const d=fwd.deltas[pid];p={...p};if(d)for(const a of fwd.attrs)p[a]=clamp(p[a]+d[a]);}
    cache.set(pid,p);return p;
  };
  const team=(name,roster)=>{const tot=roster.reduce((a,[,m])=>a+m,0),k=240/tot;return {name,season:'2024-25',roster:roster.map(([pid,m])=>({...profile(pid),targetMinutes:m*k,injured:false}))};};
  const avgTeam=()=>({name:'league-average',season:'2024-25',roster:xAvg.profiles.concat(xAvg.profiles).map((p,i)=>({...p,playerId:-1-i,targetMinutes:24,injured:false}))});
  // one game; teamA, teamB; returns {sa,sb,pa,pb}
  const game=(tA,tB,seed)=>{
    const poss=[0,0];
    const g=run(tA,tB,{...options(x,seed,undefined),eventObserver:e=>{if(e.type==='POSSESSION')poss[e.off]++;}});
    if(g.gameSeconds!==2880||!g.complete)throw Error('Incomplete game');
    return {sa:g.scoreA,sb:g.scoreB,pa:poss[0],pb:poss[1]};
  };
  return {x,team,avgTeam,game,missing};
}
export const seedOf=(s,key)=>((Math.imul(s+1,7919)+Math.imul(key+1,1000003))>>>0);
