"""E-070 只報告項目 + inputs-sha256.json + verdict.json。python -I -X utf8 report_items.py"""
import csv, json, hashlib
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).parent; ROOT = HERE.parents[1]
read = lambda p: list(csv.DictReader(open(p, encoding='utf-8-sig')))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rho = lambda a, b: float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])
old = read(ROOT / 'reports/card-0.2.0/ranking.csv'); new = read(HERE / 'primary/ranking.csv')
O = {r['name']: r for r in old}; N = {r['name']: r for r in new}
assert set(O) == set(N) and len(O) == 582
orank = {r['name']: int(r['rank']) for r in old}; nrank = {r['name']: int(r['rank']) for r in new}
fdr = lambda rows: {n: i + 1 for i, n in enumerate(sorted(rows, key=lambda n: -float(rows[n]['foulDraw'])))}
ofd, nfd = fdr(O), fdr(N)
out = {}
sv = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))['valuePer10AttributePoints']['foulDraw']
out['foulDrawCoef'] = {'card0.2.0': sv(HERE / 'cards-w0/primary/summary.json'), 'E070': sv(HERE / 'cards-w075/primary/summary.json')}
k2 = {r['name']: float(r['overall2k']) for r in read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
nm = sorted(n for n in k2 if n in N)
out['rho2k'] = {'n': len(nm), **{lab: {'perGame': rho([float(R[n]['ovr']) for n in nm], [k2[n] for n in nm]),
                                     'per36': rho([float(R[n]['ovr36']) for n in nm], [k2[n] for n in nm])} for lab, R in (('card0.2.0', O), ('E070', N))}}
out['top20'] = [{'rank': i + 1, 'old': (O[n]['name'], float(O[n]['ovr'])) , 'new': (r['name'], float(r['ovr']))} for i, (n, r) in enumerate(zip([x['name'] for x in old[:20]], new[:20]))]
out['top20_old_vs_new_names_same_order'] = [x['name'] for x in old[:20]] == [x['name'] for x in new[:20]]
mv = sorted(O, key=lambda n: -abs(float(N[n]['ovr']) - float(O[n]['ovr'])))[:15]
out['movers'] = [{'name': n, 'pos': O[n]['pos'], 'MIN': O[n]['MIN'], 'fdOld': float(O[n]['foulDraw']), 'fdNew': float(N[n]['foulDraw']), 'ovrOld': float(O[n]['ovr']), 'ovrNew': float(N[n]['ovr']),
                  'dOvr': round(float(N[n]['ovr']) - float(O[n]['ovr']), 2), 'rankOld': orank[n], 'rankNew': nrank[n]} for n in mv]
out['topFD'] = [{'rank': i + 1, 'name': n, 'fd': float(N[n]['foulDraw']), 'fdOld': float(O[n]['foulDraw']), 'oldFdRank': ofd[n], 'MIN': N[n]['MIN']} for i, n in enumerate(sorted(N, key=lambda n: -float(N[n]['foulDraw']))[:20])]
G5 = ['Shai Gilgeous-Alexander', 'Luka Dončić', 'Joel Embiid', 'Giannis Antetokounmpo', 'Jalen Brunson', 'James Harden', 'Trae Young', 'Jimmy Butler III', 'Rudy Gobert', 'Steven Adams', 'Dwight Powell', 'Mason Plumlee', 'Alex Antetokounmpo']
out['g5'] = []
for n in G5:
    if n not in N: out['g5'].append({'name': n, 'missing': True}); continue
    out['g5'].append({'name': n, 'pos': N[n]['pos'], 'MIN': N[n]['MIN'], 'fdOld': float(O[n]['foulDraw']), 'fdNew': float(N[n]['foulDraw']), 'fdRankOld': ofd[n], 'fdRankNew': nfd[n],
                      'ovrOld': float(O[n]['ovr']), 'ovrNew': float(N[n]['ovr']), 'rankOld': orank[n], 'rankNew': nrank[n]})
d = [abs(float(N[n]['ovr']) - float(O[n]['ovr'])) for n in N]
out['ovrChange'] = {'meanAbs': float(np.mean(d)), 'max': float(np.max(d)), 'n_gt1': int(sum(x > 1 for x in d)), 'n_gt3': int(sum(x > 3 for x in d)), 'spearmanOldNewOvr': rho([float(O[n]['ovr']) for n in O], [float(N[n]['ovr']) for n in O])}
(HERE / 'report-items.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

# inputs
A = 'reports/ovr-v61-shrink-history-2025-26/'
files = [HERE / 'preregistration.md', ROOT / A / 'attributes-new.csv', ROOT / A / 'backtest.json', ROOT / A / 'engine.py', ROOT / 'reports/card-0.1.1+E060-onball-targeting/defense-attributes-e060.csv',
         ROOT / 'reports/card-0.1.1+E060-onball-targeting/evaluate.mjs', ROOT / 'reports/ovr-v58-holdout-2025-26/rapm-A.csv', ROOT / 'reports/ovr-v58-holdout-2025-26/rapm-B.csv',
         ROOT / 'reports/card-0.1.2+E064-pergame/mpg-A.csv', ROOT / 'reports/card-0.1.2+E064-pergame/mpg-B.csv', ROOT / 'reports/card-0.1.2+E064-pergame/mpg-full.csv',
         ROOT / 'reports/card-0.1.2+E064-pergame/calibrate-wing.py', ROOT / 'reports/card-0.2.0/ranking.csv', ROOT / 'reports/card-0.2.0/summary.json',
         ROOT / 'reports/ovr-v55-2k27-compare/merged.csv', ROOT / 'data/season-source/player-games.json', ROOT / 'data/season-league.json']
inp = {}
for f in files:
    inp[f.relative_to(ROOT).as_posix()] = sha(f) if f.exists() else 'MISSING'

inp['output:primary/ranking.csv'] = sha(HERE / 'primary/ranking.csv')
(HERE / 'inputs-sha256.json').write_text(json.dumps(inp, indent=1), encoding='utf-8')

# verdict
c2 = json.loads((HERE / 'c2.json').read_text(encoding='utf-8')); ev = json.loads((HERE / 'evaluation.json').read_text(encoding='utf-8'))
c0 = sha(HERE / 'cards-w0/card/ranking.csv') == sha(ROOT / 'reports/card-0.2.0/ranking.csv')
log = (HERE / 'npm-test.log').read_text(encoding='utf-8', errors='replace')
c1 = (HERE / 'npm-test.exit').read_text().strip() == '0' and '57 passed, 0 failed' in log
print(type(ev), list(ev)[:10] if isinstance(ev, dict) else len(ev))
json.dump({'c0': c0, 'c1': c1, 'c2': c2['c2'], 'ev_keys': 'see next'}, open(HERE / '_tmp.json', 'w'))
