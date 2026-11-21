import {parentPort} from 'node:worker_threads';
import {loadX,makeRunner,computeDraws} from './winimp-core.mjs';
const r=await makeRunner(),X=await loadX();
parentPort.on('message',job=>{try{
 parentPort.postMessage({job,result:{id:job.id,avg:computeDraws(r,X,job,'avg'),pos:computeDraws(r,X,job,'pos')}});
}catch(e){parentPort.postMessage({job,error:e.stack});}});
