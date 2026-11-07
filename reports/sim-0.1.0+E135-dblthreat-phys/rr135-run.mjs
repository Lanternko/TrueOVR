// node reports/sim-0.1.0+E135-dblthreat-phys/rr135-run.mjs --mode legacy|ch1 [--seeds 20261028,20261029,20261030] [--pairs 2 (smoke)] --out m1-<mode>.jsonl
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const dir='reports/sim-0.1.0+E135-dblthreat-phys',arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i<0?d:process.argv[i+1];};
const mode=arg('mode',null);if(!['legacy','ch1'].includes(mode))throw Error('--mode legacy|ch1');const ch1=mode==='ch1';
const seeds=(arg('seeds',null)?.split(',').map(Number))??[20261028,20261029,20261030];
const np=arg('pairs',null)?+arg('pairs'):null;
const out=arg('out',null);if(!out)throw Error('--out required');const cf=dir+'/'+out;
const done=new Set(fs.existsSync(cf)?fs.readFileSync(cf,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l).seed):[]);
const todo=seeds.filter(s=>!done.has(s));let next=0,fin=0;const pool=[];
const pairsAll=[];for(let a=0;a<30;a++)for(let b=a+1;b<30;b++)pairsAll.push([a,b]);const pairs=np?pairsAll.slice(0,np):null;
console.log(JSON.stringify({mode,seeds,remaining:todo.length,pairs:np??'all',startedAt:new Date().toISOString()}));
await new Promise((res,rej)=>{
 if(!todo.length)return res();
 for(let n=0;n<todo.length;n++){
  const w=new Worker(new URL('./rr135-worker.mjs',import.meta.url),{workerData:{ch1}});pool.push(w);w.on('error',rej);
  w.on('message',m=>{if(m.error)return rej(Error(m.error));fs.appendFileSync(cf,JSON.stringify(m)+'\n');fin++;console.log(JSON.stringify({seed:m.seed,games:m.games.length,finished:fin,at:new Date().toISOString()}));if(fin===todo.length)res();});
  w.postMessage({seed:todo[next++],pairs});
 }
}).finally(()=>Promise.all(pool.map(w=>w.terminate())));
console.log('done');
