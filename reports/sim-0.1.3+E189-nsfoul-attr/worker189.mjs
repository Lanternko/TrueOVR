// worker: node worker189.mjs --seed S --out f.json [--attr odd|even] [--base m] [--c c] [--pace p] [--noswap 1] [--nolineup 1]
import fs from 'node:fs';
import {makeRunner, loadX, arg, allPairs, playSeedLedger, C013, P013} from './core189.mjs';
const seed = +arg('seed'), out = arg('out');
const mk = {attr: arg('attr', null), base: +arg('base', 1), c: +arg('c', C013), pace: +arg('pace', P013)};
const r = await makeRunner(mk), {x} = await loadX();
const res = playSeedLedger(r, x, seed, allPairs(x.opponents.length), arg('noswap', '0') === '1');
fs.writeFileSync(out, JSON.stringify({mk, seed, records: res.records, rows: arg('nolineup', '0') === '1' ? [] : res.rows}));
console.log('done', seed, res.records.length);
