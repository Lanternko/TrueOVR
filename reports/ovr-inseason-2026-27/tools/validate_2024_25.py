"""S2/S3：2024-25 驗證季（先驗 2023-24、觀測 2024-25 前 N 場、目標 P3 的全季 OVR）。

--select（S2，§2.4）：只在 N=10 跑 D1／D2 兩個 C 候選，把 ρ_C,V／MAE_OVR／平均 9 項 MAE
  寫進 v2/fit/drift.json，依固定規則選出 chosen（|Δρ|≤0.005、|ΔMAE|≤0.01、|Δmean9|≤0.01，
  仍平手選 D1）。只用 2024-25 資料。
預設（S3）：讀 chosen，跑 A／B／C 四個 N，寫 v2/validation 12 檔預測＋SHA256SUMS，
  寫完 SHA 才讀目標檔評分，輸出 results.csv、coverage.csv 與 v2/fit/fallback.json（§4.4）。

人群 P24：2023-24 全季 MIN≥500、2024-25 全季 MIN≥500、視窗 MIN≥1（對應 v1 §4.1）。
k_eff 用驗證季先驗 n^p（2023-24 全季樣本）；τ² 不進收縮式。
用法：python reports/ovr-inseason-2026-27/tools/validate_2024_25.py [--select]
"""
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import ATTRS, DATA, FIT, MAIN_ATTRS, ROOT, UPDATABLE, load_json, write_json
import season_attrs as SA
import inseason_common as IC
import v2_common as V2
from ovr_pipeline import OVRPipeline

PRIOR_23 = DATA / 'prior-2023-24.json'
PRIOR_24 = DATA / 'prior-2024-25.json'
SEASON_CARDS = DATA / 'season-cards-2022-25.json'
RAPM = DATA / 'rapm-2022-23-24.csv'
TARGET = V2.V2_VALIDATION / 'target-2024-25-ovr.csv'
SEED = 20261026
DRAWS = 200
N_LIST = [3, 5, 10, 20]
GROUPS = {'prior': 'A', 'raw': 'B', 'shrunk': 'C'}
FROZEN = IC.FROZEN_ATTRS
SD_ATTRS = UPDATABLE


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


def usage_adjust(x0, w, attr):
    y, x0v = w[attr], x0[attr]
    u_obs, u_prior = w['u_proxy'], w.get('_u_prior', 0.0)
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
    sdt = {pid: {a: 0.0 for a in SD_ATTRS} for pid in prior_cards}
    for pid, w in windows.items():
        if pid not in prior_cards:
            continue
        w = dict(w)
        w['_u_prior'] = usg.get(pid, 0.0)
        x0 = prior_cards[pid]
        for a in UPDATABLE:
            if a == 'pressure':
                continue
            if a == 'creation' and N < 20:
                continue
            n = IC.sample_of(w, a)
            if n < SA.SEASON_MIN_SAMPLE[a]:
                continue
            y = usage_adjust(x0, w, a)
            B[pid][a] = y
            k = ktab[pid][a]
            C[pid][a] = max(40.0, min(99.0, (n * y + k * x0[a]) / (n + k)))
            sdt[pid][a] = math.sqrt(rel[a]['sigma2'] / (n + k))
    for pid in prior_cards:
        for a in FROZEN:
            A[pid][a] = B[pid][a] = C[pid][a] = prior_cards[pid][a]
    return A, B, C, sdt


def metrics(P, ovr, attr_sets, target, target_attrs, attr_keys, n_window):
    """ovr: pid->OVR；attr_sets: pid->{attr: value}（該組餵進管線的能力值）。"""
    pred_ovr = np.array([ovr[p] for p in P])
    tgt_ovr = np.array([target[p]['ovr'] for p in P])
    tgt_rank = {n: i + 1 for i, n in enumerate(sorted(P, key=lambda n: (-target[n]['ovr'], n)))}
    rank_pred = {n: i + 1 for i, n in enumerate(sorted(P, key=lambda n: (-ovr[n], n)))}
    out = {'players': len(P),
           'rho_ovr': round(float(spearmanr(pred_ovr, tgt_ovr).statistic), 6),
           'mae_ovr': round(float(np.mean(np.abs(pred_ovr - tgt_ovr))), 4),
           'rank_mae': round(float(np.mean([abs(rank_pred[n] - tgt_rank[n]) for n in P])), 4)}
    for a in attr_keys:
        if a in ('creation', 'pressure') and n_window < 20:
            out[f'mae_{a}'] = ''
        else:
            out[f'mae_{a}'] = round(float(np.mean([abs(attr_sets[p][a] - target_attrs[p][a]) for p in P])), 4)
    out['mean_mae9'] = round(float(np.mean([out[f'mae_{a}'] for a in MAIN_ATTRS])), 4)
    return out


def main():
    select = '--select' in sys.argv
    t0 = time.time()
    rel = V2.load_reliability()
    drift = V2.load_drift()
    prior_doc = load_json(PRIOR_23)
    prior_cards_all = {c['playerId']: c for c in prior_doc['players']}
    p24 = {c['playerId'] for c in load_json(PRIOR_24)['players']}
    mapping = {'priors': prior_doc['priors'], 'pools': prior_doc['mappingPools']}
    sc = load_json(SEASON_CARDS)['seasons']['2023-24']['cards']
    usg = {int(k): float(v.get('usg') or 0.0) * 100.0 for k, v in sc.items()}
    received = IC.received_prior('2023-24')

    sd = SA.load_season('2024-25')
    full = SA.aggregate(sd)
    season_min = {p: s['MIN'] for p, s in full.items()}
    windows_all = {N: IC.window_cards(sd, N, mapping, prior_cards_all, received) for N in N_LIST}
    pipe = OVRPipeline(V2.FROZEN_SUMMARY, RAPM, prior_cards_all)
    pid_list = sorted(prior_cards_all)
    print(json.dumps({'loadedSeconds': round(time.time() - t0, 1),
                      'playersWithWindow': {str(N): len(windows_all[N]) for N in N_LIST}}), flush=True)

    if select:
        n = 10
        windows = windows_all[n]
        P = [p for p in pid_list if prior_cards_all[p]['observed']['MIN'] >= 500
             and season_min.get(p, 0.0) >= 500 and windows.get(p, {}).get('MIN', 0.0) >= 1]
        target = {int(r['playerId']): r for r in csv.DictReader(open(TARGET, encoding='utf-8'))}
        for r in target.values():
            r['ovr'] = float(r['ovr'])
            for a in ATTRS:
                r[a] = float(r[a])
        target = {p: target[p] for p in target if p in set(pid_list)}
        tgt_attrs = {p: {a: float(target[p][a]) for a in ATTRS} for p in target}
        out = {}
        for cand in ('D1', 'D2'):
            ktab = V2.k_eff_table(prior_cards_all, drift['delta2'][cand], rel)
            A, B, C, sdt = build_attr_sets(prior_cards_all, windows, n, usg, rel, ktab)
            preds = {'A': pipe.predict(A), 'B': pipe.predict(B), 'C': pipe.predict(C)}
            sets = {'A': A, 'B': B, 'C': C}
            ovrs = {g: {p: preds[g][p]['ovr'] for p in preds[g] if p != '_capIterations'}
                    for g in ('A', 'B', 'C')}
            out[cand] = {'shrunk': metrics(P, ovrs['C'], C, target, tgt_attrs, MAIN_ATTRS, n),
                         'prior': metrics(P, ovrs['A'], A, target, tgt_attrs, MAIN_ATTRS, n),
                         'raw': metrics(P, ovrs['B'], B, target, tgt_attrs, MAIN_ATTRS, n)}
        d = out['D1']['shrunk']
        d2 = out['D2']['shrunk']
        if d['rho_ovr'] > d2['rho_ovr'] + 0.005:
            chosen = 'D1'
        elif d2['rho_ovr'] > d['rho_ovr'] + 0.005:
            chosen = 'D2'
        elif d['mae_ovr'] < d2['mae_ovr'] - 0.01:
            chosen = 'D1'
        elif d2['mae_ovr'] < d['mae_ovr'] - 0.01:
            chosen = 'D2'
        elif d['mean_mae9'] < d2['mean_mae9'] - 0.01:
            chosen = 'D1'
        elif d2['mean_mae9'] < d['mean_mae9'] - 0.01:
            chosen = 'D2'
        else:
            chosen = 'D1'
        drift['candidates'] = out
        drift['selectionRule'] = {
            'N': 10,
            'order': ['rho_C_V', 'mae_ovr', 'mean_mae9'],
            'ties': {'rho': 0.005, 'mae': 0.01, 'mean9': 0.01, 'final': 'D1'},
            'population': 'P24 (prior MIN>=500, 2024-25 MIN>=500, window MIN>=1)',
            'target': 'v2/validation/target-2024-25-ovr.csv',
        }
        drift['chosen'] = chosen
        write_json(V2.V2_FIT / 'drift.json', drift)
        print(json.dumps({'candidates': out, 'chosen': chosen}, ensure_ascii=False, indent=1))
        return 0

    chosen = drift['chosen']
    if chosen not in ('D1', 'D2'):
        raise SystemExit('drift.json chosen missing; run --select first')
    delta2 = {a: float(v) for a, v in drift['delta2'][chosen].items()}
    ktab = V2.k_eff_table(prior_cards_all, delta2, rel)
    Rc = residual_corr()
    rng = np.random.default_rng(SEED)
    draws = rng.multivariate_normal(np.zeros(len(SD_ATTRS)), Rc, size=DRAWS)

    V2.V2_VALIDATION.mkdir(parents=True, exist_ok=True)
    all_metrics = {}
    all_attrs = {}
    cov_rows = []
    for n in N_LIST:
        windows = windows_all[n]
        A, B, C, sdt = build_attr_sets(prior_cards_all, windows, n, usg, rel, ktab)
        P = [p for p in pid_list if prior_cards_all[p]['observed']['MIN'] >= 500
             and season_min.get(p, 0.0) >= 500 and windows.get(p, {}).get('MIN', 0.0) >= 1]
        preds = {'A': pipe.predict(A), 'B': pipe.predict(B), 'C': pipe.predict(C)}
        draws_ovr = {p: [] for p in pid_list}
        base_C = np.array([[C[p][a] for a in ATTRS] for p in pid_list], float)
        sd_mat = np.array([[sdt[p][a] for a in SD_ATTRS] for p in pid_list], float)
        for k in range(DRAWS):
            raw = base_C.copy()
            active = sd_mat > 0
            jitter = np.clip(base_C[:, [ATTRS.index(a) for a in SD_ATTRS]] + sd_mat * draws[k], 40.0, 99.0)
            raw[:, [ATTRS.index(a) for a in SD_ATTRS]] = np.where(active, jitter,
                                                                  base_C[:, [ATTRS.index(a) for a in SD_ATTRS]])
            dr = pipe.predict({p: {a: raw[i][ATTRS.index(a)] for a in ATTRS}
                               for i, p in enumerate(pid_list)})
            for p in pid_list:
                draws_ovr[p].append(dr[p]['ovr'])
        q = {p: np.percentile(draws_ovr[p], [10, 90, 2.5, 97.5]) for p in pid_list}
        osd = {p: float(np.std(draws_ovr[p])) for p in pid_list}
        for gname, gkey in (('prior', 'A'), ('raw', 'B'), ('shrunk', 'C')):
            rows = sorted(P, key=lambda p: -preds[gkey][p]['ovr'])
            with open(V2.V2_VALIDATION / f'{gname}-N{n}.csv', 'w', encoding='utf-8', newline='') as fh:
                w = csv.writer(fh)
                w.writerow(['playerId', 'name', 'pos', 'ovr', 'rank', 'MIN_window'] + ATTRS
                           + [f'sd_{a}' for a in SD_ATTRS]
                           + ['ovr_sd', 'ovr_p10', 'ovr_p90', 'ovr_p2p5', 'ovr_p97p5'])
                for r_i, p in enumerate(rows, 1):
                    vals = [p, prior_cards_all[p].get('name', ''), prior_cards_all[p]['pos'],
                            round(preds[gkey][p]['ovr'], 4), r_i, round(windows[p]['MIN'], 1)]
                    vals += [round({'A': A, 'B': B, 'C': C}[gkey][p][a], 3) for a in ATTRS]
                    vals += [round(sdt[p][a], 6) if gkey == 'C' else 0.0 for a in SD_ATTRS]
                    if gkey == 'C':
                        vals += [round(osd[p], 4), round(q[p][0], 4), round(q[p][1], 4),
                                 round(q[p][2], 4), round(q[p][3], 4)]
                    else:
                        v = round(preds[gkey][p]['ovr'], 4)
                        vals += [0.0, v, v, v, v]
                    w.writerow(vals)
        all_metrics[n] = {'A': preds['A'], 'B': preds['B'], 'C': preds['C'], 'P': P}
        all_attrs[n] = {'A': A, 'B': B, 'C': C}
        cov_rows.append({'N': n, 'players': len(P),
                         'ovr_width80_median': float(np.median([q[p][1] - q[p][0] for p in P])),
                         'ovr_width95_median': float(np.median([q[p][3] - q[p][2] for p in P]))})
        print(json.dumps({'N': n, 'P24': len(P), 'seconds': round(time.time() - t0, 1)}), flush=True)

    files = sorted(V2.V2_VALIDATION.glob('*-N*.csv'))
    (V2.V2_VALIDATION / 'SHA256SUMS').write_text(
        '\n'.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}' for f in files) + '\n',
        encoding='utf-8')

    # 以下才讀目標（答案）檔
    target = {int(r['playerId']): r for r in csv.DictReader(open(TARGET, encoding='utf-8'))}
    for r in target.values():
        r['ovr'] = float(r['ovr'])
        for a in ATTRS:
            r[a] = float(r[a])
    tgt_attrs = {p: {a: float(target[p][a]) for a in ATTRS} for p in target}
    results = []
    coverage = []
    for n in N_LIST:
        d = all_metrics[n]
        P = [p for p in d['P'] if p in target]
        for gname, gkey in (('prior', 'A'), ('raw', 'B'), ('shrunk', 'C')):
            ovr = {p: d[gkey][p]['ovr'] for p in P}
            m = metrics(P, ovr, all_attrs[n][gkey], target, tgt_attrs,
                        MAIN_ATTRS + ['creation', 'pressure'], n)
            results.append({'N': n, 'group': gname, **m})
        rows = {int(r['playerId']): r for r in csv.DictReader(open(V2.V2_VALIDATION / f'shrunk-N{n}.csv', encoding='utf-8'))}
        covered = {'80': 0, '95': 0, 'n': 0}
        for p in P:
            r = rows[p]
            for a in MAIN_ATTRS + ['creation']:
                sdv = float(r[f'sd_{a}'])
                if sdv <= 0:
                    continue
                covered['n'] += 1
                covered['80'] += int(abs(float(r[a]) - target[p][a]) <= 1.282 * sdv)
                covered['95'] += int(abs(float(r[a]) - target[p][a]) <= 1.96 * sdv)
        coverage.append({
            'N': n, 'players': len(P), 'attr_pairs': covered['n'],
            'attr_coverage80': round(covered['80'] / covered['n'], 4),
            'attr_coverage95': round(covered['95'] / covered['n'], 4),
            'ovr_coverage80': round(float(np.mean(
                [int(float(rows[p]['ovr_p10']) <= target[p]['ovr'] <= float(rows[p]['ovr_p90'])) for p in P])), 4),
            'ovr_coverage95': round(float(np.mean(
                [int(float(rows[p]['ovr_p2p5']) <= target[p]['ovr'] <= float(rows[p]['ovr_p97p5'])) for p in P])), 4),
            'ovr_width80_median': round(float(np.median(
                [float(rows[p]['ovr_p90']) - float(rows[p]['ovr_p10']) for p in P])), 4),
            'ovr_width95_median': round(float(np.median(
                [float(rows[p]['ovr_p97p5']) - float(rows[p]['ovr_p2p5']) for p in P])), 4),
            'intervalScope': 'sampling+drift (k_eff); eps_ovr added only in the deployment (judging) season interval',
        })
    with open(V2.V2_VALIDATION / 'results.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    with open(V2.V2_VALIDATION / 'coverage.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(coverage[0].keys()))
        w.writeheader()
        w.writerows(coverage)

    by = {(r['N'], r['group']): r for r in results}
    ns = []
    for n in N_LIST:
        if (by[(n, 'raw')]['rho_ovr'] > by[(n, 'prior')]['rho_ovr'] + 0.005
                and by[(n, 'raw')]['mae_ovr'] <= by[(n, 'prior')]['mae_ovr']):
            ns.append(n)
    n_cross = min(ns) if ns else None
    fallback = {
        'rule': 'N_cross = min{N: rho_B,V(N) > rho_A,V(N)+0.005 and MAE_B,V(N) <= MAE_A,V(N)}; '
                'display A for N < N_cross (or if absent), B for N >= N_cross',
        'N_cross': n_cross,
        'perN': {str(n): {'rho_A': by[(n, 'prior')]['rho_ovr'], 'rho_B': by[(n, 'raw')]['rho_ovr'],
                          'mae_A': by[(n, 'prior')]['mae_ovr'], 'mae_B': by[(n, 'raw')]['mae_ovr'],
                          'passes': bool(by[(n, 'raw')]['rho_ovr'] > by[(n, 'prior')]['rho_ovr'] + 0.005
                                         and by[(n, 'raw')]['mae_ovr'] <= by[(n, 'prior')]['mae_ovr'])}
                  for n in N_LIST},
        'chosenCandidate': chosen,
        'season': '2024-25 validation (prior 2023-24, target v2/validation/target-2024-25-ovr.csv)',
        'note': 'fixed before any judging-season result; must not be changed mid-season',
    }
    write_json(V2.V2_FIT / 'fallback.json', fallback)
    print(json.dumps({'results': results, 'coverage': coverage, 'fallback': fallback},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
