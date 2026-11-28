"""賽中 OVR 逐點化（v5/pathA/disclosure-pointwise-ovr.md，使用者 2026-10-28 指示）。

凍結 v58 管線有兩處依當下人群名次：
  pr    = pred0 在 MIN>=500 球員裡的百分位 → bonus 的 taper
  T(A)  = 當下第 A 高的 pred → H1 封頂（固定點迭代）
賽中預測時這兩個參考改成開季（A＝先驗卡）算一次後固定，所以 OVR 只看球員自己的能力值：
能力值沒變，OVR 就不變。A 本身照原管線算（與原值差 <1e-8，建構時檢查）；答案卡不動。

pr 是經驗百分位（階梯函數），固定參考池後，能力值差 0.03 也可能跨過一個人、pr 跳 0.57、
bonus 經 taper 跳 1 分 OVR；改線性內插仍有 0.54（參考池裡 pred0 幾乎相同的兩人讓斜率很陡）。
所以 pr 直接固定為球員開季（A）的值：taper 與 bonus 整季不變，OVR 只經 pred0、align、封頂變動，
三者對能力值都是連續且斜率有界。c4-equiv-pointwise-trials.json 記了三種版本的 T1。
"""
import numpy as np

from ovr_pipeline import PR_HI, PR_LO, BONUS_MIN_POSS
from ovr_common import ATTRS


EXCLUDE_T = set()      # 0.2.12d：復出老將補卡的 pid 不進封頂表 T（否則新增的高 pred 會推動所有人的封頂門檻）


class PointwisePipeline:
    def __init__(self, pipe, attrs0):
        self.pipe = pipe
        ref = pipe.predict(attrs0)
        self.ref = ref
        self.pr0 = np.array([ref[p]['pr'] for p in pipe.pids])
        s = np.sort(np.array([ref[p]['pred'] for p in pipe.pids if p not in EXCLUDE_T]))[::-1]
        self.T = {a: float(s[min(max(int(a), 1), len(s)) - 1]) - 1e-12
                  for a in set(x for x in pipe.allowed if x is not None)}
        chk = self.predict(attrs0)
        self.check = max(abs(chk[p]['ovr'] - ref[p]['ovr']) for p in pipe.pids)
        if self.check >= 1e-8:
            raise RuntimeError(f'pointwise A != pipeline A ({self.check})')

    def predict(self, attrs_by_pid):
        P = self.pipe
        raw = np.array([[attrs_by_pid[p][a] for a in getattr(P, 'attrs', ATTRS)] for p in P.pids], float)
        pred0 = P.design(raw)
        pr = self.pr0
        taper = np.clip((PR_HI - pr) / (PR_HI - PR_LO), 0.0, 1.0)
        out = {}
        p1, p50, p99 = P.anchors
        for i, p in enumerate(P.pids):
            bonus = align = 0.0
            if P.poss[i] >= BONUS_MIN_POSS:
                bonus = max(0.0, P.centeredD[i]) * taper[i]
                align = 0.25 * (P.r[i] - pred0[i])
            pred = pred0[i] + bonus + align
            a = P.allowed[i]
            if a is not None and bonus + align > 0:
                pred = min(pred, max(pred0[i], self.T[a]))
            ovr = 40 + 30 * (pred - p1) / (p50 - p1) if pred <= p50 else 70 + 29 * (pred - p50) / (p99 - p50)
            out[p] = {'pred0': float(pred0[i]), 'bonus': float(bonus), 'align': float(align),
                      'pred': float(pred), 'ovr': float(ovr), 'pr': float(pr[i])}
        return out


_CACHE = {}


def for_start(C, start):
    """C = 已 install 的 v4_common；回傳該起點的逐點管線（A 參考由先驗卡算）。"""
    if start not in _CACHE:
        _, attrs0 = C.deployment(start)
        _CACHE[start] = PointwisePipeline(C.pipeline_for(start), attrs0)
    return _CACHE[start]
