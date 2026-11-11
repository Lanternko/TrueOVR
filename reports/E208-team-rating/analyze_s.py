# E-208 追加分析（兩季 × 分鐘 a/b/c/d）。規則全在 preregistration-2024-25.md。usage: python -I -X utf8 analyze_s.py 2425|2526
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, math
import numpy as np
from common import *
S = sys.argv[1]
cfg = {'2425': dict(inp='inputs-2425.json', V='Q', base='base2324', act='actual2425', off=None, sfx='25', mainset=['I']),
       '2526': dict(inp='inputs.json', V='P', base='base2425', act='actual2526', off='official2526', sfx='', mainset=['I'])}[S]
V = cfg['V']; sfx = cfg['sfx']
inp = json.load(open(os.path.join(HERE, cfg['inp']), encoding='utf8'))
G = inp['games']; n = len(G)
home = np.array([str(g['home']) for g in G]); away = np.array([str(g['away']) for g in G])
d = np.array([g['hs'] - g['as'] for g in G], float); y = (d > 0).astype(float)
ids = sorted(inp['teams']); Wact = {t: inp['teams'][t]['W'] for t in ids}
phi = np.vectorize(Phi)
def per_game(pm):
    p = np.clip(phi(pm / SIGMA), 1e-6, 1 - 1e-6)
    return dict(brier=(p - y) ** 2, logloss=-(y * np.log(p) + (1 - y) * np.log(1 - p)), hit=((p > .5) == (y > .5)).astype(float), mae=np.abs(pm - d), p=p)
def wins_mae(p, idx=None):
    idx = np.arange(n) if idx is None else idx
    pw = {t: 0.0 for t in ids}; aw = {t: 0.0 for t in ids}
    for i in idx:
        pw[home[i]] += p[i]; pw[away[i]] += 1 - p[i]; aw[home[i]] += y[i]; aw[away[i]] += 1 - y[i]
    return mean([abs(pw[t] - aw[t]) for t in ids]), pw
net0 = {t: inp[cfg['base']][t]['net'] for t in ids}
preds = {'B-coin': np.full(n, H), 'B0': np.array([net0[home[i]] - net0[away[i]] + H for i in range(n)])}
def gm(tag):
    r = {o['i']: mean(o['m']) for o in load(tag)}; assert len(r) == n, (tag, len(r)); return np.array([r[g['i']] + H for g in G])
for W in [V, 'I']:
    if W == 'I' and S == '2526': t = lambda k: k + '-I'
    else: t = lambda k, W=W: k + '-' + W + sfx
    preds[W + '(a)'] = gm(t('games'))
    pr = {(o['h'], o['a']): mean(o['m']) for o in load(t('pairspre'))}; assert len(pr) == 870
    preds[W + '(b)'] = np.array([pr[(home[i], away[i])] + H for i in range(n)])
for c in 'CD':
    preds[V + '(' + c.lower() + ')'] = gm('games' + c + '-' + V + sfx)
pg = {k: per_game(v) for k, v in preds.items()}
rng = np.random.default_rng(20261102); B = 2000
boots = [rng.integers(0, n, n) for _ in range(B)]
def ci(f):
    v = np.array([f(ix) for ix in boots]); return [float(np.percentile(v, 5)), float(np.percentile(v, 95))]
out = {'season': S, 'n_games': n, 'metrics': {}, 'diffs': {}}
for k in preds:
    wm, _ = wins_mae(pg[k]['p'])
    out['metrics'][k] = dict(brier=float(pg[k]['brier'].mean()), logloss=float(pg[k]['logloss'].mean()), hit=float(pg[k]['hit'].mean()), margin_mae=float(pg[k]['mae'].mean()), win_total_mae=float(wm))
def diff(a, b):
    r = {}
    for m in ['brier', 'logloss', 'mae', 'hit']:
        r[m] = dict(diff=float(pg[a][m].mean() - pg[b][m].mean()), ci90=ci(lambda ix: pg[a][m][ix].mean() - pg[b][m][ix].mean()))
    r['win_total_mae'] = dict(diff=float(wins_mae(pg[a]['p'])[0] - wins_mae(pg[b]['p'])[0]), ci90=ci(lambda ix: wins_mae(pg[a]['p'], ix)[0] - wins_mae(pg[b]['p'], ix)[0]))
    return r
pairs = [(f'{V}(b)', 'B0'), (f'{V}(c)', f'{V}(b)'), (f'{V}(d)', f'{V}(c)'), (f'{V}(d)', f'{V}(b)'), (f'{V}(c)', 'B0'), (f'{V}(d)', 'B0'), (f'{V}(a)', f'{V}(b)'), (f'{V}(a)', 'B0'), ('B0', 'B-coin'), (f'{V}(b)', 'B-coin'), ('I(b)', 'B0'), ('I(b)', f'{V}(b)')]
for a, b in pairs: out['diffs'][a + ' - ' + b] = diff(a, b)
for k in [f'{V}(a)', f'{V}(b)', f'{V}(c)', f'{V}(d)', 'B0']:
    out['metrics'][k]['slope_actual_on_pred'] = float(np.polyfit(preds[k] - H, d, 1)[0])
# ratings (team vs league-average team; (a)-free: seasonAvg / pre rosters)
act = inp[cfg['act']]; off = inp[cfg['off']] if cfg['off'] else None
def rstats(R):
    o = {}
    for key in ['ortg', 'drtg', 'net']:
        mv = np.array([R[t][key] for t in ids]); av = np.array([act[t][key] for t in ids]); mc = mv - mv.mean(); ac = av - av.mean()
        o[key] = dict(mae_centered_vs_estimator=float(np.abs(mc - ac).mean()), corr_estimator=float(np.corrcoef(mv, av)[0, 1]))
        if off:
            ov = np.array([off[t][key] for t in ids]); oc = ov - ov.mean(); o[key].update(mae_centered_vs_official=float(np.abs(mc - oc).mean()), corr_official=float(np.corrcoef(mv, ov)[0, 1]))
    return o
b0 = np.array([net0[t] for t in ids]); a0 = np.array([act[t]['net'] for t in ids])
out['ratings'] = {'B0 net': dict(net=dict(mae_centered_vs_estimator=float(np.abs((b0 - b0.mean()) - (a0 - a0.mean())).mean()), corr_estimator=float(np.corrcoef(b0, a0)[0, 1])))}
for W in [V, 'I']:
    for lab in ['seasonAvg', 'pre']:
        tg = 'rating-' + lab + '-' + W + ('' if (W == 'I' and S == '2526') else sfx) if not (W == 'I' and S == '2526') else 'rating-' + lab + '-I'
        if W == V and S == '2526': tg = 'rating-' + lab + '-' + V
        R = rating(load(tg)); assert len(R) == 30, tg; out['ratings'][W + ' ' + lab] = rstats(R)
# team table: predicted vs actual wins for (b) main, plus a, c, d, B0
pw = {k: wins_mae(pg[k]['p'])[1] for k in [f'{V}(a)', f'{V}(b)', f'{V}(c)', f'{V}(d)', 'B0']}
tab = sorted([dict(id=t, name=inp['teams'][t]['name'], abbr=inp['teams'][t]['abbr'], actual=Wact[t], n_games=sum(1 for i in range(n) if home[i] == t or away[i] == t),
                   a=pw[f'{V}(a)'][t], b=pw[f'{V}(b)'][t], c=pw[f'{V}(c)'][t], d=pw[f'{V}(d)'][t], B0=pw['B0'][t]) for t in ids], key=lambda r: -r['actual'])
out['teams'] = tab
json.dump(out, open(os.path.join(HERE, f'analysis-{S}.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
for k, v in out['metrics'].items(): print(k, {a: round(b, 4) for a, b in v.items()})
for k, v in out['diffs'].items(): print(k, 'brier', round(v['brier']['diff'], 5), [round(z, 5) for z in v['brier']['ci90']], 'wins', round(v['win_total_mae']['diff'], 3), [round(z, 3) for z in v['win_total_mae']['ci90']])
for r in tab: print(r['abbr'], r['actual'], r['n_games'], *[round(r[k], 1) for k in 'abcd'], round(r['B0'], 1))
