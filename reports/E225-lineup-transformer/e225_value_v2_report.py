"""讀 results/value-v2-raw.json，對外部指標算相關、排名表，寫 results/value-v2.json。"""
import csv, json, os, re, sys
import numpy as np
from scipy.stats import pearsonr, spearmanr, rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_value_v2 import norm
from e225_common import HERE

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
raw = json.load(open(os.path.join(HERE, 'results', 'value-v2-raw.json')))
pids = raw['pids']; n = len(pids)
pl = {r['pid']: r for r in csv.DictReader(open(os.path.join(HERE, 'data', 'players-2024-25.csv'), encoding='utf-8'))}
names = [pl[p]['name'] for p in pids]; nk = [norm(x) for x in names]
newv = (np.array(raw['new']['T-min']) + np.array(raw['new']['T-nomin'])) / 2
oldv = (np.array(raw['old']['T-min']) + np.array(raw['old']['T-nomin'])) / 2

# 網站 OVR：網站現行排名檔（賽中 0.2.12c，2026-11-02 版），以 playerId 對
site_f = os.path.join(ROOT, 'reports', 'games-view', 'site', 'ranking.csv')
site_rows = list(csv.DictReader(open(site_f, encoding='utf-8')))
site_check = {int(r['rank']): (r['name'], r['ovr']) for r in site_rows if int(r['rank']) in (21, 22, 23, 24)}
site = {r['playerId']: float(r['ovr']) for r in site_rows}
# 2025-26 卡 0.2.12c（輔助欄）
c26 = {r['playerId']: float(r['ovr']) for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'card-0.2.12c', 'ranking.csv'), encoding='utf-8')) if r.get('playerId')}
v4 = {p: float(pl[p]['ovr']) for p in pids}

# 薪水：BR 2024-25 合約頁 y1
def salaries(f):
    s = open(f, encoding='utf-8').read(); rows = {}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', s, re.S):
        m = re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row); y = re.search(r'data-stat="y1"[^>]*>\$?([\d,]+)', row)
        g = re.search(r'data-stat="remain_gtd"[^>]*>\$?([\d,]+)', row)
        if m and y: rows.setdefault(norm(m.group(1)), []).append((int(y.group(1).replace(',', '')), int(g.group(1).replace(',', '')) if g else 0))
    return {k: (v[0][0] if len(v) == 1 else min(v[0][0], min(x[1] for x in v))) for k, v in rows.items()}
sal = salaries(os.path.join(ROOT, 'reports', 'salary-corr', 'source', 'contracts2025.html'))
# 2K25：data/external-impact/2k/2k-merged-e142.csv 的 2K25 欄（2K25 發行期 Wayback 快照）
k25 = {norm(r['name']): float(r['2K25']) for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'external-impact', '2k', '2k-merged-e142.csv'), encoding='utf-8')) if r.get('2K25')}
# RAPM：多季合併至 2024-25（E-186 base-K6-2024-25）
rr = {r['playerId']: r for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'card-0.2.10+E186-t6-rapm-target', 'work', 'base-K6-2024-25', '2024-25', 'rapm-R.csv'), encoding='utf-8'))}
bp = {r['playerId']: r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'external-impact', 'bpm', 'bpm_2024-25.csv'), encoding='utf-8'))}

def col(f):
    return np.array([f(i) if f(i) is not None else np.nan for i in range(n)], float)

metrics = {
    '網站OVR（賽中0.2.12c，2026-11-02）': col(lambda i: site.get(pids[i])),
    'v4卡OVR（2024-25）': col(lambda i: v4[pids[i]]),
    '2025-26卡OVR（0.2.12c）': col(lambda i: c26.get(pids[i])),
    '薪水2024-25（BR合約頁，取log算Pearson）': col(lambda i: sal.get(nk[i])),
    '2K25 overall（發行期快照）': col(lambda i: k25.get(nk[i])),
    'RAPM淨值（多季合併至2024-25）': col(lambda i: float(rr[pids[i]]['pooledNet']) if pids[i] in rr else None),
    'RAPM進攻（同上）': col(lambda i: float(rr[pids[i]]['pooledO']) if pids[i] in rr else None),
    'RAPM防守（同上）': col(lambda i: float(rr[pids[i]]['pooledD']) if pids[i] in rr else None),
    'BPM（BR 2024-25）': col(lambda i: float(bp[pids[i]]['bpm']) if pids[i] in bp else None),
    '舊算法價值（聯盟中位數陣容）': oldv,
}
corr = {}
for lab, name_ in [('新價值', newv), ('舊價值', oldv)]:
    for m, x in metrics.items():
        ok = ~np.isnan(x)
        xx = np.log(x[ok]) if m.startswith('薪水') else x[ok]
        if ok.sum() < 10: corr.setdefault(m, {})[lab] = None; continue
        sp = float(spearmanr(name_[ok], x[ok])[0]); pr = float(pearsonr(name_[ok], xx)[0])
        corr.setdefault(m, {})[lab] = {'n': int(ok.sum()), 'spearman': round(sp, 3), 'pearson': round(pr, 3)}
# 新價值跟兩臂各自（穩定度）
arms = {a: np.array(raw['new'][a]) for a in raw['new']}
armcorr = float(spearmanr(arms['T-min'], arms['T-nomin'])[0])

# 排名：以網站 OVR 有值的球員為母體
ok = ~np.isnan(metrics['網站OVR（賽中0.2.12c，2026-11-02）'])
idx = np.where(ok)[0]
sov = metrics['網站OVR（賽中0.2.12c，2026-11-02）']
vr = rankdata(-newv[idx], method='min').astype(int); orr = rankdata(-sov[idx], method='min').astype(int)
def row(j):
    i = idx[j]
    return {'pid': pids[i], 'name': names[i], 'pos': pl[pids[i]]['pos'], 'min': raw['min'][i], 'value': round(float(newv[i]), 3), 'oldValue': round(float(oldv[i]), 3),
            'valueRank': int(vr[j]), 'siteOvr': float(sov[i]), 'siteOvrRank': int(orr[j]), 'v4Ovr': v4[pids[i]], 'diff': int(vr[j] - orr[j])}
order = np.argsort(vr, kind='stable')
top20 = [row(j) for j in order[:20]]
d = vr - orr   # >0：價值名次比網站OVR名次差＝高估
over = [row(j) for j in np.argsort(-d, kind='stable')[:15]]
under = [row(j) for j in np.argsort(d, kind='stable')[:15]]
# 全球員的完整表（含沒有網站OVR的人）
allrows = [{'pid': pids[i], 'name': names[i], 'min': raw['min'][i], 'value': round(float(newv[i]), 3), 'valueTmin': round(float(arms['T-min'][i]), 3), 'valueTnomin': round(float(arms['T-nomin'][i]), 3), 'oldValue': round(float(oldv[i]), 3)} for i in range(n)]
out = {'ndraw': raw['ndraw'], 'nEligible': n, 'nWithSiteOvr': int(ok.sum()), 'armSpearman': round(armcorr, 3),
       'siteRankingCheck': {str(k): v for k, v in site_check.items()}, 'siteRankingFile': 'reports/games-view/site/ranking.csv',
       'correlations': corr, 'top20': top20, 'overrated15': over, 'underrated15': under, 'all': allrows}
json.dump(out, open(os.path.join(HERE, 'results', 'value-v2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('site check', site_check); print('arm spearman', armcorr, 'n site', int(ok.sum()))
for m, v in corr.items(): print(m, v)
for t, lst in [('TOP20', top20), ('OVER', over), ('UNDER', under)]:
    print(t)
    for r in lst: print(f"  {r['name']:26s} {r['pos']:6s} val {r['value']:6.2f} old {r['oldValue']:6.2f} vrank {r['valueRank']:3d} siteOVR {r['siteOvr']:5.1f} #{r['siteOvrRank']:3d} v4 {r['v4Ovr']:5.1f} diff {r['diff']}")
