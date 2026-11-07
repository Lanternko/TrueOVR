// 診斷：模擬裡的「被餵禁區球比例」對不對，以及 B1 自己會不會把這個比例推高。
//   node reports/ovr-v55-finisher-fix-2025-26/fedshare-diagnostic.mjs
// 寫出 fedshare-diagnostic.json。
//
// 為什麼需要：預先登錄當時假設「模擬普遍餵得比現實少」，但校正跑（center.json）量到
// simFedShare 0.624 > 現實 0.440，方向相反。而那次量測是**開著 B1** 的，B1 會讓
// usedAssist 偏向 true（接球投機率被加了 gap，best() 就更容易選它），所以必須另外量一次
// 關掉 B1 的基準值，才能把「基準模擬本來就餵太多」跟「B1 自己造成的偏移」分開。
import fs from 'node:fs';
import {loadInput} from '../player-impact-v47/input.mjs';
import {pressureCoefficients} from '../ovr-v53-2025-26/input.mjs';
import {applyV54Shooting} from '../ovr-v54-2025-26/shooting-eb.mjs';
import {ledgerEngine,decode} from './engine-ledger.mjs';
import {shotOriginTables,attachShotOrigin} from '../../src/source_shot_origin.js';
import {applyRatesReliability} from './rates-reliability.mjs';
import {RELIABILITY_K,centerFor} from './input.mjs';
const DIR='reports/ovr-v55-finisher-fix-2025-26';
const SEASON='2025-26',SEED=20261012;
const FOCUS=['Karlo Matković','Charles Bassey','Jaxson Hayes','John Collins','Isaiah Stewart','Luka Garza',
 'Neemias Queta','Rudy Gobert','Jalen Smith','Nikola Jokić','Luka Dončić','Shai Gilgeous-Alexander','Trae Young'];
const origin=JSON.parse(fs.readFileSync(`${DIR}/shot-origin.json`,'utf8'));
const tables=shotOriginTables(origin,[SEASON]);
const coef=pressureCoefficients();
const run=await ledgerEngine('rotation-space');
async function once(useOrigin){
 const b=loadInput(SEASON);
 const roster=b.league.teams.flatMap(t=>t.roster);
 applyV54Shooting(roster,SEASON);
 applyRatesReliability(roster,SEASON,RELIABILITY_K);   // B2 兩邊都開，唯一差別是 B1
 if(useOrigin)attachShotOrigin(roster,tables,{center:centerFor('B12')});
 b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;
 b.options.spaceCenter=JSON.parse(fs.readFileSync(`reports/player-impact-v7/${SEASON}-center.json`)).fullCenter;
 for(const p of roster){const c=coef.get(p.playerId);if(c)p.pressureMeasurement={tovNonSteal:c.tovNonSteal};}
 const ledger=new Map();b.options.originLedger=ledger;
 const t0=Date.now();
 run(b.league,b.exposure,{seed:SEED,options:b.options,audit:false,replay:false,indices:null});
 const by=new Map();let fed=0,self=0;
 for(const [k,n] of ledger){const d=decode(k);if(d.putback)continue;
  const e=by.get(d.playerId)??{fed:0,self:0};e[d.assisted?'fed':'self']+=n;by.set(d.playerId,e);
  if(d.assisted)fed+=n;else self+=n;}
 const names=new Map(roster.map(p=>[p.playerId,p.name]));
 return {simFedShare:fed/(fed+self),rimAttempts:fed+self,seconds:(Date.now()-t0)/1000,
  byPlayer:[...by].map(([pid,e])=>({playerId:pid,name:names.get(pid),attempts:e.fed+e.self,simFedShare:e.fed/(e.fed+e.self)}))};
}
const off=await once(false),on=await once(true);
const idx=m=>new Map(m.byPlayer.map(r=>[r.name,r]));
const [io,ii]=[idx(off),idx(on)];
const focus=FOCUS.map(n=>{const pid=io.get(n)?.playerId;const t=pid!=null?tables.players.get(pid):null;
 return {name:n,sourceFedShare:t?.fedShare??null,sourceRimAttempts:t?.rimAttempts??null,rawGap:t?.gap??null,
  simFedShareNoB1:io.get(n)?.simFedShare??null,simAttemptsNoB1:io.get(n)?.attempts??null,
  simFedShareB1:ii.get(n)?.simFedShare??null,simAttemptsB1:ii.get(n)?.attempts??null};});
const out={season:SEASON,seed:SEED,sourceFedShareLeague:tables.league.fedShare,
 league:{noB1:{simFedShare:off.simFedShare,rimAttempts:off.rimAttempts},withB1:{simFedShare:on.simFedShare,rimAttempts:on.rimAttempts}},
 b1EffectOnFedShare:on.simFedShare-off.simFedShare,
 baselineBiasVsSource:off.simFedShare-tables.league.fedShare,
 focus,seconds:{noB1:off.seconds,withB1:on.seconds}};
fs.writeFileSync(`${DIR}/fedshare-diagnostic.json`,JSON.stringify(out,null,1));
console.log(JSON.stringify({...out,focus:undefined},null,1));
