// sim 0.1.4 multi-seed check: true default path (player-impact-v53/engine.mjs + benchmark options(), fatigue:false as in E-189).
// node reports/sim-0.1.4/verify-worker.mjs --seed S --out f.json --arm on|off   (off = options() with nsFoulExp removed = sim 0.1.3)
import fs from 'node:fs';
import {impactEngine} from '../player-impact-v53/engine.mjs';
import {loadX, arg, allPairs, playSeedLedger} from '../sim-0.1.3+E189-nsfoul-attr/core189.mjs';
import {source} from '../player-impact-v29/benchmark.mjs';
const seed = +arg('seed'), out = arg('out'), arm = arg('arm');
if (!['on', 'off'].includes(arm)) throw Error('--arm on|off');
const inner = await impactEngine('rotation-space', {game: true});
const run = (...a) => { const o = a[a.length - 1]; if (!o.nsFoulExp) throw Error('options() lacks nsFoulExp'); a[a.length - 1] = {...o, fatigue: false, ...(arm === 'off' ? {nsFoulExp: null} : {})}; return inner(...a); };
const {x} = await loadX();
const res = playSeedLedger({run, src: source()}, x, seed, allPairs(x.opponents.length));
fs.writeFileSync(out, JSON.stringify({arm, seed, records: res.records}));
console.log('done', arm, seed, res.records.length);
