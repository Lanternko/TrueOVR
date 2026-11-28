// sim 0.1.1 gate c2: first 30 games (seed 20261031 line of E-117 rr-off.jsonl) re-run on the new engine, compared record by record.
// usage: node --preserve-symlinks --preserve-symlinks-main reports/sim-0.1.1-no-fatigue/c2.mjs <out.json> old|new   (cwd = tree root)
import fs from 'node:fs';
import {engine} from './common.mjs';
import {loadX,playSeed,allPairs} from '../sim-0.1.0+E117-fatigue-off/rr-core.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
const mode=process.argv[3],run=await engine(mode),src=source(),{x}=await loadX();
const first=JSON.parse(fs.readFileSync('reports/sim-0.1.0+E117-fatigue-off/rr-off.jsonl','utf8').split('\n')[0]);
const seed=first.seed,pairs=allPairs(x.opponents.length).slice(0,30);
const recs=playSeed({run,src},x,seed,pairs);
const ref=first.records.slice(0,30);
const diffs=[];for(let i=0;i<30;i++)if(JSON.stringify(recs[i])!==JSON.stringify(ref[i]))diffs.push(i);
const out={mode,seed,games:recs.length,mismatches:diffs,pass:recs.length===30&&diffs.length===0};
fs.writeFileSync(process.argv[2],JSON.stringify(out));console.log(JSON.stringify(out));if(!out.pass)process.exit(1);
