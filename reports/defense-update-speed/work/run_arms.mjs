// defense-update-speed 回測模擬：每個 (隊, 第 N 場快照) × 臂，對 E-208 聯盟平均隊打 S 場（換主客 s&1），同一隊各臂共用 seed（G3）。
// 引擎 sim 0.1.4，屬性底＝E-208 variant（2024-25 Q、2025-26 P），只把 onBall／help 加上該臂的窗口差值（build_arms.py）。
// 用法（repo 根目錄）：node reports/defense-update-speed/work/run_arms.mjs <arms-季.json> <shard> <nshards> <out.json> [S=200]
import fs from 'node:fs';
const [inp, shard, nsh, out, Sarg] = process.argv.slice(2); const S = Number(Sarg ?? 200), sh = Number(shard), N = Number(nsh);
const A = JSON.parse(fs.readFileSync(inp, 'utf8'));
const lib = await import(A.variant === 'Q' ? '../../E208-team-rating/lib2425.mjs' : '../../E208-team-rating/lib.mjs');
const L = await lib.setup(A.variant);
const clamp = v => Math.max(0, Math.min(120, v));
const ARMS = ['A0', 'A1', 'A2'], res = [];
A.snaps.forEach((sn, j) => {
  if (j % N !== sh) return;
  const T = L.team(String(sn.team), sn.roster), av = L.avgTeam();
  for (const arm of ARMS) {
    const d = A.deltas[sn.D][arm];
    const t = {...T, roster: T.roster.map(p => { const x = d[p.playerId]; return x && !L.missing.has(p.playerId) ? {...p, onBall: clamp(p.onBall + x[0]), help: clamp(p.help + x[1])} : p; })};
    const o = {team: sn.team, N: sn.N, arm, pf: 0, pa: 0, pof: 0, poa: 0};
    for (let s = 0; s < S; s++) {
      const swap = s & 1, r = swap ? L.game(av, t, lib.seedOf(s, sn.key)) : L.game(t, av, lib.seedOf(s, sn.key));
      o.pf += swap ? r.sb : r.sa; o.pa += swap ? r.sa : r.sb; o.pof += swap ? r.pb : r.pa; o.poa += swap ? r.pa : r.pb;
    }
    res.push(o);
  }
});
fs.writeFileSync(out, JSON.stringify({inp, S, shard: sh, N, missing: [...L.missing], res}));
console.log('done', sh, res.length);
