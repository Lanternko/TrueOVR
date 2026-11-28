"""E-290 評估：預註冊 preregistration.md（凍結 sha 見 preregistration.sha256）。
REBc 籃板加分，2025-26 折用真正的 card 0.2.13a，前三折用 E-164 歷史卡。
用法（repo root）：python -I -B -X utf8 reports/E290-reb-bonus-0213a/e290_eval.py"""
import csv, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


# 台子：暫存資料夾放 ranking-S-<t>.csv（前三折＝E-164，2025-26＝card 0.2.13a），並把 E-288 平台的卡路徑指過去
E164 = ROOT / 'reports/card-0.2.9+E164-no-stamina'
CARD0213A = ROOT / 'reports/card-0.2.13a/ranking.csv'
STAGE = HERE / 'stage'
STAGE.mkdir(exist_ok=True)
for t in ('2022-23', '2023-24', '2024-25'):
    shutil.copyfile(E164 / f'ranking-S-{t}.csv', STAGE / f'ranking-S-{t}.csv')
shutil.copyfile(CARD0213A, STAGE / 'ranking-S-2025-26.csv')

E = mod('e288', 'reports/E288-center-underrated/e288_eval.py')
E.CARD = STAGE
E.Q.E.E164 = STAGE
V, Q, M = E.V, E.Q, E.M
FOLDS, NEXT, FULL, GRID = E.FOLDS, E.NEXT, E.FULL, E.GRID
SEED, B = 20261290, 2000
DATA = ROOT / 'reports/E227-lineup-transformer-r2/data'
ARMS = ['REBc', 'CON', 'MIX', 'CPOS']
CAND = ['REBc', 'CON', 'MIX']
OK_BIGS = {'Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren', 'Evan Mobley'}
SHOW = ['Rudy Gobert', 'Jarrett Allen', 'Isaiah Hartenstein', 'Ivica Zubac', 'Jakob Poeltl', 'Myles Turner', 'Mitchell Robinson',
        'Walker Kessler', 'Bam Adebayo', 'Domantas Sabonis', 'Alperen Sengun', 'Evan Mobley', 'Steven Adams',
        'Nikola Jokić', 'Victor Wembanyama']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stats_tab(t):
    out = {}
    for r in csv.DictReader(open(DATA / f'stats-{t}.csv', encoding='utf-8')):
        out[r['pid']] = {k: (float(r[k]) if r[k] not in ('', None) else None) for k in ('orebPct', 'drebPct')}
    return out


def zcol(v):
    k = np.isfinite(v); z = np.zeros(len(v))
    if k.sum() > 1:
        z[k] = (v[k] - v[k].mean()) / v[k].std()
    return z


def rescale(v, ref):
    m = np.sqrt((v ** 2).mean())
    return v * ref / m if m > 0 else v


def add_arms(c, d):
    card = {r['name']: r for r in csv.DictReader(open(STAGE / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
    tab = stats_tab(c)
    n = len(d['ids'])
    reb = np.array([float(card[nm]['rebound']) for nm in d['names']])
    ob = np.full(n, np.nan); db = np.full(n, np.nan)
    for i, p in enumerate(d['ids']):
        x = tab.get(str(p))
        if x:
            if x['orebPct'] is not None: ob[i] = x['orebPct']
            if x['drebPct'] is not None: db[i] = x['drebPct']
    rebc = np.clip((zcol(reb) + zcol(ob) + zcol(db)) / 3, 0, 1.5)
    ref = d['P_ref']
    P_reb = rescale(rebc, ref)
    P_con = d['P']['CON']
    d['P']['REBc'] = P_reb
    d['P']['MIX'] = rescale(.5 * P_reb + .5 * P_con, ref)
    d['stats_cover'] = float(np.mean(np.isfinite(ob) & np.isfinite(db)))


def main():
    assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'
    D = {c: E.build(c) for c in FOLDS}
    for c in FOLDS:
        add_arms(c, D[c])
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}
    Y['2025-26'] = V.live_targets(D['2025-26']['ids'])['epm']
    YR = {c: Q.target(D[c]['ids'], NEXT[c], 'rapm') for c in FULL}
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}
    w = {t: n[t] / sum(n.values()) for t in FOLDS}; w3 = {t: n[t] / sum(n[c] for c in FULL) for t in FULL}
    rng = np.random.default_rng(SEED)
    boot = [{t: rng.choice(np.where(np.isfinite(Y[t]))[0], n[t]) for t in FOLDS} for _ in range(B)]
    base_gap = {pv: float(np.concatenate([E.gap(D[c], Y[c], D[c]['ovr'], pv) for c in FOLDS]).mean()) for pv in ('PG', 'SG', 'SF', 'PF', 'C')}
    base_gap_fold = {c: float(E.gap(D[c], Y[c], D[c]['ovr'], 'C').mean()) for c in FOLDS}
    res = {'prereg_sha256': sha(HERE / 'preregistration.md'), 'card0213a_sha256': sha(CARD0213A),
           'live_epm_sha256': sha(E.LIVEF), 'stats_sha256': {c: sha(DATA / f'stats-{c}.csv') for c in FOLDS},
           'e164_sha256': {t: sha(E164 / f'ranking-S-{t}.csv') for t in ('2022-23', '2023-24', '2024-25')},
           'n': n, 'stats_cover': {c: D[c]['stats_cover'] for c in FOLDS}, 'base_gap': base_gap, 'base_gap_C_fold': base_gap_fold, 'arms': {}}
    print('base gap', {k: round(v, 3) for k, v in base_gap.items()}, base_gap_fold, 'cover', res['stats_cover'])
    d = D['2025-26']
    for arm in ARMS:
        Pm = {c: D[c]['P'][arm] for c in FOLDS}
        rho = {c: {l: float(Q.metrics(D[c], Y[c], E.adj(D[c], Pm[c], l))['all']) for l in GRID} for c in FOLDS}
        f4 = {}
        for t in FOLDS:
            lam = max(GRID, key=lambda l: np.mean([rho[c][l] for c in FOLDS if c != t]))
            m0, m1 = Q.metrics(D[t], Y[t], D[t]['ovr']), Q.metrics(D[t], Y[t], E.adj(D[t], Pm[t], lam))
            f4[t] = {'lambda': lam, 'all': float(m1['all'] - m0['all']), 'G': float(m1['G'] - m0['G'])}
        bs = np.array([sum(w[t] * (Q.metrics(D[t], Y[t], E.adj(D[t], Pm[t], f4[t]['lambda']), bm[t])['all']
                                   - Q.metrics(D[t], Y[t], D[t]['ovr'], bm[t])['all']) for t in FOLDS) for bm in boot])
        bs26 = np.array([Q.metrics(d, Y['2025-26'], E.adj(d, Pm['2025-26'], f4['2025-26']['lambda']), bm['2025-26'])['all']
                         - Q.metrics(d, Y['2025-26'], d['ovr'], bm['2025-26'])['all'] for bm in boot])
        lam_s = max(GRID, key=lambda l: np.mean([rho[c][l] for c in FOLDS]))
        r = {'folds': f4, 'mean_all': float(sum(w[t] * f4[t]['all'] for t in FOLDS)), '_bs': bs,
             'ci90': [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))],
             'fold2526_ci90': [float(np.percentile(bs26, 5)), float(np.percentile(bs26, 95))],
             'n_pos': int(sum(f4[t]['all'] > 0 for t in FOLDS)),
             'mean_G': float(sum(w[t] * f4[t]['G'] for t in FOLDS)),
             'gap_after': {pv: float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], Pm[t], f4[t]['lambda']), pv) for t in FOLDS]).mean()) for pv in ('PG', 'SG', 'SF', 'PF', 'C')},
             'gap_C_2526_after': float(E.gap(d, Y['2025-26'], E.adj(d, Pm['2025-26'], f4['2025-26']['lambda']), 'C').mean()),
             'rapm': float(sum(w3[t] * (Q.metrics(D[t], YR[t], E.adj(D[t], Pm[t], f4[t]['lambda']))['all'] - Q.metrics(D[t], YR[t], D[t]['ovr'])['all']) for t in FULL)),
             'lambda_star': lam_s, 'rho_grid': {t: {str(l): v for l, v in rho[t].items()} for t in FOLDS}}
        o0, o1 = d['ovr'], E.adj(d, Pm['2025-26'], lam_s)
        r0 = (-o0).argsort().argsort() + 1; r1 = (-o1).argsort().argsort() + 1; nm = d['names']
        t10, t10_0 = [nm[i] for i in np.argsort(-o1)[:10]], [nm[i] for i in np.argsort(-o0)[:10]]
        newb = [x for i, x in enumerate(nm) if x in t10 and x not in t10_0 and d['pos'][i] in ('PF', 'C') and x not in OK_BIGS]
        drops = [(nm[i], int(r0[i]), int(r1[i])) for i in range(len(nm)) if r0[i] <= 30 and r1[i] - r0[i] > 10]
        top30_moves = {nm[i]: [int(r0[i]), int(r1[i])] for i in range(len(nm)) if r0[i] <= 30 or r1[i] <= 30}
        r['rank'] = {'top10': t10, 'top10_before': t10_0, 'r001_new_bigs_violating': newb, 'top30_drops': drops,
                     'show': {x: [int(r0[nm.index(x)]), int(r1[nm.index(x)])] for x in SHOW if x in nm},
                     'top30_moves': top30_moves}
        c1 = r['mean_all'] >= .005 and r['ci90'][0] > -.005; c2 = r['n_pos'] >= 3
        c3 = (r['gap_after']['C'] <= base_gap['C'] / 2 and r['mean_G'] >= -.01) if base_gap['C'] > 0 else None
        c4 = (not newb) and len(drops) <= 1
        if arm == 'CPOS':
            r['verdict'] = 'control'
        else:
            r['checks'] = [bool(c1), bool(c2), c3 if c3 is None else bool(c3), bool(c4)]
            if c3 is None:
                r['verdict'] = 'adopt_candidate' if (c1 and c2 and c4) else 'reject'
            else:
                r['verdict'] = 'adopt_candidate' if (c1 and c2 and c3 and c4) else ('structural_partial' if (c3 and c4 and r['mean_all'] >= -.003 and r['ci90'][0] > -.01) else 'reject')
        res['arms'][arm] = r
    bsC = res['arms']['CPOS']['_bs']
    for arm in ARMS:
        r = res['arms'][arm]; df = r['_bs'] - bsC
        r['diff_vs_CPOS'] = {'mean': float(r['mean_all'] - res['arms']['CPOS']['mean_all']), 'ci90': [float(np.percentile(df, 5)), float(np.percentile(df, 95))]}
        r.pop('_bs')
        print(f"== {arm:5s} {r['verdict']:18s} Δall={r['mean_all']:+.4f} [{r['ci90'][0]:+.4f},{r['ci90'][1]:+.4f}] pos={r['n_pos']}/4 ΔG={r['mean_G']:+.4f} "
              f"RAPM={r['rapm']:+.4f} λ={[r['folds'][t]['lambda'] for t in FOLDS]} λ*={r['lambda_star']} fold26={r['folds']['2025-26']['all']:+.4f} {r['fold2526_ci90']} "
              f"gapC {base_gap['C']:+.3f}->{r['gap_after']['C']:+.3f} (26: {base_gap_fold['2025-26']:+.3f}->{r['gap_C_2526_after']:+.3f}) PF->{r['gap_after']['PF']:+.3f} vsCPOS {r['diff_vs_CPOS']['mean']:+.4f}")
        print('    checks', r.get('checks'), 'top10', r['rank']['top10'], 'viol', r['rank']['r001_new_bigs_violating'], 'drops', r['rank']['top30_drops'])
        print('    show', r['rank']['show'])
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
