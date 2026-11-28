"""E-166 §1: nonC 'fta' noise-corrected spread ratio sim/real for each k (same ridge as sim-0.1.1-wing-diag/poss_ridge.py: λ3000, weight = defensive
possessions, per 100; real halves = game id parity on 2025-26 stints, sim halves = seed 20261103 vs 20261104). Record only. cwd = repo root."""
import json, sys
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as sl
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/sim-0.1.2+E166-ft-defense/'
KEYS = ('pts', 'shot', 'ftm', 'fta', 'fga', 'tov')
def real_rows():
    out = {0: [], 1: []}
    for l in open('reports/defense-b1/stints.jsonl', encoding='utf-8'):
        s = json.loads(l); t = s['teams']; h = int(s['id']) & 1
        for k in (0, 1):
            o, p = t[k]['opponent'], t[k]['defensivePossessions']
            if p > 0: out[h].append({'o': t[1 - k]['players'], 'd': t[k]['players'], 'poss': p, 'pts': o['points'], 'shot': 2 * (o['shortM'] + o['midM']) + 3 * o['longM'],
                                     **{q: o[q] for q in ('ftm', 'fta', 'fga', 'tov')}})
    return out
def sim_rows(k):
    out = {}
    for h, s in ((0, 20261103), (1, 20261104)):
        rows = json.load(open(D + f'possk/possk-k{k}-{s}.json', encoding='utf-8'))['rows']
        for r in rows: r['shot'] = 2 * (r['shortM'] + r['midM']) + 3 * r['longM']
        out[h] = [r for r in rows if r['poss'] > 0]
    return out
def fit(rows, lam=3000):
    ids = sorted({i for r in rows for i in r['o'] + r['d']}); ix = {v: k for k, v in enumerate(ids)}; n = len(ids); rr, cc = [], []
    for k, r in enumerate(rows):
        for i in r['o']: rr.append(k); cc.append(ix[i])
        for i in r['d']: rr.append(k); cc.append(n + ix[i])
    X = sp.csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(rows), 2 * n)); W = np.array([r['poss'] for r in rows], float)
    lu = sl.splu((X.T @ sp.diags(W) @ X + lam * sp.eye(2 * n, format='csc')).tocsc()); out = {}
    for q in KEYS:
        num = np.array([r[q] for r in rows], float); y = num / W - num.sum() / W.sum(); b = lu.solve(X.T @ (W * y)) * 100
        out[q] = {i: -b[n + ix[i]] for i in ids}
    return out
x = {p['id']: p for p in json.load(open('reports/sim-0.1.1-oreb-diag/rr-20261101.json', encoding='utf-8'))['real']}
R = real_rows(); FR = {'full': fit(R[0] + R[1]), 0: fit(R[0]), 1: fit(R[1])}
def tsd(F, g, q):
    full = np.array([F['full'][q][i] for i in g]); r = np.corrcoef([F[0][q][i] for i in g], [F[1][q][i] for i in g])[0, 1]
    return full.std() * np.sqrt(max(2 * r / (1 + r), 0)), r
res = {}
for k in (1, 2, 3, 4, 6):
    S = sim_rows(k); FS = {'full': fit(S[0] + S[1]), 0: fit(S[0]), 1: fit(S[1])}
    P = [i for i in x if x[i]['min'] >= 1000 and all(i in F[h]['pts'] for F in (FR, FS) for h in ('full', 0, 1))]
    res[k] = {}
    for grp, pos in (('nonC', ('PG', 'SG', 'SF', 'PF')), ('wing', ('SG', 'SF')), ('C', ('C',))):
        g = [i for i in P if x[i]['pos'] in pos]; res[k][grp] = {'n': len(g)}
        for q in KEYS:
            (a, ra), (b, rb) = tsd(FR, g, q), tsd(FS, g, q)
            res[k][grp][q] = {'real': a, 'sim': b, 'simHalfR': rb, 'ratio': b / a if a else None}
    print(f'k={k} players={len(P)} ' + ' | '.join(f"{grp} fta {res[k][grp]['fta']['ratio']:.2f} ftm {res[k][grp]['ftm']['ratio']:.2f} pts {res[k][grp]['pts']['ratio']:.2f}" for grp in ('nonC', 'wing', 'C')))
r = {k: res[k]['nonC']['fta']['ratio'] for k in res}
cand = sorted(r, key=lambda k: (abs(r[k] - 1), k)); pick = cand[0]
if r[6] < 0.90 and all(r[k] < 0.90 for k in r): pick = 6
print('nonC fta ratio', {k: round(v, 3) for k, v in r.items()}, 'pick k =', pick)
json.dump({'rule': 'nonC fta noise-corrected ratio closest to 1.00, tie -> smaller k; if k=6 still <0.90 use 6', 'ratios': r, 'pick': pick, 'detail': res},
          open(D + 'k-calibration.json', 'w', encoding='utf-8'), indent=1)
