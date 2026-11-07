import {parentPort, workerData} from 'node:worker_threads';
const {loadX, makeRunner, computeDraws, loadBeta} = await import('./winimp-core-e122.mjs');
const r = await makeRunner(workerData.beta==='on'?loadBeta():null), X0 = await loadX();
// E-122: slot-placeholder profiles (control team and fillers) get playerId -1 so no D1 beta bleeds into them (same as c1). Off mode must stay bit-identical to E-120 checkpoint-off.
const strip=x=>({...x,profiles:x.profiles.map(p=>({...p,playerId:-1}))});
const X={x:strip(X0.x),xAvg:strip(X0.xAvg)};
parentPort.on('message', job => {try {
  parentPort.postMessage({job, result: {id: job.id, avg: computeDraws(r, X, job, 'avg'), pos: computeDraws(r, X, job, 'pos')}});
} catch (e) {parentPort.postMessage({job, error: e.stack});}});
