// v55 修正 B 的 B2：重算 shootingMeasurement.rates 的可靠度收縮權重。
//
// 為什麼不是改 k_short：centeredMake（reports/player-impact-v14/model.mjs）把命中率水準釘在
// 實測率 m.rates[z] 上，卡片只透過「新卡片 make − 凍結的 sourceBase」這個差分進入，所以加大
// 卡片層的 EB 偽計數在這塊板上幾乎被繞過。正確的槓桿是 rates 本身。
//
// 公式與 reports/player-impact-v9/input.mjs:15 完全一致（同一個聯盟 attempt-weighted 先驗、
// 同一個 shotDelta），只把偽計數 100 換成 K。先驗口徑刻意不動：改用分位置先驗會把長人往上拉
// 而不是往下壓（C/PF 的禁區先驗高於聯盟平均）。
//   K=100 必須逐位元重現 v54 的 rates（平行性檢查，見 verify-parity.mjs）。
import fs from 'node:fs';
const read=f=>JSON.parse(fs.readFileSync(f));
const ZONES=['long','mid','short'];
const cache=new Map();
function tables(season){
 if(cache.has(season))return cache.get(season);
 const cards=read(`reports/player-impact-v6/${season}-cards.json`).cards;
 const prior=Object.fromEntries(ZONES.map(z=>{let a=0,m=0;
  for(const p of Object.values(cards)){a+=p.freshShotCounts?.[z+'A']??0;m+=p.freshShotCounts?.[z+'M']??0;}
  return [z,m/a];}));
 let shift=read(`reports/defense-tenth/step4-rebounds-oreb/${season}/calibration-oreb.json`).selected.shotDelta??0;
 if(season!=='2025-26')shift+=read(`reports/defense-tenth/step4-t0/${season}/calibration-v3.json`).selected.shotDelta??0;
 const t={cards,prior,shift};cache.set(season,t);return t;
}
/** 用偽計數 K 重算 rates；回傳被改到的球員數。sourceBase、priorAttempts 之外的欄位不動。 */
export function applyRatesReliability(players,season,K){
 if(!Number.isFinite(K)||K<=0)throw Error('Invalid reliability pseudo-count');
 const {cards,prior,shift}=tables(season);
 let n=0;
 for(const p of players){
  const m=cards[p.playerId];
  if(!m)throw Error('Missing observed fresh-shot input for playerId '+p.playerId);
  if(!p.shootingMeasurement)throw Error('shootingMeasurement must already be attached');
  p.shootingMeasurement.rates=Object.fromEntries(ZONES.map(z=>{
   const a=m.freshShotCounts?.[z+'A']??0,made=m.freshShotCounts?.[z+'M']??0;
   const q=(made+K*prior[z])/(a+K);
   return [z,1/(1+Math.exp(-Math.log(q/(1-q))-shift))];}));
  p.shootingMeasurement.priorAttempts=K;
  n++;
 }
 return n;
}
