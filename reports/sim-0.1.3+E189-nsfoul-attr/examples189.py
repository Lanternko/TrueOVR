"""E-189 player examples for the report: non-shooting-foul rate per 100 defensive possessions, real (both halves pooled) vs sim base / E189 (avg of attr-odd & attr-even runs, 32 seeds). cwd = repo root."""
import sys, json, numpy as np; sys.path.insert(0, 'reports/F129-center-ft-defense-diag'); sys.argv = ['x']
exec(open('reports/sim-0.1.3+E189-nsfoul-attr/analyze189.py', encoding='utf-8').read().split('out = {}')[0])
from f129lib import players
x = players(); SR = {t: sim_rates(t) for t in ('base', 'odd', 'even')}
real = lambda i: 100 * sum(RH[str(i)]['ns']) / sum(RH[str(i)]['defposs'])
row = lambda i: {'name': x[i]['name'], 'pos': x[i]['pos'], 'min': x[i]['min'], 'real': real(i), 'base': SR['base'][0][i], 'e189': (SR['odd'][0][i] + SR['even'][0][i]) / 2}
ids = [int(i) for i in P150]; byname = {x[i]['name']: i for i in x}
ex = {n: row(byname[n]) for n in ('Jakob Poeltl', 'Daniel Gafford', 'Ace Bailey', 'Rudy Gobert', 'Bam Adebayo', 'Alex Caruso', 'Draymond Green') if n in byname and str(byname[n]) in RH}
grp = {}
for g, pos in (('C', ('C',)), ('nonC', ('PG', 'SG', 'SF', 'PF'))):
    rs = [row(i) for i in ids if x[i]['pos'] in pos]; grp[g] = {'n': len(rs), **{k: float(np.mean([r[k] for r in rs])) for k in ('real', 'base', 'e189')}}
    grp[g]['r_base'] = float(np.corrcoef([r['base'] for r in rs], [r['real'] for r in rs])[0, 1]); grp[g]['r_e189'] = float(np.corrcoef([r['e189'] for r in rs], [r['real'] for r in rs])[0, 1])
cs = sorted([row(i) for i in ids if x[i]['pos'] == 'C'], key=lambda r: -r['min'])[:10]
json.dump({'examples': ex, 'groups': grp, 'top10_centers_by_min': cs}, open(D + 'examples189.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n, r in ex.items(): print(f"{n:18s}{r['pos']:3s} real {r['real']:.2f} base {r['base']:.2f} e189 {r['e189']:.2f}")
print(grp)
for r in cs: print(f"  {r['name']:20s} real {r['real']:.2f} base {r['base']:.2f} e189 {r['e189']:.2f}")
