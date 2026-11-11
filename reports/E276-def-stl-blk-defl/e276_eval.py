"""E-276 評估（prereg.md 凍結 commit 3a2957e）。python -I -B -X utf8 reports/E276-def-stl-blk-defl/e276_eval.py"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('e275_eval', ROOT / 'reports/E275-def-distill-transformer/e275_eval.py')
Q = importlib.util.module_from_spec(s); sys.modules['e275_eval'] = Q; s.loader.exec_module(Q)
M, X, P, sp = Q.M, Q.X, Q.P, Q.sp
STATDIR = ROOT / 'reports/E227-lineup-transformer-r2/data'
NEW = ['stl36', 'blk36', 'deflections36']
NAMED = ['Alex Caruso', 'Victor Wembanyama', 'Rudy Gobert', 'Kevin Durant', 'Stephen Curry', 'Nikola Jokić', 'Amen Thompson',
         'Trae Young', 'Brook Lopez', 'Herbert Jones']


def stats(t, ids, mask):
    tab = {r['pid']: r for r in csv.DictReader(open(STATDIR / f'stats-{t}.csv', encoding='utf-8'))}
    out = {}
    for c in NEW:
        v = np.array([float(tab[str(p)][c]) if str(p) in tab and tab[str(p)][c] not in ('', None) else np.nan for p in ids])
        mu = np.nanmean(v[mask]); v = np.where(np.isfinite(v), v, mu)
        out[c] = (v - v[mask].mean()) / v[mask].std()
    return out


def zc(v, mask):
    return (v - v[mask].mean()) / v[mask].std()


def ols(cols, y, fit):
    Xd = np.c_[np.ones(len(y)), np.column_stack(cols)]
    b = np.linalg.lstsq(Xd[fit], y[fit], rcond=None)[0]
    return Xd @ b, b


def main():
    res = {'folds': {}}
    for t, u in Q.FOLDS:
        d = X.load('A0', t)
        ids, names = d['ids'], d['names']
        R = Q.rows(t, ids)
        d2 = Q.d2_of(t, ids)
        rt = M.rapm_raw(t, 1.0)
        _, mpt = P.pop_of(t)
        d4 = np.array([rt[p][0] if p in rt and rt[p][1] >= 1000 else np.nan for p in ids])
        yt = np.array([rt[p][0] * P.wfun(mpt[p]) if p in rt and rt[p][1] >= 1000 and p in mpt else np.nan for p in ids])
        _, mp = P.pop_of(u)
        ru = M.rapm_raw(u, 1.0)
        yD = np.array([ru[p][0] * P.wfun(mp[p]) if p in ru and ru[p][1] >= 1000 and p in mp else np.nan for p in ids])
        com = np.isfinite(d2) & np.isfinite(d4) & np.isfinite(yD)
        fitR = np.isfinite(yt)
        fitT = np.isfinite(d2)
        allm = np.ones(len(ids), bool)
        S = stats(t, ids, allm)
        ex = {a: zc(np.array([float(r[a]) for r in R]), allm) for a in ['onBall', 'help', 'pressure']}
        D0 = d['def']
        A = {'D0': D0}
        A['D8'], b8 = ols([D0] + [S[c] for c in NEW], yt, fitR)
        A['D8b'], _ = ols([D0] + [ex[a] for a in ex], yt, fitR)
        A['D8c'], _ = ols([D0, S['blk36']], yt, fitR)
        Xd7 = Q.design(R, Q.AALL, ['defenseBonus'])
        Xd10 = np.c_[Xd7, np.column_stack([S[c] for c in NEW])]
        A['D7'] = Xd7 @ np.linalg.lstsq(Xd7[fitT], d2[fitT], rcond=None)[0]
        A['D10'] = Xd10 @ np.linalg.lstsq(Xd10[fitT], d2[fitT], rcond=None)[0]
        sdD0 = D0[fitR].std()
        fo = {'n': int(com.sum()), 'rho': {a: sp(v[com], yD[com]) for a, v in A.items()},
              'coef_D8_per_sd': {'D0(per sd)': float(b8[1] * sdD0), **{c: float(b8[2 + i]) for i, c in enumerate(NEW)}},
              'rho_insample_t': {a: sp(A[a][com], yt[com]) for a in ['D0', 'D8', 'D8b', 'D8c']}}
        exi = np.where(com)[0]
        rk = {a: {names[j]: int((v[com] > v[j]).sum() + 1) for j in exi} for a, v in A.items()}
        fo['ranks'] = {n: {a: rk[a].get(n) for a in ['D0', 'D8', 'D10']} for n in NAMED}
        res['folds'][t] = fo
    ns = sum(res['folds'][t]['n'] for t, _ in Q.FOLDS)
    arms = list(res['folds']['2022-23']['rho'])
    comb = {a: float(sum(res['folds'][t]['rho'][a] * res['folds'][t]['n'] for t, _ in Q.FOLDS) / ns) for a in arms}
    res['combined'] = comb
    gate = {}
    for a in ['D8', 'D8c']:
        g = {'delta': comb[a] - comb['D0'], 'd>=.03': comb[a] - comb['D0'] >= 0.03,
             'every_fold': all(res['folds'][t]['rho'][a] >= res['folds'][t]['rho']['D0'] for t, _ in Q.FOLDS),
             'vs_D8b>=.01': comb[a] - comb['D8b'] >= 0.01}
        g['pass'] = bool(g['d>=.03'] and g['every_fold'] and g['vs_D8b>=.01'])
        gate[a] = g
    res['gate'] = gate
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    for t, _ in Q.FOLDS:
        f = res['folds'][t]
        print(t, f['n'], {a: round(v, 3) for a, v in f['rho'].items()}, 'coef', {k: round(v, 3) for k, v in f['coef_D8_per_sd'].items()},
              'insample', {k: round(v, 3) for k, v in f['rho_insample_t'].items()})
    print('combined', {a: round(v, 3) for a, v in comb.items()})
    print('gate', json.dumps(gate, default=bool))
    print(json.dumps(res['folds']['2024-25']['ranks'], ensure_ascii=False))


if __name__ == '__main__':
    main()
