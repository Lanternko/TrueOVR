"""v56 防守低估修正：F1/F2/F3，疊加在 E2-λ0.4 之上（不改吃餅折扣本身）。

複製自 reports/ovr-calibrated-2025-26/calibrate.py 的核心邏輯（原檔唯讀，不修改），只新增
preregistration.md 記錄的三個固定先驗修正方向：

  F1  RAPM 混合目標的防守加權：把 attach_rapm 置中用的 pooledNet 換成
      R_beta = pooledO + (1+beta)*pooledD，beta 為固定先驗（不是自由回歸係數）。
  F2  獨立防守加分：對 pos in {PF,C} 且 pooledPoss>=5000 的球員，在 pred 上加
      gamma * max(0, BLEND_PER36*pooledD - posMeanD(pos))，posMeanD 用 BLEND_POSS=1000
      池、MIN 加權，与 attach_rapm 算 mu 的方式一致。gamma 為固定先驗。
  F3  F1 的代表 beta 換目標重新擬合之後，再疊加 F2 的代表 gamma。

用法：
  python calibrate-defense.py --direction F1 --beta 0.5 --out reports/ovr-v56-card-defense-2025-26/card-F1-beta0.5
  python calibrate-defense.py --direction F2 --gamma 1.0 --out reports/ovr-v56-card-defense-2025-26/card-F2-gamma1.0
  python calibrate-defense.py --direction F3 --beta 0.5 --gamma 1.0 --out reports/ovr-v56-card-defense-2025-26/card-F3
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LEAGUE = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
TARGET = ROOT / 'reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv'
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'heightInches', 'creation', 'pressure']
POS = ['PG', 'SG', 'SF', 'PF', 'C']
INTERACT = ['long', 'short', 'pass', 'rebound', 'help']
SCALE_MIN_MINUTES = 500
BLEND_FORM, BLEND_LAM = 'position-interactions', 1.0
BLEND_POSS, BLEND_PER36 = 1000, 0.75
BONUS_POS = {'PF', 'C'}
BONUS_MIN_POSS = 5000


def load(target_path):
    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            c = cards.setdefault(p['name'], {'card': p, 'MIN': 0.0})
            c['MIN'] += p['observed']['MIN']
    attach_creation(cards, league)
    rows = []
    for r in csv.DictReader(open(target_path, encoding='utf-8')):
        m = float(r['healthy_minutes'])
        se = float(r.get('conditional_se') or r['standard_error'])
        c = cards[r['name']]
        rows.append({'name': r['name'], 'pos': r['position'], 'card': c['card'], 'MIN': c['MIN'],
                     'y': float(r['centered_contribution']) / m * 36, 'mc': (se / m * 36) ** 2})
    return rows


def attach_creation(cards, league):
    received = {r['name']: float(r['creationDependence_sourceRole']) for r in csv.DictReader(open(ROOT / 'reports/player-impact-v41/2025-26-player-validation.csv', encoding='utf-8-sig'))}
    totals = {name: {'FGA': 0.0, 'MIN': 0.0, 'GP': 0} for name in cards}
    for team in league['teams']:
        for p in team['roster']:
            t = totals[p['name']]
            for k in ('FGA', 'MIN', 'GP'):
                t[k] += p['observed'][k]
    raw = {n: (1 - received[n]) * t['FGA'] / max(t['MIN'], 1) * 36 for n, t in totals.items()}
    pool = [raw[n] for n, t in totals.items() if t['GP'] >= 30 and t['MIN'] / t['GP'] >= 20]
    ff = {int(r['playerId']): float(r['tovNonSteal_defense']) for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/four-factors.csv', encoding='utf-8'))}
    regular = [n for n, t in totals.items() if t['GP'] >= 30 and t['MIN'] / t['GP'] >= 20]
    pressure = {n: ff.get(cards[n]['card']['playerId'], 0.0) for n in cards}
    for n, c in cards.items():
        c['card'] = {**c['card'], 'creation': to_attribute(raw[n], pool), 'pressure': to_attribute(pressure[n], [pressure[m] for m in regular])}


def to_attribute(x, pool):
    pct = 100 * (sum(v < x for v in pool) + 0.5 * sum(v == x for v in pool)) / len(pool)
    return max(40, min(99, 40 + (pct - 1) * 30 / 49 if pct < 50 else 70 + (pct - 50) * 29 / 49))


def attach_rapm(rows, beta):
    """同 calibrate.py::attach_rapm，但置中用的量是 R_beta = pooledO + (1+beta)*pooledD
    （beta=0 時等於原本的 pooledNet，因 pooledO+pooledD=pooledNet）。"""
    rapm = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}
    for r in rows:
        x = rapm.get(int(r['card']['playerId']))
        r['poss'] = float(x['pooledPoss']) if x else 0.0
        r['O'] = float(x['pooledO']) if x else np.nan
        r['D'] = float(x['pooledD']) if x else np.nan
        r['N'] = (r['O'] + (1 + beta) * r['D']) if x else np.nan
    for pos in {r['pos'] for r in rows}:
        pool = [r for r in rows if r['pos'] == pos and r['poss'] >= BLEND_POSS]
        mu = sum(r['MIN'] * BLEND_PER36 * r['N'] for r in pool) / sum(r['MIN'] for r in pool)
        for r in rows:
            if r['pos'] == pos:
                r['r'] = BLEND_PER36 * r['N'] - mu if r['poss'] >= BLEND_POSS else np.nan


def blended(rows, alpha):
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
        for p in POS[:-1]:
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
    y = np.array([r['y'] for r in rows]); mc = np.array([r['mc'] for r in rows])
    w = 1 / mc
    var = np.average((y - np.average(y, weights=w)) ** 2, weights=w)
    return float(1 - np.average(mc, weights=w) / var)


def defense_bonus(rows, gamma):
    """F2：pos in {PF,C} 且 pooledPoss>=5000 的球員，加 gamma*max(0, BLEND_PER36*D - posMeanD(pos))。
    posMeanD 用 BLEND_POSS=1000 池、MIN 加權，與 attach_rapm 算 mu 的方式一致（但用 D 不用 N）。"""
    posMeanD = {}
    for pos in {r['pos'] for r in rows}:
        pool = [r for r in rows if r['pos'] == pos and r['poss'] >= BLEND_POSS]
        num = sum(r['MIN'] * BLEND_PER36 * r['D'] for r in pool)
        den = sum(r['MIN'] for r in pool)
        posMeanD[pos] = num / den
    bonus = np.zeros(len(rows))
    for i, r in enumerate(rows):
        if r['pos'] in BONUS_POS and r['poss'] >= BONUS_MIN_POSS:
            centeredD = BLEND_PER36 * r['D'] - posMeanD[r['pos']]
            bonus[i] = gamma * max(0.0, centeredD)
    return bonus, posMeanD


def main():
    argv = sys.argv
    direction = argv[argv.index('--direction') + 1]
    assert direction in ('F1', 'F2', 'F3')
    beta = float(argv[argv.index('--beta') + 1]) if '--beta' in argv else None
    gamma = float(argv[argv.index('--gamma') + 1]) if '--gamma' in argv else None
    out = Path(argv[argv.index('--out') + 1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    alpha = 0.5

    if direction in ('F1', 'F3'):
        assert beta is not None, 'F1/F3 need --beta'
    if direction in ('F2', 'F3'):
        assert gamma is not None, 'F2/F3 need --gamma'
    effective_beta = beta if direction in ('F1', 'F3') else 0.0

    rows = load(TARGET)
    for r in rows:
        r['simY'] = r['y']
    attach_rapm(rows, effective_beta)
    t, mc = blended(rows, alpha)
    for r, ti, mci in zip(rows, t, mc):
        r['y'] = float(ti); r['mc'] = float(mci)
    form, lam = BLEND_FORM, BLEND_LAM
    grid = {f'{form}|{lam}': cv_score(rows, form, lam)}

    y = np.array([r['y'] for r in rows])
    X, mean, sd = design(rows, form)
    s2 = residual_variance(rows, X, y, lam)
    w = weights(rows, s2)
    b = wfit(X, y, w, lam)
    rng = np.random.default_rng(20261017); boots = []
    for _ in range(500):
        i = rng.integers(0, len(y), len(y)); boots.append(wfit(X[i], y[i], w[i], lam))
    boots = np.array(boots)
    pred = np.c_[np.ones(len(X)), X] @ b

    bonus = np.zeros(len(rows))
    posMeanD = None
    if direction in ('F2', 'F3'):
        bonus, posMeanD = defense_bonus(rows, gamma)
    pred = pred + bonus

    ref = np.sort([p for p, r in zip(pred, rows) if r['MIN'] >= SCALE_MIN_MINUTES])
    q = lambda pr: ref[int(round(pr / 100 * (len(ref) - 1)))]
    p1, p50, p99 = q(1), q(50), q(99)
    ovr = np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1), 70 + 29 * (pred - p50) / (p99 - p50))
    per10 = {a: {'per36': float(b[1 + i] / sd[i] * 10), 'bootstrapSE': float(np.std(boots[:, 1 + i]) / sd[i] * 10)} for i, a in enumerate(ATTRS)}
    order = np.argsort(-pred)
    summary = {
        'target': str(TARGET.relative_to(ROOT)),
        'alpha': alpha, 'blendPreregistration': 'reports/ovr-v56-card-defense-2025-26/preregistration.md',
        'direction': direction, 'beta': beta, 'gamma': gamma,
        'players': len(rows), 'chosen': {'form': form, 'ridge': lam},
        'cvR2': {k: {'mean': v[0], 'sd': v[1]} for k, v in grid.items()},
        'noiseCeilingR2': ceiling(rows), 'residualTrueVariancePer36': s2,
        'valuePer10AttributePoints': per10,
        'scaleAnchorsPer36': {'PR1': float(p1), 'PR50': float(p50), 'PR99': float(p99)},
        'league': str(LEAGUE.relative_to(ROOT)), 'creationShrinkage': None,
        'defenseBonusPosMeanD': posMeanD,
        'formula': {'intercept': float(b[0]), 'attributeMean': dict(zip(ATTRS, map(float, mean))), 'attributeSD': dict(zip(ATTRS, map(float, sd))),
                    'coefficientsOnStandardized': list(map(float, b[1:]))},
    }
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(out / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'ovr', 'name', 'pos', 'MIN', 'predictedPer36', 'simulatedPer36', 'defenseBonus'] + ATTRS)
        for k, i in enumerate(order):
            r = rows[i]
            wr.writerow([k + 1, round(float(ovr[i]), 1), r['name'], r['pos'], round(r['MIN']), round(float(pred[i]), 3), round(r['simY'], 3), round(float(bonus[i]), 3)] + [round(r['card'][a], 1) for a in ATTRS])
    print(json.dumps({'direction': direction, 'beta': beta, 'gamma': gamma, 'chosen': summary['chosen'], 'noiseCeilingR2': summary['noiseCeilingR2']}, indent=1))


if __name__ == '__main__':
    main()
