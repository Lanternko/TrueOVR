import csv,json,random,sys
from collections import defaultdict,Counter
V='reports/player-impact-v41/2025-26-player-validation.csv'
rows=list(csv.DictReader(open(V,encoding='utf-8-sig')))
def agg(files):
    st=defaultdict(Counter);n=len(files)
    for f in files:
        r=json.load(open(f,encoding='utf-8'))
        for t in r['teams']:
            for p in t['players']:
                for k,v in p['stats'].items():
                    if isinstance(v,(int,float)):st[p['playerId']][k]+=v/n
    return st
def pred36(st,r):
    s=st[int(r['playerId'])];m=s['seconds']/60
    return s['tov']/m*36 if m>0 else None
if __name__=='__main__':
    off=agg([f'reports/handle-E069/sim/runs/off/off-{s}.json' for s in (20261012,20261013,20261014)])
    # check reproduction of csv
    bad=0
    for r in rows:
        if r['tov36_predicted']=='':continue
        p=pred36(off,r)
        if p is None or abs(p-float(r['tov36_predicted']))>1e-6:bad+=1
    print('off-run reproduces csv tov36_predicted mismatches:',bad,'of',len(rows))
    on=agg([f'reports/handle-E069/sim/runs/cal2-{s}.json' for s in (20261012,20261013,20261014)])
    import numpy as np
    def run(cohort,label):
        idx=[r for r in cohort if r['tov36_predicted']!='']
        act=np.array([float(r['tov36_actual']) for r in idx]);o=np.array([float(r['tov36_predicted']) for r in idx]);nn=np.array([pred36(on,r) for r in idx])
        d=np.abs(nn-act)-np.abs(o-act);rng=np.random.default_rng(1);N=len(d)
        bs=np.array([d[rng.integers(0,N,N)].mean() for _ in range(2000)])
        lo,hi=np.percentile(bs,[5,95])
        res={'label':label,'n':N,'maeCurrent':float(np.abs(o-act).mean()),'maeNew':float(np.abs(nn-act).mean()),'diff':float(d.mean()),'ci90':[float(lo),float(hi)],'upperBelow0':bool(hi<0)}
        dep=np.array([float(r['creationDependence_sourceRole']) for r in idx]);q=np.quantile(dep,[1/3,2/3]);g=np.digitize(dep,q)
        res['tertileCuts']=q.tolist();res['groups']=[]
        for k,nm in enumerate(['low','mid','high']):
            m=g==k;res['groups'].append({'group':nm,'n':int(m.sum()),'meanErrCurrent':float((o-act)[m].mean()),'meanErrNew':float((nn-act)[m].mean()),'maeCurrent':float(np.abs(o-act)[m].mean()),'maeNew':float(np.abs(nn-act)[m].mean())})
        return res
    out={'primary':run([r for r in rows if r['tov36_primary']=='True'],'primary (min>=500)'),'all':run(rows,'all 582')}
    A=sum(float(r['tovTotal_actual']) for r in rows);Po=sum(float(r['tovTotal_predicted']) for r in rows);Pn=sum(on[int(r['playerId'])]['tov'] for r in rows)
    out['league']={'actualPlayerTovSum':A,'currentSimTov':Po,'newSimTov':Pn,'errCurrent':Po/A-1,'errNew':Pn/A-1}
    n=3;out['components']={'ctl':sum(s['e069Ctl'] for s in on.values()),'pass':sum(s['e069Pass'] for s in on.values()),'other':sum(s['e069Other'] for s in on.values()),'actual':{'ctl':13686,'pass':16910,'other':5009}}
    json.dump(out,open('reports/handle-E069/sim/m2.json','w'),indent=1)
    print(json.dumps(out,indent=1))
