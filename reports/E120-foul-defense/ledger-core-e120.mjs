// E-120 copy of E-106 ledger-core.mjs + env.foulBeta (defender shooting-foul odds). Original E-106 header follows.
// E-106 deterministic expected-points ledger for the live WinImp chain.
// Mirrors the possession flow of the patched simulateDefenseFourthGame (game-source.dump.js) and calls the
// same imported functions; only the clock-state shares (pass gate, forced release, penalty) and the mean
// stamina multiplier come from fixed-seed neutral games (timing.json). Read only.
import * as M from '../../src/probability_model.js';
import * as C from '../../src/constants.js';
import {measuredFreeThrowPercentage} from '../player-impact-v47/ft-model.mjs';
import {measuredContext} from '../../src/measured_creation_context.js';
import {contactRecipientWeights,ordinaryContactProbability} from '../player-impact-v26/model.mjs';
import {spaceProbability} from '../player-impact-v45/space-model.mjs';
import {measuredPutbackChoice} from '../player-impact-v23/model.mjs';
import {terminalDefenseProbabilities} from '../player-impact-v53/model.mjs';
import {opportunityPlan,observedFoulInputs} from '../player-impact-v14/model.mjs';
import {reboundChance,reboundWeights} from '../defense-tenth/step4-rebounds-allocation/model.mjs';
import {offensiveReboundProbability} from '../../src/rebound_block_model.js';
import {pressureSignal,attemptMakeProbability} from '../../src/defense_probability.js';
import {applyRecordedZone} from '../player-impact-v42/choice-model.mjs';
import {options as benchOptions} from '../player-impact-v29/benchmark.mjs';
const Z=['long','mid','short'];
// Same defaults as the game (game-source.dump.js:30-33, 48-49), then the WinImp options.
const TIMED_DEFAULTS={quarterSeconds:720,overtimeSeconds:300,maxOvertimes:20,fatigue:true,substitutions:true,foulOut:6,pace:1,
 nonShootingFoulRate:0.04,andOneRate:0.025,replay:false,seed:1,contextScale:1,turnoverScale:1,blocks:true};
export function gameOptions(xAvg,seed=1){
 return {...TIMED_DEFAULTS,minuteMode:'heuristic',turnoverMode:'legacy',stealPriorRate:.035,touchLiveShare:.5,shotSelection:'legacy',
  foulConditioning:false,excludeZeroTargets:false,endgameStrategies:true,minuteTargets:true,reboundAccounting:false,empiricalTiming:false,
  independentClock:false,foulOutcomes:false,turnoverCategories:false,...benchOptions(xAvg,seed,[null,null])};
}
const sum=a=>a.reduce((s,v)=>s+v,0);
const norm=a=>{const t=sum(a);return a.map(v=>v/t);};
// roster entry exactly like workloadTeam (benchmark.mjs:8), then lineups() stamina (dump:179).
export function courtPlayer(p,slotProfile,fatigue){
 const r={...structuredClone(p),pos:slotProfile.pos,courtPosition:slotProfile.pos,injured:false};
 return M.applyStamina(r,fatigue);
}
const tr=lineup=>C.weightedTop(lineup.map(p=>p.rebound*(1-C.PHYS_REB_WEIGHT)+p.physique*C.PHYS_REB_WEIGHT),C.COMPOSITE.teamRebound);
// Environment of one offense five vs one defense five: every function the opportunity calls.
export function baseEnv(os,ds,opt){
 const trO=tr(os),trD=tr(ds),help=M.helpDefense(ds),phys=M.teamPhysique(ds),press=pressureSignal(ds,opt.stealPriorRate),cache=new Map();
 const prob=(i,a=null,f=false,pb=false)=>{
  const k=i+'|'+a+'|'+f+'|'+pb;let q=cache.get(k);if(q)return q;
  const orig=terminalDefenseProbabilities(os[i],measuredContext(os,i),ds[i],help,trO,trD,phys,
   {assist:a,forced:f,putback:pb,contextScale:opt.contextScale,turnoverScale:opt.turnoverScale,turnoverMode:opt.turnoverMode,
    pressureAttribute:opt.liveSignal?70:press.attribute,contextLongScale:opt.contextLongScale,contextShortScale:opt.contextShortScale},ds,opt);
  q=spaceProbability(orig,os[i],pb,opt);cache.set(k,q);return q;
 };
 let planCache=null;
 const env={os,ds,prob,
  plan:()=>planCache??=opportunityPlan(os,(i,a=null,f=false)=>prob(i,a,f,false),press.relative,opt.creationPolicy),
  contactP:()=>ordinaryContactProbability(os,opt),contactW:()=>contactRecipientWeights(os,opt),
  ftContact:k=>measuredFreeThrowPercentage(os[k]),foulPlayer:k=>os[k],
  orebChance:(z,k)=>reboundChance(os,ds,{zone:z,shooterIndex:k,oldChance:offensiveReboundProbability(os,ds,{zone:z,shooterIndex:k}),options:opt}),
  orebW:(z,k)=>reboundWeights(os,{zone:z,side:'offense',shooterIndex:k,freeThrow:false},opt),
  pbChoice:k=>measuredPutbackChoice(os[k]),passValue:k=>os[k].pass};
 return env;
}
// Offense channels: candidate at slot s, envP = lineup with him, envA = all-average lineup.
export const OFF_CHANNELS=['make_long','make_mid','make_short','zone','tov','ft','foul','oreb','creation','pass','context'];
export function mixedEnv(envP,envA,s,on){
 const E=c=>on.has(c)?envP:envA,cache=new Map();
 const prob=(i,a=null,f=false,pb=false)=>{
  if(i!==s)return E('context').prob(i,a,f,pb);
  if(pb)return E('oreb').prob(i,a,f,true);
  const k=a+'|'+f;let q=cache.get(k);if(q)return q;
  const qa=envA.prob(s,a,f,false),qp=envP.prob(s,a,f,false),m={...qa,make:{...qa.make}};
  for(const z of Z)if(on.has('make_'+z))m.make[z]=qp.make[z];
  if(on.has('tov'))m.pTovTouch=qp.pTovTouch;
  if(on.has('ft'))m.ftPct=qp.ftPct;
  if(on.has('foul'))m.pFoul=qp.pFoul;
  q=applyRecordedZone(m,on.has('zone')?qp.zone:qa.zone);cache.set(k,q);return q;
 };
 let planCache=null;
 const plan=()=>planCache??=(()=>{const P=envP.plan(),A=envA.plan();
  return {weights:(on.has('creation')?P:A).weights,rows:A.rows.map((ra,h)=>{const rp=P.rows[h];
   if(h===s)return {shoot:(on.has('pass')?rp:ra).shoot,intercept:(on.has('tov')?rp:ra).intercept,receivers:(on.has('pass')?rp:ra).receivers};
   return {shoot:(on.has('context')?rp:ra).shoot,intercept:(on.has('context')?rp:ra).intercept,receivers:(on.has('creation')?rp:ra).receivers};})};})();
 return {prob,plan,
  contactP:()=>E('foul').contactP(),contactW:()=>E('foul').contactW(),
  ftContact:k=>k===s?E('ft').ftContact(k):envA.ftContact(k),
  foulPlayer:k=>k===s?E('foul').foulPlayer(k):envA.foulPlayer(k),
  orebChance:(z,k)=>E('oreb').orebChance(z,k),orebW:(z,k)=>E('oreb').orebW(z,k),pbChoice:k=>E('oreb').pbChoice(k),
  passValue:k=>k===s?E('pass').passValue(k):envA.passValue(k)};
}
// Expected points of one possession (value of a fresh opportunity), solved as a linear system in
// x = [V0, Vpb0..Vpb4] (Vpb = value of a putback opportunity for lineup slot k).
export function possessionValue(env,opt,K){
 const D=7,unit=j=>{const v=new Float64Array(D);v[j]=1;return v;},lin=c=>{const v=new Float64Array(D);v[0]=c;return v;};
 const add=(acc,v,w)=>{if(w)for(let j=0;j<D;j++)acc[j]+=w*v[j];return acc;};
 const V0=unit(1),PB=k=>unit(2+k);
 const rr=opt.reboundRates,rf=rr.ftFinal,orebFt=rf.teamProbability*rf.teamOffShare+(1-rf.teamProbability)*rf.playerOffShare;
 const Rft=add(lin(0),V0,orebFt),rfgCache=new Map(),shotCache=new Map();
 const Rfg=(z,k)=>{const key=z+k;let v=rfgCache.get(key);if(v)return v;
  const r=rr[z],c=env.orebChance(z,k),w=norm(env.orebW(z,k));v=add(lin(0),V0,r.teamProbability*r.teamOffShare);
  for(let j=0;j<5;j++){const pb=env.pbChoice(j),wj=(1-r.teamProbability)*c*w[j];add(v,PB(j),wj*pb);add(v,V0,wj*(1-pb));}
  rfgCache.set(key,v);return v;};
 const bestQ=(k,a,f,pb)=>{const own=env.prob(k,null,f,pb);if(a===null)return own;const caught=env.prob(k,a,f,pb);return caught.ev>=own.ev?caught:own;};
 const shotVal=(k,a,f,pb)=>{const key=k+'|'+a+'|'+f+'|'+pb;let acc=shotCache.get(key);if(acc)return acc;
  const q=bestQ(k,a,f,pb),pt=Math.min(.95,q.pTovTouch),fi=observedFoulInputs(q,env.foulPlayer(k),opt,attemptMakeProbability);
  const fb=env.foulBeta??0,fo=x=>fb?x/(x+(1-x)*Math.exp(-fb)):x; // E-120: odds*exp(sum beta of defenders), same transform as the src option
  const w=Z.map(z=>q.zone[z]/(opt.foulOutcomes?fi[z].recorded:1)),W=sum(w),ft=q.ftPct;acc=lin(0);
  Z.forEach((z,zi)=>{const pts=z==='long'?3:2,{raw,qMake:qMake0,qMiss:qMiss0}=fi[z],qMake=fo(qMake0),qMiss=fo(qMiss0),s=(1-pt)*w[zi]/W;if(!s)return;
   add(acc,lin(pts+ft),s*raw*qMake);add(acc,Rft,s*raw*qMake*(1-ft));
   add(acc,lin(pts),s*raw*(1-qMake));
   add(acc,lin(pts*ft),s*(1-raw)*qMiss);add(acc,Rft,s*(1-raw)*qMiss*(1-ft));
   add(acc,Rfg(z,k),s*(1-raw)*(1-qMiss));});
  shotCache.set(key,acc);return acc;};
 const shotMix=(k,a,phi,pb)=>add(add(lin(0),shotVal(k,a,true,pb),phi),shotVal(k,a,false,pb),1-phi);
 const contact=pen=>{const cw=norm(env.contactW()),acc=lin(0);
  for(let h=0;h<5;h++){const ft=env.ftContact(h);add(acc,lin(2*ft),cw[h]*pen);add(acc,Rft,cw[h]*pen*(1-ft));add(acc,V0,cw[h]*(1-pen));}return acc;};
 const cP=env.contactP(),plan=env.plan(),wts=norm(plan.weights);
 const fresh=lin(0);
 for(let hi=0;hi<5;hi++){if(!wts[hi])continue;const row=plan.rows[hi],sh=row.shoot,ic=Math.min(.95,row.intercept),rec=norm(row.receivers),a=env.passValue(hi);
  const open=add(lin(0),shotMix(hi,null,K.forcedGateShoot,false),sh);
  for(let j=0;j<5;j++)if(rec[j])add(open,shotMix(j,a,K.forcedPassed,false),(1-sh)*(1-ic)*rec[j]);
  add(fresh,open,wts[hi]*K.gateOpen);add(fresh,shotVal(hi,null,true,false),wts[hi]*(1-K.gateOpen));}
 const E0=add(add(lin(0),contact(K.penalty),cP),fresh,1-cP),rows=[E0];
 for(let k=0;k<5;k++)rows.push(add(add(lin(0),contact(K.penaltyPutback),cP),shotMix(k,null,K.forcedPutback,true),1-cP));
 // Solve x = c + A x.
 const n=6,A=rows.map((r,i)=>[...Array(n)].map((_,j)=>(i===j?1:0)-r[1+j])),b=rows.map(r=>r[0]);
 for(let c=0;c<n;c++){let p=c;for(let r=c+1;r<n;r++)if(Math.abs(A[r][c])>Math.abs(A[p][c]))p=r;[A[c],A[p]]=[A[p],A[c]];[b[c],b[p]]=[b[p],b[c]];
  for(let r=0;r<n;r++)if(r!==c){const f=A[r][c]/A[c][c];if(f){for(let j=c;j<n;j++)A[r][j]-=f*A[c][j];b[r]-=f*b[c];}}}
 const x=b.map((v,i)=>v/A[i][i]);
 return {V0:x[0],Vpb:x.slice(1),contact:cP};
}
export function constantsFrom(t){
 return {gateOpen:t.gateOpen.fresh,forcedGateShoot:t.forced.gateShoot.share,forcedPassed:t.forced.passed.share,forcedPutback:t.forced.putback.share,
  penalty:t.penalty.fresh,penaltyPutback:t.penalty.putback,fatigue:(1-t.meanEff)/(1-C.STAMINA_MIN_EFF)*(C.STAMINA_MAX_EFF-C.STAMINA_MIN_EFF)/(C.STAMINA_MAX_EFF-C.STAMINA_MIN_EFF)};
}
