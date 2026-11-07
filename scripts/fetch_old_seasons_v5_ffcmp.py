"""v5 Path A：比較兩份 four-factors csv（每欄 Pearson r、最大差、共同球員數）。
用法：python -I scripts/fetch_old_seasons_v5_ffcmp.py REF.csv CAND.csv [--min-poss N] --json OUT"""
import argparse, csv, json, math


def load(p):
    with open(p, encoding='utf-8') as fh:
        return {int(r['playerId']): r for r in csv.DictReader(fh)}


def corr(xs, ys):
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs)); sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sx / sy, 6) if sx and sy else None


ap = argparse.ArgumentParser()
ap.add_argument('ref'); ap.add_argument('cand'); ap.add_argument('--min-poss', type=float, default=0)
ap.add_argument('--json', required=True)
a = ap.parse_args()
R, C = load(a.ref), load(a.cand)
common = sorted(p for p in set(R) & set(C) if float(R[p]['defensePossessions']) >= a.min_poss)
cols = [k for k in next(iter(R.values())) if k not in ('playerId', 'name', 'season')]
out = {'ref': a.ref, 'cand': a.cand, 'minPoss': a.min_poss, 'refN': len(R), 'candN': len(C), 'common': len(common),
       'cols': {}}
for k in cols:
    xs = [float(R[p][k]) for p in common]; ys = [float(C[p][k]) for p in common]
    out['cols'][k] = {'r': corr(xs, ys), 'maxAbsDiff': round(max(abs(x - y) for x, y in zip(xs, ys)), 4)}
open(a.json, 'w', encoding='utf-8').write(json.dumps(out, indent=1) + '\n')
print(a.cand, 'common', len(common), {k: (v['r'], v['maxAbsDiff']) for k, v in out['cols'].items() if k.endswith('_defense') or k == 'defensePossessions'})
