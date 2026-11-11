"""P6：經驗分位 80% 區間與覆蓋率（preregistration-v4 §4）。

r_{h,i} = OVR_C3(h,N,λ(h,N))_i − OVR_T(h)_i，h ∈ E(s,N)（嚴格更早的判定起點）
q10/q90 = numpy.quantile(r, [0.10,0.90], method='linear')
區間 = [pred_s − q90, pred_s − q10]
輸出：v4/intervals/<start>-N{N}.csv（逐球員）、v4/intervals/residuals-<start>-N{N}.csv（殘差池）、
      v4/coverage.csv（逐起點 + pooled；G4 兩條門檻）。
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C

JUDGED = ['D1', 'D2', 'D3']
PRED_STARTS = ['D2', 'D3']       # 只有它們有更早的判定起點可做殘差池
EPS = 1e-9


def preds(start, N):
    rows = C.load_csv(C.V4_BACKTEST / start / f'predictions-c3-N{N}.csv')
    return {int(r['playerId']): float(r['ovr']) for r in rows}


def targets(start):
    rows = C.load_csv(C.V4_BACKTEST / start / 'targets.csv')
    return {int(r['playerId']): (None if r['ovr_target'] in ('', 'None')
                                 else float(r['ovr_target'])) for r in rows}


def main():
    C.V4_INTERVALS.mkdir(parents=True, exist_ok=True)
    rows_cov, pool_rows = [], {}
    for s in PRED_STARTS:
        E = C.candidates(s)
        assert all(C.CHAIN[h]['judge'] for h in E), E
        assert s not in E and all(JUDGED.index(h) < JUDGED.index(s) for h in E), (s, E)
        for N in C.N_LIST:
            # 殘差池：只用嚴格更早的判定起點
            pool = []
            for h in E:
                assert h != s and JUDGED.index(h) < JUDGED.index(s)
                ph, th = preds(h, N), targets(h)
                P = [p for p in C.population(C.CHAIN[h]['prior'], N) if th.get(p) is not None]
                assert P, (h, N)
                pool.extend((h, p, ph[p] - th[p]) for p in P)
            r = np.array([v for _, _, v in pool], float)
            q10, q90 = (float(np.quantile(r, 0.10, method='linear')),
                        float(np.quantile(r, 0.90, method='linear')))
            C.write_csv(C.V4_INTERVALS / f'residuals-{s}-N{N}.csv',
                        [{'sourceStart': h, 'playerId': p, 'residual': round(v, 6)}
                         for h, p, v in pool],
                        head=['sourceStart', 'playerId', 'residual'])
            # 對 s 自己的預測套區間
            ps, ts = preds(s, N), targets(s)
            P = [p for p in C.population(C.CHAIN[s]['prior'], N) if ts.get(p) is not None]
            out = []
            for p in P:
                lo, hi = ps[p] - q90, ps[p] - q10
                out.append({'playerId': p, 'pred': round(ps[p], 4), 'target': round(ts[p], 4),
                            'lo': round(lo, 4), 'hi': round(hi, 4),
                            'width': round(hi - lo, 4),
                            'hit': int(lo - EPS <= ts[p] <= hi + EPS)})
            C.write_csv(C.V4_INTERVALS / f'intervals-{s}-N{N}.csv', out,
                        head=['playerId', 'pred', 'target', 'lo', 'hi', 'width', 'hit'])
            cov = float(np.mean([o['hit'] for o in out])) if out else None
            width = float(np.median([o['width'] for o in out])) if out else None
            rows_cov.append({'start': s, 'N': N, 'pooled': 'no', 'E': '+'.join(E),
                             'residualN': len(r), 'q10': round(q10, 6), 'q90': round(q90, 6),
                             'players': len(out), 'coverage': round(cov, 6),
                             'medianWidth': round(width, 6), 'hit': sum(o['hit'] for o in out)})
            pool_rows[(s, N)] = out
    # pooled（D2+D3）
    pooled = {}
    for N in C.N_LIST:
        allrows = [o for s in PRED_STARTS for o in pool_rows[(s, N)]]
        hits = sum(o['hit'] for o in allrows)
        cov = hits / len(allrows) if allrows else None
        width = float(np.median([o['width'] for o in allrows])) if allrows else None
        pooled[N] = {'coverage': round(cov, 6), 'medianWidth': round(width, 6),
                     'players': len(allrows), 'hit': hits}
        rows_cov.append({'start': 'D2+D3', 'N': N, 'pooled': 'yes', 'E': 'D1+..',
                         'residualN': '', 'q10': '', 'q90': '', 'players': len(allrows),
                         'coverage': round(cov, 6), 'medianWidth': round(width, 6), 'hit': hits})
    g4 = {
        'pooledCoverageIn070_095': {N: bool(0.70 <= pooled[N]['coverage'] <= 0.95)
                                    for N in (10, 20)},
        'medianWidthLe25': {N: bool(pooled[N]['medianWidth'] <= 25.0) for N in (10, 20)},
        'pooled': pooled,
    }
    g4['pass'] = bool(all(g4['pooledCoverageIn070_095'].values())
                      and all(g4['medianWidthLe25'].values()))
    C.write_csv(C.V4 / 'coverage.csv', rows_cov,
                head=['start', 'N', 'pooled', 'E', 'residualN', 'q10', 'q90', 'players',
                      'coverage', 'medianWidth', 'hit'])
    C.write_json(C.V4 / 'intervals' / 'g4.json',
                 {'spec': 'preregistration-v4 §4.2 / P6', **g4})
    print(json.dumps({'pooled': pooled, 'g4': {k: g4[k] for k in
                                               ('pooledCoverageIn070_095', 'medianWidthLe25', 'pass')},
                      'perStart': [r for r in rows_cov if r['pooled'] == 'no']},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
