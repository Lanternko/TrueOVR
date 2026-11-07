// v55 OVR input: v53's pressure-adjusted input with long/mid/short/ft swapped for one of the four
// v55 variants (A, C, AC, AC_oos -- see build-cards.mjs). Everything else (pressure coefficients,
// spread scale, engine, benchmark harness) is exactly v53, same pattern as reports/ovr-v54-2025-26/input.mjs.
import {ovrInput as v53Input, pressureCoefficients, spreadScale} from '../ovr-v53-2025-26/input.mjs';
import {applyV55Shooting} from './shooting-v55.mjs';
export {pressureCoefficients, spreadScale};
export function ovrInputFor(cardVariant) {
  return async function ovrInput(variant) {
    const x = await v53Input(variant);
    applyV55Shooting([...x.players, ...x.opponents.flatMap(t => t.roster)], '2025-26', cardVariant);
    return x;
  };
}
