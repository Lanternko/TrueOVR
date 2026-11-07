"""舊答案（v4）在 N=82 的 A/B/C3，用來和 v5 並列、檢查 §R.5 的「B 第 82 場下限」。

v4 的 backtest_v4.py 只算 N=3/5/10/20，沒有 N=82。這支程式用**完全不覆寫**的
v4_common / v4 卡 / v4 RAPM 重算 N=82；同時重算 N=20 和 v4/backtest/results.csv 對照，
確認同一支計算流程沒有走鐘。N=82 的 w、λ 照 §3.1 的 λ_82=λ_20，w 也用 N=20
（v4 沒有 N=82 的 w）。輸出 v5/backtest/legacy-v4-n82.json。
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'v4' / 'tools'))
import v4_common as C  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402

STARTS = ['D1', 'D2', 'D3']


def metrics(pred, tgt, P):
    e = [pred[p]['ovr'] - tgt[p] for p in P]
    a = [abs(x) for x in e]
    return {'P': len(P), 'medianAbs': round(float(np.median(a)), 6),
            'MAE': round(float(np.mean(a)), 6),
            'signedMedian': round(float(np.median(e)), 6),
            'gt10': int(sum(1 for x in a if x > 10))}


def main():
    grid = C.load_json(C.V4_FIT / 'w-grid.json')
    lam = C.load_json(C.V4_FIT / 'lambda.json')['lambda']
    wg = {s: {a: {N: grid['w'][s]['attrs'][a]['w'][str(min(N, 20))] for N in (20, 82)}
              for a in C.UPD} for s in STARTS}
    v4res = {r['start'] + '|' + r['N']: r for r in
             C.load_csv(C.V4_BACKTEST / 'results.csv')}
    out = {'spec': '舊答案（v4 卡 / v4 RAPM / v4 prior）', 'cells': {}}
    checks = {}
    for start in STARTS:
        pipe = C.pipeline_for(start)
        cards, x0 = C.deployment(start)
        tgt = F.target_ovr(start)
        for N in (20, 82):
            attrs = {'A': {p: {a: float(c[a]) for a in C.ATTRS} for p, c in cards.items()},
                     'B': F.raw_predict(start, N),
                     'C3': F.c1_predict(start, N, wg[start], lam[start]['20'])}
            preds = {k: pipe.predict(v) for k, v in attrs.items()}
            P = [p for p in C.population(C.CHAIN[start]['prior'], N) if p in tgt]
            rec = {k: metrics(preds[k], tgt, P) for k in ('A', 'B', 'C3')}
            out['cells'][f'{start}|{N}'] = rec
            if N == 20:
                v = v4res[f'{start}|20']
                checks[start] = {
                    'medianAbsA': [rec['A']['medianAbs'], float(v['medianA'])],
                    'medianAbsB': [rec['B']['medianAbs'], float(v['medianB'])],
                    'medianAbsC3': [rec['C3']['medianAbs'], float(v['medianC3'])],
                    'MAEA': [rec['A']['MAE'], float(v['meanA'])],
                    'MAEB': [rec['B']['MAE'], float(v['meanB'])],
                    'MAEC3': [rec['C3']['MAE'], float(v['meanC3'])],
                    'P': [rec['A']['P'], int(v['P'])],
                }
    out['reproducesV4ResultsN20'] = {
        'checks': checks,
        'maxAbsDiff': round(max(abs(a - b) for c in checks.values() for pair in c.values()
                                for a, b in [pair]), 9),
    }
    out['reproducesV4ResultsN20']['pass'] = out['reproducesV4ResultsN20']['maxAbsDiff'] < 1e-6
    C.write_json(C.REPORT / 'v5' / 'backtest' / 'legacy-v4-n82.json', out)
    print(json.dumps({'reproN20': out['reproducesV4ResultsN20']['pass'],
                      'maxAbsDiff': out['reproducesV4ResultsN20']['maxAbsDiff'],
                      'n82': {k: {m: v['C3'][m] for m in ('P', 'MAE', 'medianAbs', 'gt10')}
                              for k, v in out['cells'].items() if k.endswith('|82')}},
                     ensure_ascii=False, indent=1))
    return 0 if out['reproducesV4ResultsN20']['pass'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
