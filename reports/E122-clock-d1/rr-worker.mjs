import {parentPort,workerData} from 'node:worker_threads';
const {loadX,makeRunner,playSeed,allPairs}=await import('./rr-core.mjs');
const {loadBeta}=await import('./winimp-core-e122.mjs');
const {x}=await loadX(),r=await makeRunner(workerData.beta==='on'?loadBeta():null);
parentPort.on('message',seed=>{parentPort.postMessage({seed,records:playSeed(r,x,seed,allPairs(x.opponents.length))});});
