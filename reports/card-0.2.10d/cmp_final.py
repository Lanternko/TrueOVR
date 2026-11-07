"""card 0.2.10d vs 0.2.10c 對照（G3 同底）。名次＝MIN>=500 內依 ovr 排（同 cmp_ver.py）。用法：python cmp_final.py（從專案根跑）。"""
import csv, json, numpy as np
ld = lambda p: list(csv.DictReader(open(p, encoding='utf-8')))
A = ld('reports/card-0.2.10c/ranking.csv'); B = ld('reports/card-0.2.10d/ranking.csv')
def rk(rows):
    el = sorted([r for r in rows if float(r['MIN']) >= 500], key=lambda r: -float(r['ovr']))
    return {r['name']: i + 1 for i, r in enumerate(el)}
ra, rb = rk(A), rk(B); a = {r['name']: r for r in A}; b = {r['name']: r for r in B}
com = [n for n in ra if n in rb]
x = np.array([ra[n] for n in com]); y = np.array([rb[n] for n in com])
out = {'n_ranked': len(com), 'spearman': float(np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1])}
t = lambda R, k: {n for n, r in R.items() if r <= k}
out['top20_in'] = sorted(t(rb, 20) - t(ra, 20)); out['top20_out'] = sorted(t(ra, 20) - t(rb, 20))
out['top100_moved10'] = sum(1 for n in com if ra[n] <= 100 and abs(ra[n] - rb[n]) >= 10)
out['top100_in_out'] = [len(t(rb, 100) - t(ra, 100)), len(t(ra, 100) - t(rb, 100))]
out['top300_moved10'] = sum(1 for n in com if ra[n] <= 300 and abs(ra[n] - rb[n]) >= 10)
d = np.array([float(b[n]['ovr']) - float(a[n]['ovr']) for n in a if n in b])
out['ovr_diff'] = {'mean': float(d.mean()), 'sd': float(d.std()), 'p90abs': float(np.percentile(np.abs(d), 90)), 'max_abs': float(np.abs(d).max())}
out['top10_bigs'] = {k: [(n, rk_[n], float(R_[n]['ovr'])) for n in sorted([n for n in rk_ if R_[n]['pos'] in ('C', 'PF')], key=lambda n: rk_[n])[:10]]
                    for k, rk_, R_ in (('0.2.10c', ra, a), ('0.2.10d', rb, b))}
sd = {}
for c in ('long', 'creation', 'ovr'):
    va = np.array([float(a[n][c]) for n in com]); vb = np.array([float(b[n][c]) for n in com])
    sd[c] = {'sd_a': float(va.std()), 'sd_b': float(vb.std()), 'ratio': float(vb.std() / va.std()), 'corr': float(np.corrcoef(va, vb)[0, 1]),
             'mean_a': float(va.mean()), 'mean_b': float(vb.mean())}
tv = {r['name']: float(r['threeValue']) for r in ld('reports/card-0.2.10d/three-value.csv') if r.get('threeValue') not in (None, '')} if 'threeValue' in ld('reports/card-0.2.10d/three-value.csv')[0] else None
out['sd'] = sd
mv = {}
for c in ('long', 'creation'):
    dd = sorted(com, key=lambda n: -abs(float(b[n][c]) - float(a[n][c])))
    mv[c] = [(n, float(a[n][c]), float(b[n][c]), ra[n], rb[n]) for n in dd[:8]]
out['movers_attr'] = mv
out['key'] = {n: (ra.get(n), rb.get(n), float(a[n]['ovr']), float(b[n]['ovr'])) for n in ['Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić', 'Joel Embiid', 'Stephen Curry', 'Franz Wagner', 'Alperen Sengun'] if n in a and n in b}
mm = sorted(com, key=lambda n: -abs(ra[n] - rb[n]) if min(ra[n], rb[n]) <= 100 else 0)[:10]
out['top_movers_rank'] = [(n, ra[n], rb[n]) for n in mm]
print(json.dumps(out, ensure_ascii=False, indent=1))
