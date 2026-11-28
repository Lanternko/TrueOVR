"""u1 / c0a：attributes-P50.csv 除 pass 欄外和 attributes-P0.csv 逐位元（逐格字串）相同；attributes-P0.csv 對 E-101 attributes-e101.csv 逐位元相同。"""
import csv, hashlib, json
from pathlib import Path
D = Path(__file__).resolve().parent.parent
R = D.parent
def rd(p): return list(csv.reader(open(p, encoding='utf-8', newline='')))
a, b = rd(D / 'attributes-P0.csv'), rd(D / 'attributes-P50.csv')
assert a[0] == b[0] and len(a) == len(b)
diffcols = {}
for h_i, h in enumerate(a[0]):
    n = sum(1 for x, y in zip(a[1:], b[1:]) if x[h_i] != y[h_i])
    if n: diffcols[h] = n
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
e101 = R / 'card-0.2.5+E101-crossera/attributes-e101.csv'
res = {'c0a': {'P0_sha': sha(D / 'attributes-P0.csv'), 'e101_sha': sha(e101), 'pass': sha(D / 'attributes-P0.csv') == sha(e101)},
       'u1': {'rows': len(a) - 1, 'columns': a[0], 'differingColumns': diffcols, 'pass': list(diffcols) == ['pass']}}
(D / 'checks-attrs.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(res['c0a'], res['u1']['differingColumns'], res['u1']['pass'])
