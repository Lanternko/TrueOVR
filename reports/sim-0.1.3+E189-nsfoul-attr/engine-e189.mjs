// E-189: v53 impactEngine wrapper = F-129 engine-e140-f129 (stamps fatigue:false; optional foulBaseShift=c and pace multiplier on top of benchmark options(), which is already sim 0.1.3)
// plus nsAttr = {playerId: gamma} (null = off) and nsBase (multiplier on the non-shooting-foul gate). Flag off == sim 0.1.3 (parity.json).
import {impactEngine as v53} from './engine-e189-v53.mjs';
export async function impactEngine(version, options = {}) {
  const {c, pace, nsAttr = null, nsBase = 1, ...rest} = options;
  const inner = await v53(version, rest);
  const nsExp = nsAttr ? Object.fromEntries(Object.entries(nsAttr).map(([k, g]) => [k, Math.exp(g)])) : null;
  const run = (...a) => {
    const o = a[a.length - 1], add = {fatigue: false};
    // benchmark.mjs options() already carries sim 0.1.3 (beta x2, c=-0.05625, pace x0.998125). c overrides foulBaseShift; pace multiplies the options pace (1 = unchanged).
    if (c !== undefined) add.foulBaseShift = c;
    if (pace !== undefined && pace !== 1) add.pace = o.pace * pace;
    // sim 0.1.4: benchmark options() now carries nsFoulExp by default; this harness keeps its own semantics (nsAttr null = flag off), so always override.
    add.nsFoulExp = nsExp;
    if (nsExp) add.nsFoulBase = nsBase; else if (nsBase !== 1) throw Error('nsBase only with nsAttr');
    a[a.length - 1] = {...o, ...add};
    return inner(...a);
  };
  return Object.assign(run, inner);
}
