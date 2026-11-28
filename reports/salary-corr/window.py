# 只看合約簽約前後一年：簽在 2024-07 ~ 2026-06 的非新秀合約，對 2025-26 各指標
import re, csv, html, sys, unicodedata
import numpy as np
from scipy.stats import spearmanr
D=sys.argv[1]
def norm(n):
    n=unicodedata.normalize('NFKD',html.unescape(n)).encode('ascii','ignore').decode().lower()
    n=re.sub(r"[.']",'',n); n=re.sub(r'\b(jr|sr|ii|iii|iv)\b','',n); return re.sub(r'[^a-z]','',n)
def salaries(f):
    # y1＝球員該季在所有球隊的總額；被裁球員有兩列（舊隊死錢＋新隊），這時取新隊（保障額較小那列）的 remain_gtd，上限 y1
    s=open(f,encoding='utf-8').read(); rows={}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>',s,re.S):
        m=re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)',row); y=re.search(r'data-stat="y1"[^>]*>\$?([\d,]+)',row)
        g=re.search(r'data-stat="remain_gtd"[^>]*>\$?([\d,]+)',row)
        if m and y: rows.setdefault(norm(m.group(1)),[]).append((int(y.group(1).replace(',','')),int(g.group(1).replace(',','')) if g else 0))
    return {k:(v[0][0] if len(v)==1 else min(v[0][0],min(x[1] for x in v))) for k,v in rows.items()}
s26,s27=salaries(D+'/bref2526.html'),salaries(D+'/bref.html')
drafted={}
for y in range(2021,2026):
    s=open(f'{D}/draft{y}.html',encoding='utf-8').read()
    for n in re.findall(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)',s)[1:]: drafted[norm(n)]=y
ev={}  # player -> list of (season_window, kind, text)
for page,win in [('tx2025.html','2024-25'),('tx2026.html','2025-26')]:
    s=open(D+'/'+page,encoding='utf-8').read()
    for li in re.findall(r'<li[^>]*>\s*<span>([^<]+)</span>(.*?)</li>',s,re.S):
        date=li[0]
        for p in re.findall(r'<p>(.*?)</p>',li[1],re.S):
            t=html.unescape(re.sub('<[^>]+>','',p))
            m=re.search(r'signed (.+?)(?: to (a|an) (.+?))?\.$',t)
            if not m or re.search(r'two-way|10-day|Exhibit|rest-of-season|hardship',t,re.I): continue
            for nm in re.split(r', and |, | and ',m.group(1)):
                ev.setdefault(norm(nm),[]).append((win,date,'ext' if 'extension' in t else 'fa',t))
card=list(csv.DictReader(open('reports/card-0.2.7c/ranking.csv',encoding='utf-8')))
k2={norm(r['name']):r for r in csv.DictReader(open('reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv',encoding='utf-8'))}
rap={norm(r['name']):r for r in csv.DictReader(open('reports/impact-rapm/rapm.csv',encoding='utf-8')) if r['name']}
own={norm(r['name']):float(r['careerO'])+float(r['careerD']) for r in csv.DictReader(open('reports/impact-epm-2026-27/epm-live.csv',encoding='utf-8')) if r['careerO']}
f=lambda v: float(v) if v not in (None,'') else None
rows=[];skip={'rookie':0,'future-ext':0,'nosal':0}
for c in card:
    k=norm(c['name']); es=ev.get(k)
    if not es: continue
    win,date,kind,t=es[-1]   # 最近一次簽約
    dy=drafted.get(k)
    if kind=='fa' and dy and str(dy) in date: skip['rookie']+=1; continue   # 選秀當年簽的新秀約
    if kind=='ext' and win=='2025-26':
        sal=s27.get(k); old=s26.get(k)
        if sal and old and 1.0<=sal/old<=1.085: skip['future-ext']+=1; continue  # 延長合約還沒開始（2027-28 起）
    else: sal=s26.get(k)
    if not sal: skip['nosal']+=1; continue
    r=rap.get(k); y=k2.get(k,{})
    rows.append(dict(name=c['name'],MIN=float(c['MIN']),sal=sal,kind=kind,win=win,ovr=f(c['ovr']),k26=f(y.get('2K26')),k27=f(y.get('2K27')),
        own=own.get(k),rp=f(r['pooledNet']) if r else None,r1=f(r['lastSeasonNet']) if r else None))
print('skip',skip,'| kept',len(rows),'| fa',sum(r['kind']=='fa' for r in rows),'ext',sum(r['kind']=='ext' for r in rows))
M=[('我們的 OVR','ovr'),('2K26（簽約前那年的評分）','k26'),('2K27','k27'),('自製 EPM 式','own'),('RAPM 多季','rp'),('RAPM 2025-26','r1')]
for lab,fl in [('全部',lambda r:True),('≥1000 分鐘',lambda r:r['MIN']>=1000),('薪水 > $5M（去掉底薪約）',lambda r:r['sal']>5e6)]:
    g=[r for r in rows if fl(r) and all(r[k] is not None for _,k in M)]
    print(f'{lab} n={len(g)}: '+'  '.join(f"{n}={spearmanr([r[k] for r in g],[r['sal'] for r in g])[0]:.2f}" for n,k in M))
