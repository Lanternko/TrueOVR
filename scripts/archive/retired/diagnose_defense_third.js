import fs from 'node:fs';
import {runThirdJobs} from '../src/defense_third_pool.js';
import {read} from './defense_io.js';
const jobs=[{preset:'empirical',label:'empirical-pace1',seed:20261012,options:{pace:1}},{preset:'empirical',label:'empirical-pace0836',seed:20261012},{preset:'combined',seed:20261012},{preset:'v1',label:'v1-season-minutes',seed:20261012,options:{seasonMinuteTargets:true}}].map(j=>({...j,kind:'replay'}));
const results=await runThirdJobs(jobs,{onProgress:(n)=>console.log('replays',n+'/'+jobs.length)});
fs.writeFileSync('reports/defense-third/replay-diagnostics.json',JSON.stringify(results,null,2)+'\n');
