// p0 (prereg §3.3): count, per game, first-touch-site calls of handlingWeights and reads of handle inside
// handlingScore, in the WinImp path and in the v41 validation path, for handleShare 'off' and 'measured'.
// Also counts which branch of the first-touch ternary ran and TOUCH events. Writes p0.json.
// usage (repo root): node reports/sim-0.1.0+E087-handle-share/p0.mjs
import fs from 'node:fs';
import {loadX,makeRunner,computeDraws} from './winimp-core-e087.mjs';
import {v41Engine} from './engine-e087.mjs';
import {loadInput} from '../player-impact-v41/input.mjs';
import {handleMap,attachHandles,shareWeights} from './handle-share.mjs';
const D='reports/sim-0.1.0+E087-handle-share/';
const newProbe=()=>{const p={games:0,calls:0,handleReads:0,touches:0,branch:{volume:0,handling:0}};p.event=e=>{if(e.type==='TOUCH')p.touches++;};return p;};
const summ=p=>({...p,event:undefined,callsPerGame:p.calls/p.games,handleReadsPerGame:p.handleReads/p.games,touchesPerGame:p.touches/p.games,volumeBranchPerGame:p.branch.volume/p.games,handlingBranchPerGame:p.branch.handling/p.games});
const out={note:'counts per game; WinImp: SGA (1628983) vs opponents 0, samples 0-1, both variants; v41: 2025-26 schedule indices 0-2, seed 20261012',paths:{}};
// WinImp path
const R=await makeRunner({diag:true}),X=await loadX();
out.winimpMissingHandle=X.missing.length;out.winimpOptionsShotSelection=X.x.options.shotSelection;
for(const mode of ['off','measured']){const probe=newProbe();
 for(const variant of ['avg','pos'])computeDraws(R,X,{id:1628983,seed:20261028,samples:2,opponents:1,handleShare:mode,probe},variant);
 out.paths['winimp-'+mode]=summ(probe);}
// v41 validation path (same options as reports/player-impact-v41/worker.mjs)
const run=await v41Engine({diag:true});
for(const mode of ['off','measured']){
 const b=loadInput('2025-26'),miss=attachHandles(b.league.teams.flatMap(t=>t.roster),handleMap('2025-26'));
 b.options.creationPolicy='rotation-space';b.options.contextLongScale=1;b.options.spaceCenter=JSON.parse(fs.readFileSync('reports/player-impact-v7/2025-26-center.json')).fullCenter;
 out.v41OptionsShotSelection=b.options.shotSelection;out.v41MissingHandle=miss.size;
 const probe=newProbe();b.options.handleShare=mode;b.options.e087Probe=probe;b.options.eventObserver=probe.event;
 const r=run(b.league,b.exposure,{seed:20261012,options:b.options,audit:false,replay:false,indices:[0,1,2]});
 probe.games=r.matches.length;out.paths['v41-'+mode]=summ(probe);}
// three lineups: first-touch weights off vs measured (opponent starting fives = first five of roster order)
out.lineups=[];
for(const o of X.x.opponents.slice(0,3)){const ls=o.roster.slice(0,5);
 const w0=shareWeights(ls,{handleShare:'off'}),w1=shareWeights(ls,{handleShare:'measured'});
 out.lineups.push({team:o.teamId??o.id??o.name,players:ls.map((p,i)=>({name:p.name,handle:p.e087Handle??null,off:+w0[i].toFixed(4),measured:+w1[i].toFixed(4)})),differs:w0.some((v,i)=>v!==w1[i])});}
const zero=Object.entries(out.paths).filter(([k,v])=>v.calls===0).map(([k])=>k);
out.p0pass=zero.length===0&&out.lineups.every(l=>l.differs);out.zeroCallPaths=zero;
fs.writeFileSync(D+'p0.json',JSON.stringify(out,null,1)+'\n');
console.log(JSON.stringify(out,null,1));
