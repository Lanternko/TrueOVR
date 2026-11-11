// E-140 §1 calibration driver (runs on the 5090 from ~/e140). Bisection on c (pace=1), then pace (c fixed), re-check, <=3 rounds.
// Stats: foul rate = (shooting+andOne fouls)/possessions*100 over the league; poss = mean possessions per team per game.
// Target = cal-off.jsonl (beta off, c=0, pace=1) on the same seeds. File name encodes (c,pace) so a restart replays deterministically.
import fs from 'node:fs';import {execFileSync} from 'node:child_process';
const dir='reports/E140-foul-on-recal',seeds=Array.from({length:16},(_,i)=>20261100+i).join(',');
const stats=f=>{let fo=0,po=0,pts=0,n=0;for(const l of fs.readFileSync(`${dir}/${f}.jsonl`,'utf8').trim().split('\n'))for(const r of JSON.parse(l).records){fo+=r.foulShootA+r.foulShootB+r.foulAndA+r.foulAndB;po+=r.possA+r.possB;pts+=r.ptsA+r.ptsB;n++;}
 return {games:n,foulPer100:100*fo/po,possPerTeamGame:po/(2*n),ptsPerTeamGame:pts/(2*n)};};
const T=stats('cal-off'),log=[];
const ev=(c,pace)=>{const f=`cal-c${c.toFixed(6)}-p${pace.toFixed(6)}`;
 execFileSync('node',[`${dir}/rr-run.mjs`,'--beta','on','--c',String(c),'--pace',String(pace),'--workers','20','--seeds',seeds,'--out',f],{stdio:['ignore','ignore','inherit']});
 const s=stats(f);log.push({c,pace,file:f,...s});fs.writeFileSync(`${dir}/calibration-log.json`,JSON.stringify({target:T,log},null,1));console.log(JSON.stringify(log.at(-1)));return s;};
const fr=s=>(s.foulPer100/T.foulPer100-1);           // relative foul-rate gap
const pg=s=>s.possPerTeamGame-T.possPerTeamGame;     // possession gap
// rate decreases with c; poss monotone in pace (sign detected from two points)
function bis(g,lo,hi,tol,mkEval){ // g(x) decreasing/increasing detected; lo<hi with g(lo)*g(hi)<0
 let glo=g(mkEval(lo)),ghi=g(mkEval(hi));
 for(let i=0;i<30;i++){const m=(lo+hi)/2,gm=g(mkEval(m));if(Math.abs(gm)<=tol)return m;if(Math.sign(gm)===Math.sign(glo)){lo=m;glo=gm;}else{hi=m;ghi=gm;}}
 return (lo+hi)/2;}
function bracket(g,x0,step,mkEval){const g0=g(mkEval(x0));if(g0===0)return [x0,x0];let a=x0,ga=g0,b=x0+step,gb=g(mkEval(b));
 for(let i=0;i<12&&Math.sign(ga)===Math.sign(gb);i++){const d=Math.abs(gb)<Math.abs(ga)?1:-1;if(d===1){a=b;ga=gb;b=b+step;gb=g(mkEval(b));}else{b=a;gb=ga;a=a-step;ga=g(mkEval(a));}
  if(Math.sign(ga)!==Math.sign(gb))break;}
 return a<b?[a,b]:[b,a];}
let c=0,pace=1;const rounds=[];let ok=false;
for(let round=1;round<=3&&!ok;round++){
 const mkC=x=>ev(x,pace),[a,b]=bracket(fr,c,0.4,mkC);c=bis(fr,a,b,0.005*0.5,mkC);   // tolerance 0.25% (half of the 0.5% criterion) to leave room after pace step
 const mkP=x=>ev(c,x),[pa,pb]=bracket(pg,pace,0.02,mkP);pace=bis(pg,pa,pb,0.05,mkP);  // tolerance 0.05 (half of the 0.1 criterion)
 const fin=ev(c,pace);ok=Math.abs(fr(fin))<=0.005&&Math.abs(pg(fin))<=0.1;rounds.push({round,c,pace,foulGapRel:fr(fin),possGap:pg(fin),...fin});}
const last=rounds.at(-1);
fs.writeFileSync(`${dir}/calibration.json`,JSON.stringify({seeds:[20261100,20261115],target_off:T,c,pace,converged:ok,foulGapRel:last.foulGapRel,possGap:last.possGap,onAtCalibrated:{foulPer100:last.foulPer100,possPerTeamGame:last.possPerTeamGame,ptsPerTeamGame:last.ptsPerTeamGame},rounds,evaluations:log},null,1));
console.log(JSON.stringify({c,pace,ok}));
