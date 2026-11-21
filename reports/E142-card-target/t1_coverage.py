"""T1 自製 EPM 對 MIN>=500 母體的覆蓋率（只看覆蓋，不看值）。"""
import csv, importlib.util, json
from pathlib import Path
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('c', here / 'c0d_collect.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
R = here.parents[1]
cov = {}
for s in m.SEASONS:
    k = [int(x) for x in m.population(s, 500)[0]]
    ids = {int(r['playerId']) for r in csv.DictReader(open(R / f'data/external-impact/epm_self/epm_{s}.csv', encoding='utf-8'))}
    hit = sum(1 for x in k if x in ids)
    cov[s] = {'pop': len(k), 'covered': hit, 'coverage': round(hit / len(k), 4)}
    print(s, cov[s])
(here / 'c0d-coverage-T1.json').write_text(json.dumps(cov, indent=1), encoding='utf-8')
