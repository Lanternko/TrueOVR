// E-087 engines. Both add one source patch (handle-share.mjs PATCH_FROM -> PATCH_TO) to the assembled game text;
// the anchor-drift check of the host engine (split length must be 2) throws if the anchor is missing or repeated.
//  - winimpEngine: player-impact-v53 engine (WinImp path, E-065/E-069 phase 2) with the patch added to its v47 change list.
//  - v41Engine: player-impact-v41 engine (2025-26 validation path used by E-069 m2.py) with the patch appended after
//    its own creationPlan replace.
// diag:true additionally counts which branch of the first-touch ternary runs (p0 only; results unaffected).
import fs from 'node:fs';
import {PATCH_FROM, PATCH_TO} from './handle-share.mjs';
const DIAG_FROM = "pickWeighted(opt.shotSelection==='volume'?creationPlan.weights:";
const DIAG_TO = "pickWeighted((opt.e087Probe&&opt.e087Probe.branch[opt.shotSelection==='volume'?'volume':'handling']++,opt.shotSelection==='volume')?creationPlan.weights:";
const cache = new Map();
const load = s => import('data:text/javascript;base64,' + Buffer.from(s).toString('base64'));
export async function winimpEngine({diag = false} = {}) {
  const key = 'w' + diag; if (cache.has(key)) return cache.get(key);
  let s = fs.readFileSync('reports/player-impact-v53/engine.mjs', 'utf8');
  const nl = s.includes('\r\n') ? '\r\n' : '\n', a = '  const luck = [' + nl;
  if (s.split(a).length !== 2) throw Error('E087 v53 luck anchor drift');
  const extra = [[PATCH_FROM, PATCH_TO], ...(diag ? [[DIAG_FROM, DIAG_TO]] : [])];
  s = s.replace(a, a + extra.map(([f, t]) => `    [${JSON.stringify(f)},${JSON.stringify(t)}],${nl}`).join(''));
  const run = await (await load(s)).impactEngine('rotation-space', {game: true});
  cache.set(key, run); return run;
}
export async function v41Engine({diag = false} = {}) {
  const key = 'v' + diag; if (cache.has(key)) return cache.get(key);
  let s = fs.readFileSync('reports/player-impact-v41/engine.mjs', 'utf8');
  const nl = s.includes('\r\n') ? '\r\n' : '\n';
  const a = '  replace("volumeWeights(ls[off]):M.handlingWeights(ls[off])","creationPlan.weights:M.handlingWeights(ls[off])");' + nl;
  if (s.split(a).length !== 2) throw Error('E087 v41 creation anchor drift');
  const extra = [[PATCH_FROM, PATCH_TO], ...(diag ? [[DIAG_FROM, DIAG_TO]] : [])];
  s = s.replace(a, a + extra.map(([f, t]) => `  replace(${JSON.stringify(f)},${JSON.stringify(t)});${nl}`).join(''));
  const run = await (await load(s)).impactEngine('rotation-space');
  cache.set(key, run); return run;
}
