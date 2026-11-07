// 平行性檢查（必須在評估跑之前通過）：
//  1. K=100 重算的 rates 與 v54 的 rates 逐位元相同（B2 的公式真的是 v9 的公式）。
//  2. mode='v54'（不掛 shotOriginMeasurement、不動 rates）時板上一場比賽的 box score
//     與真正的 v54 input 逐位元相同（新行為預設關閉、v54 可重現）。
//   node reports/ovr-v55-finisher-fix-2025-26/verify-parity.mjs
import {ovrInput as v54Input} from '../ovr-v54-2025-26/input.mjs';
import {ovrInput as v55Input, applyV55} from './input.mjs';
import {applyRatesReliability} from './rates-reliability.mjs';
import {source,workloadTeam,opponentTeam,options} from '../player-impact-v29/benchmark.mjs';
import {impactEngine} from '../player-impact-v53/engine.mjs';

const a=await v54Input('both');
const ratesOf=x=>x.players.map(p=>[p.playerId,p.shootingMeasurement.rates.long,p.shootingMeasurement.rates.mid,p.shootingMeasurement.rates.short]);
const before=JSON.stringify(ratesOf(a));
applyRatesReliability([...a.players,...a.opponents.flatMap(t=>t.roster)],'2025-26',100);
const after=JSON.stringify(ratesOf(a));
const check1=before===after;

// 2. 一場真實的板上比賽，v54 input vs v55 input(mode='v54')
const run=await impactEngine('rotation-space',{game:true}),src=source();
const box=async(load)=>{
 const x=await load();
 const id=1631255,p=x.players.find(q=>q.playerId===id),slot=x.roleMap.get(id).slot;
 const cap=src.capMinutes,minutes=src.players[id].supportedMinutes,phase=0;
 const t=workloadTeam(x,p,slot,minutes,cap,phase),o=opponentTeam(x,x.opponents[0],cap,phase);
 const g=run(t.team,o.team,{...options(x,20261016,[t.schedule,o.schedule])});
 return JSON.stringify({scoreA:g.scoreA,scoreB:g.scoreB,statA:g.statA,statB:g.statB});
};
const b54=await box(()=>v54Input('both'));
const b55=await box(()=>v55Input('both','v54'));
const check2=b54===b55;
// 3. 反向檢查：B12 真的會改變結果（否則上面的「相同」沒有意義）
const bB12=await box(()=>v55Input('both','B12'));
const check3=bB12!==b54;
console.log(JSON.stringify({ratesK100MatchesV54:check1,v54BoxReproduced:check2,B12ActuallyChangesBox:check3,
 sample:{v54:JSON.parse(b54).scoreA+'-'+JSON.parse(b54).scoreB,B12:JSON.parse(bB12).scoreA+'-'+JSON.parse(bB12).scoreB}},null,1));
if(!check1||!check2||!check3)process.exit(1);
