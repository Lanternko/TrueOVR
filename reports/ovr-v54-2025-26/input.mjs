// v54 OVR input: the v53 pressure-adjusted input (reports/ovr-v53-2025-26/input.mjs) with the
// long/short card attributes swapped for the reliability-aware (empirical-Bayes) version
// (./shooting-eb.mjs). Pressure coefficients, spread scale, engine and benchmark harness are
// all exactly v53 — this is "v53 engine + new cards, everything else held fixed".
import {ovrInput as v53Input, pressureCoefficients, spreadScale} from '../ovr-v53-2025-26/input.mjs';
import {applyV54Shooting} from './shooting-eb.mjs';
export {pressureCoefficients, spreadScale};
export async function ovrInput(variant) {
  const x = await v53Input(variant);
  applyV54Shooting([...x.players, ...x.opponents.flatMap(t=>t.roster)], '2025-26');
  return x;
}
