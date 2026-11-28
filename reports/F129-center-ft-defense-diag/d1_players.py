"""F-129 D1 player examples: the 19 centers, full-data defence coefficient of opponent FTA per 100 (total, own shooting fouls, teammates' shooting fouls, non-shooting-foul FTs): real vs sim (config a, all 16 seeds pooled). cwd = repo root."""
import sys, json; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from d1 import *
pres = [set(i for rr_ in RR[h] for i in rr_['o'] + rr_['d']) for h in (0, 1)] + [set(i for r in SIM['a'][s] for i in r['o'] + r['d']) for s in seeds]
P = [i for i in x if x[i]['min'] >= 1000 and x[i]['pos'] == 'C' and i in pres[0] and i in pres[1]]
rb = rbar_of([RR[0], RR[1]]); real = blocks(solve([Half(RR[0], rb), Half(RR[1], rb)]))
rs = rbar_of([SIM['a'][s] for s in seeds]); sim = blocks(solve([Half(SIM['a'][s], rs) for s in seeds]))
rows = []
for i in P:
    j = ix[i]; rows.append({'name': x[i]['name'], 'min': round(x[i]['min']), **{f'real_{b}': round(float(real[b][j]), 2) for b in ('tot', 'own', 'mate', 'nsf')}, **{f'sim_{b}': round(float(sim[b][j]), 2) if i in pres[2] else None for b in ('tot', 'own', 'mate', 'nsf')}})
rows.sort(key=lambda r: -r['real_tot'])
for r in rows: print(r)
json.dump(rows, open('reports/F129-center-ft-defense-diag/d1_players.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
