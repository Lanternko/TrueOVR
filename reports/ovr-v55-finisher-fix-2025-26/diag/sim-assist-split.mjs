// 診斷用（唯讀）：在 v54 模擬板上跑少量比賽，用引擎既有的 onCourtObserver 事件統計
// 指定球員在模擬裡的「禁區出手被助攻比例」，再跟來源季的 receivedShare 對照。
//   node reports/ovr-v55-finisher-fix-2025-26/diag/sim-assist-split.mjs 1631255 1629646 1629637 1629029 201939
import {ovrInput} from '../../ovr-v54-2025-26/input.mjs';
import {source, workloadTeam, opponentTeam, options} from '../../player-impact-v29/benchmark.mjs';
import {impactEngine} from '../../player-impact-v53/engine.mjs';
const ids = process.argv.slice(2).map(Number);
const run = await impactEngine('rotation-space', {game:true}), src = source();
const x = await ovrInput('both');
const OPP = 6, SAMPLES = 2, seed0 = 20261016;
for (const id of ids) {
  const p = x.players.find(q=>q.playerId===id); if(!p){console.log(id+' not found');continue;}
  const slot = x.roleMap.get(id).slot, cap = src.capMinutes, minutes = src.players[id].supportedMinutes;
  const tally = {short:[0,0], mid:[0,0], long:[0,0]};   // [assisted, selfCreated] 出手數
  for (let opponent=0; opponent<OPP; opponent++) for (let i=0;i<SAMPLES;i++) {
    const phase=i%2;
    const a=workloadTeam(x,p,slot,minutes,cap,phase), b=opponentTeam(x,x.opponents[opponent],cap,phase);
    const seed=(seed0+Math.imul(opponent*5+slot,1000003)+Math.imul(i,7919))>>>0;
    for (const side of [0,1]) {
      const teams=side?[b.team,a.team]:[a.team,b.team], schedules=side?[b.schedule,a.schedule]:[a.schedule,b.schedule];
      const obs=e=>{ if(e.playerId!==id||!e.zone)return; tally[e.zone][e.assistPlayerId===null?1:0]++; };
      run(...teams,{...options(x,seed,schedules),onCourtObserver:obs});
    }
  }
  const m=p.opportunityMeasurement, recv=m.receiveOpportunityRate/m.terminalOpportunityRate;
  const t=tally.short, n=t[0]+t[1];
  console.log(JSON.stringify({name:p.name, sourceReceivedShare:+recv.toFixed(3),
    simRimAssistedShare: n?+(t[0]/n).toFixed(3):null, rimAttempts:n,
    simLongAssistedShare: (tally.long[0]+tally.long[1])?+(tally.long[0]/(tally.long[0]+tally.long[1])).toFixed(3):null}));
}
