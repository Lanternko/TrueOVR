// F-130 diagnostic: E-140 rr-core playSeed copy with extra RECORDING only (no probability / rng change).
// Per team (index in x.opponents), summed over its games in one seed: games, poss, team FGA, FT attempts by trigger kind,
// and per-player (playerId) FGA / FTA split into shooting+andOne vs other. Arm = B2 (k=2, sim 0.1.3), a=1 (identical to E-166 k=2).
// Runs on 5090 as ~/e184/reports/E184/*.mjs (imports below resolve there).
import {makeRunner, loadX, ARMS} from './core184.mjs';
import {opponentTeam, options} from '../player-impact-v29/benchmark.mjs';
import {allPairs} from '../E140-foul-on-recal/rr-core.mjs';
export {makeRunner, loadX, ARMS, allPairs};
export function playSeed({run, src}, x, seed, pairs, tally) {
  const records = [];
  for (const [a, b] of pairs) {
    const phase = (seed + a + b) & 1, swap = ((seed >>> 1) + a) & 1;
    const ta = opponentTeam(x, x.opponents[a], src.capMinutes, phase), tb = opponentTeam(x, x.opponents[b], src.capMinutes, phase);
    const gseed = (seed + Math.imul(a * 30 + b, 1000003)) >>> 0;
    const teams = swap ? [tb.team, ta.team] : [ta.team, tb.team], schedules = swap ? [tb.schedule, ta.schedule] : [ta.schedule, tb.schedule];
    const ft = [{}, {}], pl = [{}, {}], pc = [0, 0]; let last = 'none';
    const eventObserver = e => {
      const t = e.type, s = e.off;
      if (t === 'POSSESSION') pc[s]++;
      else if (t === 'FOUL') last = e.kind;
      else if (t === 'FTM' || t === 'FTX') {
        const kind = e.technical ? 'technical' : last;
        ft[s][kind] = (ft[s][kind] || 0) + 1;
        const o = pl[s][e.player] ??= {}; o[kind] = (o[kind] || 0) + 1;
      }
    };
    const g = run(...teams, {...options(x, gseed, schedules), eventObserver});
    if (g.gameSeconds !== 2880 || !g.complete) throw Error('Incomplete game');
    const ia = swap ? 1 : 0, ib = 1 - ia, idx = [a, b];
    const sides = [[g.playersA, teams[0]], [g.playersB, teams[1]]];
    const ids = swap ? [b, a] : [a, b]; // team index of game side 0 / 1
    for (let s = 0; s < 2; s++) {
      const t = ids[s], [box, team] = sides[s];
      const T = tally[t] ??= {games: 0, poss: 0, fga: 0, oreb: 0, fta: 0, ft: {}, players: {}};
      T.games++; T.poss += pc[s];
      for (const [k, v] of Object.entries(ft[s])) { T.ft[k] = (T.ft[k] || 0) + v; T.fta += v; }
      box.forEach((p, i) => {
        T.fga += p.fga; T.oreb += p.oreb;
        const id = team.roster[i].playerId; if (!(id > 0)) return;
        const P = T.players[id] ??= {name: team.roster[i].name, ftr: team.roster[i].shotProfile?.freeThrowsPerAttempt ?? null, fga: 0, fta: 0, ft: {}};
        P.fga += p.fga; P.fta += p.fta;
        for (const [k, v] of Object.entries(pl[s][i] || {})) P.ft[k] = (P.ft[k] || 0) + v;
      });
    }
    records.push({a, b, ptsA: [g.scoreA, g.scoreB][ia], ptsB: [g.scoreA, g.scoreB][ib], ftaA: ft[ia] ? Object.values(ft[ia]).reduce((u, v) => u + v, 0) : 0, ftaB: Object.values(ft[ib]).reduce((u, v) => u + v, 0)});
  }
  return records;
}
