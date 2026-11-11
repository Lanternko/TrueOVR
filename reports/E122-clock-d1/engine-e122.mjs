// E-122: v53 impactEngine wrapper. beta=null -> options pass through unchanged (current HEAD).
// beta=Map-like object {playerId:beta} -> stamped LAST as opt.defenderClockBeta (default-off src option).
import {impactEngine as v53} from '../player-impact-v53/engine.mjs';
export async function impactEngine(version, options = {}) {
  const {beta = null, ...rest} = options;
  const inner = await v53(version, rest);
  const run = (...a) => {
    if (beta) { const o = a[a.length - 1]; a[a.length - 1] = {...o, defenderClockBeta: beta}; }
    return inner(...a);
  };
  return Object.assign(run, inner);
}
