"""R-153／R-156：焦灼比賽分槽乘數（資料直接量，不擬合不挑參數）。用法：python -I -X utf8 reports/E208-team-rating/r153_close_multipliers.py
資料：2024-25（data/defense-seventh/2024-25）與 2025-26（data/season-source）的 leaguegamelog 例行賽 player-games／team-games。
R-156：球員「在隊期間」＝該球員該季替這隊第一場出賽（MIN>0）到最後一場出賽之間、這隊的所有比賽（季中交易的人分兩段，各算各隊）；
在隊期間沒出現在 box score（或 MIN=0）的場次記 0 分鐘，焦灼場與全部場分子分母同規則。歷史沒有傷兵資料，傷缺場次也記 0（近似：傷缺在焦灼與非焦灼場大致同比例）。
每隊每季球員依該季（該隊）在隊期間含 0 的場均分鐘排名 → 槽 1…10，>10 併成槽 11（11+）。
焦灼場＝最終分差（team-games PLUS_MINUS）|d| ≤ 5 或延長賽（team MIN > 240）。延長賽分鐘等比換算成 48 分鐘：m × 240 / team MIN。
m_k ＝ 槽 k 在焦灼場的平均分鐘 ÷ 槽 k 在全部場的平均分鐘（含 0 的在隊場次；兩季合併）。"""
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEASONS = {'2024-25': ROOT / 'data/defense-seventh/2024-25', '2025-26': ROOT / 'data/season-source'}
CLOSE = 5
OUT = Path(__file__).resolve().parent / 'r153-close-game-multipliers.json'


def rows(path):
    d = json.loads(path.read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(d['headers'])}
    return [{k: r[i] for k, i in h.items()} for r in d['rowSet']], hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    allm, closem, src = collections.defaultdict(list), collections.defaultdict(list), {}
    ngames = {}
    for season, d in SEASONS.items():
        tg, sha_t = rows(d / 'team-games.json'); pg, sha_p = rows(d / 'player-games.json')
        src[season] = {'dir': str(d.relative_to(ROOT)), 'team-games.sha256': sha_t, 'player-games.sha256': sha_p}
        info = {(r['GAME_ID'], r['TEAM_ID']): (r['MIN'], r['PLUS_MINUS'], r['GAME_DATE']) for r in tg}
        team_games = collections.defaultdict(list)   # team → [(date, game, close)]
        for (gid, t), (tmin, pm, date) in info.items():
            team_games[t].append((date, gid, abs(pm) <= CLOSE or tmin > 240))
        for t in team_games:
            team_games[t].sort()
        played = collections.defaultdict(dict)       # (team, player) → {game: scaled min}
        for r in pg:
            if not r['MIN'] or r['MIN'] <= 0:
                continue
            played[(r['TEAM_ID'], r['PLAYER_ID'])][r['GAME_ID']] = r['MIN'] * 240.0 / info[(r['GAME_ID'], r['TEAM_ID'])][0]
        teams = collections.defaultdict(list)
        for (t, p), gm in played.items():
            dates = [d for d, gid, _ in team_games[t] if gid in gm]
            lo, hi = min(dates), max(dates)
            g = [(gm.get(gid, 0.0), c) for d, gid, c in team_games[t] if lo <= d <= hi]   # 在隊期間；沒出賽記 0
            teams[t].append((sum(m for m, _ in g) / len(g), g))
        for t, lst in teams.items():
            lst.sort(key=lambda x: -x[0])
            for i, (_, g) in enumerate(lst):
                k = min(i + 1, 11)
                for m, c in g:
                    allm[k].append(m)
                    if c:
                        closem[k].append(m)
        ngames[season] = {'games': len({g for g, _ in info}), 'closeTeamGames': sum(1 for (g, t), (mn, pm, _) in info.items() if abs(pm) <= CLOSE or mn > 240) // 2}
    mult = {}
    for k in range(1, 12):
        a, c = sum(allm[k]) / len(allm[k]), sum(closem[k]) / len(closem[k])
        mult[str(k)] = {'label': str(k) if k < 11 else '11+', 'allMin': round(a, 4), 'closeMin': round(c, 4), 'm': round(c / a, 4), 'nAll': len(allm[k]), 'nClose': len(closem[k])}
    old = json.loads(OUT.read_text(encoding='utf-8'))['multipliers'] if OUT.exists() else {}
    for k, v in mult.items():
        o = old.get(k, {})
        v['mR153'] = o.get('mR153', o.get('m'))     # 舊值（R-153：只算有出賽場次）
    OUT.write_text(json.dumps({'rule': 'R-156 (supersedes R-153 weighting)', 'close': f'|margin| <= {CLOSE} or OT', 'weighting': 'games in team stint (first..last appearance for that team), DNP/absent = 0 min', 'sources': src, 'games': ngames, 'multipliers': mult}, ensure_ascii=False, indent=1), encoding='utf-8')
    print([mult[str(k)]['m'] for k in range(1, 12)], ngames)


if __name__ == '__main__':
    sys.exit(main())
