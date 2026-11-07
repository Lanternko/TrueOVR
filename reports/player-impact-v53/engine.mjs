// v53 engine: the v47 engine with its probability model swapped for v53/model.mjs.
// With no pressureMeasurement and spread scale 1 it is exactly v47. The only game-source change is
// the optional luck ledger below, which reads the draws without consuming random numbers.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const cache = new Map();
export async function impactEngine(version, options = {}) {
  const key = JSON.stringify([version, options]); if (cache.has(key)) return cache.get(key);
  let s = fs.readFileSync('reports/player-impact-v47/engine.mjs', 'utf8');
  const from = "url('reports/player-impact-v47/model.mjs')", to = "url('reports/player-impact-v53/model.mjs')";
  if (s.split(from).length !== 2) throw Error('v53 model anchor drift');
  s = s.replace(from, to);
  // Luck ledger (expected-points accounting). The game still follows the dice; when
  // opt.luckLedger = [0, 0] is passed, each FG and FT adds (made - p) * points for the shooting
  // side, with p the exact probability of that draw. No extra random numbers are consumed, so
  // every game is unchanged. Expected margin = actual margin - (own luck - opponent luck).
  const luck = [
    // sim 0.1.4 (R-131, E-189): non-shooting-foul attribute. Inert unless opt.nsFoulExp = {playerId: exp(gamma)} is set (no extra rng(), every factor is exactly 1).
    //   gate probability x mean over the 5 defenders of exp(gamma) (x opt.nsFoulBase, default 1); fouler drawn among the defenders by exp(gamma) (one extra rng() draw, only when set).
    //   Same two replacements as reports/sim-0.1.3+E189-nsfoul-attr/engine-e189-v53.mjs (which patches its own copy, so its anchors are untouched).
    ["if(intentional || rng()<ordinaryContactProbability(ls[off],opt)*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1)) {",
     "if(intentional || rng()<ordinaryContactProbability(ls[off],opt)*(opt.foulSignal?Math.exp(effect(ls[1-off],'FTA',opt)):1)*(opt.nsFoulBase??1)*(opt.nsFoulExp?ls[1-off].reduce((a,q)=>a+(opt.nsFoulExp[q.playerId]??1),0)/ls[1-off].length:1)) {"],
    ["foul(D.lineup[hi],intentional?'intentional':'nonShooting',shooter);",
     "foul(D.lineup[(opt.nsFoulExp&&!intentional)?pickWeighted(ls[1-off].map(q=>opt.nsFoulExp[q.playerId]??1),rng()):hi],intentional?'intentional':'nonShooting',shooter);"],
    ['made=rng()<foulInputs[zone].raw;', '{const drawP=foulInputs[zone].raw;made=rng()<drawP;if(opt.luckLedger)opt.luckLedger[off]+=((made?1:0)-drawP)*points;}'],
    ['made=rng()<(opt.foulConditioning?attemptMakeProbability(p.make[zone],shootingFoulChance):p.make[zone]);',
     '{const drawP=(opt.foulConditioning?attemptMakeProbability(p.make[zone],shootingFoulChance):p.make[zone]);made=rng()<drawP;if(opt.luckLedger)opt.luckLedger[off]+=((made?1:0)-drawP)*points;}'],
    ["record(off,shooter,'fta'); made=rng()<pct;", "record(off,shooter,'fta'); made=rng()<pct;if(opt.luckLedger)opt.luckLedger[off]+=(made?1:0)-pct;"],
    ['const made=rng()<pct;', 'const made=rng()<pct;if(opt.luckLedger)opt.luckLedger[off]+=(made?1:0)-pct;'],
  ];
  const listAnchor = ' const changes=[\n';
  if (s.split(listAnchor).length !== 2) throw Error('v53 luck anchor drift');
  s = s.replace(listAnchor, listAnchor + luck.map(([a, b]) => `  [${JSON.stringify(a)},${JSON.stringify(b)}],\n`).join(''));
  const mod = await import('data:text/javascript;base64,' + Buffer.from(s).toString('base64'));
  const run = await mod.impactEngine(version, options); cache.set(key, run); return run;
}
