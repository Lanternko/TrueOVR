import fs from 'node:fs';
import crypto from 'node:crypto';
import * as C from '../src/constants.js';
import {validateSeason} from '../src/season_simulation.js';

const sources=[];
function read(file, setName) {
  const bytes=fs.readFileSync(new URL('../data/'+file,import.meta.url));
  const doc=JSON.parse(bytes);
  if (doc.season!=='2025-26') throw new Error('Mixed season: '+file);
  sources.push({file,url:doc.url,fetchedAt:doc.fetchedAt,sha256:crypto.createHash('sha256').update(bytes).digest('hex')});
  const set=setName?doc.data.resultSets.find(s=>s.name===setName):Array.isArray(doc.data.resultSets)?doc.data.resultSets[0]:doc.data.resultSets;
  if (file.endsWith('/shots.json')) return set.rowSet.map(r=>({PLAYER_ID:r[0],shortM:r[6]+r[9],shortA:r[7]+r[10],midM:r[12],midA:r[13]}));
  if (!set.headers.every(h=>typeof h==='string')) throw new Error('Unsupported source headers: '+file);
  return set.rowSet.map(row=>Object.fromEntries(set.headers.map((h,i)=>[h,row[i]])));
}
const benchmark=name=>read('benchmark-source/'+name+'.json');
const teamRows=benchmark('teams'), base=benchmark('base');
const maps=Object.fromEntries(['advanced','bio','shots','defense-long','defense-rim'].map(k=>[k,
  new Map(benchmark(k).map(r=>[r.PLAYER_ID??r.CLOSE_DEF_PERSON_ID,r]))]));
const bases=new Map(base.map(r=>[r.PLAYER_ID,r]));
const pool=base.filter(r=>r.GP>=30&&r.MIN/r.GP>=20);
const safe=(a,b)=>b>0?a/b:0;
const total=(rows,key)=>rows.reduce((n,r)=>n+(r[key]??0),0);
const prior={long:safe(total(base,'FG3M'),total(base,'FG3A')),ft:safe(total(base,'FTM'),total(base,'FTA')),
  mid:safe(total([...maps.shots.values()],'midM'),total([...maps.shots.values()],'midA')),
  short:safe(total([...maps.shots.values()],'shortM'),total([...maps.shots.values()],'shortA'))};
const percentile=(x,values)=>100*(values.filter(v=>v<x).length+.5*values.filter(v=>v===x).length)/values.length;
const attr=p=>Math.max(40,Math.min(99,p<50?40+(p-1)*30/49:70+(p-50)*29/49));
const rank=(r,f)=>attr(percentile(f(r),pool.map(f)));
// --shrink: empirical-Bayes pseudo-minutes toward the card-position mean before the percentile map
// (reports/ovr-shrinkage-2025-26/preregistration.md). Writes season-league-shrunk.json instead.
const SHRINK=process.argv.includes('--shrink'), shrinkage={};
const posOfHeight=h=>h<=75?'PG':h<=78?'SG':h<=80?'SF':h<=82?'PF':'C';
const posOf=r=>posOfHeight(Number(maps.bio.get(r.PLAYER_ID)?.PLAYER_HEIGHT_INCHES));
// --shooting-eb (v54): reliability-aware shrinkage for long/short attempt accuracy only. Replaces the
// fixed 100-attempt pseudo-count with k_z from method-of-moments on Var(p_i) = tau^2 + pbar(1-pbar)/n_i,
// fit on players with attempts>=20; prior mean is the attempt-weighted rate by card position (posOfHeight).
// mid and ft keep the original fixed-100 shrinkage. Writes season-league-v54.json instead.
const SHOOTING_EB=process.argv.includes('--shooting-eb'), shootingEB={};
function fitShootingEB(name,rows) {
  const qualified=rows.filter(r=>r.attempts>=20);
  const pbar=qualified.reduce((n,r)=>n+r.makes,0)/total(qualified,'attempts');
  const rates=qualified.map(r=>r.makes/r.attempts);
  const meanRate=rates.reduce((n,r)=>n+r,0)/rates.length;
  const varRate=rates.reduce((n,r)=>n+(r-meanRate)**2,0)/rates.length;
  const meanInvN=qualified.reduce((n,r)=>n+1/r.attempts,0)/qualified.length;
  const tau2=varRate-pbar*(1-pbar)*meanInvN;
  const k=tau2>0?Math.max(50,Math.min(2000,pbar*(1-pbar)/tau2-1)):500;
  const byPos=Map.groupBy(rows,r=>posOfHeight(Number(maps.bio.get(r.playerId)?.PLAYER_HEIGHT_INCHES)));
  const positionMeans=Object.fromEntries([...byPos].map(([pos,g])=>[pos,total(g,'makes')/total(g,'attempts')]));
  shootingEB[name]={k,tau2,pbar,qualifiedPlayers:qualified.length,totalPlayers:rows.length,positionMeans};
  return (makes,attempts,pos)=>(makes+k*(positionMeans[pos]??pbar))/(attempts+k);
}
const ebLong=SHOOTING_EB?fitShootingEB('long',base.filter(r=>r.FG3A>0).map(r=>({playerId:r.PLAYER_ID,makes:r.FG3M,attempts:r.FG3A}))):null;
const ebShort=SHOOTING_EB?fitShootingEB('short',[...maps.shots.values()].filter(r=>r.shortA>0).map(r=>({playerId:r.PLAYER_ID,makes:r.shortM,attempts:r.shortA}))):null;
// --attr-deflate (v55 direction 2, reports/ovr-v55-attr-deflate-2025-26/): long only, decoupled from
// short. Diagnosis (see report): the v54 SHOOTING_EB joint long+short shrinkage legitimately pulls down
// catch-and-shoot big men's inflated 3PT rate (position-conditioned prior correctly lower for C/PF), but
// applied to short it pushes every elite rim-runner toward the 99 ceiling without separating fed-dependent
// finishers from genuinely good ones (both groups already near-ceiling under the fixed-100 global shrink,
// and a self-vs-fed rim FG% split does not transfer losslessly into one scalar attribute). Short/mid/ft keep
// the existing fixed-100 global-prior shrinkage; only long gets the reliability-fit, position-conditioned
// prior. Writes reports/ovr-v55-attr-deflate-2025-26/season-league-D.json instead of data/season-league.json.
const ATTR_DEFLATE=process.argv.includes('--attr-deflate');
const ebLongDeflate=ATTR_DEFLATE?fitShootingEB('long-deflate',base.filter(r=>r.FG3A>0).map(r=>({playerId:r.PLAYER_ID,makes:r.FG3M,attempts:r.FG3A}))):null;
function shrunk(name,f) {
  if (!SHRINK) return f;
  const rows=base.filter(r=>r.MIN>0&&Number.isFinite(f(r)));
  const mu=new Map([...Map.groupBy(rows,posOf)].map(([p,g])=>[p,g.reduce((n,r)=>n+r.MIN*f(r),0)/total(g,'MIN')]));
  const fit=rows.filter(r=>r.MIN>=50).map(r=>[1/r.MIN,(f(r)-mu.get(posOf(r)))**2]);
  const mean=i=>fit.reduce((n,v)=>n+v[i],0)/fit.length, mu_u=mean(0), mu_d=mean(1);
  const sigma2=fit.reduce((n,[u,d])=>n+(u-mu_u)*(d-mu_d),0)/fit.reduce((n,[u])=>n+(u-mu_u)**2,0);
  const tau2=mu_d-sigma2*mu_u;
  const k=tau2>0&&sigma2>0?Math.max(50,Math.min(2000,sigma2/tau2)):500;
  shrinkage[name]={pseudoMinutes:k,tau2,sigma2,fitPlayers:fit.length,positionMeans:Object.fromEntries(mu)};
  const value=new Map(base.map(r=>[r.PLAYER_ID,r.MIN>0&&Number.isFinite(f(r))?(r.MIN*f(r)+k*mu.get(posOf(r)))/(r.MIN+k):mu.get(posOf(r))]));
  return r=>value.get(r.PLAYER_ID);
}
const driveRate=shrunk('drive',r=>safe(r.FTA,r.FGA));
const tovRate=shrunk('tovSkill',r=>-safe(r.TOV,r.FGA+.44*r.FTA+r.AST+r.TOV));
const astPct=shrunk('pass',r=>maps.advanced.get(r.PLAYER_ID)?.AST_PCT);
const rebPct=shrunk('rebound',r=>maps.advanced.get(r.PLAYER_ID)?.REB_PCT);
const sizeValue=r=>{const v=maps.bio.get(r.PLAYER_ID);return Number(v.PLAYER_HEIGHT_INCHES)+Number(v.PLAYER_WEIGHT)/10;};
const sizePool=pool.filter(r=>Number(maps.bio.get(r.PLAYER_ID).PLAYER_WEIGHT)>0);
function inverse(p,curve) {
  if (!Number.isFinite(p)) throw new Error('Nonfinite probability passed to inverse curve');
  for (let i=1;i<curve.length;i++) {
    const [x0,y0]=curve[i-1],[x1,y1]=curve[i];
    if (p>=Math.min(y0,y1)&&p<=Math.max(y0,y1)) return Math.max(40,Math.min(99,x0+(p-y0)/(y1-y0)*(x1-x0)));
  }
  return Math.abs(p-curve[0][1])<Math.abs(p-curve.at(-1)[1])?40:99;
}
const easternIds=new Set([1610612737,1610612738,1610612739,1610612741,1610612748,1610612749,
  1610612751,1610612752,1610612753,1610612754,1610612755,1610612761,1610612764,1610612765,1610612766]);
function card(row) {
  const b=bases.get(row.PLAYER_ID),bio=maps.bio.get(row.PLAYER_ID),a=maps.advanced.get(row.PLAYER_ID),shot=maps.shots.get(row.PLAYER_ID);
  if (!b||!bio||!a) throw new Error('Missing core source: '+row.PLAYER_ID);
  const missing=[];
  const defense=(kind,curve)=>{
    const d=maps[kind].get(row.PLAYER_ID);
    const attempts=d?.D_FGA??d?.[kind==='defense-long'?'FG3A':'FGA_LT_06'];
    const difference=d?.PCT_PLUSMINUS??d?.PLUSMINUS;
    if (!d||!(attempts>0)||!Number.isFinite(difference)) {missing.push(kind);return 70;}
    return inverse(difference*attempts/(attempts+200),curve);
  };
  const shooting=(makes,attempts,mean,curve)=>inverse((makes+100*mean)/(attempts+100),curve);
  if (!shot) missing.push('shot-locations');
  const height=Number(bio.PLAYER_HEIGHT_INCHES),weight=Number(bio.PLAYER_WEIGHT);
  if (!(height>0)) throw new Error('Missing measured height: '+row.PLAYER_ID);
  if (!(weight>0)) missing.push('body-weight');
  const pos=posOfHeight(height);
  return {playerId:row.PLAYER_ID,name:row.PLAYER_NAME,pos,courtPosition:pos,heightInches:height,
    long:ATTR_DEFLATE?inverse(ebLongDeflate(b.FG3M,b.FG3A,pos),C.CURVE_3PT):SHOOTING_EB?inverse(ebLong(b.FG3M,b.FG3A,pos),C.CURVE_3PT):shooting(b.FG3M,b.FG3A,prior.long,C.CURVE_3PT),
    mid:shooting(shot?.midM??0,shot?.midA??0,prior.mid,C.CURVE_MID),
    short:SHOOTING_EB?inverse(ebShort(shot?.shortM??0,shot?.shortA??0,pos),C.CURVE_SHORT):shooting(shot?.shortM??0,shot?.shortA??0,prior.short,C.CURVE_SHORT),
    ft:shooting(b.FTM,b.FTA,prior.ft,C.CURVE_FT),
    drive:rank(b,driveRate),tovSkill:rank(b,tovRate),pass:rank(b,astPct),rebound:rank(b,rebPct),
    stamina:rank(b,r=>safe(r.MIN,r.GP)),
    physique:weight>0?attr(percentile(sizeValue(b),sizePool.map(sizeValue))):70,
    onBall:defense('defense-long',C.CURVE_DEF_3PT),help:defense('defense-rim',C.CURVE_DEF_RIM),
    offBall:70,screen:70,handle:70,breakDbl:70,
    ...(row.FGA>0?{shotProfile:{threeRate:row.FG3A/row.FGA,freeThrowsPerAttempt:row.FTA/row.FGA,sourceSeason:'2025-26'}}:{}),
    seasonMinutesPerGame:Math.max(.01,safe(row.MIN,row.GP)),
    observed:Object.fromEntries(['GP','MIN','PTS','FGM','FGA','FG3M','FG3A','FTM','FTA','OREB','DREB','REB','AST','TOV','STL','BLK','PF'].map(k=>[k,row[k]])),
    missingMeasurements:missing};
}
const teams=teamRows.sort((a,b)=>a.TEAM_ID-b.TEAM_ID).map(t=>{
  const rows=benchmark('team-'+t.TEAM_ID).sort((a,b)=>b.MIN-a.MIN||a.PLAYER_ID-b.PLAYER_ID);
  return {id:t.TEAM_ID,name:t.TEAM_NAME,conference:easternIds.has(t.TEAM_ID)?'East':'West',season:'2025-26',
    observed:Object.fromEntries(['GP','W','L','PTS','PLUS_MINUS','FGM','FGA','FG3M','FG3A','FTM','FTA','REB','AST','TOV'].map(k=>[k,t[k]])),roster:rows.map(card)};
});
const teamLogs=read('season-source/team-games.json'),playerLogs=read('season-source/player-games.json');
const appearances=Map.groupBy(playerLogs,r=>r.GAME_ID+'/'+r.TEAM_ID);
const schedule=[...Map.groupBy(teamLogs,r=>r.GAME_ID)].map(([id,rows])=>{
  if (rows.length!==2) throw new Error('Unpaired game: '+id);
  let home=rows.find(r=>r.MATCHUP.includes(' vs. ')),away=rows.find(r=>r.MATCHUP.includes(' @ '));
  const neutral=!home;
  let sideAssignment='official matchup';
  if (neutral) {
    const summary=read('season-source/game-summary-'+id+'.json','GameSummary')[0];
    if (summary.GAME_ID!==id) throw new Error('Wrong neutral summary: '+id);
    if (summary.HOME_TEAM_ID&&summary.VISITOR_TEAM_ID) {
      home=rows.find(r=>r.TEAM_ID===summary.HOME_TEAM_ID);away=rows.find(r=>r.TEAM_ID===summary.VISITOR_TEAM_ID);
      sideAssignment='official summary; physically neutral';
    } else {
      [home,away]=[...rows].sort((a,b)=>a.TEAM_ID-b.TEAM_ID);
      sideAssignment='neutral A/B ordered by team ID; NBA summary has no home designation';
    }
  }
  if (!home||!away||home.GAME_DATE!==away.GAME_DATE||home.TEAM_ID===away.TEAM_ID) throw new Error('Invalid home/away: '+id);
  if ((home.WL==='W')!==(home.PTS>away.PTS)||home.PTS===away.PTS||home.WL===away.WL) throw new Error('Invalid observed result: '+id);
  return {id,date:home.GAME_DATE,homeId:home.TEAM_ID,awayId:away.TEAM_ID,neutral,sideAssignment,
    homePlayerIds:(appearances.get(id+'/'+home.TEAM_ID)??[]).map(p=>p.PLAYER_ID).sort((a,b)=>a-b),
    awayPlayerIds:(appearances.get(id+'/'+away.TEAM_ID)??[]).map(p=>p.PLAYER_ID).sort((a,b)=>a-b),
    observed:{homeScore:home.PTS,awayScore:away.PTS}};
}).sort((a,b)=>a.date.localeCompare(b.date)||a.id.localeCompare(b.id));
for (const team of teams) {
  team.locationExposure={home:schedule.filter(g=>!g.neutral&&g.homeId===team.id).length,
    away:schedule.filter(g=>!g.neutral&&g.awayId===team.id).length,
    neutral:schedule.filter(g=>g.neutral&&(g.homeId===team.id||g.awayId===team.id)).length};
  const logs=teamLogs.filter(r=>r.TEAM_ID===team.id);
  if (logs.length!==team.observed.GP||logs.filter(r=>r.WL==='W').length!==team.observed.W||total(logs,'PTS')!==team.observed.PTS) {
    throw new Error('Season snapshots and game logs disagree: '+team.name);
  }
  for (const player of team.roster) {
    const logs=playerLogs.filter(r=>r.TEAM_ID===team.id&&r.PLAYER_ID===player.playerId);
    if (logs.length!==player.observed.GP||total(logs,'PTS')!==player.observed.PTS) throw new Error('Player snapshots and game logs disagree: '+player.name);
  }
}
const league={schemaVersion:1,season:'2025-26',sources,priors:prior,methodology:{
  scope:'Retrospective conditional regular-season simulation, not a preseason forecast or independent accuracy validation.',
  roster:'All observed season-in-team player stints. Game pools use observed appearances; unused DNP reserves are not known.',
  ability:'Full-season league player totals, including traded stints; inverse accuracy curves with 100-attempt shrinkage. Other measured attributes use GP>=30 / MPG>=20 percentiles.',
  defense:'Tracked percentage difference shrunk by D_FGA/(D_FGA+200); missing tracking explicitly falls back to neutral 70.',
  physique:'Height plus weight/10 ranked among measured rotation players; missing weight uses neutral physique 70 and is flagged.',
  unknown:'offBall, screen, handle and breakDbl are neutral 70 for every player.',
  minutes:'Season-in-team MPG, renormalized among each game pool to 240 and capped at 48. Observed game minutes are not supplied to the engine.',
  roles:'Top five rotation targets start, assigned PG/SG/SF/PF/C by height; bench roles use height bands. Not official starting lineups or positions.',
  schedule:'Observed regular-season games only, 1,230 unique 00225 IDs; NBA Cup championship/play-in/playoffs excluded.',
  neutral:'Five games have both teams marked away. Official summary supplies designated sides when available; otherwise team ID orders neutral A/B. Neutral games are counted separately, never forced into 41 home / 41 away.',
  outcome:'Observed scores, wins and margins are stored for comparison only; none are inputs to basketball probabilities.',
  ...(SHRINK?{shrinkage:{rule:'x = (MIN*x + k*positionMean)/(MIN + k) before the percentile map; k = sigma2/tau2 by method of moments, clamped 50-2000.',stats:shrinkage}}:{}),
  ...(SHOOTING_EB?{shootingReliability:{rule:'long/short only: shrunk rate = (makes + k_z*positionMean)/(attempts + k_z), then the same inverse accuracy curve. k_z = pbar(1-pbar)/tau2 - 1 by method of moments on Var(p_i)=tau2+pbar(1-pbar)/n_i, fit on attempts>=20, clamped 50-2000 (k=500 if tau2<=0). positionMean is the attempt-weighted raw rate by posOfHeight. mid and ft unchanged (fixed 100-attempt pseudo-count).',zones:shootingEB}}:{}),
  ...(ATTR_DEFLATE?{attrDeflate:{rule:'v55 direction 2 (reports/ovr-v55-attr-deflate-2025-26/): long only, same reliability-fit position-conditioned shrinkage as --shooting-eb (k_z = pbar(1-pbar)/tau2 - 1 by method of moments, fit on attempts>=20, clamped 50-2000). short/mid/ft keep the default fixed-100 global-prior shrinkage, decoupled from long. Diagnosis: short is already near the 99 ceiling for every elite rim finisher regardless of fed-shot dependence, so shrinking it (jointly, as --shooting-eb does) does not separate fed-dependent box-score inflation from genuinely earned value; long cleanly does (see report.md).',zones:{long:shootingEB['long-deflate']}}}:{})},teams,schedule};
const validation=validateSeason(league);
const outPath=ATTR_DEFLATE?'../reports/ovr-v55-attr-deflate-2025-26/season-league-D.json':SHOOTING_EB?'../data/season-league-v54.json':SHRINK?'../data/season-league-shrunk.json':'../data/season-league.json';
if (ATTR_DEFLATE) fs.mkdirSync(new URL('../reports/ovr-v55-attr-deflate-2025-26/',import.meta.url),{recursive:true});
fs.writeFileSync(new URL(outPath,import.meta.url),JSON.stringify(league,null,2)+'\n');
console.log(JSON.stringify({...validation,sources:sources.length,missingMeasurementCards:teams.flatMap(t=>t.roster).filter(p=>p.missingMeasurements.length).length}));
