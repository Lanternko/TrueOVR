"""E-079 第一階段：RAPM 層前瞻檢驗。python phase1.py select | test
select：4 個舊目標季 x 5 個 d 的 MSE，選 d*（只用舊季）。test：d* != 1 才做；主檢驗 2025-26、補充 2024-25、球員層 Spearman、CV lambda 敏感度。
"""
import json, sys, time
from pathlib import Path
import numpy as np
import rapm_recency as RR

HERE = Path(__file__).parent
D_GRID = RR.D_GRID
SEL_TARGETS = ['2017-18', '2018-19', '2019-20', '2020-21']
MAIN = ('2025-26', ['2022-23', '2023-24', '2024-25'])
SUPP = ('2024-25', ['2022-23', '2023-24'])
BOOT_SEED, BOOT_N = 20261029, 2000


def window_of(target, n=3):
    i = RR.SEASON_IDX[target]
    return RR.ALL_SEASONS[i - n:i]


def pred_stats(D, target, fit, intercept_mode='own'):
    """target 季每筆 stint 的 s = sum O - sum D（窗口內沒有係數的球員為 0），回傳 y, w, s, 比賽索引。"""
    d = D.s[target]
    coef = np.zeros(D.K + 1)
    for p, a in fit.items():
        j = D.pidx[p]; coef[j] = a['O']; coef[D.P + j] = a['D']
    s = d['X'] @ coef            # 截距欄係數為 0
    return d['y'], d['w'], np.asarray(s).ravel()


def mse(y, w, s, c=None):
    if c is None: c = (w * y).sum() / w.sum()
    return float((w * (y - c - s) ** 2).sum() / w.sum())


def get_fit(D, window, d, lam_mode):
    if lam_mode == 'fixed':
        fit, _ = D.fit(window, d, RR.LAMBDA); return fit, RR.LAMBDA
    lam, _ = D.fit_cv(window, d)
    fit, _ = D.fit(window, d, lam); return fit, lam


def select(D, lam_mode='fixed'):
    table = {}
    for t in SEL_TARGETS:
        W = window_of(t)
        table[t] = {}
        for d in D_GRID:
            fit, lam = get_fit(D, W, d, lam_mode)
            y, w, s = pred_stats(D, t, fit)
            table[t][d] = {'mse': mse(y, w, s), 'lambda': lam}
        print(t, {d: round(v['mse'], 4) for d, v in table[t].items()}, flush=True)
    avg = {d: float(np.mean([table[t][d]['mse'] for t in SEL_TARGETS])) for d in D_GRID}
    best = min(avg.values())
    # 平均差 < 1e-6 視為同分，取較大的 d
    dstar = max(d for d in D_GRID if avg[d] - best < 1e-6)
    return table, avg, dstar


def boot_delta(D, target, window, d_list, lam_mode, fits=None):
    """每個 d 相對 d=1 的 Delta = MSE(d) - MSE(1)；以比賽重抽，兩候選共用抽樣；截距在每次重抽內重算。"""
    dd = D.s[target]
    gids, inv = np.unique(dd['gid'], return_inverse=True)
    G = len(gids)
    y, w = dd['y'], dd['w']
    def agg(s):
        f = lambda v: np.bincount(inv, weights=v, minlength=G)
        return np.stack([f(w), f(w * y), f(w * y * y), f(w * s), f(w * s * s), f(w * y * s)])
    stats, point = {}, {}
    for d in d_list:
        fit = fits[d] if fits else get_fit(D, window, d, lam_mode)[0]
        yy, ww, s = pred_stats(D, target, fit)
        stats[d] = agg(s); point[d] = mse(yy, ww, s)
    rng = np.random.default_rng(BOOT_SEED)
    counts = np.stack([np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(BOOT_N)])  # (B,G)
    def boot_mse(a):
        T = counts @ a.T            # (B,6): sw, swy, swyy, sws, swss, swys
        sw, swy, swyy, sws, swss, swys = T.T
        c = swy / sw
        sse = swyy + c * c * sw + swss - 2 * c * swy - 2 * swys + 2 * c * sws
        return sse / sw
    bm = {d: boot_mse(stats[d]) for d in d_list}
    out = {}
    for d in d_list:
        delta = bm[d] - bm[1.0]
        out[d] = {'mse': point[d], 'delta': point[d] - point[1.0], 'lo90': float(np.percentile(delta, 5)), 'hi90': float(np.percentile(delta, 95)),
                  'bootMean': float(delta.mean())}
    # 變體：截距固定為全季平均（報告用）
    c0 = (w * y).sum() / w.sum()
    return out


def player_spearman(D, target, window, d_list, lam_mode):
    tfit, _ = D.fit([target], 1.0, RR.LAMBDA)
    res = {}
    for d in d_list:
        fit, _ = D.fit(window, d, RR.LAMBDA)
        ps = [p for p in fit if p in tfit and fit[p]['poss'] >= 2000 and tfit[p]['poss'] >= 2000]
        res[d] = {'n': len(ps), 'spearman': RR.spearman([fit[p]['net'] for p in ps], [tfit[p]['net'] for p in ps])}
    return res


def jdump(o, name):
    (HERE / name).write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    mode = sys.argv[1]
    D = RR.Data()
    if mode == 'select':
        t0 = time.time()
        table, avg, dstar = select(D)
        print('avg', avg, 'd*', dstar, time.time() - t0)
        sp = {t: player_spearman(D, t, window_of(t), D_GRID, 'fixed') for t in SEL_TARGETS}
        jdump({'lambda': RR.LAMBDA, 'dGrid': D_GRID, 'targets': SEL_TARGETS,
               'mse': {t: {str(d): v for d, v in table[t].items()} for t in table}, 'avgMSE': {str(d): v for d, v in avg.items()},
               'dStar': dstar, 'windows': {t: window_of(t) for t in SEL_TARGETS}, 'playerSpearman': {t: {str(d): v for d, v in sp[t].items()} for t in sp}},
              'phase1-select.json')
    elif mode == 'test':
        sel = json.loads((HERE / 'phase1-select.json').read_text(encoding='utf-8'))
        dstar = sel['dStar']
        assert dstar != 1.0, 'd*=1：不做檢驗'
        res = {'dStar': dstar}
        for name, (t, W) in (('main', MAIN), ('supp', SUPP)):
            r = boot_delta(D, t, W, D_GRID, 'fixed')
            res[name] = {'target': t, 'window': W, 'byD': {str(d): v for d, v in r.items()},
                         'playerSpearman': {str(d): v for d, v in player_spearman(D, t, W, D_GRID, 'fixed').items()}}
            print(name, {d: (round(v['delta'], 5), round(v['lo90'], 5), round(v['hi90'], 5)) for d, v in r.items()}, flush=True)
        # 敏感度：窗口內 5 折 CV 選 lambda
        table, avg, dstar_cv = select(D, 'cv')
        r = boot_delta(D, MAIN[0], MAIN[1], D_GRID, 'cv')
        res['sensitivityCV'] = {'dStar': dstar_cv, 'avgMSE': {str(d): v for d, v in avg.items()},
                                'lambdas': {t: {str(d): v['lambda'] for d, v in table[t].items()} for t in table},
                                'main': {str(d): v for d, v in r.items()}}
        jdump(res, 'phase1-test.json')
