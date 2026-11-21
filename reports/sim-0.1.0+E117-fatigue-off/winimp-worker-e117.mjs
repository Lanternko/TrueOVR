import {parentPort, workerData} from 'node:worker_threads';
const {loadX, makeRunner, computeDraws} = await import('./winimp-core-e117.mjs');
const r = await makeRunner(workerData.fatigue), X = await loadX();
parentPort.on('message', job => {try {
  parentPort.postMessage({job, result: {id: job.id, avg: computeDraws(r, X, job, 'avg'), pos: computeDraws(r, X, job, 'pos')}});
} catch (e) {parentPort.postMessage({job, error: e.stack});}});
