"""v57 側翼/後衛防守低估 + 前十長人修正：G1~G4，疊加在 E2-λ0.4 之上（原封不動抄
reports/ovr-v56-card-defense-2025-26/calibrate-defense.py 的核心迴歸管線，該檔唯讀不改）。

四個方向（定義見 reports/ovr-v57-card-2025-26/preregistration.md 第二節，全部是固定先驗，
不自由估計係數、不改回歸目標、不改設計矩陣、不改 ridge；pred0 與 E2-λ0.4 的 predictedPer36
完全相同，修正項全部是 pred 的後處理，發生在 percentile 映射到 OVR 之前）：

  G1  bonus(i) = gamma * max(0, centeredD(i))                    若 pooledPoss(i) >= 5000（任何位置）
  G2  bonus(i) = gamma * max(0, centeredD(i)) * w(i)              w = taper(PR(pred0), 90, 96)
  G3  bonus 同 G2 ＋ align(i) = delta * (r(i) - pred0(i))          若 pooledPoss(i) >= 5000
  G4  pred(i) = pred0(i) + delta * (r(i) - pred0(i))               若 pooledPoss(i) >= 5000（無 bonus）

--restrictPos 只用於 sanity check（把 G1 的加分對象限定在指定位置，重現 F2-γ0.5），
不是候選跑法的一部分，候選跑法一律不帶這個參數（即套用到任何位置）。

用法：
  python calibrate-wing.py --direction G1 --gamma 0.5 --out reports/ovr-v57-card-2025-26/card-G1-gamma0.5
  python calibrate-wing.py --direction G2 --gamma 0.75 --out reports/ovr-v57-card-2025-26/card-G2-gamma0.75
  python calibrate-wing.py --direction G3 --gamma 0.75 --delta 0.25 --out reports/ovr-v57-card-2025-26/card-G3-delta0.25
  python calibrate-wing.py --direction G4 --delta 0.4 --out reports/ovr-v57-card-2025-26/card-G4-delta0.4
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
BONUS_MIN_POSS = 5000
PR_LO, PR_HI = 90.0, 96.0


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
    """同 calibrate-defense.py::attach_rapm；v57 全部方向固定 beta=0（等於 calibrate.py 原本的
    pooledNet 置中），因為 v57 不碰 F1 的 RAPM 混合加權，只在 pred 後處理階段使用 r(i)。"""
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


def pos_mean_d(rows):
    """posMeanD(pos)：MIN 加權平均 0.75*pooledD，池 = 同 pos 且 pooledPoss>=1000。與
    calibrate-defense.py::defense_bonus 的 posMeanD 算法一致（只是獨立抽出，因為 G 系列
    不限定 BONUS_POS）。"""
    out = {}
    for pos in {r['pos'] for r in rows}:
        pool = [r for r in rows if r['pos'] == pos and r['poss'] >= BLEND_POSS]
        num = sum(r['MIN'] * BLEND_PER36 * r['D'] for r in pool)
        den = sum(r['MIN'] for r in pool)
        out[pos] = num / den
    return out


def percentile_rank(x, ref_pool_sorted):
    """同 reports/ovr-v57-card-2025-26/diagnose.py::pct_of：100*below/(n-1)，ref_pool 已排序。"""
    n = len(ref_pool_sorted)
    below = sum(1 for v in ref_pool_sorted if v < x)
    return 100.0 * below / (n - 1)


def taper_w(pr):
    return min(1.0, max(0.0, (PR_HI - pr) / (PR_HI - PR_LO)))


def main():
    argv = sys.argv
    direction = argv[argv.index('--direction') + 1]
    assert direction in ('G1', 'G2', 'G3', 'G4')
    gamma = float(argv[argv.index('--gamma') + 1]) if '--gamma' in argv else None
    delta = float(argv[argv.index('--delta') + 1]) if '--delta' in argv else None
    restrict_pos = argv[argv.index('--restrictPos') + 1].split(',') if '--restrictPos' in argv else None
    out = Path(argv[argv.index('--out') + 1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    alpha = 0.5

    if direction in ('G1', 'G2', 'G3'):
        assert gamma is not None, f'{direction} needs --gamma'
    if direction in ('G3', 'G4'):
        assert delta is not None, f'{direction} needs --delta'

    rows = load(TARGET)
    for r in rows:
        r['simY'] = r['y']
    attach_rapm(rows, 0.0)
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
    pred0 = np.c_[np.ones(len(X)), X] @ b

    posMeanD = pos_mean_d(rows)
    centeredD = np.array([BLEND_PER36 * r['D'] - posMeanD[r['pos']] if r['poss'] >= BLEND_POSS else np.nan for r in rows])
    r_target = np.array([r.get('r', np.nan) for r in rows])
    poss = np.array([r['poss'] for r in rows])

    pr_pool = sorted(pred0[i] for i, r in enumerate(rows) if r['MIN'] >= SCALE_MIN_MINUTES)
    pr = np.array([percentile_rank(p, pr_pool) for p in pred0])

    eligible = poss >= BONUS_MIN_POSS
    if restrict_pos is not None:
        eligible = eligible & np.array([r['pos'] in restrict_pos for r in rows])

    bonus = np.zeros(len(rows))
    align = np.zeros(len(rows))
    wgt = np.ones(len(rows))

    if direction in ('G1', 'G2', 'G3'):
        raw_bonus = np.where(eligible & ~np.isnan(centeredD), gamma * np.maximum(0.0, np.nan_to_num(centeredD, nan=0.0)), 0.0)
        if direction in ('G2', 'G3'):
            wgt = np.array([taper_w(p) for p in pr])
            bonus = raw_bonus * wgt
        else:
            bonus = raw_bonus

    if direction in ('G3', 'G4'):
        align_eligible = poss >= BONUS_MIN_POSS
        align = np.where(align_eligible & ~np.isnan(r_target), delta * (np.nan_to_num(r_target, nan=0.0) - pred0), 0.0)

    pred = pred0 + bonus + align

    ref = np.sort([p for p, r in zip(pred, rows) if r['MIN'] >= SCALE_MIN_MINUTES])
    q = lambda prc: ref[int(round(prc / 100 * (len(ref) - 1)))]
    p1, p50, p99 = q(1), q(50), q(99)
    ovr = np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1), 70 + 29 * (pred - p50) / (p99 - p50))
    per10 = {a: {'per36': float(b[1 + i] / sd[i] * 10), 'bootstrapSE': float(np.std(boots[:, 1 + i]) / sd[i] * 10)} for i, a in enumerate(ATTRS)}
    order = np.argsort(-pred)
    summary = {
        'target': str(TARGET.relative_to(ROOT)),
        'alpha': alpha, 'blendPreregistration': 'reports/ovr-v57-card-2025-26/preregistration.md',
        'direction': direction, 'gamma': gamma, 'delta': delta,
        'restrictPos': restrict_pos,
        'prLo': PR_LO, 'prHi': PR_HI,
        'players': len(rows), 'chosen': {'form': form, 'ridge': lam},
        'cvR2': {k: {'mean': v[0], 'sd': v[1]} for k, v in grid.items()},
        'noiseCeilingR2': ceiling(rows), 'residualTrueVariancePer36': s2,
        'valuePer10AttributePoints': per10,
        'scaleAnchorsPer36': {'PR1': float(p1), 'PR50': float(p50), 'PR99': float(p99)},
        'league': str(LEAGUE.relative_to(ROOT)), 'creationShrinkage': None,
        'defenseBonusPosMeanD': posMeanD,
        'prRefPoolSize': len(pr_pool),
        'formula': {'intercept': float(b[0]), 'attributeMean': dict(zip(ATTRS, map(float, mean))), 'attributeSD': dict(zip(ATTRS, map(float, sd))),
                    'coefficientsOnStandardized': list(map(float, b[1:]))},
    }
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(out / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'ovr', 'name', 'pos', 'MIN', 'predictedPer36', 'simulatedPer36', 'defenseBonus', 'align', 'pred0', 'pr'] + ATTRS)
        for k, i in enumerate(order):
            r = rows[i]
            wr.writerow([k + 1, round(float(ovr[i]), 1), r['name'], r['pos'], round(r['MIN']),
                         round(float(pred[i]), 3), round(r['simY'], 3), round(float(bonus[i]), 3),
                         round(float(align[i]), 3), round(float(pred0[i]), 3), round(float(pr[i]), 2)]
                        + [round(r['card'][a], 1) for a in ATTRS])
    print(json.dumps({'direction': direction, 'gamma': gamma, 'delta': delta, 'restrictPos': restrict_pos,
                       'chosen': summary['chosen'], 'noiseCeilingR2': summary['noiseCeilingR2']}, indent=1))


if __name__ == '__main__':
    main()
