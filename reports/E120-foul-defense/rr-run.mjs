// node reports/E120-foul-defense/rr-run.mjs --beta on|off [--workers 4] [--seeds ...]
// Output: rr-<on|off>.jsonl (one line per seed = 435 game records), resumable.
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const dir='reports/E120-foul-defense',arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i<0?d:process.argv[i+1];};
const mode=arg('beta','off');if(!['on','off'].includes(mode))throw Error('bad beta');const workers=+arg('workers',4);
const seeds=(arg('seeds',null)?.split(',').map(Number))??Array.from({length:8},(_,i)=>20261028+i);
const cf=`${dir}/rr-${mode}.jsonl`;
const done=new Set(fs.existsSync(cf)?fs.readFileSync(cf,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l).seed):[]);
const todo=seeds.filter(s=>!done.has(s));let next=0,fin=0;const pool=[];
console.log(JSON.stringify({beta:mode,seeds,remaining:todo.length,workers}));
await new Promise((res,rej)=>{
 if(!todo.length)return res();
 for(let n=0;n<Math.min(workers,todo.length);n++){
  const w=new Worker(new URL('./rr-worker.mjs',import.meta.url),{workerData:{beta:mode}});pool.push(w);w.on('error',rej);
  w.on('message',m=>{fs.appendFileSync(cf,JSON.stringify(m)+'\n');fin++;console.log(JSON.stringify({seed:m.seed,finished:fin}));if(fin===todo.length)res();else if(next<todo.length)w.postMessage(todo[next++]);});
  w.postMessage(todo[next++]);
 }
}).finally(()=>Promise.all(pool.map(w=>w.terminate())));
console.log('done');
