// marginal.js — 每個屬性值多少分？
//
// 判斷一個屬性該不該存在的唯一可靠工具：把它從 45 拉到 95，
// 在三種對手強度下各值多少「每回合得分」。
// 在所有對局都接近 0 的屬性，就該砍掉或合併。
//
// 進攻屬性看自己的得分增加，防守屬性看對手的得分減少。

import { BASELINE } from '../src/teams.js';
import { monteCarlo } from '../src/simulation_engine.js';

const N = 3000;
const OPTS = { mode: 'race', targetScore: 21, winBy: 1 };

const team = (over) => ({
  name: 'T', season: 's',
  roster: BASELINE.roster.map(p => ({ ...p, ...over })),
});
const D = (v) => team({ onBall: v, help: v });
const ppp = (A, B) => {
  const r = monteCarlo(A, B, N, OPTS);
  return r.avgScoreA / (r.avgPossessions / 2);
};

const OFF = [
  ['三分', 'long'], ['中投', 'mid'], ['近射', 'short'], ['切入', 'drive'],
  ['傳球', 'pass'], ['罰球', 'ft'], ['失誤', 'tovSkill'],
  ['無球', 'offBall'], ['擋拆', 'screen'], ['肉體', 'physique'],
  ['持球', 'handle'], ['破包夾', 'breakDbl'],
];
// 隊友情境屬性（無球/擋拆/傳球）：全隊一起改會低估，因為持球者自己的那份不算數。
// 這裡照全隊改，量的是「陣容綜效」而不是「單卡價值」。
const DEF = [['盯防', 'onBall'], ['護框', 'help']];
const LEVELS = [['弱 40', 40], ['中 70', 70], ['強 99', 99]];

console.log(`\n=== 屬性邊際價值：45 -> 95，每回合得分變化 · n=${N} ===`);
console.log('進攻屬性 = 自己多得多少；防守/籃板 = 對手少得多少\n');
console.log('屬性      對弱      對中      對強       最大值');

const results = [];
for (const [label, key] of OFF) {
  const cells = [];
  for (const [, v] of LEVELS) {
    cells.push(ppp(team({ [key]: 95 }), D(v)) - ppp(team({ [key]: 45 }), D(v)));
  }
  results.push([label, cells]);
}
// 防守與籃板：改守方屬性，看對手得分下降多少。
// 三欄變動的是**進攻方強度**（不是防守方），否則三欄會是同一個數字。
const O = (v) => team({ long: v, mid: v, short: v, drive: v, pass: v });
for (const [label, key] of [...DEF, ['籃板', 'rebound']]) {
  const cells = [];
  for (const [, v] of LEVELS) {
    cells.push(ppp(O(v), team({ [key]: 45 })) - ppp(O(v), team({ [key]: 95 })));
  }
  results.push([label, cells]);
}
// 體力：長局才看得出來，用固定 60 回合量
{
  const long = { mode: 'fixed', possessions: 60 };
  const p = (o) => {
    const r = monteCarlo(team(o), D(70), N, long);
    return r.avgScoreA / (r.avgPossessions / 2);
  };
  const d = p({ stamina: 95 }) - p({ stamina: 45 });
  results.push(['體力*', [NaN, d, NaN]]);
}

results.sort((a, b) => Math.max(...b[1].filter(x => !isNaN(x))) - Math.max(...a[1].filter(x => !isNaN(x))));
for (const [label, c] of results) {
  const f = (x) => isNaN(x) ? '    —  ' : (x >= 0 ? '+' : '') + x.toFixed(3);
  const mx = Math.max(...c.filter(x => !isNaN(x)));
  const flag = mx < 0.010 ? '  <- 接近 0，考慮砍掉或合併' : '';
  console.log(`${label.padEnd(8)}  ${f(c[0]).padStart(7)}   ${f(c[1]).padStart(7)}   ${f(c[2]).padStart(7)}    ${f(mx)}${flag}`);
}
console.log('\n* 體力用固定 60 回合量（21 分制太短，疲勞來不及累積）');
console.log('  參考尺度：PR50 對 PR50 的每回合得分約 1.16\n');
