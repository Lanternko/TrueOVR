"""E-308：OVR 是否系統性低估高 On/Off 球員（照 preregistration.md 跑；資料讀主 checkout 的 gitignored 檔）。

用法：python -I reports/E308-onoff-undervalue/e308_run.py [主 checkout 路徑]
輸出：同目錄 results.json、players.csv（人群每人數值）
"""
import csv
import json
import math
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
M = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('D:/Projects/CODING/basketball-autochess')
sys.path.insert(0, str(M / 'reports/impact-rapm'))
import rapm  # noqa: E402

SD1 = 115.0  # 每 100 回合、每回合得分標準差 1.15
B = 2000
rng = np.random.default_rng(308)
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'onBall', 'help', 'heightInches', 'creation', 'pressure', 'gravity']


def fold(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in n if c.isalnum())


def se_oo(p, q):
    return SD1 * math.sqrt(2 / p + 2 / q)


def rd(path):
    return list(csv.DictReader(open(path, encoding='utf-8')))


# ---------- 名字 → playerId ----------
name2id = {}
for path, nk in [(M / 'reports/impact-rapm/onoff.csv', 'name'), (M / 'reports/impact-rapm/rapm-prior.csv', 'name'),
                 (M / 'reports/ovr-inseason-2026-27/live/2026-11-21/ranking.csv', 'name'), (M / 'reports/card-0.2.15/gravity-attr.csv', 'name')]:
    for r in rd(path):
        if r.get('playerId'):
            name2id.setdefault(fold(r[nk]), int(float(r['playerId'])))

card = {}
unmatched = []
for r in rd(M / 'reports/card-0.2.15/ranking.csv'):
    pid = name2id.get(fold(r['name']))
    if pid is None:
        unmatched.append(r['name'])
        continue
    card[pid] = r
grav = {int(r['playerId']): float(r['gravity']) for r in rd(M / 'reports/card-0.2.15/gravity-attr.csv')}
for pid, r in card.items():
    r['gravity'] = grav.get(pid, float('nan'))

# ---------- 歷年 on/off（onoff.csv） ----------
def agg_onoff(rows):
    """rows: (pid, team, p, q, oo, onNet) → pid → dict(p, q, oo, se, team)；同季多隊依 p 加權。"""
    acc = defaultdict(list)
    for pid, team, p, q, oo, onnet in rows:
        if p > 0 and q > 0 and oo is not None:
            acc[pid].append((team, p, q, oo, onnet))
    out = {}
    for pid, L in acc.items():
        P = sum(x[1] for x in L)
        oo = sum(x[1] * x[3] for x in L) / P
        se = math.sqrt(sum((x[1] * se_oo(x[1], x[2])) ** 2 for x in L)) / P
        team = max(L, key=lambda x: x[1])[0]
        out[pid] = {'p': P, 'q': sum(x[2] for x in L), 'oo': oo, 'se': se, 'team': team, 'on': sum(x[1] * x[4] for x in L) / P}
    return out


hist = defaultdict(list)
for r in rd(M / 'reports/impact-rapm/onoff.csv'):
    if r['onOffNet']:
        hist[r['season']].append((int(r['playerId']), int(r['teamId']), float(r['onPoss']) / 2, float(r['offPoss']) / 2, float(r['onOffNet']), float(r['onNet'])))
OO = {s: agg_onoff(v) for s, v in hist.items()}
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']

prior = {int(r['playerId']): r for r in rd(M / 'reports/impact-rapm/rapm-prior.csv')}
darko = {int(r['playerId']): float(r['dpm']) for r in rd(M / 'data/external-impact/darko/darko_2025-26.csv') if r['dpm']}

# ---------- 人群與 OO4 ----------
pool = [pid for pid in card if pid in OO['2025-26'] and OO['2025-26'][pid]['p'] >= 1000]
X = {}
for pid in pool:
    L = [(OO[s][pid]['p'], OO[s][pid]['oo'], OO[s][pid]['se']) for s in SEASONS if pid in OO[s]]
    P = sum(x[0] for x in L)
    X[pid] = {'oo4': sum(x[0] * x[1] for x in L) / P, 'se4': math.sqrt(sum((x[0] * x[2]) ** 2 for x in L)) / P, 'p4': P,
              'ovr': float(card[pid]['ovr']), 'ovr36': float(card[pid]['ovr36']), 'pos': card[pid]['pos'], 'name': card[pid]['name'],
              'rank': int(card[pid]['rank']), 'team25': OO['2025-26'][pid]['team'], 'oo25': OO['2025-26'][pid]['oo'],
              'rapm': float(prior[pid]['pooledNet']) if pid in prior else None, 'darko': darko.get(pid)}
oo4 = np.array([X[p]['oo4'] for p in pool]); se4 = np.array([X[p]['se4'] for p in pool]); w4 = np.array([X[p]['p4'] for p in pool])
m = float(np.average(oo4, weights=w4))
tau2 = max(0.0, float(np.var(oo4, ddof=1) - np.mean(se4 ** 2)))
for i, pid in enumerate(pool):
    X[pid]['oo4s'] = m + tau2 / (tau2 + se4[i] ** 2) * (oo4[i] - m)
    X[pid]['shrink'] = tau2 / (tau2 + se4[i] ** 2)


def resid(pids, key, xkey='ovr'):
    pids = [p for p in pids if X[p].get(key) is not None]
    x = np.array([X[p][xkey] for p in pids]); y = np.array([X[p][key] for p in pids])
    A = np.c_[np.ones_like(x), x]
    b = np.linalg.lstsq(A, y, rcond=None)[0]
    return {p: float(y[i] - A[i] @ b) for i, p in enumerate(pids)}, b


for key, rk in [('oo4s', 'R_OO'), ('rapm', 'R_RAPM'), ('darko', 'R_DARKO')]:
    res, _ = resid(pool, key)
    for p in pool:
        X[p][rk] = res.get(p)

# ---------- 2026-27 ----------
obs27 = list(rapm.observations(['2026-27']))
y1rows = []
for r in rapm.onoff(obs27):
    if 'onOffNet' in r:
        y1rows.append((r['playerId'], r['teamId'], r['onPoss'] / 2, r['offPoss'] / 2, r['onOffNet'], r['onNet']))
Y1 = agg_onoff(y1rows)
players27 = sorted({p for o in obs27 for p in o[2] + o[3]})
fit27, info27 = rapm.fit_rapm(obs27, players27)
last_stint_game = max(o[1] for o in obs27)
for p in pool:
    if p in Y1:
        X[p].update(y1=Y1[p]['oo'], p27=Y1[p]['p'], q27=Y1[p]['q'], team27=Y1[p]['team'], se27=se_oo(Y1[p]['p'], Y1[p]['q']))
    if p in fit27:
        X[p]['y2'] = fit27[p]['net']
h1 = [p for p in pool if X[p].get('p27', 0) >= 300 and X[p].get('q27', 0) >= 100 and 'y2' in X[p]]


def z(v):
    v = np.asarray(v, float)
    return (v - v.mean()) / v.std(ddof=0)


def wls(pids, ykey, cols):
    y = np.array([X[p][ykey] for p in pids]); w = np.array([X[p]['p27'] for p in pids])
    A = np.c_[np.ones(len(pids)), *[z([X[p][c] for p in pids]) for c in cols]]
    sw = np.sqrt(w)
    return np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)[0]


def boot(pids, ykey, cols, cluster='team27'):
    teams = defaultdict(list)
    for p in pids:
        teams[X[p][cluster]].append(p)
    keys = list(teams)
    est = wls(pids, ykey, cols)
    bs = []
    for _ in range(B):
        samp = [p for k in rng.choice(len(keys), len(keys)) for p in teams[keys[k]]]
        try:
            bs.append(wls(samp, ykey, cols))
        except np.linalg.LinAlgError:
            pass
    bs = np.array(bs)
    lo, hi = np.percentile(bs, [5, 95], axis=0)
    return {'n': len(pids), 'coef': dict(zip(['a'] + cols, est.round(3).tolist())),
            'ci90': {c: [round(float(lo[i]), 3), round(float(hi[i]), 3)] for i, c in enumerate(['a'] + cols)}}


H1 = {}
for ykey in ['y1', 'y2']:
    base = [p for p in h1]
    H1[ykey] = {
        'R_OO': boot(base, ykey, ['ovr', 'R_OO']),
        'R_RAPM': boot([p for p in base if X[p]['R_RAPM'] is not None], ykey, ['ovr', 'R_RAPM']),
        'R_DARKO': boot([p for p in base if X[p]['R_DARKO'] is not None], ykey, ['ovr', 'R_DARKO']),
        'R_OO+R_RAPM': boot([p for p in base if X[p]['R_RAPM'] is not None], ykey, ['ovr', 'R_OO', 'R_RAPM']),
        'stayers': boot([p for p in base if X[p]['team27'] == X[p]['team25']], ykey, ['ovr', 'R_OO']),
        'movers': boot([p for p in base if X[p]['team27'] != X[p]['team25']], ykey, ['ovr', 'R_OO']),
        'ovr36': boot(base, ykey, ['ovr36', 'R_OO']),
    }


def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ra = a.argsort().argsort(); rb = b.argsort().argsort()
    return float(np.corrcoef(ra, rb)[0, 1])


SP = {}
for ykey in ['y1', 'y2']:
    SP[ykey] = {}
    for k in ['ovr', 'ovr36', 'oo4s', 'oo25', 'rapm', 'darko']:
        ps = [p for p in h1 if X[p].get(k) is not None]
        SP[ykey][k] = {'n': len(ps), 'rho': round(spearman([X[p][k] for p in ps], [X[p][ykey] for p in ps]), 3)}
    ps = [p for p in h1 if X[p].get('darko') is not None and X[p].get('rapm') is not None]
    SP[ykey]['common_n'] = len(ps)
    SP[ykey]['common'] = {k: round(spearman([X[p][k] for p in ps], [X[p][ykey] for p in ps]), 3) for k in ['ovr', 'oo4s', 'rapm', 'darko']}

# ---------- H2 類型 ----------
def pct(key, q):
    return float(np.percentile([float(card[p][key]) for p in pool], q))


fin = {p: (float(card[p]['long']) + float(card[p]['mid']) + float(card[p]['short'])) / 3 for p in pool}
fin_med = float(np.median(list(fin.values())))
th = {'creation75': pct('creation', 75), 'creation50': pct('creation', 50), 'long60': pct('long', 60),
      'onBall60': pct('onBall', 60), 'pressure60': pct('pressure', 60), 'help75': pct('help', 75), 'fin50': fin_med}


def group(p):
    c = card[p]; f = lambda k: float(c[k])
    if c['pos'] in ('PG', 'SG') and f('creation') >= th['creation75'] and fin[p] <= th['fin50']:
        return 'G1'
    if c['pos'] in ('SG', 'SF') and f('long') >= th['long60'] and (f('onBall') >= th['onBall60'] or f('pressure') >= th['pressure60']) and f('creation') <= th['creation50']:
        return 'G2'
    if c['pos'] in ('C', 'PF') and f('help') >= th['help75']:
        return 'G3'
    return 'G0'


for p in pool:
    X[p]['grp'] = group(p)
# 樣本外：Y 對 OVR 單變量 WLS 殘差
for ykey in ['y1', 'y2']:
    b = wls(h1, ykey, ['ovr'])
    zo = z([X[p]['ovr'] for p in h1])
    for i, p in enumerate(h1):
        X[p][ykey + 'r'] = X[p][ykey] - (b[0] + b[1] * zo[i])


def grp_mean(pids, key, wkey=None, cluster='team25'):
    teams = defaultdict(list)
    for p in pids:
        teams[X[p][cluster]].append(p)
    keys = list(teams)
    f = lambda ps: float(np.average([X[p][key] for p in ps], weights=[X[p][wkey] for p in ps] if wkey else None))
    bs = [f(s) for s in ([p for k in rng.choice(len(keys), len(keys)) for p in teams[keys[k]]] for _ in range(B)) if s]
    return {'n': len(pids), 'mean': round(f(pids), 2), 'ci90': [round(float(np.percentile(bs, 5)), 2), round(float(np.percentile(bs, 95)), 2)]}


H2 = {'thresholds': {k: round(v, 1) for k, v in th.items()}}
for g in ['G1', 'G2', 'G3', 'G0']:
    ps = [p for p in pool if X[p]['grp'] == g]
    ps1 = [p for p in h1 if X[p]['grp'] == g]
    H2[g] = {'members': sorted([X[p]['name'] for p in ps]),
             'R_OO_in': grp_mean(ps, 'R_OO'),
             'y2r_oos': grp_mean(ps1, 'y2r', 'p27', 'team27') if len(ps1) >= 3 else None,
             'y1r_oos': grp_mean(ps1, 'y1r', 'p27', 'team27') if len(ps1) >= 3 else None}

# ---------- H3 ----------
obs26 = list(rapm.observations(['2025-26']))
halves = {}
for h in (0, 1):
    rows = []
    for r in rapm.onoff([o for o in obs26 if int(o[1]) % 2 == h]):
        if 'onOffNet' in r:
            rows.append((r['playerId'], r['teamId'], r['onPoss'] / 2, r['offPoss'] / 2, r['onOffNet'], r['onNet']))
    halves[h] = agg_onoff(rows)
h3 = [p for p in pool if all(p in halves[h] and halves[h][p]['p'] >= 300 and halves[h][p]['q'] >= 100 for h in (0, 1))]
for p in h3:
    X[p]['ooA'] = halves[0][p]['oo']; X[p]['ooB'] = halves[1][p]['oo']
rA, _ = resid(h3, 'ooA'); rB, _ = resid(h3, 'ooB')
r_res = float(np.corrcoef([rA[p] for p in h3], [rB[p] for p in h3])[0, 1])
r_raw = float(np.corrcoef([X[p]['ooA'] for p in h3], [X[p]['ooB'] for p in h3])[0, 1])
sb = lambda r: 2 * r / (1 + r)
# 逐年
yy = [p for p in pool if p in OO['2024-25'] and OO['2024-25'][p]['p'] >= 1000]
for p in yy:
    X[p]['oo24'] = OO['2024-25'][p]['oo']
r24, _ = resid(yy, 'oo24'); r25, _ = resid(yy, 'oo25')
stay = [p for p in yy if OO['2024-25'][p]['team'] == OO['2025-26'][p]['team']]
move = [p for p in yy if p not in stay]
cor = lambda ps, a, b: round(float(np.corrcoef([a[p] for p in ps], [b[p] for p in ps])[0, 1]), 3)
H3 = {'splitHalf': {'n': len(h3), 'r_resid': round(r_res, 3), 'SB_resid': round(sb(r_res), 3), 'r_raw': round(r_raw, 3), 'SB_raw': round(sb(r_raw), 3)},
      'yearToYear': {'n': len(yy), 'all': cor(yy, r24, r25), 'stayers': {'n': len(stay), 'r': cor(stay, r24, r25)},
                     'movers': {'n': len(move), 'r': cor(move, r24, r25)},
                     'raw_all': cor(yy, {p: X[p]['oo24'] for p in yy}, {p: X[p]['oo25'] for p in yy})}}

# ---------- 判定 ----------
ci = lambda ykey, arm='R_OO': H1[ykey][arm]['ci90']['R_OO']
pos = lambda c: c[0] > 0
cross0 = lambda c: c[0] <= 0 <= c[1]
verdict = []
if pos(ci('y2')):
    verdict.append('rule1: 模型漏掉東西（Y2 b2 區間 > 0）')
elif pos(ci('y1')):
    verdict.append('rule1b: 只在 on/off 裡持續（Y1 > 0、Y2 跨 0），不算模型漏掉')
if cross0(ci('y1')) and cross0(ci('y2')) and H3['splitHalf']['SB_resid'] < 0.3:
    verdict.append('rule2: 雜訊為主')
if (H3['yearToYear']['stayers']['r'] - H3['yearToYear']['movers']['r'] >= 0.15) and cross0(H1['y1']['movers']['ci90']['R_OO']):
    verdict.append('rule3: 殘差主要跟著球隊走')
for g in ['G1', 'G2', 'G3']:
    o = H2[g]['y2r_oos']
    if o and (o['ci90'][0] > 0 or o['ci90'][1] < 0):
        verdict.append(f'rule4: {g} 樣本外 Y2 殘差 {o["mean"]:+.2f} 區間 {o["ci90"]}')
if not verdict:
    verdict.append('無規則觸發（介於雜訊與訊號之間）')

# ---------- LaMelo ----------
LM = name2id[fold('LaMelo Ball')]
pg = [p for p in card if card[p]['pos'] == 'PG' and float(card[p]['mpg']) >= 20]
v10 = json.load(open(M / 'reports/card-0.2.15-w246/cards/K6/primary/summary.json', encoding='utf-8'))['valuePer10AttributePoints']
contrib = {}
for a in ATTRS:
    vals = [float(card[p][a]) for p in pg if not math.isnan(float(card[p][a]))]
    mine = float(card[LM][a])
    contrib[a] = {'lamelo': round(mine, 1), 'pgMean': round(float(np.mean(vals)), 1), 'per36': round((mine - float(np.mean(vals))) / 10 * v10[a]['per36'], 3)}
rk = lambda key: 1 + sum(float(card[p][key]) > float(card[LM][key]) for p in card)
live = {r['name']: r for r in rd(M / 'reports/ovr-inseason-2026-27/live/2026-11-21/ranking.csv')}['LaMelo Ball']
lam = {'card': {k: card[LM][k] for k in ['rank', 'ovr', 'ovr36', 'predictedPer36', 'pred0', 'defenseBonus', 'mixBonus', 'mpg']},
       'rank_predictedPer36': rk('predictedPer36'), 'rank_ovr36': rk('ovr36'), 'n_card': len(card),
       'pgN': len(pg), 'pgMedian': {k: round(float(np.median([float(card[p][k]) for p in pg])), 3) for k in ['ovr', 'predictedPer36', 'pred0', 'defenseBonus', 'mixBonus', 'mpg']},
       'contrib': contrib,
       'onoff': {s: {k: round(OO[s][LM][k], 1) for k in ['oo', 'se', 'p', 'on']} for s in SEASONS if LM in OO[s]},
       'X': {k: (round(v, 2) if isinstance(v, float) else v) for k, v in X.get(LM, {}).items()},
       'rapm': prior.get(LM), 'darko': darko.get(LM),
       'live': {k: live[k] for k in ['rank', 'ovr', 'pred0', 'defenseBonus', 'mixBonus', 'formBonus', 'MPGhat', 'ovrPer36', 'predictedPer36', 'formalOVR']}}

# ---------- 例子 ----------
def row(p):
    x = X[p]
    return {k: (round(x[k], 2) if isinstance(x.get(k), float) else x.get(k)) for k in
            ['name', 'pos', 'rank', 'ovr', 'oo4s', 'R_OO', 'rapm', 'R_RAPM', 'darko', 'y1', 'p27', 'y2', 'y2r', 'grp', 'team25', 'team27']}


top = sorted(pool, key=lambda p: -X[p]['R_OO'])[:20]
bot = sorted(pool, key=lambda p: X[p]['R_OO'])[:10]
res = {'meta': {'pool': len(pool), 'h1': len(h1), 'h3': len(h3), 'unmatchedCard': unmatched, 'tau2': round(tau2, 2), 'm': round(m, 2),
                'meanShrink': round(float(np.mean([X[p]['shrink'] for p in pool])), 3), 'lastGame2627': last_stint_game,
                'rapm27': {'lambda': info27['lambda']}},
       'H1': H1, 'spearman': SP, 'H2': H2, 'H3': H3, 'verdict': verdict, 'LaMelo': lam,
       'topR_OO': [row(p) for p in top], 'bottomR_OO': [row(p) for p in bot]}
json.dump(res, open(OUT / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
keys = ['name', 'pos', 'rank', 'ovr', 'ovr36', 'oo4', 'se4', 'oo4s', 'shrink', 'R_OO', 'rapm', 'R_RAPM', 'darko', 'R_DARKO', 'oo25', 'y1', 'p27', 'y2', 'y1r', 'y2r', 'grp', 'team25', 'team27']
with open(OUT / 'players.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['playerId'] + keys)
    for p in sorted(pool, key=lambda p: X[p]['rank']):
        w.writerow([p] + [(round(X[p][k], 3) if isinstance(X[p].get(k), float) else X[p].get(k, '')) for k in keys])
print(json.dumps({'meta': res['meta'], 'verdict': verdict}, ensure_ascii=False, indent=1))
