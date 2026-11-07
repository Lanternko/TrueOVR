import {parentPort, workerData} from 'node:worker_threads';
const {makeRunner, loadX, playSeed, allPairs} = await import('./core130.mjs');
const {x} = await loadX(), r = await makeRunner(workerData);
parentPort.on('message', seed => { const tally = {}; const records = playSeed(r, x, seed, allPairs(x.opponents.length), tally); parentPort.postMessage({seed, records, tally}); });
