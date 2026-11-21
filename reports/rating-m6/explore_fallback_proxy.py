# 探索（只用 2025-26 A 半）：沒對位資料時，三種暫估能補回多少 M2−M0 差距
import sys, json, glob, collections; sys.path.insert(0,'scripts'); sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, rating_m2
pr=json.load(open('reports/rating-m6/params.json',encoding='utf-8'))['prod']; C=pr['C']['c']
rs=json.load(open('data/season-source/player-games.json',encoding='utf-8'))['data']['resultSets'][0]; h={k:i for i,k in enumerate(rs['headers'])}
rows=[r for r in rs['rowSet'] if int(r[h['GAME_ID']])%2==0 and (r[h['MIN']] or 0)>0]
R=rating_m2.Rater('2025-26')
def v0(r):
    mn=r[h['MIN']]; return R.m0['intercept']+sum(b*(r[h[k]] or 0) for k,b in R.m0['per36'].items())*36/mn
# 位置：先發位置的眾數（box traditional）
pos=collections.defaultdict(collections.Counter)
for p in glob.glob('data/defense-source/boxes/*.json'):
    if int(p[-15:-5])%2: continue
    d=json.load(open(p,encoding='utf-8')); g=d.get('boxScoreTraditional') or d.get('data',{}).get('boxScoreTraditional') or d
    if 'homeTeam' not in g: continue
    for side in ('homeTeam','awayTeam'):
        for pl in g[side]['players']:
            if pl.get('position'): pos[pl['personId']][pl['position']]+=1
P={k:c.most_common(1)[0][0] for k,c in pos.items()}
# 在場防守：stints
on=collections.defaultdict(lambda:[0.0,0.0]); lgp=[0,0]
for line in open('reports/defense-b1/stints.jsonl',encoding='utf-8'):
    s=json.loads(line)
    if int(s['id'])%2: continue
    for t in s['teams']:
        pts,ps=t['opponent']['points'],t['defensivePossessions']; lgp[0]+=pts; lgp[1]+=ps
        for pid in t['players']: a=on[(s['id'],pid)]; a[0]+=pts; a[1]+=ps
LG=lgp[0]/lgp[1]
# 對手預期：A 半每位球員 TS
tsa=collections.Counter(); pts=collections.Counter()
for r in rows: t=(r[h['FGA']] or 0)+0.44*(r[h['FTA']] or 0); tsa[r[h['PLAYER_ID']]]+=t; pts[r[h['PLAYER_ID']]]+=r[h['PTS']] or 0
lgts=sum(pts.values())/(2*sum(tsa.values()))
ets={p:(pts[p]/(2*tsa[p]) if tsa[p]>=100 else lgts) for p in tsa}
bygame=collections.defaultdict(list)
for r in rows: bygame[r[h['GAME_ID']]].append(r)
out=[]
for gid,rr in bygame.items():
    if R.extra(gid) is None: continue
    for r in rr:
        mn=r[h['MIN']]
        if mn<10: continue
        pid=r[h['PLAYER_ID']]; tid=r[h['TEAM_ID']]; gap=(R.value(r,h)-v0(r))*mn/36
        o=on.get((gid,pid)); p1=(LG*o[1]-o[0]) if o and o[1] else 0.0
        my=P.get(pid); p2=0.0
        if my:
            mates=sum(x[h['MIN']] for x in rr if x[h['TEAM_ID']]==tid and P.get(x[h['PLAYER_ID']])==my)
            for x in rr:
                if x[h['TEAM_ID']]!=tid and P.get(x[h['PLAYER_ID']])==my:
                    t=(x[h['FGA']] or 0)+0.44*(x[h['FTA']] or 0); p2+=(2*ets.get(x[h['PLAYER_ID']],lgts)*t-(x[h['PTS']] or 0))*mn/mates
        out.append((pid,gap,p1,p2,mn,my is not None))
pid=np.array([o[0] for o in out]); gap,p1,p2,mn=(np.array([o[i] for o in out]) for i in (1,2,3,4)); hasp=np.array([o[5] for o in out])
# 本人平均差距（每 36）×分鐘：留一場外
s36=collections.defaultdict(lambda:[0.0,0.0])
for a,g,m in zip(pid,gap,mn): s36[a][0]+=g; s36[a][1]+=m
p3=np.array([(s36[a][0]-g)/max(s36[a][1]-m,1)*m for a,g,m in zip(pid,gap,mn)])
def ev(name,X):
    X=np.column_stack([np.ones(len(gap))]+X); b=np.linalg.lstsq(X,gap,rcond=None)[0]; e=gap-X@b
    print(f'{name:28s} R²={1-e.var()/gap.var():.3f}  評分差中位 {np.median(np.abs(e))*C:.2f}  >1分 {(np.abs(e)*C>1).mean():.2f}')
print('n',len(gap),'有位置',hasp.mean().round(2),'LG ppp',round(LG,3))
ev('現況（不補）',[]); ev('①在場防守效率',[p1]); ev('②同位置對手 實際−預期',[p2]); ev('③本人平均防守',[p3])
ev('①＋③',[p1,p3]); ev('①＋②＋③',[p1,p2,p3])
# 拆解：差距＝box 權重不同＋hustle＋對位
W=R.w['per36']; EX=('DEFL','CONTEST','CHARGE','LOOSE','SCREEN_AST'); MU=('PTS_SAVED','TOV_FORCED')
parts=[]
for gid,rr in bygame.items():
    e=R.extra(gid)
    if e is None: continue
    for r in rr:
        mn=r[h['MIN']]
        if mn<10: continue
        x=e.get(r[h['PLAYER_ID']],{})
        box2=R.w['intercept']*mn/36+sum(b*(r[h[k]] or 0) for k,b in W.items() if k in h)
        hu=sum(W[k]*x.get(k,0) for k in EX); mu=sum(W[k]*x.get(k,0) for k in MU)
        parts.append((r[h['PLAYER_ID']],box2-v0(r)*mn/36,hu,mu,mn))
pp=np.array([p[0] for p in parts]); bx,hu,mu,mm=(np.array([p[i] for p in parts]) for i in (1,2,3,4)); G=bx+hu+mu
print('變異佔比 box權重',round(np.cov(bx,G)[0,1]/G.var(),2),'hustle',round(np.cov(hu,G)[0,1]/G.var(),2),'對位',round(np.cov(mu,G)[0,1]/G.var(),2))
acc=collections.defaultdict(lambda:[0.0,0.0])
for a,u,v,m in zip(pp,hu,mu,mm): acc[a][0]+=u+v; acc[a][1]+=m
loo=np.array([(acc[a][0]-u-v)/max(acc[a][1]-m,1)*m for a,u,v,m in zip(pp,hu,mu,mm)])
for name,est in [('現況 M0',np.zeros_like(G)),('M2 box 權重，防守不算',bx),('M2 box＋本人平均 hustle/對位',bx+loo)]:
    e=G-est; e=e-e.mean(); print(f'{name:30s} 評分差中位 {np.median(np.abs(e))*C:.2f}  >1分 {(np.abs(e)*C>1).mean():.2f}  >2分 {(np.abs(e)*C>2).mean():.2f}')
