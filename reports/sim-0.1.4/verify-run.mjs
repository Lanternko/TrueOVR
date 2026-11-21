// driver: both arms x seeds 20261250-265 (fresh: not E-189 calibration 20261190-205 nor judgement seeds). cwd = tree root.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
const OUT = 'reports/sim-0.1.4/out-verify', SEEDS = Array.from({length: 16}, (_, i) => 20261250 + i), P = +(process.argv[2] || 18);
fs.mkdirSync(OUT, {recursive: true});
const jobs = SEEDS.flatMap(s => ['on', 'off'].map(arm => ({s, arm})));
const one = ({s, arm}) => new Promise((res, rej) => { const f = `${OUT}/${arm}-${s}.json`; if (fs.existsSync(f)) return res();
  const p = spawn('node', ['reports/sim-0.1.4/verify-worker.mjs', '--seed', s, '--out', f, '--arm', arm], {stdio: ['ignore', 'inherit', 'inherit']}); p.on('exit', c => c ? rej(Error('worker ' + c)) : res()); });
const q = [...jobs]; await Promise.all(Array.from({length: P}, async () => { while (q.length) await one(q.shift()); }));
console.log('ALL DONE');
