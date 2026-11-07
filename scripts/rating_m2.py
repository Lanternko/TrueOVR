"""評分 M2（E-110／R-066）：box 11 項＋hustle 5 項＋防守對位 2 項，每 36 分鐘 × 權重（擬合 2025-26 A 半 RAPM）。

對位兩項（每場、以防守者 d 為準）：
  PTS_SAVED＝Σ(exp(o) × 部分回合 − o 得分)，exp(o)＝o 在 2025-26 整季對位的得分 ÷ 部分回合（回合 < 50 用聯盟平均）
  TOV_FORCED＝被 d 守時 o 的失誤合計
資料：data/matchup-source/<季>/<GAME_ID>.json（scripts/fetch_matchups.mjs）。某場沒有資料 → 該場用 M0（E-105）。
權重與基準：reports/game-contribution/m2/（scripts/fit_rating_m2.py）。
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MSRC = ROOT / 'data' / 'matchup-source'
M2 = ROOT / 'reports' / 'game-contribution' / 'm2'
HUSTLE = {'DEFL': 'deflections', 'CONTEST': 'contestedShots', 'CHARGE': 'chargesDrawn',
          'LOOSE': 'looseBallsRecoveredTotal', 'SCREEN_AST': 'screenAssists'}
EXP_MIN_POSS = 50


def load_games(season):
    out = {}
    for p in sorted((MSRC / season).glob('00*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        if d.get('matchups') and d.get('hustle'):
            out[d['gameId']] = d
    return out


def exp_table(games, half=None):
    """o → 得分÷部分回合；half＝0/1 只取 int(GAME_ID)%2 那半，None 取整季。回傳 (dict, 聯盟平均)。"""
    pts, poss = defaultdict(float), defaultdict(float)
    for gid, g in games.items():
        if half is not None and int(gid) % 2 != half:
            continue
        for m in g['matchups']:
            pts[m['off']] += m['playerPoints']
            poss[m['off']] += m['partialPossessions']
    return {o: pts[o] / poss[o] for o in poss if poss[o] >= EXP_MIN_POSS}, sum(pts.values()) / sum(poss.values())


def game_extra(g, exp, lg):
    """一場 → {personId: {DEFL…, PTS_SAVED, TOV_FORCED}}。"""
    e = defaultdict(lambda: defaultdict(float))
    for r in g['hustle']:
        for k, src in HUSTLE.items():
            e[r['personId']][k] += r.get(src) or 0
    for m in g['matchups']:
        d = e[m['def']]
        d['PTS_SAVED'] += exp.get(m['off'], lg) * m['partialPossessions'] - m['playerPoints']
        d['TOV_FORCED'] += m['matchupTurnovers']
    return e


class Rater:
    """一季的單場評分器：value(row, h) → 每 36 分鐘貢獻值（每 100 回合淨分），fallback(row, h) → 該場沒有對位資料。"""

    def __init__(self, season):
        w = json.loads((M2 / 'weights.json').read_text(encoding='utf-8'))
        m0 = json.loads((ROOT / 'reports' / 'game-contribution' / 'weights.json').read_text(encoding='utf-8'))
        self.w, self.m0 = w, m0
        self.exp, self.lg = {int(k): v for k, v in w['exp'].items()}, w['leagueExp']
        self.games = load_games(season)
        self._extra = {}

    def extra(self, gid):
        if gid not in self._extra:
            g = self.games.get(gid)
            self._extra[gid] = game_extra(g, self.exp, self.lg) if g else None
        return self._extra[gid]

    def fallback(self, r, h):
        return self.extra(r[h['GAME_ID']]) is None

    def value(self, r, h):
        mn = r[h['MIN']]
        e = self.extra(r[h['GAME_ID']])
        if e is None:
            return self.m0['intercept'] + sum(b * (r[h[k]] or 0) for k, b in self.m0['per36'].items()) * 36 / mn
        x = e.get(r[h['PLAYER_ID']], {})
        tot = sum(b * ((r[h[k]] or 0) if k in h else x.get(k, 0)) for k, b in self.w['per36'].items())
        return self.w['intercept'] + tot * 36 / mn
