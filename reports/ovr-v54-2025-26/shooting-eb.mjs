// v54: swap the v53 long/short card attributes for the reliability-aware (empirical-Bayes) ones from
// data/season-league-v54.json (scripts/build_season_league.js --shooting-eb), restricted to 2025-26 —
// the only season build_season_league.js generates. Other seasons' cards come from a separate
// hand-rolled formula in reports/defense-tenth/step4-t0/prepare.mjs and are left untouched (see
// reports/ovr-v54-2025-26/report.md, "其他季別" for the reasoning).
//
// Every raw card value from build_season_league.js is later passed through a single additive-logit
// shift ("shotDelta", reports/player-impact-v1/input.mjs's project()) before the engine ever sees it.
// That shift is a pure per-player function of (card value, curve, shotDelta) with no dependence on any
// other player or state, so reapplying it here to the v54 raw cards is exactly equivalent to having
// regenerated bundle.json from a v54 season-league file and let project() run normally — verified
// byte-for-byte against the real v53 pipeline's Karlo Matković card in report.md's reproduction log.
import fs from 'node:fs';
import * as M from '../../src/probability_model.js';
import * as C from '../../src/constants.js';
import {inverse} from '../../scripts/export_defense_sixth_cards.js';
const read=f=>JSON.parse(fs.readFileSync(f));
let cardCache=null;
function v54Cards() {
  cardCache??=Object.fromEntries(read('data/season-league-v54.json').teams.flatMap(t=>t.roster).map(p=>[p.playerId,{long:p.long,short:p.short}]));
  return cardCache;
}
let shotDeltaCache=null;
function shotDelta() {
  shotDeltaCache??=read('reports/defense-tenth/step4-rebounds-oreb/2025-26/calibration-oreb.json').selected.shotDelta;
  return shotDeltaCache;
}
function shiftCard(card,curve,delta) {
  const v=Math.max(.001,Math.min(.999,M.interpolate(card,curve)));
  return Math.max(0,Math.min(120,inverse(1/(1+Math.exp(-Math.log(v/(1-v))-delta)),curve)));
}
export function applyV54Shooting(players,season) {
  if (season!=='2025-26') return players;
  const cards=v54Cards(),delta=shotDelta();
  for (const p of players) {
    const c=cards[p.playerId];
    if (!c) throw new Error('Missing v54 card for playerId '+p.playerId);
    p.long=shiftCard(c.long,C.CURVE_3PT,delta);
    p.short=shiftCard(c.short,C.CURVE_SHORT,delta);
  }
  return players;
}
