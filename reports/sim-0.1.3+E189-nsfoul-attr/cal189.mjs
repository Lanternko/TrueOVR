// E-189 calibration driver (R-115: one re-solve). Runs on the 5090 (cwd = tree root).
//  step 0: baseline sim 0.1.3 on the calibration seeds 20261190-205 (flag off).
//  step 1: nsBase m so that league non-shooting-foul FT per team-game = baseline +-1% (attr = odd).
//  step 2: foul base c and pace multiplier (E-166 method) so foulPer100 +-0.5% rel and possessions +-0.1 per team-game vs baseline.
//  step 3: recheck nsFT with final (m,c,pace); check attr-even with the same constants (no refit).
import fs from 'node:fs';
import {spawn} from 'node:child_process';
const HERE = 'reports/sim-0.1.3+E189-nsfoul-attr', OUT = HERE + '/out/cal', SEEDS = Array.from({length: 16}, (_, i) => 20261190 + i);
fs.mkdirSync(OUT, {recursive: true});
const C013 = -0.05625, P013 = 0.998125, log = [];
const say = s => { console.log(s); log.push(s); fs.writeFileSync(HERE + '/calibration.log', log.join('\n') + '\n'); };
const runOne = (tag, seed, o) => new Promise((res, rej) => {
  const f = `${OUT}/${tag}-${seed}.json`;
  const a = [HERE + '/worker189.mjs', '--seed', seed, '--out', f, '--nolineup', 1];
  if (o.attr) a.push('--attr', o.attr); if (o.base !== undefined) a.push('--base', o.base); if (o.c !== undefined) a.push('--c', o.c); if (o.pace !== undefined) a.push('--pace', o.pace);
  const p = spawn('node', a, {stdio: ['ignore', 'ignore', 'inherit']}); p.on('exit', code => code ? rej(Error('worker ' + code)) : res(f));
});
async function batch(tag, o) {
  const q = [...SEEDS], files = [];
  await Promise.all(Array.from({length: 16}, async () => { while (q.length) { const s = q.shift(); files.push(await runOne(tag, s, o)); } }));
  let g = 0; const S = {poss: 0, pts: 0, fta: 0, ftm: 0, shoot: 0, and1: 0, nsFt: 0, nsFoul: 0};
  for (const f of files) for (const r of JSON.parse(fs.readFileSync(f, 'utf8')).records) {
    g += 2; S.poss += r.possA + r.possB; S.pts += r.ptsA + r.ptsB; S.fta += r.ftaA + r.ftaB; S.ftm += r.ftmA + r.ftmB;
    S.shoot += r.foulShootA + r.foulShootB; S.and1 += r.foulAndA + r.foulAndB; S.nsFt += r.nsFtA + r.nsFtB; S.nsFoul += r.nsFoulA + r.nsFoulB;
  }
  const m = {teamGames: g, possPerTG: S.poss / g, ptsPerTG: S.pts / g, ftaPerTG: S.fta / g, nsFtPerTG: S.nsFt / g, nsFoulPerTG: S.nsFoul / g, foulPer100: 100 * (S.shoot + S.and1) / S.poss};
  say(`${tag} ${JSON.stringify(o)} -> ${JSON.stringify(m)}`); return m;
}
const base = await batch('base', {});
const tgt = {nsFt: base.nsFtPerTG, foul: base.foulPer100, poss: base.possPerTG};
const res = {baseline: base, steps: []};
let m = 1, c = C013, pace = P013;
// step 1: m
for (let i = 0; i < 4; i++) {
  const x = await batch(`m${i}`, {attr: 'odd', base: m, c, pace}); res.steps.push({step: 'm', m, c, pace, ...x});
  const r = x.nsFtPerTG / tgt.nsFt; say(`  nsFT ratio ${r.toFixed(4)}`);
  if (Math.abs(r - 1) <= 0.01 && i >= 0) break; m = +(m / r).toFixed(5);
}
const mFinal = m;
// step 2: c (foulPer100), pace (possessions); <=3 rounds
let cPrev = null;
for (let round = 0; round < 3; round++) {
  const x = await batch(`cp${round}`, {attr: 'odd', base: mFinal, c, pace}); res.steps.push({step: 'cp', m: mFinal, c, pace, ...x});
  const fr = x.foulPer100 / tgt.foul - 1, dp = x.possPerTG - tgt.poss; say(`  foulPer100 rel ${(100 * fr).toFixed(3)}%  poss diff ${dp.toFixed(3)}`);
  if (Math.abs(fr) <= 0.005 && Math.abs(dp) <= 0.1) break;
  // foulPer100 ~ monotone increasing in c: log-linear slope estimate; first guess slope 1 (logit-ish), refined by secant
  let slope = 1; if (cPrev && Math.abs(c - cPrev.c) > 1e-9) slope = Math.log(x.foulPer100 / cPrev.f) / (c - cPrev.c);
  cPrev = {c, f: x.foulPer100};
  if (Math.abs(fr) > 0.005) c = +(c - Math.log(1 + fr) / slope).toFixed(5);
  if (Math.abs(dp) > 0.1) pace = +(pace * tgt.poss / x.possPerTG).toFixed(6);
}
const fin = await batch('final-odd', {attr: 'odd', base: mFinal, c, pace}); res.final = {m: mFinal, c, pace, odd: fin};
const fe = await batch('final-even', {attr: 'even', base: mFinal, c, pace}); res.final.even = fe;
res.targets = tgt; res.ok = {nsFt: Math.abs(fin.nsFtPerTG / tgt.nsFt - 1) <= 0.01, foul: Math.abs(fin.foulPer100 / tgt.foul - 1) <= 0.005, poss: Math.abs(fin.possPerTG - tgt.poss) <= 0.1,
  pts: Math.abs(fin.ptsPerTG / base.ptsPerTG - 1) < 0.01, fta: Math.abs(fin.ftaPerTG / base.ftaPerTG - 1) < 0.01};
fs.writeFileSync(HERE + '/calibration.json', JSON.stringify(res, null, 1)); say('FINAL ' + JSON.stringify({m: mFinal, c, pace, ok: res.ok}));
