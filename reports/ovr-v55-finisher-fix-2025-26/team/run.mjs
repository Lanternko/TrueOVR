// node reports/ovr-v55-finisher-fix-2025-26/team/run.mjs [season ...] [--workers=N] [--mode=B12]
// 與 reports/player-impact-v54-team/run.mjs 同一個 harness，只多 --mode，且輸出寫在本目錄的
// runs/ 底下（絕不寫 runs/ 或 reports/player-impact-v5x-team/runs/，那些是凍結產物）。
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const root='reports/ovr-v55-finisher-fix-2025-26/team',protocol=JSON.parse(fs.readFileSync('reports/player-impact-v47/protocol.json'));
const args=process.argv.slice(2),n=Number((args.find(a=>a.startsWith('--workers='))||'--workers=4').split('=')[1]);
const mode=(args.find(a=>a.startsWith('--mode='))||'--mode=B12').split('=')[1];
const seasons=args.filter(a=>!a.startsWith('--'));if(!seasons.length)seasons.push(...protocol.seasons);
const seeds=(args.find(a=>a.startsWith('--seeds='))?.split('=')[1].split(',').map(Number))||protocol.seeds;
fs.mkdirSync(root+'/runs',{recursive:true});
const jobs=seasons.flatMap(season=>seeds.map(seed=>({mode,season,seed,file:`${root}/runs/${season}-${mode}-${seed}.json`}))).filter(j=>!fs.existsSync(j.file));
let next=0,done=0;const t0=Date.now(),workers=[];console.log(JSON.stringify({mode,seasons,seeds,pending:jobs.length,workers:n}));
try{await new Promise((res,rej)=>{if(!jobs.length)return res();const go=w=>{if(next<jobs.length)w.postMessage(jobs[next++]);};
 for(let i=0;i<Math.min(n,jobs.length);i++){const w=new Worker(new URL('./worker.mjs',import.meta.url));workers.push(w);w.on('error',rej);
  w.on('message',m=>{if(m.error)return rej(Error(m.error));done++;console.log(JSON.stringify({done,total:jobs.length,season:m.job.season,seed:m.job.seed,games:m.games,tagged:m.tagged,v55:m.v55,seconds:(Date.now()-t0)/1000}));if(done===jobs.length)res();else go(w);});go(w);}});
}finally{await Promise.all(workers.map(w=>w.terminate()));}
console.log('done team '+mode);
