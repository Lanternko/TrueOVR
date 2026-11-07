import fs from 'node:fs';
import * as C from '../src/constants.js';
import * as M from '../src/probability_model.js';
import {read,table} from './defense_io.js';
const root='reports/defense-seventh',league=read('data/season-league.json'),box=table('data/season-source/player-games.json'),order={},count={};
for(const g of league.schedule)for(const t of [g.homeId,g.awayId])order[g.id+'/'+t]=count[t]=(count[t]??0)+1;
const curves={long:C.CURVE_3PT,mid:C.CURVE_MID,short:C.CURVE_SHORT},result={};
for(const k of [25,41,55]){
 const model=read(`reports/defense-sixth/model-pre${k}.json`),p=read(`reports/defense-sixth/pre${k}-role-offense-projection.json`),unique=[...new Map(p.players.map(p=>[p.id,p])).values()],byId=new Map(unique.map(p=>[p.id,p])),post=new Map(),train=model.minutes,average=(xs,w)=>xs.reduce((s,x,i)=>s+x*w[i],0)/w.reduce((a,b)=>a+b,0);
 for(const b of box)if(order[b.GAME_ID+'/'+b.TEAM_ID]>k)post.set(b.PLAYER_ID,(post.get(b.PLAYER_ID)??0)+b.MIN);
 const w=model.players.map(id=>post.get(id)??0),old=model.players.map(id=>byId.get(id).before.offense),neu=model.players.map(id=>byId.get(id).after.offense),oldD=model.players.map(id=>byId.get(id).before.defenseAllowed),newD=model.players.map(id=>byId.get(id).after.defenseAllowed),m=model.models.role;
 const profile=read(`reports/defense-sixth/card-values-pre${k}.json`).players,trained=[...new Map(profile.map(p=>[p.id,p])).values()],shooting=(after)=>{let s=0,n=0;for(const p of trained){const a=byId.get(p.id),v=after?a.attributes:a.originalAttrs,FGA=p.raw.FGA,three=p.raw.FG3A/FGA||0;const prob=three*M.interpolate(v.long,curves.long)+(1-three)*(M.interpolate(v.mid,curves.mid)+M.interpolate(v.short,curves.short))/2;s+=FGA*prob;n+=FGA;}return s/n;};
 result[k]={residualMinuteMeanBeforeCentering:average(m.offenseResidual,train),totalTargetMinuteMeanAfterCentering:0,minuteWeightedProjectionBias:average(model.players.map(id=>byId.get(id).offenseProjectionError),train),trainingCardMean:{old:average(old,train),candidate:average(neu,train)},heldoutActualMinuteWeightedCardMean:{old:average(old,w),candidate:average(neu,w)},exposureDrift:{old:average(old,w)-average(old,train),candidate:average(neu,w)-average(neu,train),oldDefense:average(oldD,w)-average(oldD,train),candidateDefense:average(newD,w)-average(newD,train)},fixedApproxShotWeightsFG:{old:shooting(false),candidate:shooting(true),limitation:'Three shares observed in training; remaining two-point attempts split equally only for this rough diagnostic. Not engine FG% or calibration input.'},interpretation:'Post minutes used only in retrospective bias diagnosis, never calibration/estimation. Static card-mean changes cannot uniquely allocate nonlinear engine mean changes. Global residual centering is exact in the trained minute coordinate; clipping bias has the opposite sign to observed negative heldout efficiency bias.'};
}
fs.writeFileSync(root+'/projection-source-diagnosis.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
