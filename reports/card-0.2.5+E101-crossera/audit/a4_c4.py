"""稽核 4：四個變體 15 項屬性 > 140、> 120 計數。"""
import csv, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parents[1]
A13 = ['long','mid','short','ft','drive','foulDraw','tovSkill','pass','rebound','physique','onBall','creation','pressure']
res = {}
for v in ('e101', 'e101z', 'e101g', 'e101w'):
    vals = []
    rows = list(csv.DictReader(open(OUT/f'attributes-{v}.csv', encoding='utf-8')))
    for r in rows:
        for a in A13: vals.append((float(r[a]), r['name'], a))
    for r in csv.DictReader(open(OUT/f'value-attrs-{v}.csv', encoding='utf-8')):
        vals.append((float(r['midAttr']), r['name'], 'midValue')); vals.append((float(r['shortAttr']), r['name'], 'shortValue'))
    res[v] = {'players': len(rows), 'cells': len(vals), 'max': max(vals)[0],
              '>140': [[n, a, round(x, 2)] for x, n, a in sorted(vals, reverse=True) if x > 140],
              '>120': [[n, a, round(x, 2)] for x, n, a in sorted(vals, reverse=True) if x > 120],
              'nan': sum(x != x for x, _, _ in vals)}
(Path(__file__).parent/'a4_c4.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, indent=1))
