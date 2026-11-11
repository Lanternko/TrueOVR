"""P5：A/B/C1/C2/C3 回測（preregistration-v4 §2.1/§2.5、§9 P5）。

A   = x0（先驗卡逐值；須等於 c_<prior> 的 OVR，否則 exit 2）
B   = y_adj（未達最低樣本者用 x0）
C1  = C3(λ=1)
C2  = v3 的貝氏收縮（δ² 沿用 P3 的 H(s) 配對；undefined／pressure 凍結）
C3  = C3(λ*(s,N))（λ 由 P4 機械選出）
輸出：
  v4/backtest/<start>/predictions-{a,b,c1,c2,c3}-N{3,5,10,20}.csv
  v4/backtest/<start>/targets.csv、sha256.txt（先寫 SHA 再評分）
  v4/backtest/results.csv、backtest-meta.json
  v4/fit/equiv.json（§2.5 三項 + 人群數對 v3 + C2 逐項重現對照）
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
import fit_w_grid_v4 as F
import inseason_common_v4 as IC
import v2_common as V2

EPS = 1e-9
STARTS = ['W', 'D1', 'D2', 'D3']


def wgrid_from(grid):
    return {s: {a: {N: grid['w'][s]['attrs'][a]['w'][str(N)] for N in C.N_LIST}
                for a in C.UPD} for s in STARTS}


def ovr_of(pipe, attrs):
    return pipe.predict(attrs)


def diff_map(pred_a, pred_b, pids):
    return {p: pred_a[p]['ovr'] - pred_b[p]['ovr'] for p in pids}


def maxabs(d):
    return max((abs(v) for v in d.values()), default=0.0)


def v3_stack():
    """唯讀載入 v3 的 C2 對照（只 import，不執行任何 writer）。"""
    sys.path.insert(0, str(C.V3 / 'tools'))
    import v3_common as C3
    import fit_w_grid as F3
    return C3, F3


def c2_repro(v4_attrs):
    """逐起點、逐 N、逐能力的 C2 對照：比較 v3 與 v4 的 C2 屬性預測。

    v4 相對 v3 的資料層改動（§3/§9 已宣告）只有：
      W 的 x0（prior-2021-22 重建：mid、shortBase/short，以及 prior 與 season-cards 對齊後的
      pass/rebound）、creation（目標季無 dependence 列時 y=x0）、
      以及上述改變經由 W 配對傳進 δ²。
    因此「未受改動」的能力值是 long/ft/drive/tovSkill/stamina/pressure 六項；
    這六項在全部格子必須逐球員差 = 0（<1e-9），作為 C2 演算法移植的證據。
    """
    C3, F3 = v3_stack()
    rel = V2.load_reliability()
    g3 = C.load_json(C.V3_FIT / 'w-grid.json')
    CHANGED = ['mid', 'short', 'creation', 'pass', 'rebound']
    UNCHANGED = [a for a in C.UPD if a not in CHANGED]
    out = {'changedAttrs': CHANGED, 'unchangedAttrs': UNCHANGED, 'per': {}}
    for s in STARTS:
        out['per'][s] = {}
        d2_3 = {a: v['delta2'] for a, v in g3['c2'][s]['attrs'].items()}
        ua3 = g3['c2'][s]['undefinedAttrs']
        fz3 = ['pressure'] if g3['c2'][s]['pressureFrozen'] else []
        for N in C.N_LIST:
            a3 = F3.c2_predict(s, N, d2_3, rel, undefined=ua3, frozen=fz3)
            a4 = v4_attrs[(s, N, 'C2')]
            common = sorted(set(a3) & set(a4))
            per_attr = {}
            for a in C.UPD:
                d = max((abs(a4[p][a] - a3[p][a]) for p in common), default=0.0)
                per_attr[a] = round(d, 9)
            same = [a for a in UNCHANGED]
            out['per'][s][str(N)] = {
                'players': len(common),
                'maxAbsDiffByAttr': per_attr,
                'unchangedAttrsMax': max(per_attr[a] for a in same),
                'changedAttrsMax': max(per_attr[a] for a in CHANGED),
            }
    out['unchangedAttrsReproduce'] = bool(
        all(v['unchangedAttrsMax'] < EPS for s in out['per'].values() for v in s.values()))
    out['strictAllAttrsMax'] = round(max(v['maxAbsDiffByAttr'][a]
                                         for s in out['per'].values() for v in s.values()
                                         for a in C.UPD), 6)
    return out


def main():
    grid = C.load_json(C.V4_FIT / 'w-grid.json')
    lam = C.load_json(C.V4_FIT / 'lambda.json')['lambda']
    wg = wgrid_from(grid)
    rel = V2.load_reliability()

    results, acheck, preds_store, c2_attrs = [], {}, {}, {}
    equiv = {'spec': 'preregistration-v4 §2.5 / P5', 'eps': EPS,
             'c3lambda1EqC1': {}, 'c3lambda0EqA': {}, 'd1C3EqC1': {}}
    v3res = {r['start'] + '|' + r['N']: r for r in
             C.load_csv(C.V3_BACKTEST / 'results.csv')}
    pop_rows = []

    for start in STARTS:
        outdir = C.V4_BACKTEST / start
        outdir.mkdir(parents=True, exist_ok=True)
        pipe = C.pipeline_for(start)
        cards, x0 = C.deployment(start)
        pred_a = ovr_of(pipe, {p: {a: float(c[a]) for a in C.ATTRS} for p, c in cards.items()})
        csv_a = {int(r['playerId']): float(r['ovr'])
                 for r in C.load_csv(C.V4_CARDS / f"{C.CHAIN[start]['prior']}.csv")}
        adiff = [abs(round(pred_a[p]['ovr'], 4) - csv_a[p]) for p in csv_a if p in pred_a]
        missing = sorted(p for p in csv_a if p not in pred_a)
        acheck[start] = {'n': len(adiff), 'maxAbsDiffRounded': max(adiff) if adiff else None,
                         'missingPids': missing,
                         'equalPerValue': bool(adiff and max(adiff) == 0.0 and not missing)}

        tgt = F.target_ovr(start)
        C.write_csv(outdir / 'targets.csv',
                    [{'playerId': p, 'name': c.get('name', ''), 'pos': c['pos'],
                      'MIN_prior': round(float(c['observed']['MIN']), 1),
                      'ovr_target': tgt.get(p)} for p, c in sorted(cards.items())],
                    head=['playerId', 'name', 'pos', 'MIN_prior', 'ovr_target'])

        d2 = {a: v['delta2'] for a, v in grid['c2'][start]['attrs'].items()}
        undefined = grid['c2'][start]['undefinedAttrs']
        frozen = ['pressure'] if grid['c2'][start]['pressureFrozen'] else []

        preds = {}
        for N in C.N_LIST:
            attrs = {
                'A': {p: {a: float(c[a]) for a in C.ATTRS} for p, c in cards.items()},
                'B': F.raw_predict(start, N),
                'C1': F.c1_predict(start, N, wg[start], 1.0),
                'C2': F.c2_predict(start, N, d2, rel, undefined=undefined, frozen=frozen),
                'C3': F.c1_predict(start, N, wg[start], lam[start][str(N)]),
            }
            for k, v in attrs.items():
                preds[(k, N)] = ovr_of(pipe, v)
                preds_store[(start, N, k)] = preds[(k, N)]
            c2_attrs[(start, N, 'C2')] = attrs['C2']
            # §2.5（逐球員、全部球員，含不在人群者）
            pids = sorted(cards)
            preds_store[(start, N, 'C3@1')] = ovr_of(pipe, F.c1_predict(start, N, wg[start], 1.0))
            preds_store[(start, N, 'C3@0')] = ovr_of(pipe, F.c1_predict(start, N, wg[start], 0.0))
            if C.CHAIN[start]['judge']:
                m1 = maxabs(diff_map(preds_store[(start, N, 'C3@1')],
                                     preds_store[(start, N, 'C1')], pids))
                m0 = maxabs(diff_map(preds_store[(start, N, 'C3@0')],
                                     preds_store[(start, N, 'A')], pids))
                equiv['c3lambda1EqC1'][f'{start}|{N}'] = round(m1, 12)
                equiv['c3lambda0EqA'][f'{start}|{N}'] = round(m0, 12)
                if start == 'D1':
                    equiv['d1C3EqC1'][f'D1|{N}'] = round(
                        maxabs(diff_map(preds_store[(start, N, 'C3')],
                                        preds_store[(start, N, 'C1')], pids)), 12)

        for N in C.N_LIST:
            for tag, key in (('a', 'A'), ('b', 'B'), ('c1', 'C1'), ('c2', 'C2'), ('c3', 'C3')):
                rows = [{'playerId': p, 'name': cards[p].get('name', ''), 'pos': cards[p]['pos'],
                         'MIN_prior': round(float(cards[p]['observed']['MIN']), 1),
                         'ovr': round(preds[(key, N)][p]['ovr'], 4)} for p in sorted(cards)]
                C.write_csv(outdir / f'predictions-{tag}-N{N}.csv', rows,
                            head=['playerId', 'name', 'pos', 'MIN_prior', 'ovr'])
        files = sorted(f for f in outdir.glob('*.csv'))
        (outdir / 'sha256.txt').write_text(
            '\n'.join(f'{f.name} {C.sha256_file(f)}' for f in files) + '\n', encoding='utf-8')

        for N in C.N_LIST:
            P = [p for p in C.population(C.CHAIN[start]['prior'], N) if p in tgt]
            v3 = v3res.get(f'{start}|{N}')
            pop_rows.append({'start': start, 'N': N, 'v4P': len(P),
                             'v3P': int(v3['P']) if v3 else None,
                             'equal': (int(v3['P']) == len(P)) if v3 else None})
            rec = {'start': start, 'N': N, 'judge': C.CHAIN[start]['judge'], 'P': len(P)}
            for key in ('A', 'B', 'C1', 'C2', 'C3'):
                errs = [abs(preds[(key, N)][p]['ovr'] - tgt[p]) for p in P]
                rec[f'median{key}'] = round(float(np.median(errs)), 6)
                rec[f'mean{key}'] = round(float(np.mean(errs)), 6)
                rec[f'gt10{key}'] = int(sum(1 for e in errs if e > 10))
            results.append(rec)

    C.write_csv(C.V4_BACKTEST / 'results.csv', results,
                head=['start', 'N', 'judge', 'P',
                      'medianA', 'medianB', 'medianC1', 'medianC2', 'medianC3',
                      'meanA', 'meanB', 'meanC1', 'meanC2', 'meanC3',
                      'gt10A', 'gt10B', 'gt10C1', 'gt10C2', 'gt10C3'])

    # ---- §2.5 判定
    equiv['pass'] = {
        'c3lambda1EqC1': all(v < EPS for v in equiv['c3lambda1EqC1'].values()),
        'c3lambda0EqA': all(v < EPS for v in equiv['c3lambda0EqA'].values()),
        'd1C3EqC1': all(v < EPS for v in equiv['d1C3EqC1'].values()),
    }
    # ---- 人群數 vs v3
    equiv['population'] = {'cells': pop_rows,
                           'allEqual': all(r['equal'] for r in pop_rows if r['equal'] is not None),
                           'note': '每格 P 與 v3/backtest/results.csv 相同（C2 重現的前提）'}
    # ---- C2 重現
    equiv['c2Reproduction'] = c2_repro(c2_attrs)
    # OVR 層的 v3 對照（只看已存檔的 OVR，不重算）
    ovr_cmp = {}
    for start in STARTS:
        for N in C.N_LIST:
            p3 = C.V3_BACKTEST / start / f'predictions-c-N{N}.csv'
            if not p3.exists():
                continue
            b3 = {int(r['playerId']): float(r['ovr'])
                  for r in C.load_csv(p3)}
            d = [abs(preds_store[(start, N, 'C2')][p]['ovr'] - b3[p]) for p in b3
                 if p in preds_store[(start, N, 'C2')]]
            ovr_cmp[f'{start}|{N}'] = {'n': len(d), 'maxAbsDiff': round(max(d), 6),
                                       'medianAbsDiff': round(float(np.median(d)), 6)}
    equiv['c2Reproduction']['ovrVsV3'] = ovr_cmp
    equiv['c2Reproduction']['pass'] = bool(
        equiv['c2Reproduction']['unchangedAttrsReproduce'] and equiv['population']['allEqual'])
    equiv['allPass'] = bool(all(equiv['pass'].values()) and equiv['c2Reproduction']['pass'])

    C.write_json(C.V4_FIT / 'equiv.json', equiv)
    meta = {'spec': 'preregistration-v4 §9 P5', 'aCheck': acheck,
            'aCheckPass': all(v['equalPerValue'] for v in acheck.values()),
            'lambda': lam, 'nList': C.N_LIST, 'starts': STARTS,
            'results': str((C.V4_BACKTEST / 'results.csv').relative_to(C.ROOT))}
    C.write_json(C.V4_BACKTEST / 'backtest-meta.json', meta)
    print(json.dumps({'aCheck': {k: v['equalPerValue'] for k, v in acheck.items()},
                      'equiv': equiv['pass'], 'c2': {'unchangedAttrsReproduce':
                                                     equiv['c2Reproduction']['unchangedAttrsReproduce'],
                                                     'strictAllAttrsMax': equiv['c2Reproduction']['strictAllAttrsMax']},
                      'population': equiv['population']['allEqual'],
                      'allPass': equiv['allPass'], 'results': results},
                     ensure_ascii=False, indent=1))
    return 0 if equiv['allPass'] and meta['aCheckPass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
