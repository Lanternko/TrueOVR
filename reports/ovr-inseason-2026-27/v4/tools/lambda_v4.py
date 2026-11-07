"""P4：λ(N) 選擇（preregistration-v4 §2.3）。

  J_{s,N}(λ) = median{ |OVR_C3(h,N,λ)_i − OVR_T(h)_i| : h ∈ E(s,N), i ∈ Pop(h,N) }
  λ*(s,N) = argmin_λ J；平手（差 <=1e-9）取較小的 λ。
  E(D2)={D1}、E(D3)={D1,D2}、E(S*)={D1,D2,D3}；D1 不判定、λ(D1,N)=1；W 不進 E。
輸出 v4/fit/lambda.json（逐 E、逐 λ 的 J 全列出）。
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
import fit_w_grid_v4 as F

TIE = 1e-9


def wgrid_of(grid, start):
    return {a: {N: grid['w'][start]['attrs'][a]['w'][str(N)] for N in C.N_LIST} for a in C.UPD}


def ovr_c3(start, N, lam, wgrid):
    return C.pipeline_for(start).predict(F.c1_predict(start, N, wgrid, lam))


def ovr_c3_vec(start, N, lam, wgrid, pids):
    pred = ovr_c3(start, N, lam, wgrid)
    return np.array([pred[p]['ovr'] for p in pids], float)


def main():
    grid = C.load_json(C.V4_FIT / 'w-grid.json')
    wg = {s: wgrid_of(grid, s) for s in C.HIST}
    tgt = {s: F.target_ovr(s) for s in C.HIST}

    lam = {'D1': {str(N): 1.0 for N in C.N_LIST}, 'W': {str(N): 1.0 for N in C.N_LIST}}
    detail = {}
    for s in ['D2', 'D3', 'S*']:
        E = C.candidates(s)
        detail[s] = {'E': E, 'per': {}}
        for N in C.N_LIST:
            pools = {}
            for h in E:
                P = [p for p in C.population(C.CHAIN[h]['prior'], N) if p in tgt[h]]
                pools[h] = P
            # 每個 h、每個 λ 的 OVR（h 自己的 w、自己的 x0/y，只換 λ）
            cache = {h: {l: ovr_c3_vec(h, N, l, wg[h], pools[h]) for l in C.LAMBDA_GRID} for h in E}
            jvals = {}
            for l in C.LAMBDA_GRID:
                errs = []
                for h in E:
                    errs.extend(np.abs(cache[h][l] - np.array([tgt[h][p] for p in pools[h]])))
                jvals[f'{l:.2f}'] = float(np.median(errs)) if errs else None
                # round 供比較用（避免浮點噪音）
            best = None
            for l in C.LAMBDA_GRID:
                v = jvals[f'{l:.2f}']
                if v is None:
                    continue
                if best is None or v < best[0] - TIE:
                    best = (v, l)
            lam[s] = lam.get(s, {})
            lam[s][str(N)] = float(best[1]) if best else None
            detail[s]['per'][str(N)] = {
                'E': E,
                'pools': {h: len(pools[h]) for h in E},
                'pooledPlayers': int(sum(len(pools[h]) for h in E)),
                'J': {k: (None if v is None else round(v, 6)) for k, v in jvals.items()},
                'best': None if best is None else {'lambda': float(best[1]),
                                                   'J': round(best[0], 6)},
                'tied': None if best is None else [l for l in C.LAMBDA_GRID
                                                   if abs(jvals[f'{l:.2f}'] - best[0]) <= TIE],
            }
            print(json.dumps({'start': s, 'N': N, 'E': E,
                              'pooledPlayers': detail[s]['per'][str(N)]['pooledPlayers'],
                              'lambda': lam[s][str(N)], 'J': best[0] if best else None},
                             ensure_ascii=False), flush=True)

    out = {
        'spec': 'preregistration-v4 §2.3 / P4',
        'grid': C.LAMBDA_GRID,
        'nList': C.N_LIST,
        'tieRule': 'J 差 <=1e-9 視為平手，取較小的 λ',
        'judged': ['D2', 'D3'],
        'fixed': {'D1': 1.0, 'W': 1.0,
                  'note': 'D1 沒有更早的 RAPM-一致起點 → λ=1（§2.3）；W 的 w 全為 0，λ 不影響 C3=A'},
        'lambda': {s: lam[s] for s in ['W', 'D1', 'D2', 'D3', 'S*']},
        'detail': detail,
        'nonMonotone': {s: [lam[s][str(N)] for N in C.N_LIST] for s in ['D1', 'D2', 'D3', 'S*']},
    }
    C.write_json(C.V4_FIT / 'lambda.json', out)
    print(json.dumps({'lambda': out['lambda']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
