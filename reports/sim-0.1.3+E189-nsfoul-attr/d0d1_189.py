"""E-189 report-only D0 (center FT-defense denoised spread ratio, F-129 definition) and D1 (non-shooting FT block, center ratio). cwd = repo root.
sim halves = two seeds (disjoint pairs of the 32 judgement seeds), real halves = game-id parity; reuses f129lib / d1.py definitions unchanged (d1 source exec'd with sim rows swapped)."""
import sys, json, glob, re, numpy as np; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from f129lib import *
D = 'reports/sim-0.1.3+E189-nsfoul-attr/'; J = D + 'out/jud/'; SEEDS = list(range(20261210, 20261242)); NP = int(sys.argv[1]) if len(sys.argv) > 1 else 8
x = players(); R = real_rows(); Rd = {h: Design(R[h]) for h in (0, 1)}; Rf = Design(R[0] + R[1])
def coef(Dg, rows, q): return dict(zip(Dg.ids, Dg.fit(np.array([r[q] for r in rows], float))[0]))
FR = {'full': coef(Rf, R[0] + R[1], 'fta'), 0: coef(Rd[0], R[0], 'fta'), 1: coef(Rd[1], R[1], 'fta')}
def load(tag, s): return sim_load(J + f'{tag}-{s}.json')
out = {'d0': {}, 'd1': {}}
pairs = [(SEEDS[2 * k], SEEDS[2 * k + 1]) for k in range(NP)]
for tag in ('base', 'odd', 'even'):
    res = []
    for sa, sb in pairs:
        S = {0: load(tag, sa), 1: load(tag, sb)}; Sd = {h: Design(S[h]) for h in (0, 1)}; Sf = Design(S[0] + S[1])
        FS = {'full': coef(Sf, S[0] + S[1], 'fta'), 0: coef(Sd[0], S[0], 'fta'), 1: coef(Sd[1], S[1], 'fta')}
        P = [i for i in x if x[i]['min'] >= 1000 and all(i in F[h] for F in (FR, FS) for h in ('full', 0, 1))]; r = {'n': len(P)}
        for grp, pos in GRP:
            g = [i for i in P if x[i]['pos'] in pos]; f = lambda F: tsd(np.array([F['full'][i] for i in g]), [F[0][i] for i in g], [F[1][i] for i in g])
            (a, _), (b, _) = f(FR), f(FS); r[grp] = {'n': len(g), 'real': a, 'sim': b, 'ratio': b / a}
        res.append(r)
    out['d0'][tag] = {g: {'ratio_mean': float(np.mean([r[g]['ratio'] for r in res])), 'ratio_sd': float(np.std([r[g]['ratio'] for r in res])), 'sim_mean': float(np.mean([r[g]['sim'] for r in res])), 'real': res[0][g]['real'], 'n': res[0][g]['n']} for g, _ in GRP}
    print('D0', tag, {g: round(v['ratio_mean'], 3) for g, v in out['d0'][tag].items()}); sys.stdout.flush()
# D1: exec d1.py's class/func definitions with our rows
src = open('reports/F129-center-ft-defense-diag/d1.py', encoding='utf-8').read(); body = src[src.index('def zsum'):src.index('def run')]
LD = None; LAM = 3000; ZONES = ('short', 'mid', 'long'); RD = json.load(open('reports/F129-center-ft-defense-diag/real_d1_rows.json', encoding='utf-8')); RR = {0: RD['0'], 1: RD['1']}
SIMD = {t: {s: load(t, s) for pr in pairs for s in pr} for t in ('base', 'odd', 'even')}
ids = sorted({i for h in RR for r in RR[h] for i in r['o'] + r['d']} | {i for t in SIMD for s in SIMD[t] for r in SIMD[t][s] for i in r['o'] + r['d']}); ix = {v: k for k, v in enumerate(ids)}; n = len(ids)
exec(body)
pres = [set(i for r in RR[h] for i in r['o'] + r['d']) for h in (0, 1)] + [set(i for r in SIMD[t][s] for i in r['o'] + r['d']) for t in SIMD for s in SIMD[t]]
P = [i for i in x if x[i]['min'] >= 1000 and all(i in p for p in pres)]; pidx = {g: np.array([ix[i] for i in P if x[i]['pos'] in pos]) for g, pos in GRP}
rb = rbar_of([RR[0], RR[1]]); H = [Half(RR[0], rb), Half(RR[1], rb)]; real = analyse(H[0], H[1], None, pidx)
out['d1']['n_players'] = len(P); out['d1']['real'] = {g: {'tsd': v['tsd'], 'var_nsh': v['var']['nsh'], 'var_sh': v['var']['sh'], 'var_tot': v['tsd'] ** 2} for g, v in real.items()}
for t in SIMD:
    L = []
    for sa, sb in pairs:
        rbs = rbar_of([SIMD[t][sa], SIMD[t][sb]]); hs = [Half(SIMD[t][sa], rbs), Half(SIMD[t][sb], rbs)]; L.append(analyse(hs[0], hs[1], None, pidx))
    out['d1'][t] = {g: {'tsd': float(np.mean([l[g]['tsd'] for l in L])), 'var_nsh': float(np.mean([l[g]['var']['nsh'] for l in L])), 'var_sh': float(np.mean([l[g]['var']['sh'] for l in L]))} for g, _ in GRP}
    for g, _ in GRP: out['d1'][t][g]['nsh_sd_ratio'] = float(np.sqrt(max(out['d1'][t][g]['var_nsh'], 0) / max(real[g]['var']['nsh'] * real[g]['tsd'] ** 2, 1e-12)))
    print('D1', t, {g: (round(v['nsh_sd_ratio'], 3), round(v['var_nsh'], 4)) for g, v in out['d1'][t].items()}); sys.stdout.flush()
print('real', {g: (round(v['var_nsh'], 4), round(v['var_tot'], 4)) for g, v in out['d1']['real'].items()})
json.dump(out, open(D + 'd0d1.json', 'w', encoding='utf-8'), indent=1)
