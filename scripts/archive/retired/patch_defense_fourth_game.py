from pathlib import Path
p=Path(__file__).resolve().parents[1]/'src/defense_fourth_game.js'
s=p.read_text(encoding='utf-8')
def change(a,b):
    global s
    assert a in s,a[:120]
    s=s.replace(a,b)
change("import * as M from './probability_model.js';","import * as M from './probability_model.js';\nimport {effect,shifted,fourthProbability,continuousDuration,starterTarget} from './defense_fourth_effects.js';")
change('const seconds=lo?a[Math.floor(empiricalRng()*lo)]/opt.pace:Math.max(.1,Math.min(clock,shotClock)/10-.1);','const seconds=opt.continuousTiming?continuousDuration(a,limit,empiricalRng)/opt.pace:lo?a[Math.floor(empiricalRng()*lo)]/opt.pace:Math.max(.1,Math.min(clock,shotClock)/10-.1);')
change('const eligible=s.roster.flatMap((p,i)=>!p.injured', '''const desired=opt.scoreRotation?starterTarget(period,clock/10,s.stat.pts-sides[1-side].stat.pts,opt.rotationCurve):null;
      const eligible=s.roster.flatMap((p,i)=>!p.injured''')
change('+(p.pos===s.roster[out].pos?8:0);','+(p.pos===s.roster[out].pos?8:0)\n            +(opt.scoreRotation&&i<5?60*(5*desired-s.lineup.filter(j=>j<5).length):0);')
change('const chance=freeThrow?', 'let chance=freeThrow?')
change('const offensive=rng()<chance, side=offensive?off:1-off;', '''if(opt.reboundSignal){
      // Replacement: keep the attacking rebound opportunity, neutralize old defensive skill.
      const neutral=ds.map(p=>({...p,rebound:70,physique:70}));
      const baseline=freeThrow?rate.playerOffShare:offensiveReboundProbability(os,neutral,{zone,shooterIndex:slot});
      chance=1-shifted(1-baseline,effect(ds,'DREB',opt));
    }
    const offensive=rng()<chance, side=offensive?off:1-off;''')
change("if(intentional || rng()<opt.nonShootingFoulRate)","if(intentional || rng()<opt.nonShootingFoulRate*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1))")
change('return defenseProbabilities(os[i]', 'return fourthProbability(os[i]')
change('pressureAttribute:pressureSignal(ds,opt.stealPriorRate).attribute,','pressureAttribute:opt.liveSignal?70:pressureSignal(ds,opt.stealPriorRate).attribute,')
change('contextLongScale:opt.contextLongScale,contextShortScale:opt.contextShortScale});','contextLongScale:opt.contextLongScale,contextShortScale:opt.contextShortScale},ds,opt);')
change("const pressureDefender=opt.turnoverMode==='pressure'?passPressureDefender(ls[1-off][hi],ls[1-off],opt.stealPriorRate):ls[1-off][hi];", "const pressureDefender=opt.liveSignal?{...ls[1-off][hi],onBall:70}:opt.turnoverMode==='pressure'?passPressureDefender(ls[1-off][hi],ls[1-off],opt.stealPriorRate):ls[1-off][hi];")
change('(opt.turnoverCategories?opt.passTurnoverScale:1)))','(opt.turnoverCategories?opt.passTurnoverScale:1)*(opt.liveSignal?Math.exp(effect(ls[1-off],\'liveTOV\',opt)):1)))')
change('const live=opt.turnoverMode', 'const live=opt.turnoverMode') if False else None
# Touch hazard: increase only the live component; leave calibrated dead hazard alone.
change('if(rng()<Math.min(.95,p.pTovTouch*(opt.turnoverCategories?opt.touchTurnoverScale:1))){', '''const originalLive=opt.liveSignal?opt.touchLiveShare:touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare);
    const liveMultiplier=opt.liveSignal?Math.exp(effect(ls[1-off],'liveTOV',opt)):1;
    const touchMultiplier=1-originalLive+originalLive*liveMultiplier;
    if(rng()<Math.min(.95,p.pTovTouch*(opt.turnoverCategories?opt.touchTurnoverScale:1)*touchMultiplier)){''')
change('touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare)', 'touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare)')
# Replace only the actual live classification, preserving clock counterfactual bookkeeping.
change("const live=opt.turnoverMode!=='legacy'&&eventRng()<touchStealProbability(ls[1-off],opt.stealPriorRate,opt.touchLiveShare);", "const live=opt.turnoverMode!=='legacy'&&eventRng()<originalLive*liveMultiplier/touchMultiplier;")
change('const scale=opt.foulOutcomes?Math.max(.25,Math.min(2.5,(profile??opt.leagueFTR)/opt.leagueFTR))*opt.foulScale:1;',"const scale=opt.foulOutcomes?Math.max(.25,Math.min(2.5,(profile??opt.leagueFTR)/(opt.relativeFouls?opt.foulProfileMeans[z]:opt.leagueFTR)))*opt.foulScale*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1):1;")
# FTA model is not identified at individual foul time: preserve attribution, change relative team hazard only.
p.write_text(s,encoding='utf-8')
