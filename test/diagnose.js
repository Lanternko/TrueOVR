// diagnose.js — 檢查球權分布、出手區域佔比、以及「防守否決逼出中距離」是否成立
import { TEAMS, BASELINE, SMALLBALL } from '../src/teams.js';
import { simulateGame, monteCarlo, teamRebound } from '../src/simulation_engine.js';
import * as M from '../src/probability_model.js';

const N = 1500;
const OPTS = { mode: 'race', targetScore: 21, winBy: 1 };
const keys = Object.keys(TEAMS);

console.log('\n=== 球權分布（該隊 possession 中各人出手比例）===');
console.log('NBA 真實範圍：頭號球星 USG% 約 28-35%，第五人約 10-14%\n');
for (const k of keys) {
  const counts = new Map(TEAMS[k].roster.map(p => [p.name, 0]));
  let total = 0;
  for (let i = 0; i < N; i++) {
    const g = simulateGame(TEAMS[k], BASELINE, { ...OPTS, seed: i * 7919 });
    for (const e of g.log) if (e.off === 0) { counts.set(e.handler, counts.get(e.handler) + 1); total++; }
  }
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  console.log(`${TEAMS[k].name}   （對 PR50 基準隊）`);
  for (const [n, c] of rows) console.log(`  ${n.padEnd(26)} ${(100 * c / total).toFixed(1)}%`);
  console.log('');
}

console.log('=== 出手區域佔比（對 PR50 基準隊）===');
console.log('對照真實：2025-26 聯盟 近.483 中.110 遠.407｜2001-02 近.437 中.378 遠.184\n');
console.log('隊伍              近射    中投    三分    eFG%   每回合得分');
for (const k of keys) {
  const r = monteCarlo(TEAMS[k], BASELINE, 3000, OPTS);
  const s = r.statA;
  console.log(`  ${TEAMS[k].name.padEnd(14)} ${s.shortRate.toFixed(3)}  ${s.midRate.toFixed(3)}  ${s.longRate.toFixed(3)}  ${s.efg.toFixed(3)}   ${(r.avgScoreA / (r.avgPossessions / 2)).toFixed(3)}`);
}

console.log('\n=== 防守否決：中距離是被逼出來的嗎 ===');
console.log('同一支 PR50 進攻，只改對手的盯防與護框\n');
const mk = (onBall, help) => ({
  name: `D${onBall}/${help}`, season: 'synthetic',
  roster: Array.from({ length: 5 }, (_, i) =>
    ({ name: `d${i}`, pos: 'C', long: 70, mid: 70, short: 70, drive: 70, tovSkill: 70,
       rebound: 70, onBall, help, stamina: 70, physique: 70, offBall: 70, screen: 70 })),
});
console.log('對手盯防/護框      近射    中投    三分    每回合得分');
for (const [ob, hp] of [[40, 40], [55, 55], [70, 70], [85, 85], [99, 99]]) {
  const r = monteCarlo(BASELINE, mk(ob, hp), 3000, OPTS);
  const s = r.statA;
  console.log(`  ${String(ob).padStart(3)} / ${String(hp).padStart(3)}        ${s.shortRate.toFixed(3)}  ${s.midRate.toFixed(3)}  ${s.longRate.toFixed(3)}   ${(r.avgScoreA / (r.avgPossessions / 2)).toFixed(3)}`);
}

console.log('\n=== 中投屬性的邊際價值：對弱防守 vs 對強防守 ===');
const midTeam = (mid) => ({
  name: `MID${mid}`, season: 'synthetic',
  roster: BASELINE.roster.map(p => ({ ...p, mid })),
});
for (const [lbl, D] of [['弱防守 (40/40)', mk(40, 40)], ['強防守 (99/99)', mk(99, 99)]]) {
  const lo = monteCarlo(midTeam(45), D, 3000, OPTS);
  const hi = monteCarlo(midTeam(95), D, 3000, OPTS);
  const gain = (hi.avgScoreA / (hi.avgPossessions / 2)) - (lo.avgScoreA / (lo.avgPossessions / 2));
  console.log(`  ${lbl}  中投 45->95 每回合得分 +${gain.toFixed(3)}   （中投佔比 ${lo.statA.midRate.toFixed(3)} -> ${hi.statA.midRate.toFixed(3)}）`);
}
console.log('');
