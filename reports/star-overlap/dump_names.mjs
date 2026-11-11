// pid -> {name,pos,selfOpp}（描述用：球星姓名、高用量判定）。node reports/star-overlap/dump_names.mjs
import fs from 'node:fs';
import {loadX} from '../E120-foul-defense/winimp-core-e120.mjs';
const {x} = await loadX();
const o = {}; for (const p of x.players) o[p.playerId] = {name: p.name, pos: p.pos, selfOpp: p.opportunityMeasurement?.selfOpportunityRate ?? null};
fs.writeFileSync(new URL('names.json', import.meta.url), JSON.stringify(o));
console.log(Object.keys(o).length);
