"""E-208 C 彙整 → C-tables.json。"""
import csv, json, statistics as S, sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
H = Path(__file__).resolve().parent
B = list(csv.DictReader(open(H / 'B-players.csv', encoding='utf-8')))
C = list(csv.DictReader(open(H / 'C-players.csv', encoding='utf-8')))
f = lambda x: float(x) if x not in ('', None) else None
for r in B:
    for k in r:
        if k not in ('name', 'pos'): r[k] = f(r[k])
for r in C:
    for k in r:
        if k != 'name': r[k] = f(r[k])
bt = json.load(open(H / 'BC-tables.json', encoding='utf-8'))
def ols(x, y):
    mx, my = S.fmean(x), S.fmean(y); b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sum((a - mx) ** 2 for a in x); return b, my - b * mx
out = {}
# usage 層貢獻（線上 − 只資料）
out['layerB'] = {str(N): S.fmean(r[f'ovr{N}'] - r[f'raw{N}'] for r in B) for N in (3, 6, 10, 20, 'end')}
print('B usage layer shift by N', {k: round(v, 2) for k, v in out['layerB'].items()})
Cg = [r for r in C if (r['MIN26'] or 0) >= 90]
Co = [r for r in C if (r['MIN26'] or 0) < 90]
out['pub'] = {'n90': len(Cg), 'mean90': S.fmean(r['pub_ovr'] - r['pub_last'] for r in Cg), 'nOther': len(Co), 'meanOther': S.fmean(r['pub_ovr'] - r['pub_last'] for r in Co)}
out['layerC'] = {'pubMinusRaw_now_ge90': S.fmean(r['pub_ovr'] - r['rawnow'] for r in Cg), 'ovrCminusRaw_now_ge90': S.fmean(r['ovrnow'] - r['rawnow'] for r in Cg)}
print(out['pub'], out['layerC'])
# 有 >=6 場的 >=90 分鐘 2026 球員：第 6 場重播 Δ，放進 B 分布
Cg6 = [r for r in Cg if r['games'] >= 6]
B90 = [r for r in B if r['min6'] >= 90]
d6B = sorted(r['ovr6'] - r['start'] for r in B90)
d6Braw = sorted(r['raw6'] - r['start'] for r in B90)
def pct(v, arr): return sum(a <= v for a in arr) / len(arr)
b_all, a_all = bt['B_ovr']['slope'], bt['B_ovr']['intercept']
b90 = bt['B_ovr']['groups']['>=90']['slope']
rb_all, ra_all = bt['B_raw']['slope'], bt['B_raw']['intercept']
rows = []
for r in Cg6:
    d6 = r['ovr6'] - r['start']; r6 = r['raw6'] - r['start']
    est = a_all + b_all * d6                       # B 全體線性關係（含 usage 層）
    estRaw = ra_all + rb_all * r6 + out['layerB']['end']   # 資料部分用 B 斜率、usage 層補到滿
    rows.append({'name': r['name'], 'pick': r['pick'], 'games': r['games'], 'min6': r['min6'], 'pubD': r['pub_ovr'] - r['pub_last'], 'd6': d6, 'raw_d6': r6,
                 'pctInB90': pct(d6, d6Braw if False else d6B), 'estEnd_B': est, 'estEnd_layerSplit': estRaw})
out['C90_ge6'] = rows
out['C90_summary'] = {'n': len(rows), 'meanPubD': S.fmean(x['pubD'] for x in rows), 'meanD6': S.fmean(x['d6'] for x in rows), 'meanRawD6': S.fmean(x['raw_d6'] for x in rows),
                      'meanEstEnd_B': S.fmean(x['estEnd_B'] for x in rows), 'meanEstEnd_split': S.fmean(x['estEnd_layerSplit'] for x in rows),
                      'B90_meanD6': S.fmean(d6B), 'B90_meanDend': bt['B_ovr']['groups']['>=90']['meanDend'],
                      'B90_meanRawD6': bt['B_raw']['groups']['>=90']['meanD6'], 'B90_meanRawDend': bt['B_raw']['groups']['>=90']['meanDend']}
print(json.dumps(out['C90_summary'], ensure_ascii=False, indent=0))
for x in sorted(rows, key=lambda x: -x['d6']): print(x['name'], x['pick'], round(x['pubD'], 1), round(x['d6'], 1), round(x['raw_d6'], 1), 'pct', round(x['pctInB90'], 2), 'est', round(x['estEnd_B'], 1), round(x['estEnd_layerSplit'], 1))
# Lendeborg / Flemings 單列
for nm in ('Yaxel Lendeborg', 'Kingston Flemings'):
    r = next(r for r in C if r['name'] == nm); print(nm, {k: r[k] for k in ('pick', 'games', 'MIN26', 'min6', 'pub_last', 'pub_ovr', 'ovr6', 'raw6', 'ovrnow', 'rawnow')})
# B 全體資料部分的分布
raw = [r['raw6'] - r['start'] for r in B]
print('B raw d6 quartiles', [round(S.quantiles(raw, n=4)[i], 1) for i in range(3)], 'max', round(max(raw), 1))
print('B ovr d6 quartiles', [round(S.quantiles([r['ovr6'] - r['start'] for r in B], n=4)[i], 1) for i in range(3)])
# 逐階段 ≥90 組（資料部分）：留下比例以斜率計
json.dump(out, open(H / 'C-tables.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
