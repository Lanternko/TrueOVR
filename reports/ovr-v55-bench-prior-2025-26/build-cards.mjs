// v55: build 2025-26 shooting cards (long/mid/short/ft) under four variants, on top of v54's
// methodology (reports/ovr-v54-2025-26/report.md, scripts/build_season_league.js --shooting-eb).
//
// Change A (multi-season pooling): pool 2022-23..2025-26 makes/attempts per player per zone with
//   fixed recency weights [1, .7, .5, .35] (2025-26 first). Weights are a fixed schedule, not CV-fit
//   (time/compute budget -- see report.md "設計與限制"); chosen so each season back halves influence
//   roughly every two seasons (0.7^2 = 0.49 ~ 0.5), a common simple recency-decay choice.
// Change C (role-conditional prior): the shrinkage target mu_i is no longer a single position mean
//   (scripts/build_season_league.js:50-51) but sigmoid(alpha_pos[pos_i] + beta*ln(mpg_i)), fit by
//   weighted least squares (weight = pooled attempts) of logit((makes+.5)/(attempts+1)) on position
//   dummies + ln(seasonMinutesPerGame). This puts the coach's rotation-minutes signal into the prior.
// Variants:
//   A       -- multi-season pooling, position-only prior (mu_pos), mpg/pos covariate from 2025-26.
//   C       -- single season (2025-26 only, same raw data as v54), role-conditional prior.
//   AC      -- multi-season pooling AND role-conditional prior. mpg/pos covariate from 2025-26.
//   AC_oos  -- out-of-sample guard: pooling excludes 2025-26 (2024-25/2023-24/2022-23 only), role-
//              conditional prior fit on that same pooled data; mpg/pos covariate taken from 2024-25
//              (the most recent pre-2025-26 season) so the attribute build never touches 2025-26 data.
//
// EB reliability k_z: method-of-moments on Var(p_i) = tau2 + pbar(1-pbar)/n_i, same form as v54, but
// residuals are taken against each player's OWN prior mean mu_i (not the single global mean v54 used)
// -- a more internally-consistent generalization once mu_i varies by player, documented in report.md.
//
//   node reports/ovr-v55-bench-prior-2025-26/build-cards.mjs --variant A
//   node reports/ovr-v55-bench-prior-2025-26/build-cards.mjs --variant C
//   node reports/ovr-v55-bench-prior-2025-26/build-cards.mjs --variant AC
//   node reports/ovr-v55-bench-prior-2025-26/build-cards.mjs --variant AC_oos
//
// Writes reports/ovr-v55-bench-prior-2025-26/cards-<variant>.json: {playerId: {long,mid,short,ft}}
// (raw 0-1 shrunk rates, pre-inverse-curve -- shooting-eb-v55.mjs applies inverse()+shotDelta) and
// reports/ovr-v55-bench-prior-2025-26/fit-<variant>.json (k_z, tau2, alpha_pos/beta or positionMeans).
import fs from 'node:fs';

const ZONES = ['long', 'mid', 'short', 'ft'];
const POSITIONS = ['PG', 'SG', 'SF', 'PF', 'C'];
const ALL_SEASON_WEIGHTS = [['2025-26', 1], ['2024-25', 0.7], ['2023-24', 0.5], ['2022-23', 0.35]];
const OOS_SEASON_WEIGHTS = [['2024-25', 0.7], ['2023-24', 0.5], ['2022-23', 0.35]];

const variant = process.argv[process.argv.indexOf('--variant') + 1];
if (!['A', 'C', 'AC', 'AC_oos'].includes(variant)) throw new Error('Usage: --variant A|C|AC|AC_oos');
const multiSeason = variant === 'A' || variant === 'AC' || variant === 'AC_oos';
const roleConditional = variant === 'C' || variant === 'AC' || variant === 'AC_oos';
const oos = variant === 'AC_oos';

const zonesRaw = JSON.parse(fs.readFileSync(new URL('./zones-raw.json', import.meta.url)));
const roster2025 = zonesRaw['2025-26']; // {playerId: {..., pos, MIN, GP, heightInches, name}}
const playerIds = Object.keys(roster2025).map(Number);

function seasonWeights() {
  if (!multiSeason) return [['2025-26', 1]];
  return oos ? OOS_SEASON_WEIGHTS : ALL_SEASON_WEIGHTS;
}

function pooledCounts(zone) {
  const out = new Map();
  for (const [season, w] of seasonWeights()) {
    const players = zonesRaw[season];
    if (!players) throw new Error('Missing season data: ' + season);
    for (const [pidStr, p] of Object.entries(players)) {
      const attempts = p[zone + 'A'], makes = p[zone + 'M'];
      if (!(attempts > 0)) continue;
      const pid = Number(pidStr);
      const e = out.get(pid) ?? { makes: 0, attempts: 0 };
      e.makes += w * makes; e.attempts += w * attempts;
      out.set(pid, e);
    }
  }
  return out;
}

// Role covariates: which season's pos/mpg represents "today's role". A/C/AC use 2025-26 (the season
// being carded); AC_oos must not touch 2025-26 at all, so it falls back to 2024-25.
const roleSeason = oos ? '2024-25' : '2025-26';
const roleRows = zonesRaw[roleSeason];
const fallbackLogMpg = (() => {
  const vals = Object.values(roleRows).filter(p => p.GP > 0).map(p => Math.log(Math.max(0.5, p.MIN / p.GP)));
  vals.sort((a, b) => a - b);
  return vals[Math.floor(vals.length / 2)];
})();
function roleOf(playerId) {
  const r = roleRows[playerId] ?? roleRows[String(playerId)];
  if (r && r.GP > 0 && r.pos) return { pos: r.pos, logMpg: Math.log(Math.max(0.5, r.MIN / r.GP)) };
  // Rookie with no roleSeason history (e.g. debuted in 2025-26 but roleSeason=2024-25): use this
  // player's 2025-26 position (height doesn't change) with the league-median log(mpg) for that season.
  const h = roster2025[playerId]?.heightInches ?? roster2025[String(playerId)]?.heightInches;
  const pos = roster2025[playerId]?.pos ?? (h != null ? posOfHeight(h) : 'SF');
  return { pos, logMpg: fallbackLogMpg };
}
function posOfHeight(h) { return h <= 75 ? 'PG' : h <= 78 ? 'SG' : h <= 80 ? 'SF' : h <= 82 ? 'PF' : 'C'; }

function solveWLS(rows, k) {
  const XtX = Array.from({ length: k }, () => new Array(k).fill(0));
  const Xty = new Array(k).fill(0);
  for (const { x, y, w } of rows) {
    for (let i = 0; i < k; i++) { Xty[i] += w * x[i] * y; for (let j = 0; j < k; j++) XtX[i][j] += w * x[i] * x[j]; }
  }
  const n = k, M = XtX.map((row, i) => [...row, Xty[i]]);
  for (let col = 0; col < n; col++) {
    let piv = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[piv][col])) piv = r;
    [M[col], M[piv]] = [M[piv], M[col]];
    const d = M[col][col];
    if (Math.abs(d) < 1e-9) throw new Error('Singular matrix in WLS fit (zone has too little data)');
    for (let j = col; j <= n; j++) M[col][j] /= d;
    for (let r = 0; r < n; r++) { if (r === col) continue; const f = M[r][col]; for (let j = col; j <= n; j++) M[r][j] -= f * M[col][j]; }
  }
  return M.map(row => row[n]);
}

function fitZone(zone) {
  const counts = pooledCounts(zone);
  // Role-conditional prior: logit((makes+.5)/(attempts+1)) ~ position dummies + beta*ln(mpg), WLS
  // weight = pooled attempts. Position-only prior: attempt-weighted raw rate by position.
  let predictMu, fitInfo;
  if (roleConditional) {
    const rows = [];
    for (const [pid, { makes, attempts }] of counts) {
      const { pos, logMpg } = roleOf(pid);
      const x = POSITIONS.map(p => (p === pos ? 1 : 0)); x.push(logMpg);
      const p = (makes + 0.5) / (attempts + 1);
      rows.push({ x, y: Math.log(p / (1 - p)), w: attempts });
    }
    const beta = solveWLS(rows, POSITIONS.length + 1);
    const alpha = Object.fromEntries(POSITIONS.map((p, i) => [p, beta[i]]));
    const slope = beta[POSITIONS.length];
    predictMu = pid => { const { pos, logMpg } = roleOf(pid); const z = alpha[pos] + slope * logMpg; return 1 / (1 + Math.exp(-z)); };
    fitInfo = { mode: 'positionConditionalOnLogMpg', alphaPos: alpha, betaLogMpg: slope, players: rows.length };
  } else {
    const byPos = new Map(POSITIONS.map(p => [p, { makes: 0, attempts: 0 }]));
    for (const [pid, { makes, attempts }] of counts) {
      const { pos } = roleOf(pid);
      const e = byPos.get(pos); e.makes += makes; e.attempts += attempts;
    }
    const positionMeans = Object.fromEntries([...byPos].map(([p, e]) => [p, e.makes / e.attempts]));
    predictMu = pid => positionMeans[roleOf(pid).pos];
    fitInfo = { mode: 'positionOnly', positionMeans, players: counts.size };
  }
  // EB reliability k_z: Var(p_i) = tau2 + pbar(1-pbar)/n_i, residual against each player's own mu_i.
  const qualified = [...counts].filter(([, c]) => c.attempts >= 20);
  const pbar = qualified.reduce((s, [, c]) => s + c.makes, 0) / qualified.reduce((s, [, c]) => s + c.attempts, 0);
  const residuals = qualified.map(([pid, c]) => c.makes / c.attempts - predictMu(pid));
  const meanResidual = residuals.reduce((s, r) => s + r, 0) / residuals.length;
  const varRate = residuals.reduce((s, r) => s + (r - meanResidual) ** 2, 0) / residuals.length;
  const meanInvN = qualified.reduce((s, [, c]) => s + 1 / c.attempts, 0) / qualified.length;
  const tau2 = varRate - pbar * (1 - pbar) * meanInvN;
  const k = tau2 > 0 ? Math.max(50, Math.min(2000, pbar * (1 - pbar) / tau2 - 1)) : 500;
  const shrunk = new Map();
  for (const pid of playerIds) {
    const c = counts.get(pid) ?? { makes: 0, attempts: 0 };
    const mu = predictMu(pid);
    shrunk.set(pid, (c.makes + k * mu) / (c.attempts + k));
  }
  return { shrunk, fit: { ...fitInfo, k, tau2, pbar, qualifiedPlayers: qualified.length } };
}

const cards = {}, fits = {};
for (const zone of ZONES) {
  const { shrunk, fit } = fitZone(zone);
  fits[zone] = fit;
  for (const pid of playerIds) { cards[pid] ??= {}; cards[pid][zone] = shrunk.get(pid); }
}
fs.writeFileSync(`reports/ovr-v55-bench-prior-2025-26/cards-${variant}.json`, JSON.stringify(cards));
fs.writeFileSync(`reports/ovr-v55-bench-prior-2025-26/fit-${variant}.json`, JSON.stringify({ variant, multiSeason, roleConditional, oos, seasonWeights: seasonWeights(), roleSeason, zones: fits }, null, 1));
console.log(JSON.stringify({ variant, players: playerIds.length, zones: Object.fromEntries(ZONES.map(z => [z, { k: fits[z].k, tau2: fits[z].tau2, mode: fits[z].mode }])) }, null, 1));
