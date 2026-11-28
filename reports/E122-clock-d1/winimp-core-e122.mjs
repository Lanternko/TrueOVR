import {loadX, computeDraws, averageProfiles} from '../card-0.1.2+E065-inout-wins/winimp-core.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
import {impactEngine} from './engine-e122.mjs';
import fs from 'node:fs';
export {loadX, computeDraws, averageProfiles};
export function loadBeta(){
  const f=JSON.parse(fs.readFileSync(new URL('../E119-clock-pressure/fullfit-d1-2025-26.json',import.meta.url),'utf8'));
  const m={};f.playerIds.forEach((id,i)=>{m[id]=f.defenderEffects[i];});return m;
}
export async function makeRunner(beta = null) {
  const run = await impactEngine('rotation-space', {game: true, beta}), src = source();
  return {src, run};
}
