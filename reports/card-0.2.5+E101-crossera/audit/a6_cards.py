"""稽核 6：卡片名次與 OVR；每 10 分屬性價值。
- 自己由 cards/e101/e084/ranking.csv 的 gRepl 重算 OVR（two_segment，錨點 = MIN>=500 池的 PR1/50/99，qf 取 round(p/100*(n-1))）與名次。
- 隨機 5 人（random.Random(7).sample，名單依 e101 ranking 檔順序）＋ Curry、Brunson、Duren、Giannis、Kessler：對 report-data.json 與 report.md 文字。
- fitA/primary summary.json 的 valuePer10AttributePoints（mid、long、short）對 E-096。"""
import csv, json, random, sys
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parents[1]
R = OUT.parent
def rk(p): return {r['name']: r for r in csv.DictReader(open(p, encoding='utf-8'))}
e101 = list(csv.DictReader(open(OUT/'cards/e101/e084/ranking.csv', encoding='utf-8')))
c025 = rk(R/'card-0.2.5/ranking.csv'); e096 = rk(R/'card-0.2.5+E096-tail150/cards/e096/e084/ranking.csv')
g = np.array([float(r['gRepl']) for r in e101]); MIN = np.array([float(r['MIN']) for r in e101])
def qf(v, m, p):
    s = np.sort(v[m]); return float(s[int(round(p/100*(len(s)-1)))])
pool = MIN >= 500
p1, p50, p99 = (qf(g, pool, q) for q in (1, 50, 99))
ovr = np.where(g <= p50, 40 + 30*(g - p1)/(p50 - p1), 70 + 29*(g - p50)/(p99 - p50))
order = np.argsort(-ovr, kind='stable')
myrank = {e101[i]['name']: k+1 for k, i in enumerate(order)}
mism = [(r['name'], r['ovr'], round(ovr[i], 1), r['rank'], myrank[r['name']]) for i, r in enumerate(e101)
        if abs(float(r['ovr']) - round(ovr[i], 1)) > 0.051 or int(r['rank']) != myrank[r['name']]]
rd = json.load(open(OUT/'report-data.json', encoding='utf-8'))
names = [r['name'] for r in e101]
sample = random.Random(7).sample(names, 5)
named = ['Stephen Curry', 'Jalen Brunson', 'Jalen Duren', 'Giannis Antetokounmpo', 'Walker Kessler']
by = {r['name']: r for r in e101}
rows = []
for n in sample + named:
    rows.append({'name': n, 'card025': [int(c025[n]['rank']), float(c025[n]['ovr'])] if n in c025 else None,
                 'e096': [int(e096[n]['rank']), float(e096[n]['ovr'])] if n in e096 else None,
                 'e101_file': [int(by[n]['rank']), float(by[n]['ovr'])], 'e101_mine': [myrank[n], round(float(ovr[names.index(n)]), 1)]})
# report-data.json 裡找名次資料
def find(o, n, path=''):
    hits = []
    if isinstance(o, dict):
        for k, v in o.items(): hits += find(v, n, path+'/'+k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if (isinstance(v, dict) and v.get('name') == n) or (isinstance(v, list) and v and v[0] == n):
                hits.append((path+f'[{i}]', v))
            else: hits += find(v, n, path+f'[{i}]')
    return hits
for r in rows:
    r['reportData'] = [h for h in find(rd, r['name']) if any(k in h[0].lower() for k in ('rank', 'move', 'top'))][:4]
val = {}
for tag, d in (('e096', R/'card-0.2.5+E096-tail150/cards/e096/P1'), ('e101', OUT/'cards/e101/P1'), ('cur', R/'card-0.2.4+E090-onball-tail/cards/cur/P1')):
    for part in ('fitA', 'fitB', 'primary'):
        p = d/part/'summary.json'
        if p.exists():
            v = json.load(open(p, encoding='utf-8'))['valuePer10AttributePoints']
            val[f'{tag}/{part}'] = {a: [round(v[a]['per36'], 3), round(v[a]['bootstrapSE'], 3)] for a in ('mid', 'long', 'short')}
# 名次移動計數（報告：對 card 0.2.5 303 人移動 >=5、133 人 >=10；升 146 降 378；對 E-096 277 人 >=5）
mv = [int(c025[n]['rank']) - int(by[n]['rank']) for n in names if n in c025]
mv96 = [int(e096[n]['rank']) - int(by[n]['rank']) for n in names if n in e096]
d_ovr = [float(by[n]['ovr']) - float(c025[n]['ovr']) for n in names if n in c025]
moves = {'vs025_ge5': sum(abs(x) >= 5 for x in mv), 'vs025_ge10': sum(abs(x) >= 10 for x in mv), 'vs096_ge5': sum(abs(x) >= 5 for x in mv96),
         'ovr_up': sum(x > 0 for x in d_ovr), 'ovr_down': sum(x < 0 for x in d_ovr), 'ovr_same': sum(x == 0 for x in d_ovr),
         'median_dOVR': float(np.median(d_ovr)), 'n': len(mv)}
top10 = [r['name'] for r in e101[:10]]
top10_025 = sorted(c025, key=lambda n: int(c025[n]['rank']))[:10]
res = {'anchors': [p1, p50, p99], 'ovrRankMismatches': mism[:10], 'nMismatch': len(mism), 'players': rows, 'valuePer10': val, 'moves': moves,
       'top10_e101': top10, 'top10_overlap_with_025': len(set(top10) & set(top10_025)), 'top10_025': top10_025}
(Path(__file__).parent/'a6_cards.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
