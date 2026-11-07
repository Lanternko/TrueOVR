import csv, numpy as np, hashlib
from pathlib import Path
R = Path(r'D:/Projects/CODING/basketball-autochess/reports')
def ld(p):
    rows = list(csv.DictReader(open(p, encoding='utf-8'))); return rows
def ovr(p): return {r['name']: (float(r['ovr']), int(r['rank'])) for r in ld(p)}
def cmp(a, b, label, ndisp=True):
    A, B = ovr(a), ovr(b); common = [n for n in A if n in B]
    d = np.array([A[n][0]-B[n][0] for n in common]); 
    print(f'{label}: n={len(common)} (A={len(A)},B={len(B)}) max|dOVR|={np.abs(d).max():.2f} mean|d|={np.abs(d).mean():.3f} rms={np.sqrt((d**2).mean()):.3f}')
    # re-rank on common by ovr desc
    def rk(X): 
        s = sorted(common, key=lambda n: -X[n][0]); return {n:i+1 for i,n in enumerate(s)}
    ra, rb = rk(A), rk(B)
    t20a = {n for n in common if ra[n]<=20}; t20b={n for n in common if rb[n]<=20}
    mv = [n for n in common if ra[n]<=100 and rb[n]<=100 and abs(ra[n]-rb[n])>=10]
    mv_any = [n for n in common if (ra[n]<=100 or rb[n]<=100) and abs(ra[n]-rb[n])>=10]
    print(f'   top20 in: {sorted(t20a-t20b)} out: {sorted(t20b-t20a)}; top100 move>=10: {len(mv_any)} (both-in-100: {len(mv)}) ', [(n,rb[n],ra[n]) for n in mv_any][:12])
cmp(R/'card-0.2.13/ranking.csv', R/'card-0.2.13-w246/ranking.csv', 'official 0.2.13 vs w246 fit 0.2.13')
cmp(R/'card-0.2.12c/ranking.csv', R/'card-0.2.12c-w246/ranking.csv', 'official 0.2.12c vs w246 fit 0.2.12c')
cmp(R/'card-0.2.13/ranking.csv', R/'card-0.2.12c/ranking.csv', 'R-109: card 0.2.12c -> 0.2.13')
L = R/'ovr-inseason-2026-27/live/_check0213'
for d in ('ref','c0','c0b','new'): print(d, [p.name for p in (L/d).glob('*')][:15])
