// node reports/sim-0.1.0+E135-dblthreat-phys/winimp-run-135.mjs --mode legacy|ch1 [--workers 12] [--ids a,b] [--sampleStart 16] [--samples 240] --out file.jsonl
// avg variant only. Run from repo root; resumable (ids already in the checkpoint are skipped). Population = ranking.csv MIN>=500 (379), same as E-065/E-076/E-102.
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const {registerE086}=await import('../sim-0.1.0+E086-param-screen/boot.mjs');registerE086();
const {loadX}=await import('./winimp-core-135.mjs');
const dir='reports/sim-0.1.0+E135-dblthreat-phys',arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i<0?d:process.argv[i+1];};
const mode=arg('mode',null);if(!['legacy','ch1'].includes(mode))throw Error('--mode legacy|ch1 required');const ch1=mode==='ch1';
const seeds=JSON.parse(fs.readFileSync('reports/card-0.1.2+E065-inout-wins/seeds.json','utf8')),workers=+arg('workers',12);
const sampleStart=+arg('sampleStart',0),samples=+arg('samples',240);
if(!(sampleStart>=0&&samples>sampleStart))throw Error('bad sample range');
const outArg=arg('out',null);if(!outArg)throw Error('--out required');
const {x}=await loadX(ch1),rows=fs.readFileSync('reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv','utf8').trim().split('\n'),head=rows[0].split(',');
const ni=head.indexOf('name'),mi=head.indexOf('MIN');
const byName=new Map();for(const p of x.players){if(byName.has(p.name))throw Error('dup name '+p.name);byName.set(p.name,p.playerId);}
const ids=[];for(const l of rows.slice(1)){const r=l.split(',');if(+r[mi]>=500){const id=byName.get(r[ni]);if(id==null)throw Error('no match '+r[ni]);ids.push(id);}}
ids.sort((a,b)=>a-b);
const only=arg('ids',null)?.split(',').map(Number);
const lim=arg('first',null)?+arg('first'):null; // convenience: first N ids by playerId (g0 uses the 10 smallest)
const sel=only?ids.filter(i=>only.includes(i)):lim?ids.slice(0,lim):ids;
if(only&&sel.length!==only.length)throw Error('some requested ids not in MIN>=500 population');
const cf=outArg.includes('/')?outArg:dir+'/'+outArg;
const done=new Set(fs.existsSync(cf)?fs.readFileSync(cf,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l).id):[]);
const jobs=sel.filter(id=>!done.has(id)).map(id=>({id,seed:seeds.baseSeed,samples,sampleStart}));
console.log(JSON.stringify({mode,population:sel.length,remaining:jobs.length,workers,sampleStart,samples,checkpoint:cf,startedAt:new Date().toISOString()}));
let next=0,finished=0;const pool=[],t0=Date.now();
await new Promise((resolve,reject)=>{
 if(!jobs.length)return resolve();
 const dispatch=w=>{if(next<jobs.length)w.postMessage(jobs[next++]);};
 for(let n=0;n<Math.min(workers,jobs.length);n++){
  const w=new Worker(new URL('./winimp-worker-135.mjs',import.meta.url),{workerData:{ch1}});pool.push(w);w.on('error',reject);
  w.on('message',m=>{
   if(m.error)return reject(Error(m.error));
   fs.appendFileSync(cf,JSON.stringify(m.result)+'\n');fs.appendFileSync(cf.replace(/\.jsonl$/,'.timing.jsonl'),JSON.stringify({id:m.result.id,ms:m.ms,samples:samples-sampleStart,opponents:30})+'\n');finished++;
   if(finished%10===0||finished===jobs.length){const s=(Date.now()-t0)/1000;console.log(JSON.stringify({mode,finished,remaining:jobs.length-finished,etaMinutes:Math.round(s/finished*(jobs.length-finished)/60),at:new Date().toISOString()}));}
   if(finished===jobs.length)resolve();else dispatch(w);
  });dispatch(w);
 }
}).finally(()=>Promise.all(pool.map(w=>w.terminate())));
console.log('done');
