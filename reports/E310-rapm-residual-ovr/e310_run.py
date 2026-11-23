"""E-310：RAPM 殘差加權進 OVR（照 preregistration.md 跑；資料讀主 checkout 的 gitignored 檔）。

用法：python -I reports/E310-rapm-residual-ovr/e310_run.py [主 checkout 路徑]
輸出：同目錄 fits.json（RAPM 擬合快取）、results.json、players.csv
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
sys.path.insert(0, str(M / 'reports/card-0.2.10a+E188-ovr-top-scale'))
import rapm  # noqa: E402
from ovr_map import ovr_map  # noqa: E402

SD1 = 115.0
B = 2000
BLEND_PER36, BLEND_POSS = 0.75, 1000
WS = [round(0.1 * i, 1) for i in range(11)]
KS = [0, 3000, 10000, 30000]
DG = 0.668  # gRepl/wMin 對 pred 的斜率（預註冊換算）


def fold(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in n if c.isalnum())


def rd(path):
    return list(csv.DictReader(open(path, encoding='utf-8')))


def se_oo(p, q):
    return SD1 * math.sqrt(2 / p + 2 / q)


# ---------- 卡片與 playerId ----------
name2id = {}
for path in [M / 'reports/impact-rapm/onoff.csv', M / 'reports/impact-rapm/rapm-prior.csv',
             M / 'reports/ovr-inseason-2026-27/live/2026-11-21/ranking.csv', M / 'reports/card-0.2.15/gravity-attr.csv']:
    for r in rd(path):
        if r.get('playerId'):
            name2id.setdefault(fold(r['name']), int(float(r['playerId'])))
card = {}
for r in rd(M / 'reports/card-0.2.15/ranking.csv'):
    pid = name2id.get(fold(r['name']))
    assert pid is not None, r['name']
    card[pid] = {'name': r['name'], 'pos': r['pos'], 'MIN': float(r['MIN']), 'pred': float(r['predictedPer36']),
                 'ovr': float(r['ovr']), 'rank': int(r['rank']), 'gRepl': float(r['gRepl']), 'wMin': float(r['wMin']),
                 'help': float(r['help']), 'mpg': float(r['mpg'])}
CARD_SUM = json.loads((M / 'reports/card-0.2.15/summary.json').read_text(encoding='utf-8'))
AN = CARD_SUM['anchors']

# ---------- RAPM 擬合（快取） ----------
FITS = OUT / 'fits.json'
SPEC = {'r3': ['2022-23', '2023-24', '2024-25'], 'r4': ['2022-23', '2023-24', '2024-25', '2025-26'],
        'y26': ['2025-26'], 'y27': ['2026-27']}
obs27 = list(rapm.observations(['2026-27']))
last_game = max(o[1] for o in obs27)
fits = json.loads(FITS.read_text(encoding='utf-8')) if FITS.exists() else {}
if fits.get('_last27') != last_game:
    fits.pop('y27', None)
for key, seasons in SPEC.items():
    if key in fits:
        continue
    obs = obs27 if key == 'y27' else list(rapm.observations(seasons))
    players = sorted({p for o in obs for p in o[2] + o[3]})
    out, info = rapm.fit_rapm(obs, players)
    fits[key] = {'lambda': info['lambda'], 'players': {str(p): v for p, v in out.items()}}
    print(key, 'lambda', info['lambda'], len(players), flush=True)
fits['_last27'] = last_game
FITS.write_text(json.dumps(fits), encoding='utf-8')
F = {k: {int(p): v for p, v in fits[k]['players'].items()} for k in SPEC}


def attach_r(key):
    """r＝0.75×RAPM − 同位置平均（card MIN 加權、回合 ≥1000）；O、D、net 各算。"""
    fit = F[key]
    res = {}
    for side in ('net', 'O', 'D'):
        for pos in {c['pos'] for c in card.values()}:
            pool = [p for p, c in card.items() if c['pos'] == pos and p in fit and fit[p]['poss'] >= BLEND_POSS]
            mu = sum(card[p]['MIN'] * BLEND_PER36 * fit[p][side] for p in pool) / sum(card[p]['MIN'] for p in pool)
            for p in pool:
                res.setdefault(p, {'P': fit[p]['poss']})[side] = BLEND_PER36 * fit[p][side] - mu
    return res


R3, R4 = attach_r('r3'), attach_r('r4')


def wcorr(x, y, w):
    x, y, w = map(np.asarray, (x, y, w))
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return float(np.average((x - mx) * (y - my), weights=w) / math.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w)))


def spearman(a, b):
    return rapm.spearman(list(a), list(b))


def score(pids, R, w, k, arm='blend', ecoef=None):
    out = []
    for p in pids:
        base = card[p]['pred']
        if p not in R:
            out.append(base); continue
        s = R[p]['P'] / (R[p]['P'] + k) if k else 1.0
        if arm == 'blend':
            out.append(base + w * s * (R[p]['net'] - base))
        else:
            a, b = ecoef
            out.append(base + w * s * (R[p][arm] - (a + b * base)))
    return np.array(out)


def ols_coef(pids, R, side):
    x = np.array([card[p]['pred'] for p in pids if p in R]); y = np.array([R[p][side] for p in pids if p in R])
    return tuple(np.polyfit(x, y, 1)[::-1])


# ---------- 校準：2025-26 單季 RAPM ----------
cal = [p for p in card if p in R3 and R3[p]['P'] >= BLEND_POSS and p in F['y26'] and F['y26'][p]['poss'] >= 2000]
ycal = np.array([F['y26'][p]['net'] for p in cal]); wcal = np.array([F['y26'][p]['poss'] for p in cal])

# 2025-26 on/off（附表）
hist = defaultdict(list)
for r in rd(M / 'reports/impact-rapm/onoff.csv'):
    if r['onOffNet']:
        hist[r['season']].append((int(r['playerId']), int(r['teamId']), float(r['onPoss']) / 2, float(r['offPoss']) / 2, float(r['onOffNet'])))


def agg(rows):
    acc = defaultdict(list)
    for pid, team, p, q, oo in rows:
        if p > 0 and q > 0:
            acc[pid].append((team, p, q, oo))
    out = {}
    for pid, L in acc.items():
        P = sum(x[1] for x in L)
        out[pid] = {'p': P, 'q': sum(x[2] for x in L), 'oo': sum(x[1] * x[3] for x in L) / P, 'team': max(L, key=lambda x: x[1])[0]}
    return out


OO26 = agg(hist['2025-26'])


def grid(pids, R, y, wt, arm='blend', ecoef=None):
    g = {}
    for w in WS:
        for k in KS:
            g[(w, k)] = wcorr(score(pids, R, w, k, arm, ecoef), y, wt)
    best = max(sorted(g), key=lambda t: (round(g[t], 12), -t[0], -t[1]))
    return g, best


calib = {}
gmain, best = grid(cal, R3, ycal, wcal)
calib['blend'] = {'best': best, 'rho_best': gmain[best], 'rho_base': gmain[(0.0, 0)], 'grid': {f'{w}|{k}': v for (w, k), v in gmain.items()}}
oo_cal = [p for p in cal if p in OO26]
g_oo, best_oo = grid(oo_cal, R3, np.array([OO26[p]['oo'] for p in oo_cal]), np.array([OO26[p]['p'] for p in oo_cal]))
calib['blend_onoff_report'] = {'best': best_oo, 'rho_best': g_oo[best_oo], 'rho_base': g_oo[(0.0, 0)], 'rho_at_main_best': g_oo[best]}
for side in ('O', 'D', 'net'):
    ec = ols_coef(cal, R3, side)
    g, b = grid(cal, R3, ycal, wcal, side, ec)
    calib[f'linear_{side}'] = {'best': b, 'rho_best': g[b], 'rho_base': g[(0.0, 0)]}
print('calibration', json.dumps({k: (v['best'], round(v['rho_best'], 4), round(v['rho_base'], 4)) for k, v in calib.items()}), flush=True)
W, K = calib['blend']['best']

# ---------- 樣本外：2026-27 ----------
y1rows = [(r['playerId'], r['teamId'], r['onPoss'] / 2, r['offPoss'] / 2, r['onOffNet']) for r in rapm.onoff(obs27) if 'onOffNet' in r]
Y1 = agg(y1rows)
# E-308 H1：2025-26 在場每邊 ≥1000；2026-27 在場每邊 ≥300、不在場每邊 ≥100
h1 = [p for p in card if p in OO26 and OO26[p]['p'] >= 1000 and p in Y1
      and Y1[p]['p'] >= 300 and Y1[p]['q'] >= 100 and p in F['y27']]
team27 = np.array([Y1[p]['team'] for p in h1])
movers = np.array([OO26[p]['team'] != Y1[p]['team'] for p in h1])
wv = np.array([Y1[p]['p'] for p in h1])
YV = {'y2': np.array([F['y27'][p]['net'] for p in h1]), 'y1': np.array([Y1[p]['oo'] for p in h1])}


def delta_boot(s_new, s_old, y, wt, seed=310, mask=None):
    idx_all = np.arange(len(h1)) if mask is None else np.where(mask)[0]
    pt = wcorr(s_new[idx_all], y[idx_all], wt[idx_all]) - wcorr(s_old[idx_all], y[idx_all], wt[idx_all])
    rng = np.random.default_rng(seed)
    teams = sorted(set(team27[idx_all]))
    by = {t: idx_all[team27[idx_all] == t] for t in teams}
    ds = []
    for _ in range(B):
        ii = np.concatenate([by[t] for t in rng.choice(teams, len(teams))])
        ds.append(wcorr(s_new[ii], y[ii], wt[ii]) - wcorr(s_old[ii], y[ii], wt[ii]))
    return {'delta': pt, 'ci90': [float(np.percentile(ds, 5)), float(np.percentile(ds, 95))],
            'rho_old': wcorr(s_old[idx_all], y[idx_all], wt[idx_all]), 'rho_new': wcorr(s_new[idx_all], y[idx_all], wt[idx_all])}


base_v = score(h1, R4, 0, 0)
VAL = {}
arms = {'main': score(h1, R4, W, K), 'fixed_w0.5_k10000': score(h1, R4, 0.5, 10000)}
for side in ('O', 'D', 'net'):
    b = tuple(calib[f'linear_{side}']['best'])
    arms[f'linear_{side}'] = score(h1, R4, b[0], b[1], side, ols_coef(h1, R4, side))
for name, s in arms.items():
    VAL[name] = {}
    for yk, y in YV.items():
        VAL[name][yk] = delta_boot(s, base_v, y, wv)
        VAL[name][yk]['spearman_old'] = spearman(base_v, y); VAL[name][yk]['spearman_new'] = spearman(s, y)
    VAL[name]['y2_movers'] = delta_boot(s, base_v, YV['y2'], wv, mask=movers)
    VAL[name]['y2_stayers'] = delta_boot(s, base_v, YV['y2'], wv, mask=~movers)
print('validation', json.dumps({n: {k: (round(v['delta'], 4), [round(c, 4) for c in v['ci90']]) for k, v in d.items()} for n, d in VAL.items()}), flush=True)

# ---------- OVR' 與人類直覺 ----------
allp = list(card)
s_all = score(allp, R4, W, K)
for i, p in enumerate(allp):
    c = card[p]
    dpred = s_all[i] - c['pred']
    dg = DG * dpred * c['wMin']
    c['dpred'] = float(dpred)
    c['ovr_new'] = round(c['ovr'] + float(ovr_map(c['gRepl'] + dg, AN) - ovr_map(c['gRepl'], AN)), 1)
order_old = sorted(allp, key=lambda p: card[p]['rank'])
order_new = sorted(allp, key=lambda p: (-card[p]['ovr_new'], card[p]['rank']))
for i, p in enumerate(order_new, 1):
    card[p]['rank_new'] = i

epm = {int(r['playerId']): float(r['net']) for r in rd(M / 'data/external-impact/epm_self/epm_2025-26.csv') if r['net']}
k2 = {fold(r['name']): float(r['2K27']) for r in rd(M / 'data/external-impact/2k/2k-merged-e142.csv') if r.get('2K27')}
G = {}
for lab, src, keyf in [('EPM', epm, lambda p: p), ('2K27', k2, lambda p: fold(card[p]['name']))]:
    ps = [p for p in allp if card[p]['MIN'] >= 500 and keyf(p) in src]
    v = [src[keyf(p)] for p in ps]
    G[lab] = {'n': len(ps), 'old': spearman([card[p]['ovr'] for p in ps], v), 'new': spearman([card[p]['ovr_new'] for p in ps], v)}
    G[lab]['pass'] = G[lab]['new'] >= G[lab]['old'] - 0.02
kd, fv = name2id[fold('Kevin Durant')], name2id[fold('Fred VanVleet')]
if fv in card:
    G['Durant>VanVleet'] = {'Durant': card[kd]['ovr_new'], 'VanVleet': card[fv]['ovr_new'], 'pass': card[kd]['ovr_new'] > card[fv]['ovr_new']}
else:  # 執行註記：VanVleet 2025-26 整季缺陣、不在 card 0.2.15，G-b 不適用（不算不過）
    G['Durant>VanVleet'] = {'Durant': card[kd]['ovr_new'], 'VanVleet': None, 'pass': True, 'note': 'VanVleet 不在 card 0.2.15，不適用'}
helps = sorted(card[p]['help'] for p in allp if card[p]['MIN'] >= 500)
h75 = helps[int(round(0.75 * (len(helps) - 1)))]
rim = lambda p: card[p]['pos'] in ('C', 'PF') and card[p]['help'] >= h75
G['rimTop30'] = {'old': sum(rim(p) for p in order_old[:30]), 'new': sum(rim(p) for p in order_new[:30]), 'help75': h75}
G['rimTop30']['pass'] = G['rimTop30']['new'] >= G['rimTop30']['old'] - 1

# ---------- 判定 ----------
v2, v1, mv = VAL['main']['y2'], VAL['main']['y1'], VAL['main']['y2_movers']
guards = all(G[k]['pass'] for k in ('EPM', '2K27', 'Durant>VanVleet', 'rimTop30'))
if W == 0 or v2['delta'] <= 0 or not guards:
    verdict = '不採用'
elif v2['ci90'][0] > 0 and v1['delta'] >= 0:
    verdict = '建議採用' + ('（換隊 Δρ<0，降一級）' if mv['delta'] < 0 else '')
else:
    verdict = '方向對、量不出'

pick = lambda p: {'name': card[p]['name'], 'pos': card[p]['pos'], 'ovr': card[p]['ovr'], 'rank': card[p]['rank'],
                  'ovr_new': card[p]['ovr_new'], 'rank_new': card[p]['rank_new'], 'dpred': round(card[p]['dpred'], 3),
                  'r4': round(R4[p]['net'], 3) if p in R4 else None, 'pred': card[p]['pred']}
mv_sorted = sorted([p for p in allp if card[p]['MIN'] >= 500], key=lambda p: card[p]['ovr_new'] - card[p]['ovr'])
res = {'last27': last_game, 'lambdas': {k: fits[k]['lambda'] for k in SPEC}, 'nCal': len(cal), 'nVal': len(h1), 'nMovers': int(movers.sum()),
       'calibration': {k: {**v, 'best': list(v['best'])} for k, v in calib.items()}, 'W': W, 'K': K, 'validation': VAL, 'guards': G, 'verdict': verdict,
       'top10_old': [pick(p) for p in order_old[:10]], 'top10_new': [pick(p) for p in order_new[:10]],
       'risers': [pick(p) for p in mv_sorted[::-1][:10]], 'fallers': [pick(p) for p in mv_sorted[:10]],
       'maxAbsDOVR': max(abs(card[p]['ovr_new'] - card[p]['ovr']) for p in allp),
       'focus': {n: pick(name2id[fold(n)]) for n in ['LaMelo Ball', 'Kentavious Caldwell-Pope', 'Jaylen Brown', 'Kevin Durant',
                                                     'Nikola Jokić', 'Victor Wembanyama', 'Rudy Gobert', 'Shai Gilgeous-Alexander', 'Jalen Williams'] if name2id.get(fold(n)) in card}}
(OUT / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
with open(OUT / 'players.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['playerId', 'name', 'pos', 'MIN', 'ovr', 'rank', 'ovr_new', 'rank_new', 'pred', 'dpred', 'r4', 'P4'])
    for p in order_new:
        c = card[p]
        w.writerow([p, c['name'], c['pos'], c['MIN'], c['ovr'], c['rank'], c['ovr_new'], c['rank_new'], c['pred'], round(c['dpred'], 4),
                    round(R4[p]['net'], 4) if p in R4 else '', round(R4[p]['P']) if p in R4 else ''])
print('W,K', W, K, 'verdict', verdict)
print(json.dumps(G, ensure_ascii=False))
