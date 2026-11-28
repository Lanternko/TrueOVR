// g0: HEAD src (0.1.1 native) vs E-135 ch1-60 checkpoint (seed 20261028): 6 players, opponents 0..3, samples 0..15 must be bit-identical. Run from repo root.
import fs from 'node:fs';
const {loadX,makeRunner,computeDraws}=await import('../../card-0.1.2+E065-inout-wins/winimp-core.mjs');
const r=await makeRunner(),X=await loadX();
const ck=fs.readFileSync('reports/sim-0.1.0+E135-dblthreat-phys/checkpoint-ch1-60.jsonl','utf8').trim().split('\n').map(l=>JSON.parse(l).avg);
const ids=[0,60,120,180,240,300].map(k=>ck[k].playerId);let bad=0,n=0;
for(const id of ids){const o=computeDraws(r,X,{id,seed:20261028,samples:16,opponents:4},'avg'),ref=ck.find(q=>q.playerId===id).draws.filter(d=>d[0]<4&&d[1]<16);
 for(let k=0;k<ref.length;k++){n++;if(JSON.stringify(ref[k])!==JSON.stringify(o.draws[k]))bad++;}
 console.log(id,o.name,ref.length,o.draws.length,bad);}
console.log(JSON.stringify({compared:n,mismatch:bad}));
