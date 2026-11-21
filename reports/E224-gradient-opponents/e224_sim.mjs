// E-224 模擬端：每個名單對五支梯度隊（B5）或拉平梯度隊（A5）各打 20 場（局序 g＝20·j＋s，換主客 swap＝g&1），回傳各對手的分差總和。引擎＝E-208 的 lib（sim 0.1.4，不改）。
// 用法（在 5090 的 repo 根）：node reports/E224-gradient-opponents/e224_sim.mjs <jobs.json> <B5|A5> <shard> <nShards> <out.json>
// jobs.json＝E-223 的 work/jobs-<season>.json（variant／S／jobs 完全沿用，S＝100＝5 對手×20 場）。
import fs from 'node:fs';
import {buildOpponents, readLadder} from './e224_opp.mjs';
const [jobsPath, mode, shardArg, nArg, outPath] = process.argv.slice(2);
if (mode !== 'B5' && mode !== 'A5') throw Error('mode must be B5 or A5');
const inp = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
const lib = await import(inp.variant === 'Q' ? '../E208-team-rating/lib2425.mjs' : '../E208-team-rating/lib.mjs');
const L = await lib.setup(inp.variant), sh = Number(shardArg), N = Number(nArg), S = inp.S, PER = S / 5;
if (!Number.isInteger(PER) || PER % 2) throw Error('S must be 5 × even');
const lad = readLadder(inp.variant === 'Q' ? '2425' : '2526');
const season = L.avgTeam().season;
const opps = buildOpponents(L, lad, mode, season).teams.map(t => ({name: t.name, season, roster: t.roster}));
const res = [];
inp.jobs.forEach((j, ji) => {
  if (ji % N !== sh) return;
  const t = L.team('T' + j.key, j.roster), per = opps.map(() => ({n: 0, msum: 0, m2: 0}));
  for (let g = 0; g < S; g++) {
    const o = Math.floor(g / PER), av = opps[o], swap = g & 1;
    const r = swap ? L.game(av, t, lib.seedOf(g, j.seedKey)) : L.game(t, av, lib.seedOf(g, j.seedKey));
    const d = swap ? r.sb - r.sa : r.sa - r.sb;
    per[o].n++; per[o].msum += d; per[o].m2 += d * d;
  }
  res.push({key: j.key, opp: per});
});
fs.writeFileSync(outPath, JSON.stringify({shard: sh, N, S, mode, missing: [...L.missing].length, res}));
console.log('done', mode, sh, res.length);
