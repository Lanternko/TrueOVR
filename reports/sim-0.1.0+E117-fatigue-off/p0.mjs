// E-117 p0: same seed, fatigue on vs off. Outputs must differ; off game must never call applyStamina (energy stays 1).
import {register} from 'node:module';
globalThis.__P0={calls:0,maxFatigue:0};
register('./p0-hooks.mjs', import.meta.url);
const {makeRunner,loadX}=await import('./winimp-core-e117.mjs');
const {workloadTeam,opponentTeam,options}=await import('../player-impact-v29/benchmark.mjs');
const X=await loadX(),{x}=X;
const p=x.players.find(q=>q.name==='Nikola Jokić')??x.players[0],slot=x.roleMap.get(p.playerId).slot;
async function one(fatigue){
 const r=await makeRunner(fatigue);globalThis.__P0={calls:0,maxFatigue:0};
 const cap=r.src.capMinutes,minutes=r.src.players[p.playerId].supportedMinutes;
 const a=workloadTeam(x,p,slot,minutes,cap,0),b=opponentTeam(x,x.opponents[0],cap,0),seed=20261028;
 const g=r.run(a.team,b.team,{...options(x,seed,[a.schedule,b.schedule]),luckLedger:[0,0]});
 return {fatigue,scoreA:g.scoreA,scoreB:g.scoreB,gameSeconds:g.gameSeconds,complete:g.complete,applyStaminaCalls:globalThis.__P0.calls,maxFatigueArg:globalThis.__P0.maxFatigue};
}
const on=await one(true),off=await one(false);
const differ=on.scoreA!==off.scoreA||on.scoreB!==off.scoreB;
const pass=differ&&off.applyStaminaCalls===0&&off.maxFatigueArg===0&&on.applyStaminaCalls>0&&on.maxFatigueArg>0&&on.complete&&off.complete;
console.log(JSON.stringify({player:p.name,seed:20261028,on,off,outputsDiffer:differ,pass},null,1));
if(!pass)process.exit(1);
