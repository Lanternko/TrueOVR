// Same-season box reconstruction with validated conditional DREB/BLK allocation.
// The separate adopted-gameplay runner remains reproducible for comparisons.
import fs from 'node:fs';
import path from 'node:path';
import {Worker} from 'node:worker_threads';
import crypto from 'node:crypto';
const root='reports/player-box-audit';
const [season='2025-26',seedText='20261018',output]=process.argv.slice(2),seed=Number(seedText);
if(!['2022-23','2023-24','2024-25','2025-26'].includes(season)||!Number.isSafeInteger(seed))throw new Error('Usage: node scripts/simulate_individual_box_season.mjs [season] [integer seed] [output.json]');
const status=JSON.parse(fs.readFileSync(root+'/status.json','utf8'));
if(!status.conditionalBoxAllocationAccepted)throw new Error('Recipient allocation has not passed acceptance checks');
for(const [f,h]of Object.entries(status.sourceSHA256))if(crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')!==h)throw new Error('Validated source changed: '+f);
const file=output??`${root}/adopted-runs/${season}-box-allocation-${seed}.json`;
if(fs.existsSync(file))throw new Error('Refusing to overwrite an existing run: '+file);
fs.mkdirSync(path.dirname(file),{recursive:true});
const w=new Worker(new URL('../reports/player-box-audit/allocation/worker.mjs',import.meta.url));
try{await new Promise((resolve,reject)=>{
 w.on('error',reject);w.on('message',m=>{if(m.error)reject(new Error(m.error.split('\n').filter(x=>!x.includes('data:text/javascript;base64')).join('\n')));else{
   const r=JSON.parse(fs.readFileSync(file,'utf8'));r.individualBoxModel={version:status.boxReconstructionVersion,gameplayBaseline:status.gameplayBaseline,sourceSHA256:status.sourceSHA256,scope:status.scope};fs.writeFileSync(file,JSON.stringify(r)+'\n');
   console.log(JSON.stringify({model:status.boxReconstructionVersion,season,seed,file,games:m.result.games}));resolve();
 }});
 w.postMessage({season,seed,version:'box-allocation',file});
});}finally{await w.terminate();}
