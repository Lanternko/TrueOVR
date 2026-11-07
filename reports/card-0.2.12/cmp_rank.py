import csv, sys
a = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
b = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
A = {r['name']: r for r in a}; B = {r['name']: r for r in b}
print(len(A), len(B), set(A) == set(B))
cols = [c for c in a[0] if c in b[0]]
nd = {}
for c in cols:
    if c == 'name': continue
    n = 0; ok = 0; mx = 0
    for k in A:
        x, y = A[k][c], B[k][c]
        try: d = abs(float(x) - float(y)); mx = max(mx, d); ok += d <= 0.1; n += 1
        except Exception: n += 1; ok += x == y
    nd[c] = (round(mx, 4), round(ok / n, 4))
print({c: v for c, v in nd.items() if v[0] != 0 or v[1] != 1})
print('ovr', nd['ovr'])
