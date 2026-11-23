import {parentPort, workerData} from 'node:worker_threads';
const {makeRunner, loadX} = await import('./core309.mjs');
const {playSeed, allPairs} = await import('../E140-foul-on-recal/rr-core.mjs');
const {x} = await loadX(workerData.arm), r = await makeRunner(workerData);
parentPort.on('message', seed => parentPort.postMessage({seed, records: playSeed(r, x, seed, allPairs(x.opponents.length))}));
