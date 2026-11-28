# E-117 W1-W3 (+W5 from bias.json). Usage (repo root): python -X utf8 reports/sim-0.1.0+E117-fatigue-off/compare_e117.py
import csv,json,numpy as np
from scipy.stats import spearmanr,rankdata
D='reports/sim-0.1.0+E117-fatigue-off/'
rd=lambda p:{r['name']:r for r in csv.DictReader(open(p,encoding='utf-8-sig'))}
on=rd('reports/card-0.1.2+E065-inout-wins/winimp.csv');off=rd(D+'winimp-off.csv')
st=json.load(open(D+'stamina.json',encoding='utf-8'))
names=sorted(on);assert set(names)==set(off) and len(names)==379
out={'n':len(names),'onSource':'reports/card-0.1.2+E065-inout-wins/winimp.csv','offSource':D+'winimp-off.csv','rankDefinition':'rank 1 = highest winsPer82 (descending, average rank for ties); rank change = rank_on - rank_off, positive = rises when fatigue is off'}
rk=lambda v:rankdata(-np.array(v))
def part(col,key):
    a=[float(on[n][col]) for n in names];b=[float(off[n][col]) for n in names];ra,rb=rk(a),rk(b)
    ch=ra-rb;rows=[]
    for i,n in enumerate(names):
        rows.append({'name':n,'pos':on[n]['pos'],'mpg':float(on[n]['MPG']),'stamina':st[n]['stamina'],'rankOn':float(ra[i]),'rankOff':float(rb[i]),'rankChange':float(ch[i]),'winsOn':a[i],'winsOff':b[i]})
    srt=sorted(rows,key=lambda r:-r['rankChange'])
    r={'spearman_on_off':float(spearmanr(ra,rb)[0]),'meanAbsRankChange':float(np.abs(ch).mean()),'medianAbsRankChange':float(np.median(np.abs(ch))),'meanWinsOn':float(np.mean(a)),'meanWinsOff':float(np.mean(b)),
       'top10Rises':srt[:10],'top10Falls':srt[::-1][:10]}
    top=lambda rr:{x for x in names if rr[names.index(x)]<=20}
    t_on,t_off=top(ra),top(rb)
    r['W2_top20']={'kept':sorted(t_on&t_off),'enteredWhenOff':sorted(t_off-t_on),'leftWhenOff':sorted(t_on-t_off),'rankOffOfEntered':{n:float(rb[names.index(n)]) for n in t_off-t_on},'rankOffOfLeft':{n:float(rb[names.index(n)]) for n in t_on-t_off}}
    s=np.array([st[n]['stamina'] for n in names]);qs=np.percentile(s,[25,50,75]);g=np.digitize(s,qs,right=True)
    q=[]
    for k in range(4):
        m=g==k;q.append({'quartile':k+1,'staminaRange':[float(s[m].min()),float(s[m].max())],'n':int(m.sum()),'meanRankChange':float(ch[m].mean()),'meanMpg':float(np.mean([on[names[i]]['MPG'] and float(on[names[i]]['MPG']) for i in np.where(m)[0]])),'meanWinsChange':float(np.mean(np.array(b)[m]-np.array(a)[m]))})
    r['W3_staminaQuartiles']={'cutPoints25_50_75':[float(v) for v in qs],'note':'quartile 1 = lowest stamina','groups':q,'ties':'stamina has many ties at 40/99; digitize(right=True) splits by cut points so group sizes are uneven'}
    r['spearman_stamina_vs_rankChange']=float(spearmanr(s,ch)[0])
    out[key]=r
part('winsPer82','main');part('winsPer82_pos','pos')
try:
    b=json.load(open(D+'bias.json',encoding='utf-8'))['e117']
    out['W5_rho']={k:{'rho_on':b[k]['rho_on'],'rho_off':b[k]['rho_off'],'rho_on_mean':b[k]['rho_on_mean'],'rho_off_mean':b[k]['rho_off_mean'],'diff':b[k]['rho_diff_off_minus_on']} for k in('main','pos')}
except FileNotFoundError:out['W5_rho']='bias.json missing'
json.dump(out,open(D+'winimp-compare.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
for k in('main','pos'):
    r=out[k];print(k,'rho',round(r['spearman_on_off'],4),'meanAbs',round(r['meanAbsRankChange'],2),'Q',[round(g['meanRankChange'],1) for g in r['W3_staminaQuartiles']['groups']])
