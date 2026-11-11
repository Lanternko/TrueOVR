"""E-141 判定：讀 rookie-players.csv，輸出 train.csv、results.json。規則照預註冊（選 s* 只用訓練季，測試季只拿來判定）。"""
import csv, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CANDS = ['B0r', 'S25', 'S0', 'S+25']
SHIFT = {'B0r': -5.0, 'S25': -2.5, 'S0': 0.0, 'S+25': 2.5}
SELECTABLE = ['B0r', 'S25', 'S0']
TRAIN, TEST, REPORT = ['Y2', 'Y3', 'Y5', 'Y6'], ['D1', 'D2'], ['D3']
NCHK = [0, 5, 10]
TIE = 0.05
GROUPS = {'all': lambda p: True, 'pick1-10': lambda p: p <= 10, 'pick11-30': lambda p: 11 <= p <= 30,
          'pick31+andUndrafted': lambda p: p >= 31, 'pick31-60': lambda p: 31 <= p <= 60, 'undrafted': lambda p: p == 61}

rows = list(csv.DictReader(open(HERE / 'rookie-players.csv', encoding='utf-8')))
for r in rows:
    r['pick'] = int(r['pick'])
    for c in CANDS:
        for N in NCHK:
            r[f'err{N}_{c}'] = float(r[f'err{N}_{c}'])


def pj(r, c):
    return sum(abs(r[f'err{N}_{c}']) for N in NCHK) / 3


def J(rs, c, N=None):
    if not rs:
        return None
    if N is None:
        return sum(pj(r, c) for r in rs) / len(rs)
    return sum(abs(r[f'err{N}_{c}']) for r in rs) / len(rs)


def bias(rs, c, N=None):
    if not rs:
        return None
    ns = NCHK if N is None else [N]
    v = [r[f'err{n}_{c}'] for r in rs for n in ns]
    return sum(v) / len(v)


def sel(seasons, f=lambda p: True):
    return [r for r in rows if r['season'] in seasons and f(r['pick'])]


# train.csv
with open(HERE / 'train.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['candidate', 'shift', 'season', 'N', 'n', 'MAE', 'bias'])
    for c in CANDS:
        for s in TRAIN + TEST + REPORT + ['TRAIN', 'TEST']:
            ss = {'TRAIN': TRAIN, 'TEST': TEST}.get(s, [s])
            rs = sel(ss)
            for N in NCHK + ['J']:
                w.writerow([c, SHIFT[c], s, N, len(rs), J(rs, c, None if N == 'J' else N), bias(rs, c, None if N == 'J' else N)])

tr = sel(TRAIN)
jt = {c: J(tr, c) for c in SELECTABLE}
jmin = min(jt.values())
tied = [c for c in SELECTABLE if jt[c] - jmin < TIE]
s_star = min(tied, key=lambda c: SHIFT[c])

te = sel(TEST)
res = {'sStar': s_star, 'sStarShift': SHIFT[s_star], 'trainN': len(tr), 'testN': len(te),
       'trainJ': jt, 'tiedWithinThreshold': tied, 'tieThreshold': TIE}
res['trainJBySeason'] = {s: {c: J(sel([s]), c) for c in SELECTABLE} for s in TRAIN}
res['testJ'] = {c: J(te, c) for c in CANDS}
res['testJBySeason'] = {s: {c: J(sel([s]), c) for c in CANDS} for s in TEST}
res['testBias'] = {g: {c: bias(sel(TEST, fn), c) for c in CANDS} for g, fn in GROUPS.items()}
res['testJByGroup'] = {g: {c: J(sel(TEST, fn), c) for c in CANDS} for g, fn in GROUPS.items()}
res['testNByGroup'] = {g: len(sel(TEST, fn)) for g, fn in GROUPS.items()}
res['d3Report'] = {'n': len(sel(REPORT)), 'J': {c: J(sel(REPORT), c) for c in CANDS},
                   'bias': {g: {c: bias(sel(REPORT, fn), c) for c in CANDS} for g, fn in GROUPS.items()}}
res['trainBias'] = {g: {c: bias(sel(TRAIN, fn), c) for c in CANDS} for g, fn in GROUPS.items()}
res['testJByN'] = {str(N): {c: J(te, c, N) for c in CANDS} for N in NCHK}

if s_star != 'B0r':
    rng = np.random.default_rng(1)
    d = np.array([pj(r, s_star) - pj(r, 'B0r') for r in te])
    idx = rng.integers(0, len(d), size=(2000, len(d)))
    bs = d[idx].mean(axis=1)
    lo, hi = np.percentile(bs, [5, 95])
    diff = float(d.mean())
    o1 = bool(hi < 0)
    p110 = [r for r in te if r['pick'] <= 10]
    o2 = bool(J(p110, s_star) <= J(p110, 'B0r'))
    bd = bias(sel(TEST, GROUPS['pick31+andUndrafted']), s_star) - bias(sel(TEST, GROUPS['pick31+andUndrafted']), 'B0r')
    o3 = bool(bd <= 3.0)
    res['testDiff'] = {'J(s*)-J(B0r)': diff, 'ci90': [float(lo), float(hi)], 'bootstrap': {'resamples': 2000, 'seed': 1, 'unit': 'player'}}
    res['checks'] = {'1_upperBound<0': o1, '2_pick1-10_J_not_worse': o2, '2_detail': [J(p110, s_star), J(p110, 'B0r')],
                     '3_biasDiff31+<=3': o3, '3_detail': bd}
    res['verdict'] = '採用候選' if (o1 and o2 and o3) else '維持 −5'
else:
    res['testDiff'] = None
    res['checks'] = None
    res['verdict'] = '維持 −5'
# 測試季其他候選對 B0r 的差（只報告，不判定）
rep = {}
rng = np.random.default_rng(1)
for c in CANDS:
    if c == 'B0r':
        continue
    d = np.array([pj(r, c) - pj(r, 'B0r') for r in te])
    idx = rng.integers(0, len(d), size=(2000, len(d)))
    bs = d[idx].mean(axis=1)
    rep[c] = {'diff': float(d.mean()), 'ci90': [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]}
res['testOtherCandidatesVsB0r_reportOnly'] = rep
c0n = json.load(open(HERE / 'phase0.json', encoding='utf-8'))['c0n']
res['mode'] = '只報告' if (len(tr) < 60 or len(te) < 40) else '照預註冊判定'
if res['mode'] == '只報告':
    res['verdict'] = '只報告（人數不足）'
json.dump(res, open(HERE / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ['sStar', 'trainJ', 'testJ', 'testDiff', 'checks', 'verdict', 'mode']}, ensure_ascii=False, indent=1))
print('testBias', json.dumps(res['testBias'], indent=0))
print('trainBias', json.dumps(res['trainBias']['all']))
print('d3', json.dumps(res['d3Report']['J']))
