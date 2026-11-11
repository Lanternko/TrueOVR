"""評分 M9（E-168，預註冊：reports/rating-m9-curve/preregistration.md）：M6 加分斜坡改曲線。

  B = f^p·(2·λ·E·TSA + g·2·(TS_lg − TS_repl)·E)，f = clip(1 + (TS − (TS_lg − λ·E))/δ, 0, 1)
  M6：δ=0.10、p=1；S1：δ=0.20、p=1；C15：δ=0.20、p=1.5；C2：δ=0.20、p=2。
其餘同 rating_m6（λ、g、TS_lg、TSA36_lg、TS_repl、PACE_lg 沿用 M6 params），各臂只重定 a、c。
"""
import json
from pathlib import Path

import numpy as np

import rating_m4
from rating_m3 import Table
from rating_m6 import G_MULT, LAM

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m9-curve'
ARMS = {'C15': (0.20, 1.5), 'C2': (0.20, 2.0), 'S1': (0.20, 1.0)}  # 順序＝預註冊 §2 平手優先序


def bonus(t, C, delta, p):
    """回 (B 分, B_G, f^p, E)。"""
    tsa = t.fga + 0.44 * t.fta
    E = np.maximum(0.0, tsa - C['TSA36_lg'] * t.mn / 36)
    ts = np.where(tsa > 0, t.pts / (2 * np.where(tsa > 0, tsa, 1)), 0.0)
    f = np.clip(1 + (ts - (C['TS_lg'] - LAM * E)) / delta, 0, 1) ** p
    f = np.where(E > 0, f, 0.0)
    B = f * (2 * LAM * E * tsa + G_MULT * 2 * (C['TS_lg'] - C['TS_repl']) * E)
    return B, B * 100 * 48 / (36 * C['PACE_lg']), f, E


def score_arrays(t, P4, C, arm):
    """回 (G', 評分)。C＝M6 常數，a、c 換成該臂的。"""
    _, _, G, _ = rating_m4.score_arrays(t, P4)
    Gp = G + bonus(t, C, *ARMS[arm])[1]
    return Gp, np.maximum(0.0, C['a'] + C['c'] * Gp)


class Scorer:
    """上線用：讀 params.json 的 prod，對某一季每個球員單場給 M9 評分。"""

    def __init__(self, season, arm):
        pr = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
        self.tab = Table(season)
        _, self.S = score_arrays(self.tab, pr['P4'], pr[arm], arm)
        self.idx = {(g, p): i for i, (g, p) in enumerate(zip(self.tab.gid, self.tab.pid))}

    def score(self, gid, pid):
        return float(self.S[self.idx[(gid, pid)]])

    def fallback(self, gid, pid):
        return int(self.tab.fb[self.idx[(gid, pid)]])
