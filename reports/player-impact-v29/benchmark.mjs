import fs from 'node:fs';
import {workloadRotation} from '../../src/player_workload.js';
const read=f=>JSON.parse(fs.readFileSync(f));
export const source=()=>read('reports/player-impact-v29/workload-source.json');
export function workloadTeam(x, player, slot, minutes, cap, phase=0){
 const loads=x.profiles.map(()=>cap);loads[slot]=minutes;
 const team={name:'工作負荷測試隊',season:'2025-26',roster:[
  ...x.profiles.map((p,i)=>({...structuredClone(i===slot?player:p),pos:p.pos,courtPosition:p.pos,targetMinutes:loads[i],injured:false})),
  ...x.profiles.map((p,i)=>({...structuredClone(p),playerId:-2000-i,targetMinutes:48-loads[i],injured:false}))
 ]};
 return {team,schedule:workloadRotation(loads,phase)};
}
export function opponentTeam(x, opponent, cap, phase=0){
 const loads=x.profiles.map(()=>cap);
 return {team:{...opponent,roster:[...opponent.roster.map(p=>({...p,targetMinutes:cap,injured:false})),
  ...x.profiles.map((p,i)=>({...structuredClone(p),playerId:-3000-i,targetMinutes:48-cap,injured:false}))]},
  schedule:workloadRotation(loads,phase)};
}
// sim 0.1.2 (R-094, E-140/F-096): defender shooting-foul beta (E-116 2025-26 fit, as in E-120) is on by default,
// with the league foul base and pace recalibrated so league fouls, possessions and points match the beta-off engine.
// sim 0.1.3 (R-115, E-166/F-111, E-184/F-127): beta table x2 so the defender FTA-allowed spread matches real
// (non-center de-noised ratio 0.54 -> 1.04); foul base and pace re-solved (E-166 cal-cp-k2).
let foulBeta=null;
const defenderFoulBeta=()=>foulBeta??=(f=>Object.fromEntries(f.playerIds.map((id,i)=>[id,2*f.defenderEffects[i]])))(read('reports/E116-fouls-matchup/fullfit-f-2025-26.json'));
// sim 0.1.4 (R-131, E-189): non-shooting-foul attribute on by default. gamma = 2025-26 full-season, shrunk non-shooting
// personal fouls per 100 defensive possessions (reports/sim-0.1.4/build_ns_gamma.py, k frozen at the E-189 value); options carry exp(gamma).
// Gate x mean exp(gamma) of the 5 defenders, fouler drawn by exp(gamma). Calibration unchanged (E-189: m=1, c=-0.05625, pace 0.998125).
// Honoured only by the v53 engine chain (reports/player-impact-v53/engine.mjs); older engines ignore the option.
let nsFoulExp=null;
const nsFoulExpTable=()=>nsFoulExp??=(f=>Object.fromEntries(Object.entries(f.gamma).map(([id,g])=>[id,Math.exp(g)])))(read('reports/sim-0.1.4/ns-foul-gamma-2025-26.json'));
export function options(x, seed, schedules){
 return {...x.options,pace:(x.options?.pace??1)*0.998125,defenderFoulBeta:defenderFoulBeta(),foulBaseShift:-0.05625,nsFoulExp:nsFoulExpTable(),
  quarterSeconds:720,sourcePeriods:4,maxOvertimes:0,substitutions:true,
  minuteMode:'budget',foulOut:99,sourceRotations:schedules,seed,creationPolicy:'rotation-space',contextLongScale:1,
  spaceCenter:read('reports/player-impact-v20/2025-26-synthetic-center.json').fullCenter};
}
