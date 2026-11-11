"""E-225 推定位置 vs 卡片 pos 交叉表（report-only，只讀 split=train 的 2021-22..2024-25；以上場秒數加權）。
用法：python -I -X utf8 reports/E225-lineup-transformer/pos_crosstab.py"""
import csv, json, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_common import DATA, HERE, load_rows
from e225_model import SEASONS

NAMES = ['PG', 'SG', 'SF', 'PF', 'C']
cardpos = {}
for s in SEASONS:
    for r in csv.DictReader(open(os.path.join(DATA, f'players-{s}.csv'), encoding='utf-8')):
        cardpos[(s, r['pid'])] = r['pos'].split('-')[0]
tab = defaultdict(float)
for r in load_rows(SEASONS):
    for x in 'ab':
        for j in range(5):
            tab[(NAMES[r[f'p{x}{j}']], cardpos.get((r['season'], r[f'{x}{j}']), '無'))] += r['sec']
cards = sorted({c for _, c in tab}, key=lambda c: (c not in NAMES, NAMES.index(c) if c in NAMES else 9, c))
out = {'unit': '上場秒數占該推定位置的比例', 'rows': {}}
for p in NAMES:
    tot = sum(tab[(p, c)] for c in cards)
    out['rows'][p] = {c: round(tab[(p, c)] / tot, 3) for c in cards}
same = sum(tab[(p, p)] for p in NAMES) / sum(tab.values())
near = sum(tab[(p, c)] for p in NAMES for c in NAMES if abs(NAMES.index(p) - NAMES.index(c)) <= 1) / sum(tab.values())
out['exactMatch'] = round(same, 3); out['within1'] = round(near, 3)
json.dump(out, open(os.path.join(HERE, 'pos-crosstab.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('rows=推定位置, cols=卡片pos'); print('      ' + ' '.join(f'{c:>6}' for c in cards))
for p in NAMES:
    print(f'{p:>5} ' + ' '.join(f'{out["rows"][p][c]:6.3f}' for c in cards))
print('exact', out['exactMatch'], 'within±1', out['within1'])
