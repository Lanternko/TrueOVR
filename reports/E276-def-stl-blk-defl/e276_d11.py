"""E-276 §7 追加臂 D11／D11b。python -I -B -X utf8 reports/E276-def-stl-blk-defl/e276_d11.py"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('e276_eval', HERE / 'e276_eval.py')
W = importlib.util.module_from_spec(s); sys.modules['e276_eval'] = W; s.loader.exec_module(W)
Q, M, X, P, sp = W.Q, W.M, W.X, W.P, W.sp
COMP = ['stl36', 'deflections36', 'charges36', 'pf36']


def main():
    out = {'folds': {}}
    for t, u in Q.FOLDS:
        d = X.load('A0', t); ids, names = d['ids'], d['names']
        R = Q.rows(t, ids)
        card = [r for r in csv.DictReader(open(X.HERE / f'ranking-A0-{t}.csv', encoding='utf-8-sig')) if float(r['MIN']) >= 500]
        mu = np.mean([float(r['pressure']) for r in card])
        pc = np.array([d['coef'][r['pos']]['pressure'] * (float(r['pressure']) - mu) for r in R])
        base = d['def'] - pc
        d2 = Q.d2_of(t, ids)
        rt = M.rapm_raw(t, 1.0); _, mpt = P.pop_of(t)
        d4 = np.array([rt[p][0] if p in rt and rt[p][1] >= 1000 else np.nan for p in ids])
        yt = np.array([rt[p][0] * P.wfun(mpt[p]) if p in rt and rt[p][1] >= 1000 and p in mpt else np.nan for p in ids])
        _, mp = P.pop_of(u); ru = M.rapm_raw(u, 1.0)
        yD = np.array([ru[p][0] * P.wfun(mp[p]) if p in ru and ru[p][1] >= 1000 and p in mp else np.nan for p in ids])
        com = np.isfinite(d2) & np.isfinite(d4) & np.isfinite(yD); fit = np.isfinite(yt)
        allm = np.ones(len(ids), bool)
        tab = {r['pid']: r for r in csv.DictReader(open(W.STATDIR / f'stats-{t}.csv', encoding='utf-8'))}
        Z = {}
        for c in COMP:
            v = np.array([float(tab[str(p)][c]) if str(p) in tab and tab[str(p)][c] not in ('', None) else np.nan for p in ids])
            v = np.where(np.isfinite(v), v, np.nanmean(v)); Z[c] = W.zc(v, allm)
        zp = W.zc(np.array([float(r['pressure']) for r in R]), allm)
        A = {'D0': d['def']}
        A['D11'], b11 = W.ols([base] + [Z[c] for c in COMP], yt, fit)
        A['D11b'], b11b = W.ols([base, zp], yt, fit)
        out['folds'][t] = {'n': int(com.sum()), 'rho': {a: sp(v[com], yD[com]) for a, v in A.items()},
                           'coef_D11': {c: float(b11[2 + i]) for i, c in enumerate(COMP)}, 'coef_D11b_pressure': float(b11b[2])}
    ns = sum(f['n'] for f in out['folds'].values())
    comb = {a: float(sum(f['rho'][a] * f['n'] for f in out['folds'].values()) / ns) for a in ['D0', 'D11', 'D11b']}
    out['combined'] = comb
    out['pass'] = bool(comb['D11'] >= comb['D0'] and comb['D11'] - comb['D11b'] >= 0.01
                       and all(f['rho']['D11'] >= f['rho']['D0'] for f in out['folds'].values()))
    (HERE / 'results-d11.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for t, f in out['folds'].items():
        print(t, {a: round(v, 3) for a, v in f['rho'].items()}, {k: round(v, 3) for k, v in f['coef_D11'].items()}, 'pres', round(f['coef_D11b_pressure'], 3))
    print('combined', {a: round(v, 3) for a, v in comb.items()}, 'pass', out['pass'])


if __name__ == '__main__':
    main()
