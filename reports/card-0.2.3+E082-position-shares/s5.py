"""E-082 §5 只報告。用法：python -I s5.py → work/s5.json"""
import csv, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
rd = lambda p: list(csv.DictReader(Path(p).open(encoding='utf-8')))
old = {r['name']: r for r in rd(ROOT / 'reports/card-0.2.3/ranking.csv')}
new_rows = rd(HERE / 'ranking.csv'); new = {r['name']: r for r in new_rows}
sh = {}
for r in rd(HERE / 'pos-shares.csv'):
    s = [float(r['s_' + p]) for p in ('PG', 'SG', 'SF', 'PF', 'C')]
    low = r['lowConfidence'] == '1'
    sh[r['name']] = {'low': low, 'starts': int(r['starts']), 'pi': None if (low or sum(s) <= 0) else [x / sum(s) for x in s]}
P = ('PG', 'SG', 'SF', 'PF', 'C')
def info(n):
    s = sh[n]
    return {'name': n, 'pos': new[n]['pos'], 'ovr_old': float(old[n]['ovr']), 'rank_old': int(old[n]['rank']), 'ovr_new': float(new[n]['ovr']), 'rank_new': int(new[n]['rank']),
            'dOvr': round(float(new[n]['ovr']) - float(old[n]['ovr']), 4), 'lowConfidence': s['low'], 'starts': s['starts'],
            'shares': (dict(zip(P, [round(x, 4) for x in s['pi']])) if s['pi'] else 'one-hot（lowConfidence）')}
out = {'three': [info(n) for n in ('Paolo Banchero', 'Jalen Williams', 'Jalen Johnson')]}
out['top20_new'] = [{'rank': int(r['rank']), 'name': r['name'], 'pos': r['pos'], 'ovr': float(r['ovr']), 'rank_old': int(old[r['name']]['rank']), 'ovr_old': float(old[r['name']]['ovr'])} for r in new_rows[:20]]
out['top20_old'] = [{'rank': int(r['rank']), 'name': r['name'], 'ovr': float(r['ovr'])} for r in sorted(old.values(), key=lambda r: int(r['rank']))[:20]]
d = sorted(new, key=lambda n: (-abs(float(new[n]['ovr']) - float(old[n]['ovr'])), n))
out['top20_change'] = [info(n) for n in d[:20]]
assert set(old) == set(new) == set(sh)
lt = [n for n in new if sh[n]['pi'] and max(sh[n]['pi']) < 0.6]
rest = [n for n in new if n not in set(lt)]
ad = lambda ns: float(np.mean([abs(float(new[n]['ovr']) - float(old[n]['ovr'])) for n in ns]))
mx = lambda ns: float(max(abs(float(new[n]['ovr']) - float(old[n]['ovr'])) for n in ns))
out['lt60'] = {'n': len(lt), 'meanAbsDOvr': ad(lt), 'maxAbsDOvr': mx(lt), 'rest_n': len(rest), 'rest_meanAbsDOvr': ad(rest), 'rest_maxAbsDOvr': mx(rest)}
rest_hi = [n for n in rest if sh[n]['pi']]
out['lt60']['rest_withShares_n'] = len(rest_hi); out['lt60']['rest_withShares_meanAbsDOvr'] = ad(rest_hi)
out['allMeanAbsDOvr'] = ad(list(new)); out['nChangedOvr'] = sum(float(new[n]['ovr']) != float(old[n]['ovr']) for n in new)
out['posLabelChanged'] = sum(new[n]['pos'] != old[n]['pos'] for n in new)
cnt = {}
for k in (30, 60, 100):
    cnt[k] = {p: [sum(1 for r in sorted(old.values(), key=lambda r: int(r['rank']))[:k] if r['pos'] == p), sum(1 for r in new_rows[:k] if r['pos'] == p)] for p in P}
out['topNposCounts_old_new'] = cnt
(HERE / 'work' / 's5.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + chr(10), encoding='utf-8')
