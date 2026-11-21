// Reproduce the measured player-flow candidate without changing the adopted
// season engine or presenting its unfinished OVR as a validated ranking.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {loadInput} from '../reports/player-impact-v6/input.mjs';
import {impactEngine as legacyClockEngine} from '../reports/player-impact-v6/engine.mjs';
import {impactEngine as teamClockEngine} from '../reports/player-impact-team-clock/engine.mjs';
import {onCourtCollector} from '../reports/player-impact-v1/on-court.mjs';
const args=process.argv.slice(2),get=(key,fallback)=>{const i=args.indexOf('--'+key);return i<0?fallback:args[i+1];};
const season=get('season','2025-26'),seed=Number(get('seed','20261012')),version=get('version','terminal-flow'),limit=get('games',null),strict=args.includes('--strict'),legacyPlayerClock=args.includes('--legacy-player-clock');
if(!['2022-23','2023-24','2024-25','2025-26'].includes(season)||!['terminal-flow','rotation-space'].includes(version)||!Number.isSafeInteger(seed)||limit!==null&&(!Number.isInteger(Number(limit))||Number(limit)<1||Number(limit)>1230))throw Error('Invalid season, seed, version or game limit');
if(version==='rotation-space'&&legacyPlayerClock)throw Error('rotation-space requires team-only clock accounting');
const out=path.resolve(get('out',`reports/player-impact-validation/manual/${season}-${version==='terminal-flow'?'':version+'-'}${seed}${strict?'-strict':''}${limit?'-'+limit+'games':''}.json`));
if(fs.existsSync(out))throw Error('Output already exists; use another --out path');
const validationRoot=version==='rotation-space'?'reports/player-impact-v14':'reports/player-impact-v6';
const statusFile=version==='rotation-space'?'reports/player-impact-v14/status.json':'reports/player-impact-validation/status.json';
const read=f=>JSON.parse(fs.readFileSync(f)),status=read(statusFile),validation=read(validationRoot+'/validation-protocol.json'),hash=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
if(!status.diagnosticRunnable||status.version!==(version==='rotation-space'?'rotation-source-context-14':'terminal-flow-validation-6'))throw Error('Candidate diagnostic is not enabled');
const clockStatus=read('reports/player-impact-team-clock/status.json');
if(!legacyPlayerClock&&(!clockStatus.enabled||clockStatus.version!=='team-only-clock-1'))throw Error('Team-only turnover accounting is not enabled');
const verify=()=>{for(const [f,h]of Object.entries({...validation.hashes,...(!legacyPlayerClock?clockStatus.hashes:{})}))if(hash(f)!==h)throw Error('Frozen candidate source changed: '+f);};verify();
const inputLoader=version==='rotation-space'?(await import('../reports/player-impact-v14/input.mjs')).loadInput:loadInput;
const engine=version==='rotation-space'?(await import('../reports/player-impact-v14/engine.mjs')).impactEngine:(legacyPlayerClock?legacyClockEngine:teamClockEngine);
const b=inputLoader(season),run=await engine(version),collector=onCourtCollector();b.options.onCourtObserver=e=>collector.event(e);
if(version==='rotation-space'){b.options.creationPolicy=version;b.options.contextLongScale=1;b.options.spaceCenter=read(`reports/player-impact-v7/${season}-center.json`).fullCenter;}
const allowed=strict?new Set(read(`reports/player-impact-v1/${season}-on-court-truth.json`).gameIds):null;
let indices=b.league.schedule.flatMap((g,i)=>!allowed||allowed.has(g.id)?[i]:[]);if(limit!==null)indices=indices.slice(0,Number(limit));
const r=run(b.league,b.exposure,{seed,options:b.options,indices,audit:false,replay:false});r.onCourt=collector.finish();delete r.options.onCourtObserver;
if(r.onCourt.games!==r.matches.length)throw Error('On-court exposure mismatch');verify();
r.playerImpactLineage={model:version,season,seed,strict,games:r.matches.length,experimental:true,officialModelReplaced:false,ovrValidated:false,teamTurnoverAccounting:legacyPlayerClock?'legacy-player-clock':'team-only-clock-1',clockAccountingHashes:!legacyPlayerClock?clockStatus.hashes:null,
 validationSHA256:hash(validationRoot+'/validation-protocol.json'),scriptSHA256:hash('scripts/simulate_player_impact_season.mjs'),statusSnapshot:status};
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(r)+'\n');
console.log(JSON.stringify({file:out,model:version,games:r.matches.length,experimental:true,sha256:hash(out)}));
