import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {buildSeventh} from './build_defense_seventh_cards.js';
import {runSeventh} from './run_defense_seventh.js';
execFileSync(process.execPath,['scripts/prepare_defense_seventh_full.js'],{stdio:'inherit'});
const c='reports/defense-seventh/full/config.json';execFileSync('python',['scripts/estimate_defense_seventh.py','82','forward'],{env:{...process.env,DEFENSE_SEVENTH_CONFIG:c},stdio:'inherit'});buildSeventh(82,{label:'candidate',configFile:c});
await runSeventh('full-candidate',{cutoff:0,bundle:'reports/defense-seventh/full/bundle.json',cardFile:'reports/defense-seventh/full/pre82-candidate-league.json'});
