# E-208 backtest analysis. All rules fixed in preregistration.md. usage: python -I -X utf8 analyze.py
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, os, math
import numpy as np
from common import *
inp = json.load(open(os.path.join(HERE, 'inputs.json'), encoding='utf8'))
G = inp['games']; n = len(G)
home = np.array([str(g['home']) for g in G]); away = np.array([str(g['away']) for g in G])
d = np.array([g['hs'] - g['as'] for g in G], float); y = (d > 0).astype(float)
ids = sorted(inp['teams'])
Wact = {t: inp['teams'][t]['W'] for t in ids}
phi = np.vectorize(Phi)
def probs(pm): return np.clip(phi(pm / SIGMA), 1e-6, 1 - 1e-6)
def per_game(pm):
    p = probs(pm)
    return dict(brier=(p - y) ** 2, logloss=-(y * np.log(p) + (1 - y) * np.log(1 - p)), hit=((p > .5) == (y > .5)).astype(float), mae=np.abs(pm - d), p=p)
def wins_mae(p, idx=None):
    idx = np.arange(n) if idx is None else idx
    pw = {t: 0.0 for t in ids}; aw = {t: 0.0 for t in ids}
    for i in idx:
        pw[home[i]] += p[i]; pw[away[i]] += 1 - p[i]; aw[home[i]] += y[i]; aw[away[i]] += 1 - y[i]
    return mean([abs(pw[t] - aw[t]) for t in ids]), pw
# --- predictors (predicted home-minus-away margin incl. home points) ---
net24 = {t: inp['base2425'][t]['net'] for t in ids}
preds = {'B-coin': np.full(n, H), 'B0': np.array([net24[home[i]] - net24[away[i]] + H for i in range(n)])}
for V in ['P', 'I']:
    gm = {o['i']: mean(o['m']) for o in load('games-' + V)}
    assert len(gm) == n, (V, len(gm))
    preds[V + '(a)'] = np.array([gm[g['i']] + H for g in G])
    pr = {(o['h'], o['a']): mean(o['m']) for o in load('pairspre-' + V)}
    assert len(pr) == 870
    preds[V + '(b)'] = np.array([pr[(home[i], away[i])] + H for i in range(n)])
pg = {k: per_game(v) for k, v in preds.items()}
rng = np.random.default_rng(20261102); B = 2000
boots = [rng.integers(0, n, n) for _ in range(B)]
def ci(f):
    v = np.array([f(ix) for ix in boots]); return [float(np.percentile(v, 5)), float(np.percentile(v, 95))]
out = {'n_games': n, 'H': H, 'sigma': SIGMA, 'metrics': {}, 'diffs': {}}
for k in preds:
    wm, _ = wins_mae(pg[k]['p'])
    out['metrics'][k] = dict(brier=float(pg[k]['brier'].mean()), logloss=float(pg[k]['logloss'].mean()), hit=float(pg[k]['hit'].mean()),
                             margin_mae=float(pg[k]['mae'].mean()), win_total_mae=float(wm))
def diff(a, b):
    r = {}
    for m in ['brier', 'logloss', 'mae']:
        r[m] = dict(diff=float(pg[a][m].mean() - pg[b][m].mean()), ci90=ci(lambda ix: pg[a][m][ix].mean() - pg[b][m][ix].mean()))
    r['hit'] = dict(diff=float(pg[a]['hit'].mean() - pg[b]['hit'].mean()), ci90=ci(lambda ix: pg[a]['hit'][ix].mean() - pg[b]['hit'][ix].mean()))
    r['win_total_mae'] = dict(diff=float(wins_mae(pg[a]['p'])[0] - wins_mae(pg[b]['p'])[0]),
                              ci90=ci(lambda ix: wins_mae(pg[a]['p'], ix)[0] - wins_mae(pg[b]['p'], ix)[0]))
    return r
for a, b in [('P(a)', 'B0'), ('P(a)', 'B-coin'), ('B0', 'B-coin'), ('P(b)', 'B0'), ('P(a)', 'P(b)'), ('I(a)', 'B0'), ('I(a)', 'P(a)')]:
    out['diffs'][a + ' - ' + b] = diff(a, b)
# slope diagnostic (informational only; nothing is refit)
for k in ['P(a)', 'I(a)', 'B0']:
    x = preds[k] - H; out['metrics'][k]['slope_actual_on_pred'] = float(np.polyfit(x, d, 1)[0])
# --- team ratings ---
act = inp['actual2526']; off = inp['official2526']
def rating_stats(R):
    o = {}
    for key in ['ortg', 'drtg', 'net']:
        mv = np.array([R[t][key] for t in ids]); av = np.array([act[t][key] for t in ids]); ov = np.array([off[t][key] for t in ids])
        mc = mv - mv.mean(); ac = av - av.mean(); oc = ov - ov.mean()
        o[key] = dict(mae_centered_vs_estimator=float(np.abs(mc - ac).mean()), corr_estimator=float(np.corrcoef(mv, av)[0, 1]),
                      mae_centered_vs_official=float(np.abs(mc - oc).mean()), corr_official=float(np.corrcoef(mv, ov)[0, 1]))
    return o
b24 = np.array([net24[t] for t in ids]); a25 = np.array([act[t]['net'] for t in ids])
out['ratings'] = {'B0 (2024-25 net)': dict(net=dict(mae_centered_vs_estimator=float(np.abs((b24 - b24.mean()) - (a25 - a25.mean())).mean()), corr_estimator=float(np.corrcoef(b24, a25)[0, 1])))}
teamrows = {}
for V in ['P', 'I']:
    for s, lab in [('SA', 'seasonAvg'), ('Pre', 'pre')]:
        R = rating(load('rating-' + lab + '-' + V)); assert len(R) == 30
        out['ratings'][V + ' ' + lab] = rating_stats(R); teamrows[V + ' ' + lab] = R
# --- team table: predicted vs actual wins (P(a) main) ---
_, pw = wins_mae(pg['P(a)']['p']); _, pw0 = wins_mae(pg['B0']['p']); _, pwb = wins_mae(pg['P(b)']['p'])
tab = sorted([dict(id=t, name=inp['teams'][t]['name'], abbr=inp['teams'][t]['abbr'], actual=Wact[t], P_a=pw[t], P_b=pwb[t], B0=pw0[t],
                   err=pw[t] - Wact[t]) for t in ids], key=lambda r: -r['actual'])
out['teams'] = tab
json.dump(out, open(os.path.join(HERE, 'analysis.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(json.dumps(out['metrics'], indent=1)); print(json.dumps(out['diffs'], indent=1)); print(json.dumps(out['ratings'], indent=1))
for r in tab: print(r['abbr'], r['actual'], round(r['P_a'], 1), round(r['P_b'], 1), round(r['B0'], 1))
c = out['diffs']['P(a) - B0']['brier']
print('PASS' if c['ci90'][1] < 0 else 'NOT PASS', c)
