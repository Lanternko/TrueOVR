# E-185 0.2.10d：賽季中（2026-10-31 資料）四個輸出互比，拆「底（0.2.10a→0.2.10c）」與「窗口」
import csv, json
R = 'D:/Projects/CODING/basketball-autochess/reports/'
LV = R + 'ovr-inseason-2026-27/live/'
def L(p):
    return {x['playerId']: x for x in csv.DictReader(open(p, encoding='utf-8'))}
S = {'0.2.12': L(LV + '2026-10-31/ranking.csv'),
     '0.2.10a關窗': L(R + 'card-0.2.12/work/inseason-0210a-nowin-1031/ranking.csv'),
     '0.2.10c關窗': L(LV + '_base10c_nowin/ranking.csv'),
     '0.2.10d': L(LV + '_win10d/ranking.csv')}
def cmp(a, b, col='ovr'):
    X, Y = S[a], S[b]
    ids = [i for i in X if i in Y]
    rx = {i: int(X[i]['rank']) for i in ids}; ry = {i: int(Y[i]['rank']) for i in ids}
    d = {i: float(Y[i][col]) - float(X[i][col]) for i in ids}
    top = lambda r, n: {i for i in ids if r[i] <= n}
    o = {'pair': f'{a}->{b}', 'n': len(ids), 'changed': sum(1 for v in d.values() if abs(v) > 1e-9),
         'meanDiff': round(sum(d.values()) / len(ids), 3), 'maxAbs': round(max(abs(v) for v in d.values()), 2),
         'top20_out': len(top(rx, 20) - top(ry, 20)), 'top100_out': len(top(rx, 100) - top(ry, 100)),
         'top100_moved10': sum(1 for i in ids if rx[i] <= 100 and abs(rx[i] - ry[i]) >= 10)}
    mv = sorted(ids, key=lambda i: -abs(d[i]))[:8]
    o['movers'] = [(X[i]['name'], X[i]['team'], rx[i], ry[i], round(d[i], 1)) for i in mv]
    return o
out = [cmp('0.2.12', '0.2.10d'), cmp('0.2.10a關窗', '0.2.10c關窗'), cmp('0.2.10c關窗', '0.2.10d'), cmp('0.2.10a關窗', '0.2.12')]
for o in out: print(json.dumps(o, ensure_ascii=False))
names = ['Tyus Jones', 'Jalen Williams', 'Nikola Jokić', 'Victor Wembanyama', 'Shai Gilgeous-Alexander', 'Anthony Edwards', 'Franz Wagner', 'Alperen Sengun']
print('key (rank/ovr):')
for n in names:
    row = []
    for k, X in S.items():
        r = [x for x in X.values() if x['name'] == n]
        row.append(f"{k}:{r[0]['rank']}/{r[0]['ovr']}" if r else f'{k}:-')
    print(n, ' | '.join(row))
for k, X in S.items():
    t = sorted(X.values(), key=lambda x: int(x['rank']))[:20]
    print(k, 'top20:', ', '.join(f"{x['name']}" for x in t))
json.dump(out, open('cmp_inseason.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
