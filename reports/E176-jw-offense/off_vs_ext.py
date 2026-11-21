"""E-176：2025-26 卡片 OFF 名次 vs 同季外部進攻（DARKO O、EPM O、OBPM）名次。同季＝樣本內，只看方向（R-007）。"""
import csv, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata, spearmanr
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import season_nav as SN
# 賽中檔（有 playerId）；MIN＝2025-26 分鐘，能力值近似先驗卡
card = [r for r in csv.DictReader(open(ROOT / 'reports/ovr-inseason-2026-27/live/2026-10-31/ranking.csv', encoding='utf-8-sig')) if float(r['MIN']) >= 900]
od, _ = SN.off_def(card, 'playerId')
def load(f, col, filt=None):
    rs = list(csv.DictReader(open(ROOT / 'data/external-impact' / f, encoding='utf-8-sig')))
    return {r['playerId']: float(r[col]) for r in rs if r[col] not in ('', None)}
ext = {'DARKO': load('darko/darko_2025-26.csv', 'o_dpm'), 'EPM': load('epm_self/epm_2025-26.csv', 'O'), 'OBPM': load('bpm/bpm_2025-26.csv', 'obpm')}
ids = [r['playerId'] for r in card if od[r['playerId']][0] is not None and all(r['playerId'] in e for e in ext.values())]
R = {r['playerId']: r for r in card}
off = np.array([od[i][0] for i in ids])
z = lambda x: (rankdata(x) - 0.5) / len(x)
ez = np.mean([z(np.array([ext[k][i] for i in ids])) for k in ext], axis=0)
res = ez - z(off)  # 負＝卡片 OFF 排得比外部高
print('n', len(ids), 'rho(OFF, ext avg)', round(spearmanr(off, ez)[0], 3))
pos = np.array([R[i]['pos'] for i in ids])
for a in ['pass', 'creation', 'drive', 'tovSkill', 'foulDraw', 'long']:
    x = np.array([float(R[i][a]) for i in ids])
    print(f'{a:9s} S(attr,res) all {spearmanr(x, res)[0]:+.3f}', ' '.join(f'{p}:{spearmanr(x[pos==p], res[pos==p])[0]:+.3f}(n{(pos==p).sum()})' for p in ['PG','SG','SF','PF','C']))
print('mean res by pos', {p: round(float(res[pos == p].mean()), 3) for p in ['PG', 'SG', 'SF', 'PF', 'C']})
n = len(ids)
order = np.argsort(-off)
print('\nTop 30 卡片 OFF：名次 / 外部平均名次')
for k, j in enumerate(order[:30]):
    i = ids[j]
    print(f"{k+1:3d} {R[i]['name']:24s} {R[i]['pos']:3s} OFF {off[j]:+.2f}  ext名次 {int(n - ez[j]*n + 0.5):3d}  pass {R[i]['pass']}")
