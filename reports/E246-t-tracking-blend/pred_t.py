"""E-246 三臂 T 預測（同 E-229b pred_t：同一份陣容分鐘、5 seed、N=2000、同亂數種子），只換 21 欄統計的混合類別。
python -I -X utf8 pred_t.py → work/t_<arm>.json {gid: marginT}"""
import json, os, sys, collections, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np, torch
torch.set_num_threads(4)
import e229_live

ARMS = {'T0': (), 'T1': e229_live.TRACK_CLASSES, 'T1h': ('hustle',)}
LIVE = os.path.join(ROOT, 'reports', 'ovr-inseason-2026-27', 'live')
games = json.load(open(os.path.join(HERE, 'work', 'games.json')))
byd = collections.defaultdict(list)
for g in games:
    byd[(g['date'], g['folder'])].append(g)
for arm, blend in ARMS.items():
    C = None; res = {}; t0 = time.time(); ntr = []
    for (d, f), gs in sorted(byd.items()):
        names = {p: 1 for g in gs for s in ('home', 'away') for p, _ in g['rot_' + s]}
        snap = os.path.join(HERE, 'snap', d)
        if C is None:
            C, info = e229_live.make_ctx(d, os.path.join(LIVE, f), names, blend, snap)
        else:
            B, tab, info = e229_live.build(d, os.path.join(LIVE, f), names, blend, snap)
            C.B = B; C.tab = tab
            C.med_h = float(np.median([x['heightInches'] for x in tab.values() if x.get('heightInches') is not None]))
        ntr.append((d, info['nBlendedTrack']))
        for g in gs:
            Rh, lh, rh = C.prep(g['rot_home']); Ra, la, ra = C.prep(g['rot_away'])
            rng = np.random.default_rng([229, int(g['gid'])])
            x = C.net100(C.draw(Rh, lh, rh, rng, 2000), C.draw(Ra, la, ra, rng, 2000))
            res[g['gid']] = float((x.mean(1) * C.avg_poss / 100).mean())
    json.dump(res, open(os.path.join(HERE, 'work', f't_{arm}.json'), 'w'))
    print(arm, 'DONE', len(res), f'{time.time() - t0:.0f}s', 'nBlendedTrack', ntr, flush=True)
