// probability_model.js — 屬性 -> possession 事件機率
//
// 階層式分解（照 Nine_innings 的作法）：
//   L1  possession 大類：TOV / FOUL / SHOT
//   L2  出手區域 (given SHOT)：三分 / 中投 / 近射
//   L3  命中 (given 區域)
//   L4  未命中 -> 進攻籃板
// 每層 clamp，最後 normalize。
//
// 持球者不是靠靜態 usage 權重抽出來的，而是每次進攻機會比較五個人的期望得分
// （見 evaluateLineup / chooseHandler）——這才是「傳球直到找到夠好的出手點」。

import * as C from './constants.js';
import { shotOriginAdjustment } from './source_shot_origin.js';

// --- 輔助 ---------------------------------------------------------------

/** 分段線性插值。anchors 為 [[x,y],...]，依 x 遞增。 */
export function interpolate(value, anchors) {
  const v = Math.min(value, C.ATTR_SOFT_CAP);
  if (v <= anchors[0][0]) return anchors[0][1];
  if (v >= anchors[anchors.length - 1][0]) return anchors[anchors.length - 1][1];
  for (let i = 0; i < anchors.length - 1; i++) {
    const [x1, y1] = anchors[i], [x2, y2] = anchors[i + 1];
    if (v >= x1 && v < x2) {
      if (x2 === x1) return y1;
      return y1 + (y2 - y1) * (v - x1) / (x2 - x1);
    }
  }
  return anchors[anchors.length - 1][1];
}

/** 屬性 -> -1..1 的 effectiveness。 */
export function tanhEff(attr, scale = 40, midpoint = C.ATTR_MIDPOINT) {
  if (scale === 0) return 0;
  return Math.tanh((attr - midpoint) / scale);
}

export const clamp = (x, [lo, hi]) => Math.max(lo, Math.min(hi, x));

const logistic = (x) => 1 / (1 + Math.exp(-x));

// --- 隊伍情境（每個陣容算一次）------------------------------------------

/**
 * 場上其他四人提供給持球者的情境。
 *
 * 無球與空間刻意分開，這是兩件常被混為一談的事：
 *   無球 = 他會不會跑（切、繞掩護、拉開接球）-> 傳得出去、接得到球
 *   空間 = 不看他行不行（定點投射威脅）      -> 命中率、三分可及性、放空稅
 * Draymond 兩者相反：跑動與掩護一流，但站在三分線外沒人理他。
 * 把兩者綁成同一個屬性，就只能二選一地弄錯其中一邊。
 */
export function teammateContext(lineup, handlerIdx) {
  const others = lineup.filter((_, i) => i !== handlerIdx);
  const offBall = others.reduce((s, p) => s + p.offBall, 0) / others.length;
  const screen = C.weightedTop(others.map(p => p.screen), C.COMPOSITE.ctxScreen);
  const pass = C.weightedTop(
    others.map(p => p.pass ?? C.ATTR_MIDPOINT), C.COMPOSITE.ctxPass);
  // 引力取「其他四人裡最強的得分威脅」——不平均。
  // 防守要分心去顧的是那一個人，不會因為另外三個是廢咖就不用顧。
  const gravity = Math.max(...others.map(gravityScore));
  // 空間 = 其他四人的**定點投射威脅平均**。跟無球是兩件事：
  // 無球是「他會不會跑」，空間是「不看他行不行」。
  // 引力取 max（防守只需分心顧最強的那一個），空間取平均
  // （每一個不能投的人都送對手一個可以沉退的防守者）。
  const spacing = others.reduce((s, p) => s + shootingThreat(p), 0) / others.length;
  // 隊友裡最會逼防守包夾的那一個。包夾只有一組人手，被他吸走就夾不到你——
  // 「Curry 引力高，吸走 Durant 的包夾」就是這一項。
  const dblPeer = Math.max(...others.map(p => doubleThreat(p)));
  // 創造力取 top-1 主導：球隊只需要一個能自己弄出機會的人，但沒有就是真的沒有。
  const create = C.weightedTop(others.map(p => selfCreation(p)), C.COMPOSITE.ctxCreate);
  return { offBall, screen, pass, gravity, spacing, dblPeer, create };
}

/**
 * 包夾威脅：不夾住他就會得分。
 * 得分能力（低位/禁區為主）與自主製造能力各半——接球才會投的人不會被包夾。
 */
export function doubleThreat(p) {
  const M = C.ATTR_MIDPOINT, w = C.DOUBLE_THREAT_W, c = C.DOUBLE_CREATE_W;
  // 體格項已拿掉（sim 0.1.1，R-089）；寫法同 E-086 ch1，逐位元相同。
  const score = (w.long * p.long + w.mid * p.mid + w.short * p.short) / (w.long + w.mid + w.short);
  const create = c.handle * (p.handle ?? M) + c.drive * p.drive;
  return C.DOUBLE_THREAT_MIX * score + (1 - C.DOUBLE_THREAT_MIX) * create;
}

/**
 * 引力＝這一球防守分掉的注意力。外線拉扯與禁區包夾取大者——
 * 兩個人被困在低位，外線一樣是空的。
 */
export function gravityScore(p) {
  return Math.max(
    C.GRAVITY_W.long * p.long + C.GRAVITY_W.short * p.short,
    doubleThreat(p));
}

/**
 * 這次持球被包夾的機率。
 *
 * 看的是「比隊友強多少」，不是絕對強度——五個人都要顧就誰都夾不了。
 * 再扣掉破包夾能力：持球運出來、切入撞出來、或無球讓自己一開始就不在那個位置。
 */
export function doubleRate(handler, ctx) {
  if (Number.isFinite(ctx.defensiveDoubleRate)) return ctx.defensiveDoubleRate;
  const M = C.ATTR_MIDPOINT;
  const peer = ctx.dblPeer ?? doubleThreat(handler);
  const base = C.DOUBLE_PEER_MIX * peer + (1 - C.DOUBLE_PEER_MIX) * M;
  const rel = doubleThreat(handler) - base;
  const brk = (handler.breakDbl ?? M) - M;
  const r = C.DOUBLE_BASE
    * (1 + Math.tanh(rel / C.DOUBLE_REL_SCALE) * C.DOUBLE_REL_SPAN)
    * (1 - Math.tanh(brk / C.DOUBLE_BREAK_SCALE) * C.DOUBLE_BREAK_SPAN);
  return clamp(r, C.DOUBLE_CLAMP);
}

/**
 * 定點投射威脅：不持球時能不能懲罰放空。
 * 三分為主、中投為輔——中投多半是持球急停，定點價值較低。
 * 這是「放空稅」與「空間」的量尺，跟無球（跑不跑得動）分開。
 */
export function shootingThreat(p) {
  return C.SPACING_W.long * p.long + C.SPACING_W.mid * p.mid;
}

/**
 * 持球能力：誰把球帶起來。
 *
 * 第一手不該由期望得分決定——那會讓終結能力最強的人變成控球後衛
 * （實測 Durant 拿到 38% 球權，真實 USG 27.4%，而且他不是勇士的持球核心）。
 * 帶球過半場、發動進攻靠的是傳球視野、突破威脅與不失誤，不是投得準。
 */
export function handlingScore(p) {
  const w = C.HANDLING_W, M = C.ATTR_MIDPOINT;
  return w.handle * (p.handle ?? M) + w.pass * (p.pass ?? M)
    + w.drive * p.drive + w.tovSkill * (p.tovSkill ?? M);
}

/** 第一手落到誰手上。持球能力的 softmax，加保底與上下限。 */
export function handlingWeights(lineup) {
  const s = lineup.map(handlingScore);
  const mx = Math.max(...s);
  const raw = s.map(x => Math.exp((x - mx) / C.HANDLING_TEMP));
  const t = raw.reduce((a, b) => a + b, 0);
  const uniform = 1 / s.length;
  let w = raw.map(x =>
    (1 - C.HANDLING_FLOOR_MIX) * (x / t) + C.HANDLING_FLOOR_MIX * uniform);
  for (let it = 0; it < 3; it++) {
    w = w.map(x => clamp(x, C.HANDLING_CLAMP));
    const q = w.reduce((a, b) => a + b, 0);
    w = w.map(x => x / q);
  }
  return w;
}

/**
 * 進攻籃板落到誰手上。籃板屬性為主，肉體為輔——跟 teamRebound 同一把尺。
 */
export function reboundWeights(lineup) {
  const s = lineup.map(p =>
    p.rebound + (p.physique - C.ATTR_MIDPOINT) * C.PHYS_REB_WEIGHT);
  const mx = Math.max(...s);
  const raw = s.map(x => Math.exp((x - mx) / C.OREB_PICK_TEMP));
  const t = raw.reduce((a, b) => a + b, 0);
  return raw.map(x => x / t);
}

/**
 * 搶到進攻籃板之後直接放回去的機率。
 *
 * 沒有這一條的話，進攻籃板會回到傳球鏈的起點，等於搶到板的人要重新競爭球權——
 * 但真實的補籃就是搶板的人自己放。這是籃板型球員（Draymond、Tristan Thompson、
 * Hartenstein）出手的主要來源之一，缺了它他們的球權會被系統性低估。
 *
 * 對手護框越強越放不進去，只好把球拉出來重新組織。
 */
export function putbackRate(rebounder, help) {
  const r = C.PUTBACK_BASE
    * (1 + tanhEff(rebounder.physique, C.PUTBACK_SCALE) * C.PUTBACK_PHYS_IMPACT)
    * (1 - tanhEff(help, C.PUTBACK_SCALE) * C.PUTBACK_RIM_IMPACT);
  return clamp(r, C.PUTBACK_CLAMP);
}

/**
 * 自主創造力：能不能自己弄出一次出手機會（給自己或給別人）。
 *
 * 跟 creationScore 是兩件事——creationScore 決定「誰出手」（進 usageFromEv），
 * 這個決定「出手機會是誰生出來的」。所以只看切入與傳球，不看投籃：
 * 定點射手投得再準也創造不出機會。
 */
export function selfCreation(p) {
  return C.CREATE_CTX_W.drive * p.drive
    + C.CREATE_CTX_W.pass * (p.pass ?? C.ATTR_MIDPOINT);
}

/**
 * 協防值：對方協防最好的人（加權平均前二，避免單點決定一切），
 * 再加上肉體的次要加成——大個子群本身就墊高護框。
 */
export function helpDefense(defLineup) {
  return C.weightedTop(
    defLineup.map(p => p.help + (p.physique - C.ATTR_MIDPOINT) * C.PHYS_HELP_BONUS),
    C.COMPOSITE.helpDefense);
}

/** 隊伍平均肉體。持球者的禁區優勢跟這個值比，五小陣容因此被大個子克制。 */
export function teamPhysique(lineup) {
  return lineup.reduce((s, p) => s + p.physique, 0) / lineup.length;
}

// --- 主函式 -------------------------------------------------------------

/**
 * 計算一個進攻機會的事件機率分布。
 * @param handler     持球者（屬性已套用體力 effectiveness）
 * @param ctx         teammateContext 的結果
 * @param defender    對位防守者（盯防用他的 onBall）
 * @param help        helpDefense 的結果（數值）
 * @param defTeamPhys 對方隊伍平均肉體
 */
export function possessionProbabilities(
  handler, ctx, defender, help, offTeamReb, defTeamReb, defTeamPhys = C.ATTR_MIDPOINT,
  opts = {}
) {
  // assist: 傳給他的人的傳球屬性（null = 自己運球創造，沒有接球投加成）
  // forced: 傳不出去或傳球次數用完的強迫出手
  const { assist = null, forced = false, putback = false, contextScale = 1, turnoverScale = 1 } = opts;
  const M = C.ATTR_MIDPOINT;
  // 肉體差：持球者 vs 對方全隊平均。這一項是「五小被大個子克制」的來源。
  const physEdge = tanhEff(M + (handler.physique - defTeamPhys), C.PHYS_SCALE);

  // --- L1: TOV / FOUL / SHOT ---
  let pTov = interpolate(handler.tovSkill ?? M, C.CURVE_TOV);
  pTov *= 1 + tanhEff(defender.onBall, 45) * 0.35;   // 防守壓迫提高失誤
  const consistentTouch = opts.consistentTouch || Number.isFinite(handler.shotProfile?.freeThrowsPerAttempt);
  if (opts.consistentTouch) {
    // Extra handling failures under pressure; good passing/escape skills mitigate it.
    const escape = ((handler.breakDbl ?? M) + (handler.pass ?? M)) / 2;
    pTov *= 1 + doubleRate(handler, ctx) * (1 - tanhEff(escape, 40));
  }
  pTov = clamp(pTov * turnoverScale * (consistentTouch ? C.HANDLER_TOV_SCALE : 1) + (opts.turnoverFloor ?? 0), C.CLAMP.tov);

  let pFoul = C.BASE_FOUL_RATE
    * (1 + tanhEff(handler.drive, C.FOUL_DRIVE_SCALE) * C.FOUL_MAX_IMPACT);
  const ftaRatio = handler.shotProfile?.freeThrowsPerAttempt;
  if (Number.isFinite(ftaRatio) && ftaRatio >= 0) {
    // Two-FT event approximation; preserves the independent FT accuracy curve.
    const touchTov = pTov;
    pFoul = (1-touchTov)*ftaRatio/(C.FT_ATTEMPTS+ftaRatio);
  }
  pFoul = clamp(pFoul, C.CLAMP.foul);

  const pShot = Math.max(0, 1 - pTov - pFoul);

  // --- 有效防守：傳球與空間都作用在這裡 ---
  //
  // 接球投的優勢不是憑空的命中率加成，而是「對位者被球的移動調動開了」。
  // 走這條路的好處是它同時打開命中率與可及性——好傳球讓你投得準，
  // 也讓你投得到（denyLong / denyShort 一起變小）。
  // 以聯盟接球投率為中心零和：自主出手 -r 份、接球投 +(1-r) 份，平均為零。
  const r = C.LEAGUE_ASSISTED_RATE;
  // 誰把防守調動開，傳球者與接球者**任一個做到就夠**，所以取 max 不是相加：
  // 球送得準（傳球高）或人自己跑開了（無球高），對位者都一樣來不及回位。
  // 兩個都低才是真的沒有——這就是「至少要有一個高」。
  const relief = Math.max(
    tanhEff(assist ?? M, C.ASSIST_DROP_SCALE),
    tanhEff(handler.offBall, C.ASSIST_DROP_SCALE));
  const defDrop = assist === null
    ? -r
    : (1 - r) * (1 + relief * C.ASSIST_DROP_SPAN);
  // 放空稅：隊友沒有投射威脅 -> 他的防守者直接沉進禁區 -> 對手協防有效值上升。
  // 中心點是 ATTR_MIDPOINT，所以 PR50 全隊時為零。
  // 用「定點投射威脅」而不是無球屬性——無球是跑動，投射威脅才是不能被放空的理由。
  // 一開始寫成 ctx.offBall 是雙重計算：引力那條線已經在懲罰「隊上沒有得分威脅」了。
  const spacingTax = clamp((M - (ctx.spacing ?? M)) * C.SPACING_HELP_W,
    [-C.SPACING_HELP_CAP, C.SPACING_HELP_CAP]);
  // 包夾：多一個人來夾就是協防加倍。以聯盟平均包夾率為中心零和。
  const dbl = doubleRate(handler, ctx) - C.LEAGUE_DOUBLE_RATE;
  const onBallEff = defender.onBall - defDrop * C.ASSIST_DEF_DROP;
  const helpEff = help - defDrop * C.ASSIST_DEF_DROP_HELP + spacingTax
    + dbl * C.DOUBLE_HELP;

  // --- L3 先算：命中 ---
  // 出手選擇要看期望值，所以命中率必須先算出來。
  // pm 已是「被他防守時對手命中率的絕對增減量」，直接相加，不轉 tanh 乘數。
  const pmLong = interpolate(onBallEff, C.CURVE_DEF_3PT);
  const pmShort = interpolate(helpEff, C.CURVE_DEF_RIM);
  const pmMid = (pmLong * 0.5 + pmShort * 0.5) * C.DEF_MID_SCALE;

  // 自主出手的品質取決於**持球投**，不是切入或傳球。
  //
  // 這是 Curry 與 Klay 的分界：兩人的三分/中投數字幾乎相同，但一個拉起來就投、
  // 一個要人餵。用 selfCreation（切入+傳球）代打的話 Curry 會被判成弱自主出手者
  // ——他的切入 58 是 FTA 率逆推的，而他本來就不切入——
  // 結果球權全流向 Durant（實測 40.1%，真實 USG 27.4%）。
  const assistBoost = assist === null
    ? 1 + tanhEff(handler.handle ?? M, C.HANDLE_SCALE) * C.HANDLE_IMPACT
    : 1;
  const f = C.LEAGUE_FORCED_RATE;
  const forcedPenalty = forced
    ? 1 - C.FORCED_MAKE_PENALTY * (1 - f)
    : 1 + C.FORCED_MAKE_PENALTY * f;

  const passBoost = (1 + tanhEff(ctx.pass, C.PASS_SCALE) * C.PASS_MAX_IMPACT)
    * assistBoost * forcedPenalty;
  const gravBoost = 1 + tanhEff(ctx.gravity ?? M, C.GRAVITY_SCALE) * C.GRAVITY_MAX_IMPACT;

  // 創造依賴：自己弄不出機會的人，出手品質綁在隊友的創造力上。
  // 依賴度 1 = 純吃餅（全靠餵），0 = 自主創造者（不需要人餵）。
  const dependence = clamp(
    C.CREATE_DEP_BASE + (M - selfCreation(handler)) / C.CREATE_DEP_SCALE, [0, 1]);
  const createBoost = 1
    + tanhEff(ctx.create ?? M, C.CREATE_SCALE) * C.CREATE_MAX_IMPACT * dependence;

  // 情境加成用**絕對增減量**，不是乘數。
  //
  // 乘法會疊在本來就高的底上被放大：近射 87 與 99 的曲線只差 .041，
  // 但乘完同一組加成後差 .147——Durant 被推到 .878（夾值上限），
  // 於是球權全流向他（實測 40%，真實 USG 27.4%）。
  // 隊友幫你創造出來的空檔，價值不該跟你本來多會投成正比；
  // 防守端的 PLUSMINUS 本來就是這樣加的，這裡只是把兩邊對齊。
  const ctxLong = (1 + tanhEff(ctx.spacing ?? M, C.OFFBALL_SCALE) * C.OFFBALL_MAX_IMPACT)
    * passBoost * gravBoost * createBoost - 1;
  let makeLong = interpolate(handler.long, C.CURVE_3PT)
    + contextScale * ctxLong * C.LEAGUE_TARGETS.longPct
    + pmLong;
  makeLong = clamp(makeLong, C.CLAMP.makeLong);

  // 中距離幾乎是純技術：沒有隊友情境加成，肉體也幫不上忙。
  let makeMid = interpolate(handler.mid, C.CURVE_MID) + pmMid;
  makeMid = clamp(makeMid, C.CLAMP.makeMid);

  const ctxShort = (1 + tanhEff(ctx.screen, C.SCREEN_SCALE) * C.SCREEN_MAX_IMPACT)
    * (1 + tanhEff(ctx.offBall, C.OFFBALL_CUT_SCALE) * C.OFFBALL_CUT_IMPACT)
    * (1 + physEdge * C.PHYS_MAX_IMPACT)
    * passBoost * gravBoost * createBoost - 1;
  // 出手來源修正（v55 修正 B）：預設 0，只有掛了 shotOriginMeasurement 的球員才有作用。
  // 模擬裡「自主出手」就是「出手前沒傳球」(assist === null)，而 centeredMake 把命中率水準
  // 釘在實測總和上，於是吃餅長人會拿被餵進去的禁區命中率去打自己創造的球。見 source_shot_origin.js。
  let makeShort = interpolate(handler.short, C.CURVE_SHORT)
    + contextScale * ctxShort * C.LEAGUE_TARGETS.shortPct
    + pmShort
    + shotOriginAdjustment(handler, assist, putback);
  makeShort = clamp(makeShort, C.CLAMP.makeShort);

  // --- L2: 出手區域 ---
  // 兩個乘數：這球值不值得（ΔEV）× 拿不拿得到（可及性）。
  // 防守否決是中投存在的理由：盯防斷三分、協防斷禁區，兩條都被斷就只剩中距離。
  const denyLong = (onBallEff - M) * C.DENY_LONG;
  const denyShort = (helpEff - M) * C.DENY_SHORT;

  // 缺創造者是一種「自我否決」：跟 denyLong / denyShort 同構，只是來源在自己這邊。
  // 兩條路都拿不到 -> 一樣只剩中距離。
  const denySelf = (M - (ctx.create ?? M)) * dependence;

  // 自己的無球給自己開三分接球機會；隊友的空間給整隊開。兩件事都算進來。
  const aLong = ((ctx.spacing ?? M) - M) * C.Z_OFFBALL_W
    + (handler.offBall - M) * C.Z_OFFBALL_SELF_W * (assist === null ? 0 : 1)
    - denyLong
    - denySelf * C.Z_CREATE_LONG_W
    - C.FORCED_DENY_LONG * (forced ? 1 - f : -f);
  const aMid = (handler.drive - M) * C.Z_DRIVE_MID_W;
  const aShort = (ctx.screen - M) * C.Z_SCREEN_W
    + (ctx.offBall - M) * C.Z_OFFBALL_RIM_W
    + (ctx.pass - M) * C.Z_PASS_RIM_W
    + (handler.drive - M) * C.Z_DRIVE_RIM_W
    + physEdge * C.PHYS_SHOT_PULL
    - denyShort
    - denySelf * C.Z_CREATE_RIM_W
    - C.FORCED_DENY_RIM * (forced ? 1 - f : -f);

  const threeRate = handler.shotProfile?.threeRate;
  const hasStyle = Number.isFinite(threeRate) && threeRate >= 0 && threeRate <= 1;
  const twoPrior = C.HALFCOURT_ZONE_SHARE.mid + C.HALFCOURT_ZONE_SHARE.short;
  const prior = hasStyle ? { long: threeRate,
    mid: (1-threeRate)*C.HALFCOURT_ZONE_SHARE.mid/twoPrior,
    short: (1-threeRate)*C.HALFCOURT_ZONE_SHARE.short/twoPrior } : C.HALFCOURT_ZONE_SHARE;
  const wLong = prior.long
    * Math.exp((3 * makeLong - C.EV_REF.long) / C.EV_TEMP + aLong / C.ZONE_TEMP);
  const wMid = prior.mid
    * Math.exp((2 * makeMid - C.EV_REF.mid) / C.EV_TEMP + aMid / C.ZONE_TEMP);
  const wShort = prior.short
    * Math.exp((2 * makeShort - C.EV_REF.short) / C.EV_TEMP + aShort / C.ZONE_TEMP);
  let zLong, zMid, zShort;
  if (putback) {
    // 補籃永遠在籃下。搶到板的人不會把球拉出來投三分——那就不叫補籃了。
    zLong = 0; zMid = 0; zShort = 1;
  } else {
    const wSum = wLong + wMid + wShort;
    // 夾完再「除以總和」會把值又推出範圍——因為上下限彼此不相容
    // （三分上限 .58 + 中投下限 .02 + 近射下限 .30 = .90 ≠ 1），
    // 極端輸入下實測三分佔比 .644 > 上限 .58。
    // 正確作法是投影到有上下限的單體：差額只分給還有餘裕的區。
    const lo = hasStyle ? [0,0,0] : [C.CLAMP.zoneLong[0], C.CLAMP.zoneMid[0], C.CLAMP.zoneShort[0]];
    const hi = hasStyle ? [1,1,1] : [C.CLAMP.zoneLong[1], C.CLAMP.zoneMid[1], C.CLAMP.zoneShort[1]];
    let z = [wLong / wSum, wMid / wSum, wShort / wSum];
    for (let it = 0; it < 8; it++) {
      z = z.map((x, i) => clamp(x, [lo[i], hi[i]]));
      const d = 1 - (z[0] + z[1] + z[2]);
      if (Math.abs(d) < 1e-12) break;
      const room = z.map((x, i) => d > 0 ? hi[i] - x : x - lo[i]);
      const tot = room.reduce((a, b) => a + b, 0);
      if (tot <= 1e-12) break;
      z = z.map((x, i) => x + d * room[i] / tot);
    }
    [zLong, zMid, zShort] = z;
  }

  // --- L4: 進攻籃板 ---
  const bias4 = Math.log(C.LEAGUE_OREB_RATE / (1 - C.LEAGUE_OREB_RATE));
  const pOreb = clamp(
    logistic((offTeamReb - defTeamReb) / C.OREB_TEMP + bias4), C.CLAMP.oreb);

  // --- 攤平成事件分布 ---
  const raw = {
    TOV: pTov,
    FOUL: pFoul,
    FG3M: pShot * zLong * makeLong,
    FG3X: pShot * zLong * (1 - makeLong),
    MIDM: pShot * zMid * makeMid,
    MIDX: pShot * zMid * (1 - makeMid),
    RIMM: pShot * zShort * makeShort,
    RIMX: pShot * zShort * (1 - makeShort),
  };

  let total = 0;
  for (const k in raw) { raw[k] = Math.max(0, raw[k]); total += raw[k]; }
  if (total === 0) {
    return { TOV: 1, FOUL: 0, FG3M: 0, FG3X: 0, MIDM: 0, MIDX: 0, RIMM: 0, RIMX: 0, pOreb, ftPct: C.FT_PCT, ev: 0 };
  }
  const norm = {};
  for (const k in raw) norm[k] = raw[k] / total;
  norm.pOreb = pOreb;
  // 期望得分：「夠不夠好，要不要出手」就是比這個值。
  norm.ftPct = clamp(interpolate(handler.ft ?? C.ATTR_MIDPOINT, C.CURVE_FT), [0.30, 0.98]);
  norm.ev = norm.FG3M * 3 + norm.MIDM * 2 + norm.RIMM * 2
    + norm.FOUL * C.FT_ATTEMPTS * norm.ftPct;
  // 引擎要分開判定「出手」與「傳球」，所以把內部量攤出來。
  // pTov 是這一次觸球的持球失誤率（縮放過——一個 possession 現在有多次觸球）。
  norm.pTovTouch = consistentTouch ? pTov : clamp(pTov * C.HANDLER_TOV_SCALE, C.CLAMP.tov);
  norm.zone = { long: zLong, mid: zMid, short: zShort };
  norm.make = { long: makeLong, mid: makeMid, short: makeShort };
  norm.pFoul = pFoul;
  return norm;
}

// --- 傳球鏈 -------------------------------------------------------------

/**
 * 傳得出去嗎。傳球者視野 + 隊友跑位/掩護 − 對位壓迫。
 * 傳不出去就只能自己出手——「壞持球員一旦拿到球只能勉強出手」就是這一條。
 */
export function passOpenRate(handler, ctx, defender) {
  const M = C.ATTR_MIDPOINT, w = C.PASS_OPEN_W;
  const s = w.pass * ((handler.pass ?? M) - M)
    + w.offBall * (ctx.offBall - M)
    + w.screen * (ctx.screen - M)
    + w.onBall * (defender.onBall - M);
  // 被包夾就傳不出去——「控球普通的終結者被夾會難以傳球」就是這一條。
  const dbl = doubleRate(handler, ctx) - C.LEAGUE_DOUBLE_RATE;
  return clamp((C.PASS_OPEN_BASE + Math.tanh(s / C.PASS_OPEN_SCALE) * 0.30)
    * (1 - dbl * C.DOUBLE_PASS_PENALTY), C.PASS_OPEN_CLAMP);
}

/** 這一次傳球被抄的機率。失誤傾向與傳球視野對上對位者的盯防。 */
export function interceptRate(handler, defender, ctx = {}) {
  const M = C.ATTR_MIDPOINT;
  const skill = 0.6 * (handler.tovSkill ?? M) + 0.4 * (handler.pass ?? M);
  const dbl = doubleRate(handler, ctx) - C.LEAGUE_DOUBLE_RATE;
  const r = C.INTERCEPT_BASE
    * (1 - tanhEff(skill, C.INTERCEPT_SCALE) * C.INTERCEPT_MAX_IMPACT)
    * (1 + tanhEff(defender.onBall, C.INTERCEPT_SCALE) * C.INTERCEPT_MAX_IMPACT)
    * (1 + dbl * (C.DOUBLE_TOV_MULT - 1));
  return clamp(r, C.INTERCEPT_CLAMP);
}

/**
 * 誰接到球。跑位拉開空檔的人先拿到，再看接到之後的出手品質。
 * evs 已經是「接球投」版本（含 assist 加成）。
 */
export function receiverWeights(evs, lineup, handlerIdx, rollAccess = 0) {
  const M = C.ATTR_MIDPOINT;
  // 防守注意力：得分威脅越高的人越難餵到球。威脅用跟引力同一把尺。
  const threat = lineup.map(gravityScore);
  const avgThreat = threat.reduce((a, b) => a + b, 0) / threat.length;
  // 創造力項沿用 usageFromEv 的同一把尺——那個式子對真實 USG% 有 r = 0.729，
  // 是唯一驗證過的球權訊號，不能因為換了傳球鏈就丟掉。
  const s = evs.map((e, i) => i === handlerIdx ? -Infinity
    : e + C.USAGE_CREATE_W * (creationScore(lineup[i]) - M) / 100
      // A screen-and-roll is a second route to a reception. Only add the
      // screen advantage NOT already represented by off-ball movement.
      + rollAccess * Math.max(0,lineup[i].screen-lineup[i].offBall)/100
        * clamp((lineup[i].physique-55)/30,[0,1])
      + C.RECEIVER_OFFBALL_W * (lineup[i].offBall - M)
      - C.RECEIVER_ATTENTION_W * (threat[i] - avgThreat) / 10);
  const mx = Math.max(...s);
  const raw = s.map(x => x === -Infinity ? 0 : Math.exp((x - mx) / C.RECEIVER_TEMP));
  const tot = raw.reduce((a, b) => a + b, 0);
  const n = s.length - 1, uniform = 1 / n;
  let w = raw.map((x, i) => i === handlerIdx ? 0
    : (1 - C.RECEIVER_FLOOR_MIX) * (x / tot) + C.RECEIVER_FLOOR_MIX * uniform);
  for (let it = 0; it < 3; it++) {
    w = w.map((x, i) => i === handlerIdx ? 0 : clamp(x, C.RECEIVER_CLAMP));
    const t = w.reduce((a, b) => a + b, 0);
    w = w.map(x => x / t);
  }
  return w;
}

/** 夠不夠好就出手。門檻隨剩餘傳球次數遞減——越接近沒得傳越願意將就。 */
export function shootRate(ev, passesLeft) {
  const used = C.MAX_PASSES - passesLeft;
  const thr = C.SHOT_THRESHOLD - used * C.SHOT_THRESHOLD_STEP;
  return logistic((ev - thr) / C.SHOT_TEMP);
}

// --- 出手品質搜尋 -------------------------------------------------------

/**
 * 算出五個人各自持球的機率分布與期望得分。
 * 一次算五個，選中的那個直接沿用——不會重算。
 */
export function evaluateLineup(lineup, ctxs, defLineup, help, oReb, dReb, dPhys, handlers) {
  return handlers.map((h, i) =>
    possessionProbabilities(h, ctxs[i], defLineup[i], help, oReb, dReb, dPhys));
}

/**
 * 依期望得分 softmax 決定誰出手。
 *
 * 純 argmax 會讓最強的人吃掉全部球權；純 usage 權重又跟出手品質脫鉤。
 * softmax 溫度就是球隊的「球商」：低溫 = 球會流動到最好的位置，
 * 高溫 = 誰拿到球誰投。FLOOR_MIX 保底，讓 usage 落在 NBA 真實範圍
 * （頭號球星 28-35%、第五人 10-14%）。
 */
export function usageFromEv(evs, creations) {
  const scores = evs.map((e, i) =>
    e + C.USAGE_CREATE_W * ((creations[i] - C.ATTR_MIDPOINT) / 100));
  const mx = Math.max(...scores);
  const raw = scores.map(s => Math.exp((s - mx) / C.USAGE_TEMP));
  const tot = raw.reduce((s, x) => s + x, 0);
  const uniform = 1 / scores.length;
  let w = raw.map(x => (1 - C.USAGE_FLOOR_MIX) * (x / tot) + C.USAGE_FLOOR_MIX * uniform);
  // 夾在 NBA 真實範圍後重新正規化（迭代兩次即收斂）
  for (let it = 0; it < 3; it++) {
    w = w.map(x => clamp(x, C.USAGE_CLAMP));
    const s = w.reduce((a, b) => a + b, 0);
    w = w.map(x => x / s);
  }
  return w;
}

/**
 * 創造力：能不能自己製造出手。
 *
 * 偏重跳投（三分與中投），因為那是「自己拔起來就投」的能力；近射權重低——
 * 中鋒的近射 98 多半是接球放進去，那是別人創造的。切入補一點自主進攻。
 * 用「三項最高值」會把吃餅中鋒誤判成創造者。
 */
export function creationScore(p) {
  const w = C.CREATE_W;
  return w.long * p.long + w.mid * p.mid + w.short * p.short
    + w.drive * p.drive + w.pass * (p.pass ?? C.ATTR_MIDPOINT)
    - C.CREATE_OFFBALL_PENALTY * (p.offBall - C.ATTR_MIDPOINT);
}
