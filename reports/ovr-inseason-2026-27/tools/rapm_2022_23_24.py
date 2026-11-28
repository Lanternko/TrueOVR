"""Real player impact from play-by-play stints: on/off ratings and RAPM (local data required).

  python3 reports/ovr-inseason-2026-27/tools/rapm_2022_23_24.py            # 2022-23 .. 2023-24（驗證季不得讀 2024-25）
  python3 reports/ovr-inseason-2026-27/tools/rapm_2022_25.py --self-test  # synthetic stints with known effects

Input: the local stint files written by scripts/prepare_defense_b1.js
  reports/defense-seventh/<season>/stints/stints.jsonl
Each stint has teams[i] = {teamId, players[5], opponent{points,...}, defensivePossessions};
teams[i].opponent holds what the OTHER team scored while team i defended.

Outputs (reports/ovr-inseason-2026-27/data/):
  onoff.csv                 per player-season: on/off offensive, defensive and net rating per 100
  rapm-2022-23-24.csv       per player: ridge-regularised offensive / defensive / net impact per 100
  rapm-2022-23-24-summary.json chosen ridge strength, cross-validated error

Model: for every stint and side, y = 100 * points / possessions, weight = possessions,
y = mu + sum(offense players' O) - sum(defense players' D); a player's net impact = O + D,
positive D means fewer points allowed. Ridge strength is chosen by 5-fold cross-validation
grouped by game, so a game never sits in both train and test. Pooled RAPM uses all seasons
with one coefficient per player; the last-season RAPM uses that season only.
"""
import csv, json, sys, unicodedata, zlib
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / 'data'
SEASONS = ['2022-23', '2023-24']
LAMBDAS = [100, 300, 1000, 3000, 10000, 30000]


def stint_path(season):
    return ROOT / f'reports/defense-seventh/{season}/stints/stints.jsonl'


def observations(seasons, reader=None):
    """Yield (season, gameId, offensePlayers, defensePlayers, points, possessions, offenseTeam, defenseTeam)."""
    for season in seasons:
        lines = reader(season) if reader else open(stint_path(season), encoding='utf-8')
        for line in lines:
            s = json.loads(line) if isinstance(line, str) else line
            if s['seconds'] <= 0 or len(s['teams']) != 2:
                continue
            for d in (0, 1):
                defense, offense = s['teams'][d], s['teams'][1 - d]
                poss = defense['defensivePossessions']
                if poss <= 0:
                    continue
                yield season, s['id'], offense['players'], defense['players'], defense['opponent']['points'], poss, offense['teamId'], defense['teamId']


def onoff(obs):
    """On/off ratings per player-season-team; off = same team's possessions without the player."""
    team = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # offPts, offPoss, defPts, defPoss
    on = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for season, _, op, dp, pts, poss, ot, dt in obs:
        t = team[(season, ot)]; t[0] += pts; t[1] += poss
        t = team[(season, dt)]; t[2] += pts; t[3] += poss
        for p in op:
            o = on[(season, ot, p)]; o[0] += pts; o[1] += poss
        for p in dp:
            o = on[(season, dt, p)]; o[2] += pts; o[3] += poss
    rows = []
    for (season, tid, pid), o in on.items():
        t = team[(season, tid)]
        off = [t[i] - o[i] for i in range(4)]
        r = lambda a, b: 100 * a / b if b > 0 else None
        rows.append({'season': season, 'teamId': tid, 'playerId': pid, 'onPoss': o[1] + o[3], 'offPoss': off[1] + off[3],
                     'onORtg': r(o[0], o[1]), 'onDRtg': r(o[2], o[3]), 'offORtg': r(off[0], off[1]), 'offDRtg': r(off[2], off[3])})
    for x in rows:
        if None not in (x['onORtg'], x['onDRtg'], x['offORtg'], x['offDRtg']):
            x['onNet'] = x['onORtg'] - x['onDRtg']; x['offNet'] = x['offORtg'] - x['offDRtg']; x['onOffNet'] = x['onNet'] - x['offNet']
    return rows


def normal_equations(obs, index, n_folds=5):
    """Accumulate X'WX and X'Wy per game fold; columns [O_0..O_P-1, D_0..D_P-1]."""
    P = len(index); K = 2 * P
    XtX = np.zeros((n_folds, K + 1, K + 1)); Xty = np.zeros((n_folds, K + 1)); yy = np.zeros(n_folds); wsum = np.zeros(n_folds)
    fold_of = {}
    for _, gid, op, dp, pts, poss, _, _ in obs:
        f = fold_of.setdefault(gid, zlib.crc32(str(gid).encode()) % n_folds)  # stable across runs
        cols = [K] + [index[p] for p in op] + [P + index[p] for p in dp]
        sign = np.array([1.0] + [1.0] * len(op) + [-1.0] * len(dp))
        y = 100 * pts / poss
        XtX[f][np.ix_(cols, cols)] += poss * np.outer(sign, sign)
        Xty[f][cols] += poss * y * sign
        yy[f] += poss * y * y; wsum[f] += poss
    return XtX, Xty, yy, wsum


def solve(A, b, lam, K, mean=None):
    """Ridge toward `mean` (zeros = ordinary RAPM); the intercept is never penalised."""
    pen = lam * np.eye(A.shape[0]); pen[K, K] = 0
    return np.linalg.solve(A + pen, b if mean is None else b + pen @ mean)


def fit_rapm(obs, players, prior=None):
    index = {p: i for i, p in enumerate(players)}
    K = 2 * len(players)
    XtX, Xty, yy, wsum = normal_equations(obs, index)
    mean = None
    if prior:
        mean = np.zeros(K + 1)
        for p, i in index.items():
            if p in prior:
                mean[i], mean[len(players) + i] = prior[p]
    cv = {}
    for lam in LAMBDAS:
        sse = 0.0
        for f in range(XtX.shape[0]):
            tr = [g for g in range(XtX.shape[0]) if g != f]
            b = solve(XtX[tr].sum(0), Xty[tr].sum(0), lam, K, mean)
            sse += yy[f] - 2 * b @ Xty[f] + b @ XtX[f] @ b  # weighted SSE on the held-out fold
        cv[lam] = float(sse / wsum.sum())
    lam = min(cv, key=cv.get)
    b = solve(XtX.sum(0), Xty.sum(0), lam, K, mean)
    poss = np.diag(XtX.sum(0))[:K]
    out = {p: {'O': float(b[i]), 'D': float(b[len(players) + i]), 'poss': float(poss[i] + poss[len(players) + i])} for p, i in index.items()}
    for v in out.values():
        v['net'] = v['O'] + v['D']
    return out, {'lambda': lam, 'cvWeightedMSE': cv, 'intercept': float(b[K])}


def spearman(a, b):
    def rank(v):
        o = np.argsort(v); r = np.empty(len(v)); r[o] = np.arange(len(v)); return r
    return float(np.corrcoef(rank(np.array(a)), rank(np.array(b)))[0, 1])


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower().replace('.', '').replace(' iii', '').replace(' jr', '')


def run(seasons, reader=None, write=True):
    obs = list(observations(seasons, reader))
    players = sorted({p for o in obs for p in o[2] + o[3]})
    # 此複本不讀任何目標季名冊或彙總，name 留空（演算法不變）。
    names = {}
    pooled, pooled_fit = fit_rapm(obs, players)
    last = [o for o in obs if o[0] == seasons[-1]]
    single, single_fit = fit_rapm(last, sorted({p for o in last for p in o[2] + o[3]}))
    if not write:
        return pooled, pooled_fit
    with open(OUT / 'onoff-2022-23-24.csv', 'w', encoding='utf-8', newline='') as fh:
        rows = onoff(obs)
        w = csv.DictWriter(fh, fieldnames=['season', 'teamId', 'playerId', 'name', 'onPoss', 'offPoss', 'onORtg', 'onDRtg', 'onNet', 'offORtg', 'offDRtg', 'offNet', 'onOffNet'])
        w.writeheader()
        for r in rows:
            w.writerow({**r, 'name': names.get(r['playerId'], '')})
    with open(OUT / 'rapm-2022-23-24.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['playerId', 'name', 'pooledNet', 'pooledO', 'pooledD', 'pooledPoss', 'lastSeasonNet', 'lastSeasonO', 'lastSeasonD', 'lastSeasonPoss'])
        for p in sorted(pooled, key=lambda p: -pooled[p]['net']):
            a, s = pooled[p], single.get(p, {})
            w.writerow([p, names.get(p, ''), round(a['net'], 3), round(a['O'], 3), round(a['D'], 3), round(a['poss']),
                        round(s.get('net', 0), 3), round(s.get('O', 0), 3), round(s.get('D', 0), 3), round(s.get('poss', 0))])
    summary = {'seasons': seasons, 'observations': len(obs), 'players': len(players),
               'pooled': pooled_fit, 'lastSeason': single_fit}
    (OUT / 'rapm-2022-23-24-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def self_test():
    """Synthetic league with known O/D effects: RAPM must recover them better than chance."""
    rng = np.random.default_rng(7)
    P = 150; trueO = rng.normal(0, 2.5, P); trueD = rng.normal(0, 2.0, P)
    teams = [list(range(i * 15, i * 15 + 15)) for i in range(10)]
    stints = []
    for g in range(1200):
        a, b = rng.choice(10, 2, replace=False)
        for k in range(20):
            la, lb = list(rng.choice(teams[a], 5, replace=False)), list(rng.choice(teams[b], 5, replace=False))
            sides = []
            for off, de in ((la, lb), (lb, la)):
                poss = float(rng.integers(3, 9))
                rate = 1.12 + (trueO[off].sum() - trueD[de].sum()) / 100
                sides.append({'teamId': 0, 'players': [int(x) for x in de], 'opponent': {'points': float(rng.poisson(rate * poss))}, 'defensivePossessions': poss})
            stints.append({'id': f'g{g}', 'seconds': 100, 'teams': sides})
    fit, info = run(['synthetic'], reader=lambda s: stints, write=False)
    estO = np.array([fit[p]['O'] for p in range(P)]); estD = np.array([fit[p]['D'] for p in range(P)])
    r = {'corrO': float(np.corrcoef(estO, trueO)[0, 1]), 'corrD': float(np.corrcoef(estD, trueD)[0, 1]),
         'corrNet': float(np.corrcoef(estO + estD, trueO + trueD)[0, 1]), 'lambda': info['lambda']}
    # Prior check: a noisy but informative prior must lower held-out error and raise recovery.
    obs = list(observations(['synthetic'], reader=lambda s: stints))
    prior = {p: (trueO[p] + rng.normal(0, 1.5), trueD[p] + rng.normal(0, 1.5)) for p in range(P)}
    pf, pinfo = fit_rapm(obs, list(range(P)), prior)
    r['corrNetWithPrior'] = float(np.corrcoef([pf[p]['net'] for p in range(P)], trueO + trueD)[0, 1])
    r['heldOutMSE'] = min(info['cvWeightedMSE'].values()); r['heldOutMSEWithPrior'] = min(pinfo['cvWeightedMSE'].values())
    print(json.dumps(r))
    assert r['corrNet'] > 0.5, 'RAPM failed to recover synthetic effects'
    assert r['heldOutMSEWithPrior'] < r['heldOutMSE'] and r['corrNetWithPrior'] > r['corrNet'], 'informative prior did not help'


if __name__ == '__main__':
    self_test() if '--self-test' in sys.argv else run(SEASONS)
