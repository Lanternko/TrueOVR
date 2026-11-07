// node reports/sim-0.1.0+E117-fatigue-off/winimp-run-e117.mjs --fatigue on|off [--workers 18] [--names 'A|B'] [--out checkpoint-x.jsonl]  (run from repo root; resumable)
// Run from repo root; resumable (checkpoint lives in this directory). Same population/seed/sample design as E-065 winimp-run.mjs.
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const {loadX}=await import('./winimp-core-e117.mjs');
const dir='reports/sim-0.1.0+E117-fatigue-off',arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i<0?d:process.argv[i+1];};
const mode=arg('fatigue','on');if(!['on','off'].includes(mode))throw Error('bad fatigue');const fatigue=mode==='on';
const seeds=JSON.parse(fs.readFileSync('reports/card-0.1.2+E065-inout-wins/seeds.json','utf8')),workers=+arg('workers',18);
const {x}=await loadX(),rows=fs.readFileSync('reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv','utf8').trim().split('\n'),head=rows[0].split(',');
const ni=head.indexOf('name'),mi=head.indexOf('MIN');
const byName=new Map();for(const p of x.players){if(byName.has(p.name))throw Error('dup name '+p.name);byName.set(p.name,p.playerId);}
const ids=[];for(const l of rows.slice(1)){const r=l.split(',');if(+r[mi]>=500){const id=byName.get(r[ni]);if(id==null)throw Error('no match '+r[ni]);ids.push(id);}}
ids.sort((a,b)=>a-b);
let only=arg('ids',null)?.split(',').map(Number);
if(arg('subset',null)){const s=JSON.parse(fs.readFileSync(dir+'/'+arg('subset'),'utf8'));only=s.playerIds;}
const names=arg('names',null)?.split('|');if(names)only=names.map(n=>{if(!byName.has(n))throw Error('no name '+n);return byName.get(n);});
const sel=only?ids.filter(i=>only.includes(i)):ids;
if(only&&sel.length!==only.length)throw Error('some requested ids not in MIN>=500 population');
const cf=dir+'/'+arg('out','checkpoint-'+mode+'.jsonl');
const done=new Set(fs.existsSync(cf)?fs.readFileSync(cf,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l).id):[]);
const jobs=sel.filter(id=>!done.has(id)).map(id=>({id,seed:seeds.baseSeed,samples:seeds.samples}));
console.log(JSON.stringify({fatigue:mode,population:sel.length,remaining:jobs.length,workers,samples:seeds.samples,checkpoint:cf}));
let next=0,finished=0;const pool=[],t0=Date.now();
await new Promise((resolve,reject)=>{
 if(!jobs.length)return resolve();
 const dispatch=w=>{if(next<jobs.length)w.postMessage(jobs[next++]);};
 for(let n=0;n<Math.min(workers,jobs.length);n++){
  const w=new Worker(new URL('./winimp-worker-e117.mjs',import.meta.url),{workerData:{fatigue}});pool.push(w);w.on('error',reject);
  w.on('message',m=>{
   if(m.error)return reject(Error(m.error));
   fs.appendFileSync(cf,JSON.stringify(m.result)+'\n');finished++;
   if(finished%10===0||finished===jobs.length){const s=(Date.now()-t0)/1000;console.log(JSON.stringify({finished,remaining:jobs.length-finished,etaMinutes:Math.round(s/finished*(jobs.length-finished)/60)}));}
   if(finished===jobs.length)resolve();else dispatch(w);
  });dispatch(w);
 }
}).finally(()=>Promise.all(pool.map(w=>w.terminate())));
console.log('done');
