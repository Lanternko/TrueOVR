"""E-246 評估：T0／T1／T1h 的 Brier、logloss、分差相關；bootstrap seed 20261105。python -I -X utf8 eval.py → work/eval.json"""
import json, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
H, SIG, MDE = 2.5, 12.0, 0.013
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))
games = json.load(open(os.path.join(HERE, 'work', 'games.json')))
arms = {a: json.load(open(os.path.join(HERE, 'work', f't_{a}.json'))) for a in ('T0', 'T1', 'T1h')}
y = np.array([1.0 if g['pts_home'] > g['pts_away'] else 0.0 for g in games]); dif = np.array([g['pts_home'] - g['pts_away'] for g in games], float)
m = {a: np.array([v[g['gid']] for g in games]) for a, v in arms.items()}
p = {a: Phi((x + H) / SIG) for a, x in m.items()}
br = {a: (q - y) ** 2 for a, q in p.items()}
ll = {a: -(y * np.log(np.clip(q, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - q, 1e-6, 1))) for a, q in p.items()}
rng = np.random.default_rng(20261105); n = len(y); idx = rng.integers(0, n, (10000, n))
ci = lambda v: [float(np.percentile(v[idx].mean(1), 5)), float(np.percentile(v[idx].mean(1), 95))]
out = {'n': n, 'arms': {}, 'diff': {}}
for a in m:
    out['arms'][a] = dict(brier=float(br[a].mean()), logloss=float(ll[a].mean()), acc=float(((p[a] > .5) == (y > .5)).mean()),
                          corr=float(np.corrcoef(m[a], dif)[0, 1]), sd=float(m[a].std()))
for a in ('T1', 'T1h'):
    d = br[a] - br['T0']; c = ci(d)
    out['diff'][f'{a}-T0'] = dict(brier=float(d.mean()), brier_ci=c, logloss=float((ll[a] - ll['T0']).mean()), logloss_ci=ci(ll[a] - ll['T0']),
                                 marginShift=float(np.abs(m[a] - m['T0']).mean()), pass_=bool(d.mean() <= 0 and c[1] < MDE))
json.dump(out, open(os.path.join(HERE, 'work', 'eval.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
