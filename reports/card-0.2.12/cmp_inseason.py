import csv,json,sys
D='D:/Projects/CODING/basketball-autochess/reports/ovr-inseason-2026-27/live/'
def L(p):
    r=list(csv.DictReader(open(D+p,encoding='utf-8')))
    return {x['playerId']:x for x in r}
A=L('2026-10-31/ranking.csv');B=L('_base10a_nowin/ranking.csv');C=L('_win10_trial/ranking.csv')
def cmp(X,Y,nx,ny,col='ovr'):
    ids=[i for i in X if i in Y]
    d=[(float(Y[i][col])-float(X[i][col]),i) for i in ids]
    nz=[x for x in d if abs(x[0])>1e-9]
    rx={i:int(X[i]['rank']) for i in ids}; ry={i:int(Y[i]['rank']) for i in ids}
    top=lambda R,n:{i for i in ids if R[i]<=n}
    out={'pair':f'{nx}->{ny}','n':len(ids),'changed':len(nz),'maxAbs':max((abs(x[0]) for x in d),default=0),
         'top20_out':len(top(rx,20)-top(ry,20)),'top100_out':len(top(rx,100)-top(ry,100)),
         'rank_moved10':sum(1 for i in ids if rx[i]<=100 and abs(rx[i]-ry[i])>=10)}
    nz.sort(key=lambda x:-abs(x[0]))
    out['movers']=[(X[i]['name'],X[i]['team'],rx[i],ry[i],round(x,1)) for x,i in nz[:12]]
    return out
for X,Y,a,b in ((A,B,'0.2.10','0.2.10a(關窗)'),(B,C,'0.2.10a(關窗)','0.2.12'),(A,C,'0.2.10','0.2.12')):
    o=cmp(X,Y,a,b);print(json.dumps(o,ensure_ascii=False))
    for col in ('dOVR',):
        pass
