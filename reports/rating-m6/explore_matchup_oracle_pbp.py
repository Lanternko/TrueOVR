# 上限測試二（2025-26 A 半）：用 PBP 逐球時間。每個得分／失誤事件，只分給「當下在場」的 5 名防守者：
#   平均分（不知道誰守誰）vs 完美權重（真實對位回合佔比，只在當下在場的人之間重分配＝機器學習天花板）
import sys, json, collections, glob; sys.path.insert(0,'scripts'); sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, rating_m2
C=json.load(open('reports/rating-m6/params.json',encoding='utf-8'))['prod']['C']['c']
R=rating_m2.Rater('2025-26'); W=R.w['per36']
rs=json.load(open('data/season-source/player-games.json',encoding='utf-8'))['data']['resultSets'][0]; h={k:i for i,k in enumerate(rs['headers'])}
mins={(r[h['GAME_ID']],r[h['PLAYER_ID']]):(r[h['MIN']] or 0) for r in rs['rowSet']}
stints=collections.defaultdict(list)
for l in open('reports/defense-b1/stints.jsonl',encoding='utf-8'):
    s=json.loads(l)
    if int(s['id'])%2==0: stints[s['id']].append(s)
T,U,O=[],[],[]
for gid,ss in stints.items():
    g=R.games.get(gid)
    try: acts=json.load(open(f'data/defense-a-source/pbp/{gid}.json',encoding='utf-8'))['data']['game']['actions']
    except Exception: continue
    if not g: continue
    ss.sort(key=lambda s:s['startIndex'])
    share=collections.defaultdict(float); tot=collections.Counter(); exp_=collections.defaultdict(float); truth=collections.defaultdict(float); tov_t=collections.defaultdict(float)
    for m in g['matchups']:
        share[(m['def'],m['off'])]+=m['partialPossessions']; tot[m['off']]+=m['partialPossessions']
        exp_[m['def']]+=R.exp.get(m['off'],R.lg)*m['partialPossessions']; truth[m['def']]+=m['playerPoints']; tov_t[m['def']]+=m['matchupTurnovers']
    k=0; prev=(0,0); allowU=collections.defaultdict(float); allowO=collections.defaultdict(float); tovU=collections.defaultdict(float); tovO=collections.defaultdict(float)
    for i,a in enumerate(acts):
        while k+1<len(ss) and ss[k+1]['startIndex']<=i: k+=1
        st=ss[k]; sc=(int(a.get('scoreHome') or prev[0]),int(a.get('scoreAway') or prev[1])); dp=sc[0]-prev[0]+sc[1]-prev[1]; prev=sc
        ev=None
        if dp>0 and a.get('personId'): ev=('p',dp)
        elif a.get('actionType')=='turnover' and a.get('personId'): ev=('t',1)
        if not ev: continue
        o=a['personId']; tm=a.get('teamId')
        dl=[t['players'] for t in st['teams'] if t['teamId']!=tm]
        if not dl: continue
        ds=dl[0]; w=np.array([share[(d,o)] for d in ds]); w=w/w.sum() if w.sum()>0 else np.full(5,0.2)
        for d,wo in zip(ds,w):
            if ev[0]=='p': allowU[d]+=ev[1]/5; allowO[d]+=ev[1]*wo
            else: tovU[d]+=0.2; tovO[d]+=wo
    for d in exp_:
        if mins.get((gid,d),0)<10: continue
        T.append(W['PTS_SAVED']*(exp_[d]-truth[d])+W['TOV_FORCED']*tov_t[d])
        U.append(W['PTS_SAVED']*(exp_[d]-allowU[d])+W['TOV_FORCED']*tovU[d])
        O.append(W['PTS_SAVED']*(exp_[d]-allowO[d])+W['TOV_FORCED']*tovO[d])
T,U,O=map(np.array,(T,U,O))
print('n',len(T),'原本誤差中位',round(np.median(np.abs(T-T.mean()))*C,2))
for nm,x in (('PBP 平均分給在場 5 人',U),('PBP＋完美猜對誰守誰',O)):
    b=np.polyfit(x,T,1); e=T-np.polyval(b,x); print(f'{nm:22s} R²={1-e.var()/T.var():.3f}  誤差中位 {np.median(np.abs(e-e.mean()))*C:.2f}  >1分 {(np.abs(e-e.mean())*C>1).mean():.2f}')
