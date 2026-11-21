"""E-084 稽核：獨立重算（不 import e084.py／e075.py／e081.py／evaluate_e064.py 的任何函式）。
依預註冊與 e075 的方法文字重寫：分類、特徵、母群、WLS、半季評估、卡片組裝、E-081 式評估、bootstrap。
用法（repo 根目錄）：python -I reports/card-0.2.3+E084-current-target/audit/recompute.py
輸出只寫本目錄：recompute.json、ranking_pooled.csv、ranking_season.csv。
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
R = lambda p: ROOT / p


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rcsv(p, enc='utf-8-sig'):
    with open(p, encoding=enc) as f:
        return list(csv.DictReader(f))


def jl(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ---------------------------------------------------------------- 常數（預註冊 §2「其他全部不動」＝E-075 寫死值）
THR_POSS, MIN_GP = 2500, 5
POOL_MIN = 500
AGE_Y, AGE_V, D_THR = 23, 31, 0.35
INJ = ('INJURY', 'ILLNESS', 'CONCUSSION', 'RECONDITIONING', 'PERSONAL', 'SUSPENSION', 'NOT_WITH_TEAM', 'TRADE')
COACH = ('DNP_COACH', 'INACTIVE_COACH', 'INACTIVE_GLEAGUE_ON_ASSIGNMENT', 'INACTIVE_GLEAGUE_TWOWAY')
CN = ['b0', 'b1_p', 'b2_L', 'b3_a', 'b4_y', 'b5_v', 'b6_yL', 'b7_vL', 'b8_ydL']
FROZEN = ['reports/ovr-calibrated-2025-26/ranking.csv', 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv',
          'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv', 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv',
          'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv']
V58 = 'reports/ovr-v58-holdout-2025-26'
P1 = 'reports/card-0.2.2/cards/P1'
GROUPS = [('<=23', 0, 23), ('24-27', 24, 27), ('28-30', 28, 30), ('>=31', 31, 999)]

# ---------------------------------------------------------------- 讀資料
pg = jl(R('data/season-source/player-games.json'))['data']['resultSets'][0]
H = {k: i for i, k in enumerate(pg['headers'])}
halfMIN = {'A': defaultdict(float), 'B': defaultdict(float)}
teamMIN = {s: defaultdict(lambda: defaultdict(float)) for s in ('A', 'B', 'full')}
for r in pg['rowSet']:
    m = r[H['MIN']]
    if not m:
        continue
    h = 'B' if int(r[H['GAME_ID']]) % 2 else 'A'
    halfMIN[h][r[H['PLAYER_ID']]] += m
    teamMIN[h][r[H['PLAYER_ID']]][r[H['TEAM_ID']]] += m
    teamMIN['full'][r[H['PLAYER_ID']]][r[H['TEAM_ID']]] += m
tg = jl(R('data/season-source/team-games.json'))['data']['resultSets'][0]
H = {k: i for i, k in enumerate(tg['headers'])}
sched_raw, W, G = defaultdict(list), defaultdict(int), defaultdict(int)
for r in tg['rowSet']:
    t = r[H['TEAM_ID']]
    sched_raw[t].append((r[H['GAME_DATE']], int(r[H['GAME_ID']])))
    G[t] += 1
    W[t] += r[H['WL']] == 'W'
pos_in_sched = {t: {g: i for i, (_, g) in enumerate(sorted(v))} for t, v in sched_raw.items()}
nsched = {t: len(v) for t, v in sched_raw.items()}
winrate = {t: W[t] / G[t] for t in G}
bio = jl(R('data/benchmark-source/bio.json'))['data']['resultSets'][0]
H = {k: i for i, k in enumerate(bio['headers'])}
AGE = {r[H['PLAYER_ID']]: r[H['AGE']] for r in bio['rowSet'] if r[H['AGE']] is not None}
dnp = jl(R('data/season-source/dnp-2025-26.json'))


def predmap(p):
    return {int(r['playerId']): {'name': r['name'], 'MIN': float(r['MIN']), 'pred': float(r['pred']),
                                 'mpg': float(r['mpg']) if r['mpg'] != '' else None} for r in rcsv(R(p))}


prim = predmap(f'{P1}/primary/pred.csv')
fitp = {h: predmap(f'{P1}/fit{h}/pred.csv') for h in 'AB'}
fsum = {h: jl(R(f'{P1}/fit{h}/pergame-summary.json')) for h in 'AB'}
mpgh = {h: {int(r['playerId']): (int(r['gp']), float(r['mpg'])) for r in rcsv(R(f'reports/card-0.1.2+E064-pergame/mpg-{h}.csv'))} for h in 'AB'}
rapm = {h: {r['name']: r for r in rcsv(R(f'{V58}/rapm-{h}.csv')) if r['name']} for h in 'AB'}
rapm1 = {h: {int(r['playerId']): {'net': float(r['net']), 'poss': float(r['poss'])} for r in rcsv(R(f'reports/card-0.2.3+E081-age-residual/rapm1-{h}.csv'), 'utf-8')} for h in 'AB'}
n2p = {v['name']: q for q, v in prim.items()}
assert len(n2p) == len(prim)

# ---------------------------------------------------------------- 分類（E-073 §2）
def classify():
    rows = []
    for gid, g in dnp['games'].items():
        for pid, tid, st, rs, mn, old in g['players']:
            if mn > 0:
                c = 'P'
            elif 'REST' in rs:
                c = 'R'
            elif any(k in rs for k in INJ):
                c = 'U'
            elif rs in COACH:
                c = 'C'
            elif rs == '' and st == 'ACTIVE':
                c = 'C'
            else:
                c = 'U'
            rows.append([pid, tid, int(gid), c, mn])
    grp = defaultdict(list)
    for k, r in enumerate(rows):
        grp[(r[0], r[1])].append(k)
    for (pid, tid), ks in grp.items():
        mins = [rows[k][4] for k in ks if rows[k][3] == 'P']
        if len(mins) < 10 or np.mean(mins) < 24.0:
            continue
        at = {pos_in_sched[tid][rows[k][2]]: k for k in ks}
        seq = [rows[at[i]][3] if i in at else None for i in range(nsched[tid])]
        i = 0
        while i < len(seq):
            if seq[i] == 'C':
                j = i
                while j + 1 < len(seq) and seq[j + 1] == 'C':
                    j += 1
                if j - i + 1 < 3:
                    for q in range(i, j + 1):
                        rows[at[q]][3] = 'S'
                i = j + 1
            else:
                i += 1
    ap = {'A': defaultdict(int), 'B': defaultdict(int)}
    pl = {'A': defaultdict(int), 'B': defaultdict(int)}
    for pid, tid, gi, c, mn in rows:
        h = 'B' if gi % 2 else 'A'
        if c in 'PC':
            ap[h][pid] += 1
        if c == 'P':
            pl[h][pid] += 1
    return ap, pl


AP, PL = classify()


def feats(scope, pm):
    pids = sorted(pm)
    p = np.array([pm[q]['pred'] for q in pids])
    mpg0 = np.array([pm[q]['mpg'] or 0.0 for q in pids])
    if scope == 'full':
        MIN = np.array([pm[q]['MIN'] for q in pids])
        ap = np.array([AP['A'][q] + AP['B'][q] for q in pids], float)
        pl = np.array([PL['A'][q] + PL['B'][q] for q in pids], float)
    else:
        MIN = np.array([halfMIN[scope].get(q, 0.0) for q in pids])
        ap = np.array([AP[scope][q] for q in pids], float)
        pl = np.array([PL[scope][q] for q in pids], float)
    has = ap > 0
    mp = np.where(has, MIN / np.maximum(ap, 1), mpg0)
    a = np.where(has, pl / np.maximum(ap, 1), 0.0)
    age = [AGE.get(q) for q in pids]
    y = np.array([float(x is not None and x <= AGE_Y) for x in age])
    v = np.array([float(x is not None and x >= AGE_V) for x in age])
    d = []
    for q in pids:
        tm = teamMIN[scope].get(q)
        if not tm:
            d.append(0.0)
            continue
        best = max(tm.values())
        t = min(t for t, m in tm.items() if m == best)
        d.append(float(winrate[t] < D_THR))
    L = np.log1p(mp)
    d = np.array(d)
    X = np.column_stack([np.ones_like(p), p, L, a, y, v, y * L, v * L, y * d * L])
    return {'pids': pids, 'ix': {q: i for i, q in enumerate(pids)}, 'p': p, 'mp': mp, 'mpg0': mpg0, 'has': has, 'X': X, 'MIN': MIN, 'age': age}


def wls(X, y, w):
    s = np.sqrt(w)
    return np.linalg.lstsq(X * s[:, None], y * s, rcond=None)[0]


def prc(vals, mask, q):
    s = np.sort(np.asarray(vals)[mask])
    return float(s[int(round(q / 100 * (len(s) - 1)))])


def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


# ---------------------------------------------------------------- 母群
k2 = {r['name'] for r in rcsv(R('reports/ovr-v55-2k27-compare/merged.csv')) if r['rank2k']}
S = [set(r['name'] for r in rcsv(R(p))) for p in FROZEN]
for sc in ('0.5', '1.0'):
    for f in 'AB':
        for k in ('E2', 'F2', 'G3', 'H1-m0'):
            S.append(set(r['name'] for r in rcsv(R(f'{V58}/fit{f}-scale{sc}/{k}/ranking.csv'))))
common = set.intersection(*S) & k2 & set(n2p) & {v['name'] for v in fitp['A'].values()} & {v['name'] for v in fitp['B'].values()}
pools = {}
for f, e in (('A', 'B'), ('B', 'A')):
    pools[f + e] = sorted(n for n in common if n in rapm[e] and float(rapm[e][n]['pooledPoss']) >= THR_POSS
                          and all(n2p[n] in mpgh[h] and mpgh[h][n2p[n]][0] >= MIN_GP for h in 'AB'))

SF = {h: feats(h, fitp[h]) for h in 'AB'}
SFF = feats('full', prim)


def run(target):
    coef, T = {}, {}
    for f, e in (('A', 'B'), ('B', 'A')):
        nm = pools[e + f]                     # 方向 f→e 的訓練列：e 半季特徵 → f 半季 RAPM
        if target == 'season':
            nm = [n for n in nm if n2p[n] in rapm1[f]]
            yv = np.array([rapm1[f][n2p[n]]['net'] for n in nm])
            w = np.array([rapm1[f][n2p[n]]['poss'] for n in nm])
        else:
            yv = np.array([float(rapm[f][n]['pooledNet']) for n in nm])
            w = np.array([float(rapm[f][n]['pooledPoss']) for n in nm])
        X = SF[e]['X'][[SF[e]['ix'][n2p[n]] for n in nm]]
        T[f + e] = (X, yv, w, nm)
        coef[f + e] = wls(X, yv, w)
    coef['card'] = wls(np.vstack([T[d][0] for d in ('AB', 'BA')]), np.concatenate([T[d][1] for d in ('AB', 'BA')]),
                       np.concatenate([T[d][2] for d in ('AB', 'BA')]))
    dirs = {}
    for f, e in (('A', 'B'), ('B', 'A')):
        sf = SF[f]
        pn = np.where(sf['has'], sf['X'] @ coef[f + e], sf['p'])
        pool = np.array([fitp[f][q]['MIN'] for q in sf['pids']]) >= POOL_MIN
        rb = prc(sf['p'], pool, 10)
        assert abs(rb - fsum[f]['rRepl_PR10_of_pred']) < 1e-12
        rr = prc(pn, pool, 10)
        nm = pools[f + e]
        sel = [sf['ix'][n2p[n]] for n in nm]
        q = [n2p[n] for n in nm]
        dirs[f + e] = {'names': nm, 'cand': ((pn - rr) * sf['mp'] / 36)[sel], 'base': ((sf['p'] - rb) * sf['mpg0'] / 36)[sel],
                       'p': sf['p'][sel], 'pn': pn[sel],
                       'ansQ': np.array([float(rapm[e][n]['pooledNet']) * mpgh[e][n2p[n]][1] for n in nm]),
                       'netQ': np.array([float(rapm[e][n]['pooledNet']) for n in nm]),
                       'netN': np.array([rapm1[e][x]['net'] if x in rapm1[e] else np.nan for x in q]),
                       'mpg_ev': np.array([mpgh[e][x][1] for x in q]),
                       'age': np.array([float(AGE[x]) if x in AGE else np.nan for x in q])}
    # 卡片
    sf = SFF
    pred = np.where(sf['has'], sf['X'] @ coef['card'], sf['p'])
    pool = sf['MIN'] >= POOL_MIN
    r = prc(pred, pool, 10)
    g = (pred - r) * sf['mp'] / 36
    a1, a50, a99 = prc(g, pool, 1), prc(g, pool, 50), prc(g, pool, 99)
    ovr = np.where(g <= a50, 40 + 30 * (g - a1) / (a50 - a1), 70 + 29 * (g - a50) / (a99 - a50))
    names = [prim[q]['name'] for q in sf['pids']]
    return {'coef': coef, 'dirs': dirs, 'pred': pred, 'g': g, 'ovr': ovr, 'names': names, 'r': r, 'anchors': (a1, a50, a99),
            'train_n': {d: len(T[d][1]) for d in T}}


def write_card(res, path):
    base = rcsv(R(f'{P1}/primary/ranking.csv'), 'utf-8')       # 同分時的順序 = 此檔列序（穩定排序）
    pub = {r['name']: r for r in rcsv(R('reports/card-0.2.2/ranking.csv'), 'utf-8')}
    cols = list(next(iter(pub.values())).keys())
    ix = {n: i for i, n in enumerate(res['names'])}
    order = sorted(range(len(base)), key=lambda k: -res['ovr'][ix[base[k]['name']]])
    rows = []
    for rk, k in enumerate(order, 1):
        n = base[k]['name']
        i = ix[n]
        o = dict(pub[n])
        o['rank'] = str(rk)
        o['ovr'] = f"{res['ovr'][i]:.1f}"
        o['mpg'] = f"{SFF['mp'][i]:.2f}"
        o['gRepl'] = f"{res['g'][i]:.4f}"
        rows.append(o)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    return rows


# ---------------------------------------------------------------- E-081 式評估
def pctr(x):
    return (rankdata(x) - 1.0) / (len(x) - 1.0)


def sp(a, b):
    ra, rb = rankdata(a), rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def build_eval(cd, bd):
    E = {}
    for dn in ('AB', 'BA'):
        c, b = cd[dn], bd[dn]
        assert c['names'] == b['names'] and np.array_equal(c['p'], b['p'])
        keep = ~np.isnan(c['age']) & ~np.isnan(c['netN'])
        hasN = ~np.isnan(c['netN'])
        ansN = c['netN'] * c['mpg_ev']
        e = {'keep': keep, 'hasN': hasN, 'ansN': ansN, 'ansQ': c['ansQ'], 'age': c['age'], 'netN': c['netN'], 'p': c['p'], 'pn': c['pn'],
             'g_c': c['cand'], 'g_b': b['cand'], 'names': c['names']}
        k = np.where(keep)[0]
        for t in 'cb':
            for A in 'NQ':
                u = np.full(len(keep), np.nan)
                u[k] = pctr(e['ans' + A][k]) - pctr(e['g_' + t][k])
                e[f'u{A}{t}'] = u
        e['gm'] = {g: np.array([(not np.isnan(x)) and lo <= x <= hi for x in c['age']]) for g, lo, hi in GROUPS}
        E[dn] = e
    return E


def stats(E, sel):
    out = defaultdict(list)
    for dn in ('AB', 'BA'):
        e, s = E[dn], sel[dn]
        sk, sn = s[e['keep'][s]], s[e['hasN'][s]]
        for t in 'cb':
            for A in 'NQ':
                u = e[f'u{A}{t}']
                out[f'S{A}_{t}'].append(sp(e['age'][sk], u[sk]))
                for g, _, _ in GROUPS:
                    m = e['gm'][g][sk]
                    out[f'g{A}_{t}_{g}'].append(float(u[sk][m].mean()) if m.any() else np.nan)
            out[f'rN_{t}'].append(rho(e['g_' + t][sn], e['ansN'][sn]))
            out[f'rQ_{t}'].append(rho(e['g_' + t][s], e['ansQ'][s]))
        out['c4_c'].append(rho(e['pn'][sn], e['netN'][sn]))
        out['c4_b'].append(rho(e['p'][sn], e['netN'][sn]))
    return {k: float(np.nanmean(v)) for k, v in out.items()}, out


def evaluate(E, seed, nboot=2000):
    full = {dn: np.arange(len(E[dn]['keep'])) for dn in E}
    pt, raw = stats(E, full)
    master = sorted(set(E['AB']['names']) | set(E['BA']['names']))
    mp_ = {dn: np.array([{n: i for i, n in enumerate(E[dn]['names'])}.get(n, -1) for n in master]) for dn in E}
    rng = np.random.default_rng(seed)
    B = defaultdict(list)
    for _ in range(nboot):
        ix = rng.integers(0, len(master), len(master))
        sel = {}
        for dn in E:
            s = mp_[dn][ix]
            sel[dn] = s[s >= 0]
        for k, v in stats(E, sel)[0].items():
            B[k].append(v)
    B = {k: np.array(v) for k, v in B.items()}

    def ci(x):
        return [float(np.nanpercentile(x, 5)), float(np.nanpercentile(x, 95))]
    res = {'n_master': len(master)}
    for nm, a, b in (('dS_N', 'SN_c', 'SN_b'), ('dS_Q', 'SQ_c', 'SQ_b'), ('c2N', 'rN_c', 'rN_b'), ('c2Q', 'rQ_c', 'rQ_b'), ('c4', 'c4_c', 'c4_b')):
        res[nm] = {'point': pt[a] - pt[b], 'ci90': ci(B[a] - B[b])}
    for k in ('SN_c', 'SN_b', 'SQ_c', 'SQ_b', 'rN_c', 'rN_b', 'rQ_c', 'rQ_b', 'c4_c', 'c4_b'):
        res[k] = {'point': pt[k], 'ci90': ci(B[k]), 'per_dir': dict(zip(('AB', 'BA'), raw[k]))}
    for A in 'NQ':
        for t in 'cb':
            res[f'groups_{A}_{t}'] = {g: pt[f'g{A}_{t}_{g}'] for g, _, _ in GROUPS}
    return res


if __name__ == '__main__':
    out = {'pools': {k: len(v) for k, v in pools.items()}, 'union': len(set(pools['AB']) | set(pools['BA']))}
    RP, RS = run('pooled'), run('season')
    out['train_n'] = {'pooled': RP['train_n'], 'season': RS['train_n']}
    out['coef'] = {t: {d: dict(zip(CN, map(float, R_['coef'][d]))) for d in ('AB', 'BA', 'card')} for t, R_ in (('pooled', RP), ('season', RS))}
    write_card(RP, OUT / 'ranking_pooled.csv')
    write_card(RS, OUT / 'ranking_season.csv')
    out['sha'] = {'ranking_pooled': sha(OUT / 'ranking_pooled.csv'), 'ranking_season': sha(OUT / 'ranking_season.csv'),
                  'card023': sha(R('reports/card-0.2.3/ranking.csv')), 'e084_ranking': sha(R('reports/card-0.2.3+E084-current-target/ranking.csv'))}
    big = SFF['MIN'] >= 1000
    out['pred_std_MIN1000'] = {'season': float(np.std(RS['pred'][big])), 'pooled': float(np.std(RP['pred'][big])), 'n': int(big.sum()),
                               'mean_season': float(np.mean(RS['pred'][big])), 'mean_pooled': float(np.mean(RP['pred'][big]))}
    E = build_eval(RS['dirs'], RP['dirs'])
    out['eval'] = {}
    for s in (1, 2, 3, 4, 5):
        out['eval'][f'seed{s}'] = evaluate(E, s)
        print('seed', s, {k: out['eval'][f'seed{s}'][k] for k in ('dS_N', 'c2N', 'c2Q', 'c4')}, flush=True)
    # 逐人資料（給退步項）
    out['card_season'] = {'r': RS['r'], 'anchors': RS['anchors']}
    out['card_pooled'] = {'r': RP['r'], 'anchors': RP['anchors']}
    per = {}
    for i, n in enumerate(RS['names']):
        per[n] = {'pid': SFF['pids'][i], 'MIN': float(SFF['MIN'][i]), 'mp': float(SFF['mp'][i]), 'p': float(SFF['p'][i]),
                  'X': [float(x) for x in SFF['X'][i]], 'has': bool(SFF['has'][i]),
                  'pred_season': float(RS['pred'][i]), 'pred_pooled': float(RP['pred'][i]),
                  'ovr_season': float(RS['ovr'][i]), 'ovr_pooled': float(RP['ovr'][i]), 'age': SFF['age'][i]}
    (OUT / 'recompute_players.json').write_text(json.dumps(per, ensure_ascii=False) + '\n', encoding='utf-8')
    (OUT / 'recompute.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('pools', 'union', 'train_n', 'sha', 'pred_std_MIN1000')}, ensure_ascii=False, indent=1))
