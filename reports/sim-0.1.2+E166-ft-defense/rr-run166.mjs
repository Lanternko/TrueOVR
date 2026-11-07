// E-166 30-team round robin under beta*k (E-140 rr-core playSeed, unchanged records). node reports/E166/rr-run166.mjs --k 2 --c .. --pace .. --seeds a,b --out name [--workers 20]
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const {arg, C012, P012} = await import('./core166.mjs');
const k = +arg('k', 1), c = +arg('c', C012), pace = +arg('pace', P012), workers = +arg('workers', 20);
const rng = (a, b) => Array.from({length: b - a + 1}, (_, i) => a + i), seeds = arg('seeds', null)?.split(',').map(Number) ?? rng(20261028, 20261059);
const cf = new URL('./' + arg('out') + '.jsonl', import.meta.url);
const done = new Set(fs.existsSync(cf) ? fs.readFileSync(cf, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l).seed) : []);
const todo = seeds.filter(s => !done.has(s)); let next = 0, fin = 0; const pool = [];
console.log(JSON.stringify({k, c, pace, remaining: todo.length}));
await new Promise((res, rej) => {
  if (!todo.length) return res();
  for (let n = 0; n < Math.min(workers, todo.length); n++) {
    const w = new Worker(new URL('./rr-worker166.mjs', import.meta.url), {workerData: {k, c, pace}}); pool.push(w); w.on('error', rej);
    w.on('message', m => { fs.appendFileSync(cf, JSON.stringify(m) + '\n'); if (++fin === todo.length) res(); else if (next < todo.length) w.postMessage(todo[next++]); });
    w.postMessage(todo[next++]);
  }
}).finally(() => Promise.all(pool.map(w => w.terminate())));
console.log('done');
