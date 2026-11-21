// parity: (1) flag-off ledger rows == frozen F-129 v-b ledger (checked in parity.py); (2) records of playSeedLedger == E-140 playSeed on the same runner (swap path); (3) same-seed double run identical with flag on.
import fs from 'node:fs';
import {makeRunner, loadX, allPairs, playSeedLedger} from './core189.mjs';
import {playSeed} from '../E140-foul-on-recal/rr-core.mjs';
const {x} = await loadX(), pairs = allPairs(x.opponents.length), seed = 20261190, out = {seed};
const r = await makeRunner({});
const a = playSeedLedger(r, x, seed, pairs), b = playSeed(r, x, seed, pairs);
const f = ['ptsA','ptsB','possA','possB','foulShootA','foulShootB','foulAndA','foulAndB','ftaA','ftaB','ftmA','ftmB','orebA','orebB','drebA','drebB','scA','scB','rimAttA','rimAttB'];
out.swapPathRecordsEqual = a.records.every((q, i) => f.every(k => q[k] === b[i][k]));
const r2 = await makeRunner({attr: 'odd', base: 1.1});
const c1 = playSeedLedger(r2, x, seed, pairs), c2 = playSeedLedger(r2, x, seed, pairs);
out.flagOnDoubleRunIdentical = JSON.stringify(c1) === JSON.stringify(c2);
out.flagOnDiffersFromOff = JSON.stringify(c1.records) !== JSON.stringify(a.records);
out.flagOnNsFoul = c1.records.reduce((s, q) => s + q.nsFoulA + q.nsFoulB, 0); out.flagOffNsFoul = a.records.reduce((s, q) => s + q.nsFoulA + q.nsFoulB, 0);
fs.writeFileSync(new URL('./parity-local.json', import.meta.url), JSON.stringify(out, null, 1)); console.log(out);
