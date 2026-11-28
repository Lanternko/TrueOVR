# 上限測試（2025-26 A 半）：就算「誰守誰、守幾回合」完全猜對，但被守者的得分只能按回合比例分攤（沒有追蹤資料就只能這樣），能補回多少對位項
import sys, json, collections; sys.path.insert(0,'scripts'); sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, rating_m2
C=json.load(open('reports/rating-m6/params.json',encoding='utf-8'))['prod']['C']['c']
R=rating_m2.Rater('2025-26'); W=R.w['per36']
rs=json.load(open('data/season-source/player-games.json',encoding='utf-8'))['data']['resultSets'][0]; h={k:i for i,k in enumerate(rs['headers'])}
box={(r[h['GAME_ID']],r[h['PLAYER_ID']]):r for r in rs['rowSet']}
true_,orc,mn_=[],[],[]
for gid,g in R.games.items():
    if int(gid)%2: continue
    poss=collections.Counter(); 
    for m in g['matchups']: poss[m['off']]+=m['partialPossessions']
    ts=collections.defaultdict(lambda:[0.0,0.0]); to=collections.defaultdict(lambda:[0.0,0.0])
    for m in g['matchups']:
        o=m['off']; r=box.get((gid,o)); share=m['partialPossessions']/poss[o] if poss[o] else 0
        opts=(r[h['PTS']] or 0) if r else 0; otov=(r[h['TOV']] or 0) if r else 0
        d=m['def']
        ts[d][0]+=R.exp.get(o,R.lg)*m['partialPossessions']-m['playerPoints']; ts[d][1]+=R.exp.get(o,R.lg)*m['partialPossessions']-opts*share
        to[d][0]+=m['matchupTurnovers']; to[d][1]+=otov*share
    for d in ts:
        r=box.get((gid,d))
        if not r or (r[h['MIN']] or 0)<10: continue
        true_.append(W['PTS_SAVED']*ts[d][0]+W['TOV_FORCED']*to[d][0]); orc.append(W['PTS_SAVED']*ts[d][1]+W['TOV_FORCED']*to[d][1])
t,o=np.array(true_),np.array(orc)
b=np.polyfit(o,t,1); e=t-np.polyval(b,o)
print('n',len(t),'對位項 R²（完美猜對誰守誰）',round(1-e.var()/t.var(),3),'相關',round(np.corrcoef(t,o)[0,1],3))
print('對位項本身 評分尺度標準差',round(t.std()*C,2),'猜完剩下誤差中位',round(np.median(np.abs(e-e.mean()))*C,2),'原本誤差中位',round(np.median(np.abs(t-t.mean()))*C,2))
