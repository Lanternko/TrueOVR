"""評分 M4（E-146，spec：reports/rating-m4/spec.md）：M2 貢獻值 v ＋ 在場正負值 q，往聯盟平均 μ 縮回，整場總量，換成 0–10 顯示尺度。

  x  = v + β_q·q                      （每 36 分鐘；q = PLUS_MINUS×36/MIN）
  x* = (MIN·x + K·μ)/(MIN + K)        μ＝聯盟分鐘加權平均 x（所有人同一個）
  G  = (x* − R)·MIN/36
  評分 = max(0, a + c·G)
M2 的 Rater.value 不改。參數由 scripts/fit_rating_m4.py 寫進 reports/rating-m4/params.json。
"""
import json
from pathlib import Path

import numpy as np

from rating_m3 import Table, season_dir  # noqa: F401  (共用資料表)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m4'


def xval(t, bq):
    return t.v + bq * (t.pm * 36 / t.mn)


def score_arrays(t, P):
    """回 (x, x*, G, 評分)。"""
    x = xval(t, P['bq'])
    xs = (t.mn * x + P['K'] * P['mu']) / (t.mn + P['K'])
    G = (xs - P['R']) * t.mn / 36
    return x, xs, G, np.maximum(0.0, P['a'] + P['c'] * G)


class Scorer:
    """上線用：讀 params.json 的 prod，對某一季每個球員單場給 M4 評分。"""

    def __init__(self, season):
        self.P = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']['P']
        self.tab = Table(season)
        _, _, _, self.S = score_arrays(self.tab, self.P)
        self.idx = {(g, p): i for i, (g, p) in enumerate(zip(self.tab.gid, self.tab.pid))}

    def score(self, gid, pid):
        return float(self.S[self.idx[(gid, pid)]])

    def fallback(self, gid, pid):
        return int(self.tab.fb[self.idx[(gid, pid)]])
