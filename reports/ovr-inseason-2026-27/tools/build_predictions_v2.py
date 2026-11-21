"""S4/S5：2025-26 前 N 場回測（A 先驗／B 原始／C_v2 收縮）＋含 ε_ovr 的 OVR 區間。

與 v1 build_predictions.py 的差異（preregistration-v2.md §2.5、§3）：
  - C 的 k 改成逐人 k_eff（δ²_a + σ²_a/n_i^p，§2.5），不再是全域 k。
  - C 的能力值區間 sd = sqrt(σ²/(n+k_eff))。
  - OVR 區間 = 管線抽樣 + ε_ovr·z（z 為 20261026 衍生的固定標準常態，每人每次一顆）。
A、B 組完全不變，輸出必須與 v1 backtest/predictions 的 prior/raw byte-identical。
ε_ovr 只用 2024-25 驗證季（§3.2b）：r = OVR_T − OVR_C(N=20)，s = 抽樣 SD；
ε = sqrt(max(0, median(r²) − median(s²)))，夾 [0.5, 3.0]，>3 或 |P24|<100 即停止。

輸出 v2/predictions/{prior,raw,shrunk}-N{3,5,10,20}.csv、SHA256SUMS、v2/fit/eps-ovr.json。
用法：python reports/ovr-inseason-2026-27/tools/build_predictions_v2.py
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
from ovr_common import ATTRS, DATA, MAIN_ATTRS, ROOT, UPDATABLE, load_json, write_json
import season_attrs as SA
import inseason_common as IC
import v2_common as V2
from ovr_pipeline import OVRPipeline

PRIOR = DATA / 'prior-2024-25.json'
SEASON_CARDS = DATA / 'season-cards-2022-25.json'
RAPM = DATA / 'rapm-2022-25.csv'
VAL_DIR = V2.V2_VALIDATION
VAL_TARGET = VAL_DIR / 'target-2024-25-ovr.csv'
N_LIST = [3, 5, 10, 20]
GROUPS = {'prior': 'A', 'raw': 'B', 'shrunk': 'C'}
SEED = 20261026
DRAWS = 200
FROZEN = IC.FROZEN_ATTRS
SD_ATTRS = UPDATABLE


def target_minutes(sd):
    return {pid: sum(r['MIN'] for r in b['rows']) for pid, b in sd['box'].items()}


def residual_corr():
    rows = list(csv.DictReader(open(DATA.parent / 'fit' / 'half-residuals.csv', encoding='utf-8')))
    data = {}
    for r in rows:
        data.setdefault(r['attr'], {})[(r['season'], r['playerId'])] = float(r['resid'])
    n = len(SD_ATTRS)
    R = np.eye(n)
    for i, a in enumerate(SD_ATTRS):
        for j, b in enumerate(SD_ATTRS):
            if j <= i:
                continue
            ka, kb = data.get(a, {}), data.get(b, {})
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
    return Rpsd / np.outer(d, d)


def usage_adjust(x0, w, attr, u_prior):
    y, x0v = w[attr], x0[attr]
    u_obs = w['u_proxy']
    if u_prior <= 0 or u_obs <= 0:
        return y
    ratio = u_obs / u_prior
    if ratio >= 1.1 or ratio <= 0.9:
        return x0v + (y - x0v) * min(1.0, u_prior / u_obs)
    return y


def build_attr_sets(prior_cards, windows, N, usg, rel, ktab):
    A = {pid: dict(c) for pid, c in prior_cards.items()}
    B = {pid: dict(c) for pid, c in prior_cards.items()}
    C = {pid: dict(c) for pid, c in prior_cards.items()}
    sdtab = {pid: {a: 0.0 for a in SD_ATTRS} for pid in prior_cards}
    for pid, w in windows.items():
        if pid not in prior_cards:
            continue
        x0 = prior_cards[pid]
        u_prior = usg.get(pid, 0.0)
        for a in UPDATABLE:
            if a == 'pressure':
                continue
            if a == 'creation' and N < 20:
                continue
            n = IC.sample_of(w, a)
            if n < SA.SEASON_MIN_SAMPLE[a]:
                continue
            y = usage_adjust(x0, w, a, u_prior)
            B[pid][a] = y
            k = ktab[pid][a]
            C[pid][a] = max(40.0, min(99.0, (n * y + k * x0[a]) / (n + k)))
            sdtab[pid][a] = math.sqrt(rel[a]['sigma2'] / (n + k))
    for pid in prior_cards:
        for a in FROZEN:
            A[pid][a] = B[pid][a] = C[pid][a] = prior_cards[pid][a]
    return A, B, C, sdtab


def eps_ovr_estimate():
    """§3.2(b)：只用 2024-25 驗證季 N=20、P24。"""
    rows = list(csv.DictReader(open(VAL_DIR / 'shrunk-N20.csv', encoding='utf-8')))
    target = {int(r['playerId']): r for r in csv.DictReader(open(VAL_TARGET, encoding='utf-8'))}
    P = [int(r['playerId']) for r in rows if int(r['playerId']) in target]
    if len(P) < 100:
        raise SystemExit(f'|P24| = {len(P)} < 100; cannot estimate eps_ovr (§3.2b)')
    by = {int(r['playerId']): r for r in rows}
    r2 = [ (float(target[p]['ovr']) - float(by[p]['ovr'])) ** 2 for p in P ]
    s2 = [ float(by[p]['ovr_sd']) ** 2 for p in P ]
    med_r2 = float(np.median(r2))
    med_s2 = float(np.median(s2))
    raw = math.sqrt(max(0.0, med_r2 - med_s2))
    eps = min(3.0, max(0.5, raw))
    out = {'epsilon': eps, 'raw': raw, 'lower': 0.5, 'upper': 3.0,
           'nP24': len(P), 'medianR2': med_r2, 'medianS2': med_s2,
           'formula': 'sqrt(max(0, median(r^2) - median(s^2))), clipped to [0.5, 3.0]',
           'source': {'validation': 'v2/validation/shrunk-N20.csv',
                      'target': 'v2/validation/target-2024-25-ovr.csv',
                      'season': '2024-25 validation; N=20; P24'}}
    if raw > 3.0:
        write_json(V2.V2_FIT / 'eps-ovr.json', out)
        raise SystemExit(f'eps_ovr raw = {raw:.4f} > 3.0 (upper bound); stop per §3.2b')
    write_json(V2.V2_FIT / 'eps-ovr.json', out)
    return eps, out


def main():
    t_start = time.time()
    V2.V2_PREDICTIONS.mkdir(parents=True, exist_ok=True)
    rel = V2.load_reliability()
    drift = V2.load_drift()
    delta2 = V2.chosen_delta2(drift)
    prior_doc = load_json(PRIOR)
    prior_cards = {p['playerId']: p for p in prior_doc['players']}
    sc_doc = load_json(SEASON_CARDS)
    sc = sc_doc['seasons']['2024-25']['cards']
    usg = {int(k): float(v.get('usg') or 0.0) * 100.0 for k, v in sc.items()}
    mapping = {'priors': sc_doc['seasons']['2024-25']['priors'],
               'pools': sc_doc['seasons']['2024-25']['pools']}
    ktab = V2.k_eff_table(prior_cards, delta2, rel)
    pipe = OVRPipeline(V2.FROZEN_SUMMARY, RAPM, prior_cards)
    eps, eps_meta = eps_ovr_estimate()
    print(json.dumps({'setupSeconds': round(time.time() - t_start, 1),
                      'epsilon': eps, 'nP24': eps_meta['nP24']}, ensure_ascii=False), flush=True)

    Rcorr = residual_corr()
    rng = np.random.default_rng(SEED)
    draws = rng.multivariate_normal(np.zeros(len(SD_ATTRS)), Rcorr, size=DRAWS)
    pid_list = sorted(prior_cards)
    zrng = np.random.default_rng(np.random.SeedSequence([SEED, 1]))
    z = zrng.standard_normal((DRAWS, len(pid_list)))

    sd = IC.load_target_season()
    tmin = target_minutes(sd)
    windows_all = {N: IC.window_cards(sd, N, mapping, prior_cards, IC.received_prior('2024-25'))
                   for N in N_LIST}
    print(json.dumps({'targetGames': len(sd['allGames']), 'pbpGames': len(sd['pbpGames']),
                      'badPbp': len(sd['badPbp']),
                      'playersWithWindow': {str(N): len(windows_all[N]) for N in N_LIST}},
                     ensure_ascii=False), flush=True)

    coverage_rows = []
    for N in N_LIST:
        windows = windows_all[N]
        A, B, C, sdt = build_attr_sets(prior_cards, windows, N, usg, rel, ktab)
        P = [p for p in pid_list
             if prior_cards[p]['observed']['MIN'] >= 500 and tmin.get(p, 0.0) >= 500
             and windows.get(p, {}).get('MIN', 0.0) >= 1]
        preds = {'A': pipe.predict(A), 'B': pipe.predict(B), 'C': pipe.predict(C)}
        c_draws = {p: [] for p in pid_list}
        base_C = np.array([[C[p][a] for a in ATTRS] for p in pid_list], float)
        sd_mat = np.array([[sdt[p][a] for a in SD_ATTRS] for p in pid_list], float)
        for k in range(DRAWS):
            raw = base_C.copy()
            active = sd_mat > 0
            jitter = np.clip(base_C[:, [ATTRS.index(a) for a in SD_ATTRS]] + sd_mat * draws[k], 40.0, 99.0)
            raw[:, [ATTRS.index(a) for a in SD_ATTRS]] = np.where(active, jitter,
                                                                  base_C[:, [ATTRS.index(a) for a in SD_ATTRS]])
            d = pipe.predict({p: {a: raw[i][ATTRS.index(a)] for a in ATTRS}
                              for i, p in enumerate(pid_list)})
            for j, p in enumerate(pid_list):
                c_draws[p].append(d[p]['ovr'] + eps * float(z[k, j]))
        q = {p: np.percentile(c_draws[p], [10, 90, 2.5, 97.5]) for p in pid_list}
        print(json.dumps({'N': N, 'P': len(P), 'seconds': round(time.time() - t_start, 1)},
                         ensure_ascii=False), flush=True)
        rank_pred = {g: sorted(P, key=lambda p: -preds[g][p]['ovr']) for g in ('A', 'B', 'C')}
        for gname, gkey in (('prior', 'A'), ('raw', 'B'), ('shrunk', 'C')):
            path = V2.V2_PREDICTIONS / f'{gname}-N{N}.csv'
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
        coverage_rows.append({'N': N, 'players': len(P),
                              'ovr_width80_median': float(np.median([q[p][1] - q[p][0] for p in P])),
                              'ovr_width95_median': float(np.median([q[p][3] - q[p][2] for p in P]))})
    write_json(V2.V2_FIT / 'coverage-intervals.json', coverage_rows)
    files = sorted(V2.V2_PREDICTIONS.glob('*.csv'))
    (V2.V2_PREDICTIONS / 'SHA256SUMS').write_text(
        '\n'.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}' for f in files) + '\n',
        encoding='utf-8')
    print(json.dumps({'intervalsSeconds': round(time.time() - t_start, 1), 'files': len(files),
                      'rows': coverage_rows, 'epsOvr': eps_meta}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
