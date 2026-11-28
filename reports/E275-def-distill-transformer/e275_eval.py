"""E-275 評估（prereg.md 已凍結，commit 4bab2d0）。python -I -B -X utf8 reports/E275-def-distill-transformer/e275_eval.py"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('e274_eval', ROOT / 'reports/E274-def-display-transformer/e274_eval.py')
M = importlib.util.module_from_spec(s); sys.modules['e274_eval'] = M; s.loader.exec_module(M)
X, P, sp, E274 = M.X, M.P, M.sp, M.HERE
FOLDS = M.FOLDS
A3 = ['onBall', 'help', 'pressure']
AALL = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help',
        'stamina', 'heightInches', 'creation', 'pressure', 'foulDisc']
NAMED = ['Kevin Durant', 'Stephen Curry', 'Victor Wembanyama', 'Rudy Gobert', 'Alex Caruso', 'Amen Thompson', 'Alperen Sengun',
         'Nikola Jokić', 'Trae Young', 'Fred VanVleet']
POS = ['PG', 'SG', 'SF', 'PF', 'C']


def rows(t, ids):
    card = list(csv.DictReader(open(X.HERE / f'ranking-A0-{t}.csv', encoding='utf-8-sig')))
    q = [r for r in card if float(r['MIN']) >= 500]
    pop, _ = P.pop_of(t)
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    m = {}
    for r in q:
        k = n2.get(P.norm(r['name'])) or []
        if len(k) == 1:
            m[k[0]] = r
    return [m[p] for p in ids]


def design(R, attrs, extra=None, pos_int=True):
    cols = [[float(r[a]) for a in attrs] + ([float(r[e]) for e in extra] if extra else []) for r in R]
    Z = np.array(cols)
    D = np.array([[1.0 if r['pos'] == ps else 0.0 for ps in POS] for r in R])
    return np.c_[D, Z] if pos_int else np.c_[np.ones(len(R)), Z]


def d2_of(t, ids):
    w = json.loads(open(E274 / f'd2-{t}.json').read())['oppPts100']
    return np.array([-w[str(p)] if str(p) in w else np.nan for p in ids])


SPECS = {'D5': (A3, None), 'D6': (AALL, None), 'D7': (AALL, ['defenseBonus'])}


def main():
    res = {'folds': {}, 'coef_std_D6': {}}
    sg = 1.0
    for t, u in FOLDS:
        d = X.load('A0', t)
        ids, names = d['ids'], d['names']
        R = rows(t, ids)
        d2 = d2_of(t, ids)
        fit = np.isfinite(d2)
        rt = M.rapm_raw(t, sg)
        d4 = np.array([rt[p][0] if p in rt and rt[p][1] >= 1000 else np.nan for p in ids])
        _, mp = P.pop_of(u)
        ru = M.rapm_raw(u, sg)
        ok = lambda p: p in ru and ru[p][1] >= 1000 and p in mp
        yD = np.array([ru[p][0] * P.wfun(mp[p]) if ok(p) else np.nan for p in ids])
        com = np.isfinite(d2) & np.isfinite(d4) & np.isfinite(yD)
        A = {'D0': d['def'], 'D2': d2}
        A_nopos, coefs = {}, {}
        for a, (attrs, extra) in SPECS.items():
            Xd = design(R, attrs, extra)
            b = np.linalg.lstsq(Xd[fit], d2[fit], rcond=None)[0]
            A[a] = Xd @ b
            A_nopos[a] = Xd[:, 5:] @ b[5:]
            coefs[a] = b
        fo = {'n': int(com.sum()), 'n_fit': int(fit.sum()),
              'rho': {a: sp(v[com], yD[com]) for a, v in A.items()},
              'rho_nopos': {a: sp(v[com], yD[com]) for a, v in A_nopos.items()},
              'fidelity_in': {a: sp(A[a][fit], d2[fit]) for a in SPECS}}
        # D6 standardized coefs
        cs = [c for c in AALL]
        sd = np.array([np.std([float(r[c]) for r in R]) for c in cs])
        res['coef_std_D6'][t] = dict(sorted({c: float(coefs['D6'][5 + i] * sd[i]) for i, c in enumerate(cs)}.items(), key=lambda kv: -abs(kv[1])))
        # out-of-season fidelity: apply t coefs to u card vs u's d2
        if (E274 / f'd2-{u}.json').exists():
            du = X.load('A0', u)
            Ru = rows(u, du['ids'])
            d2u = d2_of(u, du['ids'])
            k = np.isfinite(d2u)
            fo['fidelity_next'] = {a: sp((design(Ru, *SPECS[a]) @ coefs[a])[k], d2u[k]) for a in SPECS}
            fo['fidelity_next']['D0'] = sp(du['def'][k], d2u[k])
        ex = com
        exi = np.where(ex)[0]
        ranks = {}
        for a, v in A.items():
            vv = v[ex]
            ranks[a] = {names[j]: int((vv > val).sum() + 1) for j, val in zip(exi, vv)}
        fo['examples'] = {'n_pop': int(ex.sum()), 'ranks': {n: {a: ranks[a].get(n) for a in A} for n in NAMED}}
        res['folds'][t] = fo
    ns = sum(res['folds'][t]['n'] for t, _ in FOLDS)
    arms = ['D0', 'D2', 'D5', 'D6', 'D7']
    comb = {a: float(sum(res['folds'][t]['rho'][a] * res['folds'][t]['n'] for t, _ in FOLDS) / ns) for a in arms}
    comb_np = {a: float(sum(res['folds'][t]['rho_nopos'][a] * res['folds'][t]['n'] for t, _ in FOLDS) / ns) for a in SPECS}
    res['combined'] = comb; res['combined_nopos'] = comb_np
    gate = {}
    for a in SPECS:
        g = {'delta_vs_D0': comb[a] - comb['D0'],
             'highest': bool(comb[a] >= max(comb[b] for b in ['D0', 'D5', 'D6', 'D7'])),
             'delta>=.03': bool(comb[a] - comb['D0'] >= 0.03),
             'every_fold>=D0': bool(all(res['folds'][t]['rho'][a] >= res['folds'][t]['rho']['D0'] for t, _ in FOLDS))}
        g['pass'] = all(g[k] for k in ('highest', 'delta>=.03', 'every_fold>=D0'))
        gate[a] = g
    res['gate'] = gate
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    for t, _ in FOLDS:
        f = res['folds'][t]
        print(t, f['n'], {a: round(v, 3) for a, v in f['rho'].items()}, 'nopos', {a: round(v, 3) for a, v in f['rho_nopos'].items()},
              'fid', {a: round(v, 3) for a, v in f['fidelity_in'].items()}, 'fidnext', {a: round(v, 3) for a, v in f.get('fidelity_next', {}).items()})
    print('combined', {a: round(v, 3) for a, v in comb.items()}, 'nopos', {a: round(v, 3) for a, v in comb_np.items()})
    print('gate', json.dumps(gate))
    print('coefD6 2024-25', {k: round(v, 3) for k, v in res['coef_std_D6']['2024-25'].items()})
    print(json.dumps(res['folds']['2024-25']['examples'], ensure_ascii=False))


if __name__ == '__main__':
    main()
