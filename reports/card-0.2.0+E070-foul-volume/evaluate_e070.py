"""E-070 (c2)：E-064 §3.2 RAPM 分半。python -I evaluate_e070.py -> c2.json
答案 = RAPM_另一半 pooledNet * MPG_另一半；人群 pooledPoss>=2500 且兩半各>=5場；
統計 = ρ(候選 w075) - ρ(card 0.2.0 = w0) 兩方向平均，bootstrap 2000、seed 1、球員配對，90% CI 下界 > -0.02。
主指標 = repl（card 0.2.0 的每場 OVR 用 g_r）；game、ovr36 一併報告。possScale 0.5 為主、1.0 為敏感度。"""
import csv, json
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
V58 = ROOT / 'reports/ovr-v58-holdout-2025-26'
E064 = ROOT / 'reports/card-0.1.2+E064-pergame'
THR, MIN_G = 2500, 5
FROZEN = ['reports/ovr-calibrated-2025-26/ranking.csv', 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv',
          'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv', 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv',
          'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv']
read = lambda p: list(csv.DictReader(open(p, encoding='utf-8-sig')))
rho = lambda a, b: float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def load(tag, fit, suf):
    d = HERE / f'cards-{tag}' / (f'fit{fit}' + suf)
    return {r['name']: r for r in read(d / 'pred.csv')}, json.loads((d / 'pergame-summary.json').read_text(encoding='utf-8'))


def variants(tag, fit, suf):
    pr, sm = load(tag, fit, suf)
    pred = {n: float(r['pred']) for n, r in pr.items()}
    m = {n: (float(r['mpg']) if r['mpg'] != '' else 0.0) for n, r in pr.items()}
    rr = sm['rRepl_PR10_of_pred']
    return {'ovr36': pred, 'game': {n: pred[n] * m[n] / 36 for n in pred}, 'repl': {n: (pred[n] - rr) * m[n] / 36 for n in pred}}, set(pr)


def run(suf):
    rapm = {h: {r['name']: r for r in read(V58 / f'rapm-{h}.csv') if r['name']} for h in 'AB'}
    k2 = {r['name'] for r in read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    sets = [set(r['name'] for r in read(ROOT / p)) for p in FROZEN]
    for sc in ('0.5', '1.0'):
        for fit in 'AB':
            for k in ('E2', 'F2', 'G3', 'H1-m0'):
                sets.append(set(r['name'] for r in read(V58 / f'fit{fit}-scale{sc}' / k / 'ranking.csv')))
    common = set.intersection(*sets) & k2
    prim = {r['name']: r for r in read(HERE / 'cards-w075/primary/pred.csv')}
    V = {t: {f: variants(t, f, suf) for f in 'AB'} for t in ('w0', 'w075')}
    for t in V:
        for f in 'AB':
            common &= V[t][f][1]
    common &= set(prim)
    mpg = {h: {int(r['playerId']): (int(r['gp']), float(r['mpg'])) for r in read(E064 / f'mpg-{h}.csv')} for h in 'AB'}
    pid = {n: int(r['playerId']) for n, r in prim.items()}
    ok = lambda n: all(pid[n] in mpg[h] and mpg[h][pid[n]][0] >= MIN_G for h in 'AB')
    pools = {fit + ev: sorted(n for n in common if n in rapm[ev] and float(rapm[ev][n]['pooledPoss']) >= THR and ok(n))
             for fit, ev in (('A', 'B'), ('B', 'A'))}
    master = sorted(set(pools['AB']) | set(pools['BA']))
    keys = ['repl', 'game', 'ovr36']
    dirs = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        names = pools[fit + ev]
        d = {'names': names, 'ans': np.array([float(rapm[ev][n]['pooledNet']) * mpg[ev][pid[n]][1] for n in names])}
        for t in ('w0', 'w075'):
            for k in keys:
                d[t, k] = np.array([V[t][fit][0][k][n] for n in names])
        dirs[fit + ev] = d
    res = {dn: {t: {k: rho(d[t, k], d['ans']) for k in keys} for t in ('w0', 'w075')} for dn, d in dirs.items()}
    rng = np.random.default_rng(1)
    N = len(master)
    mp = {dn: np.array([{n: i for i, n in enumerate(d['names'])}.get(n, -1) for n in master]) for dn, d in dirs.items()}
    boot = {k: [] for k in keys}
    for _ in range(2000):
        idx = rng.integers(0, N, N)
        dl = {k: [] for k in keys}
        for dn, d in dirs.items():
            sel = mp[dn][idx]; sel = sel[sel >= 0]
            for k in keys:
                dl[k].append(rho(d['w075', k][sel], d['ans'][sel]) - rho(d['w0', k][sel], d['ans'][sel]))
        for k in keys:
            boot[k].append(float(np.mean(dl[k])))
    out = {'n': {dn: len(d['names']) for dn, d in dirs.items()}, 'unionN': N, 'rho': res}
    for k in keys:
        b = np.array(boot[k])
        out[k] = {'delta': float(np.mean([res[dn]['w075'][k] - res[dn]['w0'][k] for dn in dirs])),
                  'byDirection': {dn: res[dn]['w075'][k] - res[dn]['w0'][k] for dn in dirs},
                  'ci90': [float(np.percentile(b, 5)), float(np.percentile(b, 95))]}
        out[k]['pass'] = bool(out[k]['ci90'][0] > -0.02)
    return out


o = {'possScale0.5': run(''), 'possScale1.0': run('-scale1.0'), 'primaryVariant': 'repl', 'margin': -0.02, 'resamples': 2000, 'seed': 1}
o['c2'] = {'pass': o['possScale0.5']['repl']['pass'], 'delta': o['possScale0.5']['repl']['delta'], 'ci90': o['possScale0.5']['repl']['ci90']}
(HERE / 'c2.json').write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding='utf-8')
for s in ('possScale0.5', 'possScale1.0'):
    print(s, o[s]['n'], o[s]['unionN'])
    for k in ('repl', 'game', 'ovr36'):
        print(' ', k, round(o[s][k]['delta'], 4), [round(x, 4) for x in o[s][k]['ci90']], o[s][k]['pass'], {a: round(b, 4) for a, b in o[s][k]['byDirection'].items()})
