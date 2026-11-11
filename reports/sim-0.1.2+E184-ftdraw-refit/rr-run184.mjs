// E-184 30-team round robin (E-140 rr-core playSeed, unchanged records) + per-player FGA/FTA per seed.
// node reports/E184/rr-run184.mjs --k K --c C --pace P --a A --seeds a,b,.. --out name [--workers 20]   (cwd = tree root)
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const {arg, ARMS} = await import('./core184.mjs');
const k = +arg('k', 1), c = +arg('c', ARMS.B0.c), pace = +arg('pace', ARMS.B0.pace), a = +arg('a', 1), workers = +arg('workers', 20);
const seeds = arg('seeds').split(',').map(Number);
const cf = new URL('./' + arg('out') + '.jsonl', import.meta.url);
const done = new Set(fs.existsSync(cf) ? fs.readFileSync(cf, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l).seed) : []);
const todo = seeds.filter(s => !done.has(s)); let next = 0, fin = 0; const pool = [];
console.log(JSON.stringify({k, c, pace, a, remaining: todo.length}));
await new Promise((res, rej) => {
  if (!todo.length) return res();
  for (let n = 0; n < Math.min(workers, todo.length); n++) {
    const w = new Worker(new URL('./rr-worker184.mjs', import.meta.url), {workerData: {k, c, pace, a}}); pool.push(w); w.on('error', rej);
    w.on('message', m => { fs.appendFileSync(cf, JSON.stringify(m) + '\n'); if (++fin === todo.length) res(); else if (next < todo.length) w.postMessage(todo[next++]); });
    w.postMessage(todo[next++]);
  }
}).finally(() => Promise.all(pool.map(w => w.terminate())));
console.log('done');
