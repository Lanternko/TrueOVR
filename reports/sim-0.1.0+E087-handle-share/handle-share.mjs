// E-087 handleShare wrapper (prereg §3.1). Only the handle term inside handlingScore changes.
// The measured handle is stored on players as p.e087Handle, never as p.handle, so doubleThreat's create,
// assistBoost/HANDLE_IMPACT and the turnover formula keep reading p.handle (undefined -> 70).
// The engine patch (engine-*.mjs) replaces M.handlingWeights(ls[off]) at the first-touch site with
// globalThis.__E087.shareWeights(ls[off],opt) only when opt.handleShare==='measured' or opt.e087Probe is set;
// otherwise the original call runs untouched ('off' = bitwise current behaviour).
import fs from 'node:fs';
import * as M from '../../src/probability_model.js';
import * as C from '../../src/constants.js';
export const MODES = ['off', 'measured'];
export const MISSING_HANDLE = 70;
export const HANDLE_CSV = 'reports/handle-E069/handle.csv';
export function checkMode(mode) { if (!MODES.includes(mode ?? 'off')) throw Error('unknown handleShare ' + mode); return mode ?? 'off'; }
export function handleMap(season = '2025-26') {
  const [h, ...rows] = fs.readFileSync(HANDLE_CSV, 'utf8').replace(/^﻿/, '').trim().split(/\r?\n/);
  const k = h.split(','), pi = k.indexOf('playerId'), si = k.indexOf('season'), hi = k.indexOf('handle');
  const m = new Map();
  for (const l of rows) { const r = l.split(','); if (r[si] !== season) continue; const v = Number(r[hi]); if (Number.isFinite(v)) m.set(Number(r[pi]), v); }
  return m;
}
// Attach measured handle to real players. Missing ids get no field (-> 70 at use time).
export function attachHandles(players, map, miss = new Set()) {
  for (const p of players) { const v = map.get(Number(p.playerId)); if (v === undefined) miss.add(p.playerId); else p.e087Handle = v; }
  return miss;
}
// Same function as src handlingWeights, applied to a view of the lineup whose .handle is the measured value.
export function shareWeights(lineup, opt) {
  const mode = checkMode(opt.handleShare), probe = opt.e087Probe;
  if (probe) probe.calls++;
  const view = lineup.map(p => {
    const q = Object.create(p), h = mode === 'measured' ? (p.e087Handle ?? MISSING_HANDLE) : p.handle;
    if (probe) Object.defineProperty(q, 'handle', {get() { probe.handleReads++; return h; }, enumerable: true});
    else q.handle = h;
    return q;
  });
  const w = M.handlingWeights(view);
  if (probe?.observe) probe.observe(lineup, w);
  return w;
}
export const constants = {HANDLING_W: C.HANDLING_W, HANDLING_TEMP: C.HANDLING_TEMP, HANDLING_FLOOR_MIX: C.HANDLING_FLOOR_MIX, HANDLING_CLAMP: C.HANDLING_CLAMP, ATTR_MIDPOINT: C.ATTR_MIDPOINT};
globalThis.__E087 = {shareWeights};
// Source patch applied to the assembled game text (anchor must occur exactly once).
export const PATCH_FROM = 'creationPlan.weights:M.handlingWeights(ls[off])';
export const PATCH_TO = "creationPlan.weights:(opt.handleShare==='measured'||opt.e087Probe?globalThis.__E087.shareWeights(ls[off],opt):M.handlingWeights(ls[off]))";
