"""E-229 MDE：用 E-228 的 2025-26 逐場預測（T2425 權重，pred-T-2526.json）與 E-223 的 M0 邊際，從 1230 場隨機抽 n 場子集（不重複），
看成對 Brier 差（T−M0）的 90% bootstrap 區間（2000 次、5／95 百分位）半寬的典型值；另以「完全校準」的模擬結果得出 5 箱最大校準偏差的分布。
只讀 E-228 已存在的預測檔與 E-223 特徵（這些結果 E-228 已揭曉，不是 2026-27 資料）。  python -I -X utf8 mde.py"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
E223 = os.path.join(ROOT, 'reports', 'E223-team-rating')
sys.path.insert(0, E223)
import numpy as np
from e223_lib import H, SIGMA, CARDS, SEASONS, load_card
from fit_train import features

NS = (400, 470, 550); SUBSETS = 200; BOOT = 2000


def phi(x):
    return 0.5 * (1 + np.vectorize(math.erf)(np.asarray(x) / SIGMA / math.sqrt(2)))


def caldev(p, y, bins=5):
    o = np.argsort(p, kind='stable')
    return max(abs(p[ix].mean() - y[ix].mean()) for ix in np.array_split(o, bins))


def main():
    P = json.load(open(os.path.join(ROOT, 'reports', 'E228-transformer-team-rating', 'work', 'pred-T-2526.json')))
    zmap, zmiss, info = load_card(CARDS / SEASONS['2526']['card'])
    Fe = features('2526', zmap, zmiss); y = np.asarray(Fe['y'], float); n = len(y)
    mT = np.array(P['margin_seed']).mean(0); mM = np.asarray(Fe['m0'], float)
    pT = np.clip(phi(mT + H), 1e-6, 1 - 1e-6); pM = np.clip(phi(mM + H), 1e-6, 1 - 1e-6)
    bT, bM = (pT - y) ** 2, (pM - y) ** 2; d = bT - bM
    out = dict(nPool=n, fullBrier=dict(T=float(bT.mean()), M0=float(bM.mean())), fullDiff=float(d.mean()), full=[], note='2025-26 全 1230 場為 E-228 已揭曉；此處只量噪音大小')
    rng = np.random.default_rng(20261102)
    for m in NS:
        hw, diffs = [], []
        for _ in range(SUBSETS):
            sub = rng.choice(n, m, replace=False); dd = d[sub]
            bs = np.array([dd[rng.integers(0, m, m)].mean() for _ in range(BOOT)])
            lo, hi = np.percentile(bs, [5, 95]); hw.append((hi - lo) / 2); diffs.append(dd.mean())
        # 完全校準下的校準偏差分布：用 T 自己的 p 當真機率抽結果（噪音下限），及 T 在真實結果上的子集偏差
        null = [caldev(pT[s], (rng.random(m) < pT[s]).astype(float)) for s in (rng.choice(n, m, replace=False) for _ in range(1000))]
        real = [caldev(pT[s], y[s]) for s in (rng.choice(n, m, replace=False) for _ in range(SUBSETS))]
        pM_null = [caldev(pM[s], (rng.random(m) < pM[s]).astype(float)) for s in (rng.choice(n, m, replace=False) for _ in range(1000))]
        q = lambda v, k: float(np.percentile(v, k))
        out['full'].append(dict(n=m, halfWidth=dict(median=q(hw, 50), p10=q(hw, 10), p90=q(hw, 90)), diffSd=float(np.std(diffs)),
                                calDevNullT=dict(p50=q(null, 50), p90=q(null, 90), p95=q(null, 95)), calDevNullM0=dict(p95=q(pM_null, 95)),
                                calDevRealT=dict(p50=q(real, 50), p95=q(real, 95))))
        print(out['full'][-1], flush=True)
    json.dump(out, open(os.path.join(HERE, 'mde.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
