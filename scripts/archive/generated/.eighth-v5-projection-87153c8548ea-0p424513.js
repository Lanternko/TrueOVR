import fs from 'node:fs';
import * as C from '../src/constants.js';
import * as M from '../src/probability_model.js';
import {read,hash} from './defense_io.js';
import {sixthInputs} from '../src/defense_sixth_jobs.js';
import {createRater,inverse} from './export_defense_sixth_cards.js';
const root='reports/defense-seventh',sigmoid=x=>1/(1+Math.exp(-x)),logit=p=>Math.log(p/(1-p));
export function buildEighthProjection(k,{label='forward',validation='forward',defenseResidual=false,multi=false,configFile=null}={}){
 const config=configFile?read(configFile):null,output=config?.root??root,modelFile=config?`${output}/ability-model-${validation}.json`:`${root}/model-pre${k}-${validation}.json`,base=config?read(`${output}/bundle.json`):sixthInputs({cutoff:k}),league=structuredClone(base.league),options={...base.options,neutralContests:true},signals=structuredClone(options.defenseSignals),model=read(modelFile),raw=read(config?output+'/card-values.json':`reports/defense-sixth/card-values-pre${k}.json`),ids=new Map(model.players.map((p,i)=>[p,i])),values=new Map(raw.players.map(p=>[p.id,p]));
 options.defenseSignals=signals;const weights=model.minutes,avg=v=>v.reduce((s,x,i)=>s+x*weights[i],0)/weights.reduce((a,b)=>a+b,0),sel=model.models.role,plain=model.models.plain;
 const r=createRater(league,options),old=new Map(league.teams.flatMap(t=>t.roster.map(p=>[p.playerId,r.value(p)])));
 const centerO=avg(model.players.map(p=>old.get(p).offense)),centerD=avg(model.players.map(p=>old.get(p).defenseAllowed)),off=sel.priorOffense.map((v,i)=>v+sel.offenseResidual[i]),def=sel.priorDefenseAllowed.map((v,i)=>v+(defenseResidual?sel.defenseResidual[i]:0)),oc=avg(off),dc=avg(def),drD=sel.priorDefenseAllowed.map((v,i)=>v-plain.priorDefenseAllowed[i]),cd=avg(drD),cache=new Map(),projection=[];
 for(const team of league.teams)for(const p of team.roster){
  if(cache.has(p.playerId)){const q=cache.get(p.playerId);Object.assign(p,q.attributes);projection.push({...q.row,teamId:team.id});continue;}
  const i=ids.get(p.playerId),before=r.value(p),targetOff=centerO+100*model.leaguePPP*(off[i]-oc),targetDef=defenseResidual?centerD+100*model.leaguePPP*(def[i]-dc):before.defenseAllowed+100*model.leaguePPP*(drD[i]-cd);
  const originalAttrs=Object.fromEntries(['long','mid','short','pass','tovSkill','offBall','screen','drive'].map(z=>[z,p[z]])),curves={long:C.CURVE_3PT,mid:C.CURVE_MID,short:C.CURVE_SHORT},baseMake=Object.fromEntries(['long','mid','short'].map(z=>[z,M.interpolate(p[z],curves[z])])),direction={};
  // Single scalar ability is not identifiable as separate skills. Minimum-change
  // projection is an explicitly labelled alternative, not newly observed skill data.
  if(multi)for(const z of ['pass','tovSkill','offBall','screen','drive']){p[z]=Math.min(120,originalAttrs[z]+.1);direction[z]=(r.value(p).offense-before.offense)/.1;p[z]=originalAttrs[z];}
  const scale=multi?20:0,den=Math.sqrt(Object.values(direction).reduce((s,x)=>s+x*x,0))||1;
  const setShot=delta=>{for(const z of ['long','mid','short'])p[z]=Math.max(0,Math.min(120,inverse(sigmoid(logit(Math.max(.001,Math.min(.999,baseMake[z])))+delta),curves[z])));if(multi)for(const z of Object.keys(direction))p[z]=Math.max(0,Math.min(120,originalAttrs[z]+scale*delta*direction[z]/den));};
  let lo=-4,hi=4;for(let j=0;j<35;j++){const m=(lo+hi)/2;setShot(m);if(r.value(p).offense<targetOff)lo=m;else hi=m;}setShot((lo+hi)/2);
  const oldSignal=signals.values[p.playerId].shortFG;lo=-4;hi=4;
  for(let j=0;j<35;j++){const m=(lo+hi)/2;signals.values[p.playerId].shortFG=oldSignal+m;if(r.value(p).defenseAllowed<targetDef)lo=m;else hi=m;}signals.values[p.playerId].shortFG=oldSignal+(lo+hi)/2;
  const attributes=Object.fromEntries(Object.keys(originalAttrs).map(z=>[z,p[z]])),after=r.value(p),row={id:p.playerId,teamId:team.id,name:p.name,minutes:weights[i],before,targetOff,targetDef,after,originalAttrs,attributes,offenseProjectionError:after.offense-targetOff,defenseProjectionError:after.defenseAllowed-targetDef};projection.push(row);cache.set(p.playerId,{attributes,row});
 }
 league.seventhSignals=signals;league.seventhProvenance={k,label,validation,defenseResidual,multi,trainGames:model.trainGames,sourceModel:hash(modelFile)};
 fs.writeFileSync(`${output}/pre${k}-${label}-league.json`,JSON.stringify(league)+'\n');fs.writeFileSync(`${output}/pre${k}-${label}-projection.json`,JSON.stringify({k,label,players:projection})+'\n');console.log('CARDS',k,label);
}
if(process.argv[1]?.endsWith('build_defense_eighth_v5_projection.js'))buildEighthProjection(Number(process.argv[2]),JSON.parse(process.argv[3]??'{}'));
