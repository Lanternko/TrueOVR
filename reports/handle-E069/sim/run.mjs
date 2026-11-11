// usage: node reports/handle-E069/sim/run.mjs <outDir> <tag> <kCtl|off> <kPass> <seeds,csv> [nWorkers] [maxGames]
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const [,,outDir,tag,kc,kp,seedsArg,nw='4',maxGames]=process.argv;
const seeds=seedsArg.split(',').map(Number),season='2025-26';
const e069=kc==='off'?null:{kCtl:Number(kc),kPass:Number(kp),pOther:Number(process.env.E069_POTHER??0)};
fs.mkdirSync(outDir,{recursive:true});
const indices=maxGames?Array.from({length:Number(maxGames)},(_,i)=>i):null;
const jobs=seeds.map(seed=>({season,seed,e069,indices,file:`${outDir}/${tag}-${seed}.json`})).filter(j=>!fs.existsSync(j.file));
let next=0,done=0;const workers=[];
try{await new Promise((resolve,reject)=>{
 if(!jobs.length)return resolve();
 for(let i=0;i<Math.min(Number(nw),jobs.length);i++){
  const w=new Worker(new URL('./worker.mjs',import.meta.url),{resourceLimits:{maxOldGenerationSizeMb:6000}});workers.push(w);w.on('error',reject);
  const go=()=>{if(next<jobs.length)w.postMessage(jobs[next++]);};
  w.on('message',m=>{if(m.error)return reject(Error(m.error));console.log(JSON.stringify({done:++done,total:jobs.length,seed:m.job.seed,games:m.result.games}));if(done===jobs.length)resolve();else go();});go();
 }
});}finally{await Promise.all(workers.map(w=>w.terminate()));}
