// sim 0.1.1 gate c3: WinImp for the 10 E-065 g0 players (E-117 g0 harness, new engine, no fatigue passed) vs E-117 winimp-off.csv / checkpoint-off.jsonl.
// usage: node --preserve-symlinks --preserve-symlinks-main reports/sim-0.1.1-no-fatigue/c3-run.mjs <out.json> [new|old]   (cwd = tree root; one worker thread per player)
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const D='reports/sim-0.1.0+E117-fatigue-off/',mode=process.argv[3]??'new';
const rd=f=>fs.readFileSync(f,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l));
const ids=rd(D+'g0-on.jsonl').map(c=>c.id);
const seeds=JSON.parse(fs.readFileSync('reports/card-0.1.2+E065-inout-wins/seeds.json','utf8'));
const results=[];const t0=Date.now();
await Promise.all(ids.map(id=>new Promise((res,rej)=>{
  const w=new Worker(new URL('./c3-worker.mjs',import.meta.url),{workerData:{mode},execArgv:['--preserve-symlinks','--preserve-symlinks-main']});
  w.on('error',e=>{console.error('WORKER ERR',e&&e.stack||String(e),Object.getOwnPropertyNames(e||{}));rej(e);});w.on('message',m=>{if(m.error)return rej(Error(m.error));results.push(m.result);w.terminate();res();});
  w.postMessage({id,seed:seeds.baseSeed,samples:seeds.samples});
})));
const ck=new Map(rd(D+'checkpoint-off.jsonl').map(c=>[c.id,c]));
const csv=fs.readFileSync(D+'winimp-off.csv','utf8').replace(/^﻿/,'').trim().split('\n'),H=csv[0].split(','),wi=H.indexOf('winsPer82'),ni=H.indexOf('name');
const w82=a=>{let s=0;for(const d of a.draws)s+=d[6]-d[7];return s/a.draws.length*82;};
const rows=results.sort((a,b)=>a.id-b.id).map(r=>{
  const line=csv.slice(1).find(l=>l.split(',')[ni]===r.avg.name),csvW=line?+line.split(',')[wi]:null,mine=w82(r.avg);
  const c=ck.get(r.id);
  return {id:r.id,name:r.avg.name,winsPer82_new:mine,winsPer82_csv:csvW,csvEqual5dp:csvW!=null&&+mine.toFixed(5)===+csvW.toFixed(5),
    checkpointJsonIdentical:JSON.stringify(r)===JSON.stringify(c)};});
const pass=rows.length===ids.length&&rows.every(r=>r.csvEqual5dp&&r.checkpointJsonIdentical);
const out={mode,pass,n:rows.length,seconds:Math.round((Date.now()-t0)/1000),rows};
fs.writeFileSync(process.argv[2],JSON.stringify(out,null,1));console.log(JSON.stringify({mode,pass,n:rows.length,seconds:out.seconds}));
for(const r of rows)console.log(r.name,r.winsPer82_new,r.winsPer82_csv,r.csvEqual5dp,r.checkpointJsonIdentical);
if(!pass)process.exit(1);
