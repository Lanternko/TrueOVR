"""E-311 評估（prereg.md 凍結）：Z2／TG／ZG 各自對 B → Brier、勝場 MAE、30 隊 Spearman；兩季合併成對 bootstrap（E-286 compare 同算法）。
  python -I -X utf8 compare.py   （work/pred-*.json 從 5090 拷回）"""
import hashlib, json, math, os, sys
import numpy as np
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); REP = os.path.dirname(HERE)
H, SIG = 2.5, 12.0
INP = {'2425': 'inputs-2425.json', '2526': 'inputs.json'}
ARMS = ('B', 'Z2', 'TG', 'ZG'); NEW = ('TG', 'Z2', 'ZG')   # NEW 的順序＝平手時的優先序（改動少者優先）
erf = np.vectorize(math.erf)


def games(key):
    g = json.load(open(os.path.join(REP, 'E208-team-rating', INP[key]), encoding='utf-8'))['games']
    return np.array([str(x['home']) for x in g]), np.array([str(x['away']) for x in g]), np.array([float(x['hs'] > x['as']) for x in g])


def pred(arm, key, var):
    P = json.load(open(os.path.join(HERE, 'work', f'pred-{arm}-{key}-{var}.json')))
    m = np.array(P['margin_seed']).mean(0)
    return np.clip(0.5 * (1 + erf((m + H) / SIG / math.sqrt(2))), 1e-6, 1 - 1e-6), m, P


def team_wins(p, home, away, idx=None):
    idx = np.arange(len(p)) if idx is None else idx
    w = {}
    for i in idx:
        w[home[i]] = w.get(home[i], 0) + p[i]; w[away[i]] = w.get(away[i], 0) + 1 - p[i]
    return w


def season(key, var):
    home, away, y = games(key)
    out = {'home': home, 'away': away, 'y': y}
    for arm in ARMS:
        p, m, P = pred(arm, key, var)
        assert P['home'] == list(home) and P['away'] == list(away)
        out[arm] = p; out['m' + arm] = m
    return out


def mae(S, arm, idx=None):
    pw = team_wins(S[arm], S['home'], S['away'], idx); aw = team_wins(S['y'], S['home'], S['away'], idx)
    return float(np.mean([abs(pw[t] - aw[t]) for t in aw]))


def paired(SS, a, b, seed):
    """a−b：合併 Brier（場數加權）與勝場 MAE（兩季平均）的 bootstrap 90% 區間；每季各自重抽場次。"""
    rng = np.random.default_rng(seed); db, dm, dbs = [], [], {k: [] for k in SS}
    for _ in range(2000):
        tot_b, tot_n, m_d = 0.0, 0, 0.0
        for k, S in SS.items():
            ix = rng.integers(0, len(S['y']), len(S['y']))
            d = ((S[a][ix] - S['y'][ix]) ** 2 - (S[b][ix] - S['y'][ix]) ** 2).mean()
            dbs[k].append(d); tot_b += d * len(ix); tot_n += len(ix)
            m_d += (mae(S, a, ix) - mae(S, b, ix)) / len(SS)
        db.append(tot_b / tot_n); dm.append(m_d)
    n = {k: len(S['y']) for k, S in SS.items()}
    pt_b = sum(float(((S[a] - S['y']) ** 2).mean() - ((S[b] - S['y']) ** 2).mean()) * n[k] for k, S in SS.items()) / sum(n.values())
    pt_m = float(np.mean([mae(S, a) - mae(S, b) for S in SS.values()]))
    q = lambda v: [float(np.percentile(v, 5)), float(np.percentile(v, 95))]
    return dict(dBrier=pt_b, dBrier_ci90=q(db), dWinMAE=pt_m, dWinMAE_ci90=q(dm), perSeason_ci90={k: q(v) for k, v in dbs.items()})


def main():
    if hashlib.sha256(open(os.path.join(HERE, 'prereg.md'), 'rb').read()).hexdigest() != open(os.path.join(HERE, 'prereg.sha256')).read().strip():
        print('prereg sha mismatch'); return 1
    res = {}
    for var in ('prior', 'same'):
        SS = {k: season(k, var) for k in ('2425', '2526')}
        r = {'seasons': {}, 'vsB': {}, 'pairs': {}}
        for k, S in SS.items():
            aw = team_wins(S['y'], S['home'], S['away']); ts = sorted(aw); act = np.array([aw[t] for t in ts])
            r['seasons'][k] = dict(n=len(S['y']), brier={a: float(((S[a] - S['y']) ** 2).mean()) for a in ARMS},
                                   winMAE={a: mae(S, a) for a in ARMS},
                                   spearman={a: float(spearmanr([team_wins(S[a], S['home'], S['away'])[t] for t in ts], act)[0]) for a in ARMS},
                                   corrMarginVsB={a: float(np.corrcoef(S['mB'], S['m' + a])[0, 1]) for a in NEW})
        for j, a in enumerate(NEW):
            d = paired(SS, a, 'B', 20261311 + j)
            if var == 'prior':
                ci = d['dBrier_ci90']
                d['verdict'] = '變准' if (d['dBrier'] < 0 and ci[1] < 0.001 and d['dWinMAE'] <= 0.25) else ('持平' if ci[1] < 0.002 else '變差')
            r['vsB'][a] = d
        r['pairs']['ZG-Z2'] = paired(SS, 'ZG', 'Z2', 20261321); r['pairs']['ZG-TG'] = paired(SS, 'ZG', 'TG', 20261322)
        if var == 'prior':
            ok = [a for a in NEW if r['vsB'][a]['verdict'] == '變准']
            if ok:
                best = min(r['vsB'][a]['dBrier'] for a in ok)
                r['chosen'] = next(a for a in NEW if a in ok and r['vsB'][a]['dBrier'] - best <= 0.0005)
            else:
                r['chosen'] = None
        S = SS['2526']; aw = team_wins(S['y'], S['home'], S['away'])
        W = {a: team_wins(S[a], S['home'], S['away']) for a in ARMS}
        rk = lambda w: {t: i + 1 for i, t in enumerate(sorted(w, key=lambda t: -w[t]))}
        R = {a: rk(W[a]) for a in ARMS}; rA = rk(aw)
        r['teams2526'] = sorted(({'team': t, 'actW': aw[t], 'actRank': rA[t], **{f'pred{a}': round(W[a][t], 1) for a in ARMS},
                                  **{f'rank{a}': R[a][t] for a in ARMS}} for t in aw), key=lambda d: d['actRank'])
        res[var] = r
    os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
    json.dump(res, open(os.path.join(HERE, 'results', 'compare.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for var, r in res.items():
        print('==', var, 'chosen', r.get('chosen'))
        for a, d in {**r['vsB'], **r['pairs']}.items():
            print('  ', a, d.get('verdict', ''), {k: (round(v, 5) if isinstance(v, float) else v) for k, v in d.items() if k != 'verdict'})
        for k, s in r['seasons'].items():
            print('  ', k, 'brier', {a: round(v, 5) for a, v in s['brier'].items()}, 'winMAE', {a: round(v, 2) for a, v in s['winMAE'].items()},
                  'rho', {a: round(v, 3) for a, v in s['spearman'].items()})
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
