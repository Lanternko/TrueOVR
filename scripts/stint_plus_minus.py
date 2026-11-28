"""從 stints 算每人每場的非垃圾時間正負值（E-148，spec：reports/rating-m5/spec.md）。

垃圾時間＝某段 period ≥ 4 且「開始時」比分差絕對值 ≥ 20（比分差由各段 opponent.points 累加重建）。
輸出 per game：球隊 (淨分_總, 淨分_非垃圾, 秒_總, 秒_非垃圾)、每人 (PM_總, PM_非垃圾, 秒_總, 秒_非垃圾)。
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STINTS = {'2025-26': ROOT / 'reports/defense-b1/stints.jsonl',
          '2026-27': ROOT / 'reports/defense-seventh/2026-27/stints/stints.jsonl'}
GARBAGE_PERIOD, GARBAGE_DIFF = 4, 20


def load(season):
    """回 (players, teams)。
    players[(gid, pid)] = dict(pm, pm_ng, s, s_ng, tid)；teams[(gid, tid)] = dict(net, net_ng, s, s_ng)。"""
    games = defaultdict(list)
    for line in open(STINTS[season], encoding='utf-8'):
        d = json.loads(line)
        games[d['id']].append(d)
    players, teams = {}, {}
    for gid, sts in games.items():
        sts.sort(key=lambda d: (d['period'], -d['startClock'], d['startIndex']))
        score = defaultdict(int)  # tid -> 累計得分
        for d in sts:
            t0, t1 = d['teams']
            ids = [t0['teamId'], t1['teamId']]
            pts = {ids[0]: t1['opponent']['points'], ids[1]: t0['opponent']['points']}  # 各隊自己的得分
            diff0 = score[ids[0]] - score[ids[1]]
            garbage = d['period'] >= GARBAGE_PERIOD and abs(diff0) >= GARBAGE_DIFF
            sec = d['seconds']
            for t, me, opp in ((t0, ids[0], ids[1]), (t1, ids[1], ids[0])):
                net = pts[me] - pts[opp]
                tm = teams.setdefault((gid, me), dict(net=0, net_ng=0, s=0, s_ng=0))
                tm['net'] += net
                tm['s'] += sec
                if not garbage:
                    tm['net_ng'] += net
                    tm['s_ng'] += sec
                for p in t['players']:
                    r = players.setdefault((gid, p), dict(pm=0, pm_ng=0, s=0, s_ng=0, tid=me))
                    r['pm'] += net
                    r['s'] += sec
                    if not garbage:
                        r['pm_ng'] += net
                        r['s_ng'] += sec
            for t in ids:
                score[t] += pts[t]
    return players, teams


def q_relative(r, tm):
    """spec §2：q = 36·60·(PM_ng/S_ng − M_ng/T_ng)；S_ng < 60 秒 → 0。"""
    if r is None or r['s_ng'] < 60 or tm['s_ng'] <= 0:
        return 0.0
    return 36 * 60 * (r['pm_ng'] / r['s_ng'] - tm['net_ng'] / tm['s_ng'])
