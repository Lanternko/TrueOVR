// g0: HEAD fatigue-on rerun of E-076's 10 g0 players vs E-065 checkpoint/csv
import fs from 'node:fs';
const D='reports/sim-0.1.0+E117-fatigue-off/',E='reports/card-0.1.2+E065-inout-wins/';
const rd=f=>fs.readFileSync(f,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l));
const g=rd(D+'g0-on.jsonl'),base=new Map(rd(E+'checkpoint-winimp.jsonl').map(c=>[c.id,c]));
let allEq=true;const rows=[];
for(const c of g){const b=base.get(c.id);const eq=JSON.stringify(c)===JSON.stringify(b);allEq&&=eq;
 const w=a=>{let s=0;for(const d of a.draws)s+=d[6]-d[7];return s/a.draws.length*82;};
 rows.push({name:c.avg.name,jsonIdentical:eq,winsPer82_head_on:+w(c.avg).toFixed(5),winsPer82_e065_ckpt:+w(b.avg).toFixed(5)});}
const csv=fs.readFileSync(E+'winimp.csv','utf8').trim().split('\n'),H=csv[0].replace('﻿','').split(','),wi=H.indexOf('winsPer82');
for(const r of rows){const l=csv.find(x=>x.split(',')[0]===r.name);r.winsPer82_e065_csv=l?+(+l.split(',')[wi]).toFixed(5):null;r.csvEqual=Math.abs(r.winsPer82_head_on-r.winsPer82_e065_csv)<1e-4;allEq&&=r.csvEqual;}
console.log(JSON.stringify({g0pass:allEq,n:rows.length,rows},null,1));
fs.writeFileSync(D+'g0-compare.json',JSON.stringify({g0pass:allEq,n:rows.length,rows},null,1));
