// C1 第一步：把 shot-origin.json 的 s̃（禁區被餵占比，2025-26、EB 後）轉成卡片回歸的第 16 個
// 屬性 originShare = 1 − s̃（自創禁區比例）。
//
// s̃ 直接重用 src/source_shot_origin.js 的 shotOriginTables()（B12 預設走的同一支函式、同一組
// 超參數 pseudoAttempts=25 / minAttempts=40、只用 2025-26 單季），不另外發明一套算法。
// 「有量測」population 的定義與 reports/ovr-v55-finisher-fix-2025-26/preregistration.md §1.3
// 逐字一致：非補籃禁區出手 >=40、且 fedA>0 且 selfA>0，全聯盟 417 人（已用 _check_origin.mjs
// 驗證過 eb.players === 417，Karlo/Jalen Smith/Queta/Gobert/Hayes/Garza 的 s̃ 都與
// report.md 的點名數字逐位對上）。
//
// 582 位卡片球員裡，另外 165 人沒有達到量測門檻（6 人 2025-26 完全沒有禁區出手，159 人出手
// 不足 40 或單邊為 0）。這些人用「角色條件先驗」補：同一張卡片位置（season-league.json 的
// pos，PG/SG/SF/PF/C）裡，417 位已量測球員的 originShare 中位數。沒有任何量測球員落在的
// 位置（理論上不會發生，PG/SG/SF/PF/C 五組裡 417 人都有覆蓋）才退回全聯盟中位數。
//
// 百分位映射規則與 scripts/build_season_league.js 逐行相同：
//   percentile(x, pool) = 100 * (pool 裡 < x 的筆數 + 0.5 * pool 裡 == x 的筆數) / |pool|
//   attr(p) = clamp(40,99, p<50 ? 40+(p-1)*30/49 : 70+(p-50)*29/49)
// pool 固定為 417 位已量測球員的 originShare 原始值（= 其他屬性用 GP>=30&MPG>=20 的 pool
// 概念相同：拿統計上可信的子母體當分位數基準，再把全部球員映進去）。
//
//   node reports/ovr-v55-card-origin-attr-2025-26/build-origin-attr.mjs
// 輸出 reports/ovr-v55-card-origin-attr-2025-26/origin-attr.json
import fs from 'node:fs';
import {shotOriginTables} from '../../src/source_shot_origin.js';

const ORIGIN_FILE = 'reports/ovr-v55-finisher-fix-2025-26/shot-origin.json';
const LEAGUE_FILE = 'data/season-league.json';
const OUT_FILE = 'reports/ovr-v55-card-origin-attr-2025-26/origin-attr.json';

const origin = JSON.parse(fs.readFileSync(ORIGIN_FILE, 'utf8'));
const league = JSON.parse(fs.readFileSync(LEAGUE_FILE, 'utf8'));
const tables = shotOriginTables(origin, ['2025-26']);

// 卡片母體：582 位唯一 playerId（與 reports/ovr-calibrated-2025-26/calibrate.py 的 cards 母體相同）。
const cards = new Map();
for (const t of league.teams) {
  for (const p of t.roster) {
    if (!cards.has(p.playerId)) cards.set(p.playerId, {playerId: p.playerId, name: p.name, pos: p.pos});
  }
}
if (cards.size !== 582) throw new Error('Expected 582 unique card players, got ' + cards.size);

// 量測母體：fedA>0 且 selfA>0 且 rimAttempts>=40（與 shotOriginTables 估 tau^2 的 eligible 定義相同）。
const measured = new Map();
for (const [pid, v] of tables.players) {
  if (v.fedA > 0 && v.selfA > 0 && v.rimAttempts >= 40) {
    measured.set(pid, {fedShare: v.fedShare, originShareRaw: 1 - v.fedShare, rimAttempts: v.rimAttempts, fedA: v.fedA, selfA: v.selfA});
  }
}
if (measured.size !== 417) throw new Error('Expected 417 measured players, got ' + measured.size);

const pool = [...measured.values()].map(v => v.originShareRaw);

// 角色條件先驗：按卡片位置分組取「已量測」球員 originShare 中位數。
const median = xs => {
  const s = [...xs].sort((a, b) => a - b);
  const n = s.length;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
};
const overallMedian = median(pool);
const byPos = new Map();
for (const [pid, card] of cards) {
  const m = measured.get(pid);
  if (!m) continue;
  const list = byPos.get(card.pos) ?? [];
  list.push(m.originShareRaw);
  byPos.set(card.pos, list);
}
const posMedian = new Map([...byPos].map(([pos, xs]) => [pos, xs.length ? median(xs) : overallMedian]));

const percentile = (x, values) => 100 * (values.filter(v => v < x).length + 0.5 * values.filter(v => v === x).length) / values.length;
const attr = p => Math.max(40, Math.min(99, p < 50 ? 40 + (p - 1) * 30 / 49 : 70 + (p - 50) * 29 / 49));

const players = {};
let imputedByPos = 0, imputedByOverall = 0;
for (const [pid, card] of cards) {
  const m = measured.get(pid);
  let raw, method;
  if (m) {
    raw = m.originShareRaw; method = 'measured';
  } else {
    const pm = posMedian.get(card.pos);
    if (Number.isFinite(pm)) { raw = pm; method = 'position-median(' + card.pos + ')'; imputedByPos++; }
    else { raw = overallMedian; method = 'overall-median'; imputedByOverall++; }
  }
  players[pid] = {
    playerId: pid, name: card.name, pos: card.pos, measured: !!m,
    fedShare: m ? +m.fedShare.toFixed(4) : null,
    rimAttempts: m ? m.rimAttempts : (tables.players.get(pid)?.rimAttempts ?? 0),
    originShareRaw: +raw.toFixed(4),
    originShareAttr: +attr(percentile(raw, pool)).toFixed(2),
    imputationMethod: method,
  };
}

const out = {
  methodology: {
    source: ORIGIN_FILE, league: LEAGUE_FILE,
    seasons: tables.seasons, pseudoAttempts: tables.pseudoAttempts, minAttemptsForTau2: tables.minAttempts,
    measuredDefinition: 'fedA>0 && selfA>0 && rimAttempts(non-putback, short zone)>=40, 2025-26 only',
    measuredPlayers: measured.size, totalCardPlayers: cards.size,
    imputation: 'position-conditional median of measured originShare (season-league.json card pos), overall median fallback if a position has zero measured players',
    imputedByPositionMedian: imputedByPos, imputedByOverallMedian: imputedByOverall,
    percentileRule: 'scripts/build_season_league.js percentile()/attr(): pool = measured players only, mapped to [40,99] with PR1=40/PR50=70/PR99=99 breakpoints',
    overallMedianRaw: +overallMedian.toFixed(4),
    positionMedianRaw: Object.fromEntries([...posMedian].map(([k, v]) => [k, +v.toFixed(4)])),
    leagueTables: {fedShare: tables.league.fedShare, eb: tables.eb},
  },
  players,
};
fs.writeFileSync(OUT_FILE, JSON.stringify(out, null, 1));
console.log(JSON.stringify({measured: measured.size, total: cards.size, imputedByPos, imputedByOverall, overallMedianRaw: +overallMedian.toFixed(4)}, null, 1));
