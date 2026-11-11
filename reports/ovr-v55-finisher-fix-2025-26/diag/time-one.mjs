// 計時：單名球員在 v54 模擬板協議（30 對手 x 8 samples x 2 側 x 處理/對照）下要多久。
import {ovrInput} from '../../ovr-v54-2025-26/input.mjs';
import {source, workloadTeam, opponentTeam, options} from '../../player-impact-v29/benchmark.mjs';
import {impactEngine} from '../../player-impact-v53/engine.mjs';
const run=await impactEngine('rotation-space',{game:true}),src=source();
const x=await ovrInput('both');
const id=1631255,p=x.players.find(q=>q.playerId===id),slot=x.roleMap.get(id).slot,cap=src.capMinutes,minutes=src.players[id].supportedMinutes;
const t0=Date.now();let games=0;
for(let opponent=0;opponent<30;opponent++)for(let i=0;i<8;i++){
 const phase=i%2;
 const a=workloadTeam(x,p,slot,minutes,cap,phase),base=workloadTeam(x,x.profiles[slot],slot,minutes,cap,phase),b=opponentTeam(x,x.opponents[opponent],cap,phase);
 const seed=(20261016+Math.imul(opponent*5+slot,1000003)+Math.imul(i,7919))>>>0;
 for(const side of [0,1]){
  const teams=side?[b.team,a.team]:[a.team,b.team],baseline=side?[b.team,base.team]:[base.team,b.team],schedules=side?[b.schedule,a.schedule]:[a.schedule,b.schedule];
  const lg=[0,0],lh=[0,0];
  run(...teams,{...options(x,seed,schedules),luckLedger:lg});
  run(...baseline,{...options(x,seed,schedules),luckLedger:lh});
  games+=2;
 }
}
const s=(Date.now()-t0)/1000;
console.log(JSON.stringify({games,seconds:+s.toFixed(1),gamesPerSec:+(games/s).toFixed(1),
 est582PlayersOneWorkerHours:+(s*582/3600).toFixed(1), est10WorkersHours:+(s*582/3600/10).toFixed(2)}));
