// E-166 WinImp checkpoint under beta*k (E-140 winimp-run-e140 design: MIN>=500 population, E-065 seeds/samples, resumable).
// node reports/E166/winimp-run166.mjs --k K --c C --pace P --out checkpoint-k.jsonl [--workers 20]   (cwd = tree root)
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
import {arg} from './core189.mjs'; import {loadX} from '../E140-foul-on-recal/winimp-core-e140.mjs';
const dir = 'reports/sim-0.1.3+E189-nsfoul-attr/out', attr = arg('attr'), workers = +arg('workers', 20), c = +arg('c'), pace = +arg('pace'), base = +arg('base', 1);
if (!attr) throw Error('need --attr');
const seeds = JSON.parse(fs.readFileSync('reports/card-0.1.2+E065-inout-wins/seeds.json', 'utf8'));
const {x} = await loadX(), rows = fs.readFileSync('reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv', 'utf8').trim().split('\n'), head = rows[0].split(',');
const ni = head.indexOf('name'), mi = head.indexOf('MIN'), byName = new Map();
for (const p of x.players) { if (byName.has(p.name)) throw Error('dup name ' + p.name); byName.set(p.name, p.playerId); }
const ids = []; for (const l of rows.slice(1)) { const r = l.split(','); if (+r[mi] >= 500) { const id = byName.get(r[ni]); if (id == null) throw Error('no match ' + r[ni]); ids.push(id); } }
ids.sort((a, b) => a - b);
const cf = dir + '/' + arg('out');
const done = new Set(fs.existsSync(cf) ? fs.readFileSync(cf, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l).id) : []);
const jobs = ids.filter(id => !done.has(id)).map(id => ({id, seed: seeds.baseSeed, samples: seeds.samples}));
console.log(JSON.stringify({attr, c, pace, population: ids.length, remaining: jobs.length, workers, checkpoint: cf}));
let next = 0, finished = 0; const pool = [], t0 = Date.now();
await new Promise((resolve, reject) => {
  if (!jobs.length) return resolve();
  const dispatch = w => { if (next < jobs.length) w.postMessage(jobs[next++]); };
  for (let n = 0; n < Math.min(workers, jobs.length); n++) {
    const w = new Worker(new URL('./winimp-worker189.mjs', import.meta.url), {workerData: {attr, c, pace, base}}); pool.push(w); w.on('error', reject);
    w.on('message', m => {
      if (m.error) return reject(Error(m.error));
      fs.appendFileSync(cf, JSON.stringify(m.result) + '\n'); finished++;
      if (finished % 20 === 0 || finished === jobs.length) { const s = (Date.now() - t0) / 1000; console.log(JSON.stringify({finished, remaining: jobs.length - finished, etaMinutes: Math.round(s / finished * (jobs.length - finished) / 60)})); }
      if (finished === jobs.length) resolve(); else dispatch(w);
    }); dispatch(w);
  }
}).finally(() => Promise.all(pool.map(w => w.terminate())));
console.log('done');
