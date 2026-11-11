"""E-258 分析：12 臂（G50/G100/REL × W04/W05/W06/W08）對 E-255 T0；判定照 preregistration.md。
用法：python -I -B -X utf8 reports/E258-pnr-lowvol-gate/analyze_e258.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
E255 = HERE.parent / 'E255-pnr-handler-lineup-tf'
sys.path.insert(0, str(E255))
import analyze_e255 as A  # noqa: E402

VARS = ['G50', 'G100', 'REL']
WS = ['W04', 'W05', 'W06', 'W08']
SEED_P, SEED_G, B = 20261258, 20261107, 2000


def low_p90(var, w):
    A.P_JSON = json.loads((HERE / var / 'e255_players.json').read_text(encoding='utf-8'))
    tb = A.P_JSON['player_tables']['2024-25']; raw = tb['pnr_raw']
    from scipy.stats import rankdata
    import math
    md = tb['modes']['full']; ok = np.array(md['mask3']) > 0; rho = md['rho']
    z = (w * np.array(md['zv']) + (1 - w) * np.array(md['za'])) / math.sqrt(w * w + (1 - w) ** 2 + 2 * w * (1 - w) * rho)
    sc = np.zeros(len(z)); sc[ok] = rankdata(z[ok], method='average') / ok.sum() * 99
    low = [sc[i] for i, p in enumerate(tb['pids']) if ok[i] and raw.get(p, [0, 0, 0])[2] < 50]
    return float(np.percentile(low, 90))


def main():
    pre_ok = hashlib.sha256((HERE / 'preregistration.md').read_bytes()).hexdigest() == (HERE / 'preregistration.sha256').read_text().strip()
    y = {s: np.array(A.P_JSON['e179'][s]['O']) for s in A.E179_SEAS}
    t0 = json.loads((E255 / 'out-T0.json').read_text(encoding='utf-8'))
    p_t0 = A.ridge_cv_preds(A.make_m1(t0['e179']), y)
    r_t0, f_t0 = A.r2_pooled(y, p_t0)
    outs, m1, fold, sstd, preds, lp = {}, {}, {}, {}, {}, {}
    for v in VARS:
        for w in WS:
            a = f'{v}_{w}'
            outs[a] = json.loads((HERE / v / f'out-{w}.json').read_text(encoding='utf-8'))
            preds[a] = A.ridge_cv_preds(A.make_m1(outs[a]['e179']), y)
            r, pf = A.r2_pooled(y, preds[a]); m1[a] = round(r, 5); fold[a] = pf
            ss = [A.r2_pooled(y, A.ridge_cv_preds(A.make_m1(outs[a]['e179'], sd), y))[0] for sd in range(5)]
            sstd[a] = float(np.std(ss, ddof=1))
            lp[a] = round(low_p90(v, A.WV[w]), 1)
    ok1 = [a for a in m1 if lp[a] <= 70]
    best = max(ok1 or m1, key=lambda a: m1[a])
    v, w = best.split('_')
    gain = m1[best] - r_t0
    fg = {s: round(fold[best][s] - f_t0[s], 5) for s in A.E179_SEAS}
    rng = np.random.default_rng(SEED_P)
    idxs = [{t: rng.integers(0, len(y[t]), len(y[t])) for t in A.E179_SEAS} for _ in range(B)]
    bs = np.array([A.r2_pooled(y, preds[best], ix)[0] - A.r2_pooled(y, p_t0, ix)[0] for ix in idxs])
    ci = [round(float(np.percentile(bs, 5)), 5), round(float(np.percentile(bs, 95)), 5)]
    j = WS.index(w)
    nb = {f'{v}_{WS[x]}': round(m1[f'{v}_{WS[x]}'] - r_t0, 5) for x in (j - 1, j + 1) if 0 <= x < len(WS)}
    G = t0['cross_test']['games']; rg = np.random.default_rng(SEED_G)
    draws = np.stack([np.bincount(rg.integers(0, G, G), minlength=G) for _ in range(B)]).astype(float)
    cross = A.paired_game_bs(outs[best], t0, 'cross_test', 'pts', draws)
    cstd = float(np.std(t0['cross_test']['seed_pts100_mse'], ddof=1))
    gate = {'best': best, 'c1_low_p90': lp[best], 'c1_pass': lp[best] <= 70,
            'c2_gain': round(gain, 5), 'c2_need': round(max(0.005, 2 * sstd[best]), 5), 'c2_pass': gain >= max(0.005, 2 * sstd[best]),
            'c3_fold': fg, 'c3_pass': sum(x > 0 for x in fg.values()) >= 2, 'c4_ci90': ci, 'c4_pass': ci[0] > 0,
            'c5_neighbors': nb, 'c5_pass': all(x > 0 for x in nb.values()),
            'c6_cross': cross, 'c6_pass': cross['point'] <= 2 * cstd,
            'c7_vs_E255_W06': round(m1[best] - 0.23877, 5), 'c7_pass': m1[best] - 0.23877 >= -0.005}
    gate['all_pass'] = all(gate[k] for k in gate if k.endswith('_pass'))

    # 每點換算與例子（用 best 變體的 players json）
    A.P_JSON = json.loads((HERE / v / 'e255_players.json').read_text(encoding='utf-8'))
    X = np.vstack([np.column_stack(A.base_cols(s) + [A.score99(s, A.WV[w])]) for s in A.E179_SEAS])
    yy = np.concatenate([y[s] for s in A.E179_SEAS])
    b, mu, sd = A.ridge_fit(X, yy); coef = float(b[-2] / sd[-1])
    rb = np.random.default_rng(SEED_P + 1); cs = []
    for _ in range(B):
        ii = rb.integers(0, len(yy), len(yy)); bb, _, sdb = A.ridge_fit(X[ii], yy[ii]); cs.append(bb[-2] / sdb[-1])
    lo, hi = np.percentile(cs, [5, 95])
    per_point = {'O_per_point': round(coef, 5), 'ci90': [round(float(lo), 5), round(float(hi), 5)],
                 'wins_per_10pts_30mpg': round(coef * 10 * 30 / 48 * 2.7, 3),
                 'wins_ci90': [round(float(lo) * 10 * 30 / 48 * 2.7, 3), round(float(hi) * 10 * 30 / 48 * 2.7, 3)]}
    grp = {'G': ['PG', 'SG'], 'F': ['SF', 'PF'], 'C': ['C']}
    pos = {s: np.array(A.P_JSON['e179'][s]['pos']) for s in A.E179_SEAS}
    by_group = {g: {'T0': round(A.r2_pooled(y, p_t0, {t: np.where(np.isin(pos[t], ps))[0] for t in A.E179_SEAS})[0], 4),
                    best: round(A.r2_pooled(y, preds[best], {t: np.where(np.isin(pos[t], ps))[0] for t in A.E179_SEAS})[0], 4)} for g, ps in grp.items()}
    t = '2024-25'; d = A.P_JSON['e179'][t]; raw = A.P_JSON['player_tables'][t]['pnr_raw']
    rk = lambda q: np.argsort(np.argsort(-q)) + 1
    r0, rw, ra = rk(p_t0[t]), rk(preds[best][t]), rk(y[t]); sc = A.score99(t, A.WV[w])
    names = ('Deni Avdija', 'Cam Thomas', 'Paolo Banchero', 'Bam Adebayo', 'Pascal Siakam', 'Nickeil Alexander-Walker',
             'Jeremy Sochan', 'John Collins', 'Stephen Curry', 'Trae Young', 'Jalen Brunson', 'Tyrese Haliburton')
    ex = [{'name': d['names'][i], 'score': round(float(sc[i]), 1), 'poss': raw.get(str(d['ids'][i]), [0, 0, 0])[2],
           'rank_T0': int(r0[i]), 'rank_best': int(rw[i]), 'actual': int(ra[i])} for i, nm in enumerate(d['names']) if nm in names]
    res = {'prereg_sha256_ok': pre_ok, 'M1_T0': round(r_t0, 5), 'M1': m1, 'low_p90': lp,
           'seed_std': {k: round(x, 5) for k, x in sstd.items()}, 'gate': gate, 'per_point': per_point,
           'by_group': by_group, 'examples_2024_25': ex,
           'cross_pts100': {a: outs[a]['cross_test']['pts100_mse'] for a in outs} | {'T0': t0['cross_test']['pts100_mse']}}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=bool), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=1, default=bool))


if __name__ == '__main__':
    main()
