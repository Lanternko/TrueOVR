// sim 0.1.1 gate c0 (strength_benchmark + per36_report, 20 games each; both already pass fatigue:false themselves).
// usage: node --preserve-symlinks --preserve-symlinks-main reports/sim-0.1.1-no-fatigue/c0b.mjs <out.json>   (cwd = tree root; same script on old and new tree)
import fs from 'node:fs';import crypto from 'node:crypto';
import {measureStrength} from '../../src/strength_benchmark.js';
import {buildPer36Report} from '../../src/per36_report.js';
import {TEAMS,BASELINE} from '../../src/teams.js';
const h=o=>crypto.createHash('sha256').update(JSON.stringify(o)).digest('hex');
// measureStrength: 2 opponents x 1 slot x 5 samples x 2 games = 20 games
const sb=measureStrength([TEAMS.GSW],[BASELINE,TEAMS.CLE],{samples:5,seed:20261030});
const ref=JSON.parse(fs.readFileSync('data/reference-seasons.json','utf8')).teams.GSW;
const p36=buildPer36Report(TEAMS.GSW,ref,{n:20,pace:100,seed:20261030});
const out={strength_benchmark:{games:20,sha256:h(sb)},per36_report:{games:20,sha256:h(p36)}};
fs.writeFileSync(process.argv[2],JSON.stringify(out));console.log(JSON.stringify(out));
