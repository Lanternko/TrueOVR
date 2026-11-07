// E-184: sim 0.1.2 runner with defender foul beta scaled by k (as E-166 core166), shooter foul-draw exponent a (engine-e184, amendment A1)
// and per-player box FGA/FTA. k=1, c=-0.03125, pace=0.99875, a=1 is sim 0.1.2 (B0); k=2, c=-0.05625, pace=0.998125, a=1 is B2 (E-166, R-115).
import {impactEngine} from './engine-e184.mjs';
import {loadX, loadBeta, computeDraws} from '../E140-foul-on-recal/winimp-core-e140.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
export {loadX, computeDraws};
export const ARMS = {B0: {k: 1, c: -0.03125, pace: 0.99875, a: 1}, B2: {k: 2, c: -0.05625, pace: 0.998125, a: 1}};
export function scaledBeta(k) { const b = loadBeta(); for (const id in b) b[id] *= k; return b; }
export async function makeRunner({k = 1, c = ARMS.B0.c, pace = ARMS.B0.pace, a = 1} = {}) {
  const run = await impactEngine('rotation-space', {game: true, foulBeta: scaledBeta(k), c, pace, a});
  return {src: source(), run};
}
// Wrap run so each game also adds every real player's box FGA/FTA into acc[playerId] (roster order == playersA/B order, checked by name).
export function withPlayerBox(r, acc) {
  const run = (A, B, o) => {
    const g = r.run(A, B, o);
    for (const [team, box] of [[A, g.playersA], [B, g.playersB]]) team.roster.forEach((p, i) => {
      if (box[i].name !== p.name) throw Error('box order ' + p.name + ' vs ' + box[i].name);
      if (!(p.playerId > 0)) return;
      const s = acc[p.playerId] ??= {name: p.name, fga: 0, fta: 0, ftr: p.shotProfile?.freeThrowsPerAttempt ?? null};
      s.fga += box[i].fga; s.fta += box[i].fta;
    });
    return g;
  };
  return {...r, run};
}
export const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
