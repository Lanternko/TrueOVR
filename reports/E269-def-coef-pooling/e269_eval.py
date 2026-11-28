"""E-269 評估：prereg.md（sha 見 prereg.sha256）。五臂（A0–A4）卡 t 季 → 下季 EPM／RAPM；次指標 DEF 分對下季防守 RAPM。
用法（repo root）：python -I -B -X utf8 reports/E269-def-coef-pooling/e269_eval.py
先跑 e269_build.py 產 ranking-<arm>-<原點>.csv；本檔只讀它們。"""
import csv, hashlib, importlib.util, json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


Q = mod('e262', 'reports/E262-forward-creation-downweight/e262_eval.py')
V = mod('e267', 'reports/E267-usage-penalty/e267_eval.py')
M, E, P, SN = Q.M, Q.E, Q.P, Q.SN
pct, sp = M.pct, M.sp
ARMS = ['A0', 'A1', 'A2', 'A3', 'A4']
ORIG = ['2022-23', '2023-24', '2024-25', '2025-26']
FULL = ORIG[:3]
NEXT = Q.NEXT
SEED, B = 20261269, 2000
DEF3 = ['onBall', 'help', 'pressure']
NAMED = ['Kevin Durant', 'Fred VanVleet', 'Victor Wembanyama', 'Rudy Gobert', 'Alex Caruso', 'Stephen Curry', 'Alperen Sengun',
         'Amen Thompson']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(arm, c):
    card = list(csv.DictReader(open(HERE / f'ranking-{arm}-{c}.csv', encoding='utf-8-sig')))
    coef = {}
    for ps in {r['pos'] for r in card}:
        g = [r for r in card if r['pos'] == ps]
        X = np.c_[np.ones(len(g)), [[float(r[a]) for a in SN.OD_ALL] for r in g]]
        coef[ps] = np.linalg.lstsq(X, np.array([float(r['pred0']) for r in g]), rcond=None)[0]
    q = [r for r in card if float(r['MIN']) >= 500]
    mu = {a: np.mean([float(r[a]) for r in q]) for a in SN.OD_ALL}
    mub = np.mean([float(r['defenseBonus']) for r in q])
    pop, _ = P.pop_of(c)
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    rows = {}
    for r in q:
        ids = n2.get(P.norm(r['name'])) or []
        if len(ids) == 1:
            rows[ids[0]] = r
    ids = sorted(rows)
    R = [rows[p] for p in ids]

    def contrib(rr, attrs):
        return np.array([sum(coef[r['pos']][1 + SN.OD_ALL.index(a)] * (float(r[a]) - mu[a]) for a in attrs) for r in rr])

    bon = lambda rr: np.array([float(r['defenseBonus']) - mub for r in rr])
    d = {'ids': ids, 'names': [r['name'] for r in R], 'pos': np.array([r['pos'] for r in R]),
         'ovr': np.array([float(r['ovr']) for r in R]), 'pred0': np.array([float(r['pred0']) for r in R]),
         'def': contrib(R, DEF3) + bon(R), 'def_rbh': contrib(R, DEF3 + ['rebound', 'heightInches']) + bon(R),
         'coef': {ps: {a: float(coef[ps][1 + SN.OD_ALL.index(a)]) for a in SN.OD_ALL} for ps in coef}}
    # 全人群（MIN≥500，不要求名字唯一）的 DEF 名次表
    d['all_names'] = [r['name'] for r in q]
    d['all_def'] = contrib(q, DEF3) + bon(q)
    d['all_def_rbh'] = contrib(q, DEF3 + ['rebound', 'heightInches']) + bon(q)
    d['all_ovr'] = np.array([float(r['ovr']) for r in q]); d['all_pos'] = np.array([r['pos'] for r in q])
    d['all_pred0'] = np.array([float(r['pred0']) for r in q])
    return d


def drapm(ids, s):
    _, mp = P.pop_of(s)
    j = json.loads((E.E126 / f'rapm-{s}.json').read_text(encoding='utf-8'))['players']
    y = np.full(len(ids), np.nan)
    for i, p in enumerate(ids):
        x = j.get(str(p))
        if x and x['poss'] >= 1000 and p in mp:
            y[i] = x['D'] * P.wfun(mp[p])
    return y


def r2(x, y):
    k = np.isfinite(x) & np.isfinite(y)
    return float(np.corrcoef(x[k], y[k])[0, 1] ** 2)


def rho_idx(x, y, rows):
    return sp(x[rows], y[rows])


def main():
    if sha(HERE / 'prereg.md') != (HERE / 'prereg.sha256').read_text().split()[0]:
        print('prereg sha mismatch'); return
    # D 符號檢查（資料事實）
    chk = {}
    for s in ['2023-24', '2024-25', '2025-26']:
        j = json.loads((E.E126 / f'rapm-{s}.json').read_text(encoding='utf-8'))['players']
        v = [x for x in j.values() if x['poss'] >= 1000]
        net, o, dd = (np.array([x[k] for x in v]) for k in ('net', 'O', 'D'))
        chk[s] = {'corr_net_O+D': float(np.corrcoef(net, o + dd)[0, 1]), 'corr_net_O-D': float(np.corrcoef(net, o - dd)[0, 1]), 'n': len(v)}
    print('D sign check', chk)
    sign = 1.0 if all(c['corr_net_O+D'] > c['corr_net_O-D'] for c in chk.values()) else -1.0
    D = {a: {c: load(a, c) for c in ORIG} for a in ARMS}
    for c in ORIG:
        for a in ARMS[1:]:
            assert D[a][c]['ids'] == D['A0'][c]['ids'], 'population differs'
    ids = {c: D['A0'][c]['ids'] for c in ORIG}
    Y = {c: Q.target(ids[c], NEXT[c], 'epm') for c in FULL}
    YR = {c: Q.target(ids[c], NEXT[c], 'rapm') for c in FULL}
    YD = {c: sign * drapm(ids[c], NEXT[c]) for c in FULL}
    Y['2025-26'] = V.live_targets(ids['2025-26'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in ORIG}
    nf = sum(n[c] for c in FULL)
    w = {c: n[c] / nf for c in FULL}
    res = {'dsign_check': chk, 'sign': sign, 'n_primary': n, 'n_def': {c: int(np.isfinite(YD[c]).sum()) for c in FULL}, 'arms': {}}

    def fold(a, c, rows=None):
        d = D[a][c]
        k = np.where(np.isfinite(Y[c]))[0] if rows is None else rows
        out = {'R2': r2(d['ovr'][k], Y[c][k]), 'rho': sp(d['ovr'][k], Y[c][k])}
        if c in FULL:
            kd = np.where(np.isfinite(YD[c]))[0] if rows is None else np.array([i for i in rows if np.isfinite(YD[c][i])])
            out['rhoDEF'] = sp(d['def'][kd], YD[c][kd]); out['rhoDEF_rbh'] = sp(d['def_rbh'][kd], YD[c][kd])
            kr = np.where(np.isfinite(YR[c]))[0] if rows is None else np.array([i for i in rows if np.isfinite(YR[c][i])])
            out['R2_rapm'] = r2(d['ovr'][kr], YR[c][kr]); out['rho_rapm'] = sp(d['ovr'][kr], YR[c][kr])
        return out

    F = {a: {c: fold(a, c) for c in ORIG} for a in ARMS}
    rng = np.random.default_rng(SEED)
    idx = {c: np.where(np.isfinite(Y[c]))[0] for c in FULL}
    draws = [{c: rng.choice(idx[c], len(idx[c])) for c in FULL} for _ in range(B)]
    base_bs = [sum(w[c] * r2(D['A0'][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) for dr in draws]
    for a in ARMS:
        wm = lambda key: float(sum(w[c] * F[a][c][key] for c in FULL))
        comb = {k: wm(k) for k in ('R2', 'rho', 'rhoDEF', 'rhoDEF_rbh', 'R2_rapm', 'rho_rapm')}
        res['arms'][a] = {'folds': F[a], 'combined': comb}
    for a in ARMS[1:]:
        A0 = res['arms']['A0']
        ar = res['arms'][a]
        dd = {k: ar['combined'][k] - A0['combined'][k] for k in ar['combined']}
        per = {c: {k: F[a][c][k] - F['A0'][c][k] for k in F[a][c]} for c in ORIG}
        bs = [sum(w[c] * r2(D[a][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) - b0 for dr, b0 in zip(draws, base_bs)]
        ci = [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]
        g1 = dd['R2'] >= 0.005
        g2 = all(per[c]['R2'] >= 0 for c in FULL)
        g3 = dd['rhoDEF'] >= 0
        ar['delta'] = dd; ar['delta_fold'] = per; ar['ci90_dR2'] = ci
        ar['gates'] = {'dR2>=.005': bool(g1), 'every_fold_dR2>=0': bool(g2), 'dRhoDEF>=0': bool(g3)}
        ar['pass'] = bool(g1 and g2 and g3)
        ar['def_only'] = bool(dd['rhoDEF'] >= 0.005 and abs(dd['R2']) < 0.005)
        d0, da = D['A0'], D[a]
        ar['vs_A0'] = {c: {'n_ovr_diff>=3': int((np.abs(da[c]['ovr'] - d0[c]['ovr']) >= 3).sum()),
                          'max_abs_ovr_diff': float(np.abs(da[c]['ovr'] - d0[c]['ovr']).max()),
                          'max_abs_pred0_diff': float(np.abs(da[c]['pred0'] - d0[c]['pred0']).max())} for c in ORIG}
    passed = [a for a in ARMS[1:] if res['arms'][a]['pass']]
    res['adopt'] = max(passed, key=lambda a: res['arms'][a]['combined']['R2']) if passed else None
    res['def_display_only'] = [a for a in ARMS[1:] if res['arms'][a]['def_only']]
    res['coef'] = {a: {c: {ps: {k: D[a][c]['coef'][ps][k] for k in DEF3 + ['rebound', 'heightInches']} for ps in ['PG', 'SG', 'SF', 'PF', 'C']
                           if ps in D[a][c]['coef']} for c in ORIG} for a in ARMS}
    # 例子表（2025-26 原點為主；VanVleet 2025-26 傷缺 MIN<500 不在卡裡，補 2024-25 原點）
    res['examples'] = {}
    for c in ['2025-26', '2024-25']:
        d0 = D['A0'][c]
        bigs = [nm for nm, p, o in sorted(zip(d0['all_names'], d0['all_pos'], d0['all_ovr']), key=lambda t: -t[2]) if p == 'C'][:10]
        show = NAMED + [b for b in bigs if b not in NAMED]
        ex = {}
        for a in ARMS:
            d = D[a][c]
            ranks = {k: {nm: int((v > v[i]).sum() + 1) for i, nm in enumerate(d['all_names'])} for k, v in
                     (('def', d['all_def']), ('def_rbh', d['all_def_rbh']))}
            ro = {nm: int((d['all_ovr'] > d['all_ovr'][i]).sum() + 1) for i, nm in enumerate(d['all_names'])}
            ex[a] = {nm: {'def': float(d['all_def'][d['all_names'].index(nm)]), 'def_rank': ranks['def'].get(nm), 'def_rbh_rank': ranks['def_rbh'].get(nm),
                          'ovr': float(d['all_ovr'][d['all_names'].index(nm)]), 'ovr_rank': ro.get(nm)} if nm in d['all_names'] else None for nm in show}
        res['examples'][c] = {'show': show, 'bigs': bigs, 'n_pop': len(d0['all_names']), 'by_arm': ex}
    # A3 λ_int
    lam = {}
    for t in ORIG:
        for f in (HERE / 'work' / 'A3').glob(f'base-S-{t}/**/run.log'):
            m = re.search(r'E269 A3 lambda_int CV (\{.*?\}) chosen (\S+)', f.read_text(encoding='utf-8', errors='replace'))
            if m:
                lam.setdefault(t, {})[f.parent.name] = {'cv': m.group(1), 'chosen': m.group(2)}
    res['A3_lambda_int'] = lam
    res['sha256_rankings'] = {f'{a}-{t}': sha(HERE / f'ranking-{a}-{t}.csv') for a in ARMS for t in ORIG}
    for t in ORIG:
        ref = ROOT / f'reports/card-0.2.9+E164-no-stamina/ranking-S-{t}.csv'
        res.setdefault('A0_repro', {})[t] = sha(ref) == res['sha256_rankings'][f'A0-{t}']
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print('repro', res['A0_repro'])
    print('n', n, 'n_def', res['n_def'])
    A0 = res['arms']['A0']
    print('A0 combined', {k: round(v, 4) for k, v in A0['combined'].items()})
    for c in ORIG:
        print('  A0', c, {k: round(v, 4) for k, v in F['A0'][c].items()})
    for a in ARMS[1:]:
        ar = res['arms'][a]
        print(f'== {a} pass={ar["pass"]} gates={ar["gates"]} def_only={ar["def_only"]} ci90={[round(x, 4) for x in ar["ci90_dR2"]]}')
        print('   combined d', {k: round(v, 4) for k, v in ar['delta'].items()})
        for c in ORIG:
            print('   ', c, {k: round(v, 4) for k, v in ar['delta_fold'][c].items()}, ar['vs_A0'][c])
    print('adopt', res['adopt'], 'def_display_only', res['def_display_only'])


if __name__ == '__main__':
    main()
