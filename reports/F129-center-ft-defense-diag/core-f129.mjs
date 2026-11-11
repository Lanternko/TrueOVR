// E-166: sim 0.1.2 runner with the defender foul beta table scaled by k (A1: fb = sum(k*beta) == k*sum(beta), src untouched).
// Base = E-140 harness (engine-e140 stamps defenderFoulBeta, foulBaseShift=c, pace multiplier). k=1, c=-0.03125, pace=0.99875 is sim 0.1.2.
import {impactEngine} from './engine-e140-f129.mjs';
import {loadX, loadBeta, computeDraws} from '../E140-foul-on-recal/winimp-core-e140.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
export {loadX, computeDraws};
export const C012 = -0.03125, P012 = 0.99875;
export function scaledBeta(k) { const b = loadBeta(); for (const id in b) b[id] *= k; return b; }
export async function makeRunner({k = 1, c = C012, pace = P012} = {}) {
  const run = await impactEngine('rotation-space', {game: true, foulBeta: scaledBeta(k), c, pace});
  return {src: source(), run};
}
export const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
