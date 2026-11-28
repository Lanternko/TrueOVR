from pathlib import Path
root=Path(__file__).resolve().parents[1]
def source(name): return (root/name).read_text(encoding='utf-8')
def save(name,s): (root/name).write_text(s,encoding='utf-8')
s=source('src/defense_clock_game.js').replace('simulateDefenseClockGame','simulateDefenseThirdGame')
s=s.replace("'clockExpectedLive'];", "'clockExpectedLive','offensiveFoulTov','otherViolationTov','passOutTov','handlingOutTov','unmappedDeadTov','madeFoul','missFoul','timeSetup','timePass','timeRelease','timeFlight','timeInbound','timeViolation','timeOther','timingDraws','timingSampleSeconds','timingRawMeanSeconds'];")
s=s.replace('independentClock:false,...options','independentClock:false,foulOutcomes:false,turnoverCategories:false,...options')
s=s.replace('const advance = ticks => {','const advance = (ticks,tag="Other") => {\n    record(off,null,"time"+tag,Math.min(clock,Math.max(0,Math.round(ticks)))/10);')
s=s.replace('advance(3+Math.floor(timeRng()*10))','advance(3+Math.floor(timeRng()*10),"Flight")')
s=s.replace('advance(10+Math.floor(timeRng()*20))','advance(10+Math.floor(timeRng()*20),"Inbound")')
s=s.replace('advance(shotClock);','advance(shotClock,"Violation");')
s=s.replace('Math.max(0,shotClock-2)));','Math.max(0,shotClock-2)),"Setup");')
s=s.replace('clock-2,shotClock-2));','clock-2,shotClock-2),"Pass");')
s=s.replace('advance(Math.min(shotTime,Math.max(0,clock-1)));','advance(Math.min(shotTime,Math.max(0,clock-1)),"Release");')
s=s.replace('let p=best(hi,null), passesLeft=C.MAX_PASSES;','let p=best(hi,null), passesLeft=C.MAX_PASSES;')
s=s.replace('rng()<M.interceptRate(ls[off][hi],pressureDefender,M.teammateContext(ls[off],hi))','rng()<Math.min(.95,M.interceptRate(ls[off][hi],pressureDefender,M.teammateContext(ls[off],hi))*(opt.turnoverCategories?opt.passTurnoverScale:1))')
s=s.replace('if(rng()<p.pTovTouch){','if(rng()<Math.min(.95,p.pTovTouch*(opt.turnoverCategories?opt.touchTurnoverScale:1))){')
s=s.replace("}else emit('TOV',off,shooter,{kind:'dead'});", """}else if(opt.turnoverCategories){
        const kinds=['offensiveFoulTov','otherViolationTov','passOutTov','handlingOutTov','unmappedDeadTov'];
        const kind=kinds[pickWeighted(opt.deadCategoryWeights,eventRng())];record(off,shooter,kind);
        if(kind==='offensiveFoulTov')record(off,shooter,'pf');
        emit('TOV',off,shooter,{kind});
      }else emit('TOV',off,shooter,{kind:'dead'});""")
start=s.index("    let zone=['long','mid','short']")
end=s.index('    if(shootingFoul && !made)',start)
s=s[:start]+"""    const zones=['long','mid','short'];
    const foulInputs=Object.fromEntries(zones.map(z=>{
      const r=opt.foulRates?.[z],profile=ls[off][hi].shotProfile?.freeThrowsPerAttempt;
      const scale=opt.foulOutcomes?Math.max(.25,Math.min(2.5,(profile??opt.leagueFTR)/opt.leagueFTR))*opt.foulScale:1;
      const qMiss=opt.foulOutcomes?clamp(r.foulGivenMiss*scale,0,.8):0;
      const qMake=opt.foulOutcomes?clamp(r.foulGivenMake*scale,0,.4):0;
      const raw=opt.foulOutcomes?attemptMakeProbability(p.make[z],qMiss):p.make[z];
      return [z,{qMiss,qMake,raw,recorded:1-(1-raw)*qMiss}];
    }));
    // p.zone describes recorded FGA. Expand foul-miss opportunities before sampling.
    let zone=zones[pickWeighted(zones.map(z=>p.zone[z]/(opt.foulOutcomes?foulInputs[z].recorded:1)),rng())];
    if(opt.endgameStrategies && period>=4 && clock<=100 && D.stat.pts-O.stat.pts>=3 && putback===null) zone='long';
    const points=zone==='long'?3:2;
    const shootingFoulChance=clamp(p.pFoul/(1-p.pTovTouch),0,.999999);
    let shootingFoul,made,andOne;
    if(opt.foulOutcomes){
      made=rng()<foulInputs[zone].raw;
      shootingFoul=rng()<(made?foulInputs[zone].qMake:foulInputs[zone].qMiss);andOne=false;
      if(shootingFoul)record(off,shooter,made?'madeFoul':'missFoul');
    }else{
      shootingFoul=rng()<shootingFoulChance;
      made=rng()<(opt.foulConditioning?attemptMakeProbability(p.make[zone],shootingFoulChance):p.make[zone]);
      andOne=made && rng()<opt.andOneRate;
    }
"""+s[end:]
s=s.replace("model:'nba-defense-clock-experimental'","model:'nba-defense-third-experimental',foulOutcomes:opt.foulOutcomes,turnoverCategories:opt.turnoverCategories")
s=s.replace('offensiveFouls:false','offensiveFouls:opt.turnoverCategories')
save('src/defense_third_game.js',s)
s=source('src/defense_clock_season.js').replace('defense_clock_game','defense_third_game').replace('simulateDefenseClockGame','simulateDefenseThirdGame')
s=s.replace("'clockExpectedLive'];", "'clockExpectedLive','offensiveFoulTov','otherViolationTov','passOutTov','handlingOutTov','unmappedDeadTov','madeFoul','missFoul','timeSetup','timePass','timeRelease','timeFlight','timeInbound','timeViolation','timeOther','timingDraws','timingSampleSeconds','timingRawMeanSeconds'];")
s=s.replace("import {observedLineup} from './minute_budget.js';", "import {thirdLineup as observedLineup} from './defense_third_minutes.js';")
s=s.replace('observedTeams[i]));','observedTeams[i],options.seasonMinuteTargets));')
save('src/defense_third_season.js',s)
s=source('src/defense_clock_pool.js').replace('runClockJobs','runThirdJobs').replace('defense_clock_worker','defense_third_worker')
save('src/defense_third_pool.js',s)
s=source('scripts/defense_clock_worker.js').replace('executeClockJob','executeThirdJob').replace('defense_clock_jobs','defense_third_jobs')
save('scripts/defense_third_worker.js',s)
