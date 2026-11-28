import fs from 'node:fs';
import {clockInputs} from '../src/defense_clock_jobs.js';
import {thirdOptions} from '../src/defense_third_jobs.js';
import {simulateDefenseClockAuditGame} from '../src/defense_third_clock_audit.js';
import {thirdLineup} from '../src/defense_third_minutes.js';
import {read,hash} from './defense_io.js';
const {inputs,timing}=clockInputs(),teams=new Map(inputs.league.teams.map(t=>[t.id,t])),boxes=new Map(inputs.exposure.games.map(g=>[g.id,g]));
const results=[];
for(const pace of [1,.836]){
  const draws={};let seconds=0;
  for(const [i,f] of inputs.league.schedule.entries()){
    const b=boxes.get(f.id),pair=[f.homeId,f.awayId].map((id,j)=>thirdLineup(teams.get(id),f[j?'awayPlayerIds':'homePlayerIds'],b.teams.find(t=>t.teamId===id)));
    const game=simulateDefenseClockAuditGame(...pair,{...thirdOptions('empirical',{pace}),seed:(20261012+Math.imul(i+1,7919))>>>0,durationAudit:d=>{
      const r=draws[d.origin]??={count:0,rawSeconds:0,deadlineSeconds:0,excludedShare:0,shortClock:0};r.count++;r.rawSeconds+=d.rawSeconds;r.deadlineSeconds+=d.deadlineSeconds;r.excludedShare+=1-d.eligibleCount/d.fullCount;r.shortClock+=d.shotClock<24;
    }});seconds+=game.gameSeconds;
  }
  results.push({pace,secondsPerGame:seconds/1230,states:Object.fromEntries(Object.entries(draws).map(([k,d])=>[k,{drawsPerGame:d.count/1230,rawSeconds:d.rawSeconds/d.count,scaledDeadlineSeconds:d.deadlineSeconds/d.count,meanExcludedCDFShare:d.excludedShare/d.count,shortClockShare:d.shortClock/d.count,deadlineSecondsPerGame:d.deadlineSeconds/1230,empiricalPositiveMean:timing.states[k].reduce((a,b)=>a+b,0)/timing.states[k].length}]))});
  console.log('time audit',pace);
}
fs.writeFileSync('reports/defense-third/time-audit.json',JSON.stringify({results,provenance:{source:hash('src/defense_third_game.js'),audit:hash('src/defense_third_clock_audit.js')},definition:'Observational fork with optional callback; no new draws or probability changes. Raw durations positive-filtered then conditional CDF cut at remaining shot clock * pace, divided by pace. Sum deadlines is not elapsed time: pass steals and nonshooting fouls can preempt deadlines.'},null,2)+'\n');
