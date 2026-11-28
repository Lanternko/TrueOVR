"""Paired player bootstrap on v4 predictions (diagnostic for v5 tolerance choice).

Reads v4/backtest/<start>/predictions-{a,c3}-N{k}.csv + targets.csv.
Resamples players with replacement B=2000 (seed 20261027), recomputes
median and MAE differences C3-A on each resample, reports point estimate and
the 2.5/97.5 percentiles.  No new data, no fitting.

Output: reports/ovr-inseason-2026-27/v5/planning/bootstrap-v4.json
"""
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BT = ROOT / 'reports/ovr-inseason-2026-27/v4/backtest'
OUT = Path(__file__).resolve().parent / 'bootstrap-v4.json'
B = 2000
SEED = 20261027

# Reuse v4's exact judged population (prior MIN>=500, full-season MIN>=500, window MIN>=1).
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/v4/tools'))
import v4_common as C  # noqa: E402

PRIOR = {'D2': '2023-24', 'D3': '2024-25'}


def read_pred(path):
    with open(path, newline='', encoding='utf-8') as f:
        return {int(r['playerId']): float(r['ovr']) for r in csv.DictReader(f)}


def read_target(start):
    with open(BT / start / 'targets.csv', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return {int(r['playerId']): float(r['ovr_target']) for r in rows if r['ovr_target']}


def pct(sorted_vals, q):
    if not sorted_vals:
        return None
    pos = q * (len(sorted_vals) - 1)
    lo, hi = int(pos), min(len(sorted_vals) - 1, int(pos) + 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def boot(err_a, err_c):
    """Resample players; each replicate recomputes median(C)-median(A) and MAE(C)-MAE(A)."""
    rng = random.Random(SEED)
    n = len(err_a)
    med, mae = [], []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        ea = sorted(err_a[i] for i in idx)
        ec = sorted(err_c[i] for i in idx)
        med.append(pct(ec, 0.5) - pct(ea, 0.5))
        mae.append(sum(err_c[i] - err_a[i] for i in idx) / n)
    med.sort()
    mae.sort()
    return ({'lo': round(pct(med, 0.025), 6), 'hi': round(pct(med, 0.975), 6),
             'median': round(pct(med, 0.5), 6)},
            {'lo': round(pct(mae, 0.025), 6), 'hi': round(pct(mae, 0.975), 6),
             'median': round(pct(mae, 0.5), 6)})


out = {'spec': 'v5 planning diagnostic; v4 predictions only; B=2000; seed=20261027',
       'note': 'diff = C3 - A; positive means C3 worse', 'cells': {}}
for start in ('D2', 'D3'):
    truth = read_target(start)
    for k in (3, 5, 10, 20):
        a = read_pred(BT / start / f'predictions-a-N{k}.csv')
        c = read_pred(BT / start / f'predictions-c3-N{k}.csv')
        judged = set(C.population(PRIOR[start], k))
        pids = sorted(judged & set(a) & set(c) & set(truth))
        d_med = [abs(c[p] - truth[p]) - abs(a[p] - truth[p]) for p in pids]
        err_a = [abs(a[p] - truth[p]) for p in pids]
        err_c = [abs(c[p] - truth[p]) for p in pids]
        med_a = pct(sorted(err_a), 0.5)
        med_c = pct(sorted(err_c), 0.5)
        mae_a = sum(err_a) / len(pids)
        mae_c = sum(err_c) / len(pids)
        med_ci, mae_ci = boot(err_a, err_c)
        out['cells'][f'{start}-N{k}'] = {
            'players': len(pids),
            'medianA': round(med_a, 6), 'medianC3': round(med_c, 6),
            'medianDiff': round(med_c - med_a, 6),
            'maeA': round(mae_a, 6), 'maeC3': round(mae_c, 6),
            'maeDiff': round(mae_c - mae_a, 6),
            'medianDiffBoot': med_ci, 'maeDiffBoot': mae_ci,
        }

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for key, v in out['cells'].items():
    print(key, 'n', v['players'], '| med diff', v['medianDiff'],
          'CI', v['medianDiffBoot']['lo'], v['medianDiffBoot']['hi'],
          '| MAE diff', v['maeDiff'], 'CI', v['maeDiffBoot']['lo'], v['maeDiffBoot']['hi'])
