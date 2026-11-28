"""E-308 描述性附表（不進判定）：殘差五分位在 2026-27 的表現、LaMelo 名次。讀 players.csv。"""
import csv
import json
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parent
P = list(csv.DictReader(open(D / 'players.csv', encoding='utf-8')))
f = lambda r, k: float(r[k]) if r[k] not in ('', 'None') else None
out = {}
h1 = [r for r in P if f(r, 'y2r') is not None]
for key in ['R_OO', 'R_RAPM']:
    rs = sorted([r for r in h1 if f(r, key) is not None], key=lambda r: f(r, key))
    n = len(rs); q = n // 5
    out[key] = {}
    for name, grp in [('bottom20', rs[:q]), ('middle60', rs[q:n - q]), ('top20', rs[n - q:])]:
        w = np.array([f(r, 'p27') for r in grp])
        out[key][name] = {'n': len(grp),
                          'y1r_mean': round(float(np.average([f(r, 'y1r') for r in grp], weights=w)), 2),
                          'y2r_mean': round(float(np.average([f(r, 'y2r') for r in grp], weights=w)), 3),
                          'share_y1_above_ovr': round(float(np.mean([f(r, 'y1r') > 0 for r in grp])), 2),
                          'share_y2_above_ovr': round(float(np.mean([f(r, 'y2r') > 0 for r in grp])), 2)}
lm = next(r for r in P if r['name'] == 'LaMelo Ball')
rank = lambda k, rows: 1 + sum(f(r, k) is not None and f(r, k) > f(lm, k) for r in rows)
out['LaMelo'] = {'pool': len(P), 'h1': len(h1), **{f'rank_{k}': rank(k, P) for k in ['ovr', 'oo4s', 'R_OO', 'rapm', 'R_RAPM', 'darko']},
                 **{f'rankH1_{k}': rank(k, h1) for k in ['ovr', 'y1', 'y2', 'y1r', 'y2r']}}
json.dump(out, open(D / 'extra.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
