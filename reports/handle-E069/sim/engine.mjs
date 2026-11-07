import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const cache=new Map(),url=f=>pathToFileURL(path.resolve(f)).href;
export async function impactEngine(version,{game=false,memoized=false}={}){
 const key=JSON.stringify([version,game,memoized]);if(cache.has(key))return cache.get(key);
 if(!['rotation-flow','rotation-creation','rotation-space'].includes(version))throw Error('Unknown creation model');
 let source=fs.readFileSync('reports/defense-tenth/step4-rebounds-turnover-time/adapter.mjs','utf8');
 const patches=[];
 const replace=(from,to)=>patches.push(`{const a=${JSON.stringify(from)};if(g.split(a).length!==2)throw Error('Impact source anchor drift: '+a);g=g.replace(a,${JSON.stringify(to)});}`);
 {
  // Move this closure ahead of handler selection. It does not capture hi.
  patches.push(`{const start=g.indexOf('    const probability = (i,a=null,forced=false) => {'),end=g.indexOf('    const best = (i,a,forced=false) => {',start);if(start<0||end<0)throw Error('Probability closure drift');const p=g.slice(start,end);g=g.slice(0,start)+g.slice(end);const anchor='    let hi=putback===null?';if(g.split(anchor).length!==2)throw Error('Selection anchor drift');g=g.replace(anchor,p+'    let creationPlan=putback===null?opportunityPlan(ls[off],probability,pressureSignal(ls[1-off],opt.stealPriorRate).relative,opt.creationPolicy):null;\\n'+anchor);}`);
  replace("volumeWeights(ls[off]):M.handlingWeights(ls[off])","creationPlan.weights:M.handlingWeights(ls[off])");
  replace('M.shootRate(p.ev,passesLeft)','(passesLeft===C.MAX_PASSES?creationPlan.rows[hi].shoot:1)');
  replace('M.passOpenRate(ls[off][hi],M.teammateContext(ls[off],hi),pressureDefender)','1');
  replace('M.interceptRate(ls[off][hi],pressureDefender,M.teammateContext(ls[off],hi))*(opt.turnoverCategories?opt.passTurnoverScale:1)','creationPlan.rows[hi].intercept');
  replace("volumeWeights(ls[off],'shot').map((w,i)=>i===hi?0:w)",'creationPlan.rows[hi].receivers');
  patches.push(`g="import {opportunityPlan,contestHelp,observedFoulInputs} from '${url('reports/player-impact-v14/model.mjs')}';\\n"+g;`);
 }
 if([].includes(version)){
  replace('ds[i],M.helpDefense(ds),tr(os)','ds[i],contestHelp(ds),tr(os)');
 }
 {
  replace('return fourthProbability(os[i],','const originalProbability=fourthProbability(os[i],');
  replace('},ds,opt);\n    };','},ds,opt); return spaceProbability(originalProbability,os[i],putback!==null,opt);\n    };');
  patches.push(`{const start=g.indexOf('    const foulInputs=Object.fromEntries(zones.map(z=>{'),end=g.indexOf('    // p.zone describes recorded FGA.',start);if(start<0||end<0)throw Error('Foul input anchor drift');g=g.slice(0,start)+'    const foulInputs=observedFoulInputs(p,ls[off][hi],opt,attemptMakeProbability);\\n'+g.slice(end);}`);
 }
 replace('const originalProbability=fourthProbability(os[i],','const originalProbability=terminalDefenseProbabilities(os[i],');
 patches.push(`g="import {terminalDefenseProbabilities} from '${url('reports/player-impact-v41/model.mjs')}';\\n"+g;`);
 patches.push(`g="import {measuredPutbackChoice} from '${url('reports/player-impact-v23/model.mjs')}';\\n"+g;`);
 patches.push(`g="import {spaceProbability} from '${url('reports/player-impact-v22/model.mjs')}';\\n"+g;`);
 // Source conditional probabilities replace the global touch scale and live split.
 replace('const originalLive=opt.liveSignal?opt.touchLiveShare:touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare);','const originalLive=opt.measuredTouchTurnovers?p.measuredTouchLiveShare:opt.liveSignal?opt.touchLiveShare:touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare);');
 replace('p.pTovTouch*(opt.turnoverCategories?opt.touchTurnoverScale:1)*touchMultiplier','p.pTovTouch*(opt.measuredTouchTurnovers?1:opt.turnoverCategories?opt.touchTurnoverScale:1)*touchMultiplier');
 replace('const counterfactual=best(hi,assist,true).pTovTouch;','const counterfactualProbability=best(hi,assist,true);const counterfactual=counterfactualProbability.pTovTouch;');
 replace('counterfactual*touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare)','counterfactual*(opt.measuredTouchTurnovers?counterfactualProbability.measuredTouchLiveShare:touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare))');
 replace("emit(made?'FGM':'FGX',off,shooter,{zone,points:made?points:0,assist:made&&usedAssist?passer:null,blocker});","emit(made?'FGM':'FGX',off,shooter,{zone,points:made?points:0,assist:made&&usedAssist?passer:null,blocker,putback:putback!==null,putbackPlayerId:ls[off][hi].playerId,makeProbability:p.make[zone]});");
 replace('putback:offensive && !freeThrow && rng()<M.putbackRate(ls[side][index],M.helpDefense(ds))?player:null','putback:offensive && !freeThrow && rng()<measuredPutbackChoice(ls[side][index])?player:null');
 // Keep the already verified conditional DREB/BLK allocation for candidates.
 // Control remains byte-for-byte comparable in all team/player counters.
 if(version!=='control'){
  replace("reboundWeights(ls[side],{zone,side:offensive?'offense':'defense',shooterIndex:offensive?slot:-1,freeThrow},opt)","(offensive?reboundWeights(ls[side],{zone,side:'offense',shooterIndex:slot,freeThrow},opt):measuredRecipientWeights(ls[side],'dreb'))");
  replace('blocker=D.lineup[pickWeighted(bp.weights,rng())]',"blocker=D.lineup[pickWeighted(measuredRecipientWeights(ls[1-off],'blk'),rng())]");
  patches.push(`g="import {recipientWeights as measuredRecipientWeights} from '${url('reports/player-impact-v24/model.mjs')}';\\n"+g;`);
 }
 replace('    if (opt.eventObserver) opt.eventObserver(',`    if(opt.onCourtObserver&&['FGM','FGX','GAME_END'].includes(type))opt.onCourtObserver({type,side,zone:extra.zone,playerId:player===null?null:sides[side].roster[player].playerId,assistPlayerId:extra.assist===null||extra.assist===undefined?null:sides[side].roster[extra.assist].playerId,teams:sides.map((s,i)=>({teamId:i?teamB.id:teamA.id,lineup:s.lineup.map(j=>s.roster[j].playerId),active:s.roster.filter(p=>!p.injured&&(p.targetMinutes??1)>0).map(p=>p.playerId)}))});\n    if (opt.eventObserver) opt.eventObserver(`);
 patches.push(`g="import {contactRecipientWeights,ordinaryContactProbability} from '${url('reports/player-impact-v26/model.mjs')}';\\n"+g;`);
 replace("if(intentional || rng()<opt.nonShootingFoulRate*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1)) {", "if(intentional || rng()<ordinaryContactProbability(ls[off],opt)*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1)) {\n      if(!intentional){hi=pickWeighted(contactRecipientWeights(ls[off],opt),rng());shooter=O.lineup[hi];}");
 replace('opt.eventObserver({type,period,clock:clock/10,off:side,player,...extra});','opt.eventObserver({type,period,clock:clock/10,off:side,player,playerId:player===null?null:sides[side].roster[player].playerId,...extra});');
 replace("emit('FOUL',side,defender,{kind,shooter,teamFouls:s.teamFouls});","emit('FOUL',side,defender,{kind,shooter,drawnPlayerId:sides[off].roster[shooter].playerId,teamFouls:s.teamFouls});");
 // Budget schedules can change the five during setup/pass/release. Rebuild
 // source-role transport for the current five, while preserving slot handoff.
 replace("const refresh=()=>{if(opt.minuteMode!=='budget')return;ls=lineups();shooter=O.lineup[hi];if(passer!==null&&!O.lineup.includes(passer)){passer=null;assist=null;usedAssist=false;}};", "const refresh=()=>{if(opt.minuteMode!=='budget')return;ls=lineups();creationPlan=putback===null?opportunityPlan(ls[off],probability,pressureSignal(ls[1-off],opt.stealPriorRate).relative,opt.creationPolicy):null;opt.sourcePlanObserver?.({lineup:ls[off].map(p=>p.playerId),plan:creationPlan,putback:putback!==null});shooter=O.lineup[hi];if(passer!==null&&!O.lineup.includes(passer)){passer=null;assist=null;usedAssist=false;}};");
 // Closed-horizon source rotation diagnostic; defaults retain exact v26 behavior.
 replace('const sides = [teamA,teamB].map(t => {','const sides = [teamA,teamB].map((t,sourceSide) => {');
 replace("budget:opt.minuteMode==='budget'?minuteBudgetSchedule(t.roster):null", "budget:opt.minuteMode==='budget'?(opt.sourceRotations?.[sourceSide]??minuteBudgetSchedule(t.roster)):null");
 replace("if(opt.minuteMode!=='budget'||elapsed>=28800)return;", "if(opt.minuteMode!=='budget'||elapsed>=(opt.sourcePeriods?(2880+Math.max(0,opt.sourcePeriods-4)*300)*10:28800))return;");
 replace("if(opt.minuteMode==='budget'&&period<=4){applyBudget();return;}", "if(opt.minuteMode==='budget'&&(period<=4||opt.sourceRotations)){applyBudget();return;}");
 replace('if(period>=4 && sides[0].stat.pts!==sides[1].stat.pts)break;', 'if(opt.sourcePeriods?period>=opt.sourcePeriods:period>=4&&sides[0].stat.pts!==sides[1].stat.pts)break;');
 if(memoized){
  if(!game)throw Error('Memoization only allowed for fixed-lineup game probes');
  replace('const probability = (i,a=null,forced=false) => {','const probability = (i,a=null,forced=false) => { const cacheKey=off+":"+i+":"+a+":"+forced+":"+(putback!==null); if(opt.ovrCache?.has(cacheKey))return opt.ovrCache.get(cacheKey);');

  replace('return spaceProbability(originalProbability,os[i],putback!==null,opt);','const cachedProbability=spaceProbability(originalProbability,os[i],putback!==null,opt); if(opt.ovrCache)opt.ovrCache.set(cacheKey,cachedProbability); return cachedProbability;');
  patches.push(`g=g.replaceAll('M.teammateContext(','cachedContext(');`);
  replace('const lineups = () => sides.map(s=>s.lineup.map(i=>opt.fatigue?M.applyStamina(s.roster[i],1-s.energy[i]):s.roster[i]));',`const fixedLineups=sides.map(s=>s.lineup.map(i=>s.roster[i]));
 const lineups=()=>fixedLineups;
 const contexts=fixedLineups.map(ls=>ls.map((_,i)=>M.teammateContext(ls,i)));
 const cachedContext=(ls,i)=>contexts[fixedLineups.indexOf(ls)][i];`);
 }
 patches.push(`g=g.replaceAll('M.teammateContext(', 'measuredContext(');g="import {measuredContext} from '${url('src/measured_creation_context.js')}';\\n"+g;`);
 source=source.replace("fs.readFileSync('src/defense_fourth_season.js','utf8')","teamClockSeasonSource().replace(\"'timingRawMeanSeconds'];\",\"'timingRawMeanSeconds','e069Ctl','e069Pass','e069Other','e069Touch'];\")");
 source="import {teamClockSeasonSource} from '"+url('reports/player-impact-team-clock/season-source.mjs')+"';\n"+source;
 replace("const player=O.lineup[0];record(off,player,'tov');record(off,player,'deadTov');record(off,player,'clockTov');emit('SHOT_CLOCK',off,player,{independent:true});","const player=null;record(off,player,'tov');record(off,player,'deadTov');record(off,player,'clockTov');emit('SHOT_CLOCK',off,player,{independent:true});");
 replace("record(off,shooter,'tov');record(off,shooter,'deadTov');record(off,shooter,'clockTov');emit('SHOT_CLOCK',off,shooter);","record(off,null,'tov');record(off,null,'deadTov');record(off,null,'clockTov');emit('SHOT_CLOCK',off,null);");

 replace("if(rng()<bp.conditionalOnMiss){blocker=D.lineup[pickWeighted(measuredRecipientWeights(ls[1-off],'blk'),rng())];record(1-off,blocker,'blk');}","const blockIndex=coupledBlockLabel(ls[1-off],{zone,legacyProbability:bp.conditionalOnMiss},rng);if(blockIndex>=0){blocker=D.lineup[blockIndex];record(1-off,blocker,'blk');}");
 patches.push(`g="import {coupledBlockLabel} from '${url('src/measured_block_events.js')}';\\n"+g;`);
 // ---- E-069 patches (all inert unless opt.e069 is set) ----
 replace("const KEYS = ['pts',","const KEYS = ['e069Ctl','e069Pass','e069Other','e069Touch','pts',");
 replace("emit('TOUCH',off,shooter,{strategy});","emit('TOUCH',off,shooter,{strategy});let holdStart=elapsed;");
 replace("record(off,passer,'passes');passesLeft--;","record(off,passer,'passes');passesLeft--;holdStart=elapsed;");
 replace("Math.min(.95,creationPlan.rows[hi].intercept*","Math.min(.95,(opt.e069?e069PassSegment(ls[off][hi],(elapsed-holdStart)/10,opt.e069):creationPlan.rows[hi].intercept)*");
 replace("record(off,shooter,'tov');record(off,shooter,'liveTov');record(1-off,interceptor,'stl');record(1-off,interceptor,'passSteals');","record(off,shooter,'tov');record(off,shooter,'liveTov');record(1-off,interceptor,'stl');record(1-off,interceptor,'passSteals');if(opt.e069)record(off,shooter,eventRng()<e069State.ctlShare?'e069Ctl':'e069Pass');");
 replace("Math.min(.95,p.pTovTouch*(opt.measuredTouchTurnovers?1:opt.turnoverCategories?opt.touchTurnoverScale:1)*touchMultiplier)","(record(off,shooter,'e069Touch'),opt.e069?e069Release(ls[off][hi],(elapsed-holdStart)/10,opt.e069):Math.min(.95,p.pTovTouch*(opt.measuredTouchTurnovers?1:opt.turnoverCategories?opt.touchTurnoverScale:1)*touchMultiplier))");
 replace("const live=opt.turnoverMode!=='legacy'&&eventRng()<originalLive*liveMultiplier/touchMultiplier;","const e069Other=opt.e069?eventRng()<e069State.otherShare:false;if(opt.e069)record(off,shooter,e069Other?'e069Other':'e069Ctl');const live=!e069Other&&opt.turnoverMode!=='legacy'&&eventRng()<originalLive*liveMultiplier/touchMultiplier;");
 replace("const kind=kinds[pickWeighted(opt.deadCategoryWeights,eventRng())];","const kind=opt.e069?(e069Other?kinds[pickWeighted(opt.deadCategoryWeights.slice(0,2),eventRng())]:kinds[3+pickWeighted(opt.deadCategoryWeights.slice(3),eventRng())]):kinds[pickWeighted(opt.deadCategoryWeights,eventRng())];");
 patches.push(`g="import {passSegmentProb as e069PassSegment,releaseProb as e069Release,state as e069State} from '${url('reports/handle-E069/sim/e069.mjs')}';\\n"+g;`);
 const anchor='  const gu=encode(g),s=';if(source.split(anchor).length!==2)throw Error('Adapter export anchor');
 source=source.replace(anchor,patches.join('\n')+'\n'+anchor);
 if(game)source=source.replace('cached=(await import(encode(s))).runDefenseSeason;return cached;','cached=(await import(gu)).simulateDefenseFourthGame;return cached;');
 const mod=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
 const run=await mod.experimentalSeason();cache.set(key,run);return run;
}
