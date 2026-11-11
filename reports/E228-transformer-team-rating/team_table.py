"""E-228 報告用：2025-26 各隊預測勝場（T、M0）對實際。"""
import json, os, sys
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(D), 'E223-team-rating'))
import numpy as np
from e223_lib import *
from fit_train import features
zmap, zmiss, info = load_card(CARDS / SEASONS['2526']['card'])
F = features('2526', zmap, zmiss)
P = json.load(open(os.path.join(D, 'work', 'pred-T-2526.json')))
mT = np.array(P['margin_seed']).mean(0)
from scipy.stats import norm
y, home, away = np.array(F['y']), np.array(F['home']), np.array(F['away'])
rows = {}
for name, m in (('T', mT), ('M0', np.array(F['m0']))):
    p = norm.cdf((m + H) / SIGMA)
    for i in range(len(y)):
        rows.setdefault(home[i], {}).setdefault(name, 0.0); rows.setdefault(away[i], {}).setdefault(name, 0.0)
        rows[home[i]][name] += p[i]; rows[away[i]][name] += 1 - p[i]
for i in range(len(y)):
    w = y[i] > 0 if y.dtype != bool else y[i]
    rows[home[i]]['W'] = rows[home[i]].get('W', 0) + int(w); rows[away[i]]['W'] = rows[away[i]].get('W', 0) + int(not w)
out = sorted(({'team': str(t), **{k: round(float(v), 1) for k, v in r.items()}} for t, r in rows.items()), key=lambda r: -r['W'])
json.dump(out, open(os.path.join(D, 'results', 'team-wins-2526.json'), 'w'), indent=1)
for r in out: print(r)
