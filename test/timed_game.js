import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { simulateGame, monteCarlo } from '../src/simulation_engine.js';
import { inPenalty, clockStrategy } from '../src/timed_game.js';
import { BASELINE, TEAMS } from '../src/teams.js';

const sum = xs=>xs.reduce((a,b)=>a+b,0);
const near = (a,b)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`);
const team={name:'Synthetic ten-player fixture',roster:Array.from({length:10},(_,i)=>({
  ...BASELINE.roster[i%5],name:`Fixture ${i}`,targetMinutes:i<5?30:18 }))};
const before=JSON.stringify(team);
const types=new Set();
let rotations=0, andOnes=0, threeFouls=0, ftRebounds=0;
for(let seed=1;seed<=60;seed++) {
  const opts={mode:'timed',seed,replay:true};
  const g=simulateGame(team,team,opts);
  assert.equal(g.complete,true);
  assert.equal(g.tie,false);
  assert.equal(g.gameSeconds,2880+g.overtimes*300);
  assert.equal(g.periodScores[0].length,g.periods);
  assert.equal(sum(g.periodScores[0]),g.scoreA);assert.equal(sum(g.periodScores[1]),g.scoreB);
  for(const [s,rows] of [[g.statA,g.playersA],[g.statB,g.playersB]]) {
    near(s.seconds,5*g.gameSeconds);near(sum(rows.map(p=>p.seconds)),s.seconds);
    assert.ok(rows.slice(5).some(p=>p.seconds>0),'bench must play');
    assert.equal(s.pts,2*s.fgm+s.fg3m+s.ftm);
    for(const k of ['pts','fga','fgm','fg3a','fg3m','fta','ftm','oreb','dreb','ast','stl','blk','tov','pf','passes'])assert.equal(sum(rows.map(p=>p[k])),s[k]);
    for(const p of rows){assert.ok(p.fgm<=p.fga);assert.ok(p.fg3m<=p.fg3a);assert.ok(p.ftm<=p.fta);assert.ok(p.seconds<=g.gameSeconds);}
    assert.ok(s.ast<=s.fgm);
  }
  let previous=0;
  const onCourtSeconds=team.roster.map(()=>0);
  const fouledOut=[new Set(),new Set()];
  for(let i=0;i<g.events.length;i++) {
    const e=g.events[i],prior=g.events[i-1];types.add(e.type);
    assert.ok(e.elapsed>=previous);previous=e.elapsed;
    assert.ok(e.clock>=0 && e.shotClock>=0 && e.shotClock<=24);
    if(prior)for(const p of prior.lineups[0])onCourtSeconds[p]+=e.elapsed-prior.elapsed;
    for(const row of e.lineups)assert.equal(new Set(row).size,5);
    if(e.type==='SUBSTITUTION') { rotations++;assert.ok(!e.lineups[e.off].includes(e.out)); if(e.forced)fouledOut[e.off].add(e.out); }
    if(['FGM','FGX','PASS','TOUCH'].includes(e.type))assert.ok(!fouledOut[e.off].has(e.player),'disqualified player returned');
    if(e.type==='FOUL' && e.kind==='andOne')andOnes++;
    if(['FTM','FTX'].includes(e.type)) {
      if(e.attempts===3)threeFouls++;
      if(prior)assert.equal(e.elapsed,prior.elapsed,'free throws must stop clock');
    }
    if(e.type==='OREB')assert.equal(e.shotClock,14);
    if((e.type==='OREB'||e.type==='DREB')&&e.freeThrow)ftRebounds++;
    if(e.type==='FGM'&&e.assist!==null) {
      assert.notEqual(e.assist,e.player);
      const pass=g.events.slice(0,i).findLast(x=>x.type==='PASS'&&x.poss===e.poss);
      assert.ok(pass);assert.equal(pass.from,e.assist);assert.equal(pass.player,e.player);
    }
    if(e.type==='FGM'||e.type==='FGX') {
      const touch=g.events.slice(0,i).findLast(x=>x.type==='TOUCH');
      assert.ok(e.elapsed>touch.elapsed,'a new shot must consume positive time');
    }
  }
  g.playersA.forEach((p,i)=>near(p.seconds,onCourtSeconds[i]));
  assert.deepEqual(g.events.at(-1).score,[g.scoreA,g.scoreB]);
  if(seed===1) {
    const {events,...plain}=g;
    assert.deepEqual(simulateGame(team,team,{...opts,replay:false}),plain,'recording must not affect outcome');
    assert.deepEqual(simulateGame(team,team,opts),g,'seed must reproduce full game');
  }
}
assert.equal(JSON.stringify(team),before,'input teams must not mutate');
assert.ok(rotations>0&&andOnes>0&&threeFouls>0&&ftRebounds>0);
for(const type of ['SHOT_CLOCK','PASS','SUBSTITUTION','OREB','DREB','STEAL'])assert.ok(types.has(type),type);
assert.equal(inPenalty(1,4,1),false);assert.equal(inPenalty(1,5,0),true);
assert.equal(inPenalty(5,3,1),false);assert.equal(inPenalty(5,4,0),true);
assert.equal(inPenalty(1,2,2),true,'second foul in last two minutes triggers penalty');
assert.equal(clockStrategy(4,20,2),'runClock');assert.equal(clockStrategy(4,80,-4),'hurry');
assert.equal(clockStrategy(3,20,2),'lastShot');
let overtimeFound=false,limitFound=false;
for(let seed=1;seed<=100 && !(overtimeFound&&limitFound);seed++) {
  const opts={mode:'timed',seed,quarterSeconds:1,overtimeSeconds:10};
  const limited=simulateGame(team,team,{...opts,maxOvertimes:0});
  if(limited.tie) {
    limitFound=true;assert.equal(limited.complete,false);assert.equal(limited.winnerA,null);
    const extended=simulateGame(team,team,opts);assert.ok(extended.overtimes>0);assert.equal(extended.complete,true);overtimeFound=true;
    assert.equal(extended.gameSeconds,4+extended.overtimes*10);
  }
}
assert.ok(overtimeFound&&limitFound);
const injuryTeam={...team,roster:team.roster.map((p,i)=>({...p,injured:i===0}))};
assert.equal(simulateGame(injuryTeam,team,{mode:'timed'}).playersA[0].seconds,0);
const emergency=simulateGame(BASELINE,BASELINE,{mode:'timed',seed:42,foulOut:1,replay:true});
assert.ok(emergency.events.some(e=>e.type==='MINIMUM_FIVE_EXCEPTION'));
assert.ok(emergency.events.some(e=>e.technical));
near(emergency.statA.seconds,emergency.gameSeconds*5);
for(const opts of [{pace:0},{quarterSeconds:NaN},{maxOvertimes:-1},{fatigue:'yes'},{nonShootingFoulRate:2}])assert.throws(()=>simulateGame(team,team,{mode:'timed',...opts}));
assert.throws(()=>simulateGame({roster:[]},team,{mode:'timed'}));
assert.throws(()=>monteCarlo(team,team,1,{mode:'timed'}));
const legacyHash=createHash('sha256').update(JSON.stringify([1,42,20260909].map(seed=>simulateGame(TEAMS.GSW,TEAMS.CLE,{seed,replay:true})))).digest('hex');
assert.equal(legacyHash,'edec43423b3ef919c839a27fd9feb49f32ee6f79ab15dfb235db6304d6b771e3'); // sim 0.1.1：拿掉體力＋doubleThreat 體格項（R-089）；等於舊引擎 fatigue:false＋E-086 ch1 hook
console.log(`Timed game: 60 full games; accounting, rotation, clock, FT, assists, overtime, replay and legacy parity passed. ${rotations} substitutions, ${andOnes} and-ones, ${ftRebounds} FT rebounds.`);
