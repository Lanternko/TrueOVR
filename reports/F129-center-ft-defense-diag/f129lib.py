"""F-129 shared code. Same ridge/spread definition as reports/sim-0.1.2+E166-ft-defense/ridge_k.py (λ3000, weight = defensive possessions, per 100,
noise-corrected spread tsd = full.std*sqrt(2r/(1+r)); real halves = game id parity, sim halves = two seeds). Extra: row multipliers (bootstrap) and a
general response vector. cwd = repo root. Local, light; no subprocess."""
import json, sys
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as sl
sys.stdout.reconfigure(encoding='utf-8')
E166 = 'reports/sim-0.1.2+E166-ft-defense/'
GRP = (('nonC', ('PG', 'SG', 'SF', 'PF')), ('wing', ('SG', 'SF')), ('C', ('C',)))
def real_rows():
    """returns {0:[...],1:[...]} rows with game id 'gid' and per-row dict"""
    out = {0: [], 1: []}
    for l in open('reports/defense-b1/stints.jsonl', encoding='utf-8'):
        s = json.loads(l); t = s['teams']; h = int(s['id']) & 1
        for k in (0, 1):
            o, p = t[k]['opponent'], t[k]['defensivePossessions']
            if p > 0: out[h].append({'o': t[1 - k]['players'], 'd': t[k]['players'], 'poss': p, 'gid': s['id'], **{q: o[q] for q in ('ftm', 'fta', 'fga', 'pts' if 'pts' in o else 'points')}, 'pts': o['points'],
                                     'shortA': o.get('shortA', 0), 'midA': o.get('midA', 0), 'longA': o.get('longA', 0)})
    return out
def sim_load(path):
    return [r for r in json.load(open(path, encoding='utf-8'))['rows'] if r['poss'] > 0]
class Design:
    """sparse design for a list of rows; fit(resp, mult) -> {player: -defense coef} per 100"""
    def __init__(s, rows):
        s.rows = rows; s.ids = sorted({i for r in rows for i in r['o'] + r['d']}); s.ix = {v: k for k, v in enumerate(s.ids)}; n = s.n = len(s.ids); rr, cc = [], []
        for k, r in enumerate(rows):
            for i in r['o']: rr.append(k); cc.append(s.ix[i])
            for i in r['d']: rr.append(k); cc.append(n + s.ix[i])
        s.X = sp.csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(rows), 2 * n)); s.XT = s.X.T.tocsr(); s.P = np.array([r['poss'] for r in rows], float)
    def fit(s, nums, mult=None, lam=3000):
        W = s.P if mult is None else s.P * mult
        lu = sl.splu((s.XT @ sp.diags(W) @ s.X + lam * sp.eye(2 * s.n, format='csc')).tocsc()); out = []
        for num in (nums if isinstance(nums, list) else [nums]):
            nn = num if mult is None else num * mult
            y = num / s.P - nn.sum() / W.sum(); b = lu.solve(s.XT @ (W * y)) * 100; out.append(-b[s.n:])
        return out
def tsd(full, ha, hb):
    r = np.corrcoef(ha, hb)[0, 1]; return full.std() * np.sqrt(max(2 * r / (1 + r), 0)), r
def players():
    return {p['id']: p for p in json.load(open('reports/sim-0.1.1-oreb-diag/rr-20261101.json', encoding='utf-8'))['real']}
