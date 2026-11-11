"""E-229b 評估：T、M0、各半、B0（只用 H）。python -I -X utf8 eval.py → work/eval.json、印表"""
import json, os, math, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
H, SIG = 2.5, 12.0
Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
games = json.load(open(os.path.join(HERE, 'work', 'games.json')))
m0 = json.load(open(os.path.join(HERE, 'work', 'm0.json'))); tt = json.load(open(os.path.join(HERE, 'work', 't.json')))
ab = {}
for t in json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'data/season-source-2026-27/team-games.json'), encoding='utf-8'))['data']['resultSets'][0]['rowSet'] if False else []:
    pass
rows = []
for g in games:
    mM = m0[f"{g['gid']}|home"] - m0[f"{g['gid']}|away"]; mT = tt[g['gid']]
    y = 1.0 if g['pts_home'] > g['pts_away'] else 0.0
    rows.append((g['date'], g['home'], g['away'], y, Phi((mT + H) / SIG), Phi((mM + H) / SIG), mT, mM, g['pts_home'] - g['pts_away']))
y = np.array([r[3] for r in rows]); pT = np.array([r[4] for r in rows]); pM = np.array([r[5] for r in rows])
mT = np.array([r[6] for r in rows]); mM = np.array([r[7] for r in rows]); dif = np.array([r[8] for r in rows])
pH = np.full(len(y), Phi(H / SIG)); pA = 0.5 * (pT + pM)
eps = 1e-6
def brier(p): return (p - y) ** 2
def ll(p): q = np.clip(p, eps, 1 - eps); return -(y * np.log(q) + (1 - y) * np.log(1 - q))
def acc(p): return ((p > 0.5) == (y > 0.5)).astype(float)
M = {'T': pT, 'M0': pM, 'avg': pA, 'B0': pH}
rng = np.random.default_rng(20261102); n = len(y); idx = rng.integers(0, n, (10000, n))
def ci(v): b = v[idx].mean(1); return float(np.percentile(b, 5)), float(np.percentile(b, 95))
out = {'n': n, 'homeWinRate': float(y.mean()), 'models': {}, 'diff': {}}
for k, p in M.items():
    out['models'][k] = {m: dict(v=float(f(p).mean()), ci=ci(f(p))) for m, f in (('brier', brier), ('logloss', ll), ('acc', acc))}
for a, b in (('T', 'M0'), ('T', 'B0'), ('M0', 'B0'), ('avg', 'M0'), ('avg', 'T')):
    out['diff'][f'{a}-{b}'] = {m: dict(v=float((f(M[a]) - f(M[b])).mean()), ci=ci(f(M[a]) - f(M[b]))) for m, f in (('brier', brier), ('logloss', ll), ('acc', acc))}
out['corr_margin'] = float(np.corrcoef(mT, mM)[0, 1]); out['corr_T_actual'] = float(np.corrcoef(mT, dif)[0, 1]); out['corr_M0_actual'] = float(np.corrcoef(mM, dif)[0, 1])
out['sd_margin'] = dict(T=float(mT.std()), M0=float(mM.std()), actual=float(dif.std()))
# 校準分箱（M0 與 T 預測的主場勝率）
out['calib'] = {}
for k in ('T', 'M0'):
    p = M[k]; bins = [(0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, 1.01)]
    out['calib'][k] = [dict(lo=lo, hi=min(hi, 1), n=int(((p >= lo) & (p < hi)).sum()), pred=float(p[(p >= lo) & (p < hi)].mean()) if ((p >= lo) & (p < hi)).any() else None,
                            obs=float(y[(p >= lo) & (p < hi)].mean()) if ((p >= lo) & (p < hi)).any() else None) for lo, hi in bins]
# 各隊
tn = {}
ti = json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'reports/E208-team-rating/inputs.json'), encoding='utf-8'))['teams']
T = collections.defaultdict(lambda: dict(n=0, w=0.0, eT=0.0, eM=0.0, bT=0.0, bM=0.0))
for r in rows:
    for side, tid in ((1, r[1]), (0, r[2])):
        won = r[3] if side else 1 - r[3]; qT = r[4] if side else 1 - r[4]; qM = r[5] if side else 1 - r[5]
        t = T[tid]; t['n'] += 1; t['w'] += won; t['eT'] += qT; t['eM'] += qM; t['bT'] += (qT - won) ** 2; t['bM'] += (qM - won) ** 2
out['teams'] = {ti[k]['abbr']: v for k, v in T.items()}
json.dump(out, open(os.path.join(HERE, 'work', 'eval.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: out[k] for k in ('n', 'homeWinRate', 'models', 'diff', 'corr_margin', 'corr_T_actual', 'corr_M0_actual', 'sd_margin')}, indent=1))
print(json.dumps(out['calib']))
for a, v in sorted(out['teams'].items()):
    print(a, v['n'], round(v['w'], 0), round(v['eT'], 2), round(v['eM'], 2))
