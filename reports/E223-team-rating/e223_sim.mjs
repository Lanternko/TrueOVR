// E-223 模擬端：每個名單（lineup）對「聯盟平均隊」各打 S 場（換主客 swap＝s&1），回傳分差總和。引擎＝E-208 的 lib（sim 0.1.4，不改）。
// 用法（在 5090 的 repo 根）：node reports/E223-team-rating/e223_sim.mjs <jobs.json> <shard> <nShards> <out.json>
// jobs.json：{variant:'P'|'Q', S, jobs:[{key, seedKey, roster:[[pid,min],…]}]}；P＝2025-26 能力值、Q＝2024-25（E-208 的 lib.mjs／lib2425.mjs）。
import fs from 'node:fs';
const [jobsPath, shardArg, nArg, outPath] = process.argv.slice(2);
const inp = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
const lib = await import(inp.variant === 'Q' ? '../E208-team-rating/lib2425.mjs' : '../E208-team-rating/lib.mjs');
const L = await lib.setup(inp.variant), sh = Number(shardArg), N = Number(nArg), S = inp.S;
const av = L.avgTeam(), res = [];
inp.jobs.forEach((j, ji) => {
  if (ji % N !== sh) return;
  const t = L.team('T' + j.key, j.roster); let msum = 0, m2 = 0;
  for (let s = 0; s < S; s++) {
    const swap = s & 1, r = swap ? L.game(av, t, lib.seedOf(s, j.seedKey)) : L.game(t, av, lib.seedOf(s, j.seedKey));
    const d = swap ? r.sb - r.sa : r.sa - r.sb; msum += d; m2 += d * d;
  }
  res.push({key: j.key, n: S, msum, m2});
});
fs.writeFileSync(outPath, JSON.stringify({shard: sh, N, S, missing: [...L.missing].length, res}));
console.log('done', sh, res.length);
