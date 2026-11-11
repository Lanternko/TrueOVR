# 診斷（樣本內，只報告）：2025-26 無球外線引力 vs card 0.2.10g 對 T6 的低估量
import json, csv, numpy as np
from pathlib import Path
from scipy.stats import spearmanr
here = Path(__file__).parent; root = here.parents[2]
G = {str(x['PLAYERID']): x for x in json.load(open(here / 'gravity-2025-26.json', encoding='utf-8'))}
card = {r['name']: r for r in csv.DictReader(open(root / 'reports/card-0.2.10g/ranking.csv', encoding='utf-8')) if float(r['MIN']) >= 500}
t6 = {t['name']: t for t in csv.DictReader(open(root / 'reports/card-0.2.10g/rapm-T6.csv', encoding='utf-8')) if float(t['pooledPoss']) >= 5000}
pid = {t['name']: t['playerId'] for t in t6.values()}
n = [k for k in card if k in t6 and pid[k] in G]
p = np.array([float(card[k]['pred0']) for k in n]); t = np.array([float(t6[k]['pooledNet']) for k in n])
b = np.polyfit(t, p, 1); res = t - (p - b[1]) / b[0]          # 正＝卡片低估
f = lambda k, c: float(G[pid[k]][c] or 0)
feat = {
  'avg': np.array([f(k, 'AVGGRAVITYSCORE') for k in n]),
  'offPer': np.array([f(k, 'AVGOFFBALLPERIMETERGRAVITYSCORE') for k in n]),
  'offPerShare': np.array([f(k, 'OFFBALLPERIMETERFRAMES') / max(f(k, 'FRAMES'), 1) for k in n]),
  'offPerTot': np.array([f(k, 'OFFBALLPERIMETERGRAVITYSCORE') / max(f(k, 'FRAMES'), 1) for k in n]),
  'onPer': np.array([f(k, 'AVGONBALLPERIMETERGRAVITYSCORE') for k in n]),
}
lg = np.array([float(card[k]['long']) for k in n]); cr = np.array([float(card[k]['creation']) for k in n])
cs = (lg >= 75) & (cr <= 60)
out = {'n': len(n), 'n_cs': int(cs.sum())}
for c, v in feat.items():
  a, b2 = spearmanr(v, res), spearmanr(v[cs], res[cs])
  out[c] = {'all': [round(a.statistic, 3), round(a.pvalue, 4)], 'catchShoot': [round(b2.statistic, 3), round(b2.pvalue, 4)]}
  print(f'{c:12s} 全體 ρ {a.statistic:+.3f} (p {a.pvalue:.3f})  接球射手 ρ {b2.statistic:+.3f} (p {b2.pvalue:.3f})')
r_res = res.argsort().argsort(); pr = {c: (v.argsort().argsort() / len(v) * 100) for c, v in feat.items()}
names = ['Klay Thompson', 'Sam Hauser', 'Keon Ellis', 'Duncan Robinson', 'Luke Kennard', 'AJ Green', 'Isaiah Joe', 'Sam Merrill',
         'Donte DiVincenzo', 'Moses Moody', 'Aaron Nesmith', 'Josh Minott', 'Stephen Curry', 'Cameron Johnson', 'Grant Williams', 'Al Horford', 'Buddy Hield', 'Michael Porter Jr.', 'Kevin Huerter']
cr_rank = {k: i + 1 for i, k in enumerate(sorted(n, key=lambda k: -float(card[k]['pred0'])))}
t_rank = {k: i + 1 for i, k in enumerate(sorted(n, key=lambda k: -float(t6[k]['pooledNet'])))}
ex = []
for k in names:
  if k in n:
    i = n.index(k); ex.append([k, round(feat['offPer'][i], 1), round(pr['offPer'][i]), round(pr['offPerTot'][i]), cr_rank[k], t_rank[k], round(res[i], 2)])
    print(f'{k:20s} 無球外線 {feat["offPer"][i]:5.1f} 百分位 {pr["offPer"][i]:3.0f} 總量百分位 {pr["offPerTot"][i]:3.0f}  卡 {cr_rank[k]:3d} T6 {t_rank[k]:3d}  低估 {res[i]:+.2f}')
  else: print(k, '無資料')
out['examples'] = ex
json.dump(out, open(here / 'diag_offball.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
