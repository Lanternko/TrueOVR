// Diagnostic only. Unmodified v41 validation path (reports/player-impact-v41/engine.mjs, 'rotation-space',
// same options as reports/player-impact-v41/worker.mjs), handleShare not present (= sim 0.1.0 off).
// Counts per player via eventObserver (observers draw no random numbers):
//   first = TOUCH events (possession/opportunity starts, putbacks counted separately in `putback`)
//   recv  = PASS events received
//   holdSec = derived: game-clock seconds from the player's TOUCH/PASS to the next non-SUBSTITUTION event
//             in the same period (engine has no native touch-time stat). A substitution that removes the
//             holder hands the remaining time to the incoming player (engine's refresh() does the same).
// usage (repo root): node reports/sim-0.1.0+E087-handle-share/diag-allocation/collect.mjs <seed> <outFile> [maxGames]
import fs from 'node:fs';
import {loadInput} from '../../player-impact-v41/input.mjs';
import {impactEngine} from '../../player-impact-v41/engine.mjs';
const [,,seedArg,outFile,maxGames]=process.argv;const seed=Number(seedArg);
const b=loadInput('2025-26'),run=await impactEngine('rotation-space');
b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;
b.options.spaceCenter=JSON.parse(fs.readFileSync('reports/player-impact-v7/2025-26-center.json')).fullCenter;
const acc={};const A=id=>acc[id]??={first:0,putback:0,recv:0,holdSec:0,holdSegs:0};
let idOf,hold,pendingPutback;const reset=()=>{idOf=[{},{}];hold=null;};reset();
const close=e=>{if(!hold)return;if(e.period===hold.period){const id=idOf[hold.side][hold.idx];const a=A(id);a.holdSec+=hold.clock-e.clock;a.holdSegs++;}hold=null;};
b.options.eventObserver=e=>{
 if(e.player!==null&&e.player!==undefined&&e.playerId)idOf[e.off][e.player]=e.playerId;
 if(e.type==='SUBSTITUTION'){if(hold&&e.off===hold.side&&e.out===hold.idx){const id=idOf[hold.side][hold.idx];if(e.period===hold.period){A(id).holdSec+=hold.clock-e.clock;}hold={...hold,idx:e.player,clock:e.clock};}return;}
 close(e);
 if(e.type==='TOUCH'){A(e.playerId).first++;hold={side:e.off,idx:e.player,period:e.period,clock:e.clock};}
 else if(e.type==='PASS'){A(e.playerId).recv++;hold={side:e.off,idx:e.player,period:e.period,clock:e.clock};}
 if(e.type==='FGM'||e.type==='FGX'){if(e.putback)A(e.putbackPlayerId).putback++;}
 if(e.type==='GAME_END'||e.type==='OVERTIME_LIMIT')reset();
};
const indices=maxGames?Array.from({length:Number(maxGames)},(_,i)=>i):null;
const t0=Date.now();
const r=run(b.league,b.exposure,{seed,options:b.options,audit:false,replay:false,indices});
const sec={},tov={};for(const t of r.teams)for(const p of t.players){sec[p.playerId]=(sec[p.playerId]??0)+p.stats.seconds;tov[p.playerId]=(tov[p.playerId]??0)+p.stats.tov;}
fs.writeFileSync(outFile,JSON.stringify({seed,games:r.matches.length,ms:Date.now()-t0,players:acc,seconds:sec,tov})+'\n');
console.log(JSON.stringify({seed,games:r.matches.length,ms:Date.now()-t0}));
