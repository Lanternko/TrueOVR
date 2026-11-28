// E-142 c0s worker: sim 0.1.1 = src/ at the exported commit, plain v53 engine, E-065 winimp-core (unchanged, no hooks).
import {parentPort} from 'node:worker_threads';
const {loadX, makeRunner, computeDraws} = await import('../../card-0.1.2+E065-inout-wins/winimp-core.mjs');
const r = await makeRunner(), X = await loadX();
parentPort.on('message', job => {try {
  const t0 = Date.now();
  parentPort.postMessage({job, result: {id: job.id, avg: computeDraws(r, X, job, 'avg')}, ms: Date.now() - t0});
} catch (e) {parentPort.postMessage({job, error: e.stack});}});
