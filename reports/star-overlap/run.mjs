// star-overlap 運算腳本（診斷，不改引擎）。從 repo 根目錄跑：
//   node reports/star-overlap/run.mjs <2526|2425> <shard> <nshards> <out.json> <seeds>
// 每隊 7 個變體（同一隊共用 seed、主客輪換，G3）：v0 全平均、v1..v4 只留第 j 顆球星、v4all 四人都留、full 十人全在。
// 其餘人換成聯盟平均 profile（avgTeam().roster[2]＝xAvg.profiles[2]，同 phi3.mjs），分鐘不變。對手＝聯盟平均隊。
import fs from 'node:fs';
import {setup as setup26, seedOf} from '../E208-team-rating/lib.mjs';
import {setup as setup25} from '../E208-team-rating/lib2425.mjs';
const [season, shard, nsh, out, seedsArg] = process.argv.slice(2); const S = Number(seedsArg), sh = Number(shard), N = Number(nsh);
const here = new URL('.', import.meta.url);
const LU = JSON.parse(fs.readFileSync(new URL('lineups.json', here), 'utf8'))[season === '2526' ? '2025-26' : '2024-25'];
const L = await (season === '2526' ? setup26('P') : setup25('Q')); const av = L.avgTeam(); const avgProf = av.roster[2];
const ids = Object.keys(LU).sort(); const res = [];
const variant = (id, keep) => {
  const full = L.team(id, LU[id].rotation);
  return {...full, roster: full.roster.map((p, i) => keep === 'all' || keep.includes(p.playerId) ? p : {...avgProf, playerId: -1 - i, targetMinutes: p.targetMinutes, injured: false})};
};
ids.forEach((id, ti) => { if (ti % N !== sh) return;
  const st = LU[id].stars, V = {v0: variant(id, []), full: variant(id, 'all'), v4all: variant(id, st)};
  st.forEach((p, j) => { V['v' + (j + 1)] = variant(id, [p]); });
  const o = {id, abbr: LU[id].abbr, stars: st, m: {}, poss: {}};
  for (const k of Object.keys(V)) { o.m[k] = []; o.poss[k] = []; }
  for (let s = 0; s < S; s++) { const swap = s & 1, seed = seedOf(s, 500 + ti);
    for (const k of Object.keys(V)) { const r = swap ? L.game(av, V[k], seed) : L.game(V[k], av, seed);
      o.m[k].push(swap ? r.sb - r.sa : r.sa - r.sb); o.poss[k].push(r.pa + r.pb); } }
  res.push(o); });
fs.writeFileSync(out, JSON.stringify({season, shard: sh, N, S, missing: [...L.missing], res}));
console.log('done', season, sh, res.length);
