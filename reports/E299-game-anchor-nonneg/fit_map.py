"""E-299 部分 R：2025-26 凍結 s = a + b·rt（卡片 0.2.14a OVR 對分鐘加權平均 rt，MIN≥500）。"""
import sys, json, csv
from pathlib import Path
import numpy as np
EXP = Path(__file__).resolve().parent; ROOT = EXP.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rating_m10 import Scorer
sc = Scorer('2025-26', 'Z1'); t = sc.tab
agg = {}
for nm, mn, s in zip(t.name, t.mn, sc.S):
    a = agg.setdefault(nm, [0.0, 0.0]); a[0] += mn * s; a[1] += mn
card = {r['name']: float(r['ovr']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.14a/ranking.csv', encoding='utf8')) if float(r['MIN']) >= 500}
X, Y = [], []
for nm, o in card.items():
    if nm in agg and agg[nm][1] >= 500: X.append(agg[nm][0] / agg[nm][1]); Y.append(o)
X, Y = np.array(X), np.array(Y)
b, a = np.polyfit(X, Y, 1)
r = np.corrcoef(X, Y)[0, 1]
gr = np.percentile(sc.S[t.mn >= 15], [10, 50, 90])
out = dict(a=a, b=b, n=len(X), r=r, rt_game_p10_50_90_min15=list(gr), s_at=list(a + b * gr))
print(out); json.dump(out, open(EXP / 'map.json', 'w'), indent=1)
