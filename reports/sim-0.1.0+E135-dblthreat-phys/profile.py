import csv, json, sys, importlib.util
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
sys.stdout.reconfigure(encoding='utf-8')
R=Path('D:/Projects/CODING/basketball-autochess')
spec=importlib.util.spec_from_file_location('s240',R/'reports/sim-0.1.0+E102-winimp-240/scale240.py'); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
SC=M.SC
NAMES,A=M.load('dedup')
POSN={r['name']:r['pos'] for r in csv.DictReader(open(SC.CSV['legacy'],encoding='utf-8-sig'))}
ans={'AB':M.BC.answers('B'),'OOS':M.BE.oos_answers()[0]}
X=A['X'].mean(1)
rows={r['name']:r for r in csv.DictReader(open(R/'reports/player-impact-v41/2025-26-player-validation.csv',encoding='utf-8-sig'))}
cols=['pts36','fga36','fta36','fgPct','oreb36','dreb36','ast36','tov36','blk36','stl36','onTeamFG','onTeammateFG','onOpponentFG','teamFGOnOff','team3POnOff','onOpponent3P','rimRestoredDifference','creationDependence_sourceRole']
out={}
for an in ans:
  pop=SC.Pop(an,ans[an],NAMES,POSN); res=pop.resid(X[pop.rows])
  ok=np.array([n in rows and float(rows[n]['actualMinutes'])>=800 for n in pop.names])
  isC=pop.pos=='C'
  print(an,'n',ok.sum(),'C',(ok&isC).sum())
  for c in cols:
    key=c if c.startswith(('rim','creation')) else c+'_error'
    v=np.array([float(rows[n][key]) if ok[i] and rows[n].get(key,'') not in ('',None) else np.nan for i,n in enumerate(pop.names)])
    m=ok&~np.isnan(v); mc=m&isC
    print(f'  {c:30s} rho_all {spearmanr(res[m],v[m])[0]:+.2f}  rho_C {spearmanr(res[mc],v[mc])[0]:+.2f} meanC {np.nanmean(v[mc]):+.3f} meanG {np.nanmean(v[m&np.isin(pop.pos,["PG","SG"])]):+.3f}')
