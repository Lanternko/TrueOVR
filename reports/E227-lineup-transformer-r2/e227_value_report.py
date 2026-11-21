"""讀 results/value-raw.json，對外部指標算相關與名次表，寫 results/value.json（只報告項）。
外部指標（2025-26 賽季）：卡 OVR（正式 reports/card-0.2.12c/ranking.csv；E-225 資料檔的 v4 ovr 當輔助欄）、網站 OVR（reports/games-view/site/ranking.csv，2026-11-02 版）、
2K26（2k-merged-e142.csv 的 2K26 欄，開賣或賽季中快照）、薪水（BR contracts2025.html 的 y2＝2025-26）、BPM（bpm_2025-26.csv）、
RAPM（card-0.2.10+E186 base-K6U-2025-26 的 pooledO/pooledD）。
"""
import csv, html, json, os, re, sys, unicodedata
import numpy as np
from scipy.stats import pearsonr, rankdata, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
raw = json.load(open(os.path.join(HERE, 'results', 'value-raw.json'), encoding='utf-8'))
pids = raw['pids']; names = raw['names']; n = len(pids)
MODELS = ['R2-abil', 'R2-stats', 'R2-stats-rapm', 'E225-T-nomin']
V = {m: np.array(raw['new'][m]) for m in MODELS}


def norm(s):
    s = unicodedata.normalize('NFKD', html.unescape(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r"[.']", '', s); s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return re.sub(r'[^a-z]', '', s)


nk = [norm(x) for x in names]
card = {norm(r['name']): float(r['ovr']) for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'card-0.2.12c', 'ranking.csv'), encoding='utf-8'))}   # 正式 2025-26 卡 0.2.12c
v4 = {r['pid']: float(r['ovr']) for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'E225-lineup-transformer', 'data', 'players-2025-26.csv'), encoding='utf-8'))}   # E-225 資料檔的舊 v4 ovr（輔助）
site_rows = list(csv.DictReader(open(os.path.join(ROOT, 'reports', 'games-view', 'site', 'ranking.csv'), encoding='utf-8')))
site = {r['playerId']: float(r['ovr']) for r in site_rows}
k26 = {norm(r['name']): float(r['2K26']) for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'external-impact', '2k', '2k-merged-e142.csv'), encoding='utf-8')) if r.get('2K26')}
rr = {r['playerId']: r for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'card-0.2.10+E186-t6-rapm-target', 'work', 'base-K6U-2025-26', 'c0', 'rapm-R.csv'), encoding='utf-8'))}
bp = {r['playerId']: r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'external-impact', 'bpm', 'bpm_2025-26.csv'), encoding='utf-8'))}


def salaries(f):
    s = open(f, encoding='utf-8').read(); rows = {}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', s, re.S):
        m = re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row); y = re.search(r'data-stat="y2"[^>]*>\$?([\d,]+)', row)
        if m and y:
            rows.setdefault(norm(m.group(1)), []).append(int(y.group(1).replace(',', '')))
    return {k: v[0] for k, v in rows.items() if len(v) == 1 or True}


sal = salaries(os.path.join(ROOT, 'reports', 'salary-corr', 'source', 'contracts2025.html'))


def col(f):
    return np.array([f(i) if f(i) is not None else np.nan for i in range(n)], float)


metrics = {
    '2025-26 卡 OVR': col(lambda i: card.get(nk[i])),
    'v4 卡 OVR（E-225 資料檔，輔助）': col(lambda i: v4.get(pids[i])),
    '網站 OVR（2026-11-02）': col(lambda i: site.get(pids[i])),
    '2K26 overall': col(lambda i: k26.get(nk[i])),
    '薪水 2025-26（取 log 算 Pearson）': col(lambda i: sal.get(nk[i])),
    'BPM 2025-26': col(lambda i: float(bp[pids[i]]['bpm']) if pids[i] in bp else None),
    'RAPM 進攻 2025-26': col(lambda i: float(rr[pids[i]]['pooledO']) if pids[i] in rr else None),
    'RAPM 防守 2025-26': col(lambda i: float(rr[pids[i]]['pooledD']) if pids[i] in rr else None),
}
corr = {}
for m, x in metrics.items():
    ok = ~np.isnan(x)
    for mod in MODELS:
        xx = np.log(x[ok]) if m.startswith('薪水') else x[ok]
        corr.setdefault(m, {})[mod] = {'n': int(ok.sum()), 'spearman': round(float(spearmanr(V[mod][ok], x[ok])[0]), 3), 'pearson': round(float(pearsonr(V[mod][ok], xx)[0]), 3)}
armcorr = {f'{a}~{b}': round(float(spearmanr(V[a], V[b])[0]), 3) for i, a in enumerate(MODELS) for b in MODELS[i + 1:]}

# 排名：以有 2025-26 卡 OVR 的球員為母體
ok = ~np.isnan(metrics['2025-26 卡 OVR']); idx = np.where(ok)[0]; cov = metrics['2025-26 卡 OVR'][idx]
rank = {m: rankdata(-V[m][idx], method='min').astype(int) for m in MODELS}; crank = rankdata(-cov, method='min').astype(int)


def row(j):
    i = idx[j]
    return {'pid': pids[i], 'name': names[i], 'min': raw['min'][i], 'pos': raw['modalPos'][i], 'cardOvr': float(cov[j]), 'cardRank': int(crank[j]),
            'value': {m: round(float(V[m][i]), 3) for m in MODELS}, 'valueRank': {m: int(rank[m][j]) for m in MODELS}, 'diff': int(rank['R2-stats'][j] - crank[j])}


top20 = {m: [row(j) for j in np.argsort(rank[m], kind='stable')[:20]] for m in MODELS}
d = rank['R2-stats'] - crank   # >0：價值名次比卡名次差＝卡偏高（高估）
over = [row(j) for j in np.argsort(-d, kind='stable')[:15]]
under = [row(j) for j in np.argsort(d, kind='stable')[:15]]
wings = ['Dean Wade', 'Tari Eason', 'Luguentz Dort', 'Herbert Jones', 'Alex Caruso', 'Derrick White', 'OG Anunoby', 'Dillon Brooks', 'Draymond Green', 'Jalen Suggs']
wing = []
for w in wings:
    js = [j for j in range(len(idx)) if nk[idx[j]] == norm(w)]
    if js:
        wing.append(row(js[0]))
    else:
        wing.append({'name': w, 'missing': '不在母體（2025-26 上場 <1000 分鐘或無卡 OVR）'})
allrows = [{'pid': pids[i], 'name': names[i], 'min': raw['min'][i], 'pos': raw['modalPos'][i], 'value': {m: round(float(V[m][i]), 3) for m in MODELS}} for i in range(n)]
out = {'ndraw': raw['ndraw'], 'nEligible': n, 'nWithCard': int(ok.sum()), 'modelSpearman': armcorr, 'correlations': corr, 'top20': top20, 'overrated15': over, 'underrated15': under,
       'defWings': wing, 'rankedBy': 'R2-stats 價值名次 vs 2025-26 卡 OVR 名次（母體＝有卡 OVR 者）', 'all': allrows}
json.dump(out, open(os.path.join(HERE, 'results', 'value.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('n', n, 'with card', int(ok.sum())); print(armcorr)
for m, v in corr.items():
    print(m, {k: (x['spearman'], x['pearson']) for k, x in v.items()}, 'n', v[MODELS[0]]['n'])
for t, lst in [('TOP20 R2-stats', top20['R2-stats']), ('OVER', over), ('UNDER', under), ('WINGS', wing)]:
    print(t)
    for r in lst:
        if 'missing' in r: print('  ', r['name'], r['missing']); continue
        print(f"  {r['name']:24s} min {r['min']:6.0f} card {r['cardOvr']:5.1f} #{r['cardRank']:3d} | " + ' '.join(f"{m.replace('R2-', '')}:{r['valueRank'][m]:3d}({r['value'][m]:5.2f})" for m in MODELS))
