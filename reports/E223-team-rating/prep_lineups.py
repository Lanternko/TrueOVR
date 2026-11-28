"""E-223 prep：逐場輪替與模擬工作清單（不含任何比賽結果）。
用法：python -I -X utf8 prep_lineups.py 2425|2526  → work/lineups-<s>.json、work/jobs-<s>.json（S=100，種子 key＝1000+2i+side）"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e223_lib import *
s = sys.argv[1]
S = load_season(s); c = SEASONS[s]
zmap, zmiss, info = load_card(CARDS / c['card'])
rots, _ = build_lineups(S, zmap)
(HERE / 'work').mkdir(exist_ok=True)
json.dump({f'{i}{sd}': r for (i, sd), r in rots.items()}, open(HERE / f'work/lineups-{s}.json', 'w'))
jobs = [dict(key=2 * i + (sd == 'a'), seedKey=1000 + 2 * i + (sd == 'a'), roster=r) for (i, sd), r in rots.items()]
json.dump(dict(variant=c['variant'], S=100, jobs=jobs), open(HERE / f'work/jobs-{s}.json', 'w'))
# 覆蓋率（只看卡片有沒有人，不看結果）
tot = miss = 0; nrot = []
for (i, sd), r in rots.items():
    nrot.append(len(r))
    for p, m in r:
        tot += m; miss += m * (p not in zmap)
print(s, 'games', len(S['games']), 'lineups', len(rots), 'card', info, 'z_miss', round(zmiss, 4))
print('rotation size dist', {k: nrot.count(k) for k in sorted(set(nrot))}, 'minute share w/o card', round(miss / tot, 4))
