// E-120 p0: (a) beta absent vs beta all-0 map vs empty map => bit-identical game (score, events); (b) per-player beta=+-1:
// opponents' shooting fouls (FOUL events with shooting flag) move in expected direction; WinImp (score margin over many seeds) changes.
import {loadX,makeRunner} from './winimp-core-e120.mjs';
import {workloadTeam,opponentTeam,options} from '../player-impact-v29/benchmark.mjs';
import crypto from 'node:crypto';import fs from 'node:fs';
const {x}=await loadX();
const evSample=[];
function play(r,pid,seed,P){
 const p=x.players.find(q=>q.playerId===pid),slot=x.roleMap.get(pid).slot;
 const cap=r.src.capMinutes,minutes=r.src.players[pid].supportedMinutes;
 const a=workloadTeam(x,p,slot,minutes,cap,0),b=opponentTeam(x,x.opponents[0],cap,0);
 const h=crypto.createHash('sha256');let sf=0,sfOnB=0,ftaB=0;
 const eventObserver=e=>{h.update(JSON.stringify(e));
  if(e.type==='FOUL'||e.type==='SHOOTING_FOUL'){if(!evSample.length||evSample.length<3)evSample.push(e);}
  if(e.type==='FTA'||e.type==='FTM'||e.type==='FTX'){if(e.off===1)ftaB++;}};
 const g=r.run(a.team,b.team,{...options(x,seed,[a.schedule,b.schedule]),luckLedger:[0,0],eventObserver});
 return {sA:g.scoreA,sB:g.scoreB,hash:h.digest('hex'),ftaB,fouls:(g.stats?.teamFouls)};
}
const jok=x.players.find(q=>q.name==='Nikola Jokić').playerId;
const base=await makeRunner(null);
const zero={},allZero={};for(const q of x.players)allZero[q.playerId]=0;
const rZero=await makeRunner(allZero),rEmpty=await makeRunner(zero);
const seeds=Array.from({length:12},(_,i)=>20261028+i);
let ident=true;const idrows=[];
for(const s of seeds){const a=play(base,jok,s),b=play(rZero,jok,s),c=play(rEmpty,jok,s);
 const same=a.hash===b.hash&&a.hash===c.hash&&a.sA===b.sA&&a.sB===b.sB;ident=ident&&same;idrows.push({seed:s,same,sA:a.sA,sB:a.sB});}
// direction: Jokić beta=+1/-1 on his own side defenders (opponent B is shooting against Jokić's team)
// Jokić's team is side A (off=0); opponent B's FTs are off===1. His defenders = A lineup.
const N=300;function sweep(r){let ft=0,ma=0,mb=0;for(let i=0;i<N;i++){const o=play(r,jok,30000+i);ft+=o.ftaB;ma+=o.sA;mb+=o.sB;}return {ftaB:ft/N,margin:(ma-mb)/N};}
const mk=v=>{const m={};m[jok]=v;return m;};
const r0=sweep(base),rp=sweep(await makeRunner(mk(1))),rm=sweep(await makeRunner(mk(-1)));
const dir=rp.ftaB>r0.ftaB&&rm.ftaB<r0.ftaB;
const wchg=rp.margin<r0.margin&&rm.margin>r0.margin;
const pass=ident&&dir&&wchg;
const out={player:'Nikola Jokić',identical_beta0:ident,idrows,N,base:r0,plus1:rp,minus1:rm,oppFTAdirectionOK:dir,marginDirectionOK:wchg,pass,eventSample:evSample.slice(0,3)};
fs.writeFileSync(new URL('./p0.json',import.meta.url),JSON.stringify(out,null,1));
console.log(JSON.stringify({ident,r0,rp,rm,dir,wchg,pass}));
if(!pass)process.exit(1);
