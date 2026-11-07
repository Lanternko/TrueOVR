// Freezes the preregistered finisher / creator groups and the EB hyperparameters for d_i,
// from shot-origin.json, BEFORE any evaluation simulation is run.
//   node reports/ovr-v55-finisher-fix-2025-26/freeze-groups.mjs
import fs from 'node:fs';
const dir='reports/ovr-v55-finisher-fix-2025-26';
const O=JSON.parse(fs.readFileSync(`${dir}/shot-origin.json`,'utf8'));
// name lookup from the v47 ranking csv (quoted CSV: "rank","playerId","name","position",...)
const unq=t=>t.replace(/^﻿/,'').split(',').map(v=>v.replace(/^"|"$/g,''));
const rk=fs.readFileSync('reports/ovr-v47-2025-26/ranking.csv','utf8').trim().split(String.fromCharCode(10));
const H=unq(rk[0]),iId=H.indexOf('playerId'),iNm=H.indexOf('name'),iPos=H.indexOf('position');
const nm=new Map();
for(const line of rk.slice(1)){const c=unq(line);nm.set(+c[iId],{name:c[iNm],pos:c[iPos]});}

const K_S=25;                    // pseudo-attempts for the fed-share shrinkage
function stats(season){
 const S=O.seasons[season],L=S.league.find(r=>r.zone==='short');
 const sBar=L.fedA/(L.fedA+L.selfA), pf=L.fedPct, ps=L.selfPct, dBar=pf-ps;
 return {sBar,pf,ps,dBar};
}
function players(season){
 const S=O.seasons[season],{sBar,pf,ps,dBar}=stats(season),out=[];
 for(const [pid,z] of Object.entries(S.players)){
  const s=z.short;if(!s)continue;
  const A=s.fedA+s.selfA;if(!A)continue;
  out.push({playerId:+pid,A,fedA:s.fedA,selfA:s.selfA,
   d:s.fedA&&s.selfA?s.fedM/s.fedA-s.selfM/s.selfA:null,
   sTilde:(s.fedA+K_S*sBar)/(A+K_S),
   v:s.fedA&&s.selfA?pf*(1-pf)/s.fedA+ps*(1-ps)/s.selfA:null});
 }
 return out;
}
// tau^2 by method of moments on players with >=40 non-putback rim attempts
function tau2(list){
 const e=list.filter(p=>p.A>=40&&p.d!==null),dBar=e.reduce((a,p)=>a+p.d*p.A,0)/e.reduce((a,p)=>a+p.A,0);
 const varObs=e.reduce((a,p)=>a+(p.d-dBar)**2,0)/(e.length-1);
 const meanV=e.reduce((a,p)=>a+p.v,0)/e.length;
 return {n:e.length,dBarWeighted:dBar,varObserved:varObs,meanSamplingVar:meanV,tau2:Math.max(varObs-meanV,1e-6)};
}
const out={frozenAt:'2026-10-19',pseudoAttemptsFedShare:K_S,seasons:{}};
for(const season of Object.keys(O.seasons)){
 const list=players(season),t=tau2(list);
 out.seasons[season]={...stats(season),tau2:t};
}
// preregistered groups, from 2025-26
const L=players('2025-26'),{sBar,dBar}=stats('2025-26');
const fin=L.filter(p=>p.A>=60&&p.sTilde>=0.75).sort((a,b)=>b.sTilde-a.sTilde);
const cre=L.filter(p=>p.A>=200&&p.sTilde<=0.25).sort((a,b)=>a.sTilde-b.sTilde);
const tag=p=>({playerId:p.playerId,name:nm.get(p.playerId)?.name??'?',pos:nm.get(p.playerId)?.pos??'?',
  rimAttempts:p.A,fedShare:+p.sTilde.toFixed(3),rawGap:p.d===null?null:+p.d.toFixed(3)});
out.groups={criteria:{finisher:'rimAttempts>=60 and fedShare>=0.75',creator:'rimAttempts>=200 and fedShare<=0.25'},
 finishers:fin.map(tag).filter(p=>p.name!=='?'),creators:cre.map(tag).filter(p=>p.name!=='?')};
out.focus=[1631255,1629646,1629637].map(id=>{const p=L.find(q=>q.playerId===id);return p?tag(p):{playerId:id,name:nm.get(id)?.name,note:'no rim attempts recorded'};});
fs.writeFileSync(`${dir}/frozen-groups.json`,JSON.stringify(out,null,1));
console.log(JSON.stringify({seasons:out.seasons,nFinishers:out.groups.finishers.length,nCreators:out.groups.creators.length,
 focus:out.focus,finishers:out.groups.finishers.map(p=>p.name+' '+p.fedShare),creators:out.groups.creators.map(p=>p.name+' '+p.fedShare)},null,1));
