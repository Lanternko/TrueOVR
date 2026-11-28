"""稽核 A5：stamina 與賽季總分鐘的相關（2025-26，276 人 + 全表）。"""
import csv, json, os, numpy as np
from scipy.stats import spearmanr
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = json.load(open(os.path.join(R, 'results/value-raw.json'), encoding='utf-8'))
st = {r['pid']: float(r['stamina']) for r in csv.DictReader(open(os.path.join(R, 'data/players-2025-26.csv'), encoding='utf-8')) if r['stamina'] != ''}
ix = [i for i, p in enumerate(raw['pids']) if p in st]
print('n', len(ix), 'spearman(stamina, 賽季總分鐘)', round(float(spearmanr([st[raw['pids'][i]] for i in ix], [raw['min'][i] for i in ix])[0]), 3))
sm = {}
for s in ['2021-22','2022-23','2023-24','2024-25','2025-26']:
    p = {r['pid']: r for r in csv.DictReader(open(os.path.join(R, f'data/players-{s}.csv'), encoding='utf-8'))}
    st2 = {r['pid']: r for r in csv.DictReader(open(os.path.join(R, f'data/stats-{s}.csv'), encoding='utf-8'))}
    cols = [c for c in st2[next(iter(st2))] if 'min' in c.lower() or c.lower() in ('mpg',)]
    print(s, 'n players', len(p), 'stats cols with min:', cols)
