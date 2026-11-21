"""E-276 §9 診斷。python -I -B -X utf8 reports/E276-def-stl-blk-defl/e276_d13.py"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location('e276_d12', HERE / 'e276_d12.py')
G = importlib.util.module_from_spec(s); sys.modules['e276_d12'] = G; s.loader.exec_module(G)
W, Q, M, X, P, sp = G.W, G.Q, G.M, G.X, G.P, G.sp
COMP, CARD = G.COMP, G.CARD


def main():
    S = {t: G.season(t) for t in CARD}
    for t in CARD:
        e = S[t]; R = Q.rows(t, e['ids'])
        card = [r for r in csv.DictReader(open(X.HERE / f'ranking-A0-{t}.csv', encoding='utf-8-sig')) if float(r['MIN']) >= 500]
        mub = np.mean([float(r['defenseBonus']) for r in card])
        e['bon'] = np.array([float(r['defenseBonus']) - mub for r in R])
    out = {'folds': {}}
    for t, u in Q.FOLDS:
        tr = [S[q] for q in CARD if q <= t]
        def fit(fx):
            XX = np.vstack([fx(e) for e in tr]); yy = np.concatenate([e['yt'] for e in tr]); k = np.isfinite(yy)
            return np.linalg.lstsq(XX[k], yy[k], rcond=None)[0]
        Xc = lambda e: np.c_[np.ones(len(e['ids'])), e['base'], np.column_stack([e['Z'][c] for c in COMP])]
        Xn = lambda e: np.c_[np.ones(len(e['ids'])), e['base'] - e['bon'], np.column_stack([e['Z'][c] for c in COMP])]
        b, bn = fit(Xc), fit(Xn)
        e = S[t]; ids = e['ids']
        d2 = Q.d2_of(t, ids)
        rt = M.rapm_raw(t, 1.0)
        d4 = np.array([rt[p][0] if p in rt and rt[p][1] >= 1000 else np.nan for p in ids])
        popt, _ = P.pop_of(t); popu, mp = P.pop_of(u); ru = M.rapm_raw(u, 1.0)
        yD = np.array([ru[p][0] * P.wfun(mp[p]) if p in ru and ru[p][1] >= 1000 and p in mp else np.nan for p in ids])
        com = np.isfinite(d2) & np.isfinite(d4) & np.isfinite(yD)
        mv = np.array([p in popt and p in popu and popt[p]['team'] != popu[p]['team'] for p in ids]) & com
        A = {'D0': e['d']['def'], 'D0nb': e['d']['def'] - e['bon'], 'D12': Xc(e) @ b, 'D12nb': Xn(e) @ bn, 'D4': d4}
        out['folds'][t] = {'n': int(com.sum()), 'n_move': int(mv.sum()),
                           'rho': {a: sp(v[com], yD[com]) for a, v in A.items()},
                           'rho_move': {a: sp(v[mv], yD[mv]) for a, v in A.items()}}
    for key, nk in (('rho', 'n'), ('rho_move', 'n_move')):
        ns = sum(f[nk] for f in out['folds'].values())
        out['combined_' + key] = {a: float(sum(f[key][a] * f[nk] for f in out['folds'].values()) / ns) for a in out['folds']['2022-23'][key]}
    (HERE / 'results-d13.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for t, f in out['folds'].items():
        print(t, f['n'], f['n_move'], {a: round(v, 3) for a, v in f['rho'].items()}, 'move', {a: round(v, 3) for a, v in f['rho_move'].items()})
    print('all', {a: round(v, 3) for a, v in out['combined_rho'].items()})
    print('move', {a: round(v, 3) for a, v in out['combined_rho_move'].items()})


if __name__ == '__main__':
    main()
