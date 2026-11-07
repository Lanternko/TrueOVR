"""E-173 評估：預註冊 preregistration.md（凍結 sha 見 preregistration.sha256）。
卡片＝E-153 K6 歷史原點三季；答案＝E-126 下季 RAPM（net×W(mpg)、D）。S＝Spearman(屬性, 殘差)，三季人數加權，季內球員重抽。
用法（repo root）：python -I -B -X utf8 reports/E173-pressure-vs-rapm/e173_eval.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E142 = ROOT / 'reports/E142-card-target'
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
sys.path.insert(0, str(E142))
s = importlib.util.spec_from_file_location('pe', E142 / 'phase1_eval.py'); P = importlib.util.module_from_spec(s); s.loader.exec_module(P)
SEASONS = ['2022-23', '2023-24', '2024-25']
NEXT = {'2022-23': '2023-24', '2023-24': '2024-25', '2024-25': '2025-26'}
SEED, B = 20261101, 2000
ATTRS = ['pressure', 'onBall', 'help', 'drive']
EXAMPLES = ['Jalen Williams']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct(x):
    x = np.asarray(x, float)
    return rankdata(x) / len(x)


def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def season_data(t, rec_sha):
    f = E153 / 'work' / f'K6-{t}' / t / 'out/K0/ranking.csv'
    f0 = E153 / 'work' / f'K0h-{t}' / t / 'out/K0/ranking.csv'
    c0 = sha(f) == rec_sha[f'K6-{t}']
    pop, _ = P.pop_of(t)
    _, mp_next = P.pop_of(NEXT[t])
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)

    def load(path):
        m = {}
        for r in csv.DictReader(open(path, encoding='utf-8-sig')):
            if float(r['MIN']) < 500:
                continue
            ids = n2.get(P.norm(r['name'])) or []
            if len(ids) == 1:
                m[ids[0]] = r
        return m
    k6, k0 = load(f), load(f0)
    d = json.loads((E126 / f'rapm-{NEXT[t]}.json').read_text(encoding='utf-8'))
    assert d['season'] == NEXT[t]
    rv = {int(p): v for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mp_next}
    t6 = {}
    for r in csv.DictReader(open(E153 / 'work' / f'K6-{t}' / t / 'rapm-R.csv', encoding='utf-8-sig')):
        t6[int(r['playerId'])] = (float(r['pooledNet']), float(r['pooledD']))
    ids = sorted(p for p in set(k6) & set(k0) if p in rv)
    rows = [k6[p] for p in ids]
    out = {'ids': ids, 'names': [r['name'] for r in rows],
           'ovr': np.array([fnum(r['ovr']) for r in rows]), 'dbon': np.array([fnum(r['defenseBonus']) for r in rows]),
           'net': np.array([rv[p]['net'] * P.wfun(mp_next[p]) for p in ids]), 'D': np.array([rv[p]['D'] for p in ids]),
           't6net': np.array([t6.get(p, (np.nan, np.nan))[0] for p in ids]), 't6D': np.array([t6.get(p, (np.nan, np.nan))[1] for p in ids])}
    for a in ATTRS:
        out[a] = np.array([fnum(r[a]) for r in rows])
    n = len(ids)
    okc = int(np.sum(~np.isnan(out['pressure']) & ~np.isnan(out['dbon'])))
    out['checks'] = {'c0_sha': c0, 'sha': sha(f), 'n': n, 'nonnull_pressure_dbon': okc,
                     'c1': okc >= 0.95 * n, 'c2': n >= 150}
    return out


def resid(d, idx):
    e_net = pct(d['net'][idx]) - pct(d['ovr'][idx])
    e_D = pct(d['D'][idx]) - pct(d['dbon'][idx])
    return e_net, e_D


def stats(d, idx):
    e_net, e_D = resid(d, idx)
    o = {}
    for a in ATTRS:
        x = d[a][idx]
        o[f'S_net_{a}'] = sp(x, e_net)
        o[f'S_D_{a}'] = sp(x, e_D)
    hi = d['pressure'][idx] >= 90
    o['T_D'] = float(e_D[hi].mean() - e_D[~hi].mean()) if hi.any() and (~hi).any() else np.nan
    o['T_net'] = float(e_net[hi].mean() - e_net[~hi].mean()) if hi.any() and (~hi).any() else np.nan
    return o


def insample(d):
    ok = ~np.isnan(d['t6net'])
    idx = np.where(ok)[0]
    e_net = pct(d['t6net'][idx]) - pct(d['ovr'][idx])
    e_D = pct(d['t6D'][idx]) - pct(d['dbon'][idx])
    return {'n': int(len(idx)), 'S_net_pressure': sp(d['pressure'][idx], e_net), 'S_D_pressure': sp(d['pressure'][idx], e_D)}


def main():
    rec = json.loads((E153 / 'results.json').read_text(encoding='utf-8'))['checks']['rank_sha256']
    data = {t: season_data(t, rec) for t in SEASONS}
    checks = {t: data[t]['checks'] for t in SEASONS}
    pre_ok = all(c['c0_sha'] and c['c1'] and c['c2'] for c in checks.values())
    res = {'prereg_sha256': sha(HERE / 'preregistration.md'), 'seed': SEED, 'draws': B, 'checks': checks, 'preconditions_pass': pre_ok}
    if not pre_ok:
        res['verdict'] = 'stopped_at_preconditions'
        (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
        print(json.dumps(checks, ensure_ascii=False))
        return
    ns = {t: len(data[t]['ids']) for t in SEASONS}
    wts = {t: ns[t] / sum(ns.values()) for t in SEASONS}
    per = {t: stats(data[t], np.arange(ns[t])) for t in SEASONS}
    keys = list(per[SEASONS[0]])

    def pooled(st):
        return {k: float(sum(wts[t] * st[t][k] for t in SEASONS)) for k in keys}
    point = pooled(per)
    rng = np.random.default_rng(SEED)
    draws = {k: [] for k in keys}
    for _ in range(B):
        st = {t: stats(data[t], rng.integers(0, ns[t], ns[t])) for t in SEASONS}
        for k, v in pooled(st).items():
            draws[k].append(v)
    ci = {k: [float(np.nanpercentile(v, 5)), float(np.nanpercentile(v, 95))] for k, v in draws.items()}
    sn, sd = ci['S_net_pressure'], ci['S_D_pressure']
    if sn[1] < 0 and sd[1] < 0:
        verdict = 'pressure_overrated'
    elif sn[0] > 0 and sd[0] > 0:
        verdict = 'pressure_underrated'
    else:
        verdict = 'no_systematic_bias'
    ex = []
    allrows = []
    for t in SEASONS:
        d = data[t]
        e_net, e_D = resid(d, np.arange(ns[t]))
        for i, nm in enumerate(d['names']):
            row = {'season': t, 'name': nm, 'pressure': float(d['pressure'][i]), 'ovrPct': float(pct(d['ovr'])[i]),
                   'netPct': float(pct(d['net'])[i]), 'e_net': float(e_net[i]), 'e_D': float(e_D[i])}
            allrows.append(row)
            if nm in EXAMPLES:
                ex.append(row)
    top = sorted(allrows, key=lambda r: -r['pressure'])[:10]
    res.update({'n': ns, 'per_season': per, 'pooled': point, 'ci90': ci, 'verdict': verdict,
                'insample_T6_report_only': {t: insample(data[t]) for t in SEASONS},
                'examples': ex, 'top10_pressure': top})
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print('verdict', verdict)
    for k in keys:
        print(f'{k:18s} {point[k]:+.3f} [{ci[k][0]:+.3f}, {ci[k][1]:+.3f}]  ' + ' '.join(f'{t}:{per[t][k]:+.3f}' for t in SEASONS))
    print('n', ns)


if __name__ == '__main__':
    main()
