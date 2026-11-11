"""E-227 MDE（R-159）：只用訓練季（2021-22..2025-26）的 split=train，folds 1-4 擬合、fold 0 評估（驗證折，不是測試；測試場次不在目錄）。
臂：R2-abil、R2-stats、R2-stats-rapm（調參後選定設定、5 seed 平均預測，來自 results/preds-*.npy）；基準 B0 聯盟平均、B1-<臂>（同特徵加法模型）。
主指標：stint 淨值誤差＝回合加權 MSE，淨值＝100·(ptsA−ptsB)/P，P＝(possA+possB)/2，預測＝100·(μA·possA−μB·possB)/P。
MDE＝2×成對 90% 半寬（依場次 bootstrap 2000 次）：R2-stats−R2-abil 與 R2-stats−B1-stats（主）；R2-stats-rapm 同樣兩個比較（rapm 臂判定用）。取兩者較大。
判定 2 的門檻：每回合得分 MSE（單邊）、失誤二項 log loss、進攻籃板二項 log loss，各自 2×成對(臂−R2-abil) 90% 半寬（相對 R2-abil；同時列出相對 B1 供參考）。
用法：python -I -X utf8 mde_noise.py（在本目錄執行；先備好 results/preds-*.npy 與 tuning.json）"""
import glob, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e227_b1 import fit_b1, nll_vec
from e227_common import ARMS, HERE, SEASONS, load_rows
from e227_model import season_means, tensors

B = 2000
sig = lambda x: 1 / (1 + np.exp(-x))


def main():
    rows = load_rows(SEASONS)
    tr = [r for r in rows if r['fold'] != 0]; ev = [r for r in rows if r['fold'] == 0]
    means = season_means(tr)
    games = sorted({r['gid'] for r in ev}); gmap = {g: k for k, g in enumerate(games)}; G = len(games)
    gi = np.array([gmap[r['gid']] for r in ev]); gi2 = np.repeat(gi, 2)
    models, lam = {}, {}; ye = None
    for arm, kind in ARMS.items():
        pts, ptov, porb, ye, lam[arm] = fit_b1(tr, tensors(tr, kind, means, 'train'), ev, tensors(ev, kind, means, 'val'))
        models['B1-' + kind] = (pts, ptov, porb)
        fs = sorted(glob.glob(os.path.join(HERE, 'results', f'preds-{arm}-[0-9].npy'))); assert len(fs) >= 5, f'{arm}: 需要 5 seed，現有 {len(fs)}'
        P = np.stack([np.load(f) for f in fs[:5]])   # [seed, N, 2, 3]
        models[arm] = (P[..., 0].mean(0).reshape(-1), sig(P[..., 1]).mean(0).reshape(-1), sig(P[..., 2]).mean(0).reshape(-1))
    pts2, poss2, tov2, orb2, opp2, mean2 = ye.T
    tv = {s: sum(r['tova'] + r['tovb'] for r in tr if r['season'] == s) / sum(r['possa'] + r['possb'] for r in tr if r['season'] == s) for s in SEASONS}
    ob = {s: sum(r['orba'] + r['orbb'] for r in tr if r['season'] == s) / sum(r['rebOppa'] + r['rebOppb'] for r in tr if r['season'] == s) for s in SEASONS}
    sea2 = np.repeat([r['season'] for r in ev], 2)
    models['B0'] = (np.zeros_like(poss2), np.array([tv[s] for s in sea2]), np.array([ob[s] for s in sea2]))
    possA = poss2[0::2]; possB = poss2[1::2]; Pw = (possA + possB) / 2
    actual = np.where(Pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw, 1e-9), 0); m = mean2
    rate = np.where(poss2 > 0, pts2 / np.maximum(poss2, 1e-9), m) - m
    res = {}
    for name, (pts, ptov, porb) in models.items():
        muA, muB = pts[0::2] + m[0::2], pts[1::2] + m[1::2]
        pred = 100 * (muA * possA - muB * possB) / np.maximum(Pw, 1e-9)
        res[name] = {'net': (np.bincount(gi, Pw * (actual - pred) ** 2, G), np.bincount(gi, Pw, G)),
                     'ptsSide': (np.bincount(gi2, poss2 * (rate - pts) ** 2, G), np.bincount(gi2, poss2, G)),
                     'tovLL': (np.bincount(gi2, nll_vec(ptov, np.minimum(tov2, poss2), poss2), G), np.bincount(gi2, poss2, G)),
                     'orbLL': (np.bincount(gi2, nll_vec(porb, np.minimum(orb2, opp2), opp2), G), np.bincount(gi2, opp2, G))}
    rng = np.random.default_rng(20261103)
    draws = np.stack([np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(B)]).astype(float)

    def val(k, met):
        n, d = res[k][met]; return n.sum() / d.sum()

    def paired(a, b, met='net'):
        na, da = res[a][met]; nb, db = res[b][met]
        d = (draws @ na) / (draws @ da) - (draws @ nb) / (draws @ db); lo, hi = np.percentile(d, [5, 95])
        return {'point': round(float(val(a, met) - val(b, met)), 5), 'ci90': [round(float(lo), 5), round(float(hi), 5)],
                'halfWidth90': round(float((hi - lo) / 2), 5), 'sd': round(float(d.std()), 5)}

    out = {'seasons': SEASONS, 'fitRows': len(tr), 'evalStints': len(ev), 'evalGames': G, 'evalPoss': round(float(Pw.sum() * 2)),
           'mse': {k: round(float(val(k, 'net')), 2) for k in res},
           'sideMetrics': {k: {'ptsSideMSE': round(float(val(k, 'ptsSide')), 5), 'tovLogLoss': round(float(val(k, 'tovLL')), 5), 'orbLogLoss': round(float(val(k, 'orbLL')), 5)} for k in res},
           'b1Lambda': lam, 'paired': {}, 'arms': {}}
    A0 = 'R2-abil'
    for arm, kind in ARMS.items():
        b1 = 'B1-' + kind
        out['paired'][f'{arm}−{b1}'] = paired(arm, b1); out['paired'][f'{b1}−B0'] = paired(b1, 'B0'); out['paired'][f'{arm}−B0'] = paired(arm, 'B0')
        if arm != A0:
            out['paired'][f'{arm}−{A0}'] = paired(arm, A0)
            vsA = out['paired'][f'{arm}−{A0}']; vsB = out['paired'][f'{arm}−{b1}']
            out['arms'][arm] = {'mdeVsAbil': round(2 * vsA['halfWidth90'], 3), 'mdeVsB1': round(2 * vsB['halfWidth90'], 3),
                                'mde': round(2 * max(vsA['halfWidth90'], vsB['halfWidth90']), 3),
                                'guard2VsAbil': {met: {**paired(arm, A0, met), 'threshold': round(2 * paired(arm, A0, met)['halfWidth90'], 5)} for met in ('ptsSide', 'tovLL', 'orbLL')},
                                'guard2VsB1_reportOnly': {met: {**paired(arm, b1, met), 'threshold': round(2 * paired(arm, b1, met)['halfWidth90'], 5)} for met in ('ptsSide', 'tovLL', 'orbLL')}}
    out['paired']['R2-stats-rapm−R2-stats'] = paired('R2-stats-rapm', 'R2-stats')
    out['mde'] = {'value': out['arms']['R2-stats']['mde'], 'valueRapmArm': out['arms']['R2-stats-rapm']['mde'],
                  'rule': '2×成對 90% 半寬，取 (臂−R2-abil) 與 (臂−同特徵B1) 兩者較大；R2-stats 臂為主判定'}
    out['note'] = 'MSE 單位：(每 100 回合淨值)²，回合加權；只用訓練季 split=train 的 fold 0 評估（驗證折，不是測試），測試場次不在本目錄。'
    json.dump(out, open(os.path.join(HERE, 'mde-noise.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ('mse', 'sideMetrics', 'b1Lambda', 'arms', 'mde')}, ensure_ascii=False, indent=1))
    print(json.dumps(out['paired'], ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
