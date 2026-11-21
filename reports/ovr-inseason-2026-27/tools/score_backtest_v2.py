"""S6：2025-26 回測評分、覆蓋率、五條門檻與 v2 採用判定。

在 v2/predictions/SHA256SUMS 之後才讀答案卡 reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv。
輸出 v2/results.csv、v2/coverage.csv、v2/thresholds.json。
判定鏈（§4.3／§5.3／§2.5）：
  1. 五條門檻全部成立（第 5 條同時要求 OVR 與能力值覆蓋率，沿用 v1 的解讀）。
  2. §5.3：驗證季 N=10 需 ρ_C ≥ max(ρ_A,ρ_B) 且 MAE_C ≤ min(MAE_A,MAE_B)。
  3. §2.5 退化保護：drift.json 的 driftNegligible 為真 → 不採用 v2。
  全成立 → 採用 C_v2（生產起用點 N* 用 §4.5）；否則走 §4.4 的 A/B 退路。
用法：python reports/ovr-inseason-2026-27/tools/score_backtest_v2.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import ATTRS, MAIN_ATTRS, OUTDIR, ROOT, write_json
import v2_common as V2

TARGET = ROOT / 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv'
PRED_DIR = V2.V2_PREDICTIONS
V1_RESULTS = OUTDIR / 'backtest/results.csv'
GROUPS = ['prior', 'raw', 'shrunk']
N_LIST = [3, 5, 10, 20]
COVER_ATTRS = MAIN_ATTRS + ['creation']


def sha_check():
    sums = {}
    for line in (PRED_DIR / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        h, name = line.split()
        sums[name] = h
    for name, h in sums.items():
        got = hashlib.sha256((PRED_DIR / name).read_bytes()).hexdigest()
        if got != h:
            raise SystemExit(f'SHA mismatch: {name}')
    return sums


def read_pred(name):
    rows = list(csv.DictReader(open(PRED_DIR / name, encoding='utf-8')))
    for r in rows:
        for k in (['ovr', 'rank', 'MIN_window'] + ATTRS + [f'sd_{a}' for a in ATTRS]
                  + ['ovr_p10', 'ovr_p90', 'ovr_p2p5', 'ovr_p97p5']):
            if k in r and r[k] != '':
                r[k] = float(r[k])
    return rows


def selection_consistent(drift):
    """§2.4 規則重算，用 drift.json 裡兩候選的 N=10 數字。"""
    d = drift['candidates']['D1']['shrunk']
    d2 = drift['candidates']['D2']['shrunk']
    if d['rho_ovr'] > d2['rho_ovr'] + 0.005:
        pick = 'D1'
    elif d2['rho_ovr'] > d['rho_ovr'] + 0.005:
        pick = 'D2'
    elif d['mae_ovr'] < d2['mae_ovr'] - 0.01:
        pick = 'D1'
    elif d2['mae_ovr'] < d['mae_ovr'] - 0.01:
        pick = 'D2'
    elif d['mean_mae9'] < d2['mean_mae9'] - 0.01:
        pick = 'D1'
    elif d2['mean_mae9'] < d['mean_mae9'] - 0.01:
        pick = 'D2'
    else:
        pick = 'D1'
    return pick, pick == drift['chosen']


def main():
    sums = sha_check()
    target = {r['name']: r for r in csv.DictReader(open(TARGET, encoding='utf-8'))}
    for r in target.values():
        for k in ['ovr', 'MIN'] + ATTRS:
            r[k] = float(r[k])
    results, coverage = [], []
    details = {'predFiles': len(sums), 'targetPlayers': len(target), 'files': {}}
    for N in N_LIST:
        files = {g: read_pred(f'{g}-N{N}.csv') for g in GROUPS}
        base_names = [r['name'] for r in files['shrunk']]
        if any(set(r['name'] for r in files[g]) != set(base_names) for g in GROUPS):
            raise SystemExit(f'P mismatch at N={N}')
        P = [n for n in base_names if n in target]
        details['files'][f'N{N}'] = {'rows': len(base_names), 'matchedTarget': len(P)}
        if len(P) < 10:
            raise SystemExit(f'Too few matched players at N={N}')
        tgt_rank = {n: i + 1 for i, n in enumerate(sorted(P, key=lambda n: (-target[n]['ovr'], n)))}
        rows = {g: {r['name']: r for r in files[g]} for g in GROUPS}
        for g in GROUPS:
            pred_ovr = np.array([rows[g][n]['ovr'] for n in P])
            tgt_ovr = np.array([target[n]['ovr'] for n in P])
            rho = float(spearmanr(pred_ovr, tgt_ovr).statistic)
            mae_ovr = float(np.mean(np.abs(pred_ovr - tgt_ovr)))
            rank_mae = float(np.mean([abs(rows[g][n]['rank'] - tgt_rank[n]) for n in P]))
            attr_mae = {}
            for a in MAIN_ATTRS + ['creation', 'pressure']:
                if a in ('creation', 'pressure') and N < 20:
                    attr_mae[a] = None
                    continue
                attr_mae[a] = float(np.mean([abs(rows[g][n][a] - target[n][a]) for n in P]))
            mean9 = float(np.mean([attr_mae[a] for a in MAIN_ATTRS]))
            pred_top20 = set(sorted(P, key=lambda n: (-rows[g][n]['ovr'], n))[:20])
            tgt_top20 = set(sorted(P, key=lambda n: (-target[n]['ovr'], n))[:20])
            pred_top50 = set(sorted(P, key=lambda n: (-rows[g][n]['ovr'], n))[:50])
            tgt_top50 = set(sorted(P, key=lambda n: (-target[n]['ovr'], n))[:50])
            pos_rho = {}
            for pos in ['PG', 'SG', 'SF', 'PF', 'C']:
                pp = [n for n in P if rows[g][n]['pos'] == pos]
                if len(pp) >= 3 and len({target[n]['ovr'] for n in pp}) > 1:
                    pos_rho[pos] = float(spearmanr([rows[g][n]['ovr'] for n in pp],
                                                   [target[n]['ovr'] for n in pp]).statistic)
                else:
                    pos_rho[pos] = None
            results.append({
                'N': N, 'group': g, 'players': len(P), 'rho_ovr': round(rho, 6),
                'mae_ovr': round(mae_ovr, 4), 'rank_mae': round(rank_mae, 4),
                **{f'mae_{a}': (round(attr_mae[a], 4) if attr_mae[a] is not None else '')
                   for a in MAIN_ATTRS + ['creation', 'pressure']},
                'mean_mae9': round(mean9, 4),
                'top20_overlap': len(pred_top20 & tgt_top20),
                'top50_overlap': len(pred_top50 & tgt_top50),
                **{f'rho_{p}': (round(v, 6) if v is not None else '') for p, v in pos_rho.items()},
            })
        covered = {'80': 0, '95': 0, 'n': 0}
        for n in P:
            r = rows['shrunk'][n]
            for a in COVER_ATTRS:
                sdv = r[f'sd_{a}']
                if sdv <= 0:
                    continue
                covered['n'] += 1
                covered['80'] += int(abs(r[a] - target[n][a]) <= 1.282 * sdv)
                covered['95'] += int(abs(r[a] - target[n][a]) <= 1.96 * sdv)
        ovr80 = [int(rows['shrunk'][n]['ovr_p10'] <= target[n]['ovr'] <= rows['shrunk'][n]['ovr_p90'])
                 for n in P]
        ovr95 = [int(rows['shrunk'][n]['ovr_p2p5'] <= target[n]['ovr'] <= rows['shrunk'][n]['ovr_p97p5'])
                 for n in P]
        eps = json.loads((V2.V2_FIT / 'eps-ovr.json').read_text(encoding='utf-8'))
        coverage.append({
            'N': N, 'players': len(P), 'attr_pairs': covered['n'],
            'eps_ovr': eps['epsilon'], 'nP24_validation': eps['nP24'],
            'attr_coverage80': round(covered['80'] / covered['n'], 4) if covered['n'] else '',
            'attr_coverage95': round(covered['95'] / covered['n'], 4) if covered['n'] else '',
            'ovr_coverage80': round(float(np.mean(ovr80)), 4),
            'ovr_coverage95': round(float(np.mean(ovr95)), 4),
            'ovr_width80_median': round(float(np.median(
                [rows['shrunk'][n]['ovr_p90'] - rows['shrunk'][n]['ovr_p10'] for n in P])), 4),
            'ovr_width95_median': round(float(np.median(
                [rows['shrunk'][n]['ovr_p97p5'] - rows['shrunk'][n]['ovr_p2p5'] for n in P])), 4),
        })
    with open(V2.V2 / 'results.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    with open(V2.V2 / 'coverage.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(coverage[0].keys()))
        w.writeheader()
        w.writerows(coverage)

    r10 = {r['group']: r for r in results if r['N'] == 10}
    c10 = [c for c in coverage if c['N'] == 10][0]
    th1 = r10['shrunk']['rho_ovr'] - max(r10['prior']['rho_ovr'], r10['raw']['rho_ovr'])
    th2 = r10['shrunk']['mae_ovr'] / min(r10['prior']['mae_ovr'], r10['raw']['mae_ovr'])
    th3 = r10['shrunk']['mean_mae9'] / min(r10['prior']['mean_mae9'], r10['raw']['mean_mae9'])
    th4 = sum(1 for r in results if r['group'] == 'shrunk'
              for p in [next(x for x in results if x['group'] == 'prior' and x['N'] == r['N'])]
              if r['rho_ovr'] > p['rho_ovr'])
    thresholds = {
        'threshold1': {'value': round(th1, 6), 'pass': bool(th1 >= 0.03),
                       'rule': 'N=10 rho_C - max(rho_A, rho_B) >= 0.03'},
        'threshold2': {'value': round(th2, 6), 'pass': bool(th2 <= 0.95),
                       'rule': 'N=10 MAE_C <= 0.95*min(MAE_A, MAE_B)'},
        'threshold3': {'value': round(th3, 6), 'pass': bool(th3 <= 0.95),
                       'rule': 'N=10 mean attr MAE_C <= 0.95*min(A,B)'},
        'threshold4': {'value': th4, 'pass': bool(th4 >= 3),
                       'rule': 'rho_C > rho_A in at least 3 of 4 N'},
        'threshold5': {'attr80': c10['attr_coverage80'], 'attr95': c10['attr_coverage95'],
                       'ovr80': c10['ovr_coverage80'], 'ovr95': c10['ovr_coverage95'],
                       'passOvr': bool(0.70 <= c10['ovr_coverage80'] <= 0.90
                                       and 0.88 <= c10['ovr_coverage95'] <= 0.98),
                       'passAttr': bool(0.70 <= c10['attr_coverage80'] <= 0.90
                                        and 0.88 <= c10['attr_coverage95'] <= 0.98),
                       'rule': 'N=10 80% coverage in [0.70,0.90] and 95% in [0.88,0.98]; '
                               'reported for both OVR and attribute coverage (v1 reading)'},
    }
    thresholds['threshold5']['pass'] = bool(thresholds['threshold5']['passOvr']
                                            and thresholds['threshold5']['passAttr'])
    thresholds['allPass'] = all(thresholds[f'threshold{i}']['pass'] for i in range(1, 6))

    drift = V2.load_drift()
    pick, consistent = selection_consistent(drift)
    val = {(int(r['N']), r['group']): r for r in csv.DictReader(open(V2.V2_VALIDATION / 'results.csv',
                                                                    encoding='utf-8'))}
    vc, va, vb = val[(10, 'shrunk')], val[(10, 'prior')], val[(10, 'raw')]
    val_win = {
        'rho_C_10': float(vc['rho_ovr']), 'rho_A_10': float(va['rho_ovr']), 'rho_B_10': float(vb['rho_ovr']),
        'mae_C_10': float(vc['mae_ovr']), 'mae_A_10': float(va['mae_ovr']), 'mae_B_10': float(vb['mae_ovr']),
        'rhoPass': bool(float(vc['rho_ovr']) >= max(float(va['rho_ovr']), float(vb['rho_ovr']))),
        'maePass': bool(float(vc['mae_ovr']) <= min(float(va['mae_ovr']), float(vb['mae_ovr']))),
    }
    val_win['pass'] = bool(val_win['rhoPass'] and val_win['maePass'])
    fallback = json.loads((V2.V2_FIT / 'fallback.json').read_text(encoding='utf-8'))
    degenerate = drift.get('degenerate', {})
    adopted = bool(thresholds['allPass'] and val_win['pass'] and not degenerate.get('driftNegligible'))
    if adopted:
        ns = [n for n in N_LIST if next(r for r in results if r['N'] == n and r['group'] == 'shrunk')['rho_ovr']
              >= next(r for r in results if r['N'] == n and r['group'] == 'prior')['rho_ovr']]
        n_star = min(ns) if ns else 20
        decision = f'ADOPT C_v2 (N*={n_star})'
    else:
        n_cross = fallback['N_cross']
        decision = ('FALLBACK A/B (§4.4): N_cross = ' + ('none -> always A' if n_cross is None else str(n_cross)))
    thresholds['candidateSelection'] = {'chosen': drift['chosen'], 'recomputed': pick, 'consistent': consistent,
                                        'D1': drift['candidates']['D1']['shrunk'],
                                        'D2': drift['candidates']['D2']['shrunk']}
    thresholds['validationSeason'] = val_win
    thresholds['driftNegligible'] = degenerate
    thresholds['fallback'] = {'N_cross': fallback['N_cross'], 'perN': fallback['perN']}
    thresholds['adopted'] = adopted
    thresholds['decision'] = decision
    v1 = {}
    if V1_RESULTS.exists():
        for r in csv.DictReader(open(V1_RESULTS, encoding='utf-8')):
            if r['group'] == 'shrunk':
                v1[int(r['N'])] = {k: r[k] for k in ('rho_ovr', 'mae_ovr', 'mean_mae9', 'rank_mae')}
    thresholds['v1Reference'] = v1
    write_json(V2.V2 / 'thresholds.json', thresholds)
    write_json(V2.V2 / 'scoring-details.json', details)
    print(json.dumps({'decision': decision, 'thresholds': thresholds, 'coverage': coverage},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
