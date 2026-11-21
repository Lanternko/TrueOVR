// E-122 p0: (a) beta absent vs all-0 vs empty map => bit-identical game (events hash, score);
// (b) Jokic beta=+2s: side-B full-clock segment mean (while he is on floor) rises 1.5-2.5 s; WinImp margin changes (paired, >2 SE).
import {loadX,makeRunner} from './winimp-core-e122.mjs';
import {workloadTeam,opponentTeam,options} from '../player-impact-v29/benchmark.mjs';
import {segObserver} from './seg-core.mjs';
import crypto from 'node:crypto';import fs from 'node:fs';
const {x}=await loadX();
const jok=x.players.find(q=>q.name==='Nikola Jokić').playerId,slot=x.roleMap.get(jok).slot;
function play(r,seed){
 const p=x.players.find(q=>q.playerId===jok),cap=r.src.capMinutes,minutes=r.src.players[jok].supportedMinutes;
 const a=workloadTeam(x,p,slot,minutes,cap,0),b=opponentTeam(x,x.opponents[0],cap,0);
 const h=crypto.createHash('sha256'),so=segObserver(slot);
 const eventObserver=e=>{h.update(JSON.stringify(e));so(e);};
 const g=r.run(a.team,b.team,{...options(x,seed,[a.schedule,b.schedule]),luckLedger:[0,0],eventObserver});
 return {sA:g.scoreA,sB:g.scoreB,hash:h.digest('hex'),seg:so.stats};
}
const base=await makeRunner(null),allZero={};for(const q of x.players)allZero[q.playerId]=0;
const rZero=await makeRunner(allZero),rEmpty=await makeRunner({});
let ident=true;const idrows=[];
for(let i=0;i<12;i++){const s=20261028+i,a=play(base,s),b=play(rZero,s),c=play(rEmpty,s);
 const same=a.hash===b.hash&&a.hash===c.hash&&a.sA===b.sA&&a.sB===b.sB;ident=ident&&same;idrows.push({seed:s,same,sA:a.sA,sB:a.sB});}
const N=1500,mk=v=>({[jok]:v});
function sweep(r){let n=0,s=0,nA=0,sA=0;const m=[];for(let i=0;i<N;i++){const o=play(r,30000+i);n+=o.seg.nOn;s+=o.seg.sumOn;nA+=o.seg.nAll;sA+=o.seg.sumAll;m.push(o.sA-o.sB);}return {meanOn:s/n,meanAll:sA/nA,nOn:n,margins:m};}
const r0=sweep(base),rp=sweep(await makeRunner(mk(2)));
const dmean=rp.meanOn-r0.meanOn;
const d=rp.margins.map((v,i)=>v-r0.margins[i]),md=d.reduce((a,b)=>a+b,0)/N,sd=Math.sqrt(d.reduce((a,b)=>a+(b-md)**2,0)/(N-1)),se=sd/Math.sqrt(N);
const durOK=dmean>=1.5&&dmean<=2.5,winOK=Math.abs(md)>2*se,pass=ident&&durOK&&winOK;
const out={player:'Nikola Jokić',identical_beta0:ident,idrows,N,beta:2,meanOn_base:r0.meanOn,meanOn_plus2:rp.meanOn,dmeanOn:dmean,nOn_base:r0.nOn,marginDiff:md,marginSE:se,durOK,winOK,pass};
fs.writeFileSync(new URL('./p0.json',import.meta.url),JSON.stringify(out,null,1));
console.log(JSON.stringify(out));
if(!pass)process.exit(1);
