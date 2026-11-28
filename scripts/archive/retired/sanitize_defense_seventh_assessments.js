import fs from 'node:fs';
import {read} from './defense_io.js';
for(const season of ['2024-25','2025-26']){
 const file='reports/defense-seventh/'+season+'-calendar-assessment.json',r=read(file);
 for(const v of Object.values(r.cutoffs)){
  v.simple.global=null;v.simple.teams=v.simple.teams.map(t=>({id:t.id,name:t.name,net:t.net,wins:t.wins,observed:t.observed}));
  for(const key of ['residualSD','defenseCorrelation','defenseSDRatio']){v.simple.metrics[key]=null;delete v.pairedSimple[key];}
 }fs.writeFileSync(file,JSON.stringify(r,null,2)+'\n');
}
console.log('Comparator unsupported synthetic metrics marked missing. No predictions/results changed.');
