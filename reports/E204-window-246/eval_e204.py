"""E-204 比對：c0（WIN_LEN=328 重現開工時兩頁）、新舊版差異、季末四項 ρ、前 20 名進出。
用法（repo root）：python -I -X utf8 reports/E204-window-246/eval_e204.py   讀 data/_inseason_build/e204/{live,card}{328,246}/ranking.csv
輸出 reports/E204-window-246/results.json。人群與指標定義同 E-201（work/e201_metrics.py）。"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
B = ROOT / 'data/_inseason_build/e204'
sys.path.insert(0, str(ROOT / 'reports/E201-steeper-forgetting/work'))
import e201_metrics as M  # noqa: E402

res = {}

# --- c0(a)：線上頁，W328 重跑 vs 開工時線上頁（gh-pages e1c0391 的 index.html DATA）
cols = {}
for f, key in (('index.html', 'live'), ('2025-26.html', 'card')):
    d = json.loads((B / f'base-{f}.json').read_text(encoding='utf-8'))
    cols[key] = (d['cols'], {r[d['cols'].index('name')]: r for r in d['rows']})
live328 = {r['name']: r for r in csv.DictReader(open(B / 'live328/ranking.csv', encoding='utf-8'))}
c, rows = cols['live']
res['c0a_live_vs_published'] = {k: float(max(abs(float(r[c.index(k)]) - float(live328[n][k])) for n, r in rows.items() if n in live328 and r[c.index(k)] not in ('', None)))
                              for k in ('ovr',) + tuple(k for k in ('lastOVR', 'dOVR') if k in c)}
res['c0a_n'] = [len(rows), len(live328), len(set(rows) - set(live328))]
# --- c0(b)：卡片頁，W328 卡片路線 vs card-0.2.12-tov/ranking.csv（ovr）與開工時 2025-26 頁
card328 = {r['name']: r for r in csv.DictReader(open(B / 'card328/ranking.csv', encoding='utf-8'))}
cur_card = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.12-tov/ranking.csv', encoding='utf-8'))}
res['c0b_card_vs_card0212'] = {'max_abs_ovr': float(max(abs(float(card328[n]['ovr']) - float(r['ovr'])) for n, r in cur_card.items())), 'n': [len(card328), len(cur_card)]}
c, rows = cols['card']
res['c0b_card_vs_published'] = float(max(abs(float(r[c.index('ovr')]) - float(card328[n]['ovr'])) for n, r in rows.items() if n in card328))

# --- 老將 |ΔOVR|
l246 = {r['name']: r for r in csv.DictReader(open(B / 'live246/ranking.csv', encoding='utf-8'))}
vets = [n for n, r in live328.items() if r['formalOVR'] != '' and int(r['N']) >= 3 and float(r['MIN']) >= 500]
top12 = [r['name'] for r in sorted(live328.values(), key=lambda r: -float(r['ovr']))[:12]]
st = lambda L: {'vet_n': len(vets), 'abs_median': float(np.median([abs(float(L[n]['dOVR'])) for n in vets])),
                'gt2': int(sum(abs(float(L[n]['dOVR'])) > 2 for n in vets)), 'top12_abs_median': float(np.median([abs(float(L[n]['dOVR'])) for n in top12]))}
res['veteran'] = {'W328': st(live328), 'W246': st(l246)}
res['live_top12'] = [{'name': n, 'ovr328': float(live328[n]['ovr']), 'd328': float(live328[n]['dOVR']), 'ovr246': float(l246[n]['ovr']), 'd246': float(l246[n]['dOVR'])} for n in top12]
res['live_top10_move_abs_dOVR'] = [{'name': n, 'N': int(l246[n]['N']), 'd328': float(live328[n]['dOVR']), 'd246': float(l246[n]['dOVR'])}
                                   for n in sorted(vets, key=lambda n: -abs(float(l246[n]['dOVR'])))[:10]]


# --- 名次移動（兩頁；R-064／R-109）
def rank_move(a, b, k_top, k_move):
    ra = {n: i + 1 for i, n in enumerate(sorted(a, key=lambda n: -float(a[n]['ovr'])))}
    rb = {n: i + 1 for i, n in enumerate(sorted(b, key=lambda n: -float(b[n]['ovr'])))}
    ta, tb = {n for n, r in ra.items() if r <= k_top}, {n for n, r in rb.items() if r <= k_top}
    moved = [n for n in ra if ra[n] <= 100 and n in rb and abs(ra[n] - rb[n]) >= 10]
    moved_any = [n for n in ra if (ra[n] <= 100 or rb.get(n, 999) <= 100) and n in rb and abs(ra[n] - rb[n]) >= 10]
    return {'top20_out': sorted(ta - tb, key=lambda n: ra[n]), 'top20_in': sorted(tb - ta, key=lambda n: rb[n]), 'n_top20_swapped': len(ta - tb),
            'top100_moved_ge10_by_old_rank': len(moved), 'top100_moved_ge10_either': len(moved_any), 'ra': ra, 'rb': rb}


card246 = {r['name']: r for r in csv.DictReader(open(B / 'card246/ranking.csv', encoding='utf-8'))}
for key, a, b in (('live', live328, l246), ('card', card328, card246)):
    m = rank_move(a, b, 20, 10)
    res[f'move_{key}'] = {k: v for k, v in m.items() if k not in ('ra', 'rb')}
    if key == 'card':
        ra, rb = m['ra'], m['rb']
    # MIN>=500
    names = [n for n in a if float(a[n]['MIN']) >= 500]
    d = [abs(float(b[n]['ovr']) - float(a[n]['ovr'])) for n in names]
    res[f'move_{key}']['ovr_abs_change_median_min500'] = float(np.median(d))
    res[f'move_{key}']['ovr_abs_change_max'] = float(max(d))
    res[f'move_{key}']['top12_old'] = [{'name': n, 'rank328': m['ra'][n], 'ovr328': float(a[n]['ovr']), 'rank246': m['rb'][n], 'ovr246': float(b[n]['ovr'])}
                                       for n in sorted(a, key=lambda n: m['ra'][n])[:12]]
    res[f'move_{key}']['top20_new'] = [(n, m['rb'][n]) for n in sorted(b, key=lambda n: m['rb'][n])[:20]]

# --- 季末四項 ρ（卡片路線，MIN>=500；同 E-201 口徑）
def by_pid(path):
    return M.read_rank(path)
r328, r246 = by_pid(B / 'card328/ranking.csv'), by_pid(B / 'card246/ranking.csv')
res['rho_card328'], res['rho_card246'] = M.rhos(r328), M.rhos(r246)
res['rho_diff_246_minus_328'] = {k: res['rho_card246'][k]['rho'] - res['rho_card328'][k]['rho'] for k in M.ITEMS}
res['rho_paired_h'] = M.paired_h(r328, r246)
(ROOT / 'reports/E204-window-246/results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: res[k] for k in ('c0a_live_vs_published', 'c0a_n', 'c0b_card_vs_card0212', 'c0b_card_vs_published', 'veteran', 'rho_card328', 'rho_card246', 'rho_diff_246_minus_328')}, ensure_ascii=False, indent=1))
for key in ('live', 'card'):
    m = res[f'move_{key}']
    print(key, 'top20 出', m['top20_out'], '進', m['top20_in'], '前100移動>=10:', m['top100_moved_ge10_by_old_rank'], m['top100_moved_ge10_either'], 'median|d|', m['ovr_abs_change_median_min500'])
