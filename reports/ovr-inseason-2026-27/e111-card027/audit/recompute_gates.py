"""E-111 稽核：獨立重算 (1)(2)。只讀 predictions-027.csv 與 E-095 predictions-sat15.csv。"""
import csv
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
E111 = HERE.parent
E095 = E111.parent / 'e095-card025-minutes'
BOOT = 2000
NL = [3, 5, 10, 20, 82]


def load(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


c = load(E111 / 'predictions-027.csv')
b = load(E095 / 'predictions-sat15.csv')
order = []
for r in b:
    if r['start'] not in order:
        order.append(r['start'])
cell = {}
for r in c:
    cell.setdefault((r['start'], int(r['N'])), []).append(r)
base = {(r['start'], int(r['N']), r['playerId']): r for r in b}
n095 = {}
for r in b:
    k = (r['start'], int(r['N']))
    n095[k] = n095.get(k, 0) + 1
out = {'checks': {}}
E = {}
for k, rs in cell.items():
    P = [r['playerId'] for r in rs]
    assert len(P) == len(set(P)) == n095[k], k
    assert set(P) == {p for (s, N, p) in base if (s, N) == k}, k
    tg = np.array([float(r['targetRepl027']) for r in rs])
    rg = np.array([float(r['RG1_027']) for r in rs])
    ra = np.array([float(r['RA027']) for r in rs])
    eC = rg - tg
    eA = ra - tg
    out['checks'][f'{k}'] = float(np.max(np.abs(eC - np.array([float(r['errRG1_027']) for r in rs]))))
    bs = [base[(k[0], k[1], p)] for p in P]
    eB = np.array([float(x['RG1']) - float(x['targetRepl']) for x in bs])
    out['checks'][f'{k}-base'] = float(np.max(np.abs(eB - np.array([float(r['errRG1_sat15']) for r in rs]))))
    tB = np.array([float(x['targetRepl']) for x in bs])
    rgB = np.array([float(x['RG1']) for x in bs])
    E[k] = dict(eC=eC, eA=eA, eB=eB, tg=tg, rg=rg, ra=ra, tB=tB, rgB=rgB)


def gate(starts, seed, mimic):
    rng = np.random.default_rng(seed)
    Tb, res = {}, {}
    seq = [(s, N) for s in order for N in NL] if mimic else [(s, N) for s in starts for N in NL]
    for k in seq:
        if k not in E:
            n = n095[k]
            rng.integers(0, n, size=(BOOT, n))
            continue
        eA, eC = E[k]['eA'], E[k]['eC']
        n = len(eA)
        idx = rng.integers(0, n, size=(BOOT, n))
        T = np.median(eC[idx], 1) - np.median(eA[idx], 1)
        dM = np.abs(eC[idx]).mean(1) - np.abs(eA[idx]).mean(1)
        Tb[k] = T
        res[k] = dict(T=float(np.median(eC) - np.median(eA)), dMAE=float(np.abs(eC).mean() - np.abs(eA).mean()),
                      gt10C=int((np.abs(eC) > 10).sum()), gt10A=int((np.abs(eA) > 10).sum()),
                      dMAE_lo=float(np.quantile(dM, .025)), dMAE_hi=float(np.quantile(dM, .975)))
    g = {'V1': {}, 'V2': {}}
    for N in (3, 5):
        U = float(np.quantile(np.mean([Tb[(s, N)] for s in starts], 0), .975))
        Ts = {s: res[(s, N)]['T'] for s in starts}
        g['V1'][N] = dict(U=U, Ts=Ts, ok=bool(U <= .5 and all(t <= .25 for t in Ts.values())))
    for N in (10, 20):
        cs = {s: dict(res[(s, N)], ok=bool(res[(s, N)]['dMAE'] < 0 and res[(s, N)]['gt10C'] <= res[(s, N)]['gt10A']))
              for s in starts}
        g['V2'][N] = dict(cells=cs, ok=all(x['ok'] for x in cs.values()))
    g['pass'] = all(v['ok'] for v in g['V1'].values()) and all(v['ok'] for v in g['V2'].values())
    g['cells'] = {f'{k[0]}/N{k[1]}': v for k, v in res.items() if k[0] in starts}
    return g


SETS = (('main', ['Y5', 'Y6']), ('Y3', ['Y3']))
out['gate_mimicE095_SEEDGATE'] = {nm: gate(ss, 20261027, True) for nm, ss in SETS}
out['gate_seed1_ownorder'] = {nm: gate(ss, 1, False) for nm, ss in SETS}

cmp2 = {}
for s in ['Y5', 'Y6', 'Y3']:
    for N in (3, 5, 10, 20):
        e = E[(s, N)]
        m27, m15 = float(np.abs(e['eC']).mean()), float(np.abs(e['eB']).mean())
        sdT27, sdT15 = float(e['tg'].std()), float(e['tB'].std())
        r27 = float(np.corrcoef(e['rg'], e['tg'])[0, 1])
        r15 = float(np.corrcoef(e['rgB'], e['tB'])[0, 1])
        rgB_on27 = (e['rgB'] - e['tB'].mean()) / sdT15 * sdT27 + e['tg'].mean()
        rg27_onB = (e['rg'] - e['tg'].mean()) / sdT27 * sdT15 + e['tB'].mean()
        cmp2[f'{s}/N{N}'] = dict(
            n=len(e['eC']), MAE027=m27, MAEsat15=m15, diff=m27 - m15, ok=m27 - m15 <= .05,
            gt10_027=int((np.abs(e['eC']) > 10).sum()), gt10_sat15=int((np.abs(e['eB']) > 10).sum()),
            sdTarget027=sdT27, sdTargetE095=sdT15, meanTarget027=float(e['tg'].mean()), meanTargetE095=float(e['tB'].mean()),
            corrTargets=float(np.corrcoef(e['tg'], e['tB'])[0, 1]),
            corr027=r27, corrSat15=r15,
            corr_027pred_vs_E095ans=float(np.corrcoef(e['rg'], e['tB'])[0, 1]),
            corr_sat15pred_vs_027ans=float(np.corrcoef(e['rgB'], e['tg'])[0, 1]),
            MAEoverSD_027=m27 / sdT27, MAEoverSD_sat15=m15 / sdT15,
            common027ans_diff=m27 - float(np.abs(rgB_on27 - e['tg']).mean()),
            commonE095ans_diff=float(np.abs(rg27_onB - e['tB']).mean()) - m15)
out['cmp2'] = cmp2

rng = np.random.default_rng(1)
by_s = {}
for s in ['Y5', 'Y6']:
    pids = {N: [r['playerId'] for r in cell[(s, N)]] for N in (3, 5, 10, 20)}
    univ = sorted(set(p for v in pids.values() for p in v))
    pos = {p: i for i, p in enumerate(univ)}
    idx = rng.integers(0, len(univ), size=(BOOT, len(univ)))
    cnt = np.zeros((BOOT, len(univ)))
    for bb in range(BOOT):
        np.add.at(cnt[bb], idx[bb], 1)
    for N in (3, 5, 10, 20):
        ii = np.array([pos[p] for p in pids[N]])
        w = cnt[:, ii]
        d = np.abs(E[(s, N)]['eC']) - np.abs(E[(s, N)]['eB'])
        by_s[(s, N)] = (w * d).sum(1) / w.sum(1)
allc = np.mean(list(by_s.values()), 0)
pt = float(np.mean([cmp2[f'{s}/N{N}']['diff'] for s in ['Y5', 'Y6'] for N in (3, 5, 10, 20)]))
out['pooled8_seed1'] = dict(point=pt, ci90=[float(np.quantile(allc, .05)), float(np.quantile(allc, .95))])


def tj(o):
    if isinstance(o, dict):
        return {str(k): tj(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [tj(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (np.floating, float)):
        return round(float(o), 6)
    if isinstance(o, np.integer):
        return int(o)
    return o


(HERE / 'recompute_gates.json').write_text(json.dumps(tj(out), ensure_ascii=False, indent=1), encoding='utf-8')
print('maxcheck', max(out['checks'].values()), 'pooled', tj(out['pooled8_seed1']))
for k, v in cmp2.items():
    print(k, {a: (round(float(x), 3) if isinstance(x, float) else x) for a, x in v.items()})
for nm in ('gate_mimicE095_SEEDGATE', 'gate_seed1_ownorder'):
    for sn in ('main', 'Y3'):
        g = out[nm][sn]
        print(nm, sn, 'pass', g['pass'])
        print('  V1', {N: (round(v['U'], 4), {s: round(t, 4) for s, t in v['Ts'].items()}) for N, v in g['V1'].items()})
        print('  V2', {N: {s: (round(x['dMAE'], 4), x['gt10C'], x['gt10A'], round(x['dMAE_hi'], 4)) for s, x in v['cells'].items()}
                       for N, v in g['V2'].items()})
