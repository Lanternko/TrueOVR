// E-224 §3：梯度隊（B5）與拉平梯度隊（A5）的建構。無可調參數。引擎與屬性表＝E-208 的 lib（setup 回傳的 team() 套變體差值）。
import fs from 'node:fs';
export const MINS = [36, 36, 34, 32, 30, 26, 22, 14, 10];
export const O = ['PG', 'SG', 'SF', 'PF', 'C'];
// 遞迴等權平均（同 card-0.1.2+E065 的 averageProfiles）：數字取平均；陣列、null、非物件取第一個；物件逐鍵平均。
export function avgProfiles(ps) {
  const f = ps[0];
  if (typeof f === 'number') return ps.reduce((a, v) => a + v, 0) / ps.length;
  if (Array.isArray(f) || f === null || typeof f !== 'object') return f;
  const o = {};
  for (const k of Object.keys(f)) o[k] = avgProfiles(ps.map(p => p?.[k]).map((v, i) => v === undefined ? f[k] : v));
  return o;
}
export function readLadder(key) {
  return JSON.parse(fs.readFileSync(new URL(`./work/ladder-${key}.json`, import.meta.url), 'utf8'));
}
// 回傳 {teams:[{name, slots:[{k,pos,target,pids,names,ovrs,mismatch}], roster:[profile…]}], notes:{short:[…], noProfile:[…]}}
export function buildOpponents(L, lad, mode, season) {
  const byId = new Map(L.x.players.map(p => [p.playerId, p]));
  const notes = {short: [], noProfile: [], posMismatch: []};
  const cand = lad.candidates.filter(c => { if (byId.has(c.pid)) return true; notes.noProfile.push(c.pid); return false; });
  const teams = [];
  for (let j = 0; j < 5; j++) {
    const slots = [], roster = [];
    for (let k = 1; k <= 9; k++) {
      const pos = O[(j + (k - 1)) % 5];
      const target = mode === 'A5' ? lad.flat : lad.ladder[k - 1];
      const pool = cand.filter(c => c.pos === pos).sort((a, b) => Math.abs(a.ovr - target) - Math.abs(b.ovr - target) || b.min - a.min || a.pid - b.pid);
      const pick = pool.slice(0, 3);
      if (pick.length < 3) notes.short.push({team: j, k, pos, n: pick.length});
      const profs = pick.map(c => L.team('tmp', [[c.pid, 1]]).roster[0]);      // 變體差值已套用
      const a = avgProfiles(profs);
      const nearest = profs[0];
      for (const key of Object.keys(nearest)) if (typeof nearest[key] !== 'number' && (typeof nearest[key] !== 'object' || nearest[key] === null)) a[key] = nearest[key];   // 非數值欄位取最近者
      Object.assign(a, {playerId: -(1 + j * 9 + (k - 1)), name: `E224-${mode}-T${j}-S${k}-${pos}`, targetMinutes: MINS[k - 1], injured: false});
      const mm = pick.filter(c => byId.get(c.pid).courtPosition !== pos).map(c => c.pid);
      if (mm.length) notes.posMismatch.push({team: j, k, pos, pids: mm});
      slots.push({k, pos, target, pids: pick.map(c => c.pid), names: pick.map(c => c.name), ovrs: pick.map(c => c.ovr), courtPosition: a.courtPosition});
      roster.push(a);
    }
    teams.push({name: `${mode}-T${j}`, season, roster, slots});
  }
  return {teams, notes};
}
