"""E-107（preregistration.md 凍結）：由 reports/card-0.2.5+E106-defense-bonus-monotone/calibrate-wing.py 複製，
  從 reports/card-0.2.5+E101-crossera/calibrate-wing.py 原樣搬入 E-090 的 --tailSource（TAIL_SOURCE、TAIL_ATTRS、attach_tail、load() 呼叫、argv 解析）。不帶時與 E-106 逐位元相同。
E-106（preregistration.md 凍結）：由 reports/card-0.2.5+E104-defense-pergame-decay/calibrate-wing.py 複製，--bonusShape 加 none：
  bonus = raw_bonus（回合門檻內 max(0, centeredD)），不乘 taper、不套 T96；RAPM 名次封頂（H1）照舊。不帶 none 時逐位元不變。
E-104（preregistration.md 凍結）：由 reports/card-0.2.5+E094-defense-ceiling/calibrate-wing.py 複製，只加 --defPossFactor X
  （--defWindow season 時回合門檻 BLEND_POSS、BONUS_MIN_POSS 改乘 X；預設 0.25 = E-094 原式）。其餘一字不改。
E-094（preregistration.md 凍結）：由 reports/card-0.2.0+E071-pressure/calibrate-wing.py 複製，加兩個開關，預設逐位元不變：
  --bonusShape taper|ceiling   ceiling：bonus = min(max(0, centeredD), max(0, T96 − pred0))，T96 = 縮放池 pred0 中 PR ≥ 96 的最小值
  --defWindow pooled|season --defRapm CSV   season：defenseBonus 的 centeredD／posMeanD 改讀單季 D（rapm.csv 的 lastSeasonD／lastSeasonPoss，
                               或 rapm1-A/B 的 D／poss），回合門檻 BONUS_MIN_POSS、BLEND_POSS 乘 1/4；align、封頂、回歸目標仍讀 --rapm
E-071 複本（card 0.2.0+E071）：card 0.1.2+E064 的 calibrate-wing.py 加兩組預設關閉的開關，其餘一字不改：
  --pressure old|force|none   pressure 屬性來源：old＝four-factors tovNonSteal_defense（現行，預設）、force＝--pressureSource 的 force 欄、none＝拿掉 pressure（P0）
  --pressureSource CSV        playerId,force,negzpf（build_force.py 輸出）；force 欄經 to_attribute（同一個池）轉成 pressure
  --foulDisc                  新增屬性 foulDisc＝to_attribute(negzpf)，放在 pressure 之後（P2）；需要 --pressureSource
以下為 E-064 複本說明：
E-064 複本（card 0.1.2+E064）：card 0.1.1+E060 的 calibrate-wing.py（= card 0.1.2 管線）加三組預設關閉的開關，其餘演算法一字不改：
  --rapm PATH / --possScale X   與 reports/ovr-v58-holdout-2025-26/calibrate-wing.py 相同（RAPM 分半樣本外用）；預設全量 RAPM、不縮放
  --perGame                     在 L421 映射之前取 pred，另外輸出 pred.csv、pergame-main.csv（g = pred*MPG/36）、pergame-repl.csv（(pred-PR10)*MPG/36）；
                                不帶時一個檔案都不多寫；帶了也不改 ranking.csv／summary.json（每 36 版原封不動）
  --mpgSource CSV               playerId,mpg（半份資料用）；預設 = 季總 MIN / GP（league 檔 observed）
預註冊：reports/card-0.1.2+E064-pergame/preregistration.md（sha256 見同目錄）。以下為 E-058 說明：
E-058 複本：v61 calibrate-wing.py 加 --defSource <csv>（playerId,new_onBall,new_help）覆蓋 onBall／help；不帶時與 v61 完全相同。"""
"""v61 卡片產生器（v60 `calibrate-wing.py` 的複本，只加 --attrSource）。以下為 v60 原說明：

v60 卡片產生器：v58 H1-m0 流程原封不動，只把 drive 拆成 foulDraw（舊 drive）與新 drive。

回歸管線、目標、ridge、alpha、H1 cap（γ=1.0、δ=0.25、margin=0）與 v58 `calibrate-wing.py` 完全相同（本檔是它的複本）。
唯一差異：卡片屬性 drive 改讀 `drive-attributes.csv`（build_drive.py 由前 41 場 PBP 算出的新 drive），
並新增屬性 foulDraw（= v58 的舊 drive，FTA/FGA 百分位）。兩者都進設計矩陣（ATTRS 在 drive 之後插入 foulDraw）。

--driveMode old：不拆（ATTRS 同 v58、drive 為舊值），用來重現 v58 H1-m0 做 sanity check（應 byte-identical）。

用法（repo 根目錄）：
  python reports/ovr-v60-drive-split-2025-26/calibrate-wing.py --direction H1 --capMargin 0 --out reports/ovr-v60-drive-split-2025-26
  python reports/ovr-v60-drive-split-2025-26/calibrate-wing.py --direction H1 --capMargin 0 --driveMode old --out reports/ovr-v60-drive-split-2025-26/sanity-v58-repro
  （敏感度）--driveColumn drive_volOnly 等：改用 drive-attributes.csv 的其他欄當新 drive，輸出到 sensitivity/<name>/
"""
import csv, json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LEAGUE = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
TARGET = ROOT / 'reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv'
DRIVE = ROOT / 'reports/ovr-v60-drive-split-2025-26/drive-attributes.csv'   # v61：沿用 v60 的 drive 原檔（舊 drive 值與 foulDraw 的來源）
DEF_SOURCE = None   # E-058
PRESSURE_MODE = 'old'   # E-071
PRESSURE_SOURCE = None   # E-071
FOULDISC = False   # E-071
TAIL_SOURCE = None   # E-090
TAIL_ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'creation', 'pressure']
ATTR_SOURCE = None   # v61：--attrSource <csv> → 用 attributes-new.csv 的 new_* 欄覆蓋 8 個屬性（long 不動）
OVERRIDE = ['rebound', 'pass', 'tovSkill', 'foulDraw', 'drive', 'mid', 'short', 'ft']
DRIVE_COLUMN = 'drive'
DRIVE_MODE = 'split'
RAPM = ROOT / 'reports/impact-rapm/rapm.csv'
MERGED = ROOT / 'reports/ovr-v55-2k27-compare/merged.csv'
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'heightInches', 'creation', 'pressure']
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
    if DRIVE_MODE == 'split':
        attach_drive_split(cards)
    if ATTR_SOURCE is not None:
        attach_new_attrs(cards)
    if DEF_SOURCE is not None:
        attach_def(cards)
    if TAIL_SOURCE is not None:
        attach_tail(cards)
    rows = []
    for r in csv.DictReader(open(target_path, encoding='utf-8')):
        m = float(r['healthy_minutes'])
        se = float(r.get('conditional_se') or r['standard_error'])
        c = cards[r['name']]
        rows.append({'name': r['name'], 'pos': r['position'], 'card': c['card'], 'MIN': c['MIN'],
                     'y': float(r['centered_contribution']) / m * 36, 'mc': (se / m * 36) ** 2})
    return rows


def attach_tail(cards):
    """E-090：用 --tailSource 的值覆蓋 13 個屬性（每個卡片球員都要有一列）。"""
    src = {int(r['playerId']): r for r in csv.DictReader(open(TAIL_SOURCE, encoding='utf-8'))}
    for c in cards.values():
        r = src[int(c['card']['playerId'])]
        c['card'] = {**c['card'], **{a: float(r[a]) for a in TAIL_ATTRS}}


def attach_drive_split(cards):
    """foulDraw = v58 舊 drive（原封不動）；drive = drive-attributes.csv 的新值（沒有前 41 場資料者該檔已填中性 70）。"""
    new = {int(r['playerId']): float(r[DRIVE_COLUMN]) for r in csv.DictReader(open(DRIVE, encoding='utf-8'))}
    for c in cards.values():
        card = c['card']
        c['card'] = {**card, 'foulDraw': card['drive'], 'drive': new[card['playerId']]}


def attach_def(cards):
    new = {int(r['playerId']): r for r in csv.DictReader(open(DEF_SOURCE, encoding='utf-8'))}
    for c in cards.values():
        r = new[c['card']['playerId']]
        c['card'] = {**c['card'], 'onBall': float(r['new_onBall']), 'help': float(r['new_help'])}


def attach_new_attrs(cards):
    """v61：以 attributes-new.csv 的 new_* 覆蓋 v60 的 8 個屬性值；其餘（含 long）原封不動。"""
    new = {int(r['playerId']): r for r in csv.DictReader(open(ATTR_SOURCE, encoding='utf-8'))}
    for c in cards.values():
        r = new[c['card']['playerId']]
        c['card'] = {**c['card'], **{a: float(r['new_' + a]) for a in OVERRIDE}}


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
    if PRESSURE_MODE == 'force' or FOULDISC:
        src = {int(r['playerId']): r for r in csv.DictReader(open(PRESSURE_SOURCE, encoding='utf-8'))}
        for key, col, mode in (('pressure', 'force', PRESSURE_MODE == 'force'), ('foulDisc', 'negzpf', FOULDISC)):
            if not mode:
                continue
            val = {n: float(src[cards[n]['card']['playerId']][col]) for n in cards}
            for n, c in cards.items():
                c['card'] = {**c['card'], key: to_attribute(val[n], [val[m] for m in regular])}


def to_attribute(x, pool):
    pct = 100 * (sum(v < x for v in pool) + 0.5 * sum(v == x for v in pool)) / len(pool)
    return max(40, min(99, 40 + (pct - 1) * 30 / 49 if pct < 50 else 70 + (pct - 50) * 29 / 49))


def attach_rapm(rows, beta):
    """同 calibrate-defense.py::attach_rapm；v57 全部方向固定 beta=0（等於 calibrate.py 原本的
    pooledNet 置中），因為 v57 不碰 F1 的 RAPM 混合加權，只在 pred 後處理階段使用 r(i)。"""
    rapm = {int(r['playerId']): r for r in csv.DictReader(open(RAPM, encoding='utf-8'))}
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


def attach_external_ranks(rows):
    """RAPM pooledNet 名次與 2K27 名次。RAPM 去重方式與 v57 evaluate.mjs 相同：
    以 name 為 key、同名（含空 name）最後一列覆蓋；池 = pooledPoss >= 5000。"""
    rapm = {}
    for r in csv.DictReader(open(RAPM, encoding='utf-8')):
        rapm[r['name']] = r
    pool = [r for r in rapm.values() if float(r['pooledPoss']) >= BONUS_MIN_POSS]
    net = {r['name']: i + 1 for i, r in enumerate(sorted(pool, key=lambda x: -float(x['pooledNet'])))}
    merged = {}
    for r in csv.DictReader(open(MERGED, encoding='utf-8-sig')):
        merged[r['name']] = r
    for r in rows:
        r['rapmRank'] = net.get(r['name'])
        m = merged.get(r['name'])
        r['rank2k'] = float(m['rank2k']) if m and m['rank2k'] else None


def cap_allowed(rows, margin, ref_mode):
    """allowed(i) = max(1, ceil(ref(i) - margin))；ref_mode='rapm' 或 'consensus'。"""
    allowed = []
    for r in rows:
        if r['poss'] < BONUS_MIN_POSS:
            allowed.append(None)
            continue
        rr, kk = r['rapmRank'], r['rank2k']
        if ref_mode == 'rapm':
            ref = rr
        else:
            vals = [v for v in (rr, kk) if v is not None]
            ref = min(vals) if vals else None
        allowed.append(max(1, int(math.ceil(ref - margin))) if ref is not None else None)
    return allowed


def pred_threshold(pred):
    """回傳 T(a)：候選 pred 分布第 a 高值再減 1e-12（確保被 cap 者嚴格排在後面）。"""
    s = np.sort(pred)[::-1]

    def T(a):
        return float(s[min(max(int(a), 1), len(s)) - 1]) - 1e-12

    return T


def cap_total_lift(pred, pred0, lift, allowed):
    """H1/H3：只砍向上 lift，pred = min(pred, max(pred0, T(allowed)))。固定點迭代。"""
    pred = pred.copy()
    for it in range(100):
        T = pred_threshold(pred)
        changed = 0.0
        for i, a in enumerate(allowed):
            if a is None or lift[i] <= 0:
                continue
            v = min(pred[i], max(pred0[i], T(a)))
            changed = max(changed, pred[i] - v)
            pred[i] = v
        if changed < 1e-10:
            return pred, it + 1
    raise RuntimeError('H1/H3 cap did not converge in 100 iterations')


def cap_bonus_only(pred, pred0, bonus, align, allowed):
    """H2：只砍 defenseBonus，pred = pred0 + bonus' + align。固定點迭代。"""
    pred = pred.copy()
    bonus2 = bonus.copy()
    for it in range(100):
        T = pred_threshold(pred)
        changed = 0.0
        for i, a in enumerate(allowed):
            if a is None or bonus[i] <= 0:
                continue
            nb = min(bonus[i], max(0.0, T(a) - pred0[i]))
            v = pred0[i] + nb + align[i]
            changed = max(changed, abs(pred[i] - v))
            bonus2[i] = nb
            pred[i] = v
        if changed < 1e-10:
            return pred, bonus2, it + 1
    raise RuntimeError('H2 cap did not converge in 100 iterations')


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


def attach_def_window(rows, path):
    """E-094 season：單季 D 另存 r['Dw']／r['possW']，不動 r['D']／r['poss']（回歸目標、align、封頂仍用合併值）。"""
    src = {int(x['playerId']): x for x in csv.DictReader(open(path, encoding='utf-8'))}
    for r in rows:
        x = src.get(int(r['card']['playerId']))
        if x is None:
            r['Dw'], r['possW'] = np.nan, 0.0
        elif 'lastSeasonD' in x:
            r['Dw'], r['possW'] = float(x['lastSeasonD']), float(x['lastSeasonPoss'])
        else:
            r['Dw'], r['possW'] = float(x['D']), float(x['poss'])


def pos_mean_d_window(rows, blend_poss):
    """同 pos_mean_d，但讀 r['Dw']／r['possW']，池門檻 blend_poss。"""
    out = {}
    for pos in {r['pos'] for r in rows}:
        pool = [r for r in rows if r['pos'] == pos and r['possW'] >= blend_poss]
        out[pos] = sum(r['MIN'] * BLEND_PER36 * r['Dw'] for r in pool) / sum(r['MIN'] for r in pool)
    return out


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


def two_segment(x, p1, p50, p99):
    return np.where(x <= p50, 40 + 30 * (x - p1) / (p50 - p1), 70 + 29 * (x - p50) / (p99 - p50))


def write_pergame(out, rows, pred, argv):
    """E-064：每場影響力。g = pred*MPG/36（聯盟平均基準，主版）；g_r = (pred - r_repl)*MPG/36（替補基準，副版，r_repl = MIN>=500 池 pred 的 PR10）。
    錨點 = MIN>=500 池各人 g（或 g_r）的 PR1/PR50/PR99，分位數算法與 scaleAnchorsPer36 相同；映射與現行同一條兩段式。"""
    if '--mpgSource' in argv:
        mpg_src = {int(r['playerId']): float(r['mpg']) for r in csv.DictReader(open(Path(argv[argv.index('--mpgSource') + 1]), encoding='utf-8'))}
    else:
        league = json.loads(LEAGUE.read_text(encoding='utf-8'))
        mn, gp = {}, {}
        for t in league['teams']:
            for p in t['roster']:
                pid = int(p['playerId'])
                mn[pid] = mn.get(pid, 0.0) + p['observed']['MIN']; gp[pid] = gp.get(pid, 0) + p['observed']['GP']
        mpg_src = {pid: mn[pid] / gp[pid] for pid in mn if gp[pid] > 0}
    mpg = np.array([mpg_src.get(int(r['card']['playerId']), np.nan) for r in rows])
    inpool = np.array([r['MIN'] >= SCALE_MIN_MINUTES for r in rows])
    assert not np.isnan(mpg[inpool]).any(), 'MIN>=500 池內有人沒有 MPG'
    mpg_filled = np.where(np.isnan(mpg), 0.0, mpg)   # 該來源沒有出賽紀錄者 g=0（不在 MIN>=500 池內，不影響錨點）
    def qf(vals, prc):
        ref = np.sort(vals[inpool]); return float(ref[int(round(prc / 100 * (len(ref) - 1)))])
    r_repl = qf(np.asarray(pred), 10)
    variants = {'main': np.asarray(pred) * mpg_filled / 36, 'repl': (np.asarray(pred) - r_repl) * mpg_filled / 36}
    anchors = {}
    order = sorted(range(len(rows)), key=lambda i: rows[i]['name'])
    with open(out / 'pred.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['playerId', 'name', 'pos', 'MIN', 'pred', 'mpg'])
        for i in order:
            wr.writerow([int(rows[i]['card']['playerId']), rows[i]['name'], rows[i]['pos'], repr(float(rows[i]['MIN'])), repr(float(pred[i])), '' if np.isnan(mpg[i]) else repr(float(mpg[i]))])
    for tag, g in variants.items():
        p1, p50, p99 = qf(g, 1), qf(g, 50), qf(g, 99)
        anchors[tag] = {'PR1': p1, 'PR50': p50, 'PR99': p99}
        ovr = two_segment(g, p1, p50, p99)
        idx = sorted(range(len(rows)), key=lambda i: (-g[i], -pred[i], rows[i]['name']))
        with open(out / f'pergame-{tag}.csv', 'w', encoding='utf-8', newline='') as fh:
            wr = csv.writer(fh)
            wr.writerow(['rank', 'ovr', 'playerId', 'name', 'pos', 'MIN', 'mpg', 'pred', 'g'])
            for k, i in enumerate(idx):
                wr.writerow([k + 1, repr(float(ovr[i])), int(rows[i]['card']['playerId']), rows[i]['name'], rows[i]['pos'], round(rows[i]['MIN']),
                             '' if np.isnan(mpg[i]) else repr(float(mpg[i])), repr(float(pred[i])), repr(float(g[i]))])
    (out / 'pergame-summary.json').write_text(json.dumps({
        'definition': 'g = pred*MPG/36 (main); g_r = (pred - r_repl)*MPG/36 (repl, r_repl = PR10 of pred in MIN>=500 pool); anchors PR1/PR50/PR99 of g in MIN>=500 pool',
        'rRepl_PR10_of_pred': r_repl, 'anchors': anchors, 'poolSize': int(inpool.sum()),
        'mpgSource': argv[argv.index('--mpgSource') + 1] if '--mpgSource' in argv else 'league observed MIN/GP',
        'playersWithoutMpg': int(np.isnan(mpg).sum())}, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    argv = sys.argv
    direction = argv[argv.index('--direction') + 1]
    assert direction in ('G1', 'G2', 'G3', 'G4', 'H1', 'H2', 'H3', 'H4')
    gamma = float(argv[argv.index('--gamma') + 1]) if '--gamma' in argv else None
    delta = float(argv[argv.index('--delta') + 1]) if '--delta' in argv else None
    cap_margin = float(argv[argv.index('--capMargin') + 1]) if '--capMargin' in argv else None
    phi = float(argv[argv.index('--phi') + 1]) if '--phi' in argv else None
    restrict_pos = argv[argv.index('--restrictPos') + 1].split(',') if '--restrictPos' in argv else None
    global ATTRS, DRIVE_COLUMN, DRIVE_MODE, ATTR_SOURCE, DEF_SOURCE, RAPM, BLEND_POSS, BONUS_MIN_POSS, PRESSURE_MODE, PRESSURE_SOURCE, FOULDISC, TAIL_SOURCE
    if '--pressure' in argv:
        PRESSURE_MODE = argv[argv.index('--pressure') + 1]
    if '--pressureSource' in argv:
        PRESSURE_SOURCE = Path(argv[argv.index('--pressureSource') + 1]).resolve()
    FOULDISC = '--foulDisc' in argv
    assert PRESSURE_MODE in ('old', 'force', 'none')
    assert (PRESSURE_MODE != 'force' and not FOULDISC) or PRESSURE_SOURCE is not None, '--pressure force／--foulDisc 需要 --pressureSource'
    if PRESSURE_MODE == 'none':
        ATTRS = [a for a in ATTRS if a != 'pressure']
    if FOULDISC:
        ATTRS = ATTRS + ['foulDisc']
    if '--rapm' in argv:
        RAPM = Path(argv[argv.index('--rapm') + 1]).resolve()
    if '--possScale' in argv:
        scale = float(argv[argv.index('--possScale') + 1])
        BLEND_POSS, BONUS_MIN_POSS = 1000 * scale, 5000 * scale
    if '--driveMode' in argv:
        DRIVE_MODE = argv[argv.index('--driveMode') + 1]
    if '--attrSource' in argv:
        ATTR_SOURCE = Path(argv[argv.index('--attrSource') + 1]).resolve()
    if '--defSource' in argv:
        DEF_SOURCE = Path(argv[argv.index('--defSource') + 1]).resolve()
    if '--tailSource' in argv:
        TAIL_SOURCE = Path(argv[argv.index('--tailSource') + 1]).resolve()
    if '--driveColumn' in argv:
        DRIVE_COLUMN = argv[argv.index('--driveColumn') + 1]
    assert DRIVE_MODE in ('split', 'old')
    if DRIVE_MODE == 'old':
        ATTRS = [a for a in ATTRS if a != 'foulDraw']
    bonus_shape = argv[argv.index('--bonusShape') + 1] if '--bonusShape' in argv else 'taper'
    def_window = argv[argv.index('--defWindow') + 1] if '--defWindow' in argv else 'pooled'
    assert bonus_shape in ('taper', 'ceiling', 'none') and def_window in ('pooled', 'season')
    def_rapm = Path(argv[argv.index('--defRapm') + 1]).resolve() if '--defRapm' in argv else None
    def_poss_factor = float(argv[argv.index('--defPossFactor') + 1]) if '--defPossFactor' in argv else 0.25   # E-104
    assert (def_window == 'season') == (def_rapm is not None), '--defWindow season 需要 --defRapm'
    out = Path(argv[argv.index('--out') + 1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    alpha = 0.5

    if direction in ('G1', 'G2', 'G3'):
        assert gamma is not None, f'{direction} needs --gamma'
    if direction in ('G3', 'G4'):
        assert delta is not None, f'{direction} needs --delta'
    if direction in ('H1', 'H2', 'H3'):
        assert cap_margin is not None, f'{direction} needs --capMargin'
    if direction == 'H4':
        assert phi is not None, f'{direction} needs --phi'
    if direction.startswith('H'):
        assert restrict_pos is None, '--restrictPos is only for the G-series sanity check'

    rows = load(TARGET)
    for r in rows:
        r['simY'] = r['y']
    attach_rapm(rows, 0.0)
    attach_external_ranks(rows)
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

    if def_window == 'season':
        attach_def_window(rows, def_rapm)
        blend_w, bonus_min_w = BLEND_POSS * def_poss_factor, BONUS_MIN_POSS * def_poss_factor   # E-104：E-094 S 是 1/4，逐場加權改平均權重
        posMeanD = pos_mean_d_window(rows, blend_w)
        centeredD = np.array([BLEND_PER36 * r['Dw'] - posMeanD[r['pos']] if r['possW'] >= blend_w else np.nan for r in rows])
    else:
        posMeanD = pos_mean_d(rows)
        centeredD = np.array([BLEND_PER36 * r['D'] - posMeanD[r['pos']] if r['poss'] >= BLEND_POSS else np.nan for r in rows])
    r_target = np.array([r.get('r', np.nan) for r in rows])
    poss = np.array([r['poss'] for r in rows])

    pr_pool = sorted(pred0[i] for i, r in enumerate(rows) if r['MIN'] >= SCALE_MIN_MINUTES)
    pr = np.array([percentile_rank(p, pr_pool) for p in pred0])

    eligible = poss >= BONUS_MIN_POSS
    if def_window == 'season':
        eligible = np.array([r['possW'] >= bonus_min_w for r in rows])
    t96 = min(v for v in pr_pool if percentile_rank(v, pr_pool) >= PR_HI)
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

    if direction.startswith('H'):
        # 共同基線 = v57 G3-delta0.25：gamma=1.0、delta=0.25、taper PR 90/96
        raw_bonus = np.where(eligible & ~np.isnan(centeredD),
                             1.0 * np.maximum(0.0, np.nan_to_num(centeredD, nan=0.0)), 0.0)
        if bonus_shape == 'ceiling':
            bonus = np.minimum(raw_bonus, np.maximum(0.0, t96 - pred0))
        elif bonus_shape == 'none':   # E-106
            bonus = raw_bonus.copy()
        else:
            wgt = np.array([taper_w(p) for p in pr])
            bonus = raw_bonus * wgt
        align_eligible = poss >= BONUS_MIN_POSS
        align = np.where(align_eligible & ~np.isnan(r_target),
                         0.25 * (np.nan_to_num(r_target, nan=0.0) - pred0), 0.0)
        if direction == 'H4':
            align = np.where(align > 0, phi * align, align)

    pred = pred0 + bonus + align
    bonus_pre_cap = bonus.copy()
    cap_info = None
    if direction in ('H1', 'H2', 'H3'):
        ref_mode = 'consensus' if direction == 'H3' else 'rapm'
        allowed = cap_allowed(rows, cap_margin, ref_mode)
        lift = bonus + align
        pred_uncapped = pred0 + bonus + align
        if direction == 'H2':
            pred, bonus, iters = cap_bonus_only(pred, pred0, bonus, align, allowed)
        else:
            pred, iters = cap_total_lift(pred, pred0, lift, allowed)
        capped = np.abs(pred - pred_uncapped) > 1e-12
        cap_info = {
            'refMode': ref_mode, 'margin': cap_margin, 'iterations': iters,
            'allowedPlayers': int(sum(a is not None for a in allowed)),
            'cappedPlayers': int(capped.sum()), 'tieEpsilon': 1e-12,
            'cappedNames': [rows[i]['name'] for i in range(len(rows)) if capped[i]],
        }

    if '--perGame' in argv:
        write_pergame(out, rows, pred, argv)
    ref = np.sort([p for p, r in zip(pred, rows) if r['MIN'] >= SCALE_MIN_MINUTES])
    q = lambda prc: ref[int(round(prc / 100 * (len(ref) - 1)))]
    p1, p50, p99 = q(1), q(50), q(99)
    ovr = np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1), 70 + 29 * (pred - p50) / (p99 - p50))
    per10 = {a: {'per36': float(b[1 + i] / sd[i] * 10), 'bootstrapSE': float(np.std(boots[:, 1 + i]) / sd[i] * 10)} for i, a in enumerate(ATTRS)}
    # 決定性排序：pred 降冪，同值 pred0 降冪，再同值 name 字典序（只影響精確同值）。
    order = sorted(range(len(rows)), key=lambda i: (-pred[i], -pred0[i], rows[i]['name']))
    summary = {
        'target': str(TARGET.relative_to(ROOT)),
        'alpha': alpha, 'blendPreregistration': 'reports/ovr-v58-card-2025-26/preregistration.md', 'driveMode': DRIVE_MODE, 'driveColumn': DRIVE_COLUMN, 'attrSource': None if ATTR_SOURCE is None else ATTR_SOURCE.relative_to(ROOT).as_posix(),
        'direction': direction, 'gamma': gamma, 'delta': delta,
        'capMargin': cap_margin, 'phi': phi, 'cap': cap_info,
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
        **({} if (bonus_shape, def_window) == ('taper', 'pooled') else {'e094': {
            'bonusShape': bonus_shape, 'defWindow': def_window, 'defRapm': None if def_rapm is None else def_rapm.relative_to(ROOT).as_posix(),
            'T96': float(t96), 'bonusPositive': int((bonus_pre_cap > 1e-12).sum()),
            'bonusMedianPositive': float(np.median(bonus_pre_cap[bonus_pre_cap > 1e-12])) if (bonus_pre_cap > 1e-12).any() else 0.0,
            'bonusMax': float(bonus_pre_cap.max()),
            'f1_violations': [rows[i]['name'] for i in range(len(rows)) if pred0[i] < t96 and pred0[i] + bonus_pre_cap[i] > t96 + 1e-9],
            'f1_pr96_nonzero': [rows[i]['name'] for i in range(len(rows)) if pr[i] >= PR_HI and bonus_pre_cap[i] > 0],
            'f2_sample': [{'name': rows[i]['name'], 'centeredD': float(centeredD[i]),
                           'Dw': float(rows[i].get('Dw', rows[i]['D'])), 'pos': rows[i]['pos'], 'posMeanD': float(posMeanD[rows[i]['pos']])}
                          for i in [j for j in range(len(rows)) if not np.isnan(centeredD[j])][::37][:10]],
            **({'u1_sample': [{'name': rows[i]['name'], 'eligible': bool(eligible[i]), 'centeredD': None if np.isnan(centeredD[i]) else float(centeredD[i]),
                               'bonusPreCap': float(bonus_pre_cap[i])} for i in range(0, len(rows), max(1, len(rows) // 10))[:10]],
                'pr96_bonus': [{'name': rows[i]['name'], 'pr': float(pr[i]), 'bonusPreCap': float(bonus_pre_cap[i])}
                               for i in range(len(rows)) if pr[i] >= PR_HI and bonus_pre_cap[i] > 1e-12]} if bonus_shape == 'none' else {}),
        }}),
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
    print(json.dumps({'direction': direction, 'gamma': gamma, 'delta': delta,
                       'capMargin': cap_margin, 'phi': phi,
                       'capIterations': None if cap_info is None else cap_info['iterations'],
                       'cappedPlayers': None if cap_info is None else cap_info['cappedPlayers'],
                       'restrictPos': restrict_pos,
                       'chosen': summary['chosen'], 'noiseCeilingR2': summary['noiseCeilingR2']}, indent=1))


if __name__ == '__main__':
    main()
