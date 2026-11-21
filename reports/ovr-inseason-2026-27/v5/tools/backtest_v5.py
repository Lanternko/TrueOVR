"""§R.4：v5 的 A / B / C3 回測（D1..D3 × N=3/5/10/20/82）。

定義照 v4/tools/backtest_v4.py 與 preregistration-v5 §2：
  A  = x0（v5 prior 的部署卡）
  B  = y_adj（未達最低樣本者用 x0）
  C3 = x0 + λ_s(N)·w_s(N)·(y_adj − x0)，λ/w 沿用 v4 的選擇（不重挑）
指標：中位誤差（絕對值與帶號）、>10 分人數、MAE、80% 區間命中（D2/D3）、
      T = median(e_C3) − median(e_A) 與 dMAE 的配對 bootstrap（B=2000, seed=20261027）。
舊答案（v4）並列：N=3/5/10/20 讀 v4/backtest/results.csv；N=82 讀 legacy-v4-n82.json。
輸出 v5/backtest/results.csv、results.json、<start>/predictions-*.csv、coverage.csv。
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'v4' / 'tools'))
sys.path.insert(0, str(HERE))
import v4_common as C  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402
import v5_common as V  # noqa: E402

SEED = 20261027
BOOT = 2000


def metrics(pred, tgt, P):
    e = np.array([pred[p]['ovr'] - tgt[p] for p in P], float)
    a = np.abs(e)
    return {'P': len(P), 'medianAbs': float(np.median(a)), 'MAE': float(np.mean(a)),
            'signedMedian': float(np.median(e)), 'gt10': int(sum(a > 10)),
            '_e': e}


def boot_cell(rng, eA, eC):
    n = len(eA)
    idx = rng.integers(0, n, size=(BOOT, n))
    T = np.median(eC[idx], axis=1) - np.median(eA[idx], axis=1)
    dM = np.abs(eC[idx]).mean(axis=1) - np.abs(eA[idx]).mean(axis=1)
    q = lambda x, p: float(np.quantile(x, p, method='linear'))
    return {'T_lo': q(T, 0.025), 'T_hi': q(T, 0.975),
            'T_mean': float(np.mean(T)),
            'dMAE_lo': q(dM, 0.025), 'dMAE_hi': q(dM, 0.975),
            'dMAE_mean': float(np.mean(dM))}


def main():
    V.V5_BACKTEST.mkdir(parents=True, exist_ok=True)
    grid = C.load_json(C.V4_FIT / 'w-grid.json')
    lam = C.load_json(C.V4_FIT / 'lambda.json')['lambda']
    wg = V.wgrid_from(grid)
    legacy = C.load_json(V.V5_BACKTEST / 'legacy-v4-n82.json')['cells']
    v4res = {r['start'] + '|' + r['N']: r for r in C.load_csv(C.V4_BACKTEST / 'results.csv')}
    rng = np.random.default_rng(SEED)

    preds, targets, attrs_store = {}, {}, {}
    results = []
    for start in V.STARTS:
        outdir = V.V5_BACKTEST / start
        outdir.mkdir(parents=True, exist_ok=True)
        pipe = C.pipeline_for(start)
        cards, x0 = C.deployment(start)
        tgt = V.target_ovr(start)
        targets[start] = tgt
        predA = pipe.predict({p: {a: float(c[a]) for a in C.ATTRS} for p, c in cards.items()})
        preds[(start, 'A')] = predA
        C.write_csv(outdir / 'targets.csv',
                    [{'playerId': p, 'name': c.get('name', ''), 'pos': c['pos'],
                      'MIN_prior': round(float(c['observed']['MIN']), 1),
                      'ovr_target': tgt.get(p)} for p, c in sorted(cards.items())],
                    head=['playerId', 'name', 'pos', 'MIN_prior', 'ovr_target'])
        for N in V.N_LIST:
            attrs = {'B': F.raw_predict(start, N),
                     'C3': F.c1_predict(start, N, wg[start], V.lam_for(lam, start, N))}
            for key, a in attrs.items():
                preds[(start, key, N)] = pipe.predict(a)
                attrs_store[(start, key, N)] = a
            C.write_csv(outdir / f'predictions-a-N{N}.csv',
                        [{'playerId': p, 'name': c.get('name', ''), 'pos': c['pos'],
                          'MIN_prior': round(float(c['observed']['MIN']), 1),
                          'ovr': round(predA[p]['ovr'], 4)} for p, c in sorted(cards.items())],
                        head=['playerId', 'name', 'pos', 'MIN_prior', 'ovr'])
            for key, tag in (('B', 'b'), ('C3', 'c3')):
                C.write_csv(outdir / f'predictions-{tag}-N{N}.csv',
                            [{'playerId': p, 'name': c.get('name', ''), 'pos': c['pos'],
                              'MIN_prior': round(float(c['observed']['MIN']), 1),
                              'ovr': round(preds[(start, key, N)][p]['ovr'], 4)}
                             for p, c in sorted(cards.items())],
                            head=['playerId', 'name', 'pos', 'MIN_prior', 'ovr'])
        files = sorted(f for f in outdir.glob('*.csv'))
        (outdir / 'sha256.txt').write_text(
            '\n'.join(f'{f.name} {C.sha256_file(f)}' for f in files) + '\n', encoding='utf-8')

    # 逐格指標（順序固定：D1→D2→D3、N 由小到大，bootstrap 共用一個 rng）
    cover_rows = []
    for start in V.STARTS:
        P_by_N = {}
        for N in V.N_LIST:
            P = [p for p in C.population(C.CHAIN[start]['prior'], N) if p in targets[start]]
            P_by_N[N] = P
            rec = {'start': start, 'N': N, 'judge': C.CHAIN[start]['judge'], 'P': len(P)}
            m = {k: metrics(preds[(start, k, N)] if k != 'A' else preds[(start, 'A')],
                            targets[start], P) for k in ('A', 'B', 'C3')}
            for k, v in m.items():
                rec[f'medianAbs{k}'] = round(v['medianAbs'], 6)
                rec[f'MAE_{k}'] = round(v['MAE'], 6)
                rec[f'signedMedian{k}'] = round(v['signedMedian'], 6)
                rec[f'gt10{k}'] = v['gt10']
            rec['T_C3minusA'] = round(m['C3']['signedMedian'] - m['A']['signedMedian'], 6)
            rec['dMAE_C3minusA'] = round(m['C3']['MAE'] - m['A']['MAE'], 6)
            b = boot_cell(rng, m['A']['_e'], m['C3']['_e'])
            rec.update({k: round(v, 6) for k, v in b.items()})
            # 舊答案（v4）
            if N == 82:
                old = legacy[f'{start}|82']
                for k, tag in (('A', 'A'), ('B', 'B'), ('C3', 'C3')):
                    rec[f'oldMedianAbs{k}'] = round(old[k]['medianAbs'], 6)
                    rec[f'oldMAE{k}'] = round(old[k]['MAE'], 6)
                    rec[f'oldGt10{k}'] = old[k]['gt10']
                rec['oldP'] = old['A']['P']
            else:
                old = v4res[f'{start}|{N}']
                rec['oldMedianAbsA'] = float(old['medianA'])
                rec['oldMedianAbsB'] = float(old['medianB'])
                rec['oldMedianAbsC3'] = float(old['medianC3'])
                rec['oldMAEA'] = float(old['meanA'])
                rec['oldMAEB'] = float(old['meanB'])
                rec['oldMAEC3'] = float(old['meanC3'])
                rec['oldGt10A'] = int(old['gt10A'])
                rec['oldGt10B'] = int(old['gt10B'])
                rec['oldGt10C3'] = int(old['gt10C3'])
                rec['oldP'] = int(old['P'])
            results.append(rec)

        # 80% 區間（只用嚴格更早的判定起點；D1 沒有 E）
        E = C.candidates(start)
        for N in V.N_LIST:
            if not E:
                continue
            pool = []
            for h in E:
                Ph = [p for p in C.population(C.CHAIN[h]['prior'], N)
                      if p in targets[h]]
                for p in Ph:
                    pool.append(preds[(h, 'C3', N)][p]['ovr'] - targets[h][p])
            r = np.array(pool, float)
            q10, q90 = (float(np.quantile(r, 0.10, method='linear')),
                        float(np.quantile(r, 0.90, method='linear')))
            rows = []
            for p in P_by_N[N]:
                lo, hi = preds[(start, 'C3', N)][p]['ovr'] - q90, preds[(start, 'C3', N)][p]['ovr'] - q10
                rows.append({'playerId': p, 'pred': preds[(start, 'C3', N)][p]['ovr'],
                             'target': targets[start][p], 'lo': lo, 'hi': hi,
                             'width': hi - lo, 'hit': int(lo - 1e-9 <= targets[start][p] <= hi + 1e-9)})
            C.write_csv(V.V5_BACKTEST / f'intervals-{start}-N{N}.csv', rows,
                        head=['playerId', 'pred', 'target', 'lo', 'hi', 'width', 'hit'])
            cover_rows.append({'start': start, 'N': N, 'E': '+'.join(E),
                               'residualN': len(r), 'q10': round(q10, 6), 'q90': round(q90, 6),
                               'players': len(rows),
                               'coverage': round(float(np.mean([o['hit'] for o in rows])), 6),
                               'medianWidth': round(float(np.median([o['width'] for o in rows])), 6),
                               'hit': int(sum(o['hit'] for o in rows))})

    head = ['start', 'N', 'judge', 'P', 'medianAbsA', 'medianAbsB', 'medianAbsC3',
            'signedMedianA', 'signedMedianB', 'signedMedianC3', 'T_C3minusA',
            'MAE_A', 'MAE_B', 'MAE_C3', 'dMAE_C3minusA',
            'gt10A', 'gt10B', 'gt10C3', 'T_lo', 'T_hi', 'T_mean',
            'dMAE_lo', 'dMAE_hi', 'dMAE_mean',
            'oldMedianAbsA', 'oldMedianAbsB', 'oldMedianAbsC3',
            'oldMAEA', 'oldMAEB', 'oldMAEC3', 'oldGt10A', 'oldGt10B', 'oldGt10C3', 'oldP']
    C.write_csv(V.V5_BACKTEST / 'results.csv', results, head=head)
    C.write_csv(V.V5_BACKTEST / 'coverage.csv', cover_rows,
                head=['start', 'N', 'E', 'residualN', 'q10', 'q90', 'players',
                      'coverage', 'medianWidth', 'hit'])

    # 閘門判定（V1/V2 沒有新鮮起點 → 從缺；V3 只報告）
    gates = {}
    for N in (10, 20):
        for start in V.STARTS:
            r = next(x for x in results if x['start'] == start and x['N'] == N)
            gates[f'V2|{start}|N{N}'] = {
                'pass': bool(r['dMAE_C3minusA'] < 0 and r['gt10C3'] <= r['gt10A']),
                'dMAE': r['dMAE_C3minusA'], 'gt10C': r['gt10C3'], 'gt10A': r['gt10A'],
                'note': 'V3 診斷（D1–D3 已看過，不當閘門）'}
    for N in (3, 5):
        for start in V.STARTS:
            r = next(x for x in results if x['start'] == start and x['N'] == N)
            gates[f'V1|{start}|N{N}'] = {
                'pass': bool(r['T_C3minusA'] <= 0.25 and r['T_hi'] <= 0.50),
                'T': r['T_C3minusA'], 'T_hi': r['T_hi'],
                'note': 'V3 診斷（D1–D3 已看過，不當閘門）'}
    # §R.5：D1/D2 在 N=10/20 的 MAE 改善是否 >1.5 分（需查洩漏）；B 的 N=82 下限
    r5 = {'improvements': {}, 'leakSuspects': [], 'bFloor82': {}}
    for start in ('D1', 'D2'):
        for N in (10, 20):
            r = next(x for x in results if x['start'] == start and x['N'] == N)
            new = r['MAE_A'] - r['MAE_C3']
            old = r['oldMAEA'] - r['oldMAEC3']
            r5['improvements'][f'{start}|N{N}'] = {
                'new': round(new, 6), 'old': round(old, 6),
                'exceeds1.5': bool(new > 1.5)}
            if new > 1.5:
                r5['leakSuspects'].append(f'{start}|N{N}')
    for start in V.STARTS:
        r = next(x for x in results if x['start'] == start and x['N'] == 82)
        r5['bFloor82'][start] = {
            'newMAE': r['MAE_B'], 'oldMAE': r['oldMAEB'],
            'delta': round(r['MAE_B'] - r['oldMAEB'], 6),
            'rises': bool(r['MAE_B'] > r['oldMAEB'])}
    r5['verdict'] = ('沒有 >1.5 的格；不需查洩漏。B 的 N=82 下限沒有上升（見 bFloor82）。'
                     if not r5['leakSuspects'] else
                     '有格 >1.5，需查洩漏；候選原因見 README。')

    summary = {
        'spec': 'preregistration-v5 §R.4（D1–D3 次要；Path B 無新鮮主判定）',
        'r5': r5,
        'seed': SEED, 'boot': BOOT, 'nList': V.N_LIST,
        'lambda': {s: {str(N): V.lam_for(lam, s, N) for N in V.N_LIST} for s in V.STARTS},
        'chain': V.CHAIN_V5,
        'files': V.rapm_files(),
        'params': {'wLambda': 'v4/fit/w-grid.json、v4/fit/lambda.json（不重挑）',
                   'N82': 'λ_82=λ_20、w_82=w_20（§3.1；v4 沒有 N=82 的 w）'},
        'priors': {s: {'file': V.PRIOR_PATH_V5[s].relative_to(C.ROOT).as_posix(),
                       'sha256': C.sha256_file(V.PRIOR_PATH_V5[s])}
                   for s in C.SEASONS},
        'gates': gates,
        'gateVerdict': {
            'V1': '從缺（Path B 沒有新鮮主判定起點；D1–D3 只能診斷）',
            'V2': '從缺（同上）',
            'V3': '只報告（D1–D3 已看過）',
            'V4': '本次沒有新建目標季卡；D1/D2 -min 卡的建卡檢查見 cards/*.json',
            'V5': '本回測無 2026-27 資料、預測 RAPM 最大季 < 目標季；重跑 SHA 一致',
            'V6': '未執行（不得讀 2026-27）',
        },
        'results': results, 'coverage': cover_rows,
    }
    C.write_json(V.V5_BACKTEST / 'results.json', summary)
    print(json.dumps({'cells': [{k: r[k] for k in
                                 ('start', 'N', 'P', 'medianAbsA', 'medianAbsC3',
                                  'MAE_A', 'MAE_C3', 'dMAE_C3minusA', 'gt10A', 'gt10C3',
                                  'T_C3minusA', 'T_hi', 'oldMAEC3', 'oldMAEA')}
                                for r in results],
                      'gateVerdict': summary['gateVerdict']},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
