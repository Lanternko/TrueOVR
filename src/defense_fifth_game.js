// Separate empirical-clock experiment; frozen original, v1 and A stay unchanged.
// Versioned defense experiment fork. Keep timed_game.js unchanged so the
// original 1,230-game baseline remains reproducible during intervention tests.
import * as M from './probability_model.js';
import {effect,shifted,fourthProbability,continuousDuration,starterTarget} from './defense_fourth_effects.js';
import * as C from './constants.js';
import { makeRng, pickWeighted } from './rng.js';
import { offensiveReboundProbability, opportunityReboundWeights, blockProfile } from './rebound_block_model.js';
import {minuteBudgetSchedule} from './minute_budget.js';
import {DEFENSE_COUNT_KEYS,defenseProbabilities,pressureSignal,passPressureDefender,touchStealProbability,volumeWeights,attemptMakeProbability} from './defense_probability.js';

const KEYS = ['pts','fga','fgm','fg3a','fg3m','fta','ftm','oreb','dreb','ast','stl','blk','tov','pf','seconds','poss','passes',...DEFENSE_COUNT_KEYS,'teamOreb','teamDreb','deadFtReb','reboundChances','periodMiss','clockCandidates','clockExpectedTouch','clockExpectedLive','offensiveFoulTov','otherViolationTov','passOutTov','handlingOutTov','unmappedDeadTov','madeFoul','missFoul','timeSetup','timePass','timeRelease','timeFlight','timeInbound','timeViolation','timeOther','timingDraws','timingSampleSeconds','timingRawMeanSeconds'];
const blank = () => Object.fromEntries(KEYS.map(k => [k, 0]));
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const sum = xs => xs.reduce((a,b) => a+b,0);
const finish = s => ({ ...s, seconds:Math.round(s.seconds*10)/10, reb:s.oreb+s.dreb, minutes:Math.round(s.seconds*10)/600,
  fgPct:s.fga?s.fgm/s.fga:null, threePct:s.fg3a?s.fg3m/s.fg3a:null, ftPct:s.fta?s.ftm/s.fta:null });

export const TIMED_DEFAULTS = Object.freeze({ quarterSeconds:720, overtimeSeconds:300,
  maxOvertimes:20, substitutions:true, foulOut:6, pace:1,
  nonShootingFoulRate:0.04, andOneRate:0.025, replay:false, seed:1,
  contextScale:1, turnoverScale:1, blocks:true });

// Team foul counts include the just-committed defensive personal foul.
export function inPenalty(period, fouls, lastTwoFouls) {
  return fouls >= (period > 4 ? 4 : 5) || lastTwoFouls >= 2;
}
export function clockStrategy(period, seconds, lead) {
  if (period >= 4 && seconds <= 24 && lead > 0) return 'runClock';
  if (period >= 4 && seconds <= 120 && lead < 0) return 'hurry';
  if (period >= 4 && seconds <= 120 && lead > 0) return 'protectLead';
  if (seconds <= 24) return 'lastShot';
  return 'normal';
}

export function simulateDefenseFifthGame(teamA, teamB, options = {}) {
  const opt = { ...TIMED_DEFAULTS, minuteMode:'heuristic',turnoverMode:'legacy',stealPriorRate:.035,
    touchLiveShare:.5,shotSelection:'legacy',foulConditioning:false,excludeZeroTargets:false,endgameStrategies:true,minuteTargets:true,reboundAccounting:false,empiricalTiming:false,independentClock:false,foulOutcomes:false,turnoverCategories:false,...options };
  if(opt.empiricalTiming&&!opt.timingCDF)throw Error('Need empirical timing CDF');
  if(opt.independentClock&&!(opt.clockViolationProbability>=0&&opt.clockViolationProbability<=1))throw Error('Need observed clock-violation probability');
  if(typeof opt.foulConditioning!=='boolean')throw new Error('Invalid foulConditioning');
  for(const key of ['endgameStrategies','minuteTargets','reboundAccounting'])if(typeof opt[key]!=='boolean')throw new Error('Invalid '+key);
  if(opt.reboundAccounting)for(const zone of ['long','mid','short','ftFinal']){
    const r=opt.reboundRates?.[zone];
    if(!r||['teamProbability','teamOffShare','playerOffShare'].some(k=>!Number.isFinite(r[k])||r[k]<0||r[k]>1))throw new Error('Need audited rebound rates');
  }
  if(!['heuristic','budget'].includes(opt.minuteMode)||!['legacy','split','pressure'].includes(opt.turnoverMode)||!['legacy','volume'].includes(opt.shotSelection))throw new Error('Invalid defense mode');
  for(const k of ['stealPriorRate','touchLiveShare'])if(!Number.isFinite(opt[k])||opt[k]<0||opt[k]>1)throw new Error('Invalid '+k);
  if(opt.stealPriorRate===0)throw new Error('Need positive steal prior');
  if(opt.minuteMode==='budget'&&(opt.quarterSeconds!==720||opt.foulOut!==99))throw new Error('Budget diagnostic requires 48-minute regulation and foulOut=99');
  for (const k of ['quarterSeconds','overtimeSeconds']) {
    if (!Number.isFinite(opt[k]) || opt[k] < 1 || opt[k] > 3600 || !Number.isInteger(opt[k]*10)) throw new RangeError(`Invalid ${k}`);
  }
  if (!Number.isInteger(opt.maxOvertimes) || opt.maxOvertimes < 0 || opt.maxOvertimes > 100) throw new RangeError('Invalid maxOvertimes');
  if (!Number.isInteger(opt.foulOut) || opt.foulOut < 1) throw new RangeError('Invalid foulOut');
  if (!Number.isFinite(opt.pace) || opt.pace < 0.5 || opt.pace > 2) throw new RangeError('Invalid pace');
  for (const k of ['nonShootingFoulRate','andOneRate']) if (!Number.isFinite(opt[k]) || opt[k]<0 || opt[k]>1) throw new RangeError(`Invalid ${k}`);
  for (const k of ['contextScale','turnoverScale']) if (!Number.isFinite(opt[k]) || opt[k]<0) throw new RangeError(`Invalid ${k}`);
  for (const k of ['substitutions','blocks','replay']) if (typeof opt[k] !== 'boolean') throw new TypeError(`Invalid ${k}`);
  if (opt.fatigue !== undefined) { if (typeof opt.fatigue !== 'boolean') throw new TypeError('Invalid fatigue'); if (opt.fatigue) throw new Error('fatigue removed in sim 0.1.1'); }
  if (!Number.isSafeInteger(opt.seed)) throw new RangeError('Invalid seed');
  const attrs = ['long','mid','short','drive','tovSkill','pass','ft','rebound','onBall','help','stamina','physique','offBall','screen'];
  const sides = [teamA,teamB].map(t => {
    if (!Array.isArray(t?.roster) || t.roster.length<5) throw new RangeError('Timed games require at least five players');
    for (const p of t.roster) {
      for (const k of attrs) if (!Number.isFinite(p[k]) || p[k]<0) throw new RangeError(`Invalid player attribute: ${k}`);
      if (p.targetMinutes !== undefined && (!Number.isFinite(p.targetMinutes) || p.targetMinutes<0 || p.targetMinutes>48)) throw new RangeError('Invalid targetMinutes');
    }
    const eligible = t.roster.flatMap((p,i)=>p.injured||(opt.excludeZeroTargets&&p.targetMinutes===0)?[]:[i]);
    if (eligible.length<5) throw new RangeError('At least five healthy players are required');
    if(opt.minuteMode==='budget'&&t.roster.some(p=>p.injured))throw new Error('Budget diagnostic cannot contain injured players');
    return { roster:t.roster, lineup:eligible.slice(0,5), players:t.roster.map(blank), stat:blank(),
      budget:opt.minuteMode==='budget'?minuteBudgetSchedule(t.roster):null,
      stint:t.roster.map(()=>0), teamFouls:0, lastTwoFouls:0, periods:[] };
  });
  const rng = makeRng(opt.seed), timeRng = makeRng(opt.seed ^ 0x2B947EF1), eventRng=makeRng(opt.seed^0x791BC34D);
  const reboundRng=makeRng(opt.seed^0x163AB371);
  const empiricalRng=makeRng(opt.seed^0x47B223A1),violationRng=makeRng(opt.seed^0x55CA9101);
  let origin='period',plannedViolation=false;
  const empiricalDuration=()=>{
    const a=opt.timingCDF[origin]??opt.timingCDF.period;
    // Conditional empirical draw, not clipping all the probability mass to 24s.
    const limit=Math.min(shotClock/10-.1,clock/10-.1)*opt.pace;
    let lo=0,hi=a.length;while(lo<hi){const mid=(lo+hi)>>1;if(a[mid]<=limit)lo=mid+1;else hi=mid;}
    const seconds=opt.continuousTiming?continuousDuration(a,limit,empiricalRng)/opt.pace:lo?a[Math.floor(empiricalRng()*lo)]/opt.pace:Math.max(.1,Math.min(clock,shotClock)/10-.1);
    return Math.max(1,Math.min(seconds*10,shotClock-1,clock-1));
  };
  const events = [];
  let period=0, clock=0, shotClock=240, off=0, elapsed=0, possessions=0;
  const budgetBoundaries=opt.minuteMode==='budget'?[...new Set(sides.flatMap(s=>s.budget.map(x=>Math.round(x.end*10))))].sort((a,b)=>a-b):[];
  let budgetBoundaryIndex=0;
  const opening = rng()<0.5?0:1;
  const emit = (type, side=off, player=null, extra={}) => {
    if (opt.replay) events.push({ type, period, clock:clock/10, shotClock:shotClock/10,
      elapsed:elapsed/10, off:side, player, poss:possessions,
      score:sides.map(s=>s.stat.pts), lineups:sides.map(s=>[...s.lineup]), ...extra });
  };
  const record = (side, player, key, n=1) => {
    sides[side].stat[key]+=n;
    if (player!==null) sides[side].players[player][key]+=n;
  };
  const applyBudget = () => {
    if(opt.minuteMode!=='budget'||elapsed>=28800)return;
    for(const [side,s] of sides.entries()){
      const segment=s.budget.find(x=>elapsed>=Math.round(x.start*10)&&elapsed<Math.round(x.end*10));
      if(!segment)throw new Error('Missing minute-budget segment');
      const next=segment.lineup;
      if(next.every(i=>s.lineup.includes(i)))continue;
      const outgoing=s.lineup.filter(i=>!next.includes(i)),incoming=next.filter(i=>!s.lineup.includes(i));
      for(let j=0;j<incoming.length;j++){
        const out=outgoing[j],into=incoming[j];s.lineup[s.lineup.indexOf(out)]=into;s.stint[out]=0;s.stint[into]=0;
        emit('SUBSTITUTION',side,into,{out,forced:false,budgetControl:true});
      }
    }
  };
  const advanceSegment = ticks => {
    const dt=Math.min(clock,Math.max(0,Math.round(ticks)));
    clock-=dt; shotClock=Math.max(0,shotClock-dt); elapsed+=dt;
    for (const s of sides) for (let i=0;i<s.roster.length;i++) {
      const playing=s.lineup.includes(i);
      if (playing) { record(s===sides[0]?0:1,i,'seconds',dt/10);if(period<=4)record(s===sides[0]?0:1,i,'regulationSeconds',dt/10);s.stint[i]+=dt/10; }
    }
  };
  const advance = (ticks,tag="Other") => {
    record(off,null,"time"+tag,Math.min(clock,Math.max(0,Math.round(ticks)))/10);
    let left=Math.min(clock,Math.max(0,Math.round(ticks)));
    while(left>0){
      applyBudget();
      while(budgetBoundaryIndex<budgetBoundaries.length&&budgetBoundaries[budgetBoundaryIndex]<=elapsed)budgetBoundaryIndex++;
      const boundary=budgetBoundaries[budgetBoundaryIndex]??Infinity;
      const step=Math.min(left,boundary-elapsed);
      advanceSegment(step);left-=step;applyBudget();
    }
  };
  const rotate = (forced=false, protectedPlayer=null, protectedSide=-1) => {
    if(opt.minuteMode==='budget'&&period<=4){applyBudget();return;}
    for (const [side,s] of sides.entries()) {
      const desired=opt.scoreRotation?starterTarget(period,clock/10,s.stat.pts-sides[1-side].stat.pts,opt.rotationCurve):null;
      const eligible=s.roster.flatMap((p,i)=>!p.injured && s.players[i].pf<opt.foulOut && (!(opt.minuteMode==='budget'||opt.excludeZeroTargets)||p.targetMinutes>0)?[i]:[]);
      for (let slot=0;slot<5;slot++) {
        const out=s.lineup[slot];
        if (side===protectedSide && out===protectedPlayer) continue;
        const invalid=s.players[out].pf>=opt.foulOut;
        if (!invalid && (!opt.substitutions || (!forced && s.stint[out]<150))) continue;
        const candidates=eligible.filter(i=>!s.lineup.includes(i));
        const value = i => {
          const p=s.roster[i];
          const ability=sum(['long','short','pass','onBall','help','rebound'].map(k=>p[k]))/6;
          const target=p.targetMinutes ?? (i<5?32:16);
          const expected=target/48*(elapsed/600);
          return ability+(opt.minuteTargets?6*(expected-s.players[i].seconds/60):0)
            +(p.pos===s.roster[out].pos?8:0)
            +(opt.scoreRotation&&i<5?(opt.rotationGain??60)*(5*desired-s.lineup.filter(j=>j<5).length):0);
        };
        candidates.sort((a,b)=>value(b)-value(a)||a-b);
        const into=candidates[0];
        if (into!==undefined && (invalid || value(into)>value(out)+3)) {
          s.lineup[slot]=into; s.stint[out]=0; s.stint[into]=0;
          emit('SUBSTITUTION',side,into,{out,forced:invalid});
        }
      }
    }
  };
  const lineups = () => sides.map(s=>s.lineup.map(i=>s.roster[i]));
  const rebound = (shooter, zone, freeThrow=false) => {
    // No player rebound is awarded to a miss after the period has expired.
    if (clock<=0) {record(off,null,'periodMiss');return {end:true,dead:true};}
    // The clock starts on the legal touch of a missed FT, not during its flight.
    if (!freeThrow) advance(3+Math.floor(timeRng()*10),"Flight");
    if (clock<=0) {record(off,null,'periodMiss');return {end:true,dead:true};}
    record(off,null,'reboundChances');
    const rate=opt.reboundRates?.[freeThrow?'ftFinal':zone];
    if(opt.reboundAccounting&&reboundRng()<rate.teamProbability){
      const offensive=reboundRng()<rate.teamOffShare,side=offensive?off:1-off;
      record(side,null,offensive?'teamOreb':'teamDreb');
      if(offensive)shotClock=140;
      origin=offensive?'retained':'dreb';
      emit(offensive?'TEAM_OREB':'TEAM_DREB',side,null,{freeThrow,outOfBounds:true});
      return {end:!offensive,dead:true,putback:null};
    }
    const ls=lineups(), os=ls[off], ds=ls[1-off];
    const slot=sides[off].lineup.indexOf(shooter);
    // FT rebounding is a separate provisional prior; not calibrated tracking data.
    let chance=freeThrow?(opt.reboundAccounting?rate.playerOffShare:0.12):offensiveReboundProbability(os,ds,
      {zone,shooterIndex:slot,...(opt.reboundAccounting&&opt.reboundProfile!==false?{leagueShare:rate.playerOffShare}:{})});
    if(opt.reboundSignal){
      // Replacement: keep the attacking rebound opportunity, neutralize old defensive skill.
      const neutral=ds.map(p=>({...p,rebound:70,physique:70}));
      const baseline=freeThrow?rate.playerOffShare:offensiveReboundProbability(os,neutral,{zone,shooterIndex:slot});
      chance=1-shifted(1-baseline,effect(ds,'DREB',opt));
    }
    const offensive=rng()<chance, side=offensive?off:1-off;
    const index=pickWeighted(opportunityReboundWeights(ls[side],{zone,side:offensive?'offense':'defense',shooterIndex:offensive?slot:-1}),rng());
    const player=sides[side].lineup[index];
    record(side,player,offensive?'oreb':'dreb');
    if (offensive) shotClock=140;
    origin=offensive?'retained':'dreb';
    emit(offensive?'OREB':'DREB',side,player,{freeThrow});
    return {end:!offensive,dead:false,putback:offensive && !freeThrow && rng()<M.putbackRate(ls[side][index],M.helpDefense(ds))?player:null};
  };
  const foul = (defender, kind, shooter) => {
    const side=1-off,s=sides[side];
    record(side,defender,'pf'); s.teamFouls++;
    if(clock<=1200)s.lastTwoFouls++;
    emit('FOUL',side,defender,{kind,shooter,teamFouls:s.teamFouls});
    if(s.players[defender].pf>=opt.foulOut) {
      const available=s.roster.some((p,i)=>!p.injured && !s.lineup.includes(i) && s.players[i].pf<opt.foulOut && (!opt.excludeZeroTargets||p.targetMinutes>0));
      if(available) rotate(true,shooter,off);
      else {
        // NBA minimum-five exception: retain the disqualified player and add a technical FT.
        emit('MINIMUM_FIVE_EXCEPTION',side,defender);
        const taker=[...sides[off].lineup].sort((a,b)=>sides[off].roster[b].ft-sides[off].roster[a].ft)[0];
        record(off,taker,'fta');
        const pct=clamp(M.interpolate(sides[off].roster[taker].ft,C.CURVE_FT),0.3,0.98);
        const made=rng()<pct;
        if(made){record(off,taker,'ftm');record(off,taker,'pts');}
        emit(made?'FTM':'FTX',off,taker,{technical:true,attempt:1,attempts:1});
      }
    }
  };
  const freeThrows = (shooter, attempts, pct) => {
    rotate(false,shooter,off);
    let made=false;
    for(let attempt=1;attempt<=attempts;attempt++) {
      record(off,shooter,'fta'); made=rng()<pct;
      if(made){record(off,shooter,'ftm');record(off,shooter,'pts');}
      emit(made?'FTM':'FTX',off,shooter,{attempt,attempts});
      if(opt.reboundAccounting&&!made&&attempt<attempts){record(off,null,'deadFtReb');emit('DEAD_FT_REBOUND',off,null,{attempt,attempts});}
    }
    if(made)origin='made';
    return made?{end:true,dead:true}:rebound(shooter,'short',true);
  };
  const opportunity = putback => {
    if (clock <= 3) {
      // No new catch-and-shoot is generated in the final 0.3 seconds.
      // Tip-ins from inbounds are not modelled in this prototype.
      advance(clock); emit('NO_SHOT'); return {end:true,dead:true};
    }
    let ls=lineups(), O=sides[off], D=sides[1-off];
    if(plannedViolation){plannedViolation=false;advance(shotClock,"Violation");const player=O.lineup[0];record(off,player,'tov');record(off,player,'deadTov');record(off,player,'clockTov');emit('SHOT_CLOCK',off,player,{independent:true});origin='turnover';return {end:true,dead:true};}
    const opportunityDeadline=opt.empiricalTiming?elapsed+empiricalDuration():null;
    let hi=putback===null?pickWeighted(opt.shotSelection==='volume'?volumeWeights(ls[off]):M.handlingWeights(ls[off]),rng()):O.lineup.indexOf(putback);
    let shooter=O.lineup[hi], passer=null, assist=null, usedAssist=false;
    const refresh=()=>{if(opt.minuteMode!=='budget')return;ls=lineups();shooter=O.lineup[hi];if(passer!==null&&!O.lineup.includes(passer)){passer=null;assist=null;usedAssist=false;}};
    const strategy=opt.endgameStrategies?clockStrategy(period,clock/10,O.stat.pts-D.stat.pts):'normal';
    emit('TOUCH',off,shooter,{strategy});
    const intentional=opt.endgameStrategies && period>=4 && clock<=270 && clock>3 && O.stat.pts>D.stat.pts && O.stat.pts-D.stat.pts<=6;
    if(strategy==='runClock' && !intentional && clock<=shotClock) { advance(clock); return {end:true,dead:true}; }
    const timeFactor=strategy==='hurry'?0.6:strategy==='protectLead'?1.4:1;
    // Set up offense; leave time for a release at the end of a period.
    const setup=intentional?5+timeRng()*15:opt.empiricalTiming?Math.max(1,(opportunityDeadline-elapsed)*.45):putback===null?(40+timeRng()*60)*timeFactor/opt.pace:2;
    advance(Math.min(setup,Math.max(0,clock-4),Math.max(0,shotClock-2)),"Setup");
    refresh();
    if(intentional || rng()<opt.nonShootingFoulRate*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1)) {
      advance(Math.min(2,clock-1));
      foul(D.lineup[hi],intentional?'intentional':'nonShooting',shooter);
      if(inPenalty(period,D.teamFouls,D.lastTwoFouls)) return freeThrows(shooter,2,clamp(M.interpolate(ls[off][hi].ft,C.CURVE_FT),0.3,0.98));
      shotClock=Math.max(shotClock,140); rotate();
      origin='retained';
      return {end:false,dead:true,putback:null};
    }
    const probability = (i,a=null,forced=false) => {
      const os=ls[off],ds=ls[1-off];
      const tr = lineup=>C.weightedTop(lineup.map(p=>p.rebound*(1-C.PHYS_REB_WEIGHT)+p.physique*C.PHYS_REB_WEIGHT),C.COMPOSITE.teamRebound);
      return fourthProbability(os[i],M.teammateContext(os,i),ds[i],M.helpDefense(ds),tr(os),tr(ds),M.teamPhysique(ds),
        {assist:a,forced,putback:putback!==null,contextScale:opt.contextScale,turnoverScale:opt.turnoverScale,
          turnoverMode:opt.turnoverMode,pressureAttribute:opt.liveSignal?70:pressureSignal(ds,opt.stealPriorRate).attribute,
          contextLongScale:opt.contextLongScale,contextShortScale:opt.contextShortScale},ds,opt);
    };
    const best = (i,a,forced=false) => {
      const own=probability(i,null,forced), caught=a===null?null:probability(i,a,forced);
      usedAssist=!!caught && caught.ev>=own.ev;
      return usedAssist?caught:own;
    };
    let p=best(hi,null), passesLeft=C.MAX_PASSES;
    while(putback===null && passesLeft>0 && clock>15 && shotClock>25 && rng()>=M.shootRate(p.ev,passesLeft)) {
      advance(Math.min(opt.empiricalTiming?Math.max(1,(opportunityDeadline-elapsed)*.18):12+timeRng()*20,clock-2,shotClock-2),"Pass");
      refresh();
      const pressureDefender=opt.liveSignal?{...ls[1-off][hi],onBall:70}:opt.turnoverMode==='pressure'?passPressureDefender(ls[1-off][hi],ls[1-off],opt.stealPriorRate):ls[1-off][hi];
      if(rng()>=M.passOpenRate(ls[off][hi],M.teammateContext(ls[off],hi),pressureDefender))break;
      if(rng()<Math.min(.95,M.interceptRate(ls[off][hi],pressureDefender,M.teammateContext(ls[off],hi))*(opt.turnoverCategories?opt.passTurnoverScale:1)*(opt.liveSignal?Math.exp(effect(ls[1-off],'liveTOV',opt)):1))) {
        const interceptor=opt.turnoverMode==='legacy'?D.lineup[hi]:D.lineup[pickWeighted(pressureSignal(ls[1-off],opt.stealPriorRate).weights,eventRng())];
        record(off,shooter,'tov');record(off,shooter,'liveTov');record(1-off,interceptor,'stl');record(1-off,interceptor,'passSteals');
        emit('STEAL',1-off,interceptor,{from:shooter,kind:'pass'});origin='turnover';return {end:true,dead:false};
      }
      passer=shooter; assist=ls[off][hi].pass;
      const candidates=opt.shotSelection==='volume'?volumeWeights(ls[off],'shot').map((w,i)=>i===hi?0:w)
        :ls[off].map((_,i)=>i===hi?0:Math.max(probability(i,assist).ev,probability(i).ev));
      hi=pickWeighted(opt.shotSelection==='volume'?candidates:M.receiverWeights(candidates,ls[off],hi),rng());
      shooter=O.lineup[hi];record(off,passer,'passes');passesLeft--;
      emit('PASS',off,shooter,{from:passer});p=best(hi,assist);
    }
    let shotTime=opt.empiricalTiming?Math.max(1,opportunityDeadline-elapsed):putback!==null?2+timeRng()*7:
      strategy==='lastShot' && clock<=shotClock?Math.max(0,clock-1):(25+timeRng()*40)*timeFactor/opt.pace;
    if(shotTime>=shotClock && shotClock<clock) {
      record(off,shooter,'clockCandidates');
      const counterfactual=best(hi,assist,true).pTovTouch;
      record(off,shooter,'clockExpectedTouch',counterfactual);
      record(off,shooter,'clockExpectedLive',counterfactual*touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare));
      if(!opt.independentClock){advance(shotClock,"Violation");refresh();record(off,shooter,'tov');record(off,shooter,'deadTov');record(off,shooter,'clockTov');emit('SHOT_CLOCK',off,shooter);origin='turnover';return {end:true,dead:true};}
      shotTime=Math.max(0,shotClock-1);
    }
    advance(Math.min(shotTime,Math.max(0,clock-1)),"Release");
    refresh();
    if(clock<1) return {end:true,dead:true};
    p=best(hi,assist,shotClock<20||clock<15);
    const originalLive=opt.liveSignal?opt.touchLiveShare:touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare);
    const liveMultiplier=opt.liveSignal?Math.exp(effect(ls[1-off],'liveTOV',opt)):1;
    const touchMultiplier=1-originalLive+originalLive*liveMultiplier;
    if(rng()<Math.min(.95,p.pTovTouch*(opt.turnoverCategories?opt.touchTurnoverScale:1)*touchMultiplier)){
      record(off,shooter,'tov');
      record(off,shooter,'touchTov');
      const live=opt.turnoverMode!=='legacy'&&eventRng()<originalLive*liveMultiplier/touchMultiplier;
      record(off,shooter,live?'liveTov':'deadTov');
      if(live){
        const thief=D.lineup[pickWeighted(pressureSignal(ls[1-off],opt.stealPriorRate).weights,eventRng())];
        record(1-off,thief,'stl');record(1-off,thief,'touchSteals');emit('STEAL',1-off,thief,{from:shooter,kind:'touch'});
      }else if(opt.turnoverCategories){
        const kinds=['offensiveFoulTov','otherViolationTov','passOutTov','handlingOutTov','unmappedDeadTov'];
        const kind=kinds[pickWeighted(opt.deadCategoryWeights,eventRng())];record(off,shooter,kind);
        if(kind==='offensiveFoulTov')record(off,shooter,'pf');
        emit('TOV',off,shooter,{kind});
      }else emit('TOV',off,shooter,{kind:'dead'});
      // Classification alone keeps the original dead-ball rotation/timing.
      // A transition-state model is a separate future intervention.
      origin='turnover';return {end:true,dead:true};
    }
    const zones=['long','mid','short'];
    const foulInputs=Object.fromEntries(zones.map(z=>{
      const r=opt.foulRates?.[z],profile=ls[off][hi].shotProfile?.freeThrowsPerAttempt;
      const scale=opt.foulOutcomes?Math.max(.25,Math.min(2.5,(profile??opt.leagueFTR)/(opt.relativeFouls?opt.foulProfileMeans[z]:opt.leagueFTR)))*opt.foulScale*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1):1;
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
    if(shootingFoul && !made) {
      foul(D.lineup[hi],'shooting',shooter);
      return freeThrows(shooter,points,p.ftPct);
    }
    record(off,shooter,'fga');if(zone==='long')record(off,shooter,'fg3a');
    if(zone==='mid')record(off,shooter,'mida');if(zone==='short')record(off,shooter,'rima');
    record(off,shooter,'xfgm',p.make[zone]);if(zone==='long')record(off,shooter,'x3m',p.make[zone]);
    if(made) {
      origin='made';
      record(off,shooter,'fgm');record(off,shooter,'pts',points);if(zone==='long')record(off,shooter,'fg3m');
      if(zone==='mid')record(off,shooter,'midm');if(zone==='short')record(off,shooter,'rimm');
      if(usedAssist && passer!==null && passer!==shooter)record(off,passer,'ast');
    }
    let blocker=null;
    if(!made && opt.blocks) {
      const bp=blockProfile(ls[1-off],{zone,shooterIndex:hi,makeProbability:p.make[zone]});
      if(rng()<bp.conditionalOnMiss){blocker=D.lineup[pickWeighted(bp.weights,rng())];record(1-off,blocker,'blk');}
    }
    emit(made?'FGM':'FGX',off,shooter,{zone,points:made?points:0,assist:made&&usedAssist?passer:null,blocker});
    if(made && (shootingFoul || andOne)) {foul(D.lineup[hi],'andOne',shooter);return freeThrows(shooter,1,p.ftPct);}
    if(made) {
      const stopped=clock<=(period>=4?1200:600);
      // Inbound delay consumes game time but not the next team's shot clock.
      if(!stopped) advance(10+Math.floor(timeRng()*20),"Inbound");
      return {end:true,dead:false};
    }
    return rebound(shooter,zone);
  };
  let complete=true;
  for(period=1;;period++) {
    if(period>4+opt.maxOvertimes){complete=false;period--;break;}
    clock=Math.round((period<=4?opt.quarterSeconds:opt.overtimeSeconds)*10);
    shotClock=240;
    off=period>4?(rng()<0.5?0:1):([opening,1-opening,1-opening,opening][period-1]);
    for(const s of sides){s.teamFouls=0;s.lastTwoFouls=0;}
    rotate(true);emit('PERIOD_START');
    origin='period';
    const start=sides.map(s=>s.stat.pts);
    while(clock>0) {
      shotClock=240;possessions++;record(off,null,'poss');emit('POSSESSION');
      plannedViolation=opt.independentClock&&clock>shotClock&&violationRng()<opt.clockViolationProbability;
      let outcome={end:false,putback:null};
      while(clock>0 && !outcome.end) outcome=opportunity(outcome.putback??null);
      if(outcome.dead)rotate();
      off=1-off;
    }
    for(const [i,s] of sides.entries())s.periods.push(s.stat.pts-start[i]);
    emit('PERIOD_END');
    if(period>=4 && sides[0].stat.pts!==sides[1].stat.pts)break;
  }
  emit(complete?'GAME_END':'OVERTIME_LIMIT');
  const result = { mode:'timed-defense', complete, termination:complete?'final':'overtimeLimit',
    scoreA:sides[0].stat.pts,scoreB:sides[1].stat.pts,tie:sides[0].stat.pts===sides[1].stat.pts,
    winnerA:complete?sides[0].stat.pts>sides[1].stat.pts:null,
    periods:period,overtimes:Math.max(0,period-4),gameSeconds:elapsed/10,possessions,
    periodScores:sides.map(s=>s.periods), statA:finish(sides[0].stat),statB:finish(sides[1].stat),
    playersA:sides[0].players.map((p,i)=>({name:teamA.roster[i].name,pos:teamA.roster[i].pos,...finish(p)})),
    playersB:sides[1].players.map((p,i)=>({name:teamB.roster[i].name,pos:teamB.roster[i].pos,...finish(p)})),
    coverage:{model:'nba-defense-third-experimental',foulOutcomes:opt.foulOutcomes,turnoverCategories:opt.turnoverCategories,empiricalTiming:opt.empiricalTiming,independentClock:opt.independentClock,minuteMode:opt.minuteMode,turnoverMode:opt.turnoverMode,
      foulConditioning:opt.foulConditioning,shotSelection:opt.shotSelection,
      touchStealTransition:false,space:'abstract',timeouts:false,injuries:'pre-game-only',
      offensiveFouls:opt.turnoverCategories,backcourtViolations:false,shotFlight:'release-time-outcome',rebounds:'field-goals-and-final-free-throws',blocks:'miss-decomposition',
      assist:'last-pass-if-catch-shot-selected',rotation:opt.minuteMode==='budget'?'synthetic-exposure-schedule; live-clock substitutions; no disqualification':'energy-target-minutes-position-heuristic'} };
  return opt.replay?{...result,events}:result;
}
