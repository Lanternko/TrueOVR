"""E-223 A 線（機制線）prep：每隊在第 12／28／44／60／76 場（該隊第 n 場，今日陣容）逐一拿掉輪替內的一人，重算 R-151 輪替。
不含任何比賽結果（只用陣容）。用法：python -I -X utf8 prep_aline.py 2526 → work/aline-jobs-<s>.json、work/aline-meta-<s>.json
job key＝snap*10+slot（slot0＝原陣容、slot1..＝依輪替順序拿掉第 slot 人）；同一 snapshot 共用 seedKey（共同隨機數）。S=200。"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, sys, collections
from e223_lib import *
s = sys.argv[1]; NS = (12, 28, 44, 60, 76)
S = load_season(s); c = SEASONS[s]
zmap, zmiss, info = load_card(CARDS / c['card'])
cnt = collections.Counter(); want = {}
for g in S['games']:
    for sd, tk in (('h', 'home'), ('a', 'away')):
        cnt[g[tk]] += 1
        if cnt[g[tk]] in NS:
            want[(g['i'], sd)] = (g[tk], cnt[g[tk]])
rots, snaps = build_lineups(S, zmap, snap_games=set(want))
jobs, meta = [], []
for si, ((i, sd), (team, nth)) in enumerate(sorted(want.items())):
    st = snaps[(i, sd)]; base = rots[(i, sd)]
    jobs.append(dict(key=si * 10, seedKey=3000 + si, roster=base))
    sb = s_term(base, zmap, zmiss)
    for slot, (pid, mn) in enumerate(base, start=1):
        rr = rot_removed(st, pid, zmap)
        jobs.append(dict(key=si * 10 + slot, seedKey=3000 + si, roster=rr))
        meta.append(dict(snap=si, team=team, nth=nth, game=i, side=sd, slot=slot, pid=pid, minutes=mn, has_card=pid in zmap,
                         z=zmap.get(pid, zmiss), x=sb - s_term(rr, zmap, zmiss), base_n=len(base), rem_n=len(rr)))
json.dump(dict(variant=c['variant'], S=200, jobs=jobs), open(HERE / f'work/aline-jobs-{s}.json', 'w'))
json.dump(meta, open(HERE / f'work/aline-meta-{s}.json', 'w'))
print(s, 'snapshots', len(want), 'jobs', len(jobs), 'removals', len(meta), 'x range', round(min(m['x'] for m in meta), 3), round(max(m['x'] for m in meta), 3))
