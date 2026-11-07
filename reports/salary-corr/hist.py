# 歷年：簽約前後一年的指標 vs 簽約首年薪水（÷ 當季薪資上限），不含新秀約
import re, csv, html, sys
import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
D=sys.argv[1]; sys.argv=['x',D]
import os; HERE=os.path.dirname(os.path.abspath(__file__))
exec(open(HERE+'/proxy.py',encoding='utf-8').read().split("if __name__")[0])
exec(open(HERE+'/window.py',encoding='utf-8').read().split("s26,s27=")[0].split("D=sys.argv[1]")[1])  # salaries()
CAP={2022:112.414e6,2023:123.655e6,2024:136.021e6,2025:140.588e6,2026:154.647e6,2027:165.0e6}
SAL={2022:salaries(D+'/contracts2022.html'),2023:salaries(D+'/contracts2023.html'),2024:salaries(D+'/contracts2024.html'),
     2025:salaries(D+'/contracts2025.html'),2026:salaries(D+'/bref2526.html'),2027:salaries(D+'/bref.html')}
ADV={y:adv(y) for y in range(2021,2027)}
# 替代 OVR：用 2025-26 擬合，套到每一季
card=list(csv.DictReader(open('reports/card-0.2.7c/ranking.csv',encoding='utf-8')))
tr=[(X(ADV[2026][norm(c['name'])]),float(c['ovr'])) for c in card if norm(c['name']) in ADV[2026]]
Xt=np.array([a for a,_ in tr]); mu,sd=Xt.mean(0),Xt.std(0)+1e-9
gbm=GradientBoostingRegressor(random_state=1,n_estimators=300,max_depth=3,learning_rate=0.05,subsample=0.8).fit((Xt-mu)/sd,[b for _,b in tr])
PROXY={y:{k:float(gbm.predict(((np.array(X(v))-mu)/sd)[None])[0]) for k,v in ADV[y].items()} for y in ADV}
OVR26={norm(c['name']):float(c['ovr']) for c in card}
K2={norm(r['name']):r for r in csv.DictReader(open('reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv',encoding='utf-8'))}
drafted={}
for y in range(2021,2026):
    s=open(f'{D}/draft{y}.html',encoding='utf-8').read()
    for n in re.findall(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)',s)[1:]: drafted[norm(n)]=y
rows=[]; skip=dict(rookie=0,future=0,nosal=0,nodata=0)
for Y in range(2021,2027):   # tx{Y}：Y-1 年 7 月 ~ Y 年 6 月
    s=open(f'{D}/tx{Y}.html',encoding='utf-8').read(); seen=set()
    for li in re.findall(r'<li[^>]*>\s*<span>([^<]+)</span>(.*?)</li>',s,re.S):
        date=li[0]
        for p in re.findall(r'<p>(.*?)</p>',li[1],re.S):
            t=html.unescape(re.sub('<[^>]+>','',p)); m=re.search(r'signed (.+?)(?: to (a|an) (.+?))?\.$',t)
            if not m or re.search(r'two-way|10-day|Exhibit|rest-of-season|hardship',t,re.I): continue
            ext='extension' in t
            for nm in re.split(r', and |, | and ',m.group(1)):
                k=norm(nm)
                if (k,Y) in seen: continue
                seen.add((k,Y))
                if not ext and drafted.get(k) in (Y-1,Y): skip['rookie']+=1; continue
                first=Y+1 if ext else Y           # 合約首年（季末年份）
                if first not in SAL: skip['nosal']+=1; continue
                sal=SAL[first].get(k)
                if ext and sal and first-1 in SAL and SAL[first-1].get(k) and 1.0<=sal/SAL[first-1][k]<=1.085: skip['future']+=1; continue
                if not sal: skip['nosal']+=1; continue
                pb,pa=PROXY.get(Y-1,{}).get(k),PROXY.get(Y,{}).get(k)
                kb,ka=K2.get(k,{}).get(f'2K{Y%100}'),K2.get(k,{}).get(f'2K{(Y+1)%100}')
                mpb=ADV.get(Y-1,{}).get(k,{}).get('mp',0)
                rows.append(dict(name=nm,Y=Y,ext=ext,sal=sal/CAP[first],pb=pb,pa=pa,kb=float(kb) if kb else None,ka=float(ka) if ka else None,
                                 mpb=mpb,ovr=OVR26.get(k) if Y-1==2025 or Y==2026 else None))
print('skip',skip,'kept',len(rows))
def rho(g,k): g=[r for r in g if r[k] is not None]; return (spearmanr([r[k] for r in g],[r['sal'] for r in g])[0],len(g)) if len(g)>9 else (float('nan'),len(g))
M=[('替代 OVR，簽約前一季','pb'),('替代 OVR，合約首季','pa'),('2K，簽約前一季後出的版本','kb'),('2K，合約首季後出的版本','ka')]
for lab,fl in [('全部',lambda r:True),('前一季 ≥1000 分鐘',lambda r:r['mpb']>=1000),('薪水 > 4% 上限（去掉底薪約）',lambda r:r['sal']>0.04)]:
    g=[r for r in rows if fl(r)]
    print(f"\n{lab}: "+'  '.join(f"{n}={rho(g,k)[0]:.2f}(n={rho(g,k)[1]})" for n,k in M))
    for Y in range(2022,2027):
        gy=[r for r in g if r['Y']==Y]
        print(f"   簽約季 {Y-1}-{str(Y)[2:]}: "+'  '.join(f"{k}={rho(gy,k)[0]:.2f}(n={rho(gy,k)[1]})" for _,k in M))
# 檢查替代值能不能代表真 OVR：2025-26 窗口內同一批人
g=[r for r in rows if r['Y'] in (2025,2026) and r['ovr'] is not None and r['pa'] is not None and r['Y']==2026]
print('\n檢查（2025-26 簽約，同一批人）: 真 OVR',round(rho(g,'ovr')[0],2),' 替代 OVR 首季',round(rho(g,'pa')[0],2),' n',len(g))
print('\n同一批人（四個指標都有）:')
for lab,fl in [('全部',lambda r:True),('前一季 ≥1000 分鐘',lambda r:r['mpb']>=1000),('薪水 > 4% 上限',lambda r:r['sal']>0.04)]:
    g=[r for r in rows if fl(r) and all(r[k] is not None for _,k in M)]
    print(f"  {lab} n={len(g)}: "+'  '.join(f"{k}={rho(g,k)[0]:.2f}" for _,k in M))
with open('reports/salary-corr/signings.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
