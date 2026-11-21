"""E-229b T：同一份陣容分鐘，特徵＝e229_live.build(截止 d 前一天＝GAME_DATE < d, live＝d 之前最近一份)，5 seed 平均，N=2000。
python -I -X utf8 pred_t.py → work/t.json {gid: marginT}"""
import json, os, sys, collections, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np, torch
torch.set_num_threads(2)
import e229_live

LIVE = os.path.join(ROOT, 'reports', 'ovr-inseason-2026-27', 'live')
games = json.load(open(os.path.join(HERE, 'work', 'games.json')))
C = None; res = {}; t0 = time.time()
byd = collections.defaultdict(list)
for g in games:
    byd[(g['date'], g['folder'])].append(g)
for (d, f), gs in sorted(byd.items()):
    names = {p: 1 for g in gs for s in ('home', 'away') for p, _ in g['rot_' + s]}
    if C is None:
        C, info = e229_live.make_ctx(d, os.path.join(LIVE, f), names)
    else:
        B, tab, info = e229_live.build(d, os.path.join(LIVE, f), names)
        C.B = B; C.tab = tab
        C.med_h = float(np.median([x['heightInches'] for x in tab.values() if x.get('heightInches') is not None]))
    for g in gs:
        Rh, lh, rh = C.prep(g['rot_home']); Ra, la, ra = C.prep(g['rot_away'])
        rng = np.random.default_rng([229, int(g['gid'])])
        x = C.net100(C.draw(Rh, lh, rh, rng, 2000), C.draw(Ra, la, ra, rng, 2000))
        res[g['gid']] = float((x.mean(1) * C.avg_poss / 100).mean())
    print(d, f, len(gs), f'{time.time() - t0:.0f}s', info['nCurPlayers'], flush=True)
json.dump(res, open(os.path.join(HERE, 'work', 't.json'), 'w'))
print('DONE', len(res))
