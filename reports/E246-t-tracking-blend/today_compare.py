"""E-246 次要：同一天（2026-11-04、同傷病、同陣容）T0 vs T1 的球隊評分名次。不寫正式 team-ratings.json，只寫 work/today_<arm>.json。
python -I -X utf8 today_compare.py"""
import os, sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts')); sys.path.insert(0, str(ROOT / 'reports/E229-transformer-vs-m0-forward'))
import e229_live, team_ratings_daily as M
for arm, blend in (('T0', ()), ('T1', e229_live.TRACK_CLASSES)):
    e229_live.BLEND_DEFAULT = blend
    M.compute(M.default_live_dir(), fetch=False, today='2026-11-04', engine='t', out=HERE / 'work' / f'today_{arm}.json')
R = {a: json.load(open(HERE / 'work' / f'today_{a}.json', encoding='utf-8'))['teams'] for a in ('T0', 'T1')}
rank = {}
for a, T in R.items():
    s = sorted(T.values(), key=lambda t: -t['c']['net'])
    rank[a] = {t['abbr']: (i + 1, round(t['c']['net'], 1), round(t['c']['predWins'], 1)) for i, t in enumerate(s)}
rows = sorted(rank['T0'], key=lambda k: rank['T1'][k][0])
for k in rows:
    print(k, 'T0', rank['T0'][k], 'T1', rank['T1'][k])
json.dump(rank, open(HERE / 'work' / 'today_rank.json', 'w'), indent=1)
