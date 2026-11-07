import {parentPort,workerData} from 'node:worker_threads';
const {loadX,makeRunner,playSeed,allPairs}=await import('./rr-core.mjs');
const {x}=await loadX(),r=await makeRunner(workerData.fatigue);
parentPort.on('message',seed=>{parentPort.postMessage({seed,records:playSeed(r,x,seed,allPairs(x.opponents.length))});});
