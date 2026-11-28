import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {buildSeventh} from './build_defense_seventh_cards.js';
import {runSeventh,loadSeventh} from './run_defense_seventh.js';
import {read} from './defense_io.js';
import {loadSixth} from './run_defense_sixth.js';
import {baseRuns} from './assess_defense_sixth.js';
import {summarizeFifth,compareFifth} from '../src/defense_fifth_scoreboard.js';
const root='reports/defense-seventh';
const plan=process.argv[2]==='rolling'?[{k:25,label:'forward'},{k:55,label:'forward'}]:[{k:41,label:'forward'},{k:41,label:'defense',defenseResidual:true},{k:41,label:'multi',multi:true}];
for(const p of plan){
 buildSeventh(p.k,p);
 if(!fs.existsSync(`${root}/calibration-pre${p.k}-${p.label}.json`))execFileSync(process.execPath,['scripts/calibrate_defense_seventh.js',String(p.k),p.label],{stdio:'inherit'});
 const calibration=read(`${root}/calibration-pre${p.k}-${p.label}.json`).selected,label=`cleanup-${p.label}-${p.k}`;
 if(!fs.existsSync(`${root}/${label}-seeds.json`))await runSeventh(label,{cutoff:p.k,cardFile:`${root}/pre${p.k}-${p.label}-league.json`,calibration});
 const runs=loadSeventh(label),old=loadSixth(`role-offense-neutral-${p.k}`),result={summary:summarizeFifth(runs,p.k),pairedSixth:compareFifth(runs,old,p.k),pairedV3:compareFifth(runs,baseRuns(p.k),p.k)};
 fs.writeFileSync(`${root}/${label}-assessment.json`,JSON.stringify(result,null,2)+'\n');console.log('RESULT',label,JSON.stringify({metrics:result.summary.metrics,mean:result.summary.global,net:result.pairedSixth.netRMSE,wins:result.pairedSixth.winMAE}));
}
