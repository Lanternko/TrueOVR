import csv, json, math, random
from pathlib import Path
D=Path('reports/E120-foul-defense')
def rows(p): return {int(r['playerId']):r for r in csv.DictReader(open(p,encoding='utf-8'))}
R,F=rows('reports/impact-rapm/rapm.csv'),rows('reports/impact-rapm/four-factors.csv')
L=json.load(open(D/'ledger-ft.json',encoding='utf-8'))['players']
co=[p for p in L if p['playerId'] in R and p['playerId'] in F and float(R[p['playerId']]['pooledPoss'])>=8000]
x=[p['ft'] for p in co]; y=[0.68*float(F[p['playerId']]['ftRate_defense']) for p in co]
def mean(a): return sum(a)/len(a)
def pr(a,b):
    ma,mb=mean(a),mean(b);return sum((u-ma)*(v-mb) for u,v in zip(a,b))/math.sqrt(sum((u-ma)**2 for u in a)*sum((v-mb)**2 for v in b))
r=pr(x,y);random.seed(120);bs=[]
for _ in range(2000):
    s=[random.randrange(len(co)) for _ in co];bs.append(pr([x[i] for i in s],[y[i] for i in s]))
bs.sort()
# also E-118 beta vs ftRate (sanity), and cohort size check
sd=lambda a:math.sqrt(sum((u-mean(a))**2 for u in a)/(len(a)-1))
bypos={}
for p in co: bypos.setdefault(p['pos'],[]).append(p['ft'])
out={'n_cohort':len(co),'pooledPoss_min':8000,'r_ft_vs_068ftRateDef':r,'ci90_boot':[bs[100],bs[1899]],'threshold':0.40,'pass':r>=0.40,
 'sd_ledger_ft':sd(x),'sd_rapm_ft':sd(y),'ledger_ft_mean_by_pos':{k:mean(v) for k,v in bypos.items()},
 'ledger_ft_range':[min(x),max(x)]}
json.dump(out,open(D/'t1.json','w'),indent=1,ensure_ascii=False);print(json.dumps(out,ensure_ascii=False))
