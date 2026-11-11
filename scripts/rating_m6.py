"""評分 M6（E-150，spec：reports/rating-m6/spec.md）：M4 整場總量 G ＋ 扛出手量加分 B。

  TSA = FGA + 0.44·FTA，TS = PTS/(2·TSA)
  E   = max(0, TSA − TSA36_lg·MIN/36)            比平均多扛的出手回合
  TS_pass = TS_lg − λ·E                          及格線隨量下降
  f   = clip(1 + (TS − TS_pass)/δ, 0, 1)          低於及格線線性減免
  B   = f·(2·λ·E·TSA + g·2·(TS_lg − TS_repl)·E)  （分）
  G'  = G + B·100·48/(36·PACE_lg)
  評分 = max(0, a' + c'·G')
M4 的 score_arrays 不改。參數由 scripts/fit_rating_m6.py 寫進 reports/rating-m6/params.json。
"""
import json
from pathlib import Path

import numpy as np

import rating_m4
from rating_m3 import Table

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m6'
LAM, G_MULT, DELTA = 0.003, 1.0, 0.10


def bonus(t, C):
    """回 (B 分, B_G, f, E)。"""
    tsa = t.fga + 0.44 * t.fta
    E = np.maximum(0.0, tsa - C['TSA36_lg'] * t.mn / 36)
    ts = np.where(tsa > 0, t.pts / (2 * np.where(tsa > 0, tsa, 1)), 0.0)
    f = np.clip(1 + (ts - (C['TS_lg'] - LAM * E)) / DELTA, 0, 1)
    f = np.where(E > 0, f, 0.0)
    B = f * (2 * LAM * E * tsa + G_MULT * 2 * (C['TS_lg'] - C['TS_repl']) * E)
    return B, B * 100 * 48 / (36 * C['PACE_lg']), f, E


def score_arrays(t, P4, C):
    """回 (G', 評分)。P4＝M4 參數，C＝M6 常數（含 a、c）。"""
    _, _, G, _ = rating_m4.score_arrays(t, P4)
    Gp = G + bonus(t, C)[1]
    return Gp, np.maximum(0.0, C['a'] + C['c'] * Gp)


class Scorer:
    """上線用：讀 params.json 的 prod，對某一季每個球員單場給 M6 評分。"""

    def __init__(self, season):
        pr = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
        self.P4, self.C = pr['P4'], pr['C']
        self.tab = Table(season)
        _, self.S = score_arrays(self.tab, self.P4, self.C)
        self.idx = {(g, p): i for i, (g, p) in enumerate(zip(self.tab.gid, self.tab.pid))}

    def score(self, gid, pid):
        return float(self.S[self.idx[(gid, pid)]])

    def fallback(self, gid, pid):
        return int(self.tab.fb[self.idx[(gid, pid)]])
