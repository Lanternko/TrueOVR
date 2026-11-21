"""E-276 §8 追加臂 D12／D12b／D12w。python -I -B -X utf8 reports/E276-def-stl-blk-defl/e276_d12.py"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location('e276_eval', HERE / 'e276_eval.py')
W = importlib.util.module_from_spec(s); sys.modules['e276_eval'] = W; s.loader.exec_module(W)
Q, M, X, P, sp = W.Q, W.M, W.X, W.P, W.sp
COMP = ['stl36', 'deflections36', 'charges36', 'pf36']
ALL = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
CARD = ['2022-23', '2023-24', '2024-25']
TAB = {s_: {r['pid']: r for r in csv.DictReader(open(W.STATDIR / f'stats-{s_}.csv', encoding='utf-8'))} for s_ in ALL}


def window(s_, ids):
    i = ALL.index(s_); ss = ALL[max(0, i - 3):i + 1]
    out = {}
    for c in COMP:
        v = []
        for p in ids:
            num = den = 0.0
            for q in ss:
                r = TAB[q].get(str(p))
                if r and r[c] not in ('', None) and r['minutes'] not in ('', None) and float(r['minutes']) >= 200:
                    m = float(r['minutes']); num += m * float(r[c]); den += m
            v.append(num / den if den else np.nan)
        v = np.array(v); v = np.where(np.isfinite(v), v, np.nanmean(v))
        out[c] = (v - v.mean()) / v.std()
    return out


def season(t):
    d = X.load('A0', t); ids = d['ids']
    R = Q.rows(t, ids)
    card = [r for r in csv.DictReader(open(X.HERE / f'ranking-A0-{t}.csv', encoding='utf-8-sig')) if float(r['MIN']) >= 500]
    mu = np.mean([float(r['pressure']) for r in card]); sdp = np.std([float(r['pressure']) for r in card])
    cp = np.array([d['coef'][r['pos']]['pressure'] for r in R])
    pres = np.array([float(r['pressure']) for r in R])
    base = d['def'] - cp * (pres - mu)
    rt = M.rapm_raw(t, 1.0); _, mpt = P.pop_of(t)
    yt = np.array([rt[p][0] * P.wfun(mpt[p]) if p in rt and rt[p][1] >= 1000 and p in mpt else np.nan for p in ids])
    Z = window(t, ids)
    zp = (pres - pres.mean()) / pres.std()
    combo = Z['stl36'] + Z['deflections36'] + 0.5 * Z['charges36'] - 0.25 * Z['pf36']
    combo = (combo - combo.mean()) / combo.std()
    return dict(d=d, ids=ids, base=base, yt=yt, Z=Z, zp=zp, w=base + cp * sdp * combo)


def main():
    S = {t: season(t) for t in CARD}
    out = {'folds': {}}
    for t, u in Q.FOLDS:
        tr = [S[q] for q in CARD if q <= t]
        Xc = lambda e: np.c_[np.ones(len(e['ids'])), e['base'], np.column_stack([e['Z'][c] for c in COMP])]
        Xp = lambda e: np.c_[np.ones(len(e['ids'])), e['base'], e['zp']]
        def fit(fx):
            XX = np.vstack([fx(e) for e in tr]); yy = np.concatenate([e['yt'] for e in tr]); k = np.isfinite(yy)
            return np.linalg.lstsq(XX[k], yy[k], rcond=None)[0]
        b12, b12b = fit(Xc), fit(Xp)
        e = S[t]; ids = e['ids']
        d2 = Q.d2_of(t, ids)
        rt = M.rapm_raw(t, 1.0)
        d4 = np.array([rt[p][0] if p in rt and rt[p][1] >= 1000 else np.nan for p in ids])
        _, mp = P.pop_of(u); ru = M.rapm_raw(u, 1.0)
        yD = np.array([ru[p][0] * P.wfun(mp[p]) if p in ru and ru[p][1] >= 1000 and p in mp else np.nan for p in ids])
        com = np.isfinite(d2) & np.isfinite(d4) & np.isfinite(yD)
        A = {'D0': e['d']['def'], 'D12': Xc(e) @ b12, 'D12b': Xp(e) @ b12b, 'D12w': e['w']}
        out['folds'][t] = {'n': int(com.sum()), 'fit_seasons': [q for q in CARD if q <= t],
                           'rho': {a: sp(v[com], yD[com]) for a, v in A.items()},
                           'coef_D12': {c: float(b12[2 + i]) for i, c in enumerate(COMP)}, 'coef_D12b_pressure': float(b12b[2])}
    ns = sum(f['n'] for f in out['folds'].values())
    comb = {a: float(sum(f['rho'][a] * f['n'] for f in out['folds'].values()) / ns) for a in ['D0', 'D12', 'D12b', 'D12w']}
    out['combined'] = comb
    out['pass'] = bool(comb['D12'] >= comb['D0'] and comb['D12'] - comb['D12b'] >= 0.01
                       and all(f['rho']['D12'] >= f['rho']['D0'] for f in out['folds'].values()))
    (HERE / 'results-d12.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for t, f in out['folds'].items():
        print(t, {a: round(v, 3) for a, v in f['rho'].items()}, {k: round(v, 3) for k, v in f['coef_D12'].items()}, 'pres', round(f['coef_D12b_pressure'], 3))
    print('combined', {a: round(v, 3) for a, v in comb.items()}, 'pass', out['pass'])


if __name__ == '__main__':
    main()
