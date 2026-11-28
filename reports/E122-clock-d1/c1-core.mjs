// E-122 c1: per-defender engine duration change. Treated = candidate (workloadTeam) with beta map {cand: beta_d1};
// control = same minutes, league-average profile in his slot (playerId set to -1 so no beta applies), same seeds, same beta map.
// Both arms measured on the opponent's full-clock first-segment durations while the slot is on the floor.
// Design of draws = E-065 computeDraws (opponents x samples x both sides).
import {workloadTeam,opponentTeam,options} from '../player-impact-v29/benchmark.mjs';
import {segObserver} from './seg-core.mjs';
export function c1Player({run,src},{x,xAvg},id,beta,samples,baseSeed){
  const p=x.players.find(q=>q.playerId===id),slot=x.roleMap.get(id).slot,cap=src.capMinutes,minutes=src.players[id].supportedMinutes;
  const base=xAvg;let nT=0,sT=0,nC=0,sC=0;const per=[];
  for(let opp=0;opp<x.opponents.length;opp++)for(let i=0;i<samples;i++){
    const phase=i%2,a=workloadTeam(base,p,slot,minutes,cap,phase),c=workloadTeam(base,base.profiles[slot],slot,minutes,cap,phase),b=opponentTeam(x,x.opponents[opp],cap,phase);
    c.team.roster[slot].playerId=-1;
    const seed=(baseSeed+Math.imul(opp*5+slot,1000003)+Math.imul(i,7919))>>>0;
    for(const side of [0,1]){
      const teams=side?[b.team,a.team]:[a.team,b.team],ctrl=side?[b.team,c.team]:[c.team,b.team],schedules=side?[b.schedule,a.schedule]:[a.schedule,b.schedule];
      const so=segObserver(slot,side),sk=segObserver(slot,side);
      const g=run(...teams,{...options(base,seed,schedules),luckLedger:[0,0],eventObserver:so});
      const h=run(...ctrl,{...options(base,seed,schedules),luckLedger:[0,0],eventObserver:sk});
      if(g.gameSeconds!==2880||h.gameSeconds!==2880||!g.complete||!h.complete)throw Error('Incomplete game');
      nT+=so.stats.nOn;sT+=so.stats.sumOn;nC+=sk.stats.nOn;sC+=sk.stats.sumOn;
    }
  }
  return {id,name:p.name,slot,beta,nT,sT,nC,sC,meanT:sT/nT,meanC:sC/nC,delta:sT/nT-sC/nC};
}
