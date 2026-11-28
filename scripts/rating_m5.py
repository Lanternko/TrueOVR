"""評分 M5（E-148，spec：reports/rating-m5/spec.md，凍結 sha256 cb41c4b5…ab53）。

和 M4 只差 q：M4 的 q＝box PLUS_MINUS×36/MIN；M5 的 q＝非垃圾時間、相對全隊的每 36 分鐘淨分（stints 重建）。
  x  = v + β_q·q ;  x* = (MIN·x + K·μ)/(MIN + K) ;  G = (x* − R)·MIN/36 ;  評分 = max(0, a + c·G)
V0：≥10 分鐘球員單場，stints 加總 PM 與 box PLUS_MINUS 比對；該場不在 stints 或任一人差 >2 → 整場退回
  q = 36·(PLUS_MINUS/MIN − 球隊淨勝分/48)。
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stint_plus_minus as spm  # noqa: E402
from rating_m3 import Table  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m5'
V0_TOL = 2


class Table5(Table):
    """Table ＋ q（M5）、q_m4（box PM×36/MIN）、fb_q（該場是否退回）、gfrac（上場時間中垃圾時間比例）。"""

    def __init__(self, season):
        super().__init__(season)
        players, teams = spm.load(season)
        n = len(self)
        self.q = np.zeros(n)
        self.q_m4 = self.pm * 36 / self.mn
        self.fbq = np.zeros(n, bool)
        self.gfrac = np.zeros(n)
        # 各場是否退回
        by_game = {}
        for i in range(n):
            by_game.setdefault(self.gid[i], []).append(i)
        v0 = dict(n_pl=0, n_ok=0, n_games=0, n_games_ok=0, n_games_missing=0, n_games_bad=0, fb_games=[])
        bad_games = set()
        for gid, idxs in by_game.items():
            v0['n_games'] += 1
            miss = not any((gid, self.tid[i]) in teams for i in idxs)
            bad = miss
            for i in idxs:
                if self.mn[i] < 10:
                    continue
                v0['n_pl'] += 1
                r = players.get((gid, int(self.pid[i])))
                ok = r is not None and abs(r['pm'] - self.pm[i]) <= V0_TOL
                v0['n_ok'] += int(ok)
                if not ok:
                    bad = True
            if miss:
                v0['n_games_missing'] += 1
            elif bad:
                v0['n_games_bad'] += 1
            if bad:
                bad_games.add(gid)
                v0['fb_games'].append(str(gid))
            else:
                v0['n_games_ok'] += 1
        v0['pl_ok_ratio'] = v0['n_ok'] / max(1, v0['n_pl'])
        v0['game_ok_ratio'] = v0['n_games_ok'] / max(1, v0['n_games'])
        v0['n_fallback_games'] = len(bad_games)
        self.v0 = v0
        for i in range(n):
            gid = self.gid[i]
            if gid in bad_games:
                self.fbq[i] = True
                self.q[i] = 36 * (self.pm[i] / self.mn[i] - self.tpm[i] / 48) if not np.isnan(self.tpm[i]) else 0.0
            else:
                r = players.get((gid, int(self.pid[i])))
                tm = teams[(gid, self.tid[i])]
                self.q[i] = spm.q_relative(r, tm)
                if r is not None and r['s'] > 0:
                    self.gfrac[i] = 1 - r['s_ng'] / r['s']


def xval(t, bq):
    return t.v + bq * t.q


def score_arrays(t, P):
    x = xval(t, P['bq'])
    xs = (t.mn * x + P['K'] * P['mu']) / (t.mn + P['K'])
    G = (xs - P['R']) * t.mn / 36
    return x, xs, G, np.maximum(0.0, P['a'] + P['c'] * G)


class Scorer:
    def __init__(self, season):
        self.P = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']['P']
        self.tab = Table5(season)
        _, _, _, self.S = score_arrays(self.tab, self.P)
