// node reports/player-impact-v53-team/run.mjs [season ...] [--workers=N]
// Full-season v53 runs on the v47 protocol seeds; writes runs/<season>-v53-<seed>.json.
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
const root='reports/player-impact-v53-team',protocol=JSON.parse(fs.readFileSync('reports/player-impact-v47/protocol.json'));
const args=process.argv.slice(2),n=Number((args.find(a=>a.startsWith('--workers='))||'--workers=4').split('=')[1]),variant=(args.find(a=>a.startsWith('--variant='))||'--variant=v53').split('=')[1];
const seasons=args.filter(a=>!a.startsWith('--'));if(!seasons.length)seasons.push('2025-26');
const seeds=(args.find(a=>a.startsWith('--seeds='))?.split('=')[1].split(',').map(Number))||protocol.seeds;
fs.mkdirSync(root+'/runs',{recursive:true});
const jobs=seasons.flatMap(season=>seeds.map(seed=>({variant,season,seed,file:`${root}/runs/${season}-${variant}-${seed}.json`}))).filter(j=>!fs.existsSync(j.file));
let next=0,done=0;const t0=Date.now(),workers=[];console.log(JSON.stringify({pending:jobs.length,workers:n}));
try{await new Promise((res,rej)=>{if(!jobs.length)return res();const go=w=>{if(next<jobs.length)w.postMessage(jobs[next++]);};
 for(let i=0;i<Math.min(n,jobs.length);i++){const w=new Worker(new URL('./worker.mjs',import.meta.url));workers.push(w);w.on('error',rej);
  w.on('message',m=>{if(m.error)return rej(Error(m.error));done++;console.log(JSON.stringify({done,total:jobs.length,season:m.job.season,seed:m.job.seed,games:m.games,tagged:m.tagged,players:m.players,seconds:(Date.now()-t0)/1000}));if(done===jobs.length)res();else go(w);});go(w);}});
}finally{await Promise.all(workers.map(w=>w.terminate()));}
