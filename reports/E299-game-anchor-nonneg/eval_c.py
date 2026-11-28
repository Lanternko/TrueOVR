"""E-299 C-3：同輸入重跑（stage1/repro）vs 非負約束（stage1/nonneg）卡片 OVR 對 T／EPM（2026-27，樣本外）／2K 的 Spearman，配對 bootstrap。"""
import csv, json, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
EXP = Path(__file__).resolve().parent; ROOT = EXP.parents[1]; R = lambda p: ROOT / p
nm = lambda s: ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower().replace('.', '').replace(' jr', '').strip()
pid = {r['name']: r['playerId'] for r in csv.DictReader(open(R('reports/card-0.2.13-w246/cards/K6/primary/pred.csv'), encoding='utf-8'))}
rd = lambda p: {r['name']: r for r in csv.DictReader(open(p, encoding='utf-8'))}
A, B = rd(EXP / 'stage1/repro/ranking.csv'), rd(EXP / 'stage1/nonneg/ranking.csv')
names = [n for n in A if n in B and float(A[n]['MIN']) >= 500]
oA = np.array([float(A[n]['ovr']) for n in names]); oB = np.array([float(B[n]['ovr']) for n in names])
ts = json.load(open(R('reports/ovr-inseason-2026-27/live/2026-11-08/t-swap.json'), encoding='utf-8'))
T = {str(p): ts['ownPts100'][p] - ts['oppPts100'][p] for p in ts['pool']}
E = {r['playerId']: float(r['net']) for r in csv.DictReader(open(R('reports/impact-epm-2026-27/epm-live.csv'), encoding='utf-8')) if float(r['poss2627'] or 0) >= 200}
K = {}
for r in csv.DictReader(open(R('reports/ovr-v55-2k27-compare/2k27_ratings.csv'), encoding='utf-8-sig')):
    if r['overall2k']: K.setdefault(nm(r['name']), float(r['overall2k']))
ref = {'T': [T.get(pid.get(n)) for n in names], 'EPM': [E.get(pid.get(n)) for n in names], '2K': [K.get(nm(n)) for n in names]}
rng = np.random.default_rng(299); out = {'n_pool': len(names), 'rho': {}}
for s, y in ref.items():
    k = np.array([i for i in range(len(names)) if y[i] is not None]); yy = np.array([y[i] for i in k])
    ra, rb = spearmanr(oA[k], yy)[0], spearmanr(oB[k], yy)[0]; bs = []
    for _ in range(2000):
        b = rng.integers(0, len(k), len(k)); bs.append(spearmanr(oB[k][b], yy[b])[0] - spearmanr(oA[k][b], yy[b])[0])
    out['rho'][s] = dict(n=len(k), repro=round(ra, 4), nonneg=round(rb, 4), d=round(rb - ra, 4), ci90=[round(float(np.percentile(bs, q)), 4) for q in (5, 95)])
d = oB - oA; o = np.argsort(d)
out['absd_med'] = float(np.median(abs(d))); out['n_absd_ge1'] = int((abs(d) >= 1).sum())
out['fall'] = [(names[i], A[names[i]]['pos'], oA[i], oB[i], A[names[i]]['drive']) for i in o[:6]]
out['rise'] = [(names[i], A[names[i]]['pos'], oA[i], oB[i], A[names[i]]['drive']) for i in o[-6:]]
top = lambda o_: [names[i] for i in np.argsort(-o_)[:20]]
out['top20_overlap'] = len(set(top(oA)) & set(top(oB)))
out['C_drive_rho_with_dOVR'] = float(spearmanr([float(A[n]['drive']) for n in names], d)[0])
print(json.dumps(out, ensure_ascii=False, indent=1)); json.dump(out, open(EXP / 'eval_c.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
