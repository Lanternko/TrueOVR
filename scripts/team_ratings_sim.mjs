// 每日球隊評分的模擬端（E-208 第二階段；R-158 起對手改成 E-224 的五支梯度隊 B5）。沿用 reports/E208-team-rating/lib.mjs（F 變體）與 run_fwd.mjs 的 rating 工作：
// 每個 (球隊, 版本) 名單對五支梯度隊各打 S/5 場（局序 s 的對手＝floor(s/(S/5))），換主客 swap＝s&1、種子 seedOf(s, 500+ti)（ti＝球隊 id 排序後的序號，兩個版本共用，減少雜訊）。
// 梯度隊建法照 reports/E224-gradient-opponents/e224_opp.mjs（凍結參考）：第 j 隊第 k 個位置的守位＝O[(j+k-1)%5]，能力值＝同位置、MIN 夠的候選中 OVR 最接近 Ladder_k 的三人等權平均；
// 候選與 Ladder 來自 inp.ladder（scripts/build_gradient_ladder.py 產出）；候選用原始卡能力值（不套本季 live 差值），沒有 sim 屬性的人排除並記在輸出的 excluded。
// 用法：node scripts/team_ratings_sim.mjs <input.json> <shard> <nShards> <out.json> [seeds=200]
// input.json：{attrs, deltas:{pid:{attr:δ}}, newPlayers:[pid], jobs:[{team, ver, roster:[[pid,min],…]}], teamIds:[排序後全部球隊 id], ladder:{ladder:[9], mins:[9], candidates:[{pid,pos,ovr,min}]}}
// 不改 src/；引擎、options() 與 E-208 凍結檔相同（sim 0.1.4）。
import fs from 'node:fs';
import {loadX, makeRunner} from '../reports/E120-foul-defense/winimp-core-e120.mjs';
import {options} from '../reports/player-impact-v29/benchmark.mjs';

const [inPath, shardArg, nArg, outPath, seedsArg] = process.argv.slice(2);
const S = Number(seedsArg ?? 200), sh = Number(shardArg), N = Number(nArg);
const inp = JSON.parse(fs.readFileSync(inPath, 'utf8'));
const clamp = v => Math.max(0, Math.min(120, v));
const seedOf = (s, key) => ((Math.imul(s + 1, 7919) + Math.imul(key + 1, 1000003)) >>> 0);

const {x, xAvg} = await loadX(); const {run} = await makeRunner();
const byId = new Map(x.players.map(p => [p.playerId, p]));
const avg = xAvg.profiles[2], newSet = new Set(inp.newPlayers), missing = new Set(), based = new Set(), cache = new Map(), baseOf = inp.base ?? {};
const profile = pid => {
  if (cache.has(pid)) return cache.get(pid);
  let p = byId.get(pid); const d = inp.deltas[pid], b = baseOf[pid];
  if (newSet.has(pid) || !p) {
    p = {...avg, playerId: pid, name: 'new' + pid};
    if (d) for (const a of inp.attrs) p[a] = clamp(avg[a] + d[a]);
    if (b) {      // E-216：底卡（過去賽季）能力值＝聯盟平均 + 該卡內相對聯盟平均的差；有 live 列時 d 已含 live，與底卡 + (live − 底卡) 相同
      based.add(pid);
      if (!d) for (const a of inp.attrs) p[a] = clamp(avg[a] + b.off[a]);
      p.pos = p.courtPosition = b.pos; p.heightInches = b.heightInches;
    } else missing.add(pid);
  } else {
    p = {...p}; if (d) for (const a of inp.attrs) p[a] = clamp(p[a] + d[a]);
  }
  cache.set(pid, p); return p;
};
const team = (name, roster) => {
  const tot = roster.reduce((a, [, m]) => a + m, 0), k = 240 / tot;
  return {name, season: '2025-26', roster: roster.map(([pid, m]) => ({...profile(pid), targetMinutes: m * k, injured: false}))};
};
const O = ['PG', 'SG', 'SF', 'PF', 'C'];
// 遞迴等權平均（同 E-224 的 avgProfiles）：數字取平均；陣列、null、非物件取第一個；物件逐鍵平均。
const avgProfiles = ps => {
  const f = ps[0];
  if (typeof f === 'number') return ps.reduce((a, v) => a + v, 0) / ps.length;
  if (Array.isArray(f) || f === null || typeof f !== 'object') return f;
  const o = {};
  for (const k of Object.keys(f)) o[k] = avgProfiles(ps.map(p => p?.[k]).map(v => v === undefined ? f[k] : v));
  return o;
};
const excluded = [];
const buildOpponents = lad => {
  const cand = lad.candidates.filter(c => { if (byId.has(c.pid)) return true; excluded.push(c.pid); return false; });
  const teams = [];
  for (let j = 0; j < 5; j++) {
    const roster = [];
    for (let k = 1; k <= 9; k++) {
      const pos = O[(j + k - 1) % 5], target = lad.ladder[k - 1];
      const pick = cand.filter(c => c.pos === pos).sort((a, b) => Math.abs(a.ovr - target) - Math.abs(b.ovr - target) || b.min - a.min || a.pid - b.pid).slice(0, 3);
      if (pick.length < 3) throw Error(`gradient opponent T${j} slot ${k} ${pos}: only ${pick.length} candidates`);
      const profs = pick.map(c => ({...byId.get(c.pid)})), nearest = profs[0], a = avgProfiles(profs);
      for (const key of Object.keys(nearest)) if (typeof nearest[key] !== 'number' && (typeof nearest[key] !== 'object' || nearest[key] === null)) a[key] = nearest[key];   // 非數值欄位取最近者
      Object.assign(a, {playerId: -(1 + j * 9 + (k - 1)), name: `grad-T${j}-S${k}-${pos}`, targetMinutes: lad.mins[k - 1], injured: false});
      roster.push(a);
    }
    teams.push({name: `grad-T${j}`, season: '2025-26', roster});
  }
  return teams;
};
const opps = buildOpponents(inp.ladder), PER = S / 5;
if (!Number.isInteger(PER) || PER % 2) throw Error('seeds must be 5 × even');
const game = (tA, tB, seed) => {
  const poss = [0, 0];
  const g = run(tA, tB, {...options(x, seed, undefined), eventObserver: e => { if (e.type === 'POSSESSION') poss[e.off]++; }});
  if (g.gameSeconds !== 2880 || !g.complete) throw Error('Incomplete game');
  return {sa: g.scoreA, sb: g.scoreB, pa: poss[0], pb: poss[1]};
};
const res = [];
inp.jobs.forEach((j, ji) => {
  if (ji % N !== sh) return;
  const ti = inp.teamIds.indexOf(String(j.team)), t = team(j.team + j.ver, j.roster);
  const o = {team: j.team, ver: j.ver, n: S, msum: 0, pf: 0, pa: 0, pof: 0, poa: 0};
  for (let s = 0; s < S; s++) {
    const av = opps[Math.floor(s / PER)], swap = s & 1, r = swap ? game(av, t, seedOf(s, 500 + ti)) : game(t, av, seedOf(s, 500 + ti));
    const sf = swap ? r.sb : r.sa, sa = swap ? r.sa : r.sb, pf = swap ? r.pb : r.pa, pa = swap ? r.pa : r.pb;
    o.msum += sf - sa; o.pf += sf; o.pa += sa; o.pof += pf; o.poa += pa;
  }
  res.push(o);
});
fs.writeFileSync(outPath, JSON.stringify({shard: sh, N, S, missing: [...missing], based: [...based], excluded, res}));
console.log('done', sh, res.length);
