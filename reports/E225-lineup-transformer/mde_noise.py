"""E-225 第一版 MDE（R-157）：只用訓練季（2021-22..2024-25）的 split=train，folds 1-4 擬合、fold 0 評估（不碰 test／前向季，L-026）。

臂：T-min、T-nomin（Transformer，調參後選定設定、5 seed 平均預測，來自 results/preds-*.npy）；基準 B0 聯盟平均、B1-min／B1-nomin（同特徵加法模型，e225_b1.py）。
主指標：stint 淨值誤差＝回合加權 MSE，淨值＝100·(ptsA−ptsB)/P，P＝(possA+possB)/2，預測＝100·(μA·possA−μB·possB)/P。
MDE 定義（本版改為以「同特徵 B1」為準，不再用 B1-id）：每臂 MDE＝2×成對（T−同特徵 B1）90% 半寬（依場次 bootstrap 2000 次）；
正式 MDE＝兩臂取大者（舊草稿 22.214 的定義是 2×(B1−B1-id) 半寬，存在 previous 欄）。
判定 2 的門檻（凍結前量好）：單邊每回合得分 MSE、失誤二項 log loss、進攻籃板二項 log loss 的 T−B1 成對 90% 半寬×2（每臂各自）。
用法：python -I -X utf8 reports/E225-lineup-transformer/mde_noise.py
"""
import glob, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_b1 import fit_b1, nll
from e225_common import HERE, load_rows
from e225_model import ARMS, SEASONS, season_means

B = 2000
PREV_DRAFT = 22.214


def sig(x):
    return 1 / (1 + np.exp(-x))


def main():
    rows = load_rows(SEASONS)
    tr = [r for r in rows if r['fold'] != 0]; ev = [r for r in rows if r['fold'] == 0]
    games = sorted({r['gid'] for r in ev}); gmap = {g: k for k, g in enumerate(games)}; G = len(games)
    gi = np.array([gmap[r['gid']] for r in ev]); gi2 = np.repeat(gi, 2)
    prevB = json.load(open(os.path.join(HERE, 'mde-noise.json'), encoding='utf-8'))
    prevB = prevB.get('previous') or {k: v for k, v in prevB.items() if k != 'previous'}
    models = {}   # name -> (pts_dev[2N], p_tov[2N], p_orb[2N])
    lam = {}
    ye = None
    for arm, use_min in ARMS.items():
        predict, lam[arm], means = fit_b1(tr, [r['fold'] for r in tr], use_min)
        pts, ptov, porb, ye = predict(ev)
        models['B1-' + arm[2:]] = (pts, ptov, porb)
        fs = sorted(glob.glob(os.path.join(HERE, 'results', f'preds-{arm}-*.npy')))
        assert len(fs) >= 5, f'{arm}: 需要 5 seed 的 preds，現有 {len(fs)}'
        P = np.stack([np.load(f) for f in fs[:5]])   # [seed, N, 2, 3]
        models[arm] = (P[..., 0].mean(0).reshape(-1), sig(P[..., 1]).mean(0).reshape(-1), sig(P[..., 2]).mean(0).reshape(-1))
        lam[arm + '-seeds'] = [os.path.basename(f) for f in fs[:5]]
    pts2, poss2, tov2, orb2, opp2, mean2 = ye.T
    models['B0'] = (np.zeros_like(poss2), None, None)
    # B0 的失誤率／籃板率：訓練 folds 的該季聯盟率
    tv = {s: sum(r['tova'] + r['tovb'] for r in tr if r['season'] == s) / sum(r['possa'] + r['possb'] for r in tr if r['season'] == s) for s in SEASONS}
    ob = {s: sum(r['orba'] + r['orbb'] for r in tr if r['season'] == s) / sum(r['rebOppa'] + r['rebOppb'] for r in tr if r['season'] == s) for s in SEASONS}
    sea2 = np.repeat([r['season'] for r in ev], 2)
    models['B0'] = (models['B0'][0], np.array([tv[s] for s in sea2]), np.array([ob[s] for s in sea2]))

    possA = poss2[0::2]; possB = poss2[1::2]; Pw = (possA + possB) / 2
    actual = np.where(Pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw, 1e-9), 0)
    m = mean2
    rate = np.where(poss2 > 0, pts2 / np.maximum(poss2, 1e-9), m) - m
    res = {}   # name -> {metric: (per-game numerator, per-game denominator)}
    for name, (pts, ptov, porb) in models.items():
        muA, muB = pts[0::2] + m[0::2], pts[1::2] + m[1::2]
        pred = 100 * (muA * possA - muB * possB) / np.maximum(Pw, 1e-9)
        res[name] = {
            'net': (np.bincount(gi, Pw * (actual - pred) ** 2, G), np.bincount(gi, Pw, G)),
            'ptsSide': (np.bincount(gi2, poss2 * (rate - pts) ** 2, G), np.bincount(gi2, poss2, G)),
            'tovLL': (np.bincount(gi2, [nll(ptov[i:i + 1], np.minimum(tov2, poss2)[i:i + 1], poss2[i:i + 1]) for i in range(len(poss2))], G), np.bincount(gi2, poss2, G)),
            'orbLL': (np.bincount(gi2, [nll(porb[i:i + 1], np.minimum(orb2, opp2)[i:i + 1], opp2[i:i + 1]) for i in range(len(opp2))], G), np.bincount(gi2, opp2, G)),
        }
    rng = np.random.default_rng(20261103)
    draws = np.stack([np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(B)]).astype(float)   # [B, G]

    def val(k, met, c=None):
        n, d = res[k][met]
        return n.sum() / d.sum() if c is None else (c @ n) / (c @ d)

    def paired(a, b, met='net'):
        na, da = res[a][met]; nb, db = res[b][met]
        d = (draws @ na) / (draws @ da) - (draws @ nb) / (draws @ db); pt = val(a, met) - val(b, met)
        lo, hi = np.percentile(d, [5, 95])
        return {'point': round(float(pt), 5), 'ci90': [round(float(lo), 5), round(float(hi), 5)], 'halfWidth90': round(float((hi - lo) / 2), 5), 'sd': round(float(d.std()), 5)}

    out = {'seasons': SEASONS, 'fitRows': len(tr), 'evalStints': len(ev), 'evalGames': G, 'evalPoss': round(float(Pw.sum() * 2)),
           'mse': {k: round(float(val(k, 'net')), 2) for k in res},
           'sideMetrics': {k: {'ptsSideMSE': round(float(val(k, 'ptsSide')), 5), 'tovLogLoss': round(float(val(k, 'tovLL')), 5), 'orbLogLoss': round(float(val(k, 'orbLL')), 5)} for k in res},
           'b1Lambda': {k: lam[k] for k in ('T-min', 'T-nomin')},
           'tSeeds': {k: lam[k + '-seeds'] for k in ARMS}, 'paired': {}, 'arms': {}}
    for arm in ARMS:
        b1 = 'B1-' + arm[2:]
        out['paired'][f'{arm}−{b1}'] = paired(arm, b1)
        out['paired'][f'{b1}−B0'] = paired(b1, 'B0')
        out['paired'][f'{arm}−B0'] = paired(arm, 'B0')
        guards = {met: paired(arm, b1, met) for met in ('ptsSide', 'tovLL', 'orbLL')}
        out['arms'][arm] = {'mde': round(2 * out['paired'][f'{arm}−{b1}']['halfWidth90'], 3),
                            'guard2': {met: {**g, 'threshold': round(2 * g['halfWidth90'], 5)} for met, g in guards.items()}}
    out['paired']['T-min−T-nomin'] = paired('T-min', 'T-nomin')
    out['mde'] = {'perArm': {a: out['arms'][a]['mde'] for a in ARMS}, 'previousDraft': PREV_DRAFT,
                  'value': round(max(out['arms'][a]['mde'] for a in ARMS), 3),
                  'rule': '兩臂 2×成對(T−同特徵B1) 90% 半寬取大'}
    out['note'] = 'MSE 單位：(每 100 回合淨值)²，回合加權；只用訓練季 split=train 的 fold 0 評估（驗證折，不是測試），test／前向季未讀。'
    out['previous'] = prevB
    json.dump(out, open(os.path.join(HERE, 'mde-noise.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ('mse', 'sideMetrics', 'b1Lambda', 'arms', 'mde')}, ensure_ascii=False, indent=1))
    print(json.dumps(out['paired'], ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
