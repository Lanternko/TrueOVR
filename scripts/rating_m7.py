"""評分 M7（E-165，預註冊：reports/rating-m7-gmsc/preregistration.md）：M4 整場總量 G 混 Game Score。

  GmSc = PTS + 0.4·FGM − 0.7·FGA − 0.4·(FTA − FTM) + 0.7·OREB + 0.3·DREB + STL + 0.7·AST + 0.7·BLK − 0.4·PF − TOV
  G″   = (1−w)·z(G) + w·z(GmSc)      z 的平均、標準差：該組 ≥10 分鐘單場
  評分 = max(0, a″ + c″·G″)          a″、c″：同組 ≥10 分鐘單場中位數＝5.8、第 94 百分位＝10.0
M4 的 score_arrays 不改。參數由 scripts/fit_rating_m7.py 寫進 reports/rating-m7-gmsc/params.json。
"""
import json
from pathlib import Path

import numpy as np

import rating_m4
from rating_m3 import Table

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m7-gmsc'
ARMS = {'G15': 0.15, 'G30': 0.30}
GM_COLS = ('FGM', 'FGA', 'FTA', 'FTM', 'OREB', 'DREB', 'STL', 'AST', 'BLK', 'PF', 'TOV', 'PTS')


def gmsc(t):
    """Table 的 rows 與陣列同序（同一份 player-games.json），直接取欄位。"""
    c = {k: np.array([r[t.h[k]] or 0 for r in t.rows], float) for k in GM_COLS}
    return (c['PTS'] + 0.4 * c['FGM'] - 0.7 * c['FGA'] - 0.4 * (c['FTA'] - c['FTM']) + 0.7 * c['OREB']
            + 0.3 * c['DREB'] + c['STL'] + 0.7 * c['AST'] + 0.7 * c['BLK'] - 0.4 * c['PF'] - c['TOV'])


def score_arrays(t, P4, C, w):
    """回 (G″, 評分, zG, zS)。C 含 muG、sdG、muS、sdS、a、c。"""
    _, _, G, _ = rating_m4.score_arrays(t, P4)
    zG, zS = (G - C['muG']) / C['sdG'], (gmsc(t) - C['muS']) / C['sdS']
    Gpp = (1 - w) * zG + w * zS
    return Gpp, np.maximum(0.0, C['a'] + C['c'] * Gpp), zG, zS


class Scorer:
    """上線用：讀 params.json 的 prod，對某一季每個球員單場給 M7 評分。arm＝'G15' 或 'G30'。"""

    def __init__(self, season, arm='G15'):
        pr = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
        self.tab = Table(season)
        _, self.S, _, _ = score_arrays(self.tab, pr['P4'], pr[arm], ARMS[arm])
        self.idx = {(g, p): i for i, (g, p) in enumerate(zip(self.tab.gid, self.tab.pid))}

    def score(self, gid, pid):
        return float(self.S[self.idx[(gid, pid)]])

    def fallback(self, gid, pid):
        return int(self.tab.fb[self.idx[(gid, pid)]])
