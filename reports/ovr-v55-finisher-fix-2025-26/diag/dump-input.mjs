// 診斷用：把 v54 模擬板實際輸入的球員量測欄位印出來（唯讀，不改任何輸出）。
import {ovrInput} from '../../ovr-v54-2025-26/input.mjs';
const x = await ovrInput('both');
const p = x.players.find(p=>p.name.includes('Matkov'));
console.log('player keys:', Object.keys(p).join(','));
for (const k of ['opportunityMeasurement','shootingMeasurement','creationDependenceMeasurement','shotCreationMeasurement'])
  console.log('\n--- '+k+' ---\n'+JSON.stringify(p[k], (kk,v)=>typeof v==='string'&&v.length>200?v.slice(0,200)+'…':v, 1));
console.log('\ncard: '+JSON.stringify({long:p.long,mid:p.mid,short:p.short,drive:p.drive,pass:p.pass,handle:p.handle,offBall:p.offBall,screen:p.screen,breakDbl:p.breakDbl,onBall:p.onBall,help:p.help}));
console.log('role: '+JSON.stringify(x.roleMap.get(p.playerId)));
console.log('x keys: '+Object.keys(x).join(','));
