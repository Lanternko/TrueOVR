// v55 卡片修正 E 系列：獨立後處理腳本（不修改 scripts/build_season_league.js，
// 不碰 data/season-league.json，只讀取既有產物後另存新的 league JSON）。
// preregistration.md 記錄了完整的規則與門檻，本檔是該規則的字面實作。
//
// 用法：
//   node build-card-E.mjs --variant=E1 --k=1000  --out=season-league-E1-k1000.json
//   node build-card-E.mjs --variant=E2 --lambda=0.4 --out=season-league-E2-lam0.4.json
//   node build-card-E.mjs --variant=E3 --k=1500 --lambda=0.4 --out=season-league-E3.json
import fs from 'node:fs';
import {ATTR_MIDPOINT} from '../../src/constants.js';

const ROOT = new URL('../../', import.meta.url);
const HERE = new URL('./', import.meta.url);
const args = Object.fromEntries(process.argv.slice(2).map(a => {
  const [k, v] = a.replace(/^--/, '').split('=');
  return [k, v];
}));
const VARIANT = args.variant;
if (!['E1', 'E2', 'E3'].includes(VARIANT)) throw new Error('Need --variant=E1|E2|E3');
const K = args.k != null ? Number(args.k) : null;
const LAMBDA = args.lambda != null ? Number(args.lambda) : null;
const OUT = args.out;
if (!OUT) throw new Error('Need --out=PATH');
if ((VARIANT === 'E1' || VARIANT === 'E3') && !(K > 0)) throw new Error('E1/E3 need --k');
if ((VARIANT === 'E2' || VARIANT === 'E3') && !(LAMBDA >= 0 && LAMBDA <= 1)) throw new Error('E2/E3 need --lambda in [0,1]');

const league = JSON.parse(fs.readFileSync(new URL('data/season-league.json', ROOT), 'utf8'));
const origin = JSON.parse(fs.readFileSync(new URL('reports/ovr-v55-card-origin-attr-2025-26/origin-attr.json', ROOT), 'utf8'));
const mergedRows = fs.readFileSync(new URL('reports/ovr-v55-2k27-compare/merged.csv', ROOT), 'utf8').trim().split('\n');
const mergedHead = mergedRows[0].split(',');
const mi = k => mergedHead.indexOf(k);
const mergedByName = new Map(mergedRows.slice(1).map(line => {
  const c = line.split(',');
  return [c[mi('name')], {archetype: c[mi('archetype')], creation: Number(c[mi('creation')])}];
}));

// --- 聚合每位球員的總分鐘、姓名、位置（跨球隊站） ---------------------------
const info = new Map(); // playerId -> {name,pos,MIN}
for (const t of league.teams) {
  for (const p of t.roster) {
    if (!info.has(p.playerId)) info.set(p.playerId, {name: p.name, pos: p.pos, MIN: 0});
    info.get(p.playerId).MIN += p.observed.MIN;
  }
}

// --- E1：低分鐘屬性收縮 -----------------------------------------------------
const SHRINK_ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'onBall', 'help', 'stamina'];
function buildGroupMeans() {
  // group key = pos|archetype；用「第一個出現的 roster 卡」取原始屬性值（同一 playerId 的所有站
  // 卡片屬性本就相同，見 scripts/build_season_league.js 的 card() 以賽季總表 base 計算）。
  const firstCard = new Map();
  for (const t of league.teams) for (const p of t.roster) if (!firstCard.has(p.playerId)) firstCard.set(p.playerId, p);
  const groups = new Map(); // key -> {sumMIN, sumAttr:{attr:sum}}
  const degenerate = [];
  for (const [id, meta] of info) {
    const m = mergedByName.get(meta.name);
    const archetype = m ? m.archetype : '其他';
    const key = meta.pos + '|' + archetype;
    if (!groups.has(key)) groups.set(key, {sumMIN: 0, sumAttr: Object.fromEntries(SHRINK_ATTRS.map(a => [a, 0])), n: 0});
    const g = groups.get(key);
    const card = firstCard.get(id);
    g.sumMIN += meta.MIN;
    g.n += 1;
    for (const a of SHRINK_ATTRS) g.sumAttr[a] += card[a] * meta.MIN;
  }
  const means = new Map();
  for (const [key, g] of groups) {
    if (g.n === 1) degenerate.push(key);
    if (!(g.sumMIN > 0)) throw new Error('Group with zero total minutes: ' + key);
    means.set(key, Object.fromEntries(SHRINK_ATTRS.map(a => [a, g.sumAttr[a] / g.sumMIN])));
  }
  return {means, degenerate, groupSizes: Object.fromEntries([...groups].map(([k, g]) => [k, g.n]))};
}
let shrinkMeta = null;
function applyLowMinuteShrink(card, meta, means) {
  const archetype = mergedByName.get(meta.name)?.archetype ?? '其他';
  const key = meta.pos + '|' + archetype;
  const groupMean = means.get(key);
  const w = meta.MIN / (meta.MIN + K);
  const out = {...card};
  for (const a of SHRINK_ATTRS) out[a] = w * card[a] + (1 - w) * groupMean[a];
  return out;
}

// --- E2：吃餅折扣（固定先驗規則） -------------------------------------------
// 折扣作用在「離聯盟均值(ATTR_MIDPOINT=70)的偏離量」，不是直接乘在命中機率上：直接乘機率會讓
// Karlo 這種命中率已貼著 CURVE_SHORT 下緣的球員折完後跌出曲線定義域，inverse() 退化成地板值 40，
// 把「吃餅但終結確實不錯」跟「吃餅又真的不準」拍扁成同一個分數（preregistration.md 有記錄這個
// 用 Karlo 試跑時發現的實作問題）。
const GRAVITY_POS = new Set(['PF', 'C']);
const GRAVITY_LOW = 55, GRAVITY_HIGH = 65;
function exemptOf(pos, creation) {
  if (!GRAVITY_POS.has(pos) || !Number.isFinite(creation)) return 0;
  return Math.max(0, Math.min(1, (creation - GRAVITY_LOW) / (GRAVITY_HIGH - GRAVITY_LOW)));
}
const finishDiscountLog = [];
function applyFinishDiscount(card, meta) {
  const o = origin.players[String(card.playerId)];
  if (!o) return card; // 582 人應全覆蓋，留防呆但不應觸發
  const sTilde = o.originShareRaw;
  const m = mergedByName.get(meta.name);
  const creation = m ? m.creation : NaN;
  const exempt = exemptOf(meta.pos, creation);
  const effectiveLambda = LAMBDA + (1 - LAMBDA) * exempt;
  const discountFactor = sTilde + effectiveLambda * (1 - sTilde);
  const newShort = Math.max(40, Math.min(99, ATTR_MIDPOINT + (card.short - ATTR_MIDPOINT) * discountFactor));
  finishDiscountLog.push({name: meta.name, pos: meta.pos, sTilde, creation, exempt, effectiveLambda, discountFactor, shortBefore: card.short, shortAfter: newShort});
  return {...card, short: newShort};
}

// --- 套用並輸出 --------------------------------------------------------------
let groupMeta = null;
if (VARIANT === 'E1' || VARIANT === 'E3') {
  const built = buildGroupMeans();
  groupMeta = built;
}
for (const t of league.teams) {
  t.roster = t.roster.map(p => {
    const meta = info.get(p.playerId);
    let card = p;
    if (VARIANT === 'E1' || VARIANT === 'E3') card = applyLowMinuteShrink(card, meta, groupMeta.means);
    if (VARIANT === 'E2' || VARIANT === 'E3') card = applyFinishDiscount(card, meta);
    return card;
  });
}
league.methodology = {
  ...league.methodology,
  ...(VARIANT === 'E1' || VARIANT === 'E3' ? {lowMinuteShrink: {
    rule: 'v55 card-E E1: new = w*raw + (1-w)*groupMean, w = MIN/(MIN+k); groupMean is the MIN-weighted average of the same (card.pos, archetype) group (archetype from reports/ovr-v55-2k27-compare/merged.csv); attrs = ' + SHRINK_ATTRS.join(',') + '.',
    k: K, groupSizes: groupMeta.groupSizes, degenerateGroups: groupMeta.degenerate,
  }} : {}),
  ...(VARIANT === 'E2' || VARIANT === 'E3' ? {finishDiscount: {
    rule: 'v55 card-E E2: short only. effective_short = inverse(forward(short,CURVE_SHORT) * discountFactor, CURVE_SHORT); discountFactor = sTilde + effectiveLambda*(1-sTilde); sTilde = originShareRaw from reports/ovr-v55-card-origin-attr-2025-26/origin-attr.json; effectiveLambda = lambda + (1-lambda)*exempt; exempt = clip((creation-55)/(65-55),0,1) for pos in {PF,C} else 0; creation from reports/ovr-v55-2k27-compare/merged.csv.',
    lambda: LAMBDA, gravityPos: [...GRAVITY_POS], gravityRamp: [GRAVITY_LOW, GRAVITY_HIGH],
  }} : {}),
};
fs.mkdirSync(HERE, {recursive: true});
fs.writeFileSync(new URL(OUT, HERE), JSON.stringify(league, null, 2) + '\n');
if (finishDiscountLog.length) {
  fs.writeFileSync(new URL(OUT.replace(/\.json$/, '-finish-discount-log.json'), HERE), JSON.stringify(finishDiscountLog, null, 2) + '\n');
}
console.log(JSON.stringify({variant: VARIANT, k: K, lambda: LAMBDA, out: OUT, players: info.size}));
