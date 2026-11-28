"""E-223 訓練季（2024-25）：載入模擬結果 → M0／M1／M2 特徵 → 在訓練季擬合 k、(a,b) → 成對 bootstrap 求 MDE。
用法：python -I -X utf8 fit_train.py 2425   （2526 用 eval_oos.py，凍結後才跑）"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob, json, sys
import numpy as np
from scipy.optimize import minimize
from e223_lib import *

def load_sims(key):
    res = {}
    for f in glob.glob(str(HERE / f'work/sims-{key}/o-*.json')):
        for r in json.load(open(f))['res']:
            res[r['key']] = r
    return res

def features(key, zmap, zmiss, sims=None):
    """逐場特徵：m0＝模擬 Net 差（主−客，不含 H）、s＝Σ(min/240)·z 差（主−客）、b0＝上季淨效率差。"""
    S = load_season(key); lin = json.load(open(HERE / f'work/lineups-{key}.json')); sims = sims or load_sims(key)
    G = S['games']; n = len(G)
    home = np.array([g['home'] for g in G]); away = np.array([g['away'] for g in G])
    y = np.array([float(g['hs'] > g['as']) for g in G]); d = np.array([g['hs'] - g['as'] for g in G], float)
    sc = lambda r: sum(m / 240.0 * zmap.get(p, zmiss) for p, m in r)
    allz = [sc(r) for r in lin.values()]
    m0 = np.zeros(n); s = np.zeros(n)
    for g in G:
        i = g['i']
        # job key＝2*i+(side=='a')；msum/n＝該陣容打聯盟平均隊的平均分差
        mh = sims[2 * i]['msum'] / sims[2 * i]['n']; ma = sims[2 * i + 1]['msum'] / sims[2 * i + 1]['n']
        m0[i] = mh - ma; s[i] = sc(lin[f'{i}h']) - sc(lin[f'{i}a'])
    base = S['inp'][SEASONS[key]['base']]
    b0 = np.array([base[home[i]]['net'] - base[away[i]]['net'] for i in range(n)])
    return dict(S=S, home=home, away=away, y=y, d=d, m0=m0, s=s, b0=b0, ids=sorted(S['inp']['teams']), r=float(np.mean(allz)))

def brier(dh, y):
    p = np.clip(0.5 * (1 + np.vectorize(math.erf)(dh / SIGMA / math.sqrt(2))), 1e-6, 1 - 1e-6)
    return (p - y) ** 2, p

if __name__ == '__main__':
    key = sys.argv[1]
    zmap, zmiss, info = load_card(CARDS / SEASONS[key]['card'])
    F = features(key, zmap, zmiss)
    y = F['y']; n = len(y)
    pred = {'B0': F['b0'] + H, 'M0': F['m0'] + H}
    # M1：Net_diff = k·s（Σmin/240=1 時 r 抵銷；陣容不足 9 人時以 r 置中）
    k1 = minimize(lambda k: brier(k[0] * F['s'] + H, y)[0].mean(), [3.0], method='Nelder-Mead').x[0]
    ab = minimize(lambda v: brier(v[0] * F['m0'] + v[1] * F['s'] + H, y)[0].mean(), [0.5, 1.5], method='Nelder-Mead').x
    pred['M1'] = k1 * F['s'] + H; pred['M2'] = ab[0] * F['m0'] + ab[1] * F['s'] + H
    ids, home, away = F['ids'], F['home'], F['away']
    pg = {k: brier(v, y) for k, v in pred.items()}
    out = dict(n=n, k1=float(k1), a=float(ab[0]), b=float(ab[1]), r=F['r'], z_miss=zmiss, card=info,
               brier={k: float(v[0].mean()) for k, v in pg.items()}, win_mae={k: wins_mae(v[1], y, home, away, ids) for k, v in pg.items()})
    # 成對 bootstrap：場次重抽 2000 次（rng 20261102），90% CI；MDE＝M1／M2 對 M0 的 Brier 差分布的 95 百分位與 5 百分位絕對值較大者之半寬
    rng = np.random.default_rng(20261102); boots = [rng.integers(0, n, n) for _ in range(2000)]
    def pair(a, b, metric):
        if metric == 'brier':
            v = np.array([pg[a][0][ix].mean() - pg[b][0][ix].mean() for ix in boots])
        else:
            v = np.array([wins_mae(pg[a][1], y, home, away, ids, ix) - wins_mae(pg[b][1], y, home, away, ids, ix) for ix in boots])
        return dict(diff=float(v.mean()), lo=float(np.percentile(v, 5)), hi=float(np.percentile(v, 95)), half=float((np.percentile(v, 95) - np.percentile(v, 5)) / 2))
    out['pairs'] = {f'{a}-{b}': {m: pair(a, b, m) for m in ('brier', 'win')} for a, b in (('M1', 'M0'), ('M2', 'M0'), ('M0', 'B0'), ('M2', 'B0'), ('M1', 'B0'))}
    # 虛無情形（L-120）：M0 對自己加極小擾動不應退化成 0；這裡用「M0 對 M0 + 0.01·隨機」確認 half 非 0、非 NaN
    jit = np.random.default_rng(1).normal(0, 0.5, n); pj = brier(F['m0'] + jit + H, y)
    v = np.array([pj[0][ix].mean() - pg['M0'][0][ix].mean() for ix in boots]); out['null_check_half'] = float((np.percentile(v, 95) - np.percentile(v, 5)) / 2)
    json.dump(out, open(HERE / f'work/train-fit-{key}.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
