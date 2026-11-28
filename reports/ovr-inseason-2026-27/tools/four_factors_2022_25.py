"""Four-factor RAPM: which parts of defense are reproducible individual skills? (local data)

  python3 reports/ovr-inseason-2026-27/tools/four_factors_2022_25.py --self-test
  python3 reports/ovr-inseason-2026-27/tools/four_factors_2022_25.py   # 2022-23 .. 2024-25 stints

Same stints and design as rapm.py (five offensive + five defensive players per stint side,
ridge, strength chosen by 5-fold cross-validation grouped by game), but one model per
opponent factor instead of points:

  factor        rate per stint side                         weight
  tovNonSteal   (tov - liveTov) / possessions               possessions   no-steal turnovers
  steal         liveTov / possessions                       possessions   already simulated
  fgaPerPoss    fga / possessions                           possessions   shots allowed
  efg           (fgm + 0.5 * longM) / fga                   fga           shot efficiency allowed
  rimShare      shortA / fga                                fga           shot diet
  threeShare    longA / fga                                 fga
  ftRate        fta / fga                                   fga
  orebRate      (oreb + teamOreb) / reboundOpportunities    reb. opps     second chances allowed

A defender coefficient is reported so that positive means better defense (fewer shots, lower
efficiency, more turnovers, fewer offensive rebounds and free throws).

Reliability: the model is refitted on the two halves of the games (stable game hash) and the
defensive coefficients of players with enough weight in both halves are correlated; the
Spearman-Brown full-sample reliability says how much of the spread is a repeatable skill.
A factor is worth simulating per player only if that reliability is clearly above zero.

Outputs (reports/ovr-inseason-2026-27/data/): four-factors-2022-25.csv,
four-factors-2022-25-summary.json
"""
import csv, json, sys, zlib
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / 'data'
SEASONS = ['2022-23', '2023-24', '2024-25']
LAMBDAS = [30, 100, 300, 1000, 3000, 10000, 30000]
# name: (numerator, denominator, sign so that positive = better defense)
FACTORS = {
    'tovNonSteal': (lambda o, p: o['tov'] - o['liveTov'], lambda o, p: p, +1),
    'steal': (lambda o, p: o['liveTov'], lambda o, p: p, +1),
    'fgaPerPoss': (lambda o, p: o['fga'], lambda o, p: p, -1),
    'efg': (lambda o, p: o['fgm'] + 0.5 * o['longM'], lambda o, p: o['fga'], -1),
    'rimShare': (lambda o, p: o['shortA'], lambda o, p: o['fga'], -1),
    'threeShare': (lambda o, p: o['longA'], lambda o, p: o['fga'], -1),
    'ftRate': (lambda o, p: o['fta'], lambda o, p: o['fga'], -1),
    'orebRate': (lambda o, p: o['oreb'] + o['teamOreb'], lambda o, p: o['reboundOpportunities'], -1),
}
MIN_HALF_WEIGHT = {'possessions': 3000, 'fga': 2500, 'reboundOpportunities': 1200}


def stint_path(season):
    return ROOT / f'reports/defense-seventh/{season}/stints/stints.jsonl'


def sides(seasons, reader=None):
    """(gameId, offensePlayers, defensePlayers, opponentCounts, possessions)."""
    out = []
    for season in seasons:
        for line in (reader(season) if reader else open(stint_path(season), encoding='utf-8')):
            s = json.loads(line) if isinstance(line, str) else line
            if s['seconds'] <= 0 or len(s['teams']) != 2:
                continue
            for d in (0, 1):
                de, of = s['teams'][d], s['teams'][1 - d]
                if de['defensivePossessions'] > 0:
                    out.append((s['id'], of['players'], de['players'], de['opponent'], de['defensivePossessions']))
    return out


def fold_of(gid, n=5):
    return zlib.crc32(str(gid).encode()) % n


def accumulate(rows, index, factor, n_folds=5):
    num, den, _ = FACTORS[factor]
    P = len(index); K = 2 * P
    XtX = np.zeros((n_folds, K + 1, K + 1)); Xty = np.zeros((n_folds, K + 1)); yy = np.zeros(n_folds); ws = np.zeros(n_folds)
    for gid, op, dp, o, poss in rows:
        w = den(o, poss)
        if w <= 0:
            continue
        y = 100 * num(o, poss) / w
        f = fold_of(gid, n_folds)
        cols = [K] + [index[p] for p in op] + [P + index[p] for p in dp]
        sign = np.array([1.0] * (1 + len(op)) + [1.0] * len(dp))  # raw effects; sign applied on output
        XtX[f][np.ix_(cols, cols)] += w * np.outer(sign, sign)
        Xty[f][cols] += w * y * sign
        yy[f] += w * y * y; ws[f] += w
    return XtX, Xty, yy, ws


def solve(A, b, lam, K):
    pen = lam * np.eye(A.shape[0]); pen[K, K] = 0
    return np.linalg.solve(A + pen, b)


def fit(rows, players, factor):
    index = {p: i for i, p in enumerate(players)}; K = 2 * len(players)
    XtX, Xty, yy, ws = accumulate(rows, index, factor)
    cv = {}
    for lam in LAMBDAS:
        sse = 0.0
        for f in range(len(ws)):
            tr = [g for g in range(len(ws)) if g != f]
            b = solve(XtX[tr].sum(0), Xty[tr].sum(0), lam, K)
            sse += yy[f] - 2 * b @ Xty[f] + b @ XtX[f] @ b
        cv[lam] = float(sse / ws.sum())
    lam = min(cv, key=cv.get)
    b = solve(XtX.sum(0), Xty.sum(0), lam, K)
    weight = np.diag(XtX.sum(0))[:K]
    sign = FACTORS[factor][2]
    coef = {p: {'offense': float(b[i]), 'defense': float(sign * b[len(players) + i]),
                'offenseWeight': float(weight[i]), 'defenseWeight': float(weight[len(players) + i])} for p, i in index.items()}
    return coef, {'lambda': lam, 'cvWeightedMSE': cv, 'intercept': float(b[K])}


def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def reliability(rows, players, factor):
    halves = [[r for r in rows if fold_of(r[0], 2) == h] for h in (0, 1)]
    fits = [fit(h, players, factor)[0] for h in halves]
    den_name = {'tovNonSteal': 'possessions', 'steal': 'possessions', 'fgaPerPoss': 'possessions', 'orebRate': 'reboundOpportunities'}.get(factor, 'fga')
    need = MIN_HALF_WEIGHT[den_name]
    out = {}
    for side in ('defense', 'offense'):
        keep = [p for p in players if fits[0][p][side + 'Weight'] >= need and fits[1][p][side + 'Weight'] >= need]
        if len(keep) < 20:
            out[side] = {'players': len(keep)}
            continue
        r = spearman([fits[0][p][side] for p in keep], [fits[1][p][side] for p in keep])
        out[side] = {'players': len(keep), 'splitHalfSpearman': r, 'fullSampleReliability': 2 * r / (1 + r) if r > -1 else None}
    return out


def run(seasons, reader=None, write=True, factors=FACTORS):
    rows = sides(seasons, reader)
    players = sorted({p for r in rows for p in r[1] + r[2]})
    results, summary = {}, {'seasons': seasons, 'stintSides': len(rows), 'players': len(players), 'factors': {}}
    for factor in factors:
        coef, info = fit(rows, players, factor)
        info['reliability'] = reliability(rows, players, factor)
        results[factor] = coef; summary['factors'][factor] = info
        print(factor, json.dumps({'lambda': info['lambda'], 'reliability': info['reliability']}))
    if not write:
        return results, summary
    # 此複本不讀任何目標季名冊或彙總；不需要 name，留空。
    names = {}
    with open(OUT / 'four-factors-2022-25.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['playerId', 'name'] + [f'{f}_{s}' for f in factors for s in ('defense', 'offense')] + ['defensePossessions'])
        for p in players:
            w.writerow([p, names.get(p, '')] + [round(results[f][p][s], 4) for f in factors for s in ('defense', 'offense')]
                       + [round(results['steal'][p]['defenseWeight']) if 'steal' in results else ''])
    (OUT / 'four-factors-2022-25-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return results, summary


def self_test():
    """Known defender effects on non-steal turnovers and eFG must be recovered; a factor with no
    individual effect must show near-zero split-half reliability."""
    rng = np.random.default_rng(11)
    P = 150; teams = [list(range(i * 15, i * 15 + 15)) for i in range(10)]
    tovD = rng.normal(0, 1.5, P)   # turnovers per 100 possessions forced
    efgD = rng.normal(0, 2.0, P)   # eFG points allowed (positive = better defense)
    stints = []
    for g in range(1500):
        a, b = rng.choice(10, 2, replace=False)
        for _ in range(20):
            la, lb = rng.choice(teams[a], 5, replace=False), rng.choice(teams[b], 5, replace=False)
            sides_ = []
            for off, de in ((la, lb), (lb, la)):
                poss = float(rng.integers(3, 9))
                ptov = np.clip(0.13 + tovD[de].sum() / 100, 0.02, 0.5)
                tov = rng.binomial(int(poss), ptov); live = rng.binomial(tov, 0.5)
                fga = int(rng.integers(2, 9)); pe = np.clip(0.54 - efgD[de].sum() / 100, 0.2, 0.8)
                long_a = rng.binomial(fga, 0.4); made = rng.binomial(fga, pe)
                long_m = min(long_a, rng.binomial(made, 0.35))
                reb = int(rng.integers(1, 5))
                o = {'tov': tov, 'liveTov': live, 'fga': fga, 'fgm': made, 'longA': long_a, 'longM': long_m, 'shortA': rng.binomial(fga, 0.45),
                     'fta': rng.binomial(fga, 0.25), 'oreb': rng.binomial(reb, 0.25), 'teamOreb': 0, 'reboundOpportunities': reb}
                sides_.append({'teamId': 0, 'players': [int(x) for x in de], 'opponent': o, 'defensivePossessions': poss})
            stints.append({'id': f'g{g}', 'seconds': 100, 'teams': sides_})
    res, summ = run(['synthetic'], reader=lambda s: stints, write=False, factors={k: FACTORS[k] for k in ('tovNonSteal', 'efg', 'orebRate')})
    # Live (steal) share is 0.5 of all turnovers, so the non-steal effect is half of tovD.
    r_tov = float(np.corrcoef([res['tovNonSteal'][p]['defense'] for p in range(P)], tovD)[0, 1])
    r_efg = float(np.corrcoef([res['efg'][p]['defense'] for p in range(P)], efgD)[0, 1])
    rel_null = summ['factors']['orebRate']['reliability']['defense'].get('fullSampleReliability')
    print(json.dumps({'corrTovNonSteal': r_tov, 'corrEfg': r_efg, 'nullFactorReliability': rel_null}))
    assert r_tov > 0.5 and r_efg > 0.5, 'failed to recover known effects'
    assert rel_null is None or rel_null < 0.3, 'null factor looks reliable'


if __name__ == '__main__':
    self_test() if '--self-test' in sys.argv else run(SEASONS)
