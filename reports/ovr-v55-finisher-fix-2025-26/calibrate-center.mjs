// 定出 B1 的聯盟水準常數 c：2025-26 球隊層（真實陣容）跑一顆種子，逐禁區出手累加
// D̃_i([fed]−s̃_i)，取 attempt-weighted 平均後取負號。補籃出手不計（調整量本來就是 0）。
//   node reports/ovr-v55-finisher-fix-2025-26/calibrate-center.mjs
// 寫出 center.json。c 定下來之後凍結，四季共用。
import fs from 'node:fs';
import {loadInput} from '../player-impact-v47/input.mjs';
import {pressureCoefficients} from '../ovr-v53-2025-26/input.mjs';
import {applyV54Shooting} from '../ovr-v54-2025-26/shooting-eb.mjs';
import {ledgerEngine,decode} from './engine-ledger.mjs';
import {shotOriginTables,attachShotOrigin} from '../../src/source_shot_origin.js';
import {applyRatesReliability} from './rates-reliability.mjs';
import {RELIABILITY_K} from './input.mjs';
const DIR='reports/ovr-v55-finisher-fix-2025-26';
const SEASON='2025-26',SEED=20261012;
const origin=JSON.parse(fs.readFileSync(`${DIR}/shot-origin.json`,'utf8'));
const tables=shotOriginTables(origin,[SEASON]);
const b=loadInput(SEASON),run=await ledgerEngine('rotation-space');
const roster=b.league.teams.flatMap(t=>t.roster);
applyV54Shooting(roster,SEASON);
applyRatesReliability(roster,SEASON,RELIABILITY_K);
const att=attachShotOrigin(roster,tables,{center:0});
b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;
b.options.spaceCenter=JSON.parse(fs.readFileSync(`reports/player-impact-v7/${SEASON}-center.json`)).fullCenter;
const coef=pressureCoefficients();let tagged=0;
for(const p of roster){const c=coef.get(p.playerId);if(c){p.pressureMeasurement={tovNonSteal:c.tovNonSteal};tagged++;}}
const ledger=new Map();
// 球隊層走的是「季」層跑者，逐場比賽的 opt 來自 b.options，所以 ledger 要掛在 b.options 上
// （不是外層那個物件——第一版掛錯層，ledger 全空）。季層跑者是同一個 process 單執行緒，
// 所以 Map 可以直接共用。
b.options.originLedger=ledger;
const t0=Date.now();
const r=run(b.league,b.exposure,{seed:SEED,options:b.options,audit:false,replay:false,indices:null});
const by=new Map();
for(const [k,n] of ledger){const d=decode(k);if(d.putback)continue;
 const e=by.get(d.playerId)??{fed:0,self:0};e[d.assisted?'fed':'self']+=n;by.set(d.playerId,e);}
let num=0,den=0,fedA=0,selfA=0,miss=0;
const rows=[];
for(const [pid,e] of by){
 const m=tables.players.get(pid)??{fedShare:tables.league.fedShare,gap:tables.eb.dBar};
 if(!tables.players.has(pid))miss+=e.fed+e.self;
 const A=e.fed+e.self;fedA+=e.fed;selfA+=e.self;
 num+=m.gap*((1-m.fedShare)*e.fed+(0-m.fedShare)*e.self);den+=A;
 rows.push({playerId:pid,simFedShare:e.fed/A,sourceFedShare:m.fedShare,attempts:A});
}
const mean=num/den,c=-mean;
const simFed=fedA/(fedA+selfA);
const out={frozenAt:new Date().toISOString().slice(0,10),season:SEASON,seed:SEED,
 games:r.matches.length,rimAttempts:den,putbackAttemptsExcluded:[...ledger].filter(([k])=>decode(k).putback).reduce((a,[,n])=>a+n,0),
 simFedShare:simFed,sourceFedShareLeague:tables.league.fedShare,
 attemptsWithoutMeasurement:miss,meanAdjustment:mean,center:c,
 note:'c = -attempt-weighted mean of gap_i*([fed]-fedShare_i) over non-putback rim attempts in one 2025-26 team-layer season.',
 seconds:(Date.now()-t0)/1000};
fs.writeFileSync(`${DIR}/center.json`,JSON.stringify(out,null,1));
console.log(JSON.stringify(out,null,1));
