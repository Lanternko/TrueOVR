# E-117 T1-T3: round robin fatigue on vs off. Usage (repo root): python -X utf8 reports/sim-0.1.0+E117-fatigue-off/analyze_rr_e117.py
import json,hashlib,numpy as np
D='reports/sim-0.1.0+E117-fatigue-off/'
ids=[t['id'] for t in json.load(open(D+'team-ids.json',encoding='utf-8'))]
la=json.load(open(D+'league-actuals.json',encoding='utf-8'))
advp='data/defense-source/advanced-teams.json'
rs=json.load(open(advp,encoding='utf-8'))['data']['resultSets'][0]
ix={h:i for i,h in enumerate(rs['headers'])};R=rs['rowSet']
col=lambda k:{str(r[ix['TEAM_ID']]):float(r[ix[k]]) for r in R}
pace,net,wp=col('PACE'),col('NET_RATING'),col('W_PCT')
assert all(abs(net[k]-la['netRating'][k])<1e-9 for k in net)
actP=np.array([net[str(i)]*pace[str(i)]/100 for i in ids]);act1=np.array([net[str(i)] for i in ids]);actW=np.array([wp[str(i)] for i in ids])
def load(m):
    rec=[]
    for l in open(D+f'rr-{m}.jsonl',encoding='utf-8'):rec+=json.loads(l)['records']
    return rec
recs={m:load(m) for m in('on','off')}
seeds=sorted({r['seed'] for r in recs['on']});assert seeds==sorted({r['seed'] for r in recs['off']}) and len(seeds)==8
def stats(rec):
    M=np.zeros((8,30));N=np.zeros((8,30));W=np.zeros((8,30))
    for r in rec:
        s=seeds.index(r['seed']);d=r['ptsA']-r['ptsB'];w=1.0 if d>0 else 0.0 if d<0 else .5
        M[s,r['a']]+=d;N[s,r['a']]+=1;M[s,r['b']]-=d;N[s,r['b']]+=1;W[s,r['a']]+=w;W[s,r['b']]+=1-w
    return M/N,W/N
S={m:stats(recs[m]) for m in recs}
def err(P,act,ti,si):
    p=P[np.ix_(si,ti)].mean(0);e=p-act[ti];return float(np.abs(e).mean()),float(np.sqrt((e**2).mean()))
all30,all8=np.arange(30),np.arange(8)
rng=np.random.default_rng(117);draws=[(rng.integers(0,30,30),rng.integers(0,8,8)) for _ in range(400)]
out={'seeds':seeds,'bootN':400,'rngSeed':117,'resample':'30 teams x 8 seeds jointly; same indices for on and off; diff = off - on; 90% = 5th..95th pct',
     'sources':{'advanced-teams':advp,'sha256':hashlib.sha256(open(advp,'rb').read()).hexdigest(),'T1 primary actual':'NET_RATING*PACE/100','T2 actual':'W_PCT'}}
def block(key,mi,act):
    r={}
    for m in('on','off'):
        mae,rmse=err(S[m][mi],act,all30,all8);P=S[m][mi].mean(0)
        r[m]={'mae':mae,'rmse':rmse,'corr':float(np.corrcoef(P,act)[0,1]),'simSd':float(P.std()),'simMean':float(P.mean()),'perTeam':[float(v) for v in P]}
    for k,j in(('mae',0),('rmse',1)):
        d=np.array([err(S['off'][mi],act,ti,si)[j]-err(S['on'][mi],act,ti,si)[j] for ti,si in draws])
        r['diff_'+k]={'offMinusOn':r['off'][k]-r['on'][k],'ci90':[float(np.percentile(d,5)),float(np.percentile(d,95))]}
    r['actual']=[float(v) for v in act];out[key]=r
block('T1_pace',0,actP);block('T1_x1',0,act1);block('T2_winrate',1,actW)
out['T1_primary']='T1_pace'
t3={}
for m in('on','off'):
    rec=recs[m];n=len(rec);pts=sum(r['ptsA']+r['ptsB'] for r in rec);poss=sum(r['possA']+r['possB'] for r in rec)
    t3[m]={'games':n,'ptsPerTeamGame':pts/(2*n),'possPerTeamGame':poss/(2*n),'ptsPerPossession':pts/poss,'possessionDefinition':'count of POSSESSION events per side from eventObserver'}
t3['actual']={'ptsPerTeamGame':la['ptsPerTeamGame'],'pace(mean PACE)':float(np.mean([pace[str(i)] for i in ids]))}
out['T3']=t3
json.dump(out,open(D+'team.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
f=lambda k:{m:{a:round(v,4) for a,v in out[k][m].items() if a in('mae','rmse','corr','simSd')} for m in('on','off')}
for k in('T1_pace','T1_x1','T2_winrate'):print(k,f(k),out[k]['diff_mae'],out[k]['diff_rmse'])
print(json.dumps(t3,indent=1))
