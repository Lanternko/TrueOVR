// node reports/E122-clock-d1/c1-run.mjs [--workers 18] [--samples 8] [--ids a,b] [--out c1-checkpoint.jsonl]   (repo root; resumable)
// Population = E-106 ledger players with pooledPoss >= 8000 (impact-rapm/rapm.csv). Base seed 20261028.
import fs from 'node:fs';import {Worker} from 'node:worker_threads';
const arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i<0?d:process.argv[i+1];};
const dir='reports/E122-clock-d1',workers=+arg('workers',18),samples=+arg('samples',8);
const led=JSON.parse(fs.readFileSync('reports/E106-bias-ledger/ledger.json','utf8')),ids0=new Set(led.players.map(p=>p.playerId));
const rows=fs.readFileSync('reports/impact-rapm/rapm.csv','utf8').trim().split('\n'),h=rows[0].split(','),ii=h.indexOf('playerId'),pi=h.indexOf('pooledPoss');
let ids=rows.slice(1).map(l=>l.split(',')).filter(r=>+r[pi]>=8000&&ids0.has(+r[ii])).map(r=>+r[ii]).sort((a,b)=>a-b);
if(arg('ids',null))ids=arg('ids').split(',').map(Number);
const cf=dir+'/'+arg('out','c1-checkpoint.jsonl');
const done=new Set(fs.existsSync(cf)?fs.readFileSync(cf,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l).id):[]);
const jobs=ids.filter(i=>!done.has(i)).map(id=>({id,samples,seed:20261028}));
console.log(JSON.stringify({population:ids.length,remaining:jobs.length,workers,samples}));
let next=0,fin=0;const pool=[],t0=Date.now();
await new Promise((res,rej)=>{
 if(!jobs.length)return res();
 for(let n=0;n<Math.min(workers,jobs.length);n++){
  const w=new Worker(new URL('./c1-worker.mjs',import.meta.url));pool.push(w);w.on('error',rej);
  w.on('message',m=>{if(m.error)return rej(Error(m.error));fs.appendFileSync(cf,JSON.stringify(m.result)+'\n');fin++;
   if(fin%10===0||fin===jobs.length){const s=(Date.now()-t0)/1000;console.log(JSON.stringify({fin,remaining:jobs.length-fin,etaMin:Math.round(s/fin*(jobs.length-fin)/60)}));}
   if(fin===jobs.length)res();else if(next<jobs.length)w.postMessage(jobs[next++]);});
  w.postMessage(jobs[next++]);
 }
}).finally(()=>Promise.all(pool.map(w=>w.terminate())));
console.log('done');
