import csv, sys, numpy as np
from scipy.stats import rankdata, spearmanr
sys.stdout.reconfigure(encoding='utf-8')
L=lambda p:list(csv.DictReader(open(p,encoding='utf-8')))
c={x['name']:x for x in L('reports/card-0.2.10/ranking.csv') if float(x['MIN'])>=900}
rp={x['playerId']:x for x in L('reports/impact-rapm/rapm-prior.csv')}
A={x['playerId']:x for x in L('reports/card-0.2.3+E081-age-residual/rapm1-A.csv')}
B={x['playerId']:x for x in L('reports/card-0.2.3+E081-age-residual/rapm1-B.csv')}
ins={x['name']:x['playerId'] for x in L('reports/ovr-inseason-2026-27/live/2026-10-31/ranking.csv')}
rows=[]
for n,x in c.items():
    pid=ins.get(n)
    if pid in rp and pid in A and pid in B:
        rows.append((n,float(x['ovr']),float(rp[pid]['pooledNet']),float(rp[pid]['lastSeasonNet']),float(A[pid]['net']),float(B[pid]['net']),float(A[pid]['poss']),float(B[pid]['poss'])))
n=np.array([r[0] for r in rows]); ovr,pool,last,a,b,pa,pb=[np.array([r[i] for r in rows]) for i in range(1,8)]
print('N',len(n))
j=list(n).index('Jalen Williams')
for lab,v in [('pooled4',pool),('last',last),('A',a),('B',b)]:
    rk=rankdata(-v); print(lab,'JW rank',int(rk[j]),'rho(card)=%.3f'%spearmanr(ovr,v)[0])
print('card rank',int(rankdata(-ovr)[j]),'ovr',ovr[j])
print('split-half rho A vs B %.3f'%spearmanr(a,b)[0])
# noise: SE of a half estimate ~ sd(A-B)/sqrt2 scaled by poss; per-poss model: var ~ k/poss
d=a-b; k=np.median(d**2/(1/pa+1/pb)); print('k',k)
se_last=np.sqrt(k/(pa+pb)); print('JW single-season SE %.2f (poss %.0f)'%(se_last[j],pa[j]+pb[j]))
# expected RAPM from card: linear fit last ~ ovr
for lab,v in [('last',last),('pooled4',pool)]:
    X=np.c_[np.ones_like(ovr),ovr]; beta=np.linalg.lstsq(X,v,rcond=None)[0]; res=v-X@beta
    print(lab,'JW expected %.2f actual %.2f resid %.2f ; resid sd all %.2f ; JW resid pct %.0f%%'%(X[j]@beta,v[j],res[j],res.std(),100*(res<res[j]).mean()))
# what fraction of total residual variance (last) is measurement noise?
X=np.c_[np.ones_like(ovr),ovr]; beta=np.linalg.lstsq(X,last,rcond=None)[0]; res=last-X@beta
se_all=np.sqrt(k/(pa+pb)); print('mean noise var %.2f vs resid var %.2f'%((se_all**2).mean(),res.var()))
print('JW z vs noise only: %.2f ; vs total resid: %.2f'%(res[j]/se_all[j],res[j]/res.std()))
# top-15 card players residuals
o=np.argsort(-ovr)[:20]
for i in o: print('%-26s card%3d last%4d resid %+.2f z_noise %+.2f'%(n[i],rankdata(-ovr)[i],rankdata(-last)[i],res[i],res[i]/se_all[i]))
