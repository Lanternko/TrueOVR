import {parentPort, workerData} from 'node:worker_threads';
const {registerE086} = await import('../sim-0.1.0+E086-param-screen/boot.mjs'); registerE086();
const {loadX, makeRunner, computeDraws} = await import('./winimp-core-135.mjs');
const X = await loadX(workerData.ch1), r = await makeRunner(workerData.ch1);
parentPort.on('message', job => {try {
  const t0 = Date.now(), result = {id: job.id, avg: computeDraws(r, X, job, 'avg')};
  parentPort.postMessage({job, result, ms: Date.now() - t0});
} catch (e) {parentPort.postMessage({job, error: e.stack});}});
