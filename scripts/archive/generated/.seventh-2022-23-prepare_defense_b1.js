import fs from 'node:fs';
import {read,hash,table} from './defense_io.js';
import {reconstructLineups,normalizeRealGame,realFactorEvent,blankFactors,clockSeconds,varianceAnalysis} from '../src/defense_pbp_analysis.js';
const root='reports/defense-seventh/2022-23/stints';fs.mkdirSync(root,{recursive:true});
const manifest=read('data/defense-seventh/2022-23/manifest.json'),league=read('data/defense-seventh/2022-23/league.json'),exposure=read('data/defense-seventh/2022-23/game-exposure.json');
const fixtures=new Map(league.schedule.map(g=>[g.id,g])),boxes=new Map(exposure.games.map(g=>[g.id,g]));
const teamGames=table('data/defense-seventh/2022-23/team-games.json'),official=new Map(teamGames.map(t=>[t.GAME_ID+':'+t.TEAM_ID,t]));
const output=fs.openSync(root+'/real-games.jsonl','w'),stintFile=fs.openSync(root+'/stints.jsonl','w');
const games=[],failures=[],minuteChecks=[],players=new Map(),turnovers={},timing={made:[],dreb:[],turnover:[],retained:[],period:[]};
const totals=blankFactors(),eventDifferences=[],stintCountChecks=[];let validLineupGames=0,stintCount=0,validSeconds=0,totalSeconds=0;
const reboundClassification=(e,shot)=>{const ft=shot?.actionType==='freethrow',m=/(\d+) of (\d+)/.exec(shot?.subType??''),special=(shot?.qualifiers??[]).some(q=>/technical|flagrant|clearpath|awayfromplay|transitiontake/i.test(q));return {dead:ft&&(special||m&&m[1]!==m[2]),opportunity:+(shot?.shotResult==='Missed'&&(shot.isFieldGoal||ft&&m&&m[1]===m[2]&&!special))};};
for(const source of manifest.sources){
  if(hash(source.file)!==source.sha256)throw Error('Stale PBP '+source.id);
  const fixture=fixtures.get(source.id),box=boxes.get(source.id),actions=read(source.file).data.game.actions;
  const lineup=reconstructLineups(actions,box),game=normalizeRealGame(actions,fixture,lineup);
  games.push(game);fs.writeSync(output,JSON.stringify(game)+'\n');
  for(const [type,n] of Object.entries(game.turnoverTypes))turnovers[type]=(turnovers[type]??0)+n;
  for(const s of game.segments)if(s.duration>=0&&s.duration<=60)timing[s.state].push(s.duration);
  const periodTime=actions.filter(e=>e.actionType==='period'&&e.subType==='end').reduce((n,e)=>n+(e.period<=4?720:300),0);totalSeconds+=periodTime;
  const counts=new Map(box.teams.map(t=>[t.teamId,blankFactors()]));
  const shotMap=new Map(actions.map(e=>[e.actionNumber,e]));
  for(const e of actions){const row=counts.get(e.teamId);if(!row)continue;const c=realFactorEvent(e);
    if(e.actionType==='rebound'){const r=reboundClassification(e,shotMap.get(e.shotActionNumber));if(r.dead){c.deadFtReb=c.teamOreb;c.teamOreb=0;}c.reboundOpportunities=r.opportunity;}
    for(const k of Object.keys(c)){row[k]+=c[k];totals[k]+=c[k];}}
  for(const t of box.teams){const c=counts.get(t.teamId),o=official.get(source.id+':'+t.teamId);for(const [key,col] of [['fga','FGA'],['fgm','FGM'],['fta','FTA'],['ftm','FTM'],['tov','TOV'],['oreb','OREB'],['dreb','DREB'],['points','PTS']])if(c[key]!==o[col])eventDifferences.push({id:source.id,teamId:t.teamId,key,pbp:c[key],box:o[col]});}
  minuteChecks.push(...lineup.minuteChecks.map(p=>({id:source.id,...p})));
  if(!lineup.valid){failures.push({id:source.id,structurallyValid:lineup.structurallyValid,errors:lineup.errors,mismatches:lineup.mismatches});continue;}
  validLineupGames++;validSeconds+=periodTime;
  const factors=lineup.stints.map(s=>({...s,id:source.id,teams:lineup.ids.map((teamId,i)=>({teamId,players:s.lineups[i],opponent:blankFactors(),defensivePossessions:0,defensivePossessionEnds:0}))}));
  // Event counts use the actual lineup at the action, including FT substitutions.
  for(let index=0;index<actions.length;index++){
    const e=actions[index],stint=factors.find(s=>s.period===e.period&&index>=s.startIndex&&index<s.endIndex);if(!stint)continue;
    const c=realFactorEvent(e),side=lineup.ids.indexOf(e.teamId);if(side<0)continue;
    let defense=1-side;
    if(e.actionType==='rebound'){
      const r=reboundClassification(e,shotMap.get(e.shotActionNumber));
      if(r.dead){c.deadFtReb=c.teamOreb;c.teamOreb=0;}c.reboundOpportunities=r.opportunity;
      if(e.subType==='defensive')defense=side;
    }
    for(const k of Object.keys(c))stint.teams[defense].opponent[k]+=c[k];
  }
  for(const k of Object.keys(totals)){if(k==='possessions')continue;const expected=[...counts.values()].reduce((n,c)=>n+c[k],0),actual=factors.reduce((n,s)=>n+s.teams.reduce((v,t)=>v+t.opponent[k],0),0);if(actual!==expected)stintCountChecks.push({id:source.id,key:k,expected,actual});}
  for(const p of game.possessions){const defense=lineup.ids.indexOf(game.ids[1-p.side]);
    for(const stint of factors.filter(s=>s.period===p.period)){
      const overlap=Math.max(0,Math.min(stint.startClock,p.start)-Math.max(stint.endClock,p.end));
      const atEnd=p.endIndex>=stint.startIndex&&p.endIndex<stint.endIndex;
      stint.teams[defense].defensivePossessions+=p.duration>0?overlap/p.duration:+atEnd;
      stint.teams[defense].defensivePossessionEnds+=+atEnd;
    }
  }
  for(const stint of factors){stintCount++;fs.writeSync(stintFile,JSON.stringify(stint)+'\n');for(const t of stint.teams)for(const id of t.players){const key=t.teamId+':'+id;if(!players.has(key))players.set(key,{teamId:t.teamId,playerId:id,seconds:0,defensivePossessions:0,defensivePossessionEnds:0,games:new Set()});const p=players.get(key);p.seconds+=stint.seconds;p.defensivePossessions+=t.defensivePossessions;p.defensivePossessionEnds+=t.defensivePossessionEnds;p.games.add(source.id);}}
  if(games.length%200===0)console.log('PBP '+games.length+'/'+manifest.sources.length);
}
fs.closeSync(output);fs.closeSync(stintFile);
const quantile=(xs,p)=>{const a=xs.slice().sort((a,b)=>a-b);return a[Math.round((a.length-1)*p)]??null;};
const distribution=xs=>({n:xs.length,min:quantile(xs,0),p10:quantile(xs,.1),p25:quantile(xs,.25),median:quantile(xs,.5),p75:quantile(xs,.75),p90:quantile(xs,.9),max:quantile(xs,1)});
const playerRows=[...players.values()].map(p=>({...p,games:p.games.size}));
const names=new Map(league.teams.flatMap(t=>t.roster.map(p=>[p.playerId,p.name]))),individuals=new Map();for(const p of playerRows){p.name=names.get(p.playerId);if(!individuals.has(p.playerId))individuals.set(p.playerId,{playerId:p.playerId,name:p.name,seconds:0,defensivePossessions:0,defensivePossessionEnds:0});const r=individuals.get(p.playerId);for(const k of ['seconds','defensivePossessions','defensivePossessionEnds'])r[k]+=p[k];}
const totalTov=Object.values(turnovers).reduce((a,b)=>a+b,0);
const summary={schemaVersion:1,sourceGames:manifest.sources.length,missingPbp:manifest.failures,validLineupGames,failedLineupGames:failures.length,stintCount,validSeconds,totalSeconds,minuteToleranceSeconds:1.1,
  minuteErrors:distribution(minuteChecks.map(p=>Math.abs(p.errorSeconds))),failures,players:playerRows,individualPlayers:[...individuals.values()],defensiveSampleDistribution:distribution([...individuals.values()].map(p=>p.defensivePossessions)),teamStintSampleDistribution:distribution(playerRows.map(p=>p.defensivePossessions)),totals,stintCountChecks,
  turnoverTypes:Object.fromEntries(Object.entries(turnovers).map(([k,n])=>[k,{count:n,perTeamGame:n/(2*games.length),share:n/totalTov}])),clockViolationPerTeamGame:totals.clockTov/(2*games.length),liveTurnoverShare:totals.liveTov/totalTov,turnoversPerTeamGame:totalTov/(2*games.length),eventDifferences,
  possessionAnomalies:games.filter(g=>g.anomalies.length).map(g=>({id:g.id,anomalies:g.anomalies})),
  definitions:{lineups:'P1 uses official starters; subsequent period starters inferred from first on-court action / first substitution direction. No box-minute fit. Any ambiguity, illegal substitution or >1.1 sec individual error excludes entire game from stints.',possessions:'Made shot (plus and-one), final ordinary made FT, defensive rebound, turnover, recovered jump change or period end. OREB continues. Technical/retained FTs do not end. Signed points include opposing points. Regulation only for variance.',stintPossessions:'Fractional defensive possessions prorated by live game-clock overlap; also integer possession-end counts. Event factors assigned to actual lineup at event; no forced allocation to one lineup for whole possession.'},
  provenance:{sources:Object.fromEntries(['data/defense-seventh/2022-23/manifest.json','data/defense-seventh/2022-23/game-exposure.json','data/defense-seventh/2022-23/team-games.json','data/defense-seventh/2022-23/league.json'].map(f=>[f,hash(f)])),code:Object.fromEntries(['src/defense_pbp_analysis.js','scripts/prepare_defense_b1.js'].map(f=>[f,hash(f)]))}};
fs.writeFileSync(root+'/preparation.json',JSON.stringify(summary,null,2)+'\n');
fs.writeFileSync(root+'/empirical-timing.json',JSON.stringify({states:timing,summary:Object.fromEntries(Object.entries(timing).map(([k,a])=>[k,distribution(a)])),clockViolationPerTeamGame:summary.clockViolationPerTeamGame,clockViolationPerPossession:totals.clockTov/games.reduce((n,g)=>n+g.possessions.length,0),clockViolationPerEligiblePossession:totals.clockTov/games.reduce((n,g)=>n+g.possessions.filter(p=>p.start>24).length,0),provenance:summary.provenance},null,2)+'\n');
fs.writeFileSync(root+'/real-variance.json',JSON.stringify(varianceAnalysis(games),null,2)+'\n');
fs.writeFileSync(root+'/real-variance-strict.json',JSON.stringify(varianceAnalysis(games.filter(g=>g.anomalies.length===0&&g.possessions.every(p=>p.duration>=0))),null,2)+'\n');
fs.writeFileSync(root+'/minute-checks.jsonl',minuteChecks.map(p=>JSON.stringify(p)).join('\n')+'\n');
console.log(JSON.stringify({games:games.length,validLineupGames,failures:failures.length,stints:stintCount,clock:summary.clockViolationPerTeamGame,live:summary.liveTurnoverShare,turnovers:summary.turnoversPerTeamGame,differences:eventDifferences.length}));
