import csv, numpy as np
from pathlib import Path
L = Path(r'D:/Projects/CODING/basketball-autochess/reports/ovr-inseason-2026-27/live/_check0213')
def ld(d): return {int(r['playerId']): r for r in csv.DictReader(open(L/d/'ranking.csv', encoding='utf-8'))}
o, n = ld('c0'), ld('new')
print('n', len(o), len(n), 'common', len(set(o)&set(n)))
# 自己重新排名（ovr 降冪；同 ovr 用原 rank）
def rk(X): s = sorted(X, key=lambda p: (-float(X[p]['ovr']), int(X[p]['rank']))); return {p:i+1 for i,p in enumerate(s)}
ro, rn = rk(o), rk(n)
print('csv rank == re-rank?', all(ro[p]==int(o[p]['rank']) for p in o), all(rn[p]==int(n[p]['rank']) for p in n))
cm = [p for p in o if p in n]
print('top20 in', [n[p]['name'] for p in cm if rn[p]<=20 and ro[p]>20], 'out', [n[p]['name'] for p in cm if ro[p]<=20 and rn[p]>20])
mv = [(n[p]['name'], ro[p], rn[p]) for p in cm if ro[p]<=100 and abs(ro[p]-rn[p])>=10]
mv2 = [(n[p]['name'], ro[p], rn[p]) for p in cm if (ro[p]<=100 or rn[p]<=100) and abs(ro[p]-rn[p])>=10]
print('top100(old) move>=10', len(mv), mv); print('either-in-100 move>=10', len(mv2), mv2)
d = np.array([float(n[p]['ovr'])-float(o[p]['ovr']) for p in cm]); print('dOVR max|', np.abs(d).max(), 'mean|', np.abs(d).mean())
big = sorted(cm, key=lambda p: -abs(rn[p]-ro[p]))[:15]
for p in big: print(f"  {n[p]['name']:26s} {ro[p]:4d}->{rn[p]:4d} ovr {float(o[p]['ovr']):5.1f}->{float(n[p]['ovr']):5.1f} pnr {n[p]['pnr']} pos {n[p]['pos']} MIN {n[p]['MIN26']}")
