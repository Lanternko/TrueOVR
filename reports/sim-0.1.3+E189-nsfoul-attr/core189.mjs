// E-189 harness: sim 0.1.3 round robin (E-140 playSeed pairing/seeding unchanged) + per-lineup ledger (F-129 possk129 rows, plus non-shooting foul counts).
// makeRunner({c,pace,attr,base}): attr = null (flag off = sim 0.1.3 when c=C013,pace=P013) or 'odd'|'even' (gamma file built on that half).
import fs from 'node:fs';
import {impactEngine} from './engine-e189.mjs';
import {loadX} from '../E140-foul-on-recal/winimp-core-e140.mjs';
import {source, opponentTeam, options} from '../player-impact-v29/benchmark.mjs';
export {loadX};
export const C013 = -0.05625, P013 = 0.998125, K013 = 2;
export const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
export function loadAttr(name) { return name ? JSON.parse(fs.readFileSync(new URL(`./attr-${name}.json`, import.meta.url), 'utf8')).gamma : null; }
export async function makeRunner({c = C013, pace = P013, attr = null, base = 1} = {}) {
  // benchmark options() == sim 0.1.3 already. Only stamp c / pace when they differ from the 0.1.3 values (pace given as absolute multiplier, 0.998125 = 0.1.3).
  const run = await impactEngine('rotation-space', {game: true, c: c === C013 ? undefined : c, pace: pace === P013 ? undefined : pace / P013, nsAttr: loadAttr(attr), nsBase: base});
  return {src: source(), run};
}
const pid = p => p.playerId ?? p.id;
const blank = (o, d) => ({o, d, poss: 0, pts: 0, fga: 0, fgm: 0, shortA: 0, shortM: 0, midA: 0, midM: 0, longA: 0, longM: 0, fta: 0, ftm: 0, tov: 0, liveTov: 0, clockTov: 0, oreb: 0, dreb: 0, sf: {}, sfa: {}, nsf: {}, nsc: {}, oth: 0});
const add = (o, key, n = 1) => { o[key] = (o[key] || 0) + n; };
const blankC = () => ({oreb: 0, dreb: 0, toreb: 0, tdreb: 0, sc: 0, rimA: 0, rimM: 0, poss: 0, fs: 0, fa: 0, fta: 0, ftm: 0, nsFoul: 0, nsFt: 0});
// One seed, all 435 pairs. Returns {records (E-140 fields + nsFoul/nsFt), rows (lineup ledger, F-129 format + nsc)}.
export function playSeedLedger({run, src}, x, seed, pairs, noSwap = false) {
  const records = [], R = new Map();
  for (const [a, b] of pairs) {
    const phase = (seed + a + b) & 1, swap = noSwap ? 0 : ((seed >>> 1) + a) & 1;
    const ta = opponentTeam(x, x.opponents[a], src.capMinutes, phase), tb = opponentTeam(x, x.opponents[b], src.capMinutes, phase);
    const gseed = (seed + Math.imul(a * 30 + b, 1000003)) >>> 0;
    const teams = swap ? [tb.team, ta.team] : [ta.team, tb.team], schedules = swap ? [tb.schedule, ta.schedule] : [ta.schedule, tb.schedule];
    const roster = teams.map(t => t.roster.map(pid)), L = [roster[0].slice(0, 5), roster[1].slice(0, 5)];
    const row = off => { const key = L[off].join(',') + '|' + L[1 - off].join(','); let q = R.get(key); if (!q) R.set(key, q = blank(L[off].slice(), L[1 - off].slice())); return q; };
    const c = [blankC(), blankC()]; let scFlag = [false, false], lastZ = [null, null], fz = null, pend = null;
    const eventObserver = e => {
      const t = e.type, s = e.off;
      switch (t) {
        case 'SUBSTITUTION': { const inn = roster[s][e.player], o = roster[s][e.out], j = L[s].indexOf(o); if (j < 0 || L[s].includes(inn)) throw Error('bad substitution'); L[s][j] = inn; break; }
        case 'POSSESSION': scFlag = [false, false]; c[s].poss++; row(s).poss++; break;
        case 'OREB': case 'TEAM_OREB': c[s].oreb++; if (t === 'TEAM_OREB') c[s].toreb++; scFlag[s] = true; if (t === 'OREB') row(s).oreb++; break;
        case 'DREB': case 'TEAM_DREB': c[s].dreb++; if (t === 'TEAM_DREB') c[s].tdreb++; if (t === 'DREB') row(1 - s).dreb++; break;
        case 'FOULZONE': fz = e.zone === 'short' ? 'short' : e.zone === 'long' ? 'long' : 'mid'; break;
        case 'FOUL': { const q = row(1 - s), fouler = roster[s][e.player], kind = e.kind;
          if (kind === 'shooting') { c[s].fs++; add(q.sfa, fz); pend = {q, key: fouler + '|' + fz, sf: true}; fz = null; }
          else if (kind === 'andOne') { c[s].fa++; pend = {q, key: fouler + '|' + lastZ[1 - s], sf: true}; }
          else { if (kind === 'nonShooting') { c[s].nsFoul++; add(q.nsc, String(fouler)); } pend = {q, key: String(fouler), sf: false, ns: kind === 'nonShooting'}; }
          break; }
        case 'FTM': case 'FTX': { const q = row(s); q.fta++; c[s].fta++;
          if (e.technical || !pend) q.oth++; else if (pend.sf) add(pend.q.sf, pend.key); else { add(pend.q.nsf, pend.key); if (pend.ns) c[s].nsFt++; }
          if (t === 'FTM') { q.ftm++; q.pts++; c[s].ftm++; if (scFlag[s]) c[s].sc += 1; } break; }
        case 'FGM': case 'FGX': { const q = row(s), m = +(t === 'FGM'), z = e.zone === 'short' ? 'short' : e.zone === 'long' ? 'long' : 'mid'; lastZ[s] = z;
          q.fga++; q.fgm += m; q[z + 'A']++; q[z + 'M'] += m; q.pts += m * e.points;
          if (z === 'short') { c[s].rimA++; if (m) c[s].rimM++; } if (m && scFlag[s]) c[s].sc += e.points; break; }
        case 'TOV': row(s).tov++; break;
        case 'SHOT_CLOCK': { const q = row(s); q.tov++; q.clockTov++; break; }
        case 'STEAL': { const q = row(1 - s); q.tov++; q.liveTov++; break; }
      }
    };
    const g = run(...teams, {...options(x, gseed, schedules), eventObserver});
    if (g.gameSeconds !== 2880 || !g.complete) throw Error('Incomplete game');
    const ia = swap ? 1 : 0, ib = 1 - ia, sc = [g.scoreA, g.scoreB];
    records.push({seed, a, b, ptsA: sc[ia], ptsB: sc[ib], possA: c[ia].poss, possB: c[ib].poss, scA: c[ia].sc, scB: c[ib].sc,
      foulShootA: c[ia].fs, foulShootB: c[ib].fs, foulAndA: c[ia].fa, foulAndB: c[ib].fa, ftaA: c[ia].fta, ftaB: c[ib].fta, ftmA: c[ia].ftm, ftmB: c[ib].ftm,
      nsFoulA: c[ia].nsFoul, nsFoulB: c[ib].nsFoul, nsFtA: c[ia].nsFt, nsFtB: c[ib].nsFt, rimAttA: c[ia].rimA, rimAttB: c[ib].rimA,
      orebA: c[ia].oreb, orebB: c[ib].oreb, drebA: c[ia].dreb, drebB: c[ib].dreb});
  }
  return {seed, records, rows: [...R.values()]};
}
export const allPairs = n => { const p = []; for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) p.push([a, b]); return p; };
