"""E-062 判定與報告（預註冊 §3）。輸出 backtest-e062/{verdict.json, cells.csv, tercile.csv, report.md 的數字}。"""
import csv
import json
from pathlib import Path

import numpy as np

PA = Path(__file__).resolve().parents[1] / 'pathA'
BASE = PA / 'backtest'
OUT = PA / 'backtest-e062'
NS = [3, 5, 10, 20]
PRIMARY = ['Y5', 'Y6']
SENS = ['Y3', 'D1', 'D2', 'D3']
STARTS = ['Y3', 'Y5', 'Y6', 'D1', 'D2', 'D3']


def rd(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def jl(p):
    return json.load(open(p, encoding='utf-8'))


def load(path, s):
    d = {}
    for r in rd(path / f'predictions-{s}.csv'):
        d[(int(r['N']), int(r['playerId']))] = {k: float(r[k]) for k in ('target', 'A', 'C4')}
    return d


def boot_pool(b, c, starts, rng_seed=1, B=2000):
    """配對 bootstrap：每次對每個起點抽球員（以該起點全部球員為母體，有放回），
    每格 MAE 以抽到次數加權；統計量 = starts × N=3/5/10/20 共 8 格 MAE 差的等權平均。"""
    rng = np.random.default_rng(rng_seed)
    prep = {}
    for s in starts:
        pids = sorted({p for (_, p) in b[s]})
        pos = {p: i for i, p in enumerate(pids)}
        cells = []
        for N in NS:
            ps = [p for p in pids if (N, p) in b[s]]
            idx = np.array([pos[p] for p in ps])
            eb = np.array([abs(b[s][(N, p)]['C4'] - b[s][(N, p)]['target']) for p in ps])
            ec = np.array([abs(c[s][(N, p)]['C4'] - c[s][(N, p)]['target']) for p in ps])
            cells.append((idx, ec - eb))
        prep[s] = (len(pids), cells)
    vals = np.zeros(B)
    for i in range(B):
        acc = []
        for s in starts:
            n, cells = prep[s]
            draw = rng.integers(0, n, size=n)
            cnt = np.bincount(draw, minlength=n)
            for idx, d in cells:
                w = cnt[idx]
                acc.append((w * d).sum() / w.sum())
        vals[i] = np.mean(acc)
    return float(np.quantile(vals, 0.05)), float(np.quantile(vals, 0.95)), float(vals.mean())


def main():
    base = {s: load(BASE, s) for s in STARTS}
    res = {}
    for m in ('C4s', 'C4r'):
        cand = {s: load(OUT / m, s) for s in STARTS}
        fit = jl(OUT / m / 'fit.json')
        rj = jl(OUT / m / 'results.json')
        g = rj['gates']['C4']
        r = {'c': {s: fit['selection'][s]['c'] for s in STARTS},
             'delta2': {s: fit['fit'][s]['delta2'] for s in STARTS},
             'fresh': rj['fresh'], 'gate1_main': g['main'], 'gate1_sens': g['sensitivityAllCandidates'],
             'gate1_secondaryD': g['secondaryD']}
        # 逐格 MAE
        cells = []
        for s in STARTS:
            for N in NS:
                keys = [k for k in base[s] if k[0] == N]
                eb = np.array([abs(base[s][k]['C4'] - base[s][k]['target']) for k in keys])
                ec = np.array([abs(cand[s][k]['C4'] - cand[s][k]['target']) for k in keys])
                cells.append({'start': s, 'N': N, 'n': len(keys), 'MAE_C4': eb.mean(), 'MAE_cand': ec.mean(),
                              'diff': ec.mean() - eb.mean()})
        r['cells'] = cells
        prim = [c for c in cells if c['start'] in PRIMARY]
        r['gate2'] = {'maxDiff': max(c['diff'] for c in prim), 'pass': all(c['diff'] <= 0.05 for c in prim)}
        lo, hi, mean = boot_pool(base, cand, PRIMARY)
        r['gate3'] = {'meanDiff8': float(np.mean([c['diff'] for c in prim])), 'ci90': [lo, hi], 'boot_mean': mean,
                      'pass': hi < 0}
        # 敏感度：同 (2)(3)，單起點
        sens = {}
        for s in SENS:
            cs = [c for c in cells if c['start'] == s]
            lo_s, hi_s, _ = boot_pool(base, cand, [s])
            sens[s] = {'maxDiff': max(c['diff'] for c in cs), 'gate2': all(c['diff'] <= 0.05 for c in cs),
                       'meanDiff4': float(np.mean([c['diff'] for c in cs])), 'ci90': [lo_s, hi_s],
                       'gate3': hi_s < 0}
        r['sensitivity'] = sens
        v1 = bool(g['main']['pass']) if g['main']['pass'] is not None else False
        r['gate1'] = v1
        r['verdict'] = ('變準' if (v1 and r['gate2']['pass'] and r['gate3']['pass']) else
                        '不比 C4 差' if (v1 and r['gate2']['pass']) else '不通過')
        # 三分位
        ter = []
        for s in STARTS:
            for N in (5, 10):
                keys = sorted(k for k in base[s] if k[0] == N)
                A = np.array([base[s][k]['A'] for k in keys])
                q1, q2 = np.quantile(A, [1 / 3, 2 / 3])
                grp = np.where(A <= q1, '低', np.where(A <= q2, '中', '高'))
                for gname in ('低', '中', '高'):
                    mk = grp == gname
                    row = {'start': s, 'N': N, 'tercile': gname, 'n': int(mk.sum())}
                    for nm, dd in (('C4', base), (m, cand)):
                        e = np.array([dd[s][k]['C4'] - dd[s][k]['target'] for k in keys])[mk]
                        row[f'bias_{nm}'] = float(e.mean())
                        row[f'MAE_{nm}'] = float(np.abs(e).mean())
                    ter.append(row)
        r['tercile'] = ter
        res[m] = r
    (OUT / 'verdict.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    for m, r in res.items():
        with open(OUT / f'cells-{m}.csv', 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(r['cells'][0]))
            w.writeheader()
            w.writerows([{k: (round(v, 6) if isinstance(v, float) else v) for k, v in c.items()} for c in r['cells']])
        with open(OUT / f'tercile-{m}.csv', 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(r['tercile'][0]))
            w.writeheader()
            w.writerows([{k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items()} for c in r['tercile']])
        print(m, r['verdict'], 'c', r['c'], 'g2', r['gate2'], 'g3', r['gate3'], 'g1', r['gate1'])


if __name__ == '__main__':
    main()
