// E-208 追加：前瞻 (c)(d)。E208_FWD=forward-inputs-c.json|forward-inputs-d.json；只跑 set=fwd；其餘同 run.mjs。
// jobs: games (a: actual rosters x real schedule) | pairs:<set> (ordered home/away pairs; set=pre|seasonAvg|fwd) | rating:<set> (team vs league-average team)
import fs from 'node:fs';
import {setup,read,seedOf} from './lib.mjs';
const [job,variant,shard,nsh,out,seedsArg]=process.argv.slice(2); const S=Number(seedsArg??20), sh=Number(shard), N=Number(nsh);
const L=await setup(variant); const res=[];
if(job==='games'){
  const inp=read('inputs.json');
  for(const g of inp.games){ if(g.i%N!==sh)continue;
    const th=L.team('H'+g.home,g.hr), ta=L.team('A'+g.away,g.ar), m=[],ph=[],pa=[];
    for(let s=0;s<S;s++){ const swap=(s+g.i)&1, r=swap?L.game(ta,th,seedOf(s,g.i)):L.game(th,ta,seedOf(s,g.i));
      const hs=swap?r.sb:r.sa, as=swap?r.sa:r.sb; m.push(hs-as); ph.push(swap?r.pb:r.pa); pa.push(swap?r.pa:r.pb); }
    res.push({i:g.i,m,ph,pa}); }
}else{
  const [kind,set]=job.split(':'); const inp=read('inputs.json'); const fwd=variant==='F'?read(process.env.E208_FWD):null;
  const rosters=set==='fwd'?fwd.rosters:inp[set]; const ids=Object.keys(rosters).sort();
  const teams=Object.fromEntries(ids.map(id=>[id,L.team(id,rosters[id])]));
  if(kind==='pairs'){
    let k=0; for(let hi=0;hi<ids.length;hi++)for(let ai=0;ai<ids.length;ai++){ if(hi===ai)continue; const key=hi*30+ai; if((k++)%N!==sh)continue;
      const th=teams[ids[hi]], ta=teams[ids[ai]], m=[]; 
      for(let s=0;s<S;s++){ const swap=(s+hi)&1, r=swap?L.game(ta,th,seedOf(s,key)):L.game(th,ta,seedOf(s,key)); m.push(swap?r.sb-r.sa:r.sa-r.sb); }
      res.push({h:ids[hi],a:ids[ai],m}); }
  }else if(kind==='rating'){
    const av=L.avgTeam(); ids.forEach((id,ti)=>{ if(ti%N!==sh)return; const o={id,m:[],pf:0,pa:0,pof:0,poa:0};
      for(let s=0;s<S;s++){ const swap=s&1, r=swap?L.game(av,teams[id],seedOf(s,500+ti)):L.game(teams[id],av,seedOf(s,500+ti));
        const sf=swap?r.sb:r.sa, sa=swap?r.sa:r.sb, pf=swap?r.pb:r.pa, pa=swap?r.pa:r.pb; o.m.push(sf-sa); o.pf+=sf; o.pa+=sa; o.pof+=pf; o.poa+=pa; }
      res.push(o); });
  }else throw Error('job');
}
fs.writeFileSync(out,JSON.stringify({job,variant,shard:sh,N,S,missing:[...L.missing],res}));
console.log('done',job,variant,sh,res.length);
