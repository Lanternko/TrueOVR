"""評分 M3（E-145，spec：reports/rating-m3/spec.md）：M2 貢獻值 v ＋ 負擔 u ＋ 在場正負值 q，分鐘縮回，整場總量，換成 0–10 顯示尺度。

  x  = v + β_u·u + β_q·q                       （每 36 分鐘）
  p  = (M_prev·x̄_prev + K·μ)/(M_prev + K)      先驗：上一季同口徑整季 x（分鐘加權）往聯盟平均 μ 縮；沒上一季 → μ
  x* = (MIN·x + K·p)/(MIN + K)                 縮回
  G  = (x* − R)·MIN/36                         整場總量
  評分 = max(0, a + c·G)
M2 的 Rater.value 不改。參數由 scripts/fit_rating_m3.py 寫進 reports/rating-m3/params*.json。
"""
import json
from pathlib import Path

import numpy as np

import rating_m2

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'rating-m3'


def season_dir(season):
    return ROOT / 'data' / ('season-source' if season == '2025-26' else f'season-source-{season}')


def _rs(path):
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    s = (d['data'] if 'data' in d else d)['resultSets'][0]
    return {k: i for i, k in enumerate(s['headers'])}, s['rowSet']


class Table:
    """一季所有 MIN>0 的球員單場，欄位是 numpy 陣列。v＝M2 貢獻值（每 36 分鐘）。"""

    def __init__(self, season, rater=None):
        h, rows = _rs(season_dir(season) / 'player-games.json')
        tp = season_dir(season) / 'team-games.json'
        team = {}
        if tp.exists():
            th, trows = _rs(tp)
            team = {(r[th['GAME_ID']], r[th['TEAM_ID']]): (r[th['WL']] == 'W', r[th['PLUS_MINUS']]) for r in trows}
        rater = rater or rating_m2.Rater(season)
        cols = {k: [] for k in ('pid', 'gid', 'date', 'tid', 'mn', 'v', 'pts', 'fga', 'fta', 'tov', 'pm', 'fb', 'twin', 'tpm', 'name')}
        self.rows, self.h = [], h
        for r in rows:
            mn = r[h['MIN']]
            if not mn:
                continue
            g = lambda k: r[h[k]] or 0
            w, tpm = team.get((r[h['GAME_ID']], r[h['TEAM_ID']]), (False, np.nan))
            for k, val in (('pid', r[h['PLAYER_ID']]), ('gid', r[h['GAME_ID']]), ('date', r[h['GAME_DATE']] if 'GAME_DATE' in h else ''), ('tid', r[h['TEAM_ID']]),
                           ('mn', float(mn)), ('v', rater.value(r, h)), ('pts', g('PTS')), ('fga', g('FGA')), ('fta', g('FTA')),
                           ('tov', g('TOV')), ('pm', g('PLUS_MINUS')), ('fb', int(rater.fallback(r, h))), ('twin', float(w)),
                           ('tpm', float(tpm)), ('name', r[h['PLAYER_NAME']])):
                cols[k].append(val)
            self.rows.append(r)
        for k, v in cols.items():
            setattr(self, k, np.array(v) if k not in ('gid', 'date', 'name') else np.array(v, dtype=object))
        self.half = np.array([int(g) % 2 for g in self.gid])
        self.uses = self.fga + 0.44 * self.fta + self.tov

    def __len__(self):
        return len(self.pid)


def wquant(vals, w, p):
    o = np.argsort(vals)
    c = np.cumsum(np.asarray(w, float)[o]) / np.sum(w)
    return float(np.asarray(vals, float)[o][np.searchsorted(c, p)])


def xval(t, Rppp, bu, bq):
    u = (t.pts - Rppp * t.uses) * 36 / t.mn
    q = t.pm * 36 / t.mn
    return t.v + bu * u + bq * q


def player_means(t, x, mask):
    """pid → (分鐘合計, 分鐘加權平均 x)。"""
    idx = np.where(mask)[0]
    u, inv = np.unique(t.pid[idx], return_inverse=True)
    m = np.bincount(inv, t.mn[idx])
    xm = np.bincount(inv, (x * t.mn)[idx]) / m
    return {pid: (float(a), float(b)) for pid, a, b in zip(u, m, xm)}


def prior_table(prev, Rppp, bu, bq, mu, K):
    """上一季整季 → pid → 先驗 p。prev＝None 時回空表（沒有上一季，全部用 μ）。"""
    if prev is None:
        return {}
    pm = player_means(prev, xval(prev, Rppp, bu, bq), np.ones(len(prev), bool))
    return {pid: (M * xb + K * mu) / (M + K) for pid, (M, xb) in pm.items()}


def score_arrays(t, P, prior):
    """用參數 P（Rppp,bu,bq,K,mu,R,a,c）和先驗表算全部單場：回 (x, x*, G, 評分)。"""
    x = xval(t, P['Rppp'], P['bu'], P['bq'])
    p = np.array([prior.get(pid, P['mu']) for pid in t.pid])
    xs = (t.mn * x + P['K'] * p) / (t.mn + P['K'])
    G = (xs - P['R']) * t.mn / 36
    return x, xs, G, np.maximum(0.0, P['a'] + P['c'] * G)


class Scorer:
    """上線用：讀 params_prod.json，對某一季的每個球員單場給 M3 評分。
    先驗＝上一季（2025-26 頁用 2024-25，2026-27 頁用 2025-26，2024-25 沒有）以同一組上線參數算的整季 x。"""
    PREV = {'2025-26': '2024-25', '2026-27': '2025-26'}

    def __init__(self, season):
        self.P = json.loads((OUT / 'params_prod.json').read_text(encoding='utf-8'))['P']
        self.tab = Table(season)
        prev = Table(self.PREV[season]) if season in self.PREV else None
        self.prior = prior_table(prev, self.P['Rppp'], self.P['bu'], self.P['bq'], self.P['mu'], self.P['K'])
        _, _, _, self.S = score_arrays(self.tab, self.P, self.prior)
        self.idx = {(g, p): i for i, (g, p) in enumerate(zip(self.tab.gid, self.tab.pid))}

    def score(self, gid, pid):
        return float(self.S[self.idx[(gid, pid)]])

    def fallback(self, gid, pid):
        return int(self.tab.fb[self.idx[(gid, pid)]])
