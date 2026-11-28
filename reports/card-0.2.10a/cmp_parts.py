import csv, sys
from pathlib import Path
H = Path(__file__).resolve().parent
tag = sys.argv[1]
for p in ('primary', 'fitA', 'fitB'):
    a = {r['name']: r for r in csv.DictReader(open(H.parent / 'card-0.2.9a/cards/K6' / p / 'pred.csv', encoding='utf-8'))}
    b = {r['name']: r for r in csv.DictReader(open(H / 'work' / tag / 'cards' / p / 'pred.csv', encoding='utf-8'))}
    print(p, len(a), len(b), list(a[next(iter(a))].keys())[:12])
    cols = [c for c in a[next(iter(a))] if c in b[next(iter(b))] and c not in ('name', 'playerId')]
    for c in cols:
        d = []
        for n in a:
            try: d.append(abs(float(a[n][c]) - float(b[n][c])))
            except Exception: pass
        if d: print('  ', c, 'max', round(max(d), 5), 'frac<=0.1', round(sum(x <= .1 for x in d) / len(d), 4))
