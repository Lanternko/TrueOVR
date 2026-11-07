import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import { simulateGame, monteCarlo } from '../src/simulation_engine.js';
import { TEAMS, BASELINE } from '../src/teams.js';
import { exposure36, referencePer36, buildPer36Report, renderPer36Markdown } from '../src/per36_report.js';

let passed = 0;
function test(name, run) { run(); console.log(`PASS ${name}`); passed++; }
const close = (a, b, label) => assert.ok(Math.abs(a - b) < 1e-8, `${label}: ${a} != ${b}`);
const sum = (rows, k) => rows.reduce((s, p) => s + p[k], 0);
const counted = ['pts','fga','fgm','fg3a','fg3m','mida','midm','rima','rimm',
  'fta','ftm','tov','oreb','dreb','reb','stl','blk','blka','usageEvents','firstTouches',
  'receptions','passAttempts','interceptedPasses','shotOpportunities','evSum','doubleRateSum'];

test('20 historical golden cases remain reproducible in explicit legacy mode', () => {
  const fixture = JSON.parse(fs.readFileSync(new URL('./fixtures/measurement-legacy.json', import.meta.url)));
  for (const c of fixture.cases) {
    const g = simulateGame(TEAMS[c.key], BASELINE, {...c.opts,reboundModel:'legacy',blocks:false});
    const projection = { scoreA:g.scoreA, scoreB:g.scoreB, winnerA:g.winnerA, tie:g.tie,
      possessions:g.possessions,
      statA:Object.fromEntries(fixture.stats.map(k=>[k,g.statA[k]])),
      statB:Object.fromEntries(fixture.stats.map(k=>[k,g.statB[k]])),log:g.log };
    assert.equal(crypto.createHash('sha256').update(JSON.stringify(projection)).digest('hex'), c.sha256);
  }
});

test('Both teams conserve player totals, scoring, rebounds, turnovers and usage', () => {
  let fta = 0, steals = 0, offensiveRebounds = 0;
  for (const team of Object.values(TEAMS)) for (let seed = 1; seed <= 5; seed++) {
    const g = simulateGame(team, BASELINE, { possessions: 75, seed, fatigue: false });
    for (const [s, players, score, opponent] of [
      [g.statA,g.playersA,g.scoreA,g.statB], [g.statB,g.playersB,g.scoreB,g.statA]]) {
      for (const k of counted) close(sum(players,k),s[k],k);
      assert.equal(s.pts, score);
      assert.equal(s.pts, 3*s.fg3m + 2*(s.midm+s.rimm) + s.ftm);
      assert.equal(s.fga, s.fg3a+s.mida+s.rima);
      assert.equal(s.oreb+opponent.dreb, s.fga-s.fgm);
      assert.equal(s.usageEvents, s.fga+s.tov+s.fta/2);
      assert.equal(s.stl, opponent.interceptedPasses);
      assert.ok(s.tov >= s.interceptedPasses);
      assert.equal(s.poss, 75);
      close(sum(players,'usagePct'),100,'USG sums');
      close(sum(players,'eventSharePct'),100,'event shares');
      assert.equal(s.blk,opponent.blka);
      assert.ok(s.blka <= s.fga-s.fgm);
      fta += s.fta; steals += s.stl; offensiveRebounds += s.oreb;
    }
  }
  assert.ok(fta>0 && steals>0 && offensiveRebounds>0, 'Must exercise real event branches');
});

test('Full counters survive 400-event log cap and preserve game determinism', () => {
  const opts={ possessions:350, fatigue:false, seed:902 };
  const g=simulateGame(TEAMS.GSW,BASELINE,opts);
  assert.equal(g.log.length,400);
  assert.ok(g.statA.usageEvents+g.statB.usageEvents>400);
  close(sum(g.playersA,'pts'),g.scoreA,'Full points');
  assert.deepEqual(g,simulateGame(TEAMS.GSW,BASELINE,opts));
});

test('Fatigue removed in sim 0.1.1: false accepted and ignored, true throws, stamina irrelevant', () => {
  const high={...TEAMS.GSW,roster:TEAMS.GSW.roster.map(p=>({...p,stamina:99}))};
  const low={...TEAMS.GSW,roster:TEAMS.GSW.roster.map(p=>({...p,stamina:1}))};
  const opts={possessions:75,seed:300};
  assert.deepEqual(simulateGame(high,BASELINE,opts),simulateGame(low,BASELINE,opts));
  assert.deepEqual(simulateGame(high,BASELINE,opts),simulateGame(high,BASELINE,{...opts,fatigue:false}));
  assert.throws(()=>simulateGame(high,BASELINE,{...opts,fatigue:true}),/fatigue removed in sim 0\.1\.1/);
  assert.throws(()=>simulateGame(high,BASELINE,{fatigue:'false'}));
});

test('Monte Carlo aggregates both sides including FTA/FTM and pooled rates', () => {
  const n=16,opts={possessions:75,fatigue:false,seed:46};
  const games=Array.from({length:n},(_,i)=>simulateGame(TEAMS.GSW,BASELINE,{...opts,seed:opts.seed+i*7919}));
  const r=monteCarlo(TEAMS.GSW,BASELINE,n,opts);
  for(const side of ['A','B']) {
    const totals=k=>games.reduce((s,g)=>s+g['stat'+side][k],0);
    const stat=r['stat'+side],players=r['players'+side];
    for(const k of counted) {close(stat[k],totals(k)/n,k);close(sum(players,k),stat[k],k);}
    close(stat.fgPct,totals('fgm')/totals('fga'),'Pooled FG%');
    close(stat.ftPct,totals('ftm')/totals('fta'),'Pooled FT%');
    const raw=games.map(g=>g['players'+side][0].pts),mean=raw.reduce((a,b)=>a+b)/n;
    const expectedSe=Math.sqrt(raw.reduce((a,b)=>a+(b-mean)**2,0)/(n-1)/n);
    close(players[0].standardError.pts,expectedSe,'PTS standard error');
  }
  assert.throws(()=>monteCarlo(BASELINE,BASELINE,0));
  assert.equal(monteCarlo(BASELINE,BASELINE,1).playersA[0].standardError.pts,null);
});

test('Per36 exposure, rounding, invalid input and season conversion', () => {
  assert.equal(exposure36(100).possessions,75);
  assert.equal(exposure36(100).equivalentMinutes,36);
  const e=exposure36(100.37);
  close(e.equivalentMinutes*e.per36Scale,36,'Equivalent minutes');
  for(const bad of [0,-1,NaN,Infinity,'100',0.01])assert.throws(()=>exposure36(bad));
  const p=referencePer36({minutes:72,games:3,usagePct:20,totals:{PTS:60,FGM:20,FGA:40,FG3M:5,FG3A:10,FTM:15,FTA:20}});
  assert.equal(p.pts,30);assert.equal(p.fgPct,0.5);assert.equal(p.minutesPerGame,24);
  assert.equal(referencePer36({minutes:1,games:1,totals:{FGM:0,FGA:0,FG3M:0,FG3A:0,FTM:0,FTA:0}}).fgPct,null);
});

test('Real source report remains explicit about unmatched context and prototype blocks', () => {
  const data=JSON.parse(fs.readFileSync(new URL('../data/reference-seasons.json',import.meta.url)));
  const ref=data.teams.GSW;
  const r=buildPer36Report(TEAMS.GSW,ref,{n:16,pace:100});
  assert.equal(r.fatigue,false);assert.equal(r.exposure.possessions,75);
  assert.equal(r.coverage.blocks,'miss-decomposition-v1');
  assert.equal(r.coverage.steals,'pass-interceptions-only');
  assert.ok(r.players.every(p=>Number.isFinite(p.simulated.blk) && p.real.blk>0));
  const text=renderPer36Markdown([r]);
  assert.ok(text.includes('Kevin Durant') && text.includes('beta') && text.includes('代理'));
  assert.ok(text.includes('https://stats.nba.com/'));
  assert.throws(()=>buildPer36Report(TEAMS.GSW,{...ref,season:'wrong'},{n:1}));
  assert.throws(()=>buildPer36Report(TEAMS.GSW,{...ref,players:[]},{n:1}));
});
console.log(`\n${passed} measurement checks passed`);
