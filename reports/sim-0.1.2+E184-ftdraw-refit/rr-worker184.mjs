import {parentPort, workerData} from 'node:worker_threads';
const {makeRunner, loadX, withPlayerBox} = await import('./core184.mjs');
const {playSeed, allPairs} = await import('../E140-foul-on-recal/rr-core.mjs');
const {x} = await loadX(), r = await makeRunner(workerData);
parentPort.on('message', seed => { const players = {}; const records = playSeed(withPlayerBox(r, players), x, seed, allPairs(x.opponents.length)); parentPort.postMessage({seed, records, players}); });
