import {loadX, computeDraws, averageProfiles} from '../card-0.1.2+E065-inout-wins/winimp-core.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
import {impactEngine} from './engine-e140.mjs';
import fs from 'node:fs';
export {loadX, computeDraws, averageProfiles};
export function loadBeta(){ // E-120 foul beta (same file as E-120)
  const f=JSON.parse(fs.readFileSync(new URL('../E116-fouls-matchup/fullfit-f-2025-26.json',import.meta.url),'utf8'));
  const m={};f.playerIds.forEach((id,i)=>{m[id]=f.defenderEffects[i];});return m;
}
// cfg: {beta:'on'|'off', c, pace}
export async function makeRunner(cfg = {}) {
  const on=cfg.beta==='on';
  const run = await impactEngine('rotation-space', {game: true, foulBeta: on?loadBeta():null, c: cfg.c||0, pace: cfg.pace||1}), src = source();
  return {src, run};
}
