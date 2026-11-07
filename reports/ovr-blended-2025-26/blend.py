"""Card OVR calibrated on a blend of the sim target and pooled RAPM (see preregistration.md).

  python reports/ovr-blended-2025-26/blend.py [--league PATH] [--out DIR]

t = (1 - alpha) * sim + alpha * RAPM (per 36, position-centered) for players with >= 1000 pooled
RAPM possessions; the sim target alone otherwise. Model form and ridge are fixed to the current
card formula (position-interactions, ridge 1) so only alpha changes. Player-held-out 5-fold x 10.
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'reports/ovr-calibrated-2025-26'))
import calibrate  # noqa: E402
from calibrate import load, design, wfit, ATTRS, SCALE_MIN_MINUTES, attach_rapm, blended, BLEND_POSS  # noqa: E402

TARGET = ROOT / 'reports/ovr-v53-2025-26/calibration-target-s8-expected.csv'
FORM, LAM = 'position-interactions', 1.0
ALPHAS = [0, 0.25, 0.5, 0.75, 1]
EVAL_POSS = 5000
MAX_R2_DROP = 0.05
FOCUS = ['Alex Caruso', 'Derrick White', 'Dyson Daniels', 'Herbert Jones', 'Marcus Smart',
         'Karlo Matković', 'Isaiah Stewart', 'Mitchell Robinson', 'Zach Edey', 'Rudy Gobert',
         'Norchad Omier', 'Javon Small', 'Ty Jerome', 'Dejounte Murray']


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


def fit_weights(X, t, mc):
    s2 = 1.0
    for _ in range(30):
        w = 1 / (mc + s2); b = wfit(X, t, w, LAM)
        res = t - np.c_[np.ones(len(X)), X] @ b
        s2 = max(1e-3, float(np.sum(w * (res ** 2 - mc)) / np.sum(w)))
    return 1 / (mc + s2)


def oof(rows, X, alpha, rep):
    """Out-of-fold predictions; the blended target and its weights are built from training players only."""
    t, mc = blended(rows, alpha); pred = np.zeros(len(rows))
    idx = np.random.default_rng(rep).permutation(len(rows))
    for k in range(5):
        te = idx[k::5]; tr = np.setdiff1d(idx, te)
        w = fit_weights(X[tr], t[tr], mc[tr])
        pred[te] = np.c_[np.ones(len(te)), X[te]] @ wfit(X[tr], t[tr], w, LAM)
    return pred


def to_ovr(pred, rows):
    ref = np.sort([p for p, r in zip(pred, rows) if r['MIN'] >= SCALE_MIN_MINUTES])
    q = lambda pr: ref[int(round(pr / 100 * (len(ref) - 1)))]
    p1, p50, p99 = q(1), q(50), q(99)
    return np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1), 70 + 29 * (pred - p50) / (p99 - p50))


def main():
    global OUT
    calibrate.configure(sys.argv)
    if '--out' in sys.argv:
        OUT = calibrate.OUT
    rows = load(TARGET); attach_rapm(rows)
    X, _, sd = design(rows, FORM)
    y = np.array([r['y'] for r in rows]); mc = np.array([r['mc'] for r in rows])
    w0 = fit_weights(X, y, mc)
    tot = np.sum(w0 * (y - np.average(y, weights=w0)) ** 2)
    ev = np.array([r['poss'] >= EVAL_POSS for r in rows])
    N = np.array([r['N'] for r in rows])[ev]; D = np.array([r['D'] for r in rows])[ev]; L = np.array([r['lastN'] for r in rows])[ev]
    okL = ~np.isnan(L)
    res, mean_pred = {}, {}
    for a in ALPHAS:
        preds = [oof(rows, X, a, rep) for rep in range(10)]
        mean_pred[a] = np.mean(preds, 0)
        res[a] = {'simR2': float(np.mean([1 - np.sum(w0 * (y - p) ** 2) / tot for p in preds])),
                  'rhoNet': float(np.mean([spearman(p[ev], N) for p in preds])),
                  'rhoDefense': float(np.mean([spearman(p[ev], D) for p in preds])),
                  'rhoLastSeasonNet': float(np.mean([spearman(p[ev][okL], L[okL]) for p in preds]))}
    floor = res[0]['simR2'] - MAX_R2_DROP
    chosen = max(a for a in ALPHAS if res[a]['simR2'] >= floor)
    # Paired bootstrap of the rank-correlation gain, chosen alpha vs alpha 0 (averaged OOF predictions).
    rng = np.random.default_rng(20261018); gain = {'net': [], 'defense': []}
    p0, p1 = mean_pred[0][ev], mean_pred[chosen][ev]
    for _ in range(2000):
        i = rng.integers(0, len(N), len(N))
        gain['net'].append(spearman(p1[i], N[i]) - spearman(p0[i], N[i]))
        gain['defense'].append(spearman(p1[i], D[i]) - spearman(p0[i], D[i]))
    ci = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in gain.items()}
    gates = {'net': res[chosen]['rhoNet'] > res[0]['rhoNet'] and ci['net'][0] > 0,
             'defense': res[chosen]['rhoDefense'] > res[0]['rhoDefense'] and ci['defense'][0] > 0,
             'simR2': res[chosen]['simR2'] >= floor}
    gates['adopt'] = chosen > 0 and all(gates.values())
    # Full-data fits for alpha 0 and the chosen alpha: ranks, per-position rho, value per 10 points.
    full = {}
    for a in sorted({0, chosen}):
        t, m = blended(rows, a); w = fit_weights(X, t, m); b = wfit(X, t, w, LAM)
        pred = np.c_[np.ones(len(X)), X] @ b
        full[a] = {'pred': pred, 'ovr': to_ovr(pred, rows), 'per10': {at: float(b[1 + i] / sd[i] * 10) for i, at in enumerate(ATTRS)}}
    rank = lambda p: {rows[i]['name']: k + 1 for k, i in enumerate(np.argsort(-p))}
    rk0, rk1, rks = rank(full[0]['pred']), rank(full[chosen]['pred']), rank(y)
    posrho = {}
    for pos in ['PG', 'SG', 'SF', 'PF', 'C']:
        i = np.array([r['pos'] == pos for r in rows]) & ev
        posrho[pos] = {'alpha0': spearman(mean_pred[0][i], np.array([r['N'] for r in rows])[i]),
                       'chosen': spearman(mean_pred[chosen][i], np.array([r['N'] for r in rows])[i]), 'players': int(i.sum())}
    summary = {'preregistration': 'preregistration.md', 'league': str(calibrate.LEAGUE.relative_to(ROOT)), 'form': FORM, 'ridge': LAM, 'players': len(rows), 'evaluatedPlayers': int(ev.sum()),
               'blendedPlayers': int(sum(r['poss'] >= BLEND_POSS for r in rows)),
               'heldOut': {str(a): v for a, v in res.items()}, 'simR2Floor': floor, 'chosenAlpha': chosen,
               'bootstrapGain95': ci, 'gates': gates, 'perPositionRhoNet': posrho,
               'valuePer10AttributePoints': {at: {'alpha0': full[0]['per10'][at], 'chosen': full[chosen]['per10'][at]} for at in ATTRS},
               'focusRanks': {n: {'sim': rks[n], 'alpha0': rk0[n], 'chosen': rk1[n]} for n in FOCUS}}
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(OUT / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'ovr', 'ovrAlpha0', 'name', 'pos', 'MIN', 'predictedPer36', 'simulatedPer36', 'rapmPer36Centered', 'pooledPoss'])
        for k, i in enumerate(np.argsort(-full[chosen]['pred'])):
            r = rows[i]
            wr.writerow([k + 1, round(float(full[chosen]['ovr'][i]), 1), round(float(full[0]['ovr'][i]), 1), r['name'], r['pos'], round(r['MIN']),
                         round(float(full[chosen]['pred'][i]), 3), round(r['y'], 3), '' if np.isnan(r['r']) else round(float(r['r']), 3), round(r['poss'])])
    print(json.dumps({k: summary[k] for k in ['heldOut', 'simR2Floor', 'chosenAlpha', 'bootstrapGain95', 'gates', 'focusRanks']}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
