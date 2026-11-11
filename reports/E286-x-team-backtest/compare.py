"""E-286 評估（prereg.md 凍結）：B vs X 球隊預測 → Brier、勝場 MAE、30 隊 Spearman；兩季合併成對 bootstrap。
  python -I -X utf8 compare.py   （work/pred-*.json 從 5090 拷回）"""
import hashlib, json, math, os, sys
import numpy as np
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); REP = os.path.dirname(HERE)
H, SIG = 2.5, 12.0
INP = {'2425': 'inputs-2425.json', '2526': 'inputs.json'}
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
    for arm in ('B', 'X'):
        p, m, P = pred(arm, key, var)
        assert P['home'] == list(home) and P['away'] == list(away)
        out[arm] = p; out['m' + arm] = m
    return out


def mae(S, arm, idx=None):
    pw = team_wins(S[arm], S['home'], S['away'], idx); aw = team_wins(S['y'], S['home'], S['away'], idx)
    return float(np.mean([abs(pw[t] - aw[t]) for t in aw]))


def main():
    if hashlib.sha256(open(os.path.join(HERE, 'prereg.md'), 'rb').read()).hexdigest() != open(os.path.join(HERE, 'prereg.sha256')).read().strip():
        print('prereg sha mismatch'); return 1
    res = {}
    for var in ('prior', 'same'):
        SS = {k: season(k, var) for k in ('2425', '2526')}
        r = {'seasons': {}}
        for k, S in SS.items():
            bb = {a: float(((S[a] - S['y']) ** 2).mean()) for a in ('B', 'X')}
            aw = team_wins(S['y'], S['home'], S['away']); ts = sorted(aw)
            act = np.array([aw[t] for t in ts])
            rho = {a: float(spearmanr([team_wins(S[a], S['home'], S['away'])[t] for t in ts], act)[0]) for a in ('B', 'X')}
            r['seasons'][k] = dict(n=len(S['y']), brier=bb, dBrier=bb['X'] - bb['B'], winMAE={a: mae(S, a) for a in ('B', 'X')},
                                   spearman=rho, corrMarginBX=float(np.corrcoef(S['mB'], S['mX'])[0, 1]))
        # 合併成對 bootstrap（每季各自重抽場次，Brier 以場數加權＝合併；勝場 MAE 兩季平均）
        rng = np.random.default_rng(20261286)
        db, dm, dbs = [], [], {k: [] for k in SS}
        for _ in range(2000):
            tot_b, tot_n, m_d = 0.0, 0, 0.0
            for k, S in SS.items():
                ix = rng.integers(0, len(S['y']), len(S['y']))
                d = ((S['X'][ix] - S['y'][ix]) ** 2 - (S['B'][ix] - S['y'][ix]) ** 2).mean()
                dbs[k].append(d); tot_b += d * len(ix); tot_n += len(ix)
                m_d += (mae(S, 'X', ix) - mae(S, 'B', ix)) / len(SS)
            db.append(tot_b / tot_n); dm.append(m_d)
        pt_b = sum(r['seasons'][k]['dBrier'] * r['seasons'][k]['n'] for k in SS) / sum(r['seasons'][k]['n'] for k in SS)
        pt_m = float(np.mean([r['seasons'][k]['winMAE']['X'] - r['seasons'][k]['winMAE']['B'] for k in SS]))
        ci = [float(np.percentile(db, 5)), float(np.percentile(db, 95))]
        r['pooled'] = dict(dBrier=pt_b, dBrier_ci90=ci, dWinMAE=pt_m, dWinMAE_ci90=[float(np.percentile(dm, 5)), float(np.percentile(dm, 95))],
                           perSeason_ci90={k: [float(np.percentile(v, 5)), float(np.percentile(v, 95))] for k, v in dbs.items()})
        if var == 'prior':
            v = '變准' if (pt_b < 0 and ci[1] < 0.001 and pt_m <= 0.25) else ('持平' if ci[1] < 0.002 else '變差')
            r['verdict'] = v
        res[var] = r
        # 隊伍表（2025-26）
        S = SS['2526']; aw = team_wins(S['y'], S['home'], S['away'])
        wB, wX = team_wins(S['B'], S['home'], S['away']), team_wins(S['X'], S['home'], S['away'])
        rk = lambda w: {t: i + 1 for i, t in enumerate(sorted(w, key=lambda t: -w[t]))}
        rB, rX, rA = rk(wB), rk(wX), rk(aw)
        r['teams2526'] = sorted(({'team': t, 'actW': aw[t], 'actRank': rA[t], 'predB': round(wB[t], 1), 'rankB': rB[t], 'predX': round(wX[t], 1), 'rankX': rX[t]}
                                 for t in aw), key=lambda d: d['actRank'])
    json.dump(res, open(os.path.join(HERE, 'results', 'compare.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for var, r in res.items():
        print('==', var, r.get('verdict'), {k: round(v, 5) if isinstance(v, float) else v for k, v in r['pooled'].items()})
        for k, s in r['seasons'].items():
            print('  ', k, 'brier', {a: round(v, 5) for a, v in s['brier'].items()}, 'winMAE', {a: round(v, 2) for a, v in s['winMAE'].items()},
                  'rho', {a: round(v, 3) for a, v in s['spearman'].items()}, 'corr', round(s['corrMarginBX'], 4))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
