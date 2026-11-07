"""card 0.2.10 vs 0.2.9a 驗證表（用法：cmp_ver.py <new ranking.csv>）。rk() 同 build_card_029a：MIN>=500 內依 ovr 排名。"""
import csv, sys, numpy as np
def ld(p): return list(csv.DictReader(open(p, encoding='utf-8')))
def rk(rows):
    el = sorted([r for r in rows if float(r['MIN']) >= 500], key=lambda r: -float(r['ovr']))
    return {r['name']: i + 1 for i, r in enumerate(el)}
a = ld('reports/card-0.2.9a/ranking.csv'); b = ld(sys.argv[1])
ra, rb = rk(a), rk(b)
oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
com = [n for n in ra if n in rb]
x = np.array([ra[n] for n in com]); y = np.array([rb[n] for n in com])
rho = np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1]
print('n', len(com), 'Spearman', round(rho, 4))
t20a = {n for n, r in ra.items() if r <= 20}; t20b = {n for n, r in rb.items() if r <= 20}
print('top20 進', [(n, ra[n], rb[n]) for n in t20b - t20a], '出', [(n, ra[n], rb[n]) for n in t20a - t20b])
mv = [n for n in com if ra[n] <= 100 and abs(ra[n] - rb[n]) >= 10]
print('top100 動>=10名', len(mv))
for n in ['Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić', 'Anthony Davis', 'Joel Embiid']:
    print(n, ra.get(n), '->', rb.get(n), oa.get(n), '->', ob.get(n))
d = np.array([ob[n] - oa[n] for n in oa if n in ob]); print('ovr diff mean', d.mean().round(3), 'sd', d.std().round(3), 'p90|d|', np.percentile(np.abs(d), 90).round(2))
print('top20 new', [(n, r) for n, r in sorted(rb.items(), key=lambda t: t[1])[:20]])
