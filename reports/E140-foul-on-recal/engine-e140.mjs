// E-140: v53 impactEngine wrapper. opts: foulBeta (null=off), c (foulBaseShift), pace (opt.pace).
// Stamped LAST on the final options arg. fatigue:false always (sim 0.1.1 rejects fatigue:true; A1 point 1). defenderClockBeta stays off.
// pace is a MULTIPLIER on the options-own pace (x.options.pace=0.8847); 1 = neutral. (Defect fix 2026-10-31: stamping absolute 1 overrode 0.8847.)
import {impactEngine as v53} from '../player-impact-v53/engine.mjs';
export async function impactEngine(version, options = {}) {
  const {foulBeta = null, c = 0, pace = 1, ...rest} = options;
  const inner = await v53(version, rest);
  const run = (...a) => {
    const o = a[a.length - 1], add = {fatigue: false};
    if (foulBeta) { add.defenderFoulBeta = foulBeta; add.foulBaseShift = c; add.pace = o.pace * pace; }
    else if (c || pace !== 1) throw Error('c/pace only with beta on');
    a[a.length - 1] = {...o, ...add};
    return inner(...a);
  };
  return Object.assign(run, inner);
}
