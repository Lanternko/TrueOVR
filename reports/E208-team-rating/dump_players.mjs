// dumps engine x.players attrs/pos used by minute rules (d). Run from repo root.
import fs from 'node:fs';
import {loadX} from '../E120-foul-defense/winimp-core-e120.mjs';
const {x,xAvg}=await loadX();
const A=['long','mid','short','ft','drive','tovSkill','pass','rebound','onBall','help'];
const f=p=>({pos:p.pos,...Object.fromEntries(A.map(a=>[a,p[a]]))});
fs.writeFileSync(new URL('players-attrs.json',import.meta.url),JSON.stringify({attrs:A,avg:f(xAvg.profiles[2]),players:Object.fromEntries(x.players.map(p=>[p.playerId,f(p)]))}));
console.log(x.players.length);
