"""E-289 M3：E-288 前瞻台，RIMc（help／blk36／cont2pt36）對 REBc（rebound／orebPct／drebPct）加分，參考 CON、CPOS。
用法（repo root）：python -I -B -X utf8 reports/E289-rim-vs-reb-T/e289_bench.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


E = mod('e288', 'reports/E288-center-underrated/e288_eval.py')
V, Q, M = E.V, E.Q, E.M
FOLDS, NEXT, FULL, GRID = E.FOLDS, E.NEXT, E.FULL, E.GRID
SEED, B = 20261289, 2000
DATA = ROOT / 'reports/E227-lineup-transformer-r2/data'
RIM = ['help', 'blk36', 'cont2pt36']; REB = ['rebound', 'orebPct', 'drebPct']
CAND = ['RIMc', 'REBc', 'CON']; ARMS = CAND + ['CPOS']
SHOW = E.SHOW + ['Evan Mobley', 'Walker Kessler', 'Daniel Gafford', 'Mitchell Robinson', 'Clint Capela']


def table(t):
    out = {}
    for fn in (f'players-{t}.csv', f'stats-{t}.csv'):
        for r in csv.DictReader(open(DATA / fn, encoding='utf-8')):
            d = out.setdefault(r['pid'], {})
            for k, v in r.items():
                if k not in ('pid', 'name', 'pos'):
                    d[k] = float(v) if v not in ('', None) else None
    return out


def comp(d, tab, cs):
    n = len(d['ids']); zs = []
    for c in cs:
        v = np.full(n, np.nan)
        for i, p in enumerate(d['ids']):
            x = (tab.get(str(p)) or {}).get(c)
            if x is not None:
                v[i] = x
        k = np.isfinite(v); z = np.zeros(n); z[k] = (v[k] - v[k].mean()) / v[k].std(); zs.append(z)
    return np.clip(np.mean(zs, 0), 0, 1.5)


def main():
    assert E.sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'
    D = {c: E.build(c) for c in FOLDS}
    cover = {}
    for c in FOLDS:
        tab = table(c); d = D[c]; ref = d['P_ref']
        for nm, cs in (('RIMc', RIM), ('REBc', REB)):
            v = comp(d, tab, cs)
            d['P'][nm] = v * ref / np.sqrt((v ** 2).mean())
        cover[c] = float(np.mean([str(p) in tab for p in d['ids']]))
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}
    Y['2025-26'] = V.live_targets(D['2025-26']['ids'])['epm']
    YR = {c: Q.target(D[c]['ids'], NEXT[c], 'rapm') for c in FULL}
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}
    w = {t: n[t] / sum(n.values()) for t in FOLDS}; w3 = {t: n[t] / sum(n[c] for c in FULL) for t in FULL}
    rng = np.random.default_rng(SEED)
    boot = [{t: rng.choice(np.where(np.isfinite(Y[t]))[0], n[t]) for t in FOLDS} for _ in range(B)]
    base_gap = {pv: float(np.concatenate([E.gap(D[c], Y[c], D[c]['ovr'], pv) for c in FOLDS]).mean()) for pv in ('PG', 'SG', 'SF', 'PF', 'C')}
    res = {'prereg_sha256': E.sha(HERE / 'preregistration.md'), 'n': n, 'T_table_cover': cover, 'base_gap': base_gap, 'arms': {}}
    print('base gap', {k: round(v, 3) for k, v in base_gap.items()}, 'cover', cover)
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
        r = {'folds': f4, 'mean_all': float(sum(w[t] * f4[t]['all'] for t in FOLDS)), '_bs': bs,
             'ci90': [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))], 'n_pos': int(sum(f4[t]['all'] > 0 for t in FOLDS)),
             'mean_G': float(sum(w[t] * f4[t]['G'] for t in FOLDS)),
             'gap_after': {pv: float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], Pm[t], f4[t]['lambda']), pv) for t in FOLDS]).mean()) for pv in ('PG', 'SG', 'SF', 'PF', 'C')},
             'rapm': float(sum(w3[t] * (Q.metrics(D[t], YR[t], E.adj(D[t], Pm[t], f4[t]['lambda']))['all'] - Q.metrics(D[t], YR[t], D[t]['ovr'])['all']) for t in FULL)),
             'lambda_star': max(GRID, key=lambda l: np.mean([rho[c][l] for c in FOLDS]))}
        # 2025-26 名次
        d = D['2025-26']; o0, o1 = d['ovr'], E.adj(d, Pm['2025-26'], r['lambda_star'])
        r0 = (-o0).argsort().argsort() + 1; r1 = (-o1).argsort().argsort() + 1; nm = d['names']
        t10, t10_0 = [nm[i] for i in np.argsort(-o1)[:10]], [nm[i] for i in np.argsort(-o0)[:10]]
        newb = [x for i, x in enumerate(nm) if x in t10 and x not in t10_0 and d['pos'][i] in ('PF', 'C') and x not in E.TOP_BIGS_OK]
        drops = [nm[i] for i in range(len(nm)) if r0[i] <= 30 and r1[i] - r0[i] > 10]
        r['rank'] = {'r001_new_bigs': newb, 'top30_drops': drops, 'show': {x: [int(r0[nm.index(x)]), int(r1[nm.index(x)])] for x in SHOW if x in nm}}
        c1 = r['mean_all'] >= .005 and r['ci90'][0] > -.005; c2 = r['n_pos'] >= 3
        c3 = r['gap_after']['C'] <= base_gap['C'] / 2 and r['mean_G'] >= -.01; c4 = not newb and len(drops) <= 1
        if arm == 'CPOS':
            r['verdict'] = 'control'
        else:
            r['checks'] = [bool(c1), bool(c2), bool(c3), bool(c4)]
            r['verdict'] = 'adopt_candidate' if (c1 and c2 and c3 and c4) else ('structural_partial' if (c3 and c4 and r['mean_all'] >= -.003 and r['ci90'][0] > -.01) else 'reject')
        res['arms'][arm] = r
    d = res['arms']['RIMc']['_bs'] - res['arms']['REBc']['_bs']
    res['RIMc_minus_REBc'] = {'mean': float(res['arms']['RIMc']['mean_all'] - res['arms']['REBc']['mean_all']),
                              'ci90': [float(np.percentile(d, 5)), float(np.percentile(d, 95))]}
    for arm in ARMS:
        r = res['arms'][arm]; r.pop('_bs', None)
        print(f"== {arm:5s} {r['verdict']:18s} Δall={r['mean_all']:+.4f} [{r['ci90'][0]:+.4f},{r['ci90'][1]:+.4f}] pos={r['n_pos']}/4 ΔG={r['mean_G']:+.4f} "
              f"RAPM={r['rapm']:+.4f} λ={[r['folds'][t]['lambda'] for t in FOLDS]} gapC {base_gap['C']:+.3f}->{r['gap_after']['C']:+.3f} PF->{r['gap_after']['PF']:+.3f}")
        print('   ', r['rank'])
    print('RIMc-REBc', res['RIMc_minus_REBc'])
    (HERE / 'bench_results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
