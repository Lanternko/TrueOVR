"""F-129 D0 step 1: reproduce k=2 ratios (nonC 1.04 / wing 1.13 / C 0.56) with f129lib on the existing ledgers possk-k2-20261103/04 (and judge seeds). cwd = repo root."""
import sys, json; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from f129lib import *
x = players(); R = real_rows(); out = {}
Rd = {h: Design(R[h]) for h in (0, 1)}; Rf = Design(R[0] + R[1])
def coef(D, rows, q): return dict(zip(D.ids, D.fit(np.array([r[q] for r in rows], float))[0]))
FR = {'full': coef(Rf, R[0] + R[1], 'fta'), 0: coef(Rd[0], R[0], 'fta'), 1: coef(Rd[1], R[1], 'fta')}
def ratios(path0, path1, tag):
    S = {0: sim_load(path0), 1: sim_load(path1)}
    for h in S:
        for r in S[h]: r['fta'] = r['fta']
    Sd = {h: Design(S[h]) for h in (0, 1)}; Sf = Design(S[0] + S[1])
    FS = {'full': coef(Sf, S[0] + S[1], 'fta'), 0: coef(Sd[0], S[0], 'fta'), 1: coef(Sd[1], S[1], 'fta')}
    P = [i for i in x if x[i]['min'] >= 1000 and all(i in F[h] for F in (FR, FS) for h in ('full', 0, 1))]
    res = {'players': len(P)}
    for grp, pos in GRP:
        g = [i for i in P if x[i]['pos'] in pos]
        f = lambda F: tsd(np.array([F['full'][i] for i in g]), [F[0][i] for i in g], [F[1][i] for i in g])
        (a, ra), (b, rb) = f(FR), f(FS); res[grp] = {'n': len(g), 'real': a, 'realHalfR': ra, 'sim': b, 'simHalfR': rb, 'ratio': b / a}
    print(tag, res['players'], ' | '.join(f"{g} n={res[g]['n']} ratio {res[g]['ratio']:.3f}" for g, _ in GRP)); return res
out['k2_default'] = ratios(E166 + 'possk/possk-k2-20261103.json', E166 + 'possk/possk-k2-20261104.json', 'k2 ledgers   ')
out['judge_k2'] = ratios(E166 + 'possk/possk-judge-k2-20261028.json', E166 + 'possk/possk-judge-k2-20261029.json', 'judge k2     ')
json.dump(out, open('reports/F129-center-ft-defense-diag/d0_repro.json', 'w', encoding='utf-8'), indent=1)
