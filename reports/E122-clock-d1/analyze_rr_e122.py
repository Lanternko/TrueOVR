# E-122 c2 (amendment A1). Usage (repo root): python -X utf8 reports/E122-clock-d1/analyze_rr_e122.py
import json,hashlib,numpy as np
D='reports/E122-clock-d1/'
ids=[t['id'] for t in json.load(open(D+'team-ids.json',encoding='utf-8'))]
la=json.load(open(D+'league-actuals.json',encoding='utf-8'))
advp='data/defense-source/advanced-teams.json'
rs=json.load(open(advp,encoding='utf-8'))['data']['resultSets'][0]
ix={h:i for i,h in enumerate(rs['headers'])};R=rs['rowSet']
col=lambda k:{str(r[ix['TEAM_ID']]):float(r[ix[k]]) for r in R}
pace,net=col('PACE'),col('NET_RATING')
assert all(abs(net[k]-la['netRating'][k])<1e-9 for k in net)
act=np.array([net[str(i)]*pace[str(i)]/100 for i in ids])   # T1_pace actual
sb=json.load(open(D+'starters-beta.json'));b5=np.array([t['sum5'] for t in sb])
def load(f):
    rec=[]
    for l in open(D+f,encoding='utf-8'):rec+=json.loads(l)['records']
    return rec
def mat(rec,seeds):
    M=np.zeros((len(seeds),30));N=np.zeros((len(seeds),30))
    for r in rec:
        s=seeds.index(r['seed']);d=r['ptsA']-r['ptsB']
        M[s,r['a']]+=d;N[s,r['a']]+=1;M[s,r['b']]-=d;N[s,r['b']]+=1
    return M/N
S1=list(range(20261028,20261060));S2=list(range(20261060,20261092))
ron,roff,roff2=load('rr-on.jsonl'),load('rr-off.jsonl'),load('rr-off2.jsonl')
for rec,S in((ron,S1),(roff,S1),(roff2,S2)):assert sorted({r['seed'] for r in rec})==S and len(rec)==len(S)*435
on,off,off2=mat(ron,S1),mat(roff,S1),mat(roff2,S2)
# bit-identity of new-code off vs E-120 rr-off on its 8 seeds
e120=load('rr-off-e120.jsonl');k=lambda r:(r['seed'],r['a'],r['b'])
d_off={k(r):r for r in roff};ident=all(d_off[k(r)]==r for r in e120);
mae=lambda P,ti=slice(None):float(np.abs(P.mean(0)[ti]-act[ti]).mean())
rmse=lambda P:float(np.sqrt(((P.mean(0)-act)**2).mean()))
m_on,m_off,m_off2=mae(on),mae(off),mae(off2)
Nn=abs(m_off2-m_off);delta=m_on-m_off
rng=np.random.default_rng(122);dr=[]
for _ in range(1000):
    ti=rng.integers(0,30,30);si=rng.integers(0,32,32)
    e=lambda P:float(np.abs(P[np.ix_(si,ti)].mean(0)-act[ti]).mean())
    dr.append(e(on)-e(off))
ci=[float(np.percentile(dr,5)),float(np.percentile(dr,95))]
# 8-seed version (original spec seeds 20261028-35)
d8=mae(on[:8])-mae(off[:8])
# systematic/residual split: per-team change vs starters' D1 beta sum
ch=on.mean(0)-off.mean(0)
A=np.vstack([b5,np.ones(30)]).T;coef,*_=np.linalg.lstsq(A,ch,rcond=None);fit=A@coef;res=ch-fit
P0=off.mean(0)
reg={'slope':float(coef[0]),'intercept':float(coef[1]),'corr':float(np.corrcoef(b5,ch)[0,1]),'r2':float(1-res.var()/ch.var()),
 'maeOff':float(np.abs(P0-act).mean()),'maeOn':float(np.abs(P0+ch-act).mean()),
 'maeOff_plus_systematic':float(np.abs(P0+fit-act).mean()),'maeOff_plus_residual':float(np.abs(P0+res-act).mean()),
 'sdChange':float(ch.std()),'sdBeta5':float(b5.std()),'meanChange':float(ch.mean())}
out={'amendment':'A1','seedsOnOff':[S1[0],S1[-1]],'seedsNoise':[S2[0],S2[-1]],'offBitIdenticalToE120_on_8_seeds':bool(ident),
 'maeOn':m_on,'maeOff':m_off,'maeOff2':m_off2,'noiseN':Nn,'delta':delta,'threshold':0.1+Nn,'pass':bool(delta<=0.1+Nn),
 'delta_ci90_boot1000':ci,'delta_8seed':d8,'rmse':{'on':rmse(on),'off':rmse(off),'off2':rmse(off2)},'regression_change_vs_beta5':reg,
 'perTeam':{'off':[float(v) for v in P0],'on':[float(v) for v in on.mean(0)],'actual':[float(v) for v in act],'beta5':[float(v) for v in b5]},
 'sources':{'advanced-teams-sha256':hashlib.sha256(open(advp,'rb').read()).hexdigest()}}
json.dump(out,open(D+'team.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(json.dumps({k:v for k,v in out.items() if k!='perTeam'},indent=1))
