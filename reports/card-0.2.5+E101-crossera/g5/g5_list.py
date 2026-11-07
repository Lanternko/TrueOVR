"""G5 抽查名單（lead）：E-101 對 card 0.2.5、E-096 的名次，附 2K27 與 RAPM 名次。"""
import csv, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
R = Path(__file__).resolve().parents[3]
def load(p): 
    with open(R / p, encoding='utf-8') as f: return {r['name']: r for r in csv.DictReader(f)}
e101 = load('reports/card-0.2.5+E101-crossera/cards/e101/e084/ranking.csv')
e096 = load('reports/card-0.2.5+E096-tail150/cards/e096/e084/ranking.csv')
c025 = load('reports/card-0.2.5/ranking.csv')
m = load('reports/ovr-v55-2k27-compare/merged.csv')
def row(n):
    a = e101[n]; g = lambda d, k='rank': d.get(n, {}).get(k, '—')
    mm = m.get(n, {})
    rk = lambda x: str(int(float(x))) if x not in ('', None, '—') else '—'
    return {'name': n, 'pos': a['pos'], 'e101': int(a['rank']), 'ovr': a['ovr'], 'c025': g(c025), 'e096': g(e096),
            'rank2k': rk(mm.get('rank2k')), 'rapm': rk(mm.get('rapmPooledRank'))}
top = sorted(e101, key=lambda n: int(e101[n]['rank']))
bigs = [n for n in top if e101[n]['pos'] == 'C'][:10]
watch = ['Alex Caruso', 'Jared McCain', 'Nikola Topić', 'Cason Wallace', 'Isaiah Joe', 'Kenrich Williams', 'Dyson Daniels',
         'Tyrese Maxey', 'Stephen Curry', 'Jalen Brunson', 'Kevin Durant', 'Joel Embiid', 'Jalen Duren', 'Walker Kessler',
         'Daniel Gafford', 'Andre Drummond', 'Zach Edey', 'Amen Thompson', 'Anthony Edwards', 'LeBron James']
out = {'top20': [row(n) for n in top[:20]], 'bigs10': [row(n) for n in bigs],
       'watch': [row(n) for n in watch if n in e101], 'missing': [n for n in watch if n not in e101],
       'top20_vs_c025_out': [n for n in sorted(c025, key=lambda n: int(c025[n]['rank']))[:20] if int(e101.get(n, {'rank': 999})['rank']) > 20]}
(Path(__file__).parent / 'g5-list.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
for k in ('top20', 'bigs10', 'watch'):
    print('==', k)
    for r in out[k]: print(f"{r['e101']:>4} {r['name']:<26}{r['pos']:<3} ovr {r['ovr']:>6}  c025 {r['c025']:>4}  e096 {r['e096']:>4}  2K {r['rank2k']:>4}  RAPM {r['rapm']:>4}")
print('missing', out['missing'], 'out of top20', out['top20_vs_c025_out'])
