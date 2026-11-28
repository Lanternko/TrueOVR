// node reports/E122-clock-d1/analyze-e122.mjs <off|on>   -> winimp-<mode>.csv (no md written)
// Copy of E-065 analyze-winimp.mjs: only the checkpoint/output paths and the mode argument differ (same columns, same bootstrap).
// Reads only: checkpoint-winimp.jsonl, card 0.1.2 ranking.csv, data/season-league.json (GP/MIN). No out-of-sample answer files.
import fs from 'node:fs';
const mode=process.argv[2];if(!['off','on'].includes(mode))throw Error('mode');
const dir='reports/E122-clock-d1',seeds=JSON.parse(fs.readFileSync('reports/card-0.1.2+E065-inout-wins/seeds.json','utf8'));
const rows=fs.readFileSync('reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv','utf8').trim().split('\n').map(l=>l.split(','));
const H=rows[0],ix=k=>H.indexOf(k),card=new Map(rows.slice(1).map(r=>[r[ix('name')],r]));
const league=JSON.parse(fs.readFileSync('data/season-league.json','utf8')),gp=new Map(),mn=new Map(),ids=new Map();
for(const t of league.teams)for(const p of t.roster){gp.set(p.playerId,(gp.get(p.playerId)||0)+p.observed.GP);mn.set(p.playerId,(mn.get(p.playerId)||0)+p.observed.MIN);}
const ck=fs.readFileSync(dir+'/checkpoint-'+mode+'.jsonl','utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l));
function rng(a){return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const mean=a=>a.reduce((s,v)=>s+v,0)/a.length;
function stats(res){
 const D=res.draws,S=seeds.samples,O=seeds.opponents,cell=new Map(D.map(d=>[d[0]*S+d[1],d]));
 const est=cells=>{let m=0,e=0,w=0;for(const d of cells){m+=d[2]-d[3];e+=d[4]-d[5];w+=d[6]-d[7];}const n=cells.length;return [m/n,e/n,w/n];};
 const [m,e,w]=est(D),R=rng(seeds.bootstrap.rngSeed+res.playerId%100000),B=seeds.bootstrap.resamples,bm=[],bw=[];
 for(let b=0;b<B;b++){const os=Array.from({length:O},()=>Math.floor(R()*O)),ss=Array.from({length:S},()=>Math.floor(R()*S)),cs=[];
  for(const o of os)for(const s of ss)cs.push(cell.get(o*S+s));const r=est(cs);bm.push(r[0]);bw.push(r[2]);}
 const sd=a=>{const mu=mean(a);return Math.sqrt(a.reduce((s,v)=>s+(v-mu)**2,0)/(a.length-1));};
 return {net:m,exp:e,win:w,seNet:sd(bm),seWin:sd(bw),n:D.length};
}
const out=[];
for(const c of ck){
 const a=stats(c.avg),p=stats(c.pos),r=card.get(c.avg.name);if(!r)throw Error('no card row '+c.avg.name);
 const id=c.id,G=gp.get(id),M=mn.get(id);
 out.push({name:c.avg.name,pos:r[ix('pos')],MIN:+r[ix('MIN')],GP:G,MPG:M/G,minModel:c.avg.minutes,ovrRank:+r[ix('rank')],ovr012:+r[ix('ovr')],pred0:+r[ix('pred0')],defenseBonus:+r[ix('defenseBonus')],align:+r[ix('align')],
  netPerGame:a.net,expNetPerGame:a.exp,winDiff:a.win,winsPer82:a.win*82,se:a.seWin*82,seNet:a.seNet,n:a.n,
  netPerGame_pos:p.net,expNetPerGame_pos:p.exp,winsPer82_pos:p.win*82,se_pos:p.seWin*82});
}
// descriptive margin->wins slope from this population (no outcome data): OLS through origin of winDiff on netPerGame
const sxy=out.reduce((s,o)=>s+o.netPerGame*o.winDiff,0),sxx=out.reduce((s,o)=>s+o.netPerGame**2,0),slope=sxy/sxx;
for(const o of out)o.winsPer82_fromNet=o.netPerGame*slope*82;
out.sort((a,b)=>b.winsPer82-a.winsPer82);out.forEach((o,i)=>o.winRank=i+1);
const cols=Object.keys(out[0]),f=v=>typeof v==='number'?(Number.isInteger(v)?v:+v.toFixed(5)):v;
fs.writeFileSync(dir+'/winimp-'+mode+'.csv','﻿'+[cols.join(','),...out.map(o=>cols.map(k=>f(o[k])).join(','))].join('\n')+'\n');
const rank=a=>{const idx=a.map((v,i)=>[v,i]).sort((x,y)=>x[0]-y[0]),r=Array(a.length);let i=0;while(i<idx.length){let j=i;while(j+1<idx.length&&idx[j+1][0]===idx[i][0])j++;for(let k=i;k<=j;k++)r[idx[k][1]]=(i+j)/2;i=j+1;}return r;};
const sp=(x,y)=>{const a=rank(x),b=rank(y),ma=mean(a),mb=mean(b);let s=0,u=0,v=0;for(let i=0;i<a.length;i++){s+=(a[i]-ma)*(b[i]-mb);u+=(a[i]-ma)**2;v+=(b[i]-mb)**2;}return s/Math.sqrt(u*v);};
const L=[];
L.push(`n=${out.length}  slope(win per pt, from population)=${slope.toFixed(5)}  median se(wins/82)=${[...out.map(o=>o.se)].sort((a,b)=>a-b)[out.length>>1].toFixed(2)}`);
L.push(`Spearman(winsPer82, ovr012)=${sp(out.map(o=>o.winsPer82),out.map(o=>o.ovr012)).toFixed(3)}  Spearman(netPerGame, ovr012)=${sp(out.map(o=>o.netPerGame),out.map(o=>o.ovr012)).toFixed(3)}  Spearman(winsPer82,winsPer82_pos)=${sp(out.map(o=>o.winsPer82),out.map(o=>o.winsPer82_pos)).toFixed(3)}`);
const line=o=>`| ${o.winRank} | ${o.name} | ${o.winsPer82.toFixed(1)} (±${o.se.toFixed(1)}) | ${o.netPerGame.toFixed(2)} | ${o.winsPer82_pos.toFixed(1)} | ${o.ovrRank} | ${o.ovr012.toFixed(1)} | ${o.MPG.toFixed(1)} | ${o.defenseBonus.toFixed(2)} |`;
const head='| WinImp名次 | 球員 | winsPer82 (se) | 淨分差/場 | winsPer82(位置版) | OVR名次 | OVR | MPG | defBonus |\n|---|---|---|---|---|---|---|---|---|';
L.push('\n前20（依 winsPer82）\n'+head+'\n'+out.slice(0,20).map(line).join('\n'));
const byOvr=[...out].sort((a,b)=>a.ovrRank-b.ovrRank);
L.push('\nOVR 前20\n'+head+'\n'+byOvr.slice(0,20).map(line).join('\n'));
const pick=['Derrick White','Alex Caruso','Luka Dončić','Luka Doncic','Victor Wembanyama','Shai Gilgeous-Alexander','Nikola Jokić','Nikola Jokic'];
L.push('\n指定球員\n'+head+'\n'+out.filter(o=>pick.includes(o.name)).map(line).join('\n'));
console.log(L.join('\n'));
