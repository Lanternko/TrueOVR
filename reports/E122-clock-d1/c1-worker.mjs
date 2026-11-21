import {parentPort} from 'node:worker_threads';
const {loadX,makeRunner,loadBeta}=await import('./winimp-core-e122.mjs');
const {c1Player}=await import('./c1-core.mjs');
const X=await loadX(),B=loadBeta(),live={},r=await makeRunner(live);   // live: one-entry map, mutated per job
parentPort.on('message',job=>{try{
  for(const k of Object.keys(live))delete live[k];live[job.id]=B[job.id];
  parentPort.postMessage({result:c1Player(r,X,job.id,B[job.id],job.samples,job.seed)});
}catch(e){parentPort.postMessage({error:e.stack});}});
