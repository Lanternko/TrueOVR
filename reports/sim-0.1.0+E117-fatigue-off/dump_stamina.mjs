import fs from 'node:fs';
import {loadX} from './winimp-core-e117.mjs';
const {x}=await loadX();
const prof=new Map(x.profiles.map(p=>[p.playerId,p]));
const o={};for(const p of x.players){const q=prof.get(p.playerId);o[p.name]={playerId:p.playerId,stamina:p.stamina??q?.stamina??null};}
fs.writeFileSync('reports/sim-0.1.0+E117-fatigue-off/stamina.json',JSON.stringify(o,null,1));
console.log(Object.keys(o).length,Object.values(o).filter(v=>v.stamina==null).length);
