"""E-208 B／C 彙整 → BC-tables.json，並印出。"""
import csv, json, statistics as S, sys, math
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
H = Path(__file__).resolve().parent
B = list(csv.DictReader(open(H / 'B-players.csv', encoding='utf-8')))
C = list(csv.DictReader(open(H / 'C-players.csv', encoding='utf-8')))
def f(x):
    return float(x) if x not in ('', None) else None
for r in B:
    for k in r:
        if k not in ('name', 'pos'): r[k] = f(r[k])
def grp(m): return '<30' if m < 30 else ('30-90' if m < 90 else '>=90')
def ols(x, y):
    mx, my = S.fmean(x), S.fmean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    return b, my - b * mx
out = {}
for pre, lab in (('ovr', 'online(含usage層)'), ('raw', '只資料(不含usage層)')):
    d6 = [r[f'{pre}6'] - r['start'] for r in B]
    dE = [r[f'{pre}end'] - r['start'] for r in B]
    b, a = ols(d6, dE)
    o = {'n': len(B), 'slope': b, 'intercept': a, 'corr': S.correlation(d6, dE), 'meanD6': S.fmean(d6), 'meanDend': S.fmean(dE), 'groups': {}}
    for g in ('<30', '30-90', '>=90'):
        idx = [i for i, r in enumerate(B) if grp(r['min6']) == g]
        if not idx: continue
        m6, mE = S.fmean(d6[i] for i in idx), S.fmean(dE[i] for i in idx)
        o['groups'][g] = {'n': len(idx), 'meanD6': m6, 'meanDend': mE, 'ratio': mE / m6 if abs(m6) > 1e-9 else None,
                          'slope': ols([d6[i] for i in idx], [dE[i] for i in idx])[0] if len(idx) > 3 else None,
                          'corr': S.correlation([d6[i] for i in idx], [dE[i] for i in idx]) if len(idx) > 3 else None,
                          'sameSign': sum(1 for i in idx if d6[i] * dE[i] > 0), 'meanD3': S.fmean(B[i][f'{pre}3'] - B[i]['start'] for i in idx),
                          'meanD10': S.fmean(B[i][f'{pre}10'] - B[i]['start'] for i in idx), 'meanD20': S.fmean(B[i][f'{pre}20'] - B[i]['start'] for i in idx)}
    out['B_' + pre] = o
    print('==B', lab, {k: round(v, 3) for k, v in o.items() if isinstance(v, float)})
    for g, v in o['groups'].items(): print('  ', g, {k: (round(x, 2) if isinstance(x, float) else x) for k, x in v.items()})
ex = {}
for nm in ('Cooper Flagg', 'Dylan Harper', 'Kon Knueppel', 'VJ Edgecombe'):
    r = next(r for r in B if r['name'] == nm)
    ex[nm] = {k: round(r[k], 1) for k in ('min6', 'start', 'ovr3', 'ovr6', 'ovr10', 'ovr20', 'ovrend', 'raw6', 'rawend')}
    print(nm, ex[nm])
out['examples'] = ex
# 大幅回吐的人
for r in sorted(B, key=lambda r: -(r['ovr6'] - r['start']))[:6]:
    print('top d6', r['name'], round(r['min6']), round(r['start'], 1), round(r['ovr6'], 1), round(r['ovrend'], 1))
# C
print('== C')
pub = [(r['name'], float(r['pub_ovr']) - float(r['pub_last']), float(r['MIN26'] or 0), int(r['games'])) for r in C]
g90 = [p for p in pub if p[2] >= 90]
print('published >=90 MIN26: n', len(g90), 'mean dOVR', round(S.fmean(p[1] for p in g90), 2), 'others n', len(pub) - len(g90), 'mean', round(S.fmean(p[1] for p in pub if p[2] < 90), 2))
for p in sorted(g90, key=lambda p: -p[1]): print('  ', p[0], round(p[1], 1), p[2], p[3])
# 重播與線上對照
rep = [(float(r['ovrnow']) if r['ovrnow'] != '' else None, float(r['rawnow']) if r['rawnow'] != '' else None, float(r['pub_ovr']), float(r['start']), float(r['pub_last'])) for r in C]
ok = [x for x in rep if x[0] is not None]
print('replay(now) vs published: n', len(ok), 'mean(ovrC - pub)', round(S.fmean(x[0] - x[2] for x in ok), 2), 'corr', round(S.correlation([x[0] for x in ok], [x[2] for x in ok]), 3),
      'mean(raw - pub)', round(S.fmean(x[1] - x[2] for x in ok), 2), 'corr raw', round(S.correlation([x[1] for x in ok], [x[2] for x in ok]), 3))
out['C_replay_vs_pub'] = {'n': len(ok), 'meanC': S.fmean(x[0] - x[2] for x in ok), 'meanRaw': S.fmean(x[1] - x[2] for x in ok),
                          'corrC': S.correlation([x[0] for x in ok], [x[2] for x in ok]), 'corrRaw': S.correlation([x[1] for x in ok], [x[2] for x in ok])}
json.dump(out, open(H / 'BC-tables.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
