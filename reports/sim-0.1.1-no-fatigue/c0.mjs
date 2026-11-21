// sim 0.1.1 gate c0 (adapted from E-112 c0.mjs). usage: node --preserve-symlinks --preserve-symlinks-main reports/sim-0.1.1-no-fatigue/c0.mjs <out.json> old|new   (cwd = tree root)
// 60 budget + 60 heuristic games, sha256 of every event + final result per game.
import fs from 'node:fs';import crypto from 'node:crypto';
import {ovrInput} from '../ovr-v53-2025-26/input.mjs';
import {engine} from './common.mjs';
import {source,options as benchOptions,opponentTeam} from '../player-impact-v29/benchmark.mjs';
import {lineupForGame} from '../../src/season_simulation.js';
const OLD='data/season-league.json'; // tracked league file, unchanged since b8dabc6 (E-103 data/ copy no longer exists)
const x=await ovrInput('both'),run=await engine(process.argv[3]),L=JSON.parse(fs.readFileSync(OLD,'utf8'));
const byId=new Map(x.players.map(p=>[p.playerId,p]));
const teams=L.teams.map(t=>{const es=t.roster.filter(r=>r.observed&&r.observed.GP>=20).sort((p,q)=>q.seasonMinutesPerGame-p.seasonMinutesPerGame||p.playerId-q.playerId).slice(0,10);
  const roster=es.map(e=>({...byId.get(e.playerId),seasonMinutesPerGame:e.seasonMinutesPerGame,injured:false}));return lineupForGame({id:t.id,name:t.name,roster},roster.map(r=>r.playerId));});
const pairs=[];for(let a=0;a<30;a++)for(let b=a+1;b<30;b++)pairs.push([a,b]);
const src=source();
const results={budget:[],heuristic:[]};const seed=20261030;
for(const mode of ['budget','heuristic']){
  for(const [a,b] of pairs.slice(0,60)){
    const h=crypto.createHash('sha256');const eo=e=>h.update(JSON.stringify(e));
    const gseed=(seed+Math.imul(a*30+b,1000003))>>>0;let g;
    if(mode==='budget'){const phase=(seed+a+b)&1,swap=((seed>>>1)+a)&1;
      const ta=opponentTeam(x,x.opponents[a],src.capMinutes,phase),tb=opponentTeam(x,x.opponents[b],src.capMinutes,phase);
      const tm=swap?[tb.team,ta.team]:[ta.team,tb.team],sc=swap?[tb.schedule,ta.schedule]:[ta.schedule,tb.schedule];
      g=run(...tm,{...benchOptions(x,gseed,sc),eventObserver:eo});
    }else{const o=benchOptions(x,gseed,null);delete o.minuteMode;delete o.sourceRotations;
      g=run(teams[a],teams[b],{...o,minuteTargets:true,eventObserver:eo});}
    if(g.gameSeconds!==2880||!g.complete)throw Error('Incomplete game '+mode);
    results[mode].push([a,b,g.scoreA,g.scoreB,h.update(JSON.stringify(g)).digest('hex')]);
  }
}
const out=process.argv[2];fs.writeFileSync(out,JSON.stringify(results));
console.log(out,crypto.createHash('sha256').update(JSON.stringify(results)).digest('hex'),results.budget.length,results.heuristic.length);
