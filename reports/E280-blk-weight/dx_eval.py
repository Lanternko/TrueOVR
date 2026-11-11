"""E-280／E-281 共用評估核心（沿用 E-278 e278_eval 的口徑）。arms＝{名: {'path': f(c)->Path, 'extras': [...], 'window': bool, 'nopress': bool, 'work': Path}}。"""
import ast, csv, importlib.util, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E277 = ROOT / 'reports/E277-help-monotone'


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


Z = mod('e277e', E277 / 'e277_eval.py')
X, Q, V, P, SN = Z.X, Z.Q, Z.V, Z.P, Z.X.SN
DXS = mod('dx_stats', HERE / 'dx_stats.py')
ORIG, FULL, NEXT = X.ORIG, X.FULL, X.NEXT
NAMED = ['Kevin Durant', 'Stephen Curry', 'Victor Wembanyama', 'Rudy Gobert', 'Anthony Davis', 'Bam Adebayo', 'Jarrett Allen',
         'Isaiah Hartenstein', 'Alex Caruso', 'Amen Thompson', 'Trae Young', 'Brook Lopez', 'Herbert Jones', 'Jaren Jackson Jr.',
         'Nikola Jokić', 'Karl-Anthony Towns']
KEYS = ('R2', 'rhoDEF_epmD', 'rhoDEF_T', 'rhoDEF_rapmD', 'R2_rapm')


def load(spec, c):
    card = list(csv.DictReader(open(spec['path'](c), encoding='utf-8-sig')))
    ks = spec.get('extras', [])
    ex, miss = DXS.lookup([r['name'] for r in card], c, ks, spec.get('window', False)) if ks else ({}, {})
    base = [a for a in SN.OD_ALL if not (spec.get('nopress') and a == 'pressure')]
    feats = base + ks
    val = lambda i, a: ex[a][i] if a in ks else float(card[i][a])
    coef = {}
    for ps in {r['pos'] for r in card}:
        gi = [i for i, r in enumerate(card) if r['pos'] == ps]
        Xm = np.c_[np.ones(len(gi)), [[val(i, a) for a in feats] for i in gi]]
        coef[ps] = np.linalg.lstsq(Xm, np.array([float(card[i]['pred0']) for i in gi]), rcond=None)[0]
    qi = [i for i, r in enumerate(card) if float(r['MIN']) >= 500]
    mu = {a: np.mean([val(i, a) for i in qi]) for a in feats}
    mub = np.mean([float(card[i]['defenseBonus']) for i in qi])
    defk = ['onBall', 'help'] + ([] if spec.get('nopress') else ['pressure']) + ks

    def dscore(ii):
        return np.array([sum(coef[card[i]['pos']][1 + feats.index(a)] * (val(i, a) - mu[a]) for a in defk)
                         + float(card[i]['defenseBonus']) - mub for i in ii])
    pop, _ = P.pop_of(c)
    n2 = {}
    for p, inf in pop.items():
        n2.setdefault(P.norm(inf['name']), []).append(p)
    rows = {}
    for i in qi:
        ids = n2.get(P.norm(card[i]['name'])) or []
        if len(ids) == 1:
            rows[ids[0]] = i
    ids = sorted(rows)
    ii = [rows[p] for p in ids]
    return {'ids': ids, 'ovr': np.array([float(card[i]['ovr']) for i in ii]), 'def': dscore(ii),
            'all_names': [card[i]['name'] for i in qi], 'all_def': dscore(qi), 'all_ovr': np.array([float(card[i]['ovr']) for i in qi]),
            'all_pos': np.array([card[i]['pos'] for i in qi]), 'miss': miss}


def fitted_coef(workdir, t):
    fs = sorted((workdir / f'base-S-{t}').glob('*/cards/K0/primary/run.log'))
    if len(fs) != 1:
        return None
    m = re.search(r'(?:DX|E278) coef (\{.*\})', fs[0].read_text(encoding='utf-8', errors='replace'))
    return ast.literal_eval(m.group(1)) if m else None


def compute(arms, base, seed, B=2000):
    D = {a: {c: load(arms[a], c) for c in ORIG} for a in arms}
    for c in ORIG:
        for a in arms:
            assert D[a][c]['ids'] == D[base][c]['ids'], 'population differs'
    ids = {c: D[base][c]['ids'] for c in ORIG}
    Y = {c: Q.target(ids[c], NEXT[c], 'epm') for c in FULL}
    YR = {c: Q.target(ids[c], NEXT[c], 'rapm') for c in FULL}
    YE = {c: Z.epm_d(ids[c], NEXT[c]) for c in FULL}
    YD = {c: X.drapm(ids[c], NEXT[c]) for c in FULL}
    YT = {c: Z.t_def(ids[c], c) for c in FULL}
    Y['2025-26'] = V.live_targets(ids['2025-26'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in ORIG}
    nf = sum(n[c] for c in FULL)
    w = {c: n[c] / nf for c in FULL}

    def fold(a, c):
        d = D[a][c]
        out = {'R2': Z.r2(d['ovr'], Y[c])}
        if c in FULL:
            out['rhoDEF_epmD'], _ = Z.rho(d['def'], YE[c]); out['rhoDEF_T'], _ = Z.rho(d['def'], YT[c])
            out['rhoDEF_rapmD'], _ = Z.rho(d['def'], YD[c]); out['R2_rapm'] = Z.r2(d['ovr'], YR[c])
        return out
    F = {a: {c: fold(a, c) for c in ORIG} for a in arms}
    rng = np.random.default_rng(seed)
    idx = {c: np.where(np.isfinite(Y[c]))[0] for c in FULL}
    draws = [{c: rng.choice(idx[c], len(idx[c])) for c in FULL} for _ in range(B)]
    base_bs = [sum(w[c] * Z.r2(D[base][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) for dr in draws]
    res = {'n_primary': n, 'weights': w, 'arms': {}}
    for a in arms:
        comb = {k: float(sum(w[c] * F[a][c][k] for c in FULL)) for k in KEYS}
        ar = {'folds': F[a], 'combined': comb, 'missing': {c: D[a][c]['miss'] for c in ORIG}}
        if arms[a].get('work'):
            ar['fitted_coef'] = {t: fitted_coef(arms[a]['work'], t) for t in ORIG}
        res['arms'][a] = ar
    for a in arms:
        if a == base:
            continue
        ar = res['arms'][a]
        dd = {k: ar['combined'][k] - res['arms'][base]['combined'][k] for k in KEYS}
        per = {c: {k: F[a][c][k] - F[base][c][k] for k in F[a][c]} for c in ORIG}
        bs = [sum(w[c] * Z.r2(D[a][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) - b0 for dr, b0 in zip(draws, base_bs)]
        ar.update(delta=dd, delta_fold=per, ci90_dR2=[float(np.percentile(bs, 5)), float(np.percentile(bs, 95))],
                  S2=bool(dd['R2'] >= -0.005 and all(per[c]['R2'] >= -0.010 for c in FULL)), S3=bool(dd['rhoDEF_epmD'] >= -0.010),
                  improved={'dR2>0': bool(dd['R2'] > 0), 'dEPMD>0': bool(dd['rhoDEF_epmD'] > 0), 'dT>0': bool(dd['rhoDEF_T'] > 0)},
                  vs_base={c: {'n_ovr_diff>=3': int((np.abs(D[a][c]['ovr'] - D[base][c]['ovr']) >= 3).sum()),
                               'max_abs_ovr_diff': float(np.abs(D[a][c]['ovr'] - D[base][c]['ovr']).max())} for c in ORIG})
    res['examples'] = {}
    for c in ['2024-25', '2025-26']:
        d0 = D[base][c]
        bigs = [nm for nm, p, o in sorted(zip(d0['all_names'], d0['all_pos'], d0['all_ovr']), key=lambda t: -t[2]) if p == 'C'][:8]
        show = NAMED + [b for b in bigs if b not in NAMED]
        ex = {}
        for a in arms:
            d = D[a][c]
            v, o, nm = d['all_def'], d['all_ovr'], d['all_names']
            ex[a] = {s: ({'def_rank': int((v > v[nm.index(s)]).sum() + 1), 'ovr_rank': int((o > o[nm.index(s)]).sum() + 1)} if s in nm else None) for s in show}
        res['examples'][c] = {'n_pop': len(d0['all_names']), 'show': show, 'by_arm': ex}
    return res, F


def show(res, arms, base):
    print(base, 'combined', {k: round(v, 4) for k, v in res['arms'][base]['combined'].items()})
    for a in arms:
        if a == base:
            continue
        ar = res['arms'][a]
        print(f"== {a} S2={ar['S2']} S3={ar['S3']} improved={ar['improved']} ci90={[round(x, 4) for x in ar['ci90_dR2']]}")
        print('   d', {k: round(v, 4) for k, v in ar['delta'].items()})
        for c in ORIG:
            fc = (ar.get('fitted_coef') or {}).get(c) or {}
            print('   ', c, {k: round(v, 4) for k, v in ar['delta_fold'][c].items()}, ar['vs_base'][c],
                  {k: (round(v['perUnit'], 3), round(v['perSD'], 3), round(v['seSD'], 3)) for k, v in fc.items()})
    print('missing', {a: res['arms'][a]['missing'] for a in arms})
    for c in res['examples']:
        print('--', c, 'n', res['examples'][c]['n_pop'])
        for s in res['examples'][c]['show']:
            r = {}
            for a in arms:
                x = res['examples'][c]['by_arm'][a][s]
                r[a] = (x['def_rank'], x['ovr_rank']) if x else None
            print('  ', s, r)
