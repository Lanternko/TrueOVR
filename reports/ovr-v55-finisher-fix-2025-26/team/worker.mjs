// v55 修正 B 的球隊層 worker：與 reports/player-impact-v54-team/worker.mjs 逐行相同
// （v47 全季 job ＋ v53 引擎 ＋ v54 可靠度卡片 ＋ pressure/tovNonSteal 標記），只在
// applyV54Shooting 之後多做一件事：套 v55 的 B1／B2。
//
// 兩個刻意的口徑選擇（預先登錄 §6 之外，這裡記錄假設）：
//  1. B1 的餵／自主分割表**逐季用該季自己的 play-by-play 建**（shot-origin.json 四季都有），
//     和 v54 用該季自己的命中率一樣是季內口徑；聯盟水準常數 c 則是四季共用同一個凍結值。
//  2. B2 的 rates 收縮也逐季套。因此和 v54 不同，**2022-23/2023-24/2024-25 的球隊層結果
//     會跟 v53/v54 不一樣**（v54 的改動只產生 2025-26 卡片，所以舊季逐位元相同）。
//     score.py 不再斷言舊季相同，改成把四季的 v53/v54/v55 併排。
import fs from 'node:fs';
import {parentPort} from 'node:worker_threads';
import {loadInput} from '../../player-impact-v47/input.mjs';
import {impactEngine} from '../../player-impact-v53/engine.mjs';
import {pressureCoefficients} from '../../ovr-v53-2025-26/input.mjs';
import {applyV54Shooting} from '../../ovr-v54-2025-26/shooting-eb.mjs';
import {shotOriginTables, attachShotOrigin} from '../../../src/source_shot_origin.js';
import {applyRatesReliability} from '../rates-reliability.mjs';
import {MODES, RELIABILITY_K, centerFor} from '../input.mjs';
const coef=pressureCoefficients();
const DIR='reports/ovr-v55-finisher-fix-2025-26';
const origin=JSON.parse(fs.readFileSync(`${DIR}/shot-origin.json`,'utf8'));
const tableCache=new Map();
parentPort.on('message',async job=>{try{
 const mode=job.mode??'B12',m=MODES[mode];
 if(!m)throw Error('Unknown v55 mode '+mode);
 const b=loadInput(job.season),run=await impactEngine('rotation-space');
 const roster=b.league.teams.flatMap(t=>t.roster);
 applyV54Shooting(roster,job.season);
 const info={mode};
 if(m.rates)info.rates=applyRatesReliability(roster,job.season,RELIABILITY_K);
 if(m.origin){
  if(!tableCache.has(job.season))tableCache.set(job.season,shotOriginTables(origin,[job.season]));
  const t=tableCache.get(job.season);
  info.origin=attachShotOrigin(roster,t,{center:centerFor(mode)});
  info.league=t.league;info.eb=t.eb;
 }
 b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;
 b.options.spaceCenter=JSON.parse(fs.readFileSync(`reports/player-impact-v7/${job.season}-center.json`)).fullCenter;
 let tagged=0,players=0;
 for(const p of roster){players++;const c=coef.get(p.playerId);if(c){p.pressureMeasurement={tovNonSteal:c.tovNonSteal};tagged++;}}
 const r=run(b.league,b.exposure,{seed:job.seed,options:b.options,audit:false,replay:false,indices:null});
 r.pressureCoverage={tagged,players};r.v55=info;
 fs.writeFileSync(job.file+'.tmp',JSON.stringify(r));fs.renameSync(job.file+'.tmp',job.file);
 parentPort.postMessage({job,games:r.matches.length,tagged,players,v55:info});
}catch(e){parentPort.postMessage({job,error:e.stack.split('\n').filter(l=>!l.includes('data:text/javascript;base64')).join('\n')});}});
