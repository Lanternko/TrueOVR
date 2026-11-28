import csv, numpy as np
from pathlib import Path
R = Path(r'D:/Projects/CODING/basketball-autochess/reports')
def rd(p): return list(csv.DictReader(open(R/p, encoding='utf-8-sig')))
new = rd('card-0.2.13/ranking.csv'); old = rd('card-0.2.12c/ranking.csv')
k2 = {r['name']: (float(r['overall2k']), int(float(r['rank2k']))) for r in rd('ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
k2s = sorted(k2.items(), key=lambda kv: -kv[1][0]); k2rank = {n:i+1 for i,(n,_) in enumerate(k2s)}
rap = [r for r in rd('impact-rapm/rapm.csv') if float(r['pooledPoss'])>=5000]
rap.sort(key=lambda r:-float(r['pooledNet'])); rr = {r['name']:i+1 for i,r in enumerate(rap)}
o = {r['name']:int(r['rank']) for r in old}
pn = {r['name']:float(r['pnr']) for r in rd('card-0.2.13/pnr-attr.csv')}
pp = {r['name']:float(r['poss']) for r in rd('card-0.2.13/pnr-attr.csv')}
print('2K n', len(k2), 'RAPM n', len(rap))
big = [r for r in new if r['pos'] in ('C','PF')][:10]
print('| rank13 | rank12c | name | pos | ovr | 2K27 rank(full)/ovr | RAPM rank | pnr | poss_eff |')
for r in big:
    n=r['name']; print(f"| {r['rank']} | {o[n]} | {n} | {r['pos']} | {r['ovr']} | {k2rank.get(n,'-')}/{k2.get(n,('-',))[0]} | {rr.get(n,'-')} | {pn[n]:.0f} | {pp[n]:.0f} |")
# side-effect people: rank drop 0.2.12c->0.2.13 
new_r = {r['name']:int(r['rank']) for r in new}; ovn={r['name']:float(r['ovr']) for r in new}; ovo={r['name']:float(r['ovr']) for r in old}
dr = sorted(new_r, key=lambda n: new_r[n]-o[n], reverse=True)[:8]
print('biggest drops (rank old->new, ovr, pnr, poss, 2K rank, RAPM rank)')
for n in dr: print(f"  {n:26s} {o[n]:3d}->{new_r[n]:3d} ovr {ovo[n]:.1f}->{ovn[n]:.1f} pnr {pn[n]:.0f} poss {pp[n]:.0f} 2K {k2rank.get(n,'-')} RAPM {rr.get(n,'-')} MIN {next(r['MIN'] for r in new if r['name']==n)}")
up = sorted(new_r, key=lambda n: new_r[n]-o[n])[:6]
print('biggest rises'); 
for n in up: print(f"  {n:26s} {o[n]:3d}->{new_r[n]:3d} ovr {ovo[n]:.1f}->{ovn[n]:.1f} pnr {pn[n]:.0f} poss {pp[n]:.0f} 2K {k2rank.get(n,'-')} RAPM {rr.get(n,'-')}")
# 全體：rank change vs 2K27 / RAPM ρ（參考）
def sp(a,b): return float(np.corrcoef(np.argsort(np.argsort(a)),np.argsort(np.argsort(b)))[0,1])
nm=[n for n in new_r if n in k2]; print('rho 2K  new', round(sp([ovn[n] for n in nm],[k2[n][0] for n in nm]),4),'old',round(sp([ovo[n] for n in nm],[k2[n][0] for n in nm]),4), len(nm))
nm=[n for n in new_r if n in rr]; print('rho RAPM(in-sample-ish) new', round(sp([ovn[n] for n in nm],[-rr[n] for n in nm]),4),'old',round(sp([ovo[n] for n in nm],[-rr[n] for n in nm]),4), len(nm))
# pnr vs ovr change correlation
d=[ovn[n]-ovo[n] for n in new_r]; print('corr(dOVR,pnr)', round(float(np.corrcoef(d,[pn[n] for n in new_r])[0,1]),3))
# 7 tiny-poss
print('--- top-150 (either) movers')
mv = sorted([n for n in new_r if (new_r[n]<=150 or o[n]<=150)], key=lambda n: -abs(new_r[n]-o[n]))[:10]
for n in mv: print(f"  {n:26s} {o[n]:3d}->{new_r[n]:3d} ovr {ovo[n]:.1f}->{ovn[n]:.1f} pnr {pn[n]:.0f} poss {pp[n]:.0f} 2K {k2rank.get(n,'-')} RAPM {rr.get(n,'-')}")
print('--- top-100 drops')
for n in sorted([n for n in new_r if o[n]<=100], key=lambda n: new_r[n]-o[n], reverse=True)[:5]: print(f"  {n:26s} {o[n]:3d}->{new_r[n]:3d} ovr {ovo[n]:.1f}->{ovn[n]:.1f} pnr {pn[n]:.0f} poss {pp[n]:.0f} 2K {k2rank.get(n,'-')} RAPM {rr.get(n,'-')}")
tiny=[n for n in pn if 0<pp[n]<0.01]; print('tiny-poss names', tiny, [(round(pn[n],1), o[n], new_r[n]) for n in tiny])
