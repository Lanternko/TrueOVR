# E-122 c1: Pearson r of engine duration delta vs beta. Usage (repo root): python -X utf8 reports/E122-clock-d1/analyze_c1.py <checkpoint.jsonl>
import json,sys,math
rows=[json.loads(l) for l in open(sys.argv[1],encoding='utf-8') if l.strip()]
rows=[r for r in rows if r.get('delta') is not None]
n=len(rows);x=[r['beta'] for r in rows];y=[r['delta'] for r in rows]
mx=sum(x)/n;my=sum(y)/n
sxy=sum((a-mx)*(b-my) for a,b in zip(x,y));sxx=sum((a-mx)**2 for a in x);syy=sum((b-my)**2 for b in y)
r=sxy/math.sqrt(sxx*syy);slope=sxy/sxx
print(json.dumps({'n':n,'pearson_r':r,'slope':slope,'mean_delta':my,'sd_beta':math.sqrt(sxx/n),'sd_delta':math.sqrt(syy/n),'min_nT':min(r_['nT'] for r_ in rows),'total_segments_T':sum(r_['nT'] for r_ in rows),'pass':r>=0.5}))
