// sim 0.1.1 gate c1: E-117 p0 game (seed 20261028, Jokic, opponent 0), expected 108-122 on both old(fatigue:false) and new engine.
// usage: node --preserve-symlinks --preserve-symlinks-main reports/sim-0.1.1-no-fatigue/c1.mjs old|new   (cwd = tree root)
import {engine} from './common.mjs';
import {loadX} from '../card-0.1.2+E065-inout-wins/winimp-core.mjs';
import {source,workloadTeam,opponentTeam,options} from '../player-impact-v29/benchmark.mjs';
const mode=process.argv[2],run=await engine(mode),src=source();
const {x}=await loadX();
const p=x.players.find(q=>q.name==='Nikola Jokić')??x.players[0],slot=x.roleMap.get(p.playerId).slot;
const cap=src.capMinutes,minutes=src.players[p.playerId].supportedMinutes;
const a=workloadTeam(x,p,slot,minutes,cap,0),b=opponentTeam(x,x.opponents[0],cap,0),seed=20261028;
const g=run(a.team,b.team,{...options(x,seed,[a.schedule,b.schedule]),luckLedger:[0,0]});
const r={mode,player:p.name,seed,scoreA:g.scoreA,scoreB:g.scoreB,gameSeconds:g.gameSeconds,complete:g.complete,pass:g.scoreA===108&&g.scoreB===122&&g.complete};
console.log(JSON.stringify(r));if(!r.pass)process.exit(1);
