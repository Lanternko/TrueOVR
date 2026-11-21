"""E-278 評估（prereg.md，sha 見 prereg.sha256）。B0＝E-277 M1；B1–B3 用本目錄 e278_build.py 產的 ranking。
用法（repo root）：python -I -B -X utf8 reports/E278-def-stl-blk-defl-pred0/e278_eval.py"""
import ast, csv, hashlib, importlib.util, json, re, shutil, sys, unicodedata
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E277 = ROOT / 'reports/E277-help-monotone'


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


Z = mod('e277e', E277 / 'e277_eval.py')
X, Q, V, P, sp, SN = Z.X, Z.Q, Z.V, Z.P, Z.sp, Z.X.SN
ARMS = ['B0', 'B1', 'B2', 'B3']
EXTRA = {'B0': [], 'B1': ['blk36', 'stl36', 'deflections36'], 'B2': ['blk36', 'stl36', 'deflections36'], 'B3': ['blk36']}
ORIG, FULL, NEXT = X.ORIG, X.FULL, X.NEXT
SEED, B = 20261278, 2000
DEF3 = ['onBall', 'help', 'pressure']
NAMED = ['Kevin Durant', 'Stephen Curry', 'Victor Wembanyama', 'Rudy Gobert', 'Anthony Davis', 'Bam Adebayo', 'Jarrett Allen',
         'Isaiah Hartenstein', 'Alex Caruso', 'Amen Thompson', 'Trae Young', 'Brook Lopez', 'Herbert Jones', 'Jaren Jackson Jr.']
STATDIR = ROOT / 'reports/E227-lineup-transformer-r2/data'


def _nm(x):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', x) if not unicodedata.combining(ch)).lower().replace('.', '').replace(' jr', '').replace(' iii', '').replace(' ii', '').strip()


def extras(card, t, keys):
    by = {}
    for r in csv.DictReader(open(STATDIR / f'stats-{t}.csv', encoding='utf-8')):
        by.setdefault(r['name'], r); by.setdefault(_nm(r['name']), r)
    out, miss = {}, 0
    for k in keys:
        v = []
        for r in card:
            st = by.get(r['name']) or by.get(_nm(r['name']))
            x = st.get(k) if st else None
            v.append(float(x) if x not in (None, '') else np.nan)
        v = np.array(v); miss = int(np.isnan(v).sum()); v[np.isnan(v)] = np.nanmean(v)
        out[k] = v
    return out, miss


def load(arm, c):
    path = E277 / f'ranking-M1-{c}.csv' if arm == 'B0' else HERE / f'ranking-{arm}-{c}.csv'
    card = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    ks = EXTRA[arm]
    ex, miss = extras(card, c, ks)
    feats = SN.OD_ALL + ks
    val = lambda i, r, a: ex[a][i] if a in ks else float(r[a])
    coef = {}
    for ps in {r['pos'] for r in card}:
        gi = [i for i, r in enumerate(card) if r['pos'] == ps]
        Xm = np.c_[np.ones(len(gi)), [[val(i, card[i], a) for a in feats] for i in gi]]
        coef[ps] = np.linalg.lstsq(Xm, np.array([float(card[i]['pred0']) for i in gi]), rcond=None)[0]
    qi = [i for i, r in enumerate(card) if float(r['MIN']) >= 500]
    q = [card[i] for i in qi]
    mu = {a: np.mean([val(i, card[i], a) for i in qi]) for a in feats}
    mub = np.mean([float(r['defenseBonus']) for r in q])
    defk = DEF3 + ks

    def dscore(ii):
        return np.array([sum(coef[card[i]['pos']][1 + feats.index(a)] * (val(i, card[i], a) - mu[a]) for a in defk)
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
            'all_names': [r['name'] for r in q], 'all_def': dscore(qi), 'all_ovr': np.array([float(r['ovr']) for r in q]),
            'all_pos': np.array([r['pos'] for r in q]), 'miss': miss,
            'coef_extra_by_pos': {ps: {a: float(coef[ps][1 + feats.index(a)]) for a in ks + ['pressure', 'help']} for ps in coef}}


def fitted_coef(arm, t):
    fs = sorted((HERE / 'work' / arm / f'base-S-{t}').glob('*/cards/K0/primary/run.log'))
    if len(fs) != 1:
        return None
    f = fs[0]
    m = re.search(r'E278 coef (\{.*\})', f.read_text(encoding='utf-8', errors='replace'))
    return ast.literal_eval(m.group(1)) if m else None


def main():
    if Z.sha(HERE / 'prereg.md') != (HERE / 'prereg.sha256').read_text().split()[0]:
        print('prereg sha mismatch'); return 1
    sign = 1.0
    D = {a: {c: load(a, c) for c in ORIG} for a in ARMS}
    for c in ORIG:
        for a in ARMS[1:]:
            assert D[a][c]['ids'] == D['B0'][c]['ids'], 'population differs'
    ids = {c: D['B0'][c]['ids'] for c in ORIG}
    Y = {c: Q.target(ids[c], NEXT[c], 'epm') for c in FULL}
    YR = {c: Q.target(ids[c], NEXT[c], 'rapm') for c in FULL}
    YE = {c: Z.epm_d(ids[c], NEXT[c]) for c in FULL}
    YD = {c: sign * X.drapm(ids[c], NEXT[c]) for c in FULL}
    YT = {c: Z.t_def(ids[c], c) for c in FULL}
    Y['2025-26'] = V.live_targets(ids['2025-26'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in ORIG}
    nf = sum(n[c] for c in FULL)
    w = {c: n[c] / nf for c in FULL}
    r2, rho = Z.r2, Z.rho

    def fold(a, c):
        d = D[a][c]
        out = {'R2': r2(d['ovr'], Y[c])}
        if c in FULL:
            out['rhoDEF_epmD'], _ = rho(d['def'], YE[c]); out['rhoDEF_T'], _ = rho(d['def'], YT[c])
            out['rhoDEF_rapmD'], _ = rho(d['def'], YD[c]); out['R2_rapm'] = r2(d['ovr'], YR[c])
        return out

    F = {a: {c: fold(a, c) for c in ORIG} for a in ARMS}
    rng = np.random.default_rng(SEED)
    idx = {c: np.where(np.isfinite(Y[c]))[0] for c in FULL}
    draws = [{c: rng.choice(idx[c], len(idx[c])) for c in FULL} for _ in range(B)]
    base_bs = [sum(w[c] * r2(D['B0'][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) for dr in draws]
    keys = ('R2', 'rhoDEF_epmD', 'rhoDEF_T', 'rhoDEF_rapmD', 'R2_rapm')
    res = {'n_primary': n, 'arms': {}}
    for a in ARMS:
        res['arms'][a] = {'folds': F[a], 'combined': {k: float(sum(w[c] * F[a][c][k] for c in FULL)) for k in keys},
                          'missing_names': {c: D[a][c]['miss'] for c in ORIG}}
    B0 = res['arms']['B0']
    for a in ARMS[1:]:
        ar = res['arms'][a]
        fc = {t: fitted_coef(a, t) for t in ORIG}
        ar['fitted_coef'] = fc
        s1 = all(fc[t] is not None for t in ORIG) and all(all(fc[t][k]['perUnit'] > 1e-9 for t in ORIG) for k in EXTRA[a])
        dd = {k: ar['combined'][k] - B0['combined'][k] for k in keys}
        per = {c: {k: F[a][c][k] - F['B0'][c][k] for k in F[a][c]} for c in ORIG}
        bs = [sum(w[c] * r2(D[a][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) - b0 for dr, b0 in zip(draws, base_bs)]
        s2 = dd['R2'] >= -0.005 and all(per[c]['R2'] >= -0.010 for c in FULL)
        s3 = dd['rhoDEF_epmD'] >= -0.010
        ar.update(delta=dd, delta_fold=per, ci90_dR2=[float(np.percentile(bs, 5)), float(np.percentile(bs, 95))],
                  gates={'S1': bool(s1), 'S2': bool(s2), 'S3': bool(s3)}, candidate=bool(s1 and s2 and s3),
                  improved={'dR2>0': dd['R2'] > 0, 'dEPMD>0': dd['rhoDEF_epmD'] > 0, 'dT>0': dd['rhoDEF_T'] > 0},
                  vs_B0={c: {'n_ovr_diff>=3': int((np.abs(D[a][c]['ovr'] - D['B0'][c]['ovr']) >= 3).sum()),
                             'max_abs_ovr_diff': float(np.abs(D[a][c]['ovr'] - D['B0'][c]['ovr']).max())} for c in ORIG})
    cands = [a for a in ('B2', 'B1', 'B3') if res['arms'][a]['candidate']]
    res['adopt_candidate'] = 'B2' if 'B2' in cands else (max(cands, key=lambda a: res['arms'][a]['delta']['rhoDEF_epmD']) if cands else None)
    res['examples'] = {}
    for c in ['2024-25', '2025-26']:
        d0 = D['B0'][c]
        bigs = [nm for nm, p, o in sorted(zip(d0['all_names'], d0['all_pos'], d0['all_ovr']), key=lambda t: -t[2]) if p == 'C'][:10]
        show = NAMED + [b for b in bigs if b not in NAMED]
        ex = {}
        for a in ARMS:
            d = D[a][c]; v, o, nm = d['all_def'], d['all_ovr'], d['all_names']
            ex[a] = {s: ({'def_rank': int((v > v[nm.index(s)]).sum() + 1), 'ovr_rank': int((o > o[nm.index(s)]).sum() + 1)} if s in nm else None) for s in show}
        res['examples'][c] = {'n_pop': len(d0['all_names']), 'bigs': bigs, 'by_arm': ex}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print('B0 combined', {k: round(v, 4) for k, v in B0['combined'].items()})
    for a in ARMS[1:]:
        ar = res['arms'][a]
        print(f"== {a} cand={ar['candidate']} gates={ar['gates']} improved={ar['improved']} ci90={[round(x, 4) for x in ar['ci90_dR2']]}")
        print('   d', {k: round(v, 4) for k, v in ar['delta'].items()})
        for c in ORIG:
            print('   ', c, {k: round(v, 4) for k, v in ar['delta_fold'][c].items()}, ar['vs_B0'][c],
                  {k: (round(v['perUnit'], 3), round(v['perSD'], 3), round(v['seSD'], 3)) for k, v in (ar['fitted_coef'][c] or {}).items()})
    print('missing', {a: res['arms'][a]['missing_names'] for a in ARMS})
    for c in res['examples']:
        print('--', c, 'n', res['examples'][c]['n_pop'])
        for s in res['examples'][c]['by_arm']['B0']:
            print('  ', s, {a: (x['def_rank'], x['ovr_rank']) if (x := res['examples'][c]['by_arm'][a][s]) else None for a in ARMS})
    print('adopt_candidate', res['adopt_candidate'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
