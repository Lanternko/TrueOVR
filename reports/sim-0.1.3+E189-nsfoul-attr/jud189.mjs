// E-189 judgement runs: seeds 20261210-241 x {base, odd, even}, constants from calibration.json. Same-seed double run for seed 20261210 odd.
import fs from 'node:fs';
import {spawn} from 'node:child_process';
const HERE = 'reports/sim-0.1.3+E189-nsfoul-attr', OUT = HERE + '/out/jud', cal = JSON.parse(fs.readFileSync(HERE + '/calibration.json', 'utf8')).final;
fs.mkdirSync(OUT, {recursive: true});
const jobs = [];
for (let s = 20261210; s <= 20261241; s++) {
  jobs.push(['base', s, []]);
  for (const a of ['odd', 'even']) jobs.push([a, s, ['--attr', a, '--base', cal.m, '--c', cal.c, '--pace', cal.pace]]);
}
jobs.push(['odd2', 20261210, ['--attr', 'odd', '--base', cal.m, '--c', cal.c, '--pace', cal.pace]]);
const run = ([tag, s, extra]) => new Promise((res, rej) => {
  const p = spawn('node', [HERE + '/worker189.mjs', '--seed', s, '--out', `${OUT}/${tag}-${s}.json`, ...extra], {stdio: ['ignore', 'ignore', 'inherit']});
  p.on('exit', c => c ? rej(Error('w' + c)) : res());
});
await Promise.all(Array.from({length: 18}, async () => { while (jobs.length) await run(jobs.shift()); }));
fs.writeFileSync(HERE + '/out/jud.done', 'ok'); console.log('JUD DONE');
