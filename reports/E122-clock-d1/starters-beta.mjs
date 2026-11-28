// Per-team starter (roster[0..4]) D1 beta sum and full-roster beta sum. Run from repo root.
import fs from 'node:fs';
import {loadX,loadBeta} from './winimp-core-e122.mjs';
const X=(await loadX()).x,B=loadBeta();
const out=X.opponents.map((o,i)=>({i,starters:o.roster.slice(0,5).map(p=>p.playerId),sum5:o.roster.slice(0,5).reduce((s,p)=>s+(B[p.playerId]??0),0),sumAll:o.roster.reduce((s,p)=>s+(B[p.playerId]??0),0),n:o.roster.length}));
fs.writeFileSync('reports/E122-clock-d1/starters-beta.json',JSON.stringify(out));
console.log(out.length,out.slice(0,3));
