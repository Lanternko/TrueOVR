// source_shot_origin.js — v55 修正 B：禁區出手來源（被餵 / 自主）命中率修正。**預設不作用。**
//
// 為什麼要這一項：
//   NBA play-by-play 量到的事實（四季穩定，見 reports/ovr-v55-finisher-fix-2025-26/）是
//   禁區「被餵」與「自主」的命中率差約 +0.19，而三分只有 +0.04、中距離 ≈ 0。
//   模擬裡「自主出手」的定義恰好是「出手前沒有傳球」（src/timed_game.js 的 assist === null），
//   而 centeredMake（reports/player-impact-v14/model.mjs）把命中率水準釘在實測總和上。
//   兩者相乘的後果：吃餅長人在模擬裡拿「被餵進去的命中率」去打「自己創造的球」。
//
// 修法：在 makeShort 上加一個加法項
//   adj = gap * ( [被餵] - fedShare ) + center
//   在球員自己的實測來源組合下期望值為 0（center = 0 時），所以不改變個人命中率水準；
//   只有當模擬給他的餵球占比低於現實時才整體轉負。center 是單一個聯盟水準常數，
//   用來抵銷「模擬普遍餵得比現實少」造成的全聯盟水準漂移。
//
// 預設關閉的機制：只有掛了 shotOriginMeasurement 的球員才有作用，而只有 v55 的 input 會掛。
// 經驗貝氏：球員間 d_i 的觀測離散幾乎全是抽樣雜訊（2025-26 τ² = 0.00144 vs 平均抽樣變異
// 0.01114），所以 gap 會被收到聯盟值附近——真正的判別變數是 fedShare。

export const RIM_ZONE = 'short';
export const DEFAULT_PSEUDO_ATTEMPTS = 25;   // fedShare 收縮的偽出手數（預先登錄值）
export const MIN_ATTEMPTS_FOR_TAU2 = 40;     // 估 tau^2 時的最小出手數（預先登錄值）

/** 把 shot-origin.json 的若干季禁區計數併起來，算出聯盟值與 tau^2。 */
export function shotOriginTables(origin, seasons, opts = {}) {
  const pseudoAttempts = opts.pseudoAttempts ?? DEFAULT_PSEUDO_ATTEMPTS;
  const minAttempts = opts.minAttempts ?? MIN_ATTEMPTS_FOR_TAU2;
  if (!origin?.seasons || !Array.isArray(seasons) || !seasons.length) throw Error('Need shot-origin seasons');
  const agg = new Map();
  let LfedA = 0, LfedM = 0, LselfA = 0, LselfM = 0, LputA = 0;
  for (const season of seasons) {
    const S = origin.seasons[season];
    if (!S?.players) throw Error('Missing shot-origin season ' + season);
    for (const [pid, zones] of Object.entries(S.players)) {
      const r = zones[RIM_ZONE];
      if (!r) continue;
      const a = agg.get(+pid) ?? { fedA: 0, fedM: 0, selfA: 0, selfM: 0, putA: 0 };
      a.fedA += r.fedA; a.fedM += r.fedM; a.selfA += r.selfA; a.selfM += r.selfM; a.putA += r.putA ?? 0;
      agg.set(+pid, a);
      LfedA += r.fedA; LfedM += r.fedM; LselfA += r.selfA; LselfM += r.selfM; LputA += r.putA ?? 0;
    }
  }
  if (!LfedA || !LselfA) throw Error('Empty shot-origin pool');
  const pf = LfedM / LfedA, ps = LselfM / LselfA;
  const sBar = LfedA / (LfedA + LselfA);
  // 抽樣變異用聯盟命中率算（球員自己的率在小樣本下不穩）。
  const samplingVar = a => pf * (1 - pf) / a.fedA + ps * (1 - ps) / a.selfA;
  const eligible = [...agg.values()].filter(a => a.fedA + a.selfA >= minAttempts && a.fedA > 0 && a.selfA > 0);
  if (eligible.length < 2) throw Error('Not enough players to estimate tau^2');
  const wA = eligible.reduce((s, a) => s + a.fedA + a.selfA, 0);
  const gapOf = a => a.fedM / a.fedA - a.selfM / a.selfA;
  // 先驗平均 = 球員層 d_i 的 attempt-weighted 平均（tau^2 就是繞著它估的）。
  const dBar = eligible.reduce((s, a) => s + gapOf(a) * (a.fedA + a.selfA), 0) / wA;
  const varObserved = eligible.reduce((s, a) => s + (gapOf(a) - dBar) ** 2, 0) / (eligible.length - 1);
  const meanSamplingVar = eligible.reduce((s, a) => s + samplingVar(a), 0) / eligible.length;
  const tau2 = Math.max(varObserved - meanSamplingVar, 1e-6);
  const players = new Map();
  for (const [pid, a] of agg) {
    const A = a.fedA + a.selfA;
    const fedShare = (a.fedA + pseudoAttempts * sBar) / (A + pseudoAttempts);
    let gap = dBar, reliability = 0;
    if (a.fedA > 0 && a.selfA > 0) {
      const v = samplingVar(a);
      reliability = tau2 / (tau2 + v);
      gap = dBar + reliability * (gapOf(a) - dBar);
    }
    players.set(pid, { fedShare, gap, reliability, rimAttempts: A, fedA: a.fedA, selfA: a.selfA, putA: a.putA,
      rawGap: a.fedA > 0 && a.selfA > 0 ? gapOf(a) : null });
  }
  return { seasons: [...seasons], pseudoAttempts, minAttempts,
    league: { fedA: LfedA, fedM: LfedM, selfA: LselfA, selfM: LselfM, putA: LputA, fedPct: pf, selfPct: ps,
      leagueGap: pf - ps, fedShare: sBar },
    eb: { players: eligible.length, dBar, varObserved, meanSamplingVar, tau2 }, players };
}

/**
 * 把禁區出手來源量測掛到球員上。只有掛上的球員才會被 shotOriginAdjustment 影響。
 * center 是單一個聯盟水準常數（見檔頭），由校正跑決定後凍結。
 */
export function attachShotOrigin(players, tables, opts = {}) {
  const center = opts.center ?? 0;
  if (!Number.isFinite(center)) throw Error('Invalid shot-origin center');
  const fallback = { fedShare: tables.league.fedShare, gap: tables.eb.dBar, reliability: 0, rimAttempts: 0 };
  let tagged = 0, fell = 0;
  for (const p of players) {
    const t = tables.players.get(p.playerId) ?? (fell++, fallback);
    if (!Number.isFinite(t.fedShare) || t.fedShare < 0 || t.fedShare > 1 || !Number.isFinite(t.gap)) throw Error('Invalid shot-origin measurement');
    p.shotOriginMeasurement = { fedShare: t.fedShare, gap: t.gap, center, reliability: t.reliability,
      rimAttempts: t.rimAttempts, seasons: tables.seasons,
      source: 'Observed NBA play-by-play rim fed/self attempt partition (descriptor x subType class propensity, putbacks excluded); EB-shrunk gap, league-centered. Zero expectation at the player own measured source mix.' };
    tagged++;
  }
  return { tagged, fallbacks: fell, center };
}

/** 加在 makeShort 上的修正量。沒有量測、或是補籃，就回 0（預設路徑）。 */
export function shotOriginAdjustment(handler, assist, putback = false) {
  const m = handler?.shotOriginMeasurement;
  if (!m || putback) return 0;
  return m.gap * ((assist === null ? 0 : 1) - m.fedShare) + m.center;
}
