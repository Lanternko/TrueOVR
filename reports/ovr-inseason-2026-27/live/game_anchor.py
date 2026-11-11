"""inseason 0.2.14d「近況」（R-190，E-302 臂 MR 的 OVR 錨點項）。

單場分數 s＝A_MAP＋B_MAP·rt（E-299 凍結 map.json：rt 0–10 的單場評分換成 OVR 尺）。
  rt＝rating_m10 Z1 單場評分（scripts/rating_m10.Scorer，和賽程頁 games-box 同一套），四捨五入到 0.1；
  上場分鐘＝MIN 四捨五入成整數（同 build_games_data.minutes），0 分鐘的場次不算。
A＝Σw·s／Σw，w_j＝MIN_j·0.5^((k−j)/H)（k＝最近一場）；n＝Σw／36。
β＝B0·n/(n+5)·fade·0.5^(max(0, gap−3)/14)：
  fade＝clip((1230−已賽場數)/(0.2·1230), 0, 1)（季末最後兩成場次漸收到 0＝卡片）；
  gap＝資料截止日（本季最後一個比賽日）−本人最後一場（天）：傷停／沒上場超過 3 天，每 14 天減半。
近況 formBonus＝β·(A−W)，W＝錨點前的 OVR（含 mixBonus）；OVR＝W＋近況。lastOVR（本季 0 場）不動，ΔOVR 加上近況。
資料都從本季 season-source／matchup-source 讀：ovr_history 單日重算時兩者都導到截斷資料夾（只剩 d 以前的比賽）。
"""
import math
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEASON = '2026-27'
A_MAP, B_MAP = 2.145878686486219, 11.295278052840782   # reports/E299-game-anchor-nonneg/map.json（a, b）
B0, H = 0.5, 10.0                                       # E-302 MR：β0、半衰期（場）
N_PRIOR = 5.0                                           # β 的 n/(n+5)
GAMES_SEASON, FADE_FRAC = 1230, 0.2
GAP_FREE, GAP_HALF = 3, 14.0


def _minutes(v) -> int:
    """同 scripts/build_games_data.minutes。"""
    if v is None or v == '':
        return 0
    if isinstance(v, str) and ':' in v:
        m, s = v.split(':')[:2]
        return round(int(m) + int(s) / 60)
    return round(float(v))


def series():
    """→ (games {pid: [(date, gameId, min, rt)] 依日期}, 資料截止日, 已賽場數)。"""
    if str(ROOT / 'scripts') not in sys.path:
        sys.path.insert(0, str(ROOT / 'scripts'))
    import rating_m10
    sc = rating_m10.Scorer(SEASON, 'Z1')
    t = sc.tab
    iM = t.h['MIN']
    out, gids, last = {}, set(), ''
    for i, r in enumerate(t.rows):
        d = t.date[i]
        gids.add(t.gid[i])
        last = max(last, d)
        m = _minutes(r[iM])
        if m <= 0:
            continue
        out.setdefault(int(t.pid[i]), []).append((d, t.gid[i], m, round(float(sc.S[i]), 1)))
    for v in out.values():
        v.sort()
    return out, last, len(gids)


def term(games, asof, played):
    """一個人的 (A, β, n, gap)；沒有比賽回 None。"""
    if not games:
        return None
    k = len(games) - 1
    w = [m * 0.5 ** ((k - j) / H) for j, (_, _, m, _) in enumerate(games)]
    sw = sum(w)
    A = sum(wj * (A_MAP + B_MAP * g[3]) for wj, g in zip(w, games)) / sw
    n = sw / 36.0
    fade = min(1.0, max(0.0, (GAMES_SEASON - played) / (FADE_FRAC * GAMES_SEASON)))
    gap = (date.fromisoformat(asof) - date.fromisoformat(games[-1][0])).days
    beta = B0 * n / (n + N_PRIOR) * fade * 0.5 ** (max(0, gap - GAP_FREE) / GAP_HALF)
    return A, beta, n, gap


def apply(rows, r1):
    """rows＝寫 ranking.csv 前的合併列（老將＋新秀，已含 mixBonus）。原地改 _ovr／ovr／dOVR，加 formBonus；回傳 (明細 {pid: …}, meta)。"""
    games, asof, played = series()
    detail = {}
    for r in rows:
        pid = int(r['playerId'])
        tm = term(games.get(pid), asof, played)
        if tm is None:
            r['formBonus'] = 0.0
            continue
        A, beta, n, gap = tm
        W = r['_ovr']
        f = beta * (A - W)
        r['_ovr'] = W + f
        r['ovr'] = r1(r['_ovr'])
        if r.get('dOVR') not in ('', None):
            r['dOVR'] = round(float(r['dOVR']) + f, 2)
        r['formBonus'] = round(f, 3)
        g = games[pid]
        detail[str(pid)] = {'A': round(A, 3), 'beta': round(beta, 4), 'n': round(n, 3), 'gap': gap, 'W': round(W, 3),
                            'form': round(f, 3), 'games': len(g),
                            'last': [{'date': d, 'min': m, 'rt': rt} for d, _, m, rt in g[-5:]]}
    meta = {'asof': asof, 'gamesPlayed': played, 'fade': round(min(1.0, max(0.0, (GAMES_SEASON - played) / (FADE_FRAC * GAMES_SEASON))), 4),
            'params': {'a': A_MAP, 'b': B_MAP, 'beta0': B0, 'halfLifeGames': H, 'nPrior': N_PRIOR,
                       'gapFreeDays': GAP_FREE, 'gapHalfDays': GAP_HALF, 'season': GAMES_SEASON, 'fadeFrac': FADE_FRAC}}
    return detail, meta


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    g, a, p = series()
    print(f'截止 {a}、已賽 {p} 場、{len(g)} 人有上場；fade＝{min(1.0, max(0.0, (GAMES_SEASON - p) / (FADE_FRAC * GAMES_SEASON))):.3f}')
