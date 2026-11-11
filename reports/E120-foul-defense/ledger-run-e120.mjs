// E-120 t1: FT component of the deterministic ledger. node reports/E120-foul-defense/ledger-run-e120.mjs
// ft = -100*(V(osA, all-average defense with foul odds*exp(beta_p)) - base). Also re-derives E-106 defFull (beta=0) as reproduction check.
import fs from 'node:fs';
import {loadX} from '../card-0.1.2+E065-inout-wins/winimp-core.mjs';
import {gameOptions,courtPlayer,baseEnv,possessionValue,constantsFrom} from './ledger-core-e120.mjs';
import {loadBeta} from './winimp-core-e120.mjs';
const X=await loadX(),opt=gameOptions(X.xAvg,1),T=JSON.parse(fs.readFileSync('reports/E106-bias-ledger/timing.json','utf8')),K=constantsFrom(T);
const prof=X.xAvg.profiles,five=(cand,slot)=>prof.map((q,i)=>courtPlayer(i===slot?cand:q,q,K.fatigue));
const V=(os,ds,fb=0)=>{const e=baseEnv(os,ds,opt);e.foulBeta=fb;return possessionValue(e,opt,K).V0;};
const beta=loadBeta(),base=V(five(null,-1),five(null,-1));
const old=JSON.parse(fs.readFileSync('reports/E106-bias-ledger/ledger.json','utf8'));
const byId=new Map(old.players.map(p=>[p.playerId,p]));
const out=[];let maxDiffBase=Math.abs(100*base-old.meta.base100),maxDiffDef=0;
for(const p of X.x.players){const o=byId.get(p.playerId);if(!o)continue;
 const slot=X.x.roleMap.get(p.playerId).slot,osA=five(null,-1),dsA=osA,b=beta[p.playerId]??0;
 const defFull0=-100*(V(osA,five(p,slot))-base);maxDiffDef=Math.max(maxDiffDef,Math.abs(defFull0-o.defFull));
 const ft=-100*(V(osA,dsA,b)-base);
 out.push({playerId:p.playerId,name:p.name,pos:o.pos,beta:b,inTable:p.playerId in beta,ft,defFull:o.defFull,defFullWithFt:o.defFull+ft});}
fs.writeFileSync(new URL('./ledger-ft.json',import.meta.url),JSON.stringify({meta:{base100:100*base,maxDiffBase,maxDiffDef,n:out.length},players:out},null,1));
console.log(JSON.stringify({n:out.length,maxDiffBase,maxDiffDef,inTable:out.filter(r=>r.inTable).length}));
