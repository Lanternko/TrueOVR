import {parentPort, workerData} from 'node:worker_threads';
import {makeRunner} from './core189.mjs';
import {loadX, computeDraws} from '../E140-foul-on-recal/winimp-core-e140.mjs';
const r = await makeRunner(workerData), X0 = await loadX();
// same as E-166/E-140 worker: slot-placeholder profiles get playerId -1 so no foul attribute bleeds into control team / fillers.
const strip = x => ({...x, profiles: x.profiles.map(p => ({...p, playerId: -1}))});
const X = {x: strip(X0.x), xAvg: strip(X0.xAvg)};
parentPort.on('message', job => { try {
  parentPort.postMessage({job, result: {id: job.id, avg: computeDraws(r, X, job, 'avg'), pos: computeDraws(r, X, job, 'pos')}});
} catch (e) { parentPort.postMessage({job, error: e.stack}); } });
