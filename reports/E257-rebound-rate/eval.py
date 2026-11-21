"""E-257 評估（預註冊 11cd2e9）：球隊籃板率能不能補 T＋K10 殘差。python -I -X utf8 eval.py → work/eval.json"""
import collections, gzip, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REP = os.path.dirname(HERE); ROOT = os.path.dirname(REP)
sys.path.insert(0, os.path.join(REP, 'E253-actual-results-blend')); sys.path.insert(0, os.path.join(REP, 'E223-team-rating'))
import eval as E253
from e223_lib import load_season
H, SIG, K, KS = 2.5, 12.0, 10, 5
ARMS = {'SORB': ['orb'], 'SDRB': ['drb'], 'SREB': ['orb', 'drb']}
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))


def box_season(season):
    S = load_season(season); out = {}
    d = os.path.join(ROOT, f'data/season-source/dnp-20{season[:2]}-{season[2:]}-raw')
    for g in S['games']:
        bx = json.loads(gzip.open(os.path.join(d, f"boxscore_{g['id']}.json.gz"), 'rt', encoding='utf-8').read())['game']
        out[g['id']] = {str(bx[s]['teamId']): dict(oreb=bx[s]['statistics']['reboundsOffensive'], dreb=bx[s]['statistics']['reboundsDefensive'])
                        for s in ('homeTeam', 'awayTeam')}
    return out, S


def box_2627():
    d = json.load(open(os.path.join(ROOT, 'data/season-source-2026-27/team-games.json'), encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d; box = collections.defaultdict(dict); ab = {}
    for row in t['rowSet']:
        r = dict(zip(t['headers'], row)); ab[str(r['TEAM_ID'])] = r['TEAM_ABBREVIATION']
        box[r['GAME_ID']][str(r['TEAM_ID'])] = dict(oreb=r['OREB'], dreb=r['DREB'])
    return dict(box), ab


def acc_add(acc, lg, g, b):
    for t, o in ((g['home'], g['away']), (g['away'], g['home'])):
        a = acc[t]; a['of'] += b[t]['oreb']; a['oc'] += b[t]['oreb'] + b[o]['dreb']
        a['df'] += b[o]['oreb']; a['dc'] += b[o]['oreb'] + b[t]['dreb']; a['n'] += 1
        lg['f'] += b[t]['oreb']; lg['c'] += b[t]['oreb'] + b[o]['dreb']


def team_feat(a, lg):
    if a['n'] == 0 or lg['c'] == 0:
        return dict(orb=0.0, drb=0.0)
    s = a['n'] / (a['n'] + KS); m = lg['f'] / lg['c']
    return dict(orb=s * (a['of'] / a['oc'] - m), drb=s * (a['df'] / a['dc'] - m))


def features(G, box):
    acc = collections.defaultdict(lambda: collections.Counter()); lg = collections.Counter()
    X = [None] * len(G); byd = collections.defaultdict(list)
    for i, g in enumerate(G):
        byd[g['date']].append(i)
    for day in sorted(byd):
        for i in byd[day]:
            g = G[i]; fh, fa = team_feat(acc[g['home']], lg), team_feat(acc[g['away']], lg)
            X[i] = {k: fh[k] - fa[k] for k in fh}
        for i in byd[day]:
            g = G[i]; b = box.get(g['gid'])
            if b and g['home'] in b and g['away'] in b:
                acc_add(acc, lg, g, b)
    return X, acc, lg


def brier(G, m, idx):
    y = np.array([1.0 if G[i]['d'] > 0 else 0.0 for i in idx]); p = np.clip(Phi((m + H) / SIG), 1e-6, 1 - 1e-6)
    return (p - y) ** 2


def fit(G, mb, X, cols, idx):
    A = np.array([[X[i][c] for c in cols] for i in idx]); r = np.array([G[i]['d'] - (mb[i] + H) for i in idx])
    beta, *_ = np.linalg.lstsq(A, r, rcond=None); res = r - A @ beta
    se = np.sqrt(np.diag(res @ res / (len(r) - len(cols)) * np.linalg.inv(A.T @ A)))
    return beta, se


def evaluate(G, mb, X, test, betas, seed=20261107):
    b0 = brier(G, mb[test], test); out = {'B0': float(b0.mean()), 'n': len(test), 'arms': {}}
    ix = np.random.default_rng(seed).integers(0, len(test), (10000, len(test)))
    for a, cols in ARMS.items():
        A = np.array([[X[i][c] for c in cols] for i in test]); m = mb[test] + A @ betas[a][0]
        d = brier(G, m, test) - b0; bm = d[ix].mean(1)
        out['arms'][a] = dict(beta=list(map(float, betas[a][0])), se=list(map(float, betas[a][1])), dBrier=float(d.mean()),
                              ci9833=[float(np.percentile(bm, 0.833)), float(np.percentile(bm, 99.167))],
                              ci90=[float(np.percentile(bm, 5)), float(np.percentile(bm, 95))], meanShift=float(np.abs(A @ betas[a][0]).mean()))
    return out


def season_rates(box):
    acc = collections.defaultdict(collections.Counter); lg = collections.Counter()
    for gid, b in box.items():
        ts = list(b)
        if len(ts) != 2:
            continue
        acc_add(acc, lg, dict(home=ts[0], away=ts[1]), b)
    return {t: (a['of'] / a['oc'], a['df'] / a['dc']) for t, a in acc.items()}


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    G25 = sorted(E253.load_2526(), key=lambda g: g['date']); box25, _ = box_season('2526')
    mb25 = np.array(E253.blend(G25, K, None)[0]); X25, _, _ = features(G25, box25)
    tr = [i for i, g in enumerate(G25) if g['date'] < '2026-01-01']; te = [i for i, g in enumerate(G25) if g['date'] >= '2026-01-01']
    bt = {a: fit(G25, mb25, X25, c, tr) for a, c in ARMS.items()}; o25 = evaluate(G25, mb25, X25, te, bt)
    passing = [a for a, v in o25['arms'].items() if v['ci9833'][1] < 0]
    pick = min(passing, key=lambda a: o25['arms'][a]['dBrier']) if passing else None
    full = {a: fit(G25, mb25, X25, c, list(range(len(G25)))) for a, c in ARMS.items()}
    G26 = sorted(E253.load_2627(), key=lambda g: g['date']); box26, AB = box_2627()
    mb26 = np.array(E253.blend(G26, K, None)[0]); X26, acc26, lg26 = features(G26, box26)
    o26 = evaluate(G26, mb26, X26, list(range(len(G26))), full)
    J = {'J1_pass': bool(pick), 'pick': pick, 'J2_pass': bool(pick and o26['arms'][pick]['dBrier'] <= 0)}
    # 季層級
    res = collections.defaultdict(list)
    for g in G25:
        r = g['d'] - (g['mT'] + H); res[g['home']].append(r); res[g['away']].append(-r)
    tids = sorted(res); rr = np.array([np.mean(res[t]) for t in tids])
    s25 = season_rates(box25); box24, _ = box_season('2425'); s24 = season_rates(box24); season = {}
    for name, s in (('2526', s25), ('2425', s24)):
        for j, k in enumerate(('orb', 'drb')):
            x = np.array([s[t][j] for t in tids]); season[f'{name}_{k}'] = float(np.corrcoef(x, rr)[0, 1])
    # 2026-27 現在調整量（整季 β、SREB 或採用臂）
    show = pick or 'SREB'; beta = full[show][0]; lgm = lg26['f'] / lg26['c']; now = {}
    for t, a in acc26.items():
        f = team_feat(a, lg26)
        now[AB.get(t, t)] = dict(n=a['n'], orb=round(a['of'] / a['oc'], 3), drb=round(a['df'] / a['dc'], 3),
                                 adj=round(float(sum(f[c] * b for c, b in zip(ARMS[show], beta))), 2), arm=show)
    out = dict(prereg='11cd2e9', j1=o25, j2=o26, judgment=J, beta_full={a: list(map(float, b[0])) for a, b in full.items()},
               se_full={a: list(map(float, b[1])) for a, b in full.items()}, season_corr=season, lg_orb_2627=lgm, now_2627=now)
    json.dump(out, open(os.path.join(HERE, 'work', 'eval.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    r = lambda v: round(v, 4)
    print(json.dumps(dict(J=J, B0=o25['B0'], j1={a: (r(v['dBrier']), list(map(r, v['ci9833'])), [round(x, 1) for x in v['beta']], [round(x, 1) for x in v['se']]) for a, v in o25['arms'].items()},
                          j2={a: (r(v['dBrier']), list(map(r, v['ci90']))) for a, v in o26['arms'].items()},
                          full={a: ([round(x, 1) for x in out['beta_full'][a]], [round(x, 1) for x in out['se_full'][a]]) for a in ARMS},
                          season={k: round(v, 3) for k, v in season.items()}, lg=lgm), indent=1, ensure_ascii=False))
    for t in sorted(now, key=lambda t: -now[t]['adj'])[:5] + ['POR']:
        print(t, now[t])
