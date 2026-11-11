// v55: swap v53's long/mid/short/ft card attributes for one of the four v55 variants built by
// build-cards.mjs (reports/ovr-v55-bench-prior-2025-26/cards-<variant>.json). Unlike v54's
// shooting-eb.mjs, build-cards.mjs's output is a raw 0-1 shrunk rate (not yet an attribute value), so
// the shotDelta logit shift is applied directly in probability space before inverse(curve) -- no need
// for the M.interpolate(card,curve) round-trip v54 needed (its cache already held attribute values).
import fs from 'node:fs';
import * as C from '../../src/constants.js';
import {inverse} from '../../scripts/export_defense_sixth_cards.js';
const read = f => JSON.parse(fs.readFileSync(f));
const CURVES = {long: C.CURVE_3PT, mid: C.CURVE_MID, short: C.CURVE_SHORT, ft: C.CURVE_FT};
const cardCache = new Map();
function v55Cards(variant) {
  if (!cardCache.has(variant)) cardCache.set(variant, read(`reports/ovr-v55-bench-prior-2025-26/cards-${variant}.json`));
  return cardCache.get(variant);
}
let shotDeltaCache = null;
function shotDelta() {
  shotDeltaCache ??= read('reports/defense-tenth/step4-rebounds-oreb/2025-26/calibration-oreb.json').selected.shotDelta;
  return shotDeltaCache;
}
function shiftRate(rate, curve, delta) {
  const v = Math.max(.001, Math.min(.999, rate));
  return Math.max(0, Math.min(120, inverse(1 / (1 + Math.exp(-Math.log(v / (1 - v)) - delta)), curve)));
}
export function applyV55Shooting(players, season, variant) {
  if (season !== '2025-26') return players;
  const cards = v55Cards(variant), delta = shotDelta();
  for (const p of players) {
    const c = cards[p.playerId];
    if (!c) throw new Error(`Missing v55 (${variant}) card for playerId ${p.playerId}`);
    for (const zone of ['long', 'mid', 'short', 'ft']) p[zone] = shiftRate(c[zone], CURVES[zone], delta);
  }
  return players;
}
