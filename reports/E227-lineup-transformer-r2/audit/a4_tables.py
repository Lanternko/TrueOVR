"""稽核 A4：從 value-raw.json 重算報告的相關表（BPM、RAPM）與防守側翼名次。"""
import json, csv, os, numpy as np
from scipy.stats import spearmanr, rankdata
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ROOT = os.path.dirname(os.path.dirname(R))
raw = json.load(open(os.path.join(R, 'results/value-raw.json'), encoding='utf-8')); pids = raw['pids']; names = raw['names']
V = {m: np.array(raw['new'][m]) for m in raw['new']}
bp = {r['playerId']: float(r['bpm']) for r in csv.DictReader(open(os.path.join(ROOT, 'data/external-impact/bpm/bpm_2025-26.csv'), encoding='utf-8'))}
rr = list(csv.DictReader(open(os.path.join(ROOT, 'reports/card-0.2.10+E186-t6-rapm-target/work/base-K6U-2025-26/c0/rapm-R.csv'), encoding='utf-8')))
o = {r['playerId']: float(r['pooledO']) for r in rr}; d = {r['playerId']: float(r['pooledD']) for r in rr}
M = ('R2-abil', 'R2-stats', 'R2-stats-rapm')
for nm, f in (('BPM', bp), ('RAPM off', o), ('RAPM def', d)):
    ix = [i for i, p in enumerate(pids) if p in f]
    print(nm, len(ix), [round(float(spearmanr(V[m][ix], [f[pids[i]] for i in ix])[0]), 3) for m in M])
for m in M:
    rk = rankdata(-V[m], method='min').astype(int)
    print(m, {n: int(rk[names.index(n)]) for n in ('Dean Wade', 'Tari Eason', 'Herbert Jones', 'Draymond Green')})
