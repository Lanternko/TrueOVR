"""E-195（F-136 擬合端診斷）：卡片為什麼把切入型排得比 T6 高。定義見 diag_plan.md（跑前凍結）。
用法（repo root）：python -I -B -X utf8 reports/F136-fit-side/diag.py   → results.json
只讀 E-190 的 work/；暫存寫在本目錄 work/；不改卡、不提採用。"""
import contextlib, csv, hashlib, importlib.util, io, json, os, sys
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E190 = ROOT / 'reports/card-0.2.10c+E190-creation-jumper'
CW = ROOT / 'reports/E180-pass-pool-creation-interact/calibrate_wing_t.py'
F133 = ROOT / 'reports/F133-drive-scoring/results.json'
WORK = HERE / 'work'
SEED, B = 20261101, 2000
ARMS = ['KJ', 'KA']
STEPS = ['S0', 'S0r', 'S1', 'S2', 'S3', 'S4', 'S4m', 'S5']          # 步驟表順序
CHAIN = ['S0', 'S1', 'S2', 'S3', 'S4', 'S5']                          # 增量鏈


def _load(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


M = _load('e190e', E190 / 'e190_eval.py')
P, HIST = M.P, M.HIST


def pct(x):
    return rankdata(np.asarray(x, float)) / len(x)


def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def pear(x, y):
    return float(np.corrcoef(x, y)[0, 1])


def wpear(x, y, w):
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    c = np.average((x - mx) * (y - my), weights=w)
    return float(c / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w)))


def ci(v):
    v = np.asarray(v, float)
    return [float(np.nanpercentile(v, 5)), float(np.nanpercentile(v, 95))]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------- 在行程內重跑卡建置（只為取得擬合池／權重） ----------------
def rebuild(arm, t, outdir):
    base = E190 / 'work' / f'base-{arm}-{t}' / t
    cmd = (base / 'cards/K0/primary/run.log').read_text(encoding='utf-8').splitlines()[0].split()
    args = cmd[1:]
    i = args.index('--out')
    args[i + 1] = str(outdir)
    os.environ['E134_CFG'] = str(base / 'calib-primary.json')
    cw = _load(f'cw_{arm}_{t}', CW)
    cap = {}
    o = cw.load

    def ld(p):
        r = o(p)
        cap['rows'] = r
        return r
    cw.load = ld
    cwd = os.getcwd()
    os.chdir(ROOT)
    argv0 = sys.argv
    sys.argv = [str(CW)] + args
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cw.main()
    finally:
        sys.argv = argv0
        os.chdir(cwd)
    return cw, cap['rows']


def read_rank(p):
    return {r['name']: r for r in csv.DictReader(open(p, encoding='utf-8-sig'))}


def load_season(arm, t):
    base = E190 / 'work' / f'base-{arm}-{t}' / t
    od = WORK / f'rebuild-{arm}-{t}'
    od.mkdir(parents=True, exist_ok=True)
    cw, rows = rebuild(arm, t, od)
    summ = json.loads((od / 'summary.json').read_text(encoding='utf-8'))
    bsum = json.loads((base / 'cards/K0/primary/summary.json').read_text(encoding='utf-8'))
    f, bf = summ['formula'], bsum['formula']
    b = np.array(f['coefficientsOnStandardized'])
    cdiff = float(np.max(np.abs(b - np.array(bf['coefficientsOnStandardized']))))
    assert cdiff < 1e-9 and abs(f['intercept'] - bf['intercept']) < 1e-9, (arm, t, cdiff)
    ranking_same = sha(od / 'ranking.csv') == sha(base / 'cards/K0/primary/ranking.csv')
    rk = read_rank(od / 'ranking.csv')
    X, mean, sd = cw.design(rows, 'position-interactions')
    ATT = list(cw.ATTRS)
    assert len(ATT) == 14 and X.shape[1] == 30 and len(b) == 30
    y = np.array([r['y'] for r in rows])
    mc = np.array([r['mc'] for r in rows])
    s2 = float(summ['residualTrueVariancePer36'])
    w = 1.0 / (mc + s2)
    icpt = float(f['intercept'])
    pred0 = icpt + X @ b
    names = [r['name'] for r in rows]
    assert len(set(names)) == len(names)
    assert max(abs(pred0[i] - float(rk[n]['pred0'])) for i, n in enumerate(names)) < 0.0011
    # 驗證 (y, w, X, λ=1) 能重現係數
    lam = 1.0
    b_chk = cw.wfit(X, y, w, lam)
    chk_diff = float(np.max(np.abs(b_chk - np.r_[icpt, b])))
    assert chk_diff < 1e-6, ('wfit mismatch', arm, t, chk_diff)
    # S0 截斷、S0r 重擬合（14 欄主效應）
    S0 = icpt + X[:, :14] @ b[:14]
    b14 = cw.wfit(X[:, :14], y, w, lam)
    S0r = np.c_[np.ones(len(X)), X[:, :14]] @ b14
    # T6fit：0.75·N − mu_pos（mu_pos 由 poss≥1000 的列 mu = 0.75N − r 反推）
    poss = np.array([r['poss'] for r in rows], float)
    N = np.array([r['N'] for r in rows], float)
    rr = np.array([r['r'] for r in rows], float)
    pos = np.array([r['pos'] for r in rows])
    mu = {}
    for p in sorted(set(pos)):
        sel = (pos == p) & (poss >= 1000) & ~np.isnan(rr)
        v = 0.75 * N[sel] - rr[sel]
        assert v.size and np.ptp(v) < 1e-9, (p, np.ptp(v))
        mu[p] = float(v[0])
    t6fit = np.array([0.75 * N[i] - mu[pos[i]] if not np.isnan(N[i]) else np.nan for i in range(len(rows))])
    pool = {'names': names, 'pos': pos, 'MIN': np.array([r['MIN'] for r in rows], float), 'poss': poss, 'y': y, 'w': w,
            'zdrive': X[:, ATT.index('drive')], 'pred0': pred0, 'S0': S0, 'S0r': S0r, 't6fit': t6fit, 'N': N,
            'y_is_zero': (np.abs(y) == 0.0) & (poss < 1000)}
    # 評估人群
    d = M.s_data(t, (arm,))
    ids = d['ids']
    popd, _ = P.pop_of(t)
    n2 = {}
    for p_, i_ in popd.items():
        n2.setdefault(P.norm(i_['name']), []).append(p_)
    orow = {}
    for r in csv.DictReader(open(M.rpath(arm, t), encoding='utf-8-sig')):
        if float(r['MIN']) < 500:
            continue
        c = n2.get(P.norm(r['name'])) or []
        if len(c) == 1:
            orow[c[0]] = r
    er = [orow[p] for p in ids]
    nm = [r['name'] for r in er]
    ix = np.array([names.index(n) for n in nm])
    t6raw_all = {int(r['playerId']): float(r['pooledNet']) for r in csv.DictReader(open(base / 'rapm-R.csv', encoding='utf-8-sig'))}
    t6raw = np.array([t6raw_all.get(p, np.nan) for p in ids])
    ev = {'t': t, 'ids': ids, 'n': len(ids), 'names': nm, 'pool_ix': ix, 'pos': pos[ix],
          'drive': d[arm]['drive'], 'ovr': d[arm]['ovr'], 't6raw': t6raw, 't6fit': t6fit[ix],
          'poss': poss[ix], 'zdrive': pool['zdrive'][ix], 'w': w[ix]}
    g = lambda k, rowsrc: np.array([float(r[k]) for r in rowsrc])
    prim = [rk[n] for n in nm]
    ev['S0'], ev['S0r'], ev['S1'] = S0[ix], S0r[ix], pred0[ix]
    ev['S2'] = ev['S1'] + g('defenseBonus', prim)
    ev['S3'] = ev['S2'] + g('align', prim)
    ev['S4'] = g('predictedPer36', prim)
    ev['S4m'] = g('ovr36', er)
    ev['S5'] = ev['ovr']
    ev['mpg'] = g('mpg', er)
    assert np.max(np.abs(ev['S4'] - g('predictedPer36', er))) < 1e-9
    assert np.max(np.abs(ev['drive'] - g('drive', er))) < 1e-9
    ev['uncapped_gap_max'] = float(np.max(np.abs(ev['S3'] - ev['S4'])))
    # t6raw 與池內 N 核對
    both = ~np.isnan(t6raw) & ~np.isnan(N[ix])
    chk = {'n_both': int(both.sum()), 'maxdiff_t6raw_vs_N': float(np.max(np.abs(t6raw[both] - N[ix][both]))) if both.any() else None,
           'n_ok_t6fit_nan': int((~np.isnan(t6raw) & np.isnan(N[ix])).sum())}
    meta = {'coef_maxdiff_vs_card': cdiff, 'wfit_maxdiff': chk_diff, 'ranking_csv_identical': bool(ranking_same), 's2': s2,
            'n_pool': len(rows), 'n_pool_poss1000': int((poss >= 1000).sum()), 'n_pool_y_zero': int(pool['y_is_zero'].sum()),
            'n_pool_min500': int((pool['MIN'] >= 500).sum()), 'mu_pos': mu, 'alpha_blend_y_equals_r': bool(np.allclose(y[poss >= 1000], rr[poss >= 1000])),
            'weight_min': float(w.min()), 'weight_max': float(w.max()), 'weight_share_y_zero': float(w[pool['y_is_zero']].sum() / w.sum()),
            't6_check': chk, 'uncapped_gap_max': ev['uncapped_gap_max']}
    return pool, ev, meta


# ---------------- 統計 ----------------
def step_vals(ev, k):
    return ev[k]


def season_stats(ev, idx, detail=False):
    """idx＝評估人群重抽（點估計＝arange）。回傳 dict（V1/V2/V3/VD/top25/mpg）。"""
    drive = ev['drive'][idx]
    t6 = ev['t6raw'][idx]
    t6f = ev['t6fit'][idx]
    ok = ~np.isnan(t6)
    ok3 = ok & ~np.isnan(t6f)
    top = drive >= np.percentile(drive, 75)
    out = {'n_sub': int(ok.sum()), 'n_ok3': int(ok3.sum())}
    ds = drive[ok]
    pt6 = pct(t6[ok])
    d3 = drive[ok3]
    pt6f = pct(t6f[ok3])
    z = ev['zdrive'][idx]
    e1 = {}
    for k in STEPS:
        v = ev[k][idx]
        e = pt6 - pct(v)[ok]
        e1[k] = e
        out[f'V1_{k}'] = sp(ds, e)
        out[f'V2_{k}'] = sp(ds, pt6 - pct(v[ok]))
        out[f'V3_{k}'] = sp(d3, pt6f - pct(v[ok3]))
        out[f'top_e_{k}'] = float(e[top[ok]].mean())
        out[f'rest_e_{k}'] = float(e[~top[ok]].mean())
        out[f'topdiff_e_{k}'] = out[f'top_e_{k}'] - out[f'rest_e_{k}']
        if k in ('S0', 'S0r', 'S1', 'S2', 'S3', 'S4'):
            out[f'VDp_{k}'] = pear(d3, t6f[ok3] - v[ok3])
            out[f'VDs_{k}'] = sp(d3, t6f[ok3] - v[ok3])
    out['mpg_sp_drive'] = sp(drive, ev['mpg'][idx])
    # 跑後補（post-hoc，非 diag_plan 預註冊；只加不改前面的定義）
    out['PH_sp_drive_T6raw'] = sp(ds, t6[ok])
    for k in ('S1', 'S4', 'S5'):
        out[f'PH_sp_drive_{k}'] = sp(ds, ev[k][idx][ok])
    out['PH_sd_ratio_S1_over_T6fit'] = float(np.std(ev['S1'][idx][ok3]) / np.std(t6f[ok3]))
    out['PH_sp_T6fit_S1'] = sp(t6f[ok3], ev['S1'][idx][ok3])
    # Step 2 (d)：評估人群（有 T6fit）值差 vs 名次差，及 poss≥1000 子集
    e_pos = ev['poss'][idx] >= 1000
    s_ = ok3
    out['E_pear_val'] = pear(d3, t6f[ok3] - ev['S1'][idx][ok3])
    out['E_sp_rank'] = sp(d3, pt6f - pct(ev['S1'][idx][ok3]))
    out['E_sp_val'] = sp(d3, t6f[ok3] - ev['S1'][idx][ok3])
    s1 = ok3 & e_pos
    if s1.sum() > 10:
        out['E1_pear_val'] = pear(drive[s1], t6f[s1] - ev['S1'][idx][s1])
        out['E1_sp_rank'] = sp(drive[s1], pct(t6f[s1]) - pct(ev['S1'][idx][s1]))
    else:
        out['E1_pear_val'] = out['E1_sp_rank'] = float('nan')
    out['E_wpear_val'] = wpear(d3, t6f[ok3] - ev['S1'][idx][ok3], ev['w'][idx][ok3])
    out['n_E'] = int(ok3.sum())
    out['n_E1'] = int(s1.sum())
    if detail:
        out['_e'] = e1
        out['_ok'] = ok
    return out


def pool_stats(pool, idx):
    z = pool['zdrive'][idx]
    res = pool['y'][idx] - pool['pred0'][idx]
    w = pool['w'][idx]
    m500 = pool['MIN'][idx] >= 500
    p1 = pool['poss'][idx] >= 1000
    out = {}
    out['a_wpear_A'] = wpear(z, res, w)
    out['b_pear_A'] = pear(z, res)
    out['c_pear_B'] = pear(z[m500], res[m500])
    out['a_wpear_A1'] = wpear(z[p1], res[p1], w[p1])
    out['b_pear_A1'] = pear(z[p1], res[p1])
    sel = m500 & p1
    out['c_pear_B1'] = pear(z[sel], res[sel])
    out['c_wpear_B'] = wpear(z[m500], res[m500], w[m500])
    out['n_A'], out['n_B'], out['n_A1'], out['n_B1'] = int(len(z)), int(m500.sum()), int(p1.sum()), int(sel.sum())
    return out


def wavg(per, key, ns):
    tot = sum(ns[t] for t in HIST)
    return sum(ns[t] / tot * per[t][key] for t in HIST)


def run_arm(arm, data, boot=True):
    pool = {t: data[t][0] for t in HIST}
    ev = {t: data[t][1] for t in HIST}
    per = {t: season_stats(ev[t], np.arange(ev[t]['n']), detail=True) for t in HIST}
    pper = {t: pool_stats(pool[t], np.arange(len(pool[t]['y']))) for t in HIST}
    ns_sub = {t: per[t]['n_sub'] for t in HIST}
    ns_E = {t: per[t]['n_E'] for t in HIST}
    ns_E1 = {t: per[t]['n_E1'] for t in HIST}
    ns_full = {t: ev[t]['n'] for t in HIST}
    npool = {t: pper[t]['n_A'] for t in HIST}
    nB = {t: pper[t]['n_B'] for t in HIST}
    nA1 = {t: pper[t]['n_A1'] for t in HIST}
    nB1 = {t: pper[t]['n_B1'] for t in HIST}
    # 每個鍵用哪一組人數加權（固定在點估計的人數）
    def wts(key):
        if key.startswith(('a_', 'b_')):
            return nA1 if key.endswith('A1') else npool
        if key.startswith('c_'):
            return nB1 if key.endswith('B1') else nB
        return None

    ekeys = [k for k in per[HIST[0]] if not k.startswith('_') and k not in ('n_sub', 'n_ok3', 'n_E', 'n_E1')]
    ew = {k: (ns_E1 if k.startswith('E1_') else ns_E if k.startswith(('E_', 'VD', 'V3')) else ns_sub) for k in ekeys}
    point = {k: wavg(per, k, ew[k]) for k in ekeys}
    pkeys = [k for k in pper[HIST[0]] if not k.startswith('n_')]
    ppoint = {k: wavg(pper, k, wts(k)) for k in pkeys}
    res = {'n_full': ns_full, 'n_sub': ns_sub, 'n_E': ns_E, 'n_E1': ns_E1, 'n_pool': npool, 'n_poolB': nB,
           'point_pooled': point, 'pool_point_pooled': ppoint,
           'per_season': {t: {k: per[t][k] for k in ekeys} for t in HIST},
           'pool_per_season': {t: pper[t] for t in HIST}}
    if boot:
        rng = np.random.default_rng(SEED)
        db = {k: [] for k in ekeys}
        dp = {k: [] for k in pkeys}
        for _ in range(B):
            pb, qb = {}, {}
            for t in HIST:
                ie = rng.integers(0, ev[t]['n'], ev[t]['n'])
                ip = rng.integers(0, len(pool[t]['y']), len(pool[t]['y']))
                pb[t] = season_stats(ev[t], ie)
                qb[t] = pool_stats(pool[t], ip)
            for k in ekeys:
                db[k].append(wavg(pb, k, ew[k]))
            for k in pkeys:
                dp[k].append(wavg(qb, k, wts(k)))
        res['ci90_pooled'] = {k: ci(db[k]) for k in ekeys}
        res['se_pooled'] = {k: float(np.nanstd(db[k], ddof=1)) for k in ekeys}
        res['pool_ci90'] = {k: ci(dp[k]) for k in pkeys}
        res['pool_se'] = {k: float(np.nanstd(dp[k], ddof=1)) for k in pkeys}
        res['draws'] = B
    return res, per


def top10_table(ev):
    """三季評估人群（有 T6）依 drive 降冪前 10：T6 名次（子群內）→ S0…S5 名次（全人群）。"""
    cand = []
    for si, t in enumerate(HIST):
        e = ev[t]
        ok = ~np.isnan(e['t6raw'])
        rk_t6 = rankdata(-e['t6raw'][ok], method='min')
        okidx = np.where(ok)[0]
        rks = {k: rankdata(-e[k], method='min') for k in STEPS}
        for j, i in enumerate(okidx):
            cand.append((-float(e['drive'][i]), si, int(i), t, e['names'][i], int(rk_t6[j]), int(ok.sum()), int(e['n']),
                         {k: int(rks[k][i]) for k in STEPS}, float(e['drive'][i])))
    cand.sort(key=lambda c: (c[0], c[1], c[2]))
    return [{'season': c[3], 'name': c[4], 'drive': c[9], 'rank_T6': c[5], 'n_sub': c[6], 'n_full': c[7], **{f'rank_{k}': c[8][k] for k in STEPS}}
            for c in cand[:10]]


def main():
    (HERE / 'logs').mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    out = {'seed': SEED, 'draws': B, 'steps': STEPS, 'chain': CHAIN, 'definition': 'diag_plan.md', 'arms': {}, 'meta': {}}
    for arm in ARMS:
        data = {t: load_season(arm, t) for t in HIST}
        out['meta'][arm] = {t: data[t][2] for t in HIST}
        res, per = run_arm(arm, data)
        ev = {t: data[t][1] for t in HIST}
        res['top10_drive'] = top10_table(ev)
        out['arms'][arm] = res
    # 閘門：KJ S5 的 E-194 跨季 efit
    ref = json.loads(F133.read_text(encoding='utf-8'))['D1']['pooled']['S_drive_efit']['point']
    got = out['arms']['KJ']['point_pooled']['V1_S5']
    out['gate'] = {'E194_pooled_S_drive_efit': ref, 'this_V1_S5': got, 'absdiff': abs(got - ref)}
    assert abs(got - ref) < 1e-9, (got, ref)
    a = out['arms']['KJ']['pool_point_pooled']['a_wpear_A']
    out['accept_2a'] = {'a_wpear_A_pooled_KJ': a, 'abs_lt_0.02': abs(a) < 0.02}
    (HERE / 'results.json').write_text(json.dumps(out, sort_keys=True, indent=1, default=float, ensure_ascii=False), encoding='utf-8')
    print('gate', out['gate'], 'accept_2a', out['accept_2a'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
