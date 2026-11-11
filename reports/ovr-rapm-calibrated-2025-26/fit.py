"""Box-score OVR calibrated to real impact (RAPM), 2025-26.

Like BPM: the weight of every box-score rate is learned from players' measured impact
instead of being set by hand.

  target   pooled 2022-26 RAPM per 100 possessions (reports/impact-rapm/rapm.csv),
           offense O and defense D fitted separately, net = O + D
  inputs   2025-26 per-100-possession rates from data/season-league.json, plus the
           received-pass share and the v45 on/off opponent shooting already used by
           reports/ovr-expected-2025-26
  fit      ridge, weight = min(RAPM possessions, 20000); ridge strength chosen by repeated
           5-fold cross-validation; training players: >= 5000 RAPM possessions and
           >= 500 minutes in 2025-26
  shrink   predictions from small samples are noisy: each rate is treated as a Poisson count,
           each side's sampling variance follows from the fitted weights, and offense and
           defense are shrunk separately toward a role prior (log minutes per game) by
           empirical Bayes, the same routine as reports/ovr-expected-2025-26. priors.csv
           holds the shrunk values (an unshrunk prior let 92-possession players reach the
           top of box-prior RAPM)
  output   ranking.csv (all 582 players), summary.json, priors.csv (box-predicted O and D
           per player, usable as RAPM prior means)

  python3 reports/ovr-rapm-calibrated-2025-26/fit.py

RAPM itself is ridge-shrunk and partly confounded (coaching, lineups, garbage time); it is
the best available player-level outcome, not ground truth.
"""
import csv, importlib.util, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
spec = importlib.util.spec_from_file_location('expected', ROOT / 'reports/ovr-expected-2025-26/expected-ovr.py')
expected = importlib.util.module_from_spec(spec); spec.loader.exec_module(expected)

OFFENSE = ['pts', 'tsa', 'fg3a', 'fta', 'ast', 'receivedFgm', 'tov', 'oreb']
DEFENSE = ['dreb', 'stl', 'blk', 'pf', 'onoffSaved', 'height']
LAMBDAS = [0.1, 0.3, 1, 3, 10, 30, 100]
MIN_POSS, MIN_MINUTES, WEIGHT_CAP = 5000, 500, 20000


def features():
    league, onoff, received, teams, lg = expected.load(expected.WEIGHTS)
    acc = {}
    for t in teams:
        for p in t['roster']:
            o = p['observed']
            if o['MIN'] <= 0:
                continue
            a = acc.setdefault(p['playerId'], {'name': p['name'], 'pos': p['pos'], 'height': p['heightInches'], 'poss': 0.0, 'MIN': 0.0, 'GP': 0, **{k: 0.0 for k in ['PTS', 'FGA', 'FG3A', 'FTA', 'AST', 'FGM', 'TOV', 'OREB', 'DREB', 'STL', 'BLK', 'PF']}})
            a['poss'] += o['MIN'] * t['poss'] / (t['min'] / 5)
            a['MIN'] += o['MIN']; a['GP'] += o['GP']
            for k in ['PTS', 'FGA', 'FG3A', 'FTA', 'AST', 'FGM', 'TOV', 'OREB', 'DREB', 'STL', 'BLK', 'PF']:
                a[k] += o[k]
    rows = {}
    for pid, a in acc.items():
        per = lambda k: a[k] / a['poss'] * 100
        saved, var = expected.onoff_value(onoff.get(pid), {**expected.WEIGHTS, 'W_ONOFF': 1.0})
        rows[pid] = {'playerId': pid, 'name': a['name'], 'pos': a['pos'], 'MIN': a['MIN'], 'GP': a['GP'], 'poss': a['poss'],
                     'pts': per('PTS'), 'tsa': (a['FGA'] + 0.44 * a['FTA']) / a['poss'] * 100, 'fg3a': per('FG3A'), 'fta': per('FTA'),
                     'ast': per('AST'), 'receivedFgm': received[pid] * per('FGM'), 'tov': per('TOV'), 'oreb': per('OREB'),
                     'dreb': per('DREB'), 'stl': per('STL'), 'blk': per('BLK'), 'pf': per('PF'),
                     'onoffSaved': saved if var is not None else 0.0, 'onoffVar': var, 'height': a['height']}
    return rows


def ridge(X, y, w, lam):
    A = np.c_[np.ones(len(X)), X]
    pen = lam * np.eye(A.shape[1]); pen[0, 0] = 0
    return np.linalg.solve(A.T @ (w[:, None] * A) + pen * w.sum() / len(w), A.T @ (w * y))


def cv(X, y, w, lam, reps=10):
    tot = np.sum(w * (y - np.average(y, weights=w)) ** 2); out = []
    for rep in range(reps):
        idx = np.random.default_rng(rep).permutation(len(y)); sse = 0.0
        for k in range(5):
            te = idx[k::5]; tr = np.setdiff1d(idx, te)
            b = ridge(X[tr], y[tr], w[tr], lam)
            sse += np.sum(w[te] * (y[te] - np.c_[np.ones(len(te)), X[te]] @ b) ** 2)
        out.append(1 - sse / tot)
    return float(np.mean(out))


def standardize(M, ref):
    mu, sd = ref.mean(0), ref.std(0)
    return (M - mu) / sd, mu, sd


def main():
    feats = features()
    rapm = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}
    train = [p for p in feats.values() if p['playerId'] in rapm and float(rapm[p['playerId']]['pooledPoss']) >= MIN_POSS and p['MIN'] >= MIN_MINUTES]
    w = np.array([min(float(rapm[p['playerId']]['pooledPoss']), WEIGHT_CAP) for p in train])
    every = list(feats.values())
    result, models = {}, {}
    for side, cols in (('O', OFFENSE), ('D', DEFENSE)):
        y = np.array([float(rapm[p['playerId']]['pooled' + side]) for p in train])
        Xall = np.array([[p[c] for c in cols] for p in every])
        X = np.array([[p[c] for c in cols] for p in train])
        Z, mu, sd = standardize(X, X)
        scores = {lam: cv(Z, y, w, lam) for lam in LAMBDAS}
        lam = max(scores, key=scores.get)
        b = ridge(Z, y, w, lam)
        rng = np.random.default_rng(20261017)
        boot = np.array([ridge(Z[i], y[i], w[i], lam) for i in (rng.integers(0, len(y), len(y)) for _ in range(500))])
        models[side] = (cols, mu, sd, b)
        result[side] = {'lambda': lam, 'cvR2': scores, 'intercept': float(b[0]),
                        'perUnitRate': {c: {'value': float(b[1 + i] / sd[i]), 'bootstrapSE': float(boot[:, 1 + i].std() / sd[i])} for i, c in enumerate(cols)}}
    for p in every:
        for side, (cols, mu, sd, b) in models.items():
            p['pred' + side] = float(b[0] + ((np.array([p[c] for c in cols]) - mu) / sd) @ b[1:])
        # Sampling variance of each side's prediction: Var(rate) = count * 1e4 / poss^2 per rate feature.
        for side, (cols, mu, sd, b) in models.items():
            var = 0.0
            for i, c in enumerate(cols):
                if c == 'height':
                    continue
                if c == 'onoffSaved':
                    var += (b[1 + i] / sd[i]) ** 2 * (p['onoffVar'] if p['onoffVar'] is not None else 0.0)
                else:
                    var += (b[1 + i] / sd[i]) ** 2 * p[c] * 100 / p['poss']
            p['pred' + side + 'Var'] = var
        p['mpg'] = p['MIN'] / p['GP']
    # Shrink offense and defense separately so priors.csv carries the shrunk values too.
    result['shrinkage'] = {side: expected.shrink(every, 'pred' + side, 'pred' + side + 'Var') for side in 'OD'}
    for p in every:
        p['rawNet'] = p['predO'] + p['predD']
        p['predO'], p['predD'] = p['predOShrunk'], p['predDShrunk']
        p['predNet'] = p['predO'] + p['predD']
        p['predNetB'] = (p['predOB'] + p['predDB']) / 2
    # Net check on held-out players: cross-validated O and D predictions added together.
    yN = np.array([float(rapm[p['playerId']]['pooledNet']) for p in train])
    hand = np.array([0.0] * len(train))
    exp_rows = {r['name']: float(r['netPer100']) for r in csv.DictReader(open(ROOT / 'reports/ovr-expected-2025-26/ranking.csv', encoding='utf-8'))}
    hand = np.array([exp_rows.get(p['name'], 0.0) for p in train])
    def r2_from_single(x):
        X = x[:, None]; return cv((X - X.mean()) / X.std(), yN, w, 0.0)
    oof = np.zeros(len(train))
    for rep in range(1):
        idx = np.random.default_rng(99).permutation(len(train))
        for k in range(5):
            te = idx[k::5]; tr = np.setdiff1d(idx, te)
            for side, cols in (('O', OFFENSE), ('D', DEFENSE)):
                y = np.array([float(rapm[p['playerId']]['pooled' + side]) for p in train])
                X = np.array([[p[c] for c in cols] for p in train]); Z, _, _ = standardize(X, X[tr])
                b = ridge(Z[tr], y[tr], w[tr], result[side]['lambda'])
                oof[te] += np.c_[np.ones(len(te)), Z[te]] @ b
    tot = np.sum(w * (yN - np.average(yN, weights=w)) ** 2)
    result['net'] = {'cvR2_calibrated': float(1 - np.sum(w * (yN - oof) ** 2) / tot),
                     'cvR2_handWeightedExpectedOVR': r2_from_single(hand),
                     'spearmanOOFvsRAPM': float(np.corrcoef(np.argsort(np.argsort(oof)), np.argsort(np.argsort(yN)))[0, 1]),
                     'spearmanHandVsRAPM': float(np.corrcoef(np.argsort(np.argsort(hand)), np.argsort(np.argsort(yN)))[0, 1]),
                     'trainingPlayers': len(train)}
    # Display scale on the predicted net (players >= 500 minutes), same PR1/PR50/PR99 anchors.
    ref = np.sort([p['predNet'] for p in every if p['MIN'] >= MIN_MINUTES])
    q = lambda pr: ref[int(round(pr / 100 * (len(ref) - 1)))]
    p1, p50, p99 = q(1), q(50), q(99)
    for p in every:
        x = p['predNet']; p['ovr'] = 40 + 30 * (x - p1) / (p50 - p1) if x <= p50 else 70 + 29 * (x - p50) / (p99 - p50)
    every.sort(key=lambda p: -p['predNet'])
    result['scaleAnchorsNetPer100'] = {'PR1': float(p1), 'PR50': float(p50), 'PR99': float(p99)}
    (OUT / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(OUT / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'ovr', 'playerId', 'name', 'pos', 'MIN', 'predNet', 'predNetUnshrunk', 'meanShrinkFactor', 'predO', 'predD', 'rapmNet', 'rapmO', 'rapmD', 'rapmPoss'])
        for k, p in enumerate(every):
            r = rapm.get(p['playerId'], {})
            wr.writerow([k + 1, round(p['ovr'], 1), p['playerId'], p['name'], p['pos'], round(p['MIN']), round(p['predNet'], 2), round(p['rawNet'], 2), round(p['predNetB'], 3), round(p['predO'], 2), round(p['predD'], 2),
                         r.get('pooledNet', ''), r.get('pooledO', ''), r.get('pooledD', ''), r.get('pooledPoss', '')])
    with open(OUT / 'priors.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh); wr.writerow(['playerId', 'priorO', 'priorD'])
        for p in every:
            wr.writerow([p['playerId'], round(p['predO'], 3), round(p['predD'], 3)])
    print(json.dumps({k: result[k] for k in ['net']}, indent=1))
    for side in 'OD':
        print(side, 'lambda', result[side]['lambda'], 'cvR2 %.3f' % result[side]['cvR2'][result[side]['lambda']])
        print('  ', {c: (round(v['value'], 3), round(v['bootstrapSE'], 3)) for c, v in result[side]['perUnitRate'].items()})
    # 給 reports/impact-epm-2026-27/epm_live.py 取凍結權重（不影響上面的輸出檔）
    return {'result': result, 'models': models, 'train': train, 'weights': w, 'rapm': rapm}


if __name__ == '__main__':
    main()
