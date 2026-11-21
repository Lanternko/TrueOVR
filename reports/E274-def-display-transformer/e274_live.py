"""E-274 本季 live 例子（只報告）：2026-27 上線 T（make_ctx）的換人防守值 D2 與現行 DEF（D0）名次。
python -I -B -X utf8 reports/E274-def-display-transformer/e274_live.py"""
import csv, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports' / 'E229-transformer-vs-m0-forward'))
sys.path.insert(0, str(ROOT / 'reports' / 'E228-transformer-team-rating'))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(1, str(HERE))
import numpy as np
import torch
torch.set_num_threads(6)
import e229_live as L
import season_nav as SN
from e274_swap import swap_values

today = '2026-11-08'
C, info = L.make_ctx(today)
ldir = L.live_dir()
rows = list(csv.DictReader(open(os.path.join(ldir, 'ranking.csv'), encoding='utf-8')))
name = {r['playerId']: r['name'] for r in rows}
pool = [r['playerId'] for r in rows if float(r.get('MIN26') or 0) >= 150 and r['playerId'] in C.B]
v = swap_values(C, pool)
od, bad = SN.off_def(rows, 'playerId')
d0 = {p: od[p][1] for p in pool if od.get(p) and od[p][1] is not None}
ids = [p for p in pool if p in d0]
d2 = {p: -v[p] for p in ids}


def rank(dct):
    s = sorted(ids, key=lambda p: -dct[p])
    return {p: i + 1 for i, p in enumerate(s)}


r0, r2 = rank(d0), rank(d2)
mu = np.mean([v[p] for p in ids])
bigs = [r['name'] for r in sorted(rows, key=lambda r: -float(r['ovr'])) if r['pos'] == 'C' and r['playerId'] in d0][:10]
want = ['Kevin Durant', 'Stephen Curry', 'Fred VanVleet', 'Victor Wembanyama', 'Rudy Gobert', 'Alex Caruso', 'Amen Thompson', 'Alperen Sengun',
        'Nikola Jokić', 'Trae Young'] + bigs
out = {'date': today, 'dataDir': ldir, 'n_pool': len(pool), 'n_ranked': len(ids), 'off_def_bad': bad, 'bigs': bigs, 'players': {}}
seen = set()
for n in want:
    if n in seen:
        continue
    seen.add(n)
    p = next((p for p in ids if name[p] == n), None)
    if p:
        out['players'][n] = {'D0': d0[p], 'D0_rank': r0[p], 'D2_oppPts100_vs_avg': v[p] - mu, 'D2_rank': r2[p]}
json.dump(out, open(HERE / 'live-examples.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n, x in out['players'].items():
    print(f'{n:22s} D0 {x["D0"]:+.2f} 名次 {x["D0_rank"]:3d} | D2 對手得分 {x["D2_oppPts100_vs_avg"]:+.2f} 名次 {x["D2_rank"]:3d}')
print('pool', len(ids))
