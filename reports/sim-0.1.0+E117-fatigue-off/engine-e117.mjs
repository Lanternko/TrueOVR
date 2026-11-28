// E-117: v53 impactEngine wrapper. fatigue=true -> options pass through unchanged (current HEAD behaviour);
// fatigue=false -> every game's options get fatigue:false stamped LAST (after benchmark.mjs options()), nothing else changes.
import {impactEngine as v53} from '../player-impact-v53/engine.mjs';
export async function impactEngine(version, options = {}) {
  const {fatigue = true, ...rest} = options;
  const inner = await v53(version, rest);
  const run = (...a) => {
    if (!fatigue) { const o = a[a.length - 1]; a[a.length - 1] = {...o, fatigue: false}; }
    return inner(...a);
  };
  return Object.assign(run, inner);
}
