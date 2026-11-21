"""F-129 D1 check: real total-FTA spread under two bases: stint-level FTA (D0, as in ridge_k.py) vs foul-time attribution (pbp, same basis as sim). cwd = repo root."""
import sys, json; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from f129lib import *
x = players(); RD = json.load(open('reports/F129-center-ft-defense-diag/real_d1_rows.json', encoding='utf-8')); RR = [RD['0'], RD['1']]
LD = 'reports/F129-center-ft-defense-diag/ledgers/'
sim = {c: [sim_load(LD + f'v-{c}-{s}.json') for s in (20261103, 20261104)] for c in 'ab'}
pres = [set(i for r in rr for i in r['o'] + r['d']) for rr in RR + sim['a'] + sim['b']]
P = [i for i in x if x[i]['min'] >= 1000 and all(i in p for p in pres)]
def spread(rowsets, key):
    D = [Design(r) for r in rowsets]; F = Design(rowsets[0] + rowsets[1]); out = {}
    cs = [dict(zip(d.ids, d.fit(np.array([r[key] for r in d.rows], float))[0])) for d in D]; cf = dict(zip(F.ids, F.fit(np.array([r[key] for r in F.rows], float))[0]))
    for g, pos in GRP:
        J = [i for i in P if x[i]['pos'] in pos]; t, r = tsd(np.array([cf[i] for i in J]), np.array([cs[0].get(i, 0) for i in J]), np.array([cs[1].get(i, 0) for i in J])); out[g] = (round(float(t), 3), round(float(r), 3))
    return out
res = {'real_stintFTA': spread(RR, 'fta_stint'), 'real_foultimeFTA': spread(RR, 'fta'), 'sim_a': spread(sim['a'], 'fta'), 'sim_b': spread(sim['b'], 'fta')}
tot = {k: sum(r[k] for h in RR for r in h) for k in ('fta_stint', 'fta')}; res['real_totals'] = tot
for k, v in res.items(): print(k, v)
for c in ('a', 'b'):
    print('ratio sim_' + c + ' / real_stint', {g: round(res['sim_' + c][g][0] / res['real_stintFTA'][g][0], 3) for g, _ in GRP}, ' / real_foultime', {g: round(res['sim_' + c][g][0] / res['real_foultimeFTA'][g][0], 3) for g, _ in GRP})
json.dump(res, open('reports/F129-center-ft-defense-diag/d1_basis.json', 'w', encoding='utf-8'), indent=1)
