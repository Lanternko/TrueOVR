"""E-254 評估（預註冊 eb6025e）：球隊出手結構能不能補 T＋K10 殘差。python -I -X utf8 eval.py → work/eval.json"""
import collections, gzip, json, math, os, sys, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REP = os.path.dirname(HERE); ROOT = os.path.dirname(REP)
sys.path.insert(0, os.path.join(REP, 'E253-actual-results-blend')); sys.path.insert(0, os.path.join(REP, 'E223-team-rating'))
import eval as E253
from e223_lib import load_season
H, SIG, K, KS = 2.5, 12.0, 10, 5
FEAT = ['f3', 'fmid', 'fft']
ARMS = {'S3': ['o_f3'], 'SMID': ['o_fmid'], 'SALL': ['o_f3', 'o_fmid', 'o_fft'], 'SALLD': ['o_f3', 'o_fmid', 'o_fft', 'd_f3', 'd_fmid', 'd_fft']}
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))


def profiles(games, box):
    """box[gid][tid] = dict(fga, fg3a, mid, fta)（自己出手）。回傳 X[i] = {o_f3…, d_f3…}（主減客，收縮置中，只用比賽日 < 該場）。"""
    acc = collections.defaultdict(lambda: {'o': collections.Counter(), 'd': collections.Counter(), 'n': 0})
    lg = collections.Counter()
    X = [None] * len(games); byd = collections.defaultdict(list)
    for i, g in enumerate(games): byd[g['date']].append(i)
    for day in sorted(byd):
        for i in byd[day]:
            g = games[i]; v = {}
            for side in ('o', 'd'):
                for f in FEAT:
                    x = {}
                    for t in (g['home'], g['away']):
                        a = acc[t]; c = a[side]
                        if a['n'] == 0 or lg['fga'] == 0: x[t] = 0.0; continue
                        num = {'f3': 'fg3a', 'fmid': 'mid', 'fft': 'fta'}[f]
                        x[t] = a['n'] / (a['n'] + KS) * (c[num] / c['fga'] - lg[num] / lg['fga'])
                    v[f'{side}_{f}'] = x[g['home']] - x[g['away']]
            X[i] = v
        for i in byd[day]:
            g = games[i]; b = box.get(g['gid'])
            if b is None: continue
            for t, o in ((g['home'], g['away']), (g['away'], g['home'])):
                acc[t]['o'].update(b[t]); acc[t]['d'].update(b[o]); acc[t]['n'] += 1
                lg.update(b[t])
    return X


def brier(games, m):
    y = np.array([1.0 if g['d'] > 0 else 0.0 for g in games]); p = np.clip(Phi((m + H) / SIG), 1e-6, 1 - 1e-6)
    return (p - y) ** 2


def fit(games, mb, X, cols, idx):
    A = np.array([[X[i][c] for c in cols] for i in idx]); r = np.array([games[i]['d'] - (mb[i] + H) for i in idx])
    beta, *_ = np.linalg.lstsq(A, r, rcond=None)
    res = r - A @ beta; s2 = res @ res / (len(r) - len(cols)); se = np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ A)))
    return beta, se


def apply(mb, X, cols, beta):
    return mb + np.array([[x[c] for c in cols] for x in X]) @ beta


def boot(d, B=10000, seed=20261107):
    rng = np.random.default_rng(seed); bm = d[rng.integers(0, len(d), (B, len(d)))].mean(1)
    return bm


def load_2526():
    G = E253.load_2526(); S = load_season('2526'); box = {}
    for g in S['games']:
        f = os.path.join(ROOT, 'data/season-source/dnp-2025-26-raw', f"boxscore_{g['id']}.json.gz")
        bx = json.loads(gzip.open(f, 'rt', encoding='utf-8').read())['game']; b = {}
        for s in ('homeTeam', 'awayTeam'):
            st = bx[s]['statistics']
            b[str(bx[s]['teamId'])] = dict(fga=st['fieldGoalsAttempted'], fg3a=st['threePointersAttempted'], fta=st['freeThrowsAttempted'],
                                         mid=st['twoPointersAttempted'] - st['pointsInThePaintAttempted'])
        box[g['id']] = b
    return G, box


def load_2627():
    G = E253.load_2627()
    d = json.load(open(os.path.join(ROOT, 'data/season-source-2026-27/team-games.json'), encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d; R = [dict(zip(t['headers'], r)) for r in t['rowSet']]
    box = collections.defaultdict(dict)
    for r in R:
        box[r['GAME_ID']][str(r['TEAM_ID'])] = dict(fga=r['FGA'], fg3a=r['FG3A'], fta=r['FTA'], mid=0)
    # 中距離：leaguedashteamshotlocations 季累積（DateTo＝前一天）→ 逐日差分攤回當天每場（同日一隊只打一場）
    loc = {}
    for f in sorted(os.listdir(os.path.join(HERE, 'data/loc'))):
        rs = json.load(open(os.path.join(HERE, 'data/loc', f)))
        loc[f[:10]] = {str(r[0]): (r[9], sum(r[k] for k in (3, 6, 9, 12, 15, 18, 21))) for r in rs['rowSet']}
    gdate = {g['gid']: g['date'] for g in G}
    for gid, tm in box.items():
        d0 = gdate.get(gid)
        if d0 is None: continue
        if d0 not in loc: continue
        prev = (dt.date.fromisoformat(d0) - dt.timedelta(1)).isoformat()
        for tid, v in tm.items():
            if d0 in loc and tid in loc[d0]:
                v['mid'] = loc[d0][tid][0] - loc.get(prev, {}).get(tid, (0, 0))[0]      # loc[d] 含 ≤ d 的比賽；同日一隊只打一場
    return G, dict(box)


def run_season(G, box, train_idx, test_idx, betas=None):
    for g in G: g.setdefault('gid', g.get('gid'))
    mb, _, _ = E253.blend(G, K, None)
    X = profiles(G, box)
    out = {'n_train': len(train_idx), 'n_test': len(test_idx), 'arms': {}}
    b0 = brier(G, mb)
    out['B0_brier_test'] = float(b0[test_idx].mean())
    fitted = {}
    for a, cols in ARMS.items():
        if betas is None:
            beta, se = fit(G, mb, X, cols, train_idx); fitted[a] = (beta, se)
        else:
            beta, se = betas[a]
        m = apply(mb, X, cols, beta); d = (brier(G, m) - b0)[test_idx]; bm = boot(d)
        out['arms'][a] = dict(beta=dict(zip(cols, map(float, beta))), se=dict(zip(cols, map(float, se))), dBrier=float(d.mean()),
                              ci975=[float(np.percentile(bm, 1.25)), float(np.percentile(bm, 98.75))],
                              ci90=[float(np.percentile(bm, 5)), float(np.percentile(bm, 95))], meanShift=float(np.abs(m - mb)[test_idx].mean()))
    return out, fitted, X, mb


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    G25, box25 = load_2526()
    for g in G25: g['gid'] = g['gid']
    tr = [i for i, g in enumerate(G25) if g['date'] < '2026-01-01']; te = [i for i, g in enumerate(G25) if g['date'] >= '2026-01-01']
    o25, fit25, X25, mb25 = run_season(G25, box25, np.array(tr), np.array(te))
    passing = [a for a, v in o25['arms'].items() if v['ci975'][1] < 0]
    pick = min(passing, key=lambda a: o25['arms'][a]['dBrier']) if passing else None
    # J2：β 用 2025-26 整季重擬
    allidx = np.arange(len(G25)); full = {a: fit(G25, mb25, X25, c, allidx) for a, c in ARMS.items()}
    G26, box26 = load_2627()
    o26, _, X26, mb26 = run_season(G26, box26, np.arange(0), np.arange(len(G26)), betas=full)
    J = {'J1_pass': bool(pick), 'pick': pick, 'J2_pass': bool(pick and o26['arms'][pick]['dBrier'] <= 0)}
    # 季層級（只報）：2024-25 各隊出手結構 vs 2025-26 整季平均殘差（實際 − T）
    S24 = load_season('2425'); tot = collections.defaultdict(collections.Counter)
    for g in S24['games']:
        bx = json.loads(gzip.open(os.path.join(ROOT, 'data/season-source/dnp-2024-25-raw', f"boxscore_{g['id']}.json.gz"), 'rt', encoding='utf-8').read())['game']
        for s in ('homeTeam', 'awayTeam'):
            st = bx[s]['statistics']
            tot[str(bx[s]['teamId'])].update(dict(fga=st['fieldGoalsAttempted'], fg3a=st['threePointersAttempted'], fta=st['freeThrowsAttempted'],
                                                  mid=st['twoPointersAttempted'] - st['pointsInThePaintAttempted']))
    res = collections.defaultdict(list)
    for g in G25:
        r = g['d'] - (g['mT'] + H); res[g['home']].append(r); res[g['away']].append(-r)
    tids = sorted(res); rr = np.array([np.mean(res[t]) for t in tids]); season = {}
    for f, num in (('f3', 'fg3a'), ('fmid', 'mid'), ('fft', 'fta')):
        x = np.array([tot[t][num] / tot[t]['fga'] for t in tids]); season[f] = float(np.corrcoef(x, rr)[0, 1])
    # 2026-27 現在（11-02 前資料）各隊調整量：用整季 β、最後狀態特徵（只報）
    now = {}
    if True:
        a = pick or 'SALL'; cols = ARMS[a]; beta = full[a][0]
        acc = collections.defaultdict(collections.Counter); n = collections.Counter(); lg = collections.Counter()
        for g in G26:
            b = box26.get(g['gid'])
            if not b: continue
            for t, o in ((g['home'], g['away']), (g['away'], g['home'])):
                acc[('o', t)].update(b[t]); acc[('d', t)].update(b[o]); n[t] += 1
                lg.update(b[t])
        for t in n:
            v = {}
            for side in ('o', 'd'):
                for f, num in (('f3', 'fg3a'), ('fmid', 'mid'), ('fft', 'fta')):
                    c = acc[(side, t)]; v[f'{side}_{f}'] = n[t] / (n[t] + KS) * (c[num] / c['fga'] - lg[num] / lg['fga'])
            now[t] = dict(arm=a, adj=float(sum(v[c] * b for c, b in zip(cols, beta))), raw={k: round(x, 4) for k, x in v.items()})
    out = {'prereg': 'eb6025e', '2025-26': o25, '2026-27': o26, 'judgment': J, 'beta_full': {a: dict(zip(ARMS[a], map(float, b))) for a, (b, s) in full.items()},
           'se_full': {a: dict(zip(ARMS[a], map(float, s))) for a, (b, s) in full.items()}, 'season_corr_2425_profile_vs_2526_resid': season, 'now_2627': now}
    json.dump(out, open(os.path.join(HERE, 'work', 'eval.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({'J': J, 'B0_test': o25['B0_brier_test'],
                      '25': {a: (round(v['dBrier'], 4), [round(x, 4) for x in v['ci975']]) for a, v in o25['arms'].items()},
                      '26': {a: (round(v['dBrier'], 4), [round(x, 4) for x in v['ci90']]) for a, v in o26['arms'].items()},
                      'beta_full': {a: {k: round(x, 1) for k, x in b.items()} for a, b in out['beta_full'].items()},
                      'se_full': {a: {k: round(x, 1) for k, x in b.items()} for a, b in out['se_full'].items()},
                      'season': {k: round(v, 3) for k, v in season.items()}}, indent=1, ensure_ascii=False))
