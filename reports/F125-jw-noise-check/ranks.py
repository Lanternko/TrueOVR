import csv, sys, numpy as np
from scipy.stats import rankdata
sys.stdout.reconfigure(encoding='utf-8')
L=lambda p:list(csv.DictReader(open(p,encoding='utf-8')))
idx=lambda rows,key,col:{x[key]:x[col] for x in rows}
c=[x for x in L('reports/card-0.2.10/ranking.csv') if float(x['MIN'])>=900]
src={'dpm':idx(L('data/external-impact/darko/darko_2025-26.csv'),'name','dpm'),
 'bpm':idx(L('data/external-impact/bpm/bpm_2025-26.csv'),'name','bpm'),
 'epm':idx(L('data/external-impact/epm_self/epm_2025-26.csv'),'name','net'),
 'rapm4':idx(L('reports/card-0.2.10/rapm-T6.csv'),'name','pooledNet'),
 '2k26':idx(L('data/external-impact/2k/2k26-launch.csv'),'name','ovr')}
names=[x['name'] for x in c]
V={'ovr':np.array([float(x['ovr']) for x in c])}
for k,dct in src.items():
    V[k]=np.array([float(dct[n]) if dct.get(n) not in (None,'') else np.nan for n in names])
z=lambda a:(a-np.nanmean(a))/np.nanstd(a)
V['T6']=(z(V['dpm'])+z(V['bpm']))/2
R={}
for k,a in V.items():
    rr=np.full(len(a),np.nan); ok=~np.isnan(a); rr[ok]=rankdata(-a[ok]); R[k]=rr
print('N',len(c)); keys=['ovr','T6','dpm','bpm','epm','rapm4','2k26']
print('%-26s %4s '%('name','pos')+' '.join('%6s'%k for k in keys))
order=np.argsort(R['ovr'])
for i in order[:25]:
    print('%-26s %4s '%(names[i],c[i]['pos'])+' '.join('%6.0f'%R[k][i] for k in keys))
ok=~np.isnan(V['T6'])
o=V['ovr'][ok]; t=V['T6'][ok]; nm=np.array(names)[ok]
X=np.c_[np.ones_like(o),o]; beta=np.linalg.lstsq(t[:,None]*0+X,t,rcond=None)[0]
res=t-X@beta; j=list(nm).index('Jalen Williams')
print('T6 resid JW %.2f sd %.2f pct %.1f%% ; z %.2f'%(res[j],res.std(),100*(res<res[j]).mean(),res[j]/res.std()))
top=np.argsort(-o)[:40]; rr=res[top]; print('among card top40 JW resid rank (most negative=1):',int((rr<res[j]).sum())+1)
