// E-166 §1: per lineup-pair possession ledger (same rows as sim-0.1.1-wing-diag/poss-sim.mjs) under beta*k. Record only.
// node reports/E166/possk.mjs --k 2 --seed 20261103 --out possk-k2-20261103.json   (cwd = tree root)
import fs from 'node:fs';
const {makeRunner, loadX, arg} = await import('./core166.mjs');
const {opponentTeam, options} = await import('../player-impact-v29/benchmark.mjs');
const {allPairs} = await import('../E140-foul-on-recal/rr-core.mjs');
const k = +arg('k', 1), seed = +arg('seed'), out = new URL('./' + arg('out'), import.meta.url);
const r = await makeRunner({k}), {x} = await loadX(), pid = p => p.playerId ?? p.id;
const R = new Map(), chk = {fg: 0, mismatch: 0, subs: 0, games: 0, k, seed};
const blank = (o, d) => ({o, d, poss: 0, pts: 0, fga: 0, fgm: 0, shortA: 0, shortM: 0, midA: 0, midM: 0, longA: 0, longM: 0, fta: 0, ftm: 0, tov: 0, liveTov: 0, clockTov: 0, oreb: 0, dreb: 0});
for (const [a, b] of allPairs(x.opponents.length)) {
  const phase = (seed + a + b) & 1, ta = opponentTeam(x, x.opponents[a], r.src.capMinutes, phase), tb = opponentTeam(x, x.opponents[b], r.src.capMinutes, phase);
  const gseed = (seed + Math.imul(a * 30 + b, 1000003)) >>> 0, roster = [ta.team.roster.map(pid), tb.team.roster.map(pid)], L = [roster[0].slice(0, 5), roster[1].slice(0, 5)];
  const row = off => { const key = L[off].join(',') + '|' + L[1 - off].join(','); let q = R.get(key); if (!q) R.set(key, q = blank(L[off].slice(), L[1 - off].slice())); return q; };
  const g = r.run(ta.team, tb.team, {...options(x, gseed, [ta.schedule, tb.schedule]),
    onCourtObserver: e => { if (e.type !== 'FGM' && e.type !== 'FGX') return; chk.fg++;
      for (const s of [0, 1]) { const t = e.teams[s].lineup; if (t.length !== 5 || t.some(i => !L[s].includes(i))) chk.mismatch++; } },
    eventObserver: e => { const off = e.off;
      switch (e.type) {
        case 'SUBSTITUTION': { chk.subs++; const inn = roster[off][e.player], o = roster[off][e.out], j = L[off].indexOf(o); if (j < 0 || L[off].includes(inn)) throw Error('bad substitution'); L[off][j] = inn; break; }
        case 'POSSESSION': row(off).poss++; break;
        case 'FGM': case 'FGX': { const q = row(off), m = +(e.type === 'FGM'), z = e.zone === 'short' ? 'short' : e.zone === 'long' ? 'long' : 'mid'; q.fga++; q.fgm += m; q[z + 'A']++; q[z + 'M'] += m; q.pts += m * e.points; break; }
        case 'FTM': case 'FTX': { const q = row(off); q.fta++; if (e.type === 'FTM') { q.ftm++; q.pts++; } break; }
        case 'TOV': row(off).tov++; break;
        case 'SHOT_CLOCK': { const q = row(off); q.tov++; q.clockTov++; break; }
        case 'STEAL': { const q = row(1 - off); q.tov++; q.liveTov++; break; }
        case 'OREB': row(off).oreb++; break;
        case 'DREB': row(1 - off).dreb++; break;
      } }});
  if (!g.complete) throw Error('incomplete'); chk.games++;
}
fs.writeFileSync(out, JSON.stringify({chk, rows: [...R.values()]}));
console.log('done', JSON.stringify(chk));
