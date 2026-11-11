// v54 full-season team run: identical to reports/player-impact-v53-team/worker.mjs (v47 full-season
// job on the v53 engine, four-factor tovNonSteal coefficients tagged, spread scale 1) except every
// 2025-26 roster player's long/short cards are swapped for the v54 reliability-aware (empirical-Bayes)
// version (../ovr-v54-2025-26/shooting-eb.mjs) right after loadInput. Other seasons are untouched --
// applyV54Shooting() no-ops outside 2025-26 (see ../ovr-v54-2025-26/report.md). variant 'v54' tags
// pressureMeasurement same as v53-team's 'v53' variant; variant 'v47' is the harness-parity check.
import fs from 'node:fs';
import {parentPort} from 'node:worker_threads';
import {loadInput} from '../player-impact-v47/input.mjs';
import {impactEngine} from '../player-impact-v53/engine.mjs';
import {pressureCoefficients} from '../ovr-v53-2025-26/input.mjs';
import {applyV54Shooting} from '../ovr-v54-2025-26/shooting-eb.mjs';
const coef=pressureCoefficients();
parentPort.on('message',async job=>{try{
 const b=loadInput(job.season),run=await impactEngine('rotation-space');
 applyV54Shooting(b.league.teams.flatMap(t=>t.roster),job.season);
 b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;b.options.spaceCenter=JSON.parse(fs.readFileSync(`reports/player-impact-v7/${job.season}-center.json`)).fullCenter;
 let tagged=0,players=0;
 if(job.variant==='v54')for(const p of b.league.teams.flatMap(t=>t.roster)){players++;const c=coef.get(p.playerId);if(c){p.pressureMeasurement={tovNonSteal:c.tovNonSteal};tagged++;}}
 const r=run(b.league,b.exposure,{seed:job.seed,options:b.options,audit:false,replay:false,indices:null});
 r.pressureCoverage={tagged,players};
 fs.writeFileSync(job.file+'.tmp',JSON.stringify(r));fs.renameSync(job.file+'.tmp',job.file);parentPort.postMessage({job,games:r.matches.length,tagged,players});
}catch(e){parentPort.postMessage({job,error:e.stack.split('\n').filter(l=>!l.includes('data:text/javascript;base64')).join('\n')});}});
