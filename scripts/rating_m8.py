"""評分 M8（E-167，預註冊：reports/rating-m8-smooth/preregistration.md）：M6 加分改平滑。

  B = f·(2·λ·E·X + g·2·(TS_lg − TS_repl)·E)，f = clip(1 + (TS − (TS_lg − λ·E))/δ, 0, 1)
  M6：δ=0.10、X=TSA；S1：δ=0.20；S3：X=TSA36_lg·MIN/36；S13：兩個都改。
其餘同 rating_m6（λ、g、TS_lg、TSA36_lg、TS_repl、PACE_lg 沿用 M6 params），各臂只重定 a、c。
"""
import json
from pathlib import Path

import numpy as np

import rating_m4
from rating_m3 import Table
from rating_m6 import G_MULT, LAM

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m8-smooth'
ARMS = {'S1': (0.20, False), 'S3': (0.10, True), 'S13': (0.20, True)}


def bonus(t, C, delta, lin):
    """回 (B 分, B_G, f, E)。lin＝True 時 X 用同分鐘聯盟平均出手。"""
    tsa = t.fga + 0.44 * t.fta
    base = C['TSA36_lg'] * t.mn / 36
    E = np.maximum(0.0, tsa - base)
    ts = np.where(tsa > 0, t.pts / (2 * np.where(tsa > 0, tsa, 1)), 0.0)
    f = np.clip(1 + (ts - (C['TS_lg'] - LAM * E)) / delta, 0, 1)
    f = np.where(E > 0, f, 0.0)
    X = base if lin else tsa
    B = f * (2 * LAM * E * X + G_MULT * 2 * (C['TS_lg'] - C['TS_repl']) * E)
    return B, B * 100 * 48 / (36 * C['PACE_lg']), f, E


def score_arrays(t, P4, C, arm):
    """回 (G', 評分)。C＝M6 常數，a、c 換成該臂的。"""
    _, _, G, _ = rating_m4.score_arrays(t, P4)
    Gp = G + bonus(t, C, *ARMS[arm])[1]
    return Gp, np.maximum(0.0, C['a'] + C['c'] * Gp)


class Scorer:
    """上線用：讀 params.json 的 prod，對某一季每個球員單場給 M8 評分。"""

    def __init__(self, season, arm):
        pr = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
        self.tab = Table(season)
        _, self.S = score_arrays(self.tab, pr['P4'], pr[arm], arm)
        self.idx = {(g, p): i for i, (g, p) in enumerate(zip(self.tab.gid, self.tab.pid))}

    def score(self, gid, pid):
        return float(self.S[self.idx[(gid, pid)]])

    def fallback(self, gid, pid):
        return int(self.tab.fb[self.idx[(gid, pid)]])
