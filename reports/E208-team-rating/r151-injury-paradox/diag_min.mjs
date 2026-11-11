// 每日球隊評分的模擬端（E-208 第二階段）。沿用 reports/E208-team-rating/lib.mjs（F 變體）與 run_fwd.mjs 的 rating 工作：
// 每個 (球隊, 版本) 名單跟「聯盟平均隊」打 S 場，換主客、種子 seedOf(s, 500+ti)（ti＝球隊 id 排序後的序號，兩個版本共用，減少雜訊）。
// 用法：node scripts/team_ratings_sim.mjs <input.json> <shard> <nShards> <out.json> [seeds=200]
// input.json：{attrs, deltas:{pid:{attr:δ}}, newPlayers:[pid], jobs:[{team, ver, roster:[[pid,min],…]}], teamIds:[排序後全部球隊 id]}
// 不改 src/；引擎、options() 與 E-208 凍結檔相同（sim 0.1.4）。
import fs from 'node:fs';
import {loadX, makeRunner} from '../../E120-foul-defense/winimp-core-e120.mjs';
import {options} from '../../player-impact-v29/benchmark.mjs';

const [inPath, outPath] = process.argv.slice(2);
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

const team = (name, roster) => { const tot = roster.reduce((a, [, m]) => a + m, 0), k = 240 / tot;
  return {name, season: '2025-26', roster: roster.map(([pid, m]) => ({...profile(pid), targetMinutes: m * k, injured: false}))}; };
const av = {name: 'league-average', season: '2025-26', roster: xAvg.profiles.concat(xAvg.profiles).map((p, i) => ({...p, playerId: -1 - i, targetMinutes: 24, injured: false}))};
const out = [];
for (const j of inp.jobs) {
  const t = team(j.ver, j.roster), acc = new Map();
  for (let s = 0; s < 200; s++) {
    const swap = s & 1, g = swap ? run(av, t, options(x, seedOf(s, 500 + inp.ti), undefined)) : run(t, av, options(x, seedOf(s, 500 + inp.ti), undefined));
    for (const p of (swap ? g.playersB : g.playersA)) { const a = acc.get(p.name) ?? {sec: 0, pts: 0, pf: 0, fga: 0, tov: 0, ast: 0, reb: 0, n: 0}; a.sec += p.seconds; a.pts += p.pts; a.pf += p.pf; a.fga += p.fga; a.tov += p.tov; a.ast += p.ast; a.reb += p.oreb + p.dreb; a.n++; acc.set(p.name, a); }
  }
  out.push({ver: j.ver, players: Object.fromEntries([...acc].map(([k, a]) => [k, {min: +(a.sec / a.n / 60).toFixed(1), pts36: +(a.pts / a.sec * 2160).toFixed(1), pf: +(a.pf / a.n).toFixed(2), tov: +(a.tov / a.n).toFixed(1), ast: +(a.ast / a.n).toFixed(1), reb: +(a.reb / a.n).toFixed(1)}]))});
}
fs.writeFileSync(outPath, JSON.stringify(out));
