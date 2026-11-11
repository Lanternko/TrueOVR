"""E-253 評估（預註冊 e9ebda7）：T 殘差收縮混入本季實際表現。python -I -X utf8 eval.py → work/eval.json"""
import json, math, os, sys, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REP, 'E223-team-rating'))
from e223_lib import load_season
H, SIG = 2.5, 12.0
ARMS = {'T0': (None, None), 'K5': (5, None), 'K10': (10, None), 'K20': (20, None), 'K40': (40, None), 'K10c': (10, 15.0)}
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))


def blend(games, k, cap):
    """games: list of dict(date, home, away, mT, d)；按日期排序。回傳 (m, nh, na)。"""
    res = collections.defaultdict(list); m = np.zeros(len(games)); nh = np.zeros(len(games), int); na = np.zeros(len(games), int)
    order = sorted(range(len(games)), key=lambda i: games[i]['date'])
    by_date = collections.defaultdict(list)
    for i in order: by_date[games[i]['date']].append(i)
    for day in sorted(by_date):
        idx = by_date[day]
        for i in idx:
            g = games[i]; R = {}
            for t in (g['home'], g['away']):
                r = res[t]
                R[t] = 0.0 if k is None or not r else sum(r) / (len(r) + k)
            m[i] = g['mT'] + R[g['home']] - R[g['away']]; nh[i] = len(res[g['home']]); na[i] = len(res[g['away']])
        for i in idx:   # 同日比賽結束後才更新
            g = games[i]; rh = g['d'] - (g['mT'] + H)
            if cap is not None: rh = max(-cap, min(cap, rh))
            res[g['home']].append(rh); res[g['away']].append(-rh)
    return m, nh, na


def score(games, m):
    y = np.array([1.0 if g['d'] > 0 else 0.0 for g in games])
    p = np.clip(Phi((m + H) / SIG), 1e-6, 1 - 1e-6)
    return (p - y) ** 2, -(y * np.log(p) + (1 - y) * np.log(1 - p)), ((p > .5) == (y > .5)).astype(float), p


def run(games, seed=20261107, B=10000):
    n = len(games); rng = np.random.default_rng(seed); idx = rng.integers(0, n, (B, n))
    out = {'n': n, 'arms': {}, 'diff': {}}; br = {}; ll = {}; M = {}; NN = None
    for a, (k, cap) in ARMS.items():
        m, nh, na = blend(games, k, cap); b, l, acc, p = score(games, m); br[a], ll[a], M[a] = b, l, m; NN = np.minimum(nh, na)
        out['arms'][a] = dict(brier=float(b.mean()), logloss=float(l.mean()), acc=float(acc.mean()))
    for a in ARMS:
        if a == 'T0': continue
        d = br[a] - br['T0']; bm = d[idx].mean(1)
        seg = {}
        for lab, lo, hi in (('g1-10', 0, 10), ('g11-30', 10, 30), ('g31+', 30, 999)):
            s = (NN >= lo) & (NN < hi)
            seg[lab] = dict(n=int(s.sum()), dBrier=float(d[s].mean()) if s.any() else None)
        out['diff'][a] = dict(dBrier=float(d.mean()), ci90=[float(np.percentile(bm, 5)), float(np.percentile(bm, 95))],
                              ci98=[float(np.percentile(bm, 1)), float(np.percentile(bm, 99))], dLogloss=float((ll[a] - ll['T0']).mean()),
                              meanShift=float(np.abs(M[a] - M['T0']).mean()), seg=seg)
    return out, M


def wins_at20(games, M):
    """各隊打完第 20 場時：已得勝場＋剩餘場預測勝率總和，對實際全季勝場的 MAE。"""
    order = sorted(range(len(games)), key=lambda i: games[i]['date']); cnt = collections.Counter(); won = collections.Counter()
    cut = {}
    for i in order:
        g = games[i]
        for t in (g['home'], g['away']):
            if cnt[t] == 20 and t not in cut: cut[t] = g['date']
        for t, w in ((g['home'], g['d'] > 0), (g['away'], g['d'] < 0)):
            cnt[t] += 1; won[t] += w
    out = {}
    for a, m in M.items():
        p = Phi((m + H) / SIG); err = []
        for t in cut:
            proj = 0.0
            for i in range(len(games)):
                g = games[i]
                if t not in (g['home'], g['away']): continue
                ph = p[i] if g['home'] == t else 1 - p[i]
                if g['date'] < cut[t]: proj += float((g['d'] > 0) == (g['home'] == t))
                else: proj += ph
            err.append(abs(proj - won[t]))
        out[a] = float(np.mean(err))
    return out


def load_2526():
    P = json.load(open(os.path.join(REP, 'E228-transformer-team-rating', 'work', 'pred-T-2526.json')))
    S = load_season('2526'); G = S['games']
    assert P['home'] == [g['home'] for g in G] and P['away'] == [g['away'] for g in G]
    mT = np.array(P['margin_seed']).mean(0)
    return [dict(date=g['date'], home=g['home'], away=g['away'], mT=float(mT[i]), d=g['hs'] - g['as'], gid=g['id']) for i, g in enumerate(G)]


def load_2627():
    G = json.load(open(os.path.join(REP, 'E246-t-tracking-blend', 'work', 'games.json'))); T = json.load(open(os.path.join(REP, 'E246-t-tracking-blend', 'work', 't_T1.json')))
    return [dict(date=g['date'], home=g['home'], away=g['away'], mT=float(T[g['gid']]), d=g['pts_home'] - g['pts_away'], gid=g['gid']) for g in G]


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    g25 = load_2526(); o25, M25 = run(g25); o25['winsMAE_at20'] = wins_at20(g25, M25)
    passing = [a for a, v in o25['diff'].items() if v['ci98'][1] < 0]
    pick = min(passing, key=lambda a: o25['diff'][a]['dBrier']) if passing else None
    g26 = load_2627(); o26, M26 = run(g26)
    J = {'J1_pass': bool(pick), 'pick': pick, 'J2_pass': bool(pick and o26['diff'][pick]['dBrier'] <= 0)}
    # 現在名次（11-02 截止）：各隊殘差收縮量 R（採用臂；未選則 K10 只報）
    show = pick or 'K10'; k, cap = ARMS[show]; res = collections.defaultdict(list)
    for g in sorted(g26, key=lambda x: x['date']):
        rh = g['d'] - (g['mT'] + H)
        if cap is not None: rh = max(-cap, min(cap, rh))
        res[g['home']].append(rh); res[g['away']].append(-rh)
    R = {t: dict(n=len(r), meanResid=float(np.mean(r)), shrunk=float(sum(r) / (len(r) + k))) for t, r in res.items()}
    out = {'prereg': 'e9ebda7', '2025-26': o25, '2026-27': o26, 'judgment': J, 'resid_now': {'arm': show, 'teams': R}}
    json.dump(out, open(os.path.join(HERE, 'work', 'eval.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({'judgment': J, '2025-26': {a: v['brier'] for a, v in o25['arms'].items()}, 'diff25': {a: (round(v['dBrier'], 4), [round(x, 4) for x in v['ci98']]) for a, v in o25['diff'].items()},
                      'seg25': {a: v['seg'] for a, v in o25['diff'].items()}, 'winsMAE20': o25['winsMAE_at20'],
                      '2026-27': {a: (round(v['dBrier'], 4), [round(x, 4) for x in v['ci90']]) for a, v in o26['diff'].items()}}, indent=1, ensure_ascii=False))
