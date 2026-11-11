// E-140 ledger FT component (report-only). Same as E-120 ledger-run-e120.mjs, plus a variant with the calibrated baseline shift c:
// ft_c = -100*(V(avg, avg, beta-c) - V(avg, avg, -c)); ft_0 is the E-120 definition. Run from repo root: node reports/E140-foul-on-recal/ledger-run-e140.mjs
import fs from 'node:fs';
import {loadX} from '../card-0.1.2+E065-inout-wins/winimp-core.mjs';
import {gameOptions,courtPlayer,baseEnv,possessionValue,constantsFrom} from './ledger-core-e140.mjs';
import {loadBeta} from './winimp-core-e140.mjs';
const c=JSON.parse(fs.readFileSync('reports/E140-foul-on-recal/calibration.json','utf8')).c;
const X=await loadX(),opt=gameOptions(X.xAvg,1),T=JSON.parse(fs.readFileSync('reports/E106-bias-ledger/timing.json','utf8')),K=constantsFrom(T);
const prof=X.xAvg.profiles,five=(cand,slot)=>prof.map((q,i)=>courtPlayer(i===slot?cand:q,q,K.fatigue));
const V=(os,ds,fb=0)=>{const e=baseEnv(os,ds,opt);e.foulBeta=fb;return possessionValue(e,opt,K).V0;};
const beta=loadBeta(),osA=five(null,-1),base=V(osA,osA),baseC=V(osA,osA,-c);
const old=JSON.parse(fs.readFileSync('reports/E106-bias-ledger/ledger.json','utf8')),byId=new Map(old.players.map(p=>[p.playerId,p]));
const out=[];
for(const p of X.x.players){const o=byId.get(p.playerId);if(!o)continue;const b=beta[p.playerId]??0;
 out.push({playerId:p.playerId,name:p.name,pos:o.pos,beta:b,inTable:p.playerId in beta,ft:-100*(V(osA,osA,b)-base),ftC:-100*(V(osA,osA,b-c)-baseC)});}
fs.writeFileSync(new URL('./ledger-ft.json',import.meta.url),JSON.stringify({meta:{c,base100:100*base,baseC100:100*baseC,n:out.length},players:out},null,1));
console.log(JSON.stringify({c,n:out.length}));
