"""E-287 評估（prereg.md 凍結）。python -I -B -X utf8 reports/E287-offdef-align-t/e287_eval.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X = importlib.util.module_from_spec(s); sys.modules['e269_eval'] = X; s.loader.exec_module(X)
P, Q = X.P, X.Q
ORIG = ['2022-23', '2023-24', '2024-25', '2025-26']; FULL = ORIG[:3]; NEXT = Q.NEXT
W = [0.0, 0.25, 0.5, 0.75, 1.0]
K2D = ['Block', 'Steal', 'Interior Defense', 'Perimeter Defense', 'Help Defense IQ']
K2O = ['Three-Point Shot', 'Mid-Range Shot', 'Close Shot', 'Layup', 'Draw Foul', 'Ball Handle', 'Pass Accuracy', 'Pass Vision', 'Pass IQ', 'Shot IQ', 'Offensive Consistency']
NAMED = ['Kevin Durant', 'Fred VanVleet', 'Stephen Curry', 'Victor Wembanyama', 'Rudy Gobert', 'Alex Caruso', 'Amen Thompson', 'Jaren Jackson Jr.',
         'Bam Adebayo', 'Draymond Green', 'Trae Young', 'Nikola Jokić', 'Shai Gilgeous-Alexander', 'Luka Dončić', 'Giannis Antetokounmpo']


def z(v):
    return (v - v.mean()) / v.std()


def epm(ids, s, col):
    _, mp = P.pop_of(s); v = {}
    for r in csv.DictReader(open(Q.EPMDIR / f'epm_{s}.csv', encoding='utf-8-sig')):
        p = int(r['playerId'])
        if float(r['stintPoss']) >= 1000 and p in mp:
            v[p] = float(r[col]) * P.wfun(mp[p])
    return np.array([v.get(int(p), np.nan) for p in ids])


def rho(x, y):
    k = np.isfinite(x) & np.isfinite(y); return float(spearmanr(x[k], y[k])[0]), int(k.sum())


def load(t):
    cur = json.load(open(HERE / f'cur-{t}.json', encoding='utf-8')); T = json.load(open(HERE / f't-{t}.json'))
    ids = [p for p in sorted(cur) if p in T['ownPts100']]
    to = np.array([T['ownPts100'][p] for p in ids]); td = -np.array([T['oppPts100'][p] for p in ids])
    d = {'ids': ids, 'names': [cur[p]['name'] for p in ids], 'pos': [cur[p]['pos'] for p in ids], 'ovr': np.array([cur[p]['ovr'] for p in ids]),
         'cur': {'OFF': np.array([cur[p]['off0'] for p in ids]), 'DEF': np.array([cur[p]['def0'] for p in ids])}, 'T': {'OFF': to, 'DEF': td}}
    d['blend'] = {k: {w: (1 - w) * z(d['cur'][k]) + w * z(d['T'][k]) for w in W} for k in ('OFF', 'DEF')}
    return d


def pick(F, folds, k):
    n = {c: F[c]['n'][k] for c in folds}; tot = sum(n.values()); ok = []
    for w in W:
        d = {c: F[c][k][w] - F[c][k][0.0] for c in folds}
        if sum(n[c] * d[c] for c in folds) / tot >= -0.010 and min(d.values()) >= -0.020:
            ok.append(w)
    return max(ok)


def main():
    if hashlib.sha256((HERE / 'prereg.md').read_bytes()).hexdigest() != (HERE / 'prereg.sha256').read_text().strip():
        print('prereg sha mismatch'); return 1
    D = {t: load(t) for t in ORIG}
    F = {}
    for c in FULL:
        F[c] = {'n': {}}
        for k, col in (('OFF', 'O'), ('DEF', 'D')):
            y = epm(D[c]['ids'], NEXT[c], col)
            F[c][k] = {w: rho(D[c]['blend'][k][w], y)[0] for w in W}; F[c]['n'][k] = rho(D[c]['blend'][k][0.0], y)[1]
    res = {'folds': F, 'combined': {}, 'choice': {}, 'lofo': {}}
    for k in ('OFF', 'DEF'):
        n = {c: F[c]['n'][k] for c in FULL}; tot = sum(n.values())
        res['combined'][k] = {w: sum(n[c] * F[c][k][w] for c in FULL) / tot for w in W}
        res['choice'][k] = pick(F, FULL, k)
        res['lofo'][k] = {}
        for out in FULL:
            w = pick(F, [c for c in FULL if c != out], k)
            res['lofo'][k][out] = {'w': w, 'heldoutDelta': F[out][k][w] - F[out][k][0.0]}
    # 2K27（2025-26）
    k2 = {}
    for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8')):
        try:
            k2[P.norm(r['name'])] = (np.mean([float(r[a]) for a in K2O]), np.mean([float(r[a]) for a in K2D]))
        except ValueError:
            pass
    d = D['2025-26']
    y2 = {k: np.array([k2.get(P.norm(nm), (np.nan, np.nan))[j] for nm in d['names']]) for j, k in enumerate(('OFF', 'DEF'))}
    res['k2'] = {k: {w: rho(d['blend'][k][w], y2[k])[0] for w in W} for k in ('OFF', 'DEF')}
    res['k2_n'] = int(np.isfinite(y2['DEF']).sum())
    res['vsT'] = {k: {w: float(np.mean([spearmanr(D[c]['blend'][k][w], D[c]['T'][k])[0] for c in ORIG])) for w in W} for k in ('OFF', 'DEF')}
    # 例子（2025-26）
    ex = {}
    for k in ('OFF', 'DEF'):
        ex[k] = {}
        for w in W:
            v = d['blend'][k][w]; rk = {nm: int((v > v[i]).sum() + 1) for i, nm in enumerate(d['names'])}
            ex[k][w] = {'named': {nm: rk.get(nm) for nm in NAMED}, 'top10': [d['names'][i] for i in np.argsort(-v)[:10]]}
    bigs = [d['names'][i] for i in np.argsort(-d['ovr']) if d['pos'][i] == 'C'][:10]
    v0 = d['blend']['DEF']
    ex['bigsDEF'] = {nm: {w: int((v0[w] > v0[w][d['names'].index(nm)]).sum() + 1) for w in W} for nm in bigs}
    res['examples'] = ex; res['n_pop'] = {t: len(D[t]['ids']) for t in ORIG}
    json.dump(res, open(HERE / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    for k in ('OFF', 'DEF'):
        print('==', k, 'choice', res['choice'][k], 'combined', {w: round(v, 4) for w, v in res['combined'][k].items()})
        for c in FULL: print('  ', c, {w: round(F[c][k][w], 4) for w in W}, 'n', F[c]['n'][k])
        print('   lofo', res['lofo'][k]); print('   2K', {w: round(v, 3) for w, v in res['k2'][k].items()}, ' vsT', {w: round(v, 3) for w, v in res['vsT'][k].items()})
        for w in W: print('   w', w, ex[k][w]['named'], ex[k][w]['top10'][:10])
    print('bigs', ex['bigsDEF'], 'k2n', res['k2_n'], res['n_pop'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
