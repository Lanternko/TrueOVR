"""v58 H1-m0 凍結 OVR 管線（只換能力值，不重擬合）。

凍結內容（reports/ovr-v58-card-2025-26/card-H1-m0/summary.json）：
  迴歸截距／標準化係數／屬性 mean,sd、OVR 錨點 PR1/PR50/PR99、H1 封頂（ref=rapm、margin=0）。
RAPM 輸入依 §5.3 用 data/rapm-2022-25.csv（不含 2025-26）：
  r(i)        = 0.75·pooledNet − 同位置 MIN 加權平均（pooledPoss>=1000）
  centeredD(i)= 0.75·pooledD   − 同位置 MIN 加權平均（pooledPoss>=1000）
  rank(i)     = pooledNet 名次（pooledPoss>=5000）；allowed=max(1, ceil(rank-margin))
  bonus       = max(0,centeredD)·taper(PR(pred0))，taper=clip((96-PR)/6,0,1)
  align       = 0.25·(r − pred0)
  pred        = pred0+bonus+align；H1 只砍 lift>0 的人：pred=min(pred,max(pred0,T(allowed)))
MIN 用先驗季（2024-25）分鐘（§4.5「當日全部有先驗卡的球員」；不讀目標季 MIN）。
封頂門檻 T(A) 每次重算（固定點迭代）；其餘全部凍結。
"""
import csv
import json
import math

import numpy as np

from ovr_common import ATTRS

POS = ['PG', 'SG', 'SF', 'PF', 'C']
INTERACT = ['long', 'short', 'pass', 'rebound', 'help']
BLEND_POSS = 1000
BONUS_MIN_POSS = 5000
BLEND_PER36 = 0.75
PR_LO, PR_HI = 90.0, 96.0
SCALE_MIN_MINUTES = 500


def percentile_rank(x, ref_sorted):
    n = len(ref_sorted)
    if n <= 1:
        return 50.0
    below = sum(1 for v in ref_sorted if v < x)
    return 100.0 * below / (n - 1)


def cap_total_lift(pred, pred0, lift, allowed, pool=None):
    """pool：布林遮罩，只有 True 的人進封頂門檻表 T（0.2.12d 復出老將補卡不推動別人的門檻）；None＝全部。"""
    pred = pred.copy()
    for it in range(100):
        s = np.sort(pred if pool is None else pred[pool])[::-1]

        def T(a):
            return float(s[min(max(int(a), 1), len(s)) - 1]) - 1e-12

        changed = 0.0
        for i, a in enumerate(allowed):
            if a is None or lift[i] <= 0:
                continue
            v = min(pred[i], max(pred0[i], T(a)))
            changed = max(changed, pred[i] - v)
            pred[i] = v
        if changed < 1e-10:
            return pred, it + 1
    raise RuntimeError('H1 cap did not converge in 100 iterations')


class OVRPipeline:
    def __init__(self, summary_path, rapm_path, prior_cards):
        s = json.loads(open(summary_path, encoding='utf-8').read())
        # card 0.2.7c 起迴歸拿掉 physique：只用 summary 有的屬性（舊 summary 全有 → 與原本逐位元相同）
        self.attrs = [a for a in ATTRS if a in s['formula']['attributeMean']]
        self.mean = np.array([s['formula']['attributeMean'][a] for a in self.attrs], float)
        self.sd = np.array([s['formula']['attributeSD'][a] for a in self.attrs], float)
        self.b = np.array([s['formula']['intercept']] + s['formula']['coefficientsOnStandardized'], float)
        # E-180/E-187：card 0.2.10c 起位置交互項拿掉 pass（--dropInteract pass）→ 係數少 4 個；由係數個數判斷（舊 summary 仍用全部 INTERACT）
        k = (len(self.b) - 1 - len(self.attrs)) // 4
        assert len(self.b) - 1 == len(self.attrs) + 4 * k and k in (len(INTERACT), len(INTERACT) - 1), (len(self.b), len(self.attrs))
        self.interact = INTERACT if k == len(INTERACT) else [a for a in INTERACT if a != 'pass']
        self.anchors = (s['scaleAnchorsPer36']['PR1'], s['scaleAnchorsPer36']['PR50'],
                        s['scaleAnchorsPer36']['PR99'])
        self.pids = sorted(prior_cards)
        self.pos = [prior_cards[p]['pos'] for p in self.pids]
        self.minutes = np.array([float(prior_cards[p]['observed']['MIN']) for p in self.pids])
        rapm = {int(r['playerId']): r for r in csv.DictReader(open(rapm_path, encoding='utf-8'))}
        self.poss = np.array([float(rapm[p]['pooledPoss']) if p in rapm else 0.0 for p in self.pids])
        net = np.array([float(rapm[p]['pooledNet']) if p in rapm else 0.0 for p in self.pids])
        d = np.array([float(rapm[p]['pooledD']) if p in rapm else 0.0 for p in self.pids])
        # 同位置 MIN 加權平均（poss>=1000）
        self.r = np.zeros(len(self.pids))
        self.centeredD = np.zeros(len(self.pids))
        for pos in POS:
            idx = [i for i, p in enumerate(self.pids) if self.pos[i] == pos]
            elig = [i for i in idx if self.poss[i] >= BLEND_POSS]
            wsum = sum(self.minutes[i] for i in elig)
            if wsum > 0:
                muN = sum(self.minutes[i] * BLEND_PER36 * net[i] for i in elig) / wsum
                muD = sum(self.minutes[i] * BLEND_PER36 * d[i] for i in elig) / wsum
            else:
                muN = muD = 0.0
            for i in idx:
                if self.poss[i] >= BLEND_POSS:
                    self.r[i] = BLEND_PER36 * net[i] - muN
                    self.centeredD[i] = BLEND_PER36 * d[i] - muD
        # RAPM 名次（poss>=5000；以 pooledNet 降冪）
        pool = [i for i in range(len(self.pids)) if self.poss[i] >= BONUS_MIN_POSS]
        order = sorted(pool, key=lambda i: -net[i])
        rank = {i: k + 1 for k, i in enumerate(order)}
        self.allowed = [rank.get(i) for i in range(len(self.pids))]  # margin=0
        self.pr_mask = self.minutes >= SCALE_MIN_MINUTES
        self.name_by_pid = {p: prior_cards[p].get('name', '') for p in self.pids}
        self.summary_path = summary_path
        self.rapm_path = rapm_path

    def design(self, raw):
        z = (raw - self.mean) / self.sd
        cols = [z]
        pos_arr = np.array(self.pos)
        for p in POS[:-1]:
            d = (pos_arr == p).astype(float)[:, None]
            cols.append(d * z[:, [self.attrs.index(a) for a in self.interact]])
        X = np.hstack(cols)
        return np.c_[np.ones(len(X)), X] @ self.b

    def predict(self, attrs_by_pid):
        raw = np.array([[attrs_by_pid[p][a] for a in self.attrs] for p in self.pids], float)
        pred0 = self.design(raw)
        pr_pool = sorted(pred0[i] for i in range(len(pred0)) if self.pr_mask[i])
        pr = np.array([percentile_rank(v, pr_pool) for v in pred0])
        taper = np.clip((PR_HI - pr) / (PR_HI - PR_LO), 0.0, 1.0)
        bonus = np.zeros(len(pred0))
        align = np.zeros(len(pred0))
        for i in range(len(pred0)):
            if self.poss[i] >= BONUS_MIN_POSS:
                bonus[i] = max(0.0, self.centeredD[i]) * taper[i]
                align[i] = 0.25 * (self.r[i] - pred0[i])
        lift = bonus + align
        pred = pred0 + bonus + align
        pred, iters = cap_total_lift(pred, pred0, lift, self.allowed)
        p1, p50, p99 = self.anchors
        ovr = np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1),
                       70 + 29 * (pred - p50) / (p99 - p50))
        out = {}
        for i, p in enumerate(self.pids):
            out[p] = {'pred0': float(pred0[i]), 'bonus': float(bonus[i]), 'align': float(align[i]),
                      'pred': float(pred[i]), 'ovr': float(ovr[i]), 'pr': float(pr[i])}
        out['_capIterations'] = iters
        return out
