import fs from 'node:fs';
import {read,table} from './defense_io.js';
import {runSeventh} from './run_defense_seventh.js';
import {teamDefenseMetrics,realCountStats} from '../src/defense_sixth_season.js';
const configFile=process.argv[2],version=process.argv[3]??'v4',c=read(configFile),bundle=read(c.root+'/bundle.json'),train=new Set(c.trainGames),logs=table(c.paths['data/season-source/team-games.json']).filter(r=>train.has(r.GAME_ID)),indices=bundle.league.schedule.flatMap((g,i)=>train.has(g.id)?[i]:[]),label="2023-24-eighth-c-calendar-25-v1";
const sum=rs=>Object.fromEntries(Object.keys(rs[0]).map(z=>[z,rs.reduce((s,r)=>s+(r[z]??0),0)])),stats=sum(logs.map(r=>realCountStats(r))),target=teamDefenseMetrics(stats,stats,logs.length),groups=bundle.measured.turnoverGroups,n=2*train.size;
const targets={passSteals:(groups.passing?.live??0)/n,touchSteals:Object.entries(groups).filter(([k])=>k!=='passing').reduce((s,[k,g])=>s+g.live,0)/n,clock:(groups.shotClock?.count??0)/n};
let calibration={shotDelta:0,options:{}},history=[];const seeds=[20260101,20260102,20260103];
for(let iteration=0;iteration<5;iteration++){
 const rs=await runSeventh('cal-'+label+'-'+iteration,{bundle:c.root+'/bundle.json',cutoff:c.k,phase:'train',calendarDate:c.date,indices,cardFile:version==='v4'?`${c.root}/pre${c.k}-v4-league.json`:c.leagueOutput,neutralContests:version==='v4',calibration},seeds);
 const ss=sum(rs.flatMap(r=>r.teams.map(t=>t.stats))),op=sum(rs.flatMap(r=>r.teams.map(t=>t.opponent))),sim=teamDefenseMetrics(ss,op,rs.reduce((s,r)=>s+r.teams.reduce((s,t)=>s+t.games,0),0));history.push({iteration,calibration:structuredClone(calibration),sim,target,targets});
 if(Math.abs(sim.offensiveRatingProxy-target.offensiveRatingProxy)<.12&&Math.abs(sim.possessionsProxy-target.possessionsProxy)<.15&&Math.abs(sim.opponentFTR-target.opponentFTR)<.002&&Math.abs(sim.turnovers-target.turnovers)<.15)break;
 const o={...bundle.options,...calibration.options},clip=(x,a,b)=>Math.max(a,Math.min(b,x));calibration.shotDelta+=clip((target.offensiveRatingProxy-sim.offensiveRatingProxy)/65,-.08,.08);
 calibration.options.pace=clip(o.pace*target.possessionsProxy/sim.possessionsProxy,.5,2);
 calibration.options.foulScale=clip(o.foulScale*target.opponentFTR/sim.opponentFTR,.1,3);
 calibration.options.passTurnoverScale=clip(o.passTurnoverScale*targets.passSteals/Math.max(.01,sim.passSteals),.1,5);
 const targetTouch=target.turnovers-targets.passSteals-targets.clock;
 calibration.options.touchTurnoverScale=clip(o.touchTurnoverScale*targetTouch/Math.max(.01,sim.touchTurnovers),.1,5);
 calibration.options.touchLiveShare=clip(o.touchLiveShare*targets.touchSteals/Math.max(.01,sim.touchSteals),.01,.99);
 calibration.options.clockViolationProbability=clip(o.clockViolationProbability*targets.clock/Math.max(.01,sim.clockTurnovers),0,.2);
}
fs.writeFileSync(c.root+'/calibration-'+version+'.json',JSON.stringify({date:c.date,version,seeds,trainGames:c.trainGames,target,targets,selected:history.at(-1).calibration,history,method:'At most five training-only iterations, three seeds, pooled league rates only; fixed simultaneous multiplicative moment updates. Global shooting logit step efficiency error/65 ±0.08. Last evaluated point, no after-cutoff calibration and no net/wins objective.'},null,2)+'\n');
