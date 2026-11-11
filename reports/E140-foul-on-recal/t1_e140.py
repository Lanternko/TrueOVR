import csv, json, math, random
from pathlib import Path
D=Path('reports/E140-foul-on-recal')
def rows(p): return {int(r['playerId']):r for r in csv.DictReader(open(p,encoding='utf-8'))}
R,F=rows('reports/impact-rapm/rapm.csv'),rows('reports/impact-rapm/four-factors.csv')
L=json.load(open(D/'ledger-ft.json',encoding='utf-8'))['players']
co=[p for p in L if p['playerId'] in R and p['playerId'] in F and float(R[p['playerId']]['pooledPoss'])>=8000]
y=[0.68*float(F[p['playerId']]['ftRate_defense']) for p in co]
mean=lambda a:sum(a)/len(a)
def pr(a,b):
    ma,mb=mean(a),mean(b);return sum((u-ma)*(v-mb) for u,v in zip(a,b))/math.sqrt(sum((u-ma)**2 for u in a)*sum((v-mb)**2 for v in b))
out={'n_cohort':len(co)}
for key in('ft','ftC'):
    x=[p[key] for p in co];r=pr(x,y);random.seed(140);bs=[]
    for _ in range(2000):
        s=[random.randrange(len(co)) for _ in co];bs.append(pr([x[i] for i in s],[y[i] for i in s]))
    bs.sort();out[key]={'r':r,'ci90_boot':[bs[100],bs[1899]],'mean':mean(x),'range':[min(x),max(x)]}
json.dump(out,open(D/'t1.json','w'),indent=1,ensure_ascii=False);print(json.dumps(out,ensure_ascii=False))
