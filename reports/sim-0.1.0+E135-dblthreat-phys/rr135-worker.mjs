import {parentPort,workerData} from 'node:worker_threads';
const {registerE086}=await import('../sim-0.1.0+E086-param-screen/boot.mjs');registerE086();
const {loadX,makeRunner,playSeed,allPairs}=await import('./rr135-core.mjs');
const {x}=await loadX(workerData.ch1),r=await makeRunner(workerData.ch1);
parentPort.on('message',j=>{try{parentPort.postMessage(playSeed(r,x,j.seed,j.pairs??allPairs(x.opponents.length)));}catch(e){parentPort.postMessage({error:e.stack});}});
