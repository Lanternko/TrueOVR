"""評分 M10（E-169，預註冊：reports/rating-m10-scurve/preregistration.md）：M6 加分斜坡改 S 形。

  T0 = TS_lg − λ·E；B = s·(2·λ·E·TSA + g·2·(TS_lg − TS_repl)·E)
  C2：s = clip(1 + (TS − T0)/0.20, 0, 1)²；Z1：s = smoothstep((TS − (T0 − 0.18))/0.26)；Z2：smoothstep((TS − (T0 − 0.15))/0.20)。
其餘同 rating_m6（λ、g、TS_lg、TSA36_lg、TS_repl、PACE_lg 沿用 M6 params），各臂只重定 a、c。
"""
import json
from pathlib import Path

import numpy as np

import rating_m4
from rating_m3 import Table
from rating_m6 import G_MULT, LAM

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m10-scurve'
ARMS = {'Z1': ('ss', 0.18, 0.26), 'Z2': ('ss', 0.15, 0.20), 'C2': ('pow', 0.20, 2.0)}  # 順序＝預註冊 §2 平手優先序


def bonus(t, C, kind, a, b):
    """回 (B 分, B_G, s, E)。kind='pow'：a＝δ、b＝次方；kind='ss'：起點 T0−a、寬 b。"""
    tsa = t.fga + 0.44 * t.fta
    E = np.maximum(0.0, tsa - C['TSA36_lg'] * t.mn / 36)
    ts = np.where(tsa > 0, t.pts / (2 * np.where(tsa > 0, tsa, 1)), 0.0)
    T0 = C['TS_lg'] - LAM * E
    if kind == 'pow':
        s = np.clip(1 + (ts - T0) / a, 0, 1) ** b
    else:
        u = np.clip((ts - (T0 - a)) / b, 0, 1)
        s = u * u * (3 - 2 * u)
    s = np.where(E > 0, s, 0.0)
    B = s * (2 * LAM * E * tsa + G_MULT * 2 * (C['TS_lg'] - C['TS_repl']) * E)
    return B, B * 100 * 48 / (36 * C['PACE_lg']), s, E


def score_arrays(t, P4, C, arm):
    """回 (G', 評分)。C＝M6 常數，a、c 換成該臂的。"""
    _, _, G, _ = rating_m4.score_arrays(t, P4)
    Gp = G + bonus(t, C, *ARMS[arm])[1]
    return Gp, np.maximum(0.0, C['a'] + C['c'] * Gp)


class Scorer:
    """上線用：讀 params.json 的 prod，對某一季每個球員單場給 M10 評分。"""

    def __init__(self, season, arm):
        pr = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
        self.tab = Table(season)
        _, self.S = score_arrays(self.tab, pr['P4'], pr[arm], arm)
        self.idx = {(g, p): i for i, (g, p) in enumerate(zip(self.tab.gid, self.tab.pid))}

    def score(self, gid, pid):
        return float(self.S[self.idx[(gid, pid)]])

    def fallback(self, gid, pid):
        return int(self.tab.fb[self.idx[(gid, pid)]])
