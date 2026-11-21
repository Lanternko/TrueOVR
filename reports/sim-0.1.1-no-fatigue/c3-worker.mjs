import {parentPort,workerData} from 'node:worker_threads';
import {engine} from './common.mjs';
import {loadX,computeDraws} from '../card-0.1.2+E065-inout-wins/winimp-core.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
const run=await engine(workerData.mode),src=source(),X=await loadX(),r={src,run};
parentPort.on('message',job=>{try{parentPort.postMessage({job,result:{id:job.id,avg:computeDraws(r,X,job,'avg'),pos:computeDraws(r,X,job,'pos')}});}catch(e){parentPort.postMessage({job,error:e.stack});}});
