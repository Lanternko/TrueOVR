"""Simulation-calibrated attribute OVR (2025-26).

Like the baseball calculator (attributes -> wOBA -> OVR), but the value of each attribute is
learned from the simulator instead of being set by hand:

  target  v47 simulated contribution, position-centered (step 1), per 36 simulated minutes
  inputs  the card attributes in data/season-league.json (40-99 percentile scale) + height
  fit     weighted least squares / ridge; weight = 1 / (Monte Carlo variance + residual
          true variance), so noisy bench players count less. Noise in the target averages
          out across 582 players; it does not need 500 games per player.
  choose  model form and ridge strength by repeated 5-fold cross-validation only
  output  OVR = predicted per-36 value mapped PR1=40 / PR50=70 / PR99=99 (players >= 500 min)

  python3 reports/ovr-calibrated-2025-26/calibrate.py [--target PATH] [--league PATH] [--out DIR]

Extra derived card attribute 'creation': self-created field-goal attempts per 36 minutes
= (1 - receivedShare) * FGA/36, receivedShare from the v41 validation export
(creationDependence_sourceRole). Mapped to 40-99 with the same percentile rule and pool as
scripts/build_season_league.js (GP >= 30 and MPG >= 20). Real-player simulations use this
self-creation through opportunityMeasurement; without it the formula cannot see it.

Extra derived card attribute 'pressure': the four-factor RAPM non-steal turnovers forced
(reports/impact-rapm/four-factors.csv, tovNonSteal_defense), percentile-mapped the same way.
It drives the v53 simulator's dead-ball pressure (reports/player-impact-v53), so a card needs it.

--league / --out read another league file (e.g. data/season-league-shrunk.json) and write elsewhere.
When the league carries methodology.shrinkage, 'creation' is shrunk by the same rule
(reports/ovr-shrinkage-2025-26/preregistration.md).

BACKFILL COPY (reports/ovr-metrics-backfill-2025-26): identical to reports/ovr-calibrated-2025-26/calibrate.py except
  --rapm PATH      read this RAPM csv (default reports/impact-rapm/rapm.csv) in attach_rapm; lastSeason columns optional
  --possScale X    multiply BLEND_POSS (1000) by X (half-split RAPM has ~half the possessions; main setting 0.5)
so the RAPM-blend target can be refit on one half of the games.

--target lets the 24-seed local run (resample-ranking.csv: name, healthy_minutes,
centered_contribution, standard_error) replace the saved 4-seed board.
Calibrated on one engine version: the formula inherits the simulator's blind spots
(off-ball, screen, handle and breakDbl are 70 for everyone, so they cannot be valued).
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
LEAGUE = ROOT / 'data/season-league.json'
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'heightInches', 'creation', 'pressure']
POS = ['PG', 'SG', 'SF', 'PF', 'C']
INTERACT = ['long', 'short', 'pass', 'rebound', 'help']
SCALE_MIN_MINUTES = 500
# Blend target (reports/ovr-blended-2025-26/preregistration.md): shared with blend.py so --alpha
# reproduces blend.py exactly instead of drifting from a second copy of the same logic.
BLEND_FORM, BLEND_LAM = 'position-interactions', 1.0
BLEND_POSS, BLEND_PER36 = 1000, 0.75
RAPM = ROOT / 'reports/impact-rapm/rapm.csv'  # --rapm overrides


def load(target_path):
    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            c = cards.setdefault(p['name'], {'card': p, 'MIN': 0.0})
            c['MIN'] += p['observed']['MIN']
    attach_creation(cards)
    rows = []
    for r in csv.DictReader(open(target_path, encoding='utf-8')):
        m = float(r['healthy_minutes'])
        se = float(r.get('conditional_se') or r['standard_error'])
        c = cards[r['name']]
        rows.append({'name': r['name'], 'pos': r['position'], 'card': c['card'], 'MIN': c['MIN'],
                     'y': float(r['centered_contribution']) / m * 36, 'mc': (se / m * 36) ** 2})
    return rows


def attach_creation(cards):
    received = {r['name']: float(r['creationDependence_sourceRole']) for r in csv.DictReader(open(ROOT / 'reports/player-impact-v41/2025-26-player-validation.csv', encoding='utf-8-sig'))}
    totals = {name: {'FGA': 0.0, 'MIN': 0.0, 'GP': 0} for name in cards}
    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    for team in league['teams']:
        for p in team['roster']:
            t = totals[p['name']]
            for k in ('FGA', 'MIN', 'GP'):
                t[k] += p['observed'][k]
    raw = {n: (1 - received[n]) * t['FGA'] / max(t['MIN'], 1) * 36 for n, t in totals.items()}
    if 'shrinkage' in league['methodology']:
        raw = shrink(raw, {n: t['MIN'] for n, t in totals.items()}, {n: c['card']['pos'] for n, c in cards.items()})
    pool = [raw[n] for n, t in totals.items() if t['GP'] >= 30 and t['MIN'] / t['GP'] >= 20]
    ff = {int(r['playerId']): float(r['tovNonSteal_defense']) for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/four-factors.csv', encoding='utf-8'))}
    regular = [n for n, t in totals.items() if t['GP'] >= 30 and t['MIN'] / t['GP'] >= 20]
    pressure = {n: ff.get(cards[n]['card']['playerId'], 0.0) for n in cards}
    for n, c in cards.items():
        c['card'] = {**c['card'], 'creation': to_attribute(raw[n], pool), 'pressure': to_attribute(pressure[n], [pressure[m] for m in regular])}


def shrink(raw, minutes, pos):
    """Pseudo-minutes toward the MIN-weighted position mean; k = sigma2 / tau2 by method of moments (as scripts/build_season_league.js --shrink)."""
    live = [n for n in raw if minutes[n] > 0]
    mu = {p: sum(minutes[n] * raw[n] for n in live if pos[n] == p) / sum(minutes[n] for n in live if pos[n] == p) for p in set(pos.values())}
    fit = np.array([[1 / minutes[n], (raw[n] - mu[pos[n]]) ** 2] for n in live if minutes[n] >= 50])
    sigma2 = float(np.cov(fit[:, 0], fit[:, 1], bias=True)[0, 1] / np.var(fit[:, 0]))
    tau2 = float(fit[:, 1].mean() - sigma2 * fit[:, 0].mean())
    k = min(2000, max(50, sigma2 / tau2)) if tau2 > 0 and sigma2 > 0 else 500
    SHRINKAGE['creation'] = {'pseudoMinutes': k, 'tau2': tau2, 'sigma2': sigma2, 'fitPlayers': len(fit)}
    return {n: (minutes[n] * raw[n] + k * mu[pos[n]]) / (minutes[n] + k) for n in raw}


SHRINKAGE = {}


def to_attribute(x, pool):
    """Percentile among regular players mapped PR1 = 40, PR50 = 70, PR99 = 99 (scripts/build_season_league.js)."""
    pct = 100 * (sum(v < x for v in pool) + 0.5 * sum(v == x for v in pool)) / len(pool)
    return max(40, min(99, 40 + (pct - 1) * 30 / 49 if pct < 50 else 70 + (pct - 50) * 29 / 49))


def attach_rapm(rows):
    """Attach pooled RAPM (position-centered per-36 net) for the alpha blend; see blend.py."""
    rapm = {int(r['playerId']): r for r in csv.DictReader(open(RAPM, encoding='utf-8'))}
    for r in rows:
        x = rapm.get(int(r['card']['playerId']))
        r['poss'] = float(x['pooledPoss']) if x else 0.0
        r['N'] = float(x['pooledNet']) if x else np.nan
        r['D'] = float(x['pooledD']) if x else np.nan
        r['lastN'] = float(x['lastSeasonNet']) if x and x.get('lastSeasonNet') else np.nan
    for pos in {r['pos'] for r in rows}:
        pool = [r for r in rows if r['pos'] == pos and r['poss'] >= BLEND_POSS]
        mu = sum(r['MIN'] * BLEND_PER36 * r['N'] for r in pool) / sum(r['MIN'] for r in pool)
        for r in rows:
            if r['pos'] == pos:
                r['r'] = BLEND_PER36 * r['N'] - mu if r['poss'] >= BLEND_POSS else np.nan


def blended(rows, alpha):
    """t = (1 - alpha) * sim + alpha * RAPM for players with >= BLEND_POSS pooled possessions."""
    has = np.array([r['poss'] >= BLEND_POSS for r in rows])
    y = np.array([r['y'] for r in rows]); rr = np.array([r['r'] if h else 0.0 for r, h in zip(rows, has)])
    mc = np.array([r['mc'] for r in rows])
    t = np.where(has, (1 - alpha) * y + alpha * rr, y)
    return t, np.where(has, (1 - alpha) ** 2 * mc, mc)


def design(rows, form, mean=None, sd=None):
    raw = np.array([[r['card'][a] for a in ATTRS] for r in rows], float)
    if mean is None:
        mean, sd = raw.mean(0), raw.std(0)
    z = (raw - mean) / sd
    cols = [z]
    if form == 'position-interactions':
        for p in POS[:-1]:  # C is the reference slope
            d = np.array([[1.0 if r['pos'] == p else 0.0] for r in rows])
            cols.append(d * z[:, [ATTRS.index(a) for a in INTERACT]])
    return np.hstack(cols), mean, sd


def wfit(X, y, w, lam):
    A = np.c_[np.ones(len(X)), X]
    W = w[:, None]
    pen = lam * np.eye(A.shape[1]); pen[0, 0] = 0
    return np.linalg.solve(A.T @ (W * A) + pen, A.T @ (w * y))


def weights(rows, s2):
    return np.array([1 / (r['mc'] + s2) for r in rows])


def residual_variance(rows, X, y, lam):
    s2 = 1.0
    for _ in range(30):
        w = weights(rows, s2)
        b = wfit(X, y, w, lam)
        res = y - np.c_[np.ones(len(X)), X] @ b
        mc = np.array([r['mc'] for r in rows])
        s2 = max(1e-3, float(np.sum(w * (res ** 2 - mc)) / np.sum(w)))
    return s2


def cv_score(rows, form, lam, reps=10):
    """Weighted out-of-fold R^2 against the noisy target (noise lowers the ceiling equally for all models)."""
    y = np.array([r['y'] for r in rows])
    X, _, _ = design(rows, form)
    s2 = residual_variance(rows, X, y, lam)
    w = weights(rows, s2)
    tot = np.sum(w * (y - np.average(y, weights=w)) ** 2)
    scores = []
    for rep in range(reps):
        idx = np.random.default_rng(rep).permutation(len(y)); sse = 0.0
        for k in range(5):
            te = idx[k::5]; tr = np.setdiff1d(idx, te)
            b = wfit(X[tr], y[tr], w[tr], lam)
            sse += np.sum(w[te] * (y[te] - np.c_[np.ones(len(te)), X[te]] @ b) ** 2)
        scores.append(1 - sse / tot)
    return float(np.mean(scores)), float(np.std(scores))


def ceiling(rows):
    """Share of weighted target variance that is not Monte Carlo noise."""
    y = np.array([r['y'] for r in rows]); mc = np.array([r['mc'] for r in rows])
    w = 1 / mc
    var = np.average((y - np.average(y, weights=w)) ** 2, weights=w)
    return float(1 - np.average(mc, weights=w) / var)


def configure(argv):
    global LEAGUE, OUT, RAPM, BLEND_POSS
    if '--rapm' in argv:
        RAPM = Path(argv[argv.index('--rapm') + 1]).resolve()
    if '--possScale' in argv:
        BLEND_POSS = 1000 * float(argv[argv.index('--possScale') + 1])
    if '--league' in argv:
        LEAGUE = Path(argv[argv.index('--league') + 1]).resolve()
    if '--out' in argv:
        OUT = Path(argv[argv.index('--out') + 1]).resolve(); OUT.mkdir(parents=True, exist_ok=True)


def main():
    target = ROOT / 'reports/ovr-v47-2025-26/centered-ranking.csv'
    if '--target' in sys.argv:
        target = Path(sys.argv[sys.argv.index('--target') + 1])
    alpha = float(sys.argv[sys.argv.index('--alpha') + 1]) if '--alpha' in sys.argv else 0.0
    configure(sys.argv)
    rows = load(target)
    for r in rows:
        r['simY'] = r['y']  # pure sim target, kept for display even when --alpha mutates r['y']
    if alpha > 0:
        # Reuse blend.py's fixed model form/ridge (reports/ovr-blended-2025-26/blend.py) instead of
        # re-running the form/ridge grid search on a moving target, so --alpha reproduces blend.py exactly.
        attach_rapm(rows)
        t, mc = blended(rows, alpha)
        for r, ti, mci in zip(rows, t, mc):
            r['y'] = float(ti); r['mc'] = float(mci)
        form, lam = BLEND_FORM, BLEND_LAM
        grid = {f'{form}|{lam}': cv_score(rows, form, lam)}
    else:
        grid = {}
        for form in ['linear', 'position-interactions']:
            for lam in [0, 1, 3, 10, 30, 100]:
                grid[f'{form}|{lam}'] = cv_score(rows, form, lam)
        best = max(grid, key=lambda k: grid[k][0])
        form, lam = best.split('|')[0], float(best.split('|')[1])
    y = np.array([r['y'] for r in rows])
    X, mean, sd = design(rows, form)
    s2 = residual_variance(rows, X, y, lam)
    w = weights(rows, s2)
    b = wfit(X, y, w, lam)
    # Bootstrap coefficient uncertainty (players resampled).
    rng = np.random.default_rng(20261017); boots = []
    for _ in range(500):
        i = rng.integers(0, len(y), len(y)); boots.append(wfit(X[i], y[i], w[i], lam))
    boots = np.array(boots)
    pred = np.c_[np.ones(len(X)), X] @ b
    ref = np.sort([p for p, r in zip(pred, rows) if r['MIN'] >= SCALE_MIN_MINUTES])
    q = lambda pr: ref[int(round(pr / 100 * (len(ref) - 1)))]
    p1, p50, p99 = q(1), q(50), q(99)
    ovr = np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1), 70 + 29 * (pred - p50) / (p99 - p50))
    # Per-attribute value: points per 36 minutes for +10 attribute points (main effects).
    per10 = {a: {'per36': float(b[1 + i] / sd[i] * 10), 'bootstrapSE': float(np.std(boots[:, 1 + i]) / sd[i] * 10)} for i, a in enumerate(ATTRS)}
    order = np.argsort(-pred)
    summary = {
        'target': str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target),
        'alpha': alpha, 'blendPreregistration': 'reports/ovr-blended-2025-26/preregistration.md' if alpha > 0 else None,
        'players': len(rows), 'chosen': {'form': form, 'ridge': lam},
        'cvR2': {k: {'mean': v[0], 'sd': v[1]} for k, v in grid.items()},
        'noiseCeilingR2': ceiling(rows), 'residualTrueVariancePer36': s2,
        'valuePer10AttributePoints': per10,
        'scaleAnchorsPer36': {'PR1': float(p1), 'PR50': float(p50), 'PR99': float(p99)},
        'league': str(LEAGUE.relative_to(ROOT)), 'creationShrinkage': SHRINKAGE.get('creation'),
        'formula': {'intercept': float(b[0]), 'attributeMean': dict(zip(ATTRS, map(float, mean))), 'attributeSD': dict(zip(ATTRS, map(float, sd))),
                    'coefficientsOnStandardized': list(map(float, b[1:]))},
    }
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(OUT / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'ovr', 'name', 'pos', 'MIN', 'predictedPer36', 'simulatedPer36'] + ATTRS)
        for k, i in enumerate(order):
            r = rows[i]
            wr.writerow([k + 1, round(float(ovr[i]), 1), r['name'], r['pos'], round(r['MIN']), round(float(pred[i]), 3), round(r['simY'], 3)] + [round(r['card'][a], 1) for a in ATTRS])
    print(json.dumps({k: summary[k] for k in ['chosen', 'noiseCeilingR2', 'residualTrueVariancePer36']}, indent=1))
    print('cv', {k: round(v[0], 3) for k, v in grid.items()})
    print('per10', {a: (round(v['per36'], 2), round(v['bootstrapSE'], 2)) for a, v in per10.items()})


if __name__ == '__main__':
    main()
