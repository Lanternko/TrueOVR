// simulation_engine.js — possession loop + Monte Carlo

import { makeRng, pickWeighted } from './rng.js';
import { simulateTimedGame } from './timed_game.js';
import * as M from './probability_model.js';
import * as C from './constants.js';
import { opportunityReboundWeights, blockProfile, offensiveReboundProbability, DEFAULT_OREB_SHARE } from './rebound_block_model.js';

/**
 * 隊伍籃板加權值：五人籃板的加權平均，偏重最高者。
 * 肉體佔 30% —— 卡位吃身材，這是肉體的次要作用之一。
 */
export function teamRebound(lineup) {
  return C.weightedTop(
    lineup.map(p => p.rebound * (1 - C.PHYS_REB_WEIGHT) + p.physique * C.PHYS_REB_WEIGHT),
    C.COMPOSITE.teamRebound);
}

// 記帳新增的籃板歸屬使用獨立亂數，不改變原有比賽結果。
const COUNT_KEYS = ['poss', 'fga', 'fg3a', 'fg3m', 'mida', 'midm', 'rima', 'rimm',
  'tov', 'oreb', 'dreb', 'fta', 'ftm', 'pts', 'stl', 'blk', 'blka', 'pf', 'usageEvents', 'truncations',
  'passes', 'touches', 'assisted', 'forced', 'putbacks',
  'firstTouches', 'receptions', 'passAttempts', 'interceptedPasses',
  'shotOpportunities', 'evSum', 'doubleRateSum'];

function record(side, index, key, value = 1) {
  side.stat[key] += value;
  side.players[index][key] += value;
}

/**
 * 決定出手結果。持球失誤已經在外面判掉了，這裡只分犯規與三個區域。
 * 用攤出來的 zone/make 而不是正規化後的事件分布——因為 TOV 被抽掉了，
 * 直接用舊的 norm 會把犯規與出手的比例算錯。
 */
function sampleShot(p, rng) {
  if (rng() < p.pFoul / (1 - p.pTovTouch)) return 'FOUL';
  let x = rng() * (p.zone.long + p.zone.mid + p.zone.short);
  if ((x -= p.zone.long) <= 0) return rng() < p.make.long ? 'FG3M' : 'FG3X';
  if ((x -= p.zone.mid) <= 0) return rng() < p.make.mid ? 'MIDM' : 'MIDX';
  return rng() < p.make.short ? 'RIMM' : 'RIMX';
}

/**
 * 跑一場比賽。
 * mode: 'fixed' = 每方固定 possessions 個回合
 *       'race'  = 先到 targetScore 分（需贏 winBy 分）
 */
export function simulateGame(teamA, teamB, opts = {}) {
  if (opts.mode === 'timed') {
    if ((opts.possessionModel && opts.possessionModel!=='legacy') || opts.rollAccess || opts.turnoverFloor) {
      throw new RangeError('Stable possession calibration is only validated for fixed-lineup games');
    }
    return simulateTimedGame(teamA, teamB, opts);
  }
  const {
    mode = 'fixed', possessions = 20, targetScore = 21, winBy = 1,
    maxPossessions = 200, seed = 1,
    reboundModel = 'opportunity', blocks = true, replay = false,
    leagueReboundShare = DEFAULT_OREB_SHARE, contextScale = 1, turnoverScale = 1, turnoverFloor = 0,
    possessionModel = 'legacy', rollAccess = 0,
  } = opts;
  if (![contextScale, turnoverScale].every(x => Number.isFinite(x) && x >= 0)) throw new RangeError('Invalid calibration scale');
  if (!Number.isFinite(turnoverFloor)||turnoverFloor<0||turnoverFloor>.1) throw new RangeError('Invalid turnover floor');
  if (!['legacy','stable'].includes(possessionModel)) throw new RangeError('Invalid possession calibration');
  if (!Number.isFinite(rollAccess)||rollAccess<0) throw new RangeError('Invalid interior access');
  if (!Number.isFinite(leagueReboundShare) || leagueReboundShare <= 0 || leagueReboundShare >= 1) throw new RangeError('Invalid leagueReboundShare');
  if (!['fixed', 'race'].includes(mode)) throw new RangeError('Unknown game mode');
  if (opts.fatigue !== undefined) { if (typeof opts.fatigue !== 'boolean') throw new TypeError('fatigue must be boolean'); if (opts.fatigue) throw new Error('fatigue removed in sim 0.1.1'); }
  if (typeof blocks !== 'boolean') throw new TypeError('blocks must be boolean');
  if (!['legacy','opportunity'].includes(reboundModel)) throw new RangeError('Unknown rebound model');
  if (mode === 'fixed' && (!Number.isSafeInteger(possessions) || possessions < 1)) {
    throw new RangeError('possessions must be a positive integer per side');
  }
  const rng = makeRng(seed);
  const attributionRng = makeRng(seed ^ 0x51ED270B);
  const blockRng = makeRng(seed ^ 0x713B12A9);

  const sides = [teamA, teamB].map(t => ({
    lineup: t.roster,
    ctxs: t.roster.map((_, i) => M.teammateContext(t.roster, i)),
    score: 0, stat: newStat(),
    players: t.roster.map(() => newStat()),
    reb: teamRebound(t.roster),
    phys: M.teamPhysique(t.roster),
  }));
  const help = sides.map(s => M.helpDefense(s.lineup));
  const distributions = [new Map(), new Map()];
  const initialWeights = sides.map(s => M.handlingWeights(s.lineup));
  if (possessionModel === 'stable') {
    sides.forEach((s, side) => {
      const d = sides[1-side];
      // Defense commits using untrapped threat. Never switch off because its own
      // double has lowered the subsequent EV (the old circular decision hazard).
      const evs = s.lineup.map((p,i)=>M.possessionProbabilities(p,
        {...s.ctxs[i],defensiveDoubleRate:0},d.lineup[i],help[1-side],s.reb,d.reb,d.phys,
        {contextScale,turnoverScale,turnoverFloor,consistentTouch:true}).ev);
      s.ctxs = s.ctxs.map((ctx,i)=>{
        const alternatives = evs.filter((_,j)=>j!==i);
        const advantage = evs[i] - alternatives.reduce((a,b)=>a+b,0)/4;
        const spacingCost = (ctx.spacing-70)/100;
        const target = M.doubleRate(s.lineup[i],ctx) * (1 + .3*Math.tanh((advantage-spacingCost)/.25));
        return {...ctx,defensiveDoubleRate:M.clamp(target,C.DOUBLE_CLAMP)};
      });
    });
  }

  let poss = 0, off = 0;
  const log = [];
  const events = [];
  const emit = (type, side, player, detail = {}) => {
    if (!replay) return;
    events.push({ type, poss, off: side, player, ...detail,
      score: sides.map(s => s.score),
      players: sides.map(s => s.players.map(p => finalize({ ...p }))) });
  };

  // 一個 possession 在「投進 / 失誤 / 被防守籃板」時結束。
  // 進攻籃板延續同一個 possession，不是新的一次——這是 NBA 的定義，
  // 也讓每回合得分可以直接跟真實的 1.15 比較。
  //
  // 結束條件只在 off === 0 時檢查，確保兩隊回合數永遠相等。
  for (;;) {
    if (off === 0) {
      if (mode === 'fixed' && poss >= possessions * 2) break;
      if (mode === 'race') {
        const a = sides[0].score, b = sides[1].score;
        const done = (a >= targetScore || b >= targetScore) && Math.abs(a - b) >= winBy;
        if (done || poss >= maxPossessions) break;
      }
    }

    const O = sides[off], D = sides[1 - off];
    O.stat.poss++;
    let alive = true, chances = 0;
    // >= 0 表示上一球被自己搶下進攻籃板，而且搶板的人決定直接補籃。
    let putbackBy = -1;

    while (alive && chances < 6) {
      chances++;

      const handlers = O.lineup;
      const dist = (i, options) => {
        const key = `${i}/${options.assist}/${!!options.forced}/${!!options.putback}`;
        if (distributions[off].has(key)) return distributions[off].get(key);
        const value = M.possessionProbabilities(handlers[i], O.ctxs[i], D.lineup[i], help[1-off], O.reb, D.reb, D.phys,
          {...options,contextScale,turnoverScale,turnoverFloor,consistentTouch:possessionModel==='stable'});
        distributions[off].set(key,value);
        return value;
      };

      let assist = null, passesLeft = C.MAX_PASSES, forced = false;
      // 接到球的人有兩個選項：接球就投，或自己再創造一次。取較好的那個。
      // 定點射手選前者，創造者選後者——這是球權會流向創造者的原因。
      const best = (i, a) => {
        if (a === null) return dist(i, { assist: null, forced: false });
        const c = dist(i, { assist: a, forced: false });
        const o = dist(i, { assist: null, forced: false });
        return o.ev > c.ev ? o : c;
      };

      let hi, p;
      if (putbackBy >= 0) {
        // 補籃：搶到板的人直接放，不重走傳球鏈。沒有傳球，也沒有選擇餘地。
        hi = putbackBy;
        putbackBy = -1;
        passesLeft = 0;
        p = dist(hi, { assist: null, forced: false, putback: true });
      } else {
        // 第一手：誰把球帶起來。由**持球能力**決定，不是由期望得分決定——
        // 出手多跟持球多是兩件事（Durant 出手多，但持球核心是 Curry 與 Draymond）。
        const weights = initialWeights[off];
        hi = pickWeighted(weights, rng());
        record(O, hi, 'firstTouches');
        p = best(hi, assist);
        emit('POSSESSION', off, hi);

        // 傳球鏈：夠好就投，不夠好就找人傳，傳不出去或次數用完就勉強出手。
        for (;;) {
          if (rng() < M.shootRate(p.ev, passesLeft)) break;
          if (passesLeft <= 0) { forced = true; break; }             // 沒得傳 -> 勉強出手
          if (rng() >= M.passOpenRate(handlers[hi], O.ctxs[hi], D.lineup[hi])) {
            forced = true; break;                                     // 傳不出去 -> 勉強出手
          }
          record(O, hi, 'passAttempts');
          if (rng() < M.interceptRate(handlers[hi], D.lineup[hi], O.ctxs[hi])) {  // 傳球被抄
            record(O, hi, 'tov'); record(O, hi, 'usageEvents');
            record(O, hi, 'interceptedPasses'); record(D, hi, 'stl');
            O.stat.passes += C.MAX_PASSES - passesLeft;
            // 失誤要記進球權：真實 USG% 的分子是 FGA + 0.44FTA + **TOV**，
            // 少記的話 Draymond 這種「傳球一流、投籃很差」的人會被系統性低估。
            if (log.length < 400) log.push({ poss, off, handler: O.lineup[hi].name, ev: 'TOV' });
            emit('STEAL', off, hi, { defender: hi });
            alive = false; break;
          }
          // 接球者：跑位拉開空檔的人先拿到，再看他接球投的品質
          const passerIndex = hi;
          const passer = handlers[hi];
          const cand = O.lineup.map((_, i) =>
            i === hi ? 0 : best(i, passer.pass ?? 70).ev);
          hi = pickWeighted(M.receiverWeights(cand, O.lineup, hi, rollAccess), rng());
          record(O, hi, 'receptions');
          emit('PASS', off, hi, { from: passerIndex });
          assist = passer.pass ?? 70;
          passesLeft--;
          p = best(hi, assist);
        }
      }
      if (!alive) break;
      if (forced) {
        const c = assist === null ? null : dist(hi, { assist, forced: true });
        const o = dist(hi, { assist: null, forced: true });
        p = (c && c.ev > o.ev) ? c : o;
      }
      O.stat.passes += C.MAX_PASSES - passesLeft;
      if (assist !== null) O.stat.assisted++;
      if (forced) O.stat.forced++;
      O.stat.touches++;
      record(O, hi, 'shotOpportunities');
      record(O, hi, 'evSum', p.ev);
      record(O, hi, 'doubleRateSum', M.doubleRate(handlers[hi], O.ctxs[hi]));

      // 出手 / 持球失誤 / 犯規
      if (rng() < p.pTovTouch) {
        record(O, hi, 'tov'); record(O, hi, 'usageEvents');
        if (log.length < 400) log.push({ poss, off, handler: O.lineup[hi].name, ev: 'TOV' });
        emit('TOV', off, hi);
        alive = false; continue;
      }
      const ev = sampleShot(p, rng);
      let blocker = null;
      record(O, hi, 'usageEvents');

      if (ev === 'FOUL') {
        // Foul attribution follows the model's matched on-ball defender.
        // No extra RNG calls: split the existing free throws into replay beats.
        record(D, hi, 'pf');
        emit('FOUL', off, hi, { defender: hi, attempts: C.FT_ATTEMPTS });
        for (let i = 0; i < C.FT_ATTEMPTS; i++) {
          record(O, hi, 'fta');
          const made = rng() < p.ftPct;
          if (made) { O.score++; record(O, hi, 'ftm'); record(O, hi, 'pts'); }
          emit(made ? 'FTM' : 'FTX', off, hi, { attempt: i + 1, attempts: C.FT_ATTEMPTS });
        }
        alive = false;
      } else if (ev === 'FG3M') {
        O.score += 3; record(O, hi, 'pts', 3); record(O, hi, 'fg3m');
        record(O, hi, 'fg3a'); record(O, hi, 'fga'); alive = false;
      } else if (ev === 'MIDM') {
        O.score += 2; record(O, hi, 'pts', 2); record(O, hi, 'midm');
        record(O, hi, 'mida'); record(O, hi, 'fga'); alive = false;
      } else if (ev === 'RIMM') {
        O.score += 2; record(O, hi, 'pts', 2); record(O, hi, 'rimm');
        record(O, hi, 'rima'); record(O, hi, 'fga'); alive = false;
      } else {
        if (ev === 'FG3X') record(O, hi, 'fg3a');
        else if (ev === 'MIDX') record(O, hi, 'mida');
        else record(O, hi, 'rima');
        record(O, hi, 'fga');
        const zone = ev === 'FG3X' ? 'long' : ev === 'MIDX' ? 'mid' : 'short';
        if (blocks) {
          const profile = blockProfile(D.lineup, { zone, shooterIndex: hi, makeProbability: p.make[zone] });
          if (blockRng() < profile.conditionalOnMiss) {
            const bi = pickWeighted(profile.weights, blockRng());
            record(D, bi, 'blk'); record(O, hi, 'blka');
            blocker = D.lineup[bi].name;
          }
        }
        emit(ev, off, hi, { blocker });
        const reboundChance = reboundModel === 'legacy' ? p.pOreb
          : offensiveReboundProbability(O.lineup, D.lineup, { zone, shooterIndex: hi, leagueShare: leagueReboundShare });
        if (rng() < reboundChance) {
          O.stat.oreb++;
          // 誰搶到，以及他要不要直接放回去。對手護框強就放不進去，只好拉出來重組。
          const weights = reboundModel === 'legacy' ? M.reboundWeights(O.lineup)
            : opportunityReboundWeights(O.lineup, { side:'offense', zone, shooterIndex:hi });
          const rb = pickWeighted(weights, rng());
          O.players[rb].oreb++;
          emit('OREB', off, rb);
          if (rng() < M.putbackRate(O.lineup[rb], help[1 - off])) {
            putbackBy = rb; O.stat.putbacks++;
          }
        } else {
          const weights = reboundModel === 'legacy' ? M.reboundWeights(D.lineup)
            : opportunityReboundWeights(D.lineup, { side:'defense', zone });
          const rb = pickWeighted(weights, attributionRng());
          record(D, rb, 'dreb');
          emit('DREB', 1 - off, rb);
          alive = false;
        }
      }

      if (['FG3M', 'MIDM', 'RIMM'].includes(ev)) emit(ev, off, hi);
      if (log.length < 400) log.push({ poss, off, handler: O.lineup[hi].name, ev,
        ...(blocker === null ? {} : { blocker }) });
    }
    if (alive) O.stat.truncations++;

    poss++;
    off = 1 - off;
  }

  return {
    scoreA: sides[0].score, scoreB: sides[1].score,
    winnerA: sides[0].score > sides[1].score,
    tie: sides[0].score === sides[1].score,
    possessions: poss,
    statA: finalize(sides[0].stat), statB: finalize(sides[1].stat),
    playersA: playerRows(sides[0].players, teamA.roster, sides[0].stat),
    playersB: playerRows(sides[1].players, teamB.roster, sides[1].stat),
    fatigue: false, reboundModel,
    coverage: { blocks: blocks ? 'miss-decomposition-v1' : 'disabled', steals: 'pass-interceptions-only',
      rebounds: 'live-field-goal-misses-only' },
    log,
    ...(replay ? { events } : {}),
  };
}

function newStat() {
  return Object.fromEntries(COUNT_KEYS.map(k => [k, 0]));
}

function finalize(s) {
  const fgm = s.fg3m + s.midm + s.rimm;
  return {
    ...s,
    fgm, reb: s.oreb + s.dreb,
    fgPct: s.fga ? fgm / s.fga : null,
    twoPct: s.fga>s.fg3a ? (s.midm+s.rimm)/(s.fga-s.fg3a) : null,
    ftPct: s.fta ? s.ftm / s.fta : null,
    threePct: s.fg3a ? s.fg3m / s.fg3a : null,
    meanEv: s.shotOpportunities ? s.evSum / s.shotOpportunities : null,
    meanDoubleRate: s.shotOpportunities ? s.doubleRateSum / s.shotOpportunities : null,
    passPerPoss: s.poss ? s.passes / s.poss : 0,
    assistedRate: s.touches ? s.assisted / s.touches : 0,
    forcedRate: s.touches ? s.forced / s.touches : 0,
    putbackRate: s.oreb ? s.putbacks / s.oreb : 0,
    efg: s.fga ? (fgm + 0.5 * s.fg3m) / s.fga : 0,
    longPct: s.fg3a ? s.fg3m / s.fg3a : 0,
    midPct: s.mida ? s.midm / s.mida : 0,
    shortPct: s.rima ? s.rimm / s.rima : 0,
    longRate: s.fga ? s.fg3a / s.fga : 0,
    midRate: s.fga ? s.mida / s.fga : 0,
    shortRate: s.fga ? s.rima / s.fga : 0,
    tovPct: s.poss ? s.tov / s.poss : 0,
  };
}

function playerRows(players, roster, team, n = 1) {
  const usageTotal = team.fga + 0.44 * team.fta + team.tov;
  return players.map((counts, i) => {
    const stats = averageStat(counts, n);
    // 原團隊傳球鏈診斷沒有球員歸屬；不以假的 0 對外呈現。
    for (const k of ['poss', 'passes', 'touches', 'assisted', 'forced', 'putbacks',
      'truncations', 'passPerPoss', 'assistedRate', 'forcedRate', 'putbackRate', 'tovPct']) delete stats[k];
    return {
    name: roster[i].name, pos: roster[i].pos,
    ...stats,
    // 全員同時上場的固定五人陣容；不是整季官方 USG%。
    usagePct: usageTotal ? 100 * (counts.fga + 0.44 * counts.fta + counts.tov) / usageTotal : null,
    eventSharePct: team.usageEvents ? 100 * counts.usageEvents / team.usageEvents : null,
    teamPossessions: team.poss / n,
    };
  });
}

function averageStat(counts, n) {
  const result = finalize(counts);
  for (const k of COUNT_KEYS) result[k] /= n;
  result.fgm /= n;
  result.reb /= n;
  return result;
}

/** Monte Carlo：跑 n 場，回傳勝率與平均統計。 */
export function monteCarlo(teamA, teamB, n = 1000, opts = {}) {
  if (opts.mode === 'timed') throw new RangeError('Use simulateGame with mode: timed; legacy Monte Carlo assumes fixed-lineup count keys');
  if (!Number.isSafeInteger(n) || n < 1) throw new RangeError('n must be a positive integer');
  let wins = 0, ties = 0, sumA = 0, sumB = 0, sumPoss = 0;
  // 統計要先累加次數再算比率。中投一場只有約 3 次出手，若把每場的比率平均，
  // 投 0 次的場次會貢獻 0，把中投命中率壓低約 4 個百分點。
  const c = newStat(), d = newStat();
  const playersA = teamA.roster.map(() => newStat());
  const playersB = teamB.roster.map(() => newStat());
  const moments = [teamA, teamB].map(t => t.roster.map(() => ({ pts: 0, reb: 0, tov: 0, blk: 0 })));
  const margins = [];
  for (let i = 0; i < n; i++) {
    const g = simulateGame(teamA, teamB, { ...opts, seed: (opts.seed ?? 1) + i * 7919 });
    if (g.tie) ties++; else if (g.winnerA) wins++;
    sumA += g.scoreA; sumB += g.scoreB; sumPoss += g.possessions;
    margins.push(g.scoreA - g.scoreB);
    for (const k of COUNT_KEYS) {
      c[k] += g.statA[k]; d[k] += g.statB[k];
      for (let j = 0; j < playersA.length; j++) playersA[j][k] += g.playersA[j][k] ?? 0;
      for (let j = 0; j < playersB.length; j++) playersB[j][k] += g.playersB[j][k] ?? 0;
    }
    for (const [side, rows] of [g.playersA, g.playersB].entries()) {
      rows.forEach((p, j) => {
        for (const k of ['pts', 'reb', 'tov', 'blk']) moments[side][j][k] += p[k] ** 2;
      });
    }
  }
  const mean = margins.reduce((s, x) => s + x, 0) / n;
  const sd = Math.sqrt(margins.reduce((s, x) => s + (x - mean) ** 2, 0) / n);
  const withUncertainty = (counts, roster, team, side) =>
    playerRows(counts, roster, team, n).map((row, i) => ({ ...row,
      standardError: Object.fromEntries(['pts', 'reb', 'tov', 'blk'].map(k => [k,
        n > 1 ? Math.sqrt(Math.max(0, moments[side][i][k] - n * row[k] ** 2) / (n - 1) / n) : null])),
    }));
  return {
    n, winRateA: wins / n, tieRate: ties / n,
    avgScoreA: sumA / n, avgScoreB: sumB / n, avgPossessions: sumPoss / n,
    marginMean: mean, marginSd: sd, statA: averageStat(c, n), statB: averageStat(d, n),
    playersA: withUncertainty(playersA, teamA.roster, c, 0),
    playersB: withUncertainty(playersB, teamB.roster, d, 1),
  };
}
