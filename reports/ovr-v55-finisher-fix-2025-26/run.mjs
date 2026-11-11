// v55 修正 B 的 OVR 板。harness 與 reports/ovr-v54-2025-26/run.mjs 相同，只多一個 --mode，
// 輸出改寫到 reports/ovr-v55-finisher-fix-2025-26/<mode>/checkpoint-both-s8.jsonl。
//   node reports/ovr-v55-finisher-fix-2025-26/run.mjs --mode B12 --variant both --samples 8 --workers 18
//   node reports/ovr-v55-finisher-fix-2025-26/run.mjs --mode B12 --ids 1631255,1629027   # 冒煙測試
// 可用 checkpoint 續跑。
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
import {ovrInput} from '../ovr-v47-2025-26/input.mjs';
import {MODES} from './input.mjs';
const root='reports/ovr-v55-finisher-fix-2025-26',arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i<0?d:process.argv[i+1];};
const variant=arg('variant','both'),workers=+arg('workers',6),seed=20261016,samples=+arg('samples',8),mode=arg('mode','B12');
if(!MODES[mode])throw Error('Unknown mode '+mode+'; expected one of '+Object.keys(MODES));
const x=await ovrInput(),only=arg('ids',null)?.split(',').map(Number);
const ids=x.players.map(p=>p.playerId).filter(id=>!only||only.includes(id)).sort((a,b)=>a-b);
const dir=`${root}/${mode}`;fs.mkdirSync(dir,{recursive:true});
const cf=`${dir}/checkpoint-${variant}${samples===4?'':'-s'+samples}.jsonl`;
const done=new Set(fs.existsSync(cf)?fs.readFileSync(cf,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l).playerId):[]);
const jobs=ids.filter(id=>!done.has(id)).map(id=>({id,variant,seed,samples,mode}));
console.log(JSON.stringify({mode,variant,total:ids.length,remaining:jobs.length,workers}));
let next=0,finished=0;const pool=[],t0=Date.now();
await new Promise((resolve,reject)=>{
 if(!jobs.length)return resolve();
 const dispatch=w=>{if(next<jobs.length)w.postMessage(jobs[next++]);};
 for(let n=0;n<Math.min(workers,jobs.length);n++){
  const w=new Worker(new URL('./worker.mjs',import.meta.url));pool.push(w);w.on('error',reject);
  w.on('message',m=>{
   if(m.error)return reject(Error(m.error));
   fs.appendFileSync(cf,JSON.stringify(m.result)+'\n');finished++;
   if(finished%20===0||finished===jobs.length){const s=(Date.now()-t0)/1000;console.log(JSON.stringify({mode,finished,remaining:jobs.length-finished,etaMinutes:Math.round(s/finished*(jobs.length-finished)/60)}));}
   if(finished===jobs.length)resolve();else dispatch(w);
  });dispatch(w);
 }
}).finally(()=>Promise.all(pool.map(w=>w.terminate())));
console.log('done '+mode);
