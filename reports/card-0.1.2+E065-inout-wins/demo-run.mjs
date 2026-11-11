// node reports/card-0.1.2+E065-inout-wins/demo-run.mjs [--workers 6]   (repo root; resumable)
// Phase 1: baseline over all seeds -> median-wins team (15th of 30 by mean baseline wins, ties by id; never the player's own team).
// Phase 2: remove-X and add-X-to-median arms, same seeds.
import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
import {prepare,findPlayer} from './demo-core.mjs';
const dir='reports/card-0.1.2+E065-inout-wins',arg=(k,d)=>{const i=process.argv.indexOf('--'+k);return i<0?d:process.argv[i+1];};
const seeds=JSON.parse(fs.readFileSync(dir+'/seeds.json','utf8')).demo.seeds,workers=+arg('workers',6);
const NAMES=['Derrick White','Luka Doncic','Victor Wembanyama','Alex Caruso'];
const cf=dir+'/checkpoint-demo.jsonl',rows=()=>fs.existsSync(cf)?fs.readFileSync(cf,'utf8').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l)):[];
const b=await prepare(),players=NAMES.map(n=>{const h=findPlayer(b,n);return {name:h.player.name,playerId:h.player.playerId,teamId:h.team,teamName:h.teamName};});
const pool=[];for(let i=0;i<workers;i++){const w=new Worker(new URL('./demo-worker.mjs',import.meta.url));pool.push(w);}
async function runJobs(jobs){
 const done=new Set(rows().map(r=>r.armId+'|'+r.seed)),todo=jobs.filter(j=>!done.has(j.arm.id+'|'+j.seed));let next=0,fin=0;const t0=Date.now();
 console.log(JSON.stringify({jobs:jobs.length,todo:todo.length}));
 if(!todo.length)return;
 await new Promise((res,rej)=>{
  const go=w=>{if(next<todo.length)w.postMessage(todo[next++]);};
  for(const w of pool){w.removeAllListeners('message');w.on('error',rej);w.on('message',m=>{
   if(m.error)return rej(Error(m.error));fs.appendFileSync(cf,JSON.stringify(m.result)+'\n');fin++;
   console.log(JSON.stringify({fin,of:todo.length,arm:m.result.armId,seed:m.result.seed,min:Math.round((Date.now()-t0)/600)/100}));
   if(fin===todo.length)res();else go(w);});go(w);}
 });
}
await runJobs(seeds.map(seed=>({arm:{id:'base',kind:'base'},seed})));
const base=rows().filter(r=>r.armId==='base'),mean=new Map();
for(const r of base)for(const t of r.teams)mean.set(t.id,(mean.get(t.id)||0)+t.wins/base.length);
const own=new Set(players.map(p=>p.teamId)),ranked=[...mean.entries()].sort((a,c)=>c[1]-a[1]||a[0]-c[0]);
const median=ranked[14]; // 15th of 30
const medianTeam={id:median[0],meanWins:median[1],rank:15,ownTeamConflict:own.has(median[0])};
if(own.has(median[0]))throw Error('median team is one of the demo players teams; decide rule');
fs.writeFileSync(dir+'/demo-arms.json',JSON.stringify({players,medianTeam,baselineMeanWins:Object.fromEntries(ranked),seeds},null,1));
console.log(JSON.stringify({medianTeam}));
const arms=[];for(const p of players){arms.push({id:'remove:'+p.name,kind:'remove',teamId:p.teamId,playerId:p.playerId});arms.push({id:'add:'+p.name,kind:'add',teamId:p.teamId,playerId:p.playerId,toTeamId:medianTeam.id});}
await runJobs(arms.flatMap(arm=>seeds.map(seed=>({arm,seed}))));
await Promise.all(pool.map(w=>w.terminate()));console.log('done');
