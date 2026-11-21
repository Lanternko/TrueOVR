// v53 full-season team run: the v47 full-season job (reports/player-impact-v47/worker.mjs, legacy rotation)
// on the v53 engine, with every roster player carrying the four-factor tovNonSteal coefficient.
// Spread scale stays 1 (adopted v53). variant 'v47' = same harness without coefficients (exact v47 check).
import fs from 'node:fs';
import {parentPort} from 'node:worker_threads';
import {loadInput} from '../player-impact-v47/input.mjs';
import {impactEngine} from '../player-impact-v53/engine.mjs';
import {pressureCoefficients} from '../ovr-v53-2025-26/input.mjs';
const coef=pressureCoefficients();
parentPort.on('message',async job=>{try{
 const b=loadInput(job.season),run=await impactEngine('rotation-space');
 b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;b.options.spaceCenter=JSON.parse(fs.readFileSync(`reports/player-impact-v7/${job.season}-center.json`)).fullCenter;
 let tagged=0,players=0;
 if(job.variant==='v53')for(const p of b.league.teams.flatMap(t=>t.roster)){players++;const c=coef.get(p.playerId);if(c){p.pressureMeasurement={tovNonSteal:c.tovNonSteal};tagged++;}}
 const r=run(b.league,b.exposure,{seed:job.seed,options:b.options,audit:false,replay:false,indices:null});
 r.pressureCoverage={tagged,players};
 fs.writeFileSync(job.file+'.tmp',JSON.stringify(r));fs.renameSync(job.file+'.tmp',job.file);parentPort.postMessage({job,games:r.matches.length,tagged,players});
}catch(e){parentPort.postMessage({job,error:e.stack.split('\n').filter(l=>!l.includes('data:text/javascript;base64')).join('\n')});}});
