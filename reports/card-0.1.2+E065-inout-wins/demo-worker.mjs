import {parentPort} from 'node:worker_threads';
import {prepare,applyArm,runSeason} from './demo-core.mjs';
const base=await prepare();
parentPort.on('message',job=>{try{
 const b=structuredClone(base),applied=applyArm(b,job.arm),result=runSeason(b,job.seed);
 parentPort.postMessage({job,result:{armId:job.arm.id,seed:job.seed,applied,...result}});
}catch(e){parentPort.postMessage({job,error:e.stack.split('\n').filter(l=>!l.includes('base64')).join('\n')});}});
