import fs from 'node:fs';
import {playerErrors} from './diagnose_defense_seventh.js';
import {loadSeventh} from './run_defense_seventh.js';
import {read} from './defense_io.js';
const result={multi:playerErrors(loadSeventh('cleanup-multi-41'),41),forward:playerErrors(loadSeventh('cleanup-forward-41'),41),candidate:read('reports/defense-seventh/initial-diagnosis.json').cutoffs[41].candidate};
fs.writeFileSync('reports/defense-seventh/multi-player-diagnosis.json',JSON.stringify(result,null,2)+'\n');for(const[k,v]of Object.entries(result))console.log(k,JSON.stringify(v.metrics));
