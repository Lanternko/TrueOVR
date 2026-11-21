import fs from 'node:fs';
import {parentPort} from 'node:worker_threads';
import {loadInput} from './input.mjs';
import {impactEngine} from './engine.mjs';
parentPort.on('message',async job=>{try{
 const b=loadInput(job.season,job.e069),run=await impactEngine('rotation-space');
 b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;b.options.spaceCenter=JSON.parse(fs.readFileSync(`reports/player-impact-v7/${job.season}-center.json`)).fullCenter;
 if(job.e069)b.options.e069=job.e069;
 const r=run(b.league,b.exposure,{seed:job.seed,options:b.options,audit:false,replay:false,indices:job.indices??null});
 delete r.options.e069;
 fs.writeFileSync(job.file,JSON.stringify(r)+'\n');
 parentPort.postMessage({job,result:{games:r.matches.length}});
}catch(e){parentPort.postMessage({job,error:e.stack.split('\n').filter(s=>!s.includes('data:text/javascript;base64')).join('\n')});}});
