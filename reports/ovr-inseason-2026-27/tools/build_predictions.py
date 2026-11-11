"""S4/S5：2025-26 前 N 場回測預測（A 先驗／B 原始／C 收縮）＋區間覆蓋率。

只讀 §5.2 允許的目標季資料：data/season-source/player-games.json、team-games.json、
data/defense-a-source/pbp；答案卡 card-H1-m0/ranking.csv 由 score_backtest.py 在
SHA256SUMS 寫出後才讀。人群 P 的 2025-26 全季 MIN 由 player-games 累加（不讀答案卡）。

A：x̂=x0'（先驗＋§3 選中的調整，本輪年齡=none）
B：x̂=y_adj（達季中最低樣本才用觀測，否則 x0'；creation 只在 N>=20）
C：§1.3 收縮 (n·y_adj + k·x0')/(n+k)
pressure 本輪不更新（2025-26 無 stints），所有組別沿用先驗。
區間：sd=sqrt(σ²/(n+k))；OVR 用 2022-25 分半殘差相關矩陣做 200 次聯合抽樣（種子 20261026）。

輸出：backtest/predictions/{prior,raw,shrunk}-N{3,5,10,20}.csv、backtest/coverage.csv、
      backtest/predictions/SHA256SUMS（最後才寫）。
用法：python reports/ovr-inseason-2026-27/tools/build_predictions.py
"""
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import ATTRS, BACKTEST, DATA, FIT, MAIN_ATTRS, ROOT, UPDATABLE, load_json, write_json
import season_attrs as SA
import inseason_common as IC
from ovr_pipeline import OVRPipeline

PRIOR = DATA / 'prior-2024-25.json'
SEASON_CARDS = DATA / 'season-cards-2022-25.json'
SUMMARY = ROOT / 'reports/ovr-v58-card-2025-26/card-H1-m0/summary.json'
RAPM = DATA / 'rapm-2022-25.csv'
N_LIST = [3, 5, 10, 20]
GROUPS = {'prior': 'A', 'raw': 'B', 'shrunk': 'C'}
SEED = 20261026
DRAWS = 200
FROZEN = IC.FROZEN_ATTRS
SD_ATTRS = UPDATABLE


def target_minutes(sd):
    out = {}
    for pid, b in sd['box'].items():
        out[pid] = sum(r['MIN'] for r in b['rows'])
    return out


def load_reliability():
    rows = list(csv.DictReader(open(FIT / 'reliability.csv', encoding='utf-8')))
    return {r['attr']: {'k': float(r['k']), 'sigma2': float(r['sigma2']), 'nRef': float(r['nRef'])}
            for r in rows if r['season'] == '2022-25'}


def residual_corr():
    rows = list(csv.DictReader(open(FIT / 'half-residuals.csv', encoding='utf-8')))
    data = {}
    for r in rows:
        data.setdefault(r['attr'], {})[(r['season'], r['playerId'])] = float(r['resid'])
    n = len(SD_ATTRS)
    R = np.eye(n)
    for i, a in enumerate(SD_ATTRS):
        for j, b in enumerate(SD_ATTRS):
            if j <= i:
                continue
            ka = data.get(a, {})
            kb = data.get(b, {})
            keys = sorted(set(ka) & set(kb))
            if len(keys) < 3:
                rho = 0.0
            else:
                x = np.array([ka[k] for k in keys])
                y = np.array([kb[k] for k in keys])
                rho = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else 0.0
            R[i, j] = R[j, i] = rho
    w, V = np.linalg.eigh((R + R.T) / 2)
    w = np.clip(w, 1e-6, None)
    Rpsd = V @ np.diag(w) @ V.T
    d = np.sqrt(np.diag(Rpsd))
    Rpsd = Rpsd / np.outer(d, d)
    return Rpsd


def age_rule(fit):
    return fit['chosen']


def apply_age(card, rule, fit):
    out = dict(card)
    if rule == 'none':
        return out
    a = card.get('age')
    if a is None:
        return out
    for attr in MAIN_ATTRS:
        if rule == 'A1':
            from fit_adjustments import band
            d = fit['groupDelta'][attr].get(band(a), 0.0)
        else:
            c = fit['linear'][attr]
            d = c['alpha'] + c['beta'] * (a + 1 - 27.0)
        out[attr] = max(40.0, min(99.0, card[attr] + d))
    return out


def usage_adjust(x0, w, attr, coef, u_prior):
    y = w[attr]
    x0v = x0[attr]
    u_obs = w['u_proxy']
    if u_prior <= 0 or u_obs <= 0:
        return y
    ratio = u_obs / u_prior
    if ratio >= 1.1 or ratio <= 0.9:
        return x0v + (y - x0v) * min(1.0, u_prior / u_obs)
    return y


def build_attr_sets(prior_cards, windows, N, age_r, age_fit, u_coef, usg):
    x0s = {pid: apply_age(c, age_r, age_fit) for pid, c in prior_cards.items()}
    A = {pid: dict(x0s[pid]) for pid in prior_cards}
    B = {pid: dict(x0s[pid]) for pid in prior_cards}
    C = {pid: dict(x0s[pid]) for pid in prior_cards}
    sdtab = {pid: {a: 0.0 for a in SD_ATTRS} for pid in prior_cards}
    for pid, w in windows.items():
        if pid not in prior_cards:
            continue
        x0 = x0s[pid]
        u_prior = usg.get(pid, 0.0)
        for a in UPDATABLE:
            if a == 'pressure':
                continue
            if a == 'creation' and N < 20:
                continue
            n = IC.sample_of(w, a)
            if n < SA.SEASON_MIN_SAMPLE[a]:
                continue
            y = usage_adjust(x0, w, a, u_coef, u_prior)
            B[pid][a] = y
            rel = REL[a]
            C[pid][a] = max(40.0, min(99.0, (n * y + rel['k'] * x0[a]) / (n + rel['k'])))
            sdtab[pid][a] = math.sqrt(rel['sigma2'] / (n + rel['k']))
    for pid in prior_cards:
        for a in FROZEN:
            A[pid][a] = B[pid][a] = C[pid][a] = prior_cards[pid][a]
    return A, B, C, sdtab


def predict_ovr(pipe, attrs):
    return pipe.predict(attrs)


def main():
    t_start = time.time()
    BACKTEST.mkdir(parents=True, exist_ok=True)
    (BACKTEST / 'predictions').mkdir(parents=True, exist_ok=True)
    prior_doc = load_json(PRIOR)
    prior_cards = {p['playerId']: p for p in prior_doc['players']}
    sc = load_json(SEASON_CARDS)['seasons']['2024-25']['cards']
    usg = {int(k): float(v.get('usg') or 0.0) * 100.0 for k, v in sc.items()}
    age_fit = load_json(FIT / 'age.json')
    usage_fit = load_json(FIT / 'usage.json')
    age_r = age_rule(age_fit)
    u_coef = usage_fit['regression']['attrs']
    global REL
    REL = load_reliability()
    mapping = {'priors': load_json(SEASON_CARDS)['seasons']['2024-25']['priors'],
               'pools': load_json(SEASON_CARDS)['seasons']['2024-25']['pools']}
    pipe = OVRPipeline(SUMMARY, RAPM, prior_cards)
    Rcorr = residual_corr()
    rng = np.random.default_rng(SEED)
    draws = rng.multivariate_normal(np.zeros(len(SD_ATTRS)), Rcorr, size=DRAWS)
    print(json.dumps({'setupSeconds': round(time.time() - t_start, 1),
                      'ageRule': age_r, 'usageChosen': usage_fit['chosen']}, ensure_ascii=False),
          flush=True)

    sd = IC.load_target_season()
    tmin = target_minutes(sd)
    windows_all = {N: IC.window_cards(sd, N, mapping, prior_cards, IC.received_prior('2024-25'))
                   for N in N_LIST}
    print(json.dumps({'targetGames': len(sd['allGames']), 'pbpGames': len(sd['pbpGames']),
                      'badPbp': len(sd['badPbp']),
                      'playersWithWindow': {str(N): len(windows_all[N]) for N in N_LIST}},
                     ensure_ascii=False), flush=True)

    coverage_rows = []
    pid_list = sorted(prior_cards)
    for N in N_LIST:
        windows = windows_all[N]
        A, B, C, sdt = build_attr_sets(prior_cards, windows, N, age_r, age_fit, u_coef, usg)
        # 人群 P：先驗季 MIN>=500、2025-26 全季 MIN>=500、視窗 MIN>=1
        P = [p for p in pid_list
             if prior_cards[p]['observed']['MIN'] >= 500 and tmin.get(p, 0.0) >= 500
             and windows.get(p, {}).get('MIN', 0.0) >= 1]
        Pset = set(P)
        preds = {'A': predict_ovr(pipe, A), 'B': predict_ovr(pipe, B), 'C': predict_ovr(pipe, C)}
        # C 的聯合抽樣（OVR 區間）
        c_draws = {p: [] for p in pid_list}
        base_C = np.array([[C[p][a] for a in ATTRS] for p in pid_list], float)
        sd_mat = np.array([[sdt[p][a] for a in SD_ATTRS] for p in pid_list], float)
        for k in range(DRAWS):
            raw = base_C.copy()
            active = sd_mat > 0
            jitter = np.clip(base_C[:, [ATTRS.index(a) for a in SD_ATTRS]]
                             + sd_mat * draws[k], 40.0, 99.0)
            raw[:, [ATTRS.index(a) for a in SD_ATTRS]] = np.where(active, jitter,
                                                                  base_C[:, [ATTRS.index(a) for a in SD_ATTRS]])
            d = pipe.predict({p: {a: raw[i][ATTRS.index(a)] for a in ATTRS}
                              for i, p in enumerate(pid_list)})
            for p in pid_list:
                c_draws[p].append(d[p]['ovr'])
        q = {p: np.percentile(c_draws[p], [10, 90, 2.5, 97.5]) for p in pid_list}
        print(json.dumps({'N': N, 'P': len(P), 'seconds': round(time.time() - t_start, 1)},
                         ensure_ascii=False), flush=True)
        # 寫 12 檔
        rank_pred = {g: sorted(P, key=lambda p: -preds[g][p]['ovr']) for g in ('A', 'B', 'C')}
        for gname, gkey in (('prior', 'A'), ('raw', 'B'), ('shrunk', 'C')):
            path = BACKTEST / 'predictions' / f'{gname}-N{N}.csv'
            with open(path, 'w', encoding='utf-8', newline='') as fh:
                w = csv.writer(fh)
                head = (['playerId', 'name', 'pos', 'ovr', 'rank', 'MIN_window'] + ATTRS
                        + [f'sd_{a}' for a in SD_ATTRS]
                        + ['ovr_p10', 'ovr_p90', 'ovr_p2p5', 'ovr_p97p5'])
                w.writerow(head)
                for r_i, p in enumerate(rank_pred[gkey], 1):
                    vals = [p, prior_cards[p].get('name', ''), prior_cards[p]['pos'],
                            round(preds[gkey][p]['ovr'], 4), r_i,
                            round(windows[p]['MIN'], 1)]
                    vals += [round({'A': A, 'B': B, 'C': C}[gkey][p][a], 3) for a in ATTRS]
                    vals += [round(sdt[p][a], 6) if gkey == 'C' else 0.0 for a in SD_ATTRS]
                    if gkey == 'C':
                        vals += [round(q[p][0], 4), round(q[p][1], 4), round(q[p][2], 4), round(q[p][3], 4)]
                    else:
                        v = round(preds[gkey][p]['ovr'], 4)
                        vals += [v, v, v, v]
                    w.writerow(vals)
        # 覆蓋率需要答案卡，由 score_backtest.py 在 SHA 之後算並寫 coverage.csv；
        # 這裡只留下區間寬度。
        cov = {'N': N, 'players': len(P),
               'ovr_width80_median': float(np.median([q[p][1] - q[p][0] for p in P])),
               'ovr_width95_median': float(np.median([q[p][3] - q[p][2] for p in P]))}
        coverage_rows.append(cov)
    write_json(DATA / 'coverage-intervals.json', coverage_rows)
    # SHA 必須在 score_backtest.py 讀答案卡之前寫出（§5.5）
    files = sorted((BACKTEST / 'predictions').glob('*.csv'))
    lines = []
    for f in files:
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        lines.append(f'{h}  {f.name}')
    (BACKTEST / 'predictions' / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'intervalsSeconds': round(time.time() - t_start, 1),
                      'files': len(files),
                      'rows': coverage_rows}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
