"""E-141 複算：只讀 rookie-players.csv，重算 J、偏差、s*、檢定與判定，並與 results.json 比對。獨立於 analysis.py（不 import）。"""
import csv, json, sys
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
H = Path(__file__).resolve().parent
rows = list(csv.DictReader(open(H / 'rookie-players.csv', encoding='utf-8')))
cs = ['B0r', 'S25', 'S0', 'S+25']
sh = dict(zip(cs, [-5, -2.5, 0, 2.5]))


def e(r, c):
    return [float(r[f'err{n}_{c}']) for n in (0, 5, 10)]


def pj(r, c):
    return float(np.mean(np.abs(e(r, c))))


def S(seasons):
    return [r for r in rows if r['season'] in seasons]


def Jm(rs, c):
    return float(np.mean([pj(r, c) for r in rs]))


def Bm(rs, c):
    return float(np.mean([x for r in rs for x in e(r, c)]))


tr, te = S(['Y2', 'Y3', 'Y5', 'Y6']), S(['D1', 'D2'])
jt = {c: Jm(tr, c) for c in cs[:3]}
m = min(jt.values())
star = min([c for c in cs[:3] if jt[c] - m < 0.05], key=lambda c: sh[c])
out = {'trainN': len(tr), 'testN': len(te), 'trainJ': jt, 'sStar': star}
if star != 'B0r':
    d = np.array([pj(r, star) - pj(r, 'B0r') for r in te])
    bs = d[np.random.default_rng(1).integers(0, len(d), size=(2000, len(d)))].mean(axis=1)
    lo, hi = np.percentile(bs, [5, 95])
    p1 = [r for r in te if int(r['pick']) <= 10]
    g = [r for r in te if int(r['pick']) >= 31]
    c1, c2, c3 = bool(hi < 0), Jm(p1, star) <= Jm(p1, 'B0r'), (Bm(g, star) - Bm(g, 'B0r')) <= 3
    out.update(diff=float(d.mean()), ci90=[float(lo), float(hi)], c1=c1, c2=c2, c3=c3,
               verdict='採用候選' if (c1 and c2 and c3) else '維持 −5')
else:
    out['verdict'] = '維持 −5'
out['testJ'] = {c: Jm(te, c) for c in cs}
out['testBiasAll'] = {c: Bm(te, c) for c in cs}
print(json.dumps(out, ensure_ascii=False, indent=1))
R = json.load(open(H / 'results.json', encoding='utf-8'))
ok = (R['sStar'] == out['sStar'] and R['verdict'] == out['verdict'] and R['trainN'] == out['trainN'] and R['testN'] == out['testN']
      and all(abs(R['trainJ'][c] - out['trainJ'][c]) < 1e-9 for c in jt) and all(abs(R['testJ'][c] - out['testJ'][c]) < 1e-9 for c in cs)
      and all(abs(R['testBias']['all'][c] - out['testBiasAll'][c]) < 1e-9 for c in cs))
if star != 'B0r':
    ok = ok and abs(R['testDiff']['J(s*)-J(B0r)'] - out['diff']) < 1e-9 and all(abs(a - b) < 1e-9 for a, b in zip(R['testDiff']['ci90'], out['ci90']))
    ok = ok and [R['checks']['1_upperBound<0'], R['checks']['2_pick1-10_J_not_worse'], R['checks']['3_biasDiff31+<=3']] == [out['c1'], out['c2'], out['c3']]
print('與 results.json 一致:', ok)
sys.exit(0 if ok else 1)
