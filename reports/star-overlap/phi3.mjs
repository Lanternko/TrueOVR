import fs from 'node:fs';
import {loadX, makeRunner} from 'file:///D:/Projects/CODING/basketball-autochess/reports/E120-foul-defense/winimp-core-e120.mjs';
import {options} from 'file:///D:/Projects/CODING/basketball-autochess/reports/player-impact-v29/benchmark.mjs';
const D = JSON.parse(fs.readFileSync(new URL('./phi_d.json', import.meta.url)));
const {x, xAvg} = await loadX(); const {run} = await makeRunner();
const byId = new Map(x.players.map(p => [p.playerId, p])); const clamp = v => Math.max(0, Math.min(120, v));
const P = pid => { if (pid < 0) return {...xAvg.profiles[2], playerId: pid}; const p = {...byId.get(pid)}; const d = D[pid]; if (d) for (const a in d) p[a] = clamp(p[a] + d[a]); return p; };
const av = {name: 'avg', season: '2025-26', roster: xAvg.profiles.concat(xAvg.profiles).map((p, i) => ({...p, playerId: -100 - i, targetMinutes: 24, injured: false}))};
const PHI = [[1630178,38.4],[1627759,32.1],[1642845,29.2],[203954,25.7],[1629014,25.2],[203484,24.8],[2544,24.4],[1629731,20.3],[1641737,14.4],[1631133,5.6]];
const rate = keep => { const k = 240 / PHI.reduce((a, e) => a + e[1], 0); let m = 0;
  for (let s = 0; s < 200; s++) { const t = {name: 't', season: '2025-26', roster: PHI.map(([pid, mm], i) => ({...P(keep.includes(pid) ? pid : -1 - i), targetMinutes: mm * k, injured: false}))}, sw = s & 1;
    const g = run(sw ? av : t, sw ? t : av, options(x, 1000 + s, undefined)); m += sw ? g.scoreB - g.scoreA : g.scoreA - g.scoreB; }
  return m / 200; };
const base = rate([]); console.log('全平均', base.toFixed(1));
const names = {1630178: 'Maxey', 1627759: 'Brown', 203954: 'Embiid', 2544: 'LeBron'}; let sum = 0;
for (const pid of Object.keys(names).map(Number)) { const g = rate([pid]) - base; sum += g; console.log('只放', names[pid], '+' + g.toFixed(1)); }
const all4 = rate(Object.keys(names).map(Number)) - base; console.log('單人加總 +' + sum.toFixed(1), ' 四人一起 +' + all4.toFixed(1));
