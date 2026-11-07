"""Descriptive, past-only omitted-factor counterfactual, not causal attribution."""
from defense_sixth_data import *
from itertools import combinations
d=Data(41);teams=d.league['teams'];raw=[]
for t in teams:
 logs=[r for r in d.team if r['TEAM_ID']==t['id'] and d.order[r['GAME_ID'],r['TEAM_ID']]<=41];opp=[d.tb[r['GAME_ID'],d.gmap[r['GAME_ID']]['awayId'] if d.gmap[r['GAME_ID']]['homeId']==t['id'] else d.gmap[r['GAME_ID']]['homeId']] for r in logs]
 sums={k:sum(r[k] for r in opp) for k in ['PTS','FGA','FGM','FG3M','FTA','FTM','OREB','TOV']}
 w=[p for p in d.cards['players'] if p['teamId']==t['id']];proxy=sum(p['minutes']*p['defenseAllowed'] for p in w)/sum(p['minutes'] for p in w)
 ownposs=sum(r['FGA']-r['OREB']+r['TOV']+.44*r['FTA'] for r in logs);opposs=sums['FGA']-sums['OREB']+sums['TOV']+.44*sums['FTA'];raw.append(dict(id=t['id'],name=t['name'],proxy=proxy,actual=100*sums['PTS']/((ownposs+opposs)/2),**sums))
tot={k:sum(r[k] for r in raw) for k in ['FGA','OREB','TOV','FTA','FTM']};league={k:tot[k]/tot['FGA'] for k in ['OREB','TOV','FTA']};ftp=tot['FTM']/tot['FTA'];factors=['OREB','TOV','FTA']
def counter(r,active):
 z={k:r[k]/r['FGA'] if k in active else league[k] for k in factors};return 100*((2*r['FGM']+r['FG3M'])/r['FGA']+z['FTA']*(r['FTM']/r['FTA'] if r['FTA'] else ftp))/(1-z['OREB']+z['TOV']+.44*z['FTA'])
components={f:[] for f in factors}
for r in raw:
 for f in factors:
  value=0
  for n in range(3):
   for a in combinations([z for z in factors if z!=f],n):value+=(counter(r,set(a)|{f})-counter(r,set(a)))/[3,6,3][n]
  components[f].append(value)
actual=np.array([r['actual'] for r in raw]);proxy=np.array([r['proxy'] for r in raw]);base=metrics(actual,proxy);allsets={}
for n in range(4):
 for a in combinations(factors,n):allsets['+'.join(a) or 'none']=metrics(actual,proxy+sum((np.array(components[z]) for z in a),np.zeros(30)))
contributions={}
for f in factors:
 v=0
 for n in range(3):
  for a in combinations([z for z in factors if z!=f],n):
   key=lambda b:'+'.join(z for z in factors if z in b) or 'none'
   v+=(allsets[key(set(a))]['calibrationSlope']-allsets[key(set(a)|{f})]['calibrationSlope'])/[3,6,3][n]
 contributions[f]=v
result=dict(definition='Existing shot-only card proxy augmented with observed training omitted-factor Shapley components. Calibration-slope changes are descriptive; observed components give an upper-information diagnostic, not an engine/player estimate and never an input. Exact counterfactual uses opponent possession proxy, whereas scored truth uses paired proxy; remaining slope is not uniquely identifiable as compressed cards.',before=base,after=allsets['OREB+TOV+FTA'],slopeGapReduction=contributions,components=components,teams=raw,subsets=allsets)
(R/'reports/defense-seventh/proxy-decomposition.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(base,result['after'],contributions)
