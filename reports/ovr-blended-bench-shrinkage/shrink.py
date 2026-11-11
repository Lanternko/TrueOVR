"""Output-layer reliability shrinkage of the blended card OVR toward the position prior,
for low-card-minute players (reports/ovr-blended-bench-shrinkage/preregistration.md).

Shrinks the alpha=0.5 full-data predicted-per-36 value p_i (not the blended target, not the
OVR number) toward the MIN-weighted position mean of p, by a reliability factor keyed on card
minutes m_i with a starter-protection ramp (same shape as the already-adopted v53 sim-board
shrinkage, ported from sim-minutes thresholds 10/20 to card-minutes thresholds 1000/2000).
Does not touch blend.py's or calibrate.py's fit, target, model form or ridge.

  python reports/ovr-blended-bench-shrinkage/shrink.py [--out DIR]
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'reports/ovr-calibrated-2025-26'))
sys.path.insert(0, str(ROOT / 'reports/ovr-blended-2025-26'))
import calibrate  # noqa: E402
from calibrate import load, design, wfit, SCALE_MIN_MINUTES, attach_rapm, blended, BLEND_POSS  # noqa: E402
import blend  # noqa: E402
from blend import fit_weights, spearman, FORM, LAM, EVAL_POSS, TARGET  # noqa: E402

ALPHA = 0.5  # fixed; this round only shrinks the output of the already-adopted alpha=0.5 board
POS = ['PG', 'SG', 'SF', 'PF', 'C']
LOW_MIN, HIGH_MIN = 1000, 2000          # shrinkage ramp thresholds (status_snapshot.LOW_MIN; 2000 ~= 82 games * 24 min)
PRIOR_MIN = SCALE_MIN_MINUTES           # 500: pool for the position-prior mean, same line as calibrate.py's scale anchors
KAPPA_MIN_M = 50                        # players with m >= 50 feed the method-of-moments kappa fit
KAPPA_GRID = [250, 500, 1000, 2000]     # transparency only; never used to pick the adopted kappa
KAPPA_FALLBACK = 500.0
FOCUS = ['Alex Caruso', 'Derrick White', 'Dyson Daniels', 'Herbert Jones', 'Marcus Smart',
         'Karlo Matković', 'Isaiah Stewart', 'Norchad Omier', 'Javon Small', 'Ty Jerome',
         'Dejounte Murray', 'Walker Kessler', 'Charles Bassey', 'Obi Toppin']
G1_TOL = 0.01
BOOT_SEED, BOOT_N = 20261018, 2000


def mu_by_pos(pos, m, p, min_m=PRIOR_MIN):
    return {pp: float(np.average(p[(pos == pp) & (m >= min_m)], weights=m[(pos == pp) & (m >= min_m)])) for pp in set(pos)}


def estimate_kappa(pos, m, p, mu, min_m=KAPPA_MIN_M):
    """Weighted least squares of (p-mu_pos)^2 on [1, 1/m], weight m; kappa = sigma2/tau2, clipped [250,2000]."""
    sel = m >= min_m
    mm, y = m[sel], (p[sel] - np.array([mu[pp] for pp in pos[sel]])) ** 2
    A = np.c_[np.ones(len(mm)), 1 / mm]
    tau2, sigma2 = np.linalg.solve(A.T @ (mm[:, None] * A), A.T @ (mm * y))
    tau2, sigma2 = float(tau2), float(sigma2)
    if tau2 <= 0 or sigma2 <= 0:
        return KAPPA_FALLBACK, tau2, sigma2, int(len(mm)), 'fallback', True
    k = min(2000.0, max(250.0, sigma2 / tau2))
    return float(k), tau2, sigma2, int(len(mm)), 'method-of-moments', (k in (250.0, 2000.0))


def shrink_factor(m, kappa):
    b = m / (m + kappa)
    ramp = np.clip((m - LOW_MIN) / (HIGH_MIN - LOW_MIN), 0, 1)
    return b + (1 - b) * ramp


def apply_shrink(pos, m, p, mu, kappa):
    mu_arr = np.array([mu[pp] for pp in pos])
    bp = shrink_factor(m, kappa)
    return mu_arr + bp * (p - mu_arr), bp


def to_ovr_anchors(pred, min_pool):
    ref = np.sort(pred[min_pool])
    q = lambda pr: ref[int(round(pr / 100 * (len(ref) - 1)))]
    p1, p50, p99 = q(1), q(50), q(99)
    ovr = np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1), 70 + 29 * (pred - p50) / (p99 - p50))
    return ovr, (float(p1), float(p50), float(p99))


def full_fit(rows, X):
    """Full-data alpha=0.5 fit, identical to blend.py's full[chosen] for chosen=0.5."""
    t, mc = blended(rows, ALPHA)
    w = fit_weights(X, t, mc)
    b = wfit(X, t, w, LAM)
    return np.c_[np.ones(len(X)), X] @ b


def oof_pair(rows, X, pos, m, rep, kappa_override):
    """Out-of-fold baseline (pred) and shrunk (phat) predictions for one repeat; shrinkage params
    (mu_pos, kappa unless overridden) are estimated from training players' in-fold predictions only."""
    t, mc = blended(rows, ALPHA)
    pred = np.zeros(len(rows)); phat = np.zeros(len(rows))
    idx = np.random.default_rng(rep).permutation(len(rows))
    for k in range(5):
        te = idx[k::5]; tr = np.setdiff1d(idx, te)
        w = fit_weights(X[tr], t[tr], mc[tr])
        b = wfit(X[tr], t[tr], w, LAM)
        pred_tr = np.c_[np.ones(len(tr)), X[tr]] @ b
        pred_te = np.c_[np.ones(len(te)), X[te]] @ b
        pred[te] = pred_te
        mu_tr = mu_by_pos(pos[tr], m[tr], pred_tr)
        if kappa_override is None:
            kappa_tr = estimate_kappa(pos[tr], m[tr], pred_tr, mu_tr)[0]
        else:
            kappa_tr = kappa_override
        mu_te = np.array([mu_tr[pp] for pp in pos[te]])
        phat[te] = mu_te + shrink_factor(m[te], kappa_tr) * (pred_te - mu_te)
    return pred, phat


def bootstrap_ci(values, seed=BOOT_SEED, n=BOOT_N):
    rng = np.random.default_rng(seed)
    v = np.asarray(values)
    draws = [float(np.mean(v[rng.integers(0, len(v), len(v))])) for _ in range(n)]
    return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]


def pipeline(rows, X, pos, m, poss, N, D, lastN, ev, kappa_override):
    """Run the full held-out + full-board protocol once, fixed or auto-estimated kappa."""
    pred_reps, phat_reps = [], []
    for rep in range(10):
        pr, ph = oof_pair(rows, X, pos, m, rep, kappa_override)
        pred_reps.append(pr); phat_reps.append(ph)
    pred_reps, phat_reps = np.array(pred_reps), np.array(phat_reps)
    mean_pred, mean_phat = pred_reps.mean(0), phat_reps.mean(0)

    g1 = {
        'rhoNetBaseline': float(np.mean([spearman(pr[ev], N) for pr in pred_reps])),
        'rhoNetShrunk': float(np.mean([spearman(ph[ev], N) for ph in phat_reps])),
        'rhoDefenseBaseline': float(np.mean([spearman(pr[ev], D) for pr in pred_reps])),
        'rhoDefenseShrunk': float(np.mean([spearman(ph[ev], D) for ph in phat_reps])),
    }
    g1['passNet'] = g1['rhoNetShrunk'] >= g1['rhoNetBaseline'] - G1_TOL
    g1['passDefense'] = g1['rhoDefenseShrunk'] >= g1['rhoDefenseBaseline'] - G1_TOL
    g1['pass'] = g1['passNet'] and g1['passDefense']
    # Paired bootstrap of the rho difference (shrunk - baseline), on the 10-repeat-averaged OOF
    # predictions, players resampled with replacement (same recipe/seed as blend.py's bootstrapGain95).
    p0, p1 = mean_pred[ev], mean_phat[ev]
    rng_g1 = np.random.default_rng(BOOT_SEED)
    net_diffs, def_diffs = [], []
    for _ in range(BOOT_N):
        bi = rng_g1.integers(0, len(N), len(N))
        net_diffs.append(spearman(p1[bi], N[bi]) - spearman(p0[bi], N[bi]))
        def_diffs.append(spearman(p1[bi], D[bi]) - spearman(p0[bi], D[bi]))
    g1['bootstrapRhoDiff95'] = {
        'net': [float(np.percentile(net_diffs, 2.5)), float(np.percentile(net_diffs, 97.5))],
        'defense': [float(np.percentile(def_diffs, 2.5)), float(np.percentile(def_diffs, 97.5))],
    }

    bench = (m < LOW_MIN) & (poss >= BLEND_POSS)
    r_bench = np.array([row['r'] for row, b in zip(rows, bench) if b])
    base_bench = mean_pred[bench]; shr_bench = mean_phat[bench]
    l_base_i = (base_bench - r_bench) ** 2; l_shr_i = (shr_bench - r_bench) ** 2
    gain_i = l_base_i - l_shr_i
    gain_ci = bootstrap_ci(gain_i)
    g2 = {'benchPlayers': int(bench.sum()), 'meanLBaseline': float(l_base_i.mean()), 'meanLShrunk': float(l_shr_i.mean()),
          'meanGain': float(gain_i.mean()), 'gainBootstrapCI95': gain_ci,
          'pass': bool(l_shr_i.mean() < l_base_i.mean() and gain_ci[0] > 0)}

    pred_full = full_fit(rows, X)
    if kappa_override is None:
        mu_full = mu_by_pos(pos, m, pred_full)
        kappa_full, tau2_full, sigma2_full, n_fit_full, source_full, clipped_full = estimate_kappa(pos, m, pred_full, mu_full)
    else:
        mu_full = mu_by_pos(pos, m, pred_full)
        kappa_full, tau2_full, sigma2_full, n_fit_full, source_full, clipped_full = kappa_override, None, None, None, 'grid-fixed', False
    phat_full, bp_full = apply_shrink(pos, m, pred_full, mu_full, kappa_full)

    order_base = np.argsort(-pred_full); order_shr = np.argsort(-phat_full)
    top20_base, top20_shr = order_base[:20], order_shr[:20]
    top50_base, top50_shr = set(order_base[:50].tolist()), set(order_shr[:50].tolist())
    g3 = {'baselineTop20LowMin': int((m[top20_base] < LOW_MIN).sum()), 'shrunkTop20LowMin': int((m[top20_shr] < LOW_MIN).sum()),
          'baselineTop50LowMin1000': int((m[order_base[:50]] < LOW_MIN).sum()), 'baselineTop50LowMin500': int((m[order_base[:50]] < PRIOR_MIN).sum())}
    g3['pass'] = g3['shrunkTop20LowMin'] <= 1

    starters = m >= HIGH_MIN
    g4a_rho = spearman(pred_full[starters], phat_full[starters]) if starters.sum() > 1 else 1.0
    starters_in_base50 = set(i for i in top50_base if starters[i])
    dropped = starters_in_base50 - top50_shr
    g4 = {'starters': int(starters.sum()),
          'g4aSpearmanAmongStarters': float(g4a_rho), 'g4aPass': bool(round(g4a_rho, 6) == 1.0),
          'g4bDroppedFromTop50': sorted(rows[i]['name'] for i in dropped), 'g4bPass': len(dropped) == 0,
          'baselineTop20Starters': int(starters[top20_base].sum()), 'shrunkTop20Starters': int(starters[top20_shr].sum())}
    g4['g4cPass'] = g4['shrunkTop20Starters'] >= g4['baselineTop20Starters']

    return {
        'kappa': kappa_full, 'kappaSource': source_full, 'kappaClippedToBound': clipped_full,
        'tau2': tau2_full, 'sigma2': sigma2_full, 'kappaFitPlayers': n_fit_full,
        'g1': g1, 'g2': g2, 'g3': g3, 'g4': g4,
        'adopt': bool(g1['pass'] and g2['pass'] and g3['pass'] and g4['g4aPass'] and g4['g4bPass'] and g4['g4cPass']),
        '_predFull': pred_full, '_phatFull': phat_full, '_muFull': mu_full, '_bpFull': bp_full,
        '_meanPred': mean_pred, '_meanPhat': mean_phat,
    }


def main():
    global OUT
    if '--out' in sys.argv:
        OUT = Path(sys.argv[sys.argv.index('--out') + 1]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
    rows = load(TARGET); attach_rapm(rows)
    X, _, sd = design(rows, FORM)
    pos = np.array([r['pos'] for r in rows]); m = np.array([r['MIN'] for r in rows]); poss = np.array([r['poss'] for r in rows])
    ev = poss >= EVAL_POSS
    N = np.array([r['N'] for r in rows])[ev]; D = np.array([r['D'] for r in rows])[ev]
    lastN = np.array([r['lastN'] for r in rows])[ev]

    chosen = pipeline(rows, X, pos, m, poss, N, D, lastN, ev, None)
    grid = {k: pipeline(rows, X, pos, m, poss, N, D, lastN, ev, float(k)) for k in KAPPA_GRID}

    pred_full, phat_full, mu_full, bp_full = chosen['_predFull'], chosen['_phatFull'], chosen['_muFull'], chosen['_bpFull']
    min_pool = m >= PRIOR_MIN
    ovr_base, anchors_base = to_ovr_anchors(pred_full, min_pool)
    ovr_shr, anchors_shr = to_ovr_anchors(phat_full, min_pool)

    bins = [(0, 250), (250, 500), (500, 1000), (1000, 2000), (2000, np.inf)]
    median_bp = {f'{lo}-{hi if hi != np.inf else "inf"}': (float(np.median(bp_full[(m >= lo) & (m < hi)])) if ((m >= lo) & (m < hi)).any() else None) for lo, hi in bins}

    risk_mask = (m < PRIOR_MIN) & (ovr_shr - ovr_base > 5)
    risk_list = sorted([{'name': rows[i]['name'], 'MIN': int(m[i]), 'ovrBaseline': round(float(ovr_base[i]), 1), 'ovrShrunk': round(float(ovr_shr[i]), 1)}
                         for i in np.where(risk_mask)[0]], key=lambda d: -(d['ovrShrunk'] - d['ovrBaseline']))

    order_shr = np.argsort(-phat_full); rank_shr = {int(i): k + 1 for k, i in enumerate(order_shr)}
    order_base = np.argsort(-pred_full); rank_base = {int(i): k + 1 for k, i in enumerate(order_base)}
    name_to_i = {r['name']: i for i, r in enumerate(rows)}
    focus = {}
    for n in FOCUS:
        i = name_to_i.get(n)
        if i is None:
            continue
        focus[n] = {'MIN': int(m[i]), 'rankBaseline': rank_base[i], 'rankShrunk': rank_shr[i],
                    'ovrBaseline': round(float(ovr_base[i]), 1), 'ovrShrunk': round(float(ovr_shr[i]), 1),
                    'shrinkFactor': round(float(bp_full[i]), 3)}

    y_sim = np.array([r['y'] for r in rows])
    s2_0 = calibrate.residual_variance(rows, X, y_sim, LAM)
    w0 = calibrate.weights(rows, s2_0)
    tot0 = np.sum(w0 * (y_sim - np.average(y_sim, weights=w0)) ** 2)
    sim_r2 = {'baseline': float(1 - np.sum(w0 * (y_sim - chosen['_meanPred']) ** 2) / tot0),
              'shrunk': float(1 - np.sum(w0 * (y_sim - chosen['_meanPhat']) ** 2) / tot0)}

    summary = {
        'preregistration': 'preregistration.md', 'alpha': ALPHA, 'form': FORM, 'ridge': LAM,
        'players': len(rows), 'lowMinThreshold': LOW_MIN, 'highMinThreshold': HIGH_MIN, 'priorPoolMin': PRIOR_MIN,
        'kappa': chosen['kappa'], 'kappaSource': chosen['kappaSource'], 'kappaClippedToBound': chosen['kappaClippedToBound'],
        'kappaTau2': chosen['tau2'], 'kappaSigma2': chosen['sigma2'], 'kappaFitPlayers': chosen['kappaFitPlayers'],
        'kappaGridTransparencyOnly': {str(k): {'gates': {g: v[g]['pass'] if g in ('g1', 'g2', 'g3') else None for g in ('g1', 'g2', 'g3')},
                                                'g4': {k2: v['g4'][k2] for k2 in ('g4aPass', 'g4bPass', 'g4cPass')}, 'adopt': v['adopt']}
                                      for k, v in grid.items()},
        'gates': {'G1': chosen['g1'], 'G2': chosen['g2'], 'G3': chosen['g3'], 'G4': chosen['g4']},
        'adopt': chosen['adopt'],
        'simR2HeldOut': sim_r2,
        'medianShrinkFactorByMinuteBand': median_bp,
        'scaleAnchorsPer36': {'baseline': {'PR1': anchors_base[0], 'PR50': anchors_base[1], 'PR99': anchors_base[2]},
                               'shrunk': {'PR1': anchors_shr[0], 'PR50': anchors_shr[1], 'PR99': anchors_shr[2]}},
        'belowPriorOvrUp5Risk': {'count': len(risk_list), 'players': risk_list},
        'focusPlayers': focus,
    }
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    with open(OUT / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'rawRank', 'name', 'pos', 'MIN', 'pooledPoss', 'predictedPer36Baseline', 'predictedPer36Shrunk',
                     'ovrBaseline', 'ovrShrunk', 'shrinkFactor', 'rapmPer36Centered'])
        for k, i in enumerate(order_shr):
            r = rows[i]
            wr.writerow([k + 1, rank_base[i], r['name'], r['pos'], int(m[i]), round(poss[i]),
                         round(float(pred_full[i]), 3), round(float(phat_full[i]), 3),
                         round(float(ovr_base[i]), 1), round(float(ovr_shr[i]), 1), round(float(bp_full[i]), 3),
                         '' if np.isnan(r['r']) else round(float(r['r']), 3)])

    print(json.dumps({k: summary[k] for k in ['kappa', 'kappaSource', 'kappaClippedToBound', 'adopt']}, ensure_ascii=False, indent=1))
    print('gates', {g: summary['gates'][g]['pass'] if g != 'G4' else {k2: summary['gates']['G4'][k2] for k2 in ('g4aPass', 'g4bPass', 'g4cPass')} for g in ('G1', 'G2', 'G3', 'G4')})


if __name__ == '__main__':
    main()
