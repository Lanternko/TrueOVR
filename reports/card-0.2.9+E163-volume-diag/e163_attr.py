"""E-163 輔助：各能力值與 USG／TS／FGA 代理的 Spearman（MIN>=500，4 季平均）。"""
import csv, pickle, sys, json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
sys.argv = [sys.argv[0]]
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
E162 = ROOT / 'reports/card-0.2.9+E162-per-volume'
import importlib.util
sp = importlib.util.spec_from_file_location('d', HERE / 'e163_diag.py')
src = (HERE / 'e163_diag.py').read_text(encoding='utf-8').replace('\nmain()\n', '\n')
ns = {'__file__': str(HERE / 'e163_diag.py')}
exec(compile(src, 'e163_diag', 'exec'), ns)
nm, EI, SEAS = ns['nm'], ns['EI'], ns['SEAS']
A = ['long','mid','short','ft','drive','foulDraw','tovSkill','pass','rebound','onBall','help','stamina','creation','pressure','pred0','pr','predictedPer36']
res = {a: {'usg': [], 'ts': []} for a in A}
for s in SEAS:
    adv = pickle.load(open(E162 / f'work/adv-{s}.pkl', 'rb')); nid = ns['names'](s)
    R = []
    for r in csv.DictReader(open(E162 / f'ranking-K-{s}.csv', encoding='utf-8')):
        if float(r['MIN']) < 500: continue
        p = nid.get(nm(r['name']))
        if p in adv and adv[p].get('usg_pct') is not None: R.append((r, adv[p]))
    for a in A:
        try:
            v = [float(r[a]) for r, _ in R]
        except Exception: continue
        res[a]['usg'].append(spearmanr(v, [x['usg_pct'] for _, x in R])[0]); res[a]['ts'].append(spearmanr(v, [x['ts_pct'] for _, x in R])[0])
out = {a: {k: round(float(np.mean(v)), 3) for k, v in d.items() if v} for a, d in res.items()}
(HERE / 'e163_attr_corr.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out))
