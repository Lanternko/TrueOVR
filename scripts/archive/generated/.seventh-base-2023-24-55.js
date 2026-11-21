import fs from 'node:fs';
import readline from 'node:readline';
import * as C from '../src/constants.js';
import {read as sourceRead,table as sourceTable,hash as sourceHash} from './defense_io.js';
const config=sourceRead("reports/defense-seventh/2023-24/calendar-55/config.json"),mapped=f=>config.paths[f]??f,read=f=>sourceRead(mapped(f)),table=f=>sourceTable(mapped(f)),hash=f=>sourceHash(mapped(f));
const cutoff=55;
const league=read('data/season-league.json'),signal=read('reports/defense-fifth/model-pre'+cutoff+'/engine-signals.json'),train=new Set(signal.trainGames),baseLogs=table('data/season-source/player-games.json'),teamLogs=table('data/season-source/team-games.json');
const keys=['MIN','PTS','FGM','FGA','FG3M','FG3A','FTM','FTA','OREB','DREB','REB','AST','TOV','STL','BLK','PF'],totals=new Map(),stints=new Map(),shots=new Map(),exposed=new Map();
const blank=()=>Object.fromEntries([...keys,'GP'].map(k=>[k,0])),add=(dest,row)=>{dest.GP++;for(const k of keys)dest[k]+=row[k]??0;};
for(const r of baseLogs)if(train.has(r.GAME_ID)){if(!totals.has(r.PLAYER_ID))totals.set(r.PLAYER_ID,blank());add(totals.get(r.PLAYER_ID),r);const key=r.TEAM_ID+'/'+r.PLAYER_ID;if(!stints.has(key))stints.set(key,blank());add(stints.get(key),r);}
const zones=e=>e.actionType==='3pt'?'long':e.area==='Mid-Range'?'mid':'short';
for(const source of read('data/defense-a-source/manifest.json').sources)if(train.has(source.id))for(const e of read(source.file).data.game.actions)if(e.isFieldGoal===1&&['2pt','3pt'].includes(e.actionType)){const s=shots.get(e.personId)??{longA:0,longM:0,midA:0,midM:0,shortA:0,shortM:0};s[zones(e)+'A']++;s[zones(e)+'M']+=e.shotResult==='Made';shots.set(e.personId,s);}
// Opportunity denominators measured from actual first-half on-court intervals.
for await(const line of readline.createInterface({input:fs.createReadStream(mapped('reports/defense-b1/stints.jsonl'))})){
  const s=JSON.parse(line);if(!train.has(s.id))continue;
  for(let side=0;side<2;side++){const own=s.teams[1-side].opponent,opp=s.teams[side].opponent;
    for(const p of s.teams[side].players){const e=exposed.get(p)??{reb:0,fgm:0};e.reb+=own.oreb+own.dreb+opp.oreb+opp.dreb;e.fgm+=own.fgm;exposed.set(p,e);}}
}
const sum=(rows,k)=>rows.reduce((n,r)=>n+(r[k]??0),0),rows=[...totals].map(([id,r])=>({id,...r}));
const shotRows=[...shots.values()],priors={long:sum(rows,'FG3M')/sum(rows,'FG3A'),ft:sum(rows,'FTM')/sum(rows,'FTA'),short:sum(shotRows,'shortM')/sum(shotRows,'shortA'),mid:sum(shotRows,'midM')/sum(shotRows,'midA')};
const pool=rows.filter(r=>r.GP>=15&&r.MIN/r.GP>=20),pct=(x,a)=>100*(a.filter(v=>v<x).length+.5*a.filter(v=>v===x).length)/(a.length||1),attr=p=>Math.max(40,Math.min(99,p<50?40+(p-1)*30/49:70+(p-50)*29/49));
const safe=(a,b)=>b>0?a/b:0,rank=(r,f)=>attr(pct(f(r),pool.map(f)));
function inverse(p,curve){for(let i=1;i<curve.length;i++){const [a,b]=curve[i-1],[c,d]=curve[i];if(p>=Math.min(b,d)&&p<=Math.max(b,d))return Math.max(40,Math.min(99,a+(p-b)/(d-b)*(c-a)));}return Math.abs(p-curve[0][1])<Math.abs(p-curve.at(-1)[1])?40:99;}
const tracking=new Map();for(const s of read((cutoff===41?'data/defense-third-source/manifest.json':'data/defense-fifth-source/pre'+cutoff+'/manifest.json')).sources)for(const r of table(s.file)){const n=r[s.zone==='long'?'FG3A':'FGA_LT_06']??0;tracking.set(s.teamId+'/'+r.CLOSE_DEF_PERSON_ID+'/'+s.zone,n?inverse(r.PLUSMINUS*n/(n+200),s.zone==='long'?C.CURVE_DEF_3PT:C.CURVE_DEF_RIM):70);}
const measured=structuredClone(league);let unseen=0;
for(const t of measured.teams)for(const p of t.roster){const b=totals.get(p.playerId),r=stints.get(t.id+'/'+p.playerId),s=shots.get(p.playerId)??{},e=exposed.get(p.playerId);
  p.onBall=tracking.get(t.id+'/'+p.playerId+'/long')??70;p.help=tracking.get(t.id+'/'+p.playerId+'/short')??70;
  const available=r??b;
  p.observed=r??blank();p.seasonMinutesPerGame=available?Math.max(.01,available.MIN/available.GP):sum(rows,'MIN')/sum(rows,'GP');
  const shoot=(m,n,mean,curve)=>inverse(((m??0)+100*mean)/((n??0)+100),curve);
  p.long=shoot(b?.FG3M,b?.FG3A,priors.long,C.CURVE_3PT);p.mid=shoot(s.midM,s.midA,priors.mid,C.CURVE_MID);p.short=shoot(s.shortM,s.shortA,priors.short,C.CURVE_SHORT);p.ft=shoot(b?.FTM,b?.FTA,priors.ft,C.CURVE_FT);
  p.drive=b?rank({...b,id:p.playerId},r=>safe(r.FTA,r.FGA)):70;p.tovSkill=b?rank({...b,id:p.playerId},r=>-safe(r.TOV,r.FGA+.44*r.FTA+r.AST+r.TOV)):70;
  p.pass=b?rank({...b,id:p.playerId},r=>safe(r.AST,Math.max(1,(exposed.get(r.id)?.fgm??0)-r.FGM))):70;
  p.rebound=b?rank({...b,id:p.playerId},r=>safe(r.REB,exposed.get(r.id)?.reb??0)):70;p.stamina=b?rank({...b,id:p.playerId},r=>safe(r.MIN,r.GP)):70;
  p.shotProfile={threeRate:available?.FGA?safe(available.FG3A,available.FGA):sum(rows,'FG3A')/sum(rows,'FGA'),freeThrowsPerAttempt:available?.FGA?safe(available.FTA,available.FGA):sum(rows,'FTA')/sum(rows,'FGA'),sourceSeason:'2025-26 first41 strictly disjoint training games'};
  p.defenseMeasurement={steals:b?.STL??0,minutes:b?.MIN??0};p.offenseMeasurement={attempts:available?.FGA??sum(rows,'FGA')/sum(rows,'MIN'),freeThrows:available?.FTA??sum(rows,'FTA')/sum(rows,'MIN'),turnovers:available?.TOV??sum(rows,'TOV')/sum(rows,'MIN'),minutes:available?.MIN||1};
  // Body dimensions and position are metadata. Absent training players get population skill priors.
  if(!b)unseen++;
}
measured.priorRate=sum(rows,'STL')/sum(rows,'MIN');
measured.fourthProvenance={trainingGames:[...train],unseenInstances:unseen,method:'All variable attack/defense/minute card inputs rebuilt from strictly disjoint574 first41 games. Shooting inverse curves/shrinkage unchanged. AST and REB percentile opportunity rates reconstructed from strict on-court stint counters (not full-season official advanced percentages). Official post41 availability and starters conditional inputs; post41 observed minute targets replaced with training in-team MPG, falling back to player training MPG at another team, then league training MPG. Unknown player skills/usage use population priors. Static body/position metadata retained.',sources:Object.fromEntries(['reports/defense-fifth/model-pre'+cutoff+'/engine-signals.json','data/season-source/player-games.json','reports/defense-b1/stints.jsonl',(cutoff===41?'data/defense-third-source/manifest.json':'data/defense-fifth-source/pre'+cutoff+'/manifest.json')].map(f=>[f,hash(f)]))};
measured.fourthProvenance.method=`Attack/defense/minute inputs from ${train.size} strictly disjoint pre${cutoff} games; cutoff-specific official tracking, conditional later active players/starters, training MPG and population priors. No later observed minute targets.`;
measured.fifthProvenance={cutoff,trainingGames:[...train],sources:measured.fourthProvenance.sources};
fs.writeFileSync(config.leagueOutput,JSON.stringify(measured)+'\n');
const means={},sums={};for(const t of measured.teams)for(const p of t.roster){const s=shots.get(p.playerId);if(!s)continue;for(const z of ['long','mid','short']){const a=sums[z]??=[0,0],n=s[z+'A'];a[0]+=n*p.shotProfile.freeThrowsPerAttempt;a[1]+=n;}}
means['pre'+cutoff]=Object.fromEntries(Object.entries(sums).map(([z,a])=>[z,a[0]/a[1]]));fs.writeFileSync(config.foulMeansOutput,JSON.stringify(means,null,2)+'\n');
console.log(JSON.stringify({trainingGames:train.size,unseen,priors,priorRate:measured.priorRate}));
