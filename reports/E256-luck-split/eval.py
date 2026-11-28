"""E-256 評估（預註冊 8715446）：殘差拆運氣型／結構型。python -I -X utf8 eval.py → work/eval.json"""
import collections, gzip, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REP = os.path.dirname(HERE); ROOT = os.path.dirname(REP)
sys.path.insert(0, os.path.join(REP, 'E253-actual-results-blend')); sys.path.insert(0, os.path.join(REP, 'E223-team-rating'))
import eval as E253
from e223_lib import load_season
H, SIG, K = 2.5, 12.0, 10
COMP = ['C3', 'CFT', 'C2', 'REST']
ARMS = {'TOT': [['C3', 'CFT', 'C2', 'REST']], 'SPLIT2': [['C3', 'CFT'], ['C2', 'REST']], 'SPLIT4': [['C3'], ['CFT'], ['C2'], ['REST']]}
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))


def box_raw(season):
    S = load_season(season); out = {}
    d = os.path.join(ROOT, f'data/season-source/dnp-20{season[:2]}-{season[2:]}-raw')
    for g in S['games']:
        bx = json.loads(gzip.open(os.path.join(d, f"boxscore_{g['id']}.json.gz"), 'rt', encoding='utf-8').read())['game']
        b = {}
        for s in ('homeTeam', 'awayTeam'):
            st = bx[s]['statistics']
            b[str(bx[s]['teamId'])] = dict(m3=st['threePointersMade'], a3=st['threePointersAttempted'], m2=st['twoPointersMade'],
                                         a2=st['twoPointersAttempted'], mft=st['freeThrowsMade'], aft=st['freeThrowsAttempted'])
        out[g['id']] = b
    return out


def rates(box):
    c = collections.Counter()
    for b in box.values():
        for v in b.values():
            c.update(v)
    return dict(p3=c['m3'] / c['a3'], p2=c['m2'] / c['a2'], pft=c['mft'] / c['aft'])


def comps(g, b, p):
    """主隊視角每場成分（自己 − 對手，單位：分）。"""
    h, a = b[g['home']], b[g['away']]
    lk = lambda x, m, at, q, w: w * (x[m] - x[at] * q)
    c3 = lk(h, 'm3', 'a3', p['p3'], 3) - lk(a, 'm3', 'a3', p['p3'], 3)
    cft = lk(h, 'mft', 'aft', p['pft'], 1) - lk(a, 'mft', 'aft', p['pft'], 1)
    c2 = lk(h, 'm2', 'a2', p['p2'], 2) - lk(a, 'm2', 'a2', p['p2'], 2)
    r = g['d'] - (g['mT'] + H)
    return dict(C3=c3, CFT=cft, C2=c2, REST=r - c3 - cft - c2)


def features(G, box, p):
    acc = collections.defaultdict(lambda: [collections.Counter(), 0])
    X = [None] * len(G); per = [None] * len(G); byd = collections.defaultdict(list)
    for i, g in enumerate(G):
        byd[g['date']].append(i)
    for day in sorted(byd):
        for i in byd[day]:
            g = G[i]
            X[i] = {c: acc[g['home']][0][c] / (acc[g['home']][1] + K) - acc[g['away']][0][c] / (acc[g['away']][1] + K) for c in COMP}
        for i in byd[day]:
            g = G[i]; b = box.get(g['gid'])
            if b is None or g['home'] not in b or g['away'] not in b:
                continue
            cc = comps(g, b, p); per[i] = cc
            for t, s in ((g['home'], 1), (g['away'], -1)):
                acc[t][0].update({k: s * x for k, x in cc.items()}); acc[t][1] += 1
    return X, per


def design(X, arm, idx):
    return np.array([[sum(X[i][c] for c in grp) for grp in ARMS[arm]] for i in idx])


def brier(G, m, idx):
    y = np.array([1.0 if G[i]['d'] > 0 else 0.0 for i in idx]); pr = np.clip(Phi((m + H) / SIG), 1e-6, 1 - 1e-6)
    return (pr - y) ** 2


def fit(G, X, arm, idx):
    A = design(X, arm, idx); r = np.array([G[i]['d'] - (G[i]['mT'] + H) for i in idx])
    beta, *_ = np.linalg.lstsq(A, r, rcond=None); res = r - A @ beta
    se = np.sqrt(np.diag(res @ res / (len(r) - A.shape[1]) * np.linalg.inv(A.T @ A)))
    return beta, se


def evaluate(G, X, test, betas, seed=20261107):
    mT = np.array([G[i]['mT'] for i in test])
    b0 = brier(G, mT + design(X, 'TOT', test)[:, 0], test); out = {'B0': float(b0.mean()), 'n': len(test), 'arms': {}}
    ix = np.random.default_rng(seed).integers(0, len(test), (10000, len(test)))
    for a in ARMS:
        d = brier(G, mT + design(X, a, test) @ betas[a][0], test) - b0; bm = d[ix].mean(1)
        out['arms'][a] = dict(dBrier=float(d.mean()), ci9833=[float(np.percentile(bm, 0.833)), float(np.percentile(bm, 99.167))],
                              ci90=[float(np.percentile(bm, 5)), float(np.percentile(bm, 95))])
    return out


def load_2627_box():
    d = json.load(open(os.path.join(ROOT, 'data/season-source-2026-27/team-games.json'), encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d; box = collections.defaultdict(dict); ab = {}
    for row in t['rowSet']:
        r = dict(zip(t['headers'], row)); ab[str(r['TEAM_ID'])] = r['TEAM_ABBREVIATION']
        box[r['GAME_ID']][str(r['TEAM_ID'])] = dict(m3=r['FG3M'], a3=r['FG3A'], m2=r['FGM'] - r['FG3M'], a2=r['FGA'] - r['FG3A'],
                                                    mft=r['FTM'], aft=r['FTA'])
    return dict(box), ab


def team_seq(G, per):
    seq = collections.defaultdict(list)
    for i, g in enumerate(G):
        c = per[i]
        if c is None:
            continue
        seq[g['home']].append(c); seq[g['away']].append({k: -x for k, x in c.items()})
    return seq


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    p25 = rates(box_raw('2425')); box25 = box_raw('2526'); p26 = rates(box25)
    G25 = sorted(E253.load_2526(), key=lambda g: g['date']); X25, per25 = features(G25, box25, p25)
    tr = [i for i, g in enumerate(G25) if g['date'] < '2026-01-01']; te = [i for i, g in enumerate(G25) if g['date'] >= '2026-01-01']
    bt = {a: fit(G25, X25, a, tr) for a in ARMS}; o25 = evaluate(G25, X25, te, bt)
    passing = [a for a, v in o25['arms'].items() if a != 'TOT' and v['ci9833'][1] < 0 and v['dBrier'] < o25['arms']['TOT']['dBrier']]
    pick = min(passing, key=lambda a: o25['arms'][a]['dBrier']) if passing else None
    full = {a: fit(G25, X25, a, list(range(len(G25)))) for a in ARMS}
    G26 = sorted(E253.load_2627(), key=lambda g: g['date']); box26, AB = load_2627_box(); X26, per26 = features(G26, box26, p26)
    o26 = evaluate(G26, X26, list(range(len(G26))), full)
    J = {'J1_pass': bool(pick), 'pick': pick, 'J2_pass': bool(pick and o26['arms'][pick]['dBrier'] <= 0)}
    # 隊層級：2025-26 前 7 場拆解 vs 第 8 場起
    team = {}
    for t, s in team_seq(G25, per25).items():
        e, r = s[:7], s[7:]
        mean = lambda xs, k: sum(x[k] for x in xs) / len(xs)
        team[AB.get(t, t)] = dict(early={k: round(mean(e, k), 2) for k in COMP}, rest={k: round(mean(r, k), 2) for k in COMP},
                                 early_tot=round(sum(mean(e, k) for k in COMP), 2), rest_tot=round(sum(mean(r, k) for k in COMP), 2))
    tl = list(team.values()); corr = {}
    for k in COMP + ['TOT']:
        a = np.array([v['early_tot'] if k == 'TOT' else v['early'][k] for v in tl]); b = np.array([v['rest_tot'] for v in tl])
        own = np.array([v['rest_tot'] if k == 'TOT' else v['rest'][k] for v in tl])
        corr[k] = dict(r_vs_rest_total=float(np.corrcoef(a, b)[0, 1]), slope_vs_rest_total=float(np.polyfit(a, b, 1)[0]),
                       r_vs_rest_same=float(np.corrcoef(a, own)[0, 1]), sd_early=float(a.std()))
    # 2026-27 現在各隊拆解
    show = pick or 'SPLIT4'; now = {}
    for t, s in team_seq(G26, per26).items():
        n = len(s); tot = {k: sum(x[k] for x in s) for k in COMP}
        adj = sum(beta * sum(tot[c] for c in grp) / (n + K) for grp, beta in zip(ARMS[show], full[show][0]))
        now[AB.get(t, t)] = dict(n=n, per_game={k: round(v / n, 2) for k, v in tot.items()}, B0=round(sum(tot.values()) / (n + K), 2),
                                 arm=show, adj=round(float(adj), 2))
    out = dict(prereg='8715446', rates_2425=p25, rates_2526=p26, beta_train={a: list(map(float, b[0])) for a, b in bt.items()},
               se_train={a: list(map(float, b[1])) for a, b in bt.items()},
               beta_full={a: list(map(float, b[0])) for a, b in full.items()}, se_full={a: list(map(float, b[1])) for a, b in full.items()},
               j1=o25, j2=o26, judgment=J, team_2526=team, corr_2526=corr, now_2627=now)
    json.dump(out, open(os.path.join(HERE, 'work', 'eval.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    r2 = lambda d: {a: [round(x, 2) for x in v] for a, v in d.items()}
    print(json.dumps(dict(J=J, rates=[p25, p26], j1=o25, j2=o26, bt=r2(out['beta_train']), st=r2(out['se_train']), bf=r2(out['beta_full']),
                          sf=r2(out['se_full']), corr=corr), indent=1, ensure_ascii=False))
