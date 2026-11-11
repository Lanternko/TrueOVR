"""v5 §R.7：被交易球員分鐘數的跨隊加總來源。

來源依 preregistration-v5 §R.7 第 1 條定案（2026-10-28）：
  - 2021-22..2023-24：`v5/history/box-totals-<season>.csv` 的 `teamId=ALL`
    （官方 boxscoretraditionalv3 整季合計，被交易球員已跨隊加總）。
  - 2024-25：沒有 box-totals 檔，且本機沒有**整季**的 season-league roster
    （`reports/defense-seventh/2024-25/calendar-82/v3-league.json` 的 observed 只到約 60-69 場，
    例如 Jimmy Butler 46 場、KAT 60 場，不是整季）。改用
    `data/defense-seventh/2024-25/player-games.json` 逐場列，按 (playerId, teamId) 加總後再跨隊相加，
    與 season-league roster 逐隊 `+=` 是同一種計算，且涵蓋整季。
  - 2025-26：`reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json` 逐隊 roster
    `observed.MIN/GP` 加總（正式卡 calibrate-wing.py:58-59 的做法）。

輸出一律是 {pid: {'MIN', 'GP', 'teams', 'perTeam'}}，MIN/GP 為整季跨隊總和。
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT = ROOT / 'reports/ovr-inseason-2026-27'
V5_HISTORY = REPORT / 'v5/history'
TWOK27 = ROOT / 'reports/ovr-v55-2k27-compare'

SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']

SOURCE = {
    '2021-22': ('box-totals', V5_HISTORY / 'box-totals-2021-22.csv'),
    '2022-23': ('box-totals', V5_HISTORY / 'box-totals-2022-23.csv'),
    '2023-24': ('box-totals', V5_HISTORY / 'box-totals-2023-24.csv'),
    '2024-25': ('player-games', ROOT / 'data/defense-seventh/2024-25/player-games.json'),
    '2025-26': ('season-league',
                ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'),
}


def _empty(pid):
    return {'MIN': 0.0, 'GP': 0.0, 'teams': 0, 'perTeam': {}}


def _add(out, pid, team, minutes, gp):
    pid = int(pid)
    rec = out.setdefault(pid, _empty(pid))
    key = str(team)
    t = rec['perTeam'].setdefault(key, {'MIN': 0.0, 'GP': 0.0})
    t['MIN'] += float(minutes)
    t['GP'] += float(gp)
    rec['MIN'] += float(minutes)
    rec['GP'] += float(gp)


def from_box_totals(path):
    """官方 box totals：teamId=ALL 就是跨隊合計；分隊列只用來數被交易球員。"""
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    out, teams = {}, {}
    for r in rows:
        pid, team = int(r['playerId']), r['teamId']
        if team == 'ALL':
            rec = out.setdefault(pid, _empty(pid))
            rec['MIN'] = float(r['MIN'])
            rec['GP'] = float(r['GP'])
        else:
            teams.setdefault(pid, set()).add(team)
            rec = out.setdefault(pid, _empty(pid))
            rec['perTeam'][team] = {'MIN': float(r['MIN']), 'GP': float(r['GP'])}
    for pid, ts in teams.items():
        out[pid]['teams'] = len(ts)
    return out


def from_player_games(path):
    """逐場 player-games：先按 (pid, team) 加總，再跨隊相加。"""
    doc = json.load(open(path, encoding='utf-8'))
    s = doc['data']['resultSets']
    s = s[0] if isinstance(s, list) else s
    idx = {k: i for i, k in enumerate(s['headers'])}
    out = {}
    for r in s['rowSet']:
        _add(out, r[idx['PLAYER_ID']], r[idx['TEAM_ID']],
             r[idx['MIN']], 1.0)
    for pid, rec in out.items():
        rec['teams'] = len(rec['perTeam'])
    return out


def from_season_league(path):
    """season-league roster 逐隊 +=（正式卡做法）。"""
    doc = json.load(open(path, encoding='utf-8'))
    out = {}
    for t in doc['teams']:
        for p in t['roster']:
            _add(out, p['playerId'], t['id'],
                 p['observed']['MIN'], p['observed']['GP'])
    for pid, rec in out.items():
        rec['teams'] = len(rec['perTeam'])
    return out


def load_minutes(season, kind=None):
    kind = kind or SOURCE[season][0]
    if kind == 'box-totals':
        return from_box_totals(V5_HISTORY / f'box-totals-{season}.csv')
    if kind == 'player-games':
        return from_player_games(ROOT / f'data/defense-seventh/{season}/player-games.json')
    if kind == 'season-league':
        return from_season_league(SOURCE[season][1])
    raise ValueError(kind)


def describe(season):
    kind, path = SOURCE[season]
    return {'kind': kind, 'file': str(path.relative_to(ROOT))}


def first_record_minutes(season):
    """只取「第一筆」roster 紀錄時的 MIN/GP，用來說明舊檔是否只取第一隊。

    - season-league：照 build_prior_v4.py:159/172 的攤平順序取第一筆。
    - player-games：第一場出賽的球隊（逐場順序）。
    - box-totals：分隊列的第一筆（檔案順序）。
    """
    kind, path = SOURCE[season]
    out = {}
    if kind == 'season-league':
        doc = json.load(open(path, encoding='utf-8'))
        for t in doc['teams']:
            for p in t['roster']:
                out.setdefault(int(p['playerId']),
                               {'MIN': float(p['observed']['MIN']),
                                'GP': float(p['observed']['GP']), 'team': str(t['id'])})
        return out
    if kind == 'player-games':
        doc = json.load(open(path, encoding='utf-8'))
        s = doc['data']['resultSets']
        s = s[0] if isinstance(s, list) else s
        idx = {k: i for i, k in enumerate(s['headers'])}
        for r in s['rowSet']:
            pid, team = int(r[idx['PLAYER_ID']]), str(r[idx['TEAM_ID']])
            rec = out.setdefault(pid, {'MIN': 0.0, 'GP': 0.0, 'team': team})
            if rec['team'] != team:
                continue
            rec['MIN'] += float(r[idx['MIN']])
            rec['GP'] += 1.0
        return out
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    for r in rows:
        if r['teamId'] == 'ALL':
            continue
        out.setdefault(int(r['playerId']),
                       {'MIN': float(r['MIN']), 'GP': float(r['GP']), 'team': r['teamId']})
    return out


def cross_check(season, other):
    """box-totals vs 另一來源（player-games 逐隊加總）的整季 MIN 對照。"""
    a = load_minutes(season, 'box-totals')
    b = load_minutes(season, other)
    common = sorted(set(a) & set(b))
    diffs = [a[p]['MIN'] - b[p]['MIN'] for p in common]
    import statistics
    return {'season': season, 'sourceA': 'box-totals', 'sourceB': other,
            'n': len(common),
            'pearson': round(float(statistics.correlation(
                [a[p]['MIN'] for p in common], [b[p]['MIN'] for p in common])), 8),
            'maxAbsDiff': round(max(abs(d) for d in diffs), 4),
            'medianAbsDiff': round(statistics.median(abs(d) for d in diffs), 4),
            'nDiffGt1': sum(1 for d in diffs if abs(d) > 1.0),
            'playersOnlyA': sorted(set(a) - set(b)),
            'playersOnlyB': sorted(set(b) - set(a))}
