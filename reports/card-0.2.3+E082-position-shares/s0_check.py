"""(s0) 自檢：非 lowConfidence 球員比例最大位置 == calibration-target-B12.csv 的 position。"""
import csv, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parents[2]
E = Path(__file__).resolve().parent
POS = ['PG', 'SG', 'SF', 'PF', 'C']
T = {r['name']: r['position'] for r in csv.DictReader((ROOT / 'reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv').open(encoding='utf-8'))}
S = list(csv.DictReader((E / 'pos-shares.csv').open(encoding='utf-8')))
mism, missing, n_nl, n_low = [], [], 0, 0
for r in S:
    low = r['lowConfidence'] == '1'
    if r['name'] not in T:
        missing.append(r['name']); continue
    if low:
        n_low += 1; continue
    n_nl += 1
    s = [float(r['s_' + p]) for p in POS]
    top = POS[s.index(max(s))]
    if top != T[r['name']]:
        mism.append({'name': r['name'], 'top': top, 'label': T[r['name']], 'seconds': s})
res = {'n_players_shares': len(S), 'n_target': len(T), 'n_nonLow_checked': n_nl, 'n_lowConfidence_in_target': n_low,
       'in_shares_not_in_target': missing, 'in_target_not_in_shares': sorted(set(T) - {r['name'] for r in S}),
       'mismatch_n': len(mism), 'mismatch': mism, 'pass': len(mism) <= 3}
(E / 'work/s0.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, indent=1))
