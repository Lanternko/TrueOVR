import re, csv, html, unicodedata, sys, math
import numpy as np
from scipy.stats import spearmanr, pearsonr
D=sys.argv[1]
def norm(n):
    n=unicodedata.normalize('NFKD',html.unescape(n)).encode('ascii','ignore').decode().lower()
    n=re.sub(r'[.\']','',n); n=re.sub(r'\b(jr|sr|ii|iii|iv)\b','',n)
    return re.sub(r'[^a-z]','',n)
# salary 2025-26 (bref contracts page archived 2026-02-20, column y1)
def salaries(f):
    # y1＝球員該季在所有球隊的總額；被裁球員有兩列（舊隊死錢＋新隊），這時取新隊（保障額較小那列）的 remain_gtd，上限 y1
    s=open(f,encoding='utf-8').read(); rows={}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>',s,re.S):
        m=re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)',row); y=re.search(r'data-stat="y1"[^>]*>\$?([\d,]+)',row)
        g=re.search(r'data-stat="remain_gtd"[^>]*>\$?([\d,]+)',row)
        if m and y: rows.setdefault(norm(m.group(1)),[]).append((int(y.group(1).replace(',','')),int(g.group(1).replace(',','')) if g else 0))
    return {k:(v[0][0] if len(v)==1 else min(v[0][0],min(x[1] for x in v))) for k,v in rows.items()}
sal=salaries(D+'/bref2526.html'); hdr='2025-26'
# 真 EPM（dunksandthrees）付費牆後只有前 5 名，不用；改用自製 EPM 式
epm={}
own={norm(r['name']):float(r['careerO'])+float(r['careerD']) for r in csv.DictReader(open('reports/impact-epm-2026-27/epm-live.csv',encoding='utf-8')) if r['careerO']}
card=list(csv.DictReader(open('reports/card-0.2.7c/ranking.csv',encoding='utf-8')))
r2k={norm(r['name']):float(r['overall2k']) for r in csv.DictReader(open('reports/ovr-v55-2k27-compare/2k27_ratings.csv',encoding='utf-8')) if r['overall2k']}
rap={norm(r['name']):r for r in csv.DictReader(open('reports/impact-rapm/rapm.csv',encoding='utf-8')) if r['name']}
pid={}
for r in csv.DictReader(open('reports/impact-rapm/rapm.csv',encoding='utf-8')):
    if r['name']: pid[norm(r['name'])]=int(r['playerId'])
rows=[]
for c in card:
    k=norm(c['name']); 
    if k not in sal: continue
    ra=rap.get(k); p=pid.get(k)
    rows.append(dict(name=c['name'],MIN=int(float(c['MIN'])),sal=sal[k],ovr=float(c['ovr']),
        twok=r2k.get(k),own=own.get(k),epm=epm.get(k),
        rapm_pool=float(ra['pooledNet']) if ra else None,
        rapm_2526=float(ra['lastSeasonNet']) if ra and ra['lastSeasonNet'] else None))
print('salary col',hdr,'| card',len(card),'matched salary',len(rows),'| epm',sum(r['epm'] is not None for r in rows),'2k',sum(r['twok'] is not None for r in rows),'rapm',sum(r['rapm_pool'] is not None for r in rows))
mets=[('our OVR (card 0.2.7c)','ovr'),('2K27 overall','twok'),('own EPM-style prior','own'),('RAPM multi-yr','rapm_pool'),('RAPM 2025-26','rapm_2526')]
for label,flt in [('all matched',lambda r:True),('MIN>=1000',lambda r:r['MIN']>=1000)]:
    print(f'\n== {label} ==  metric | n | Spearman | Pearson vs log(salary)')
    for nm,k in mets:
        g=[r for r in rows if flt(r) and r[k] is not None]
        if len(g)<10: continue
        x=[r[k] for r in g]; y=[r['sal'] for r in g]
        print(f'{nm:24s} {len(g):4d}  {spearmanr(x,y)[0]:.3f}  {pearsonr(x,np.log(y))[0]:.3f}')
    # common subset
    g=[r for r in rows if flt(r) and all(r[k] is not None for _,k in mets)]
    print(f'-- common subset n={len(g)}: '+'  '.join(f"{k}={spearmanr([r[k] for r in g],[r['sal'] for r in g])[0]:.3f}" for _,k in mets))
# biggest disagreement OVR vs salary rank, MIN>=1000
g=[r for r in rows if r['MIN']>=1000]
import scipy.stats as ss
ro=ss.rankdata([-r['ovr'] for r in g]); rs=ss.rankdata([-r['sal'] for r in g])
d=sorted(zip(ro-rs,g,ro,rs),key=lambda t:t[0])
print('\nUnderpaid (OVR rank >> salary rank):'); [print(f"  {r['name']}: OVR #{int(a)}, salary #{int(b)} ${r['sal']/1e6:.1f}M") for _,r,a,b in d[:8]]
print('Overpaid:'); [print(f"  {r['name']}: OVR #{int(a)}, salary #{int(b)} ${r['sal']/1e6:.1f}M") for _,r,a,b in d[-8:]]
unm=[c['name'] for c in card if norm(c['name']) not in sal and float(c['MIN'])>=1000]; print('\nunmatched MIN>=1000:',len(unm),unm[:15])
