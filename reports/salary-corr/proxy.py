# 用 bref 進階數據擬合 2025-26 的 card 0.2.7c OVR，當過去賽季的 OVR 替代值
import re, csv, html, sys, unicodedata, json
import numpy as np
from scipy.stats import spearmanr
D=sys.argv[1]
def norm(n):
    n=unicodedata.normalize('NFKD',html.unescape(n)).encode('ascii','ignore').decode().lower()
    n=re.sub(r"[.']",'',n); n=re.sub(r'\b(jr|sr|ii|iii|iv)\b','',n); return re.sub(r'[^a-z]','',n)
F=['games','mp','per','ts_pct','usg_pct','ows','dws','ws_per_48','obpm','dbpm','bpm','vorp','orb_pct','drb_pct','ast_pct','stl_pct','blk_pct','tov_pct','fta_per_fga_pct','fg3a_per_fga_pct','age']
def adv(y):
    s=open(f'{D}/adv{y}.html',encoding='utf-8').read(); i=s.find('id="advanced"'); s=s[i:s.find('</table>',i)]; out={}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>',s,re.S):
        m=re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)*([^<]+)',row) or re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)',row)
        if not m: continue
        k=norm(m.group(1))
        if k in out: continue   # 第一列＝TOT（被交易球員的合計）
        v={}
        for f in F:
            x=re.search(rf'data-stat="{f}"[^>]*>(.*?)</td>',row,re.S)   # L-102：去掉 <strong>
            try: v[f]=float(re.sub(r'<[^>]+>','',x.group(1))) if x else 0.0
            except ValueError: v=None; break
        if v is None: continue
        out[k]=v
    return out
def X(v):
    mpg=v['mp']/max(v['games'],1)
    base=[v[f] for f in F]+[mpg, mpg*v['bpm'], v['vorp']/max(v['games'],1)*82, np.log1p(v['mp'])]
    return base
if __name__=='__main__':
    a=adv(2026); card=list(csv.DictReader(open('reports/card-0.2.7c/ranking.csv',encoding='utf-8')))
    xs,ys,ns=[],[],[]
    for c in card:
        k=norm(c['name'])
        if k in a: xs.append(X(a[k])); ys.append(float(c['ovr'])); ns.append(c['name'])
    Xm=np.array(xs); y=np.array(ys); print('matched',len(y),'of',len(card))
    mu,sd=Xm.mean(0),Xm.std(0)+1e-9; Z=(Xm-mu)/sd
    from sklearn.linear_model import RidgeCV
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_predict, KFold
    kf=KFold(10,shuffle=True,random_state=1)
    for nm,mdl in [('ridge',RidgeCV(alphas=np.logspace(-2,3,30))),('gbm',GradientBoostingRegressor(random_state=1,n_estimators=300,max_depth=3,learning_rate=0.05,subsample=0.8))]:
        p=cross_val_predict(mdl,Z,y,cv=kf)
        print(nm,'10-fold out-of-sample: Spearman',round(spearmanr(p,y)[0],3),'RMSE',round(float(np.sqrt(((p-y)**2).mean())),2),'| top-50 overlap',len(set(np.argsort(-p)[:50])&set(np.argsort(-y)[:50])))
        mp=np.array([r[1] for r in xs]); hi=mp>=1000
        print('   ≥1000 min Spearman',round(spearmanr(p[hi],y[hi])[0],3))
