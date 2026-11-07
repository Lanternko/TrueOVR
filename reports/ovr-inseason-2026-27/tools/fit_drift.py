"""S1：跨季漂移 δ²（preregistration-v2.md §2）。

兩端：先驗 data/prior-2023-24.json（x^p，P1）與 data/prior-2024-25.json（x^t，v1 S1），
同一 builder。逐能力值 a：
  d_i  = x_i^t − clip(x_i^p, 40, 99)                         i ∈ E_a
  V_a  = Σ(d_i − mean d)² / (m_a − 1)
  s²_i = σ²_a · (1/n_i^t + 1/n_i^p)
  δ²_a = max(0, V_a − mean_i s²_i)
候選只有兩個（§2.3）：D1 逐項 δ²（m_a<30 走 D2 比例並標 lowN）、D2 共用比例
  r̂ = Σ_{m_a≥30} δ²_a / Σ_{m_a≥30} σ²_a，δ²_{a,D2} = r̂·σ²_a。
τ² 不進收縮式；k_eff 逐人（§2.5），本檔只算部署人群（2024-25 先驗卡）的中位數對照。

輸出 v2/fit/drift.csv、v2/fit/drift.json（chosen 由 validate_2024_25.py --select 寫入）。
用法：python reports/ovr-inseason-2026-27/tools/fit_drift.py
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import DATA, FIT, ROOT, sha256_file, write_json
import season_attrs as SA
import v2_common as V2

PRIOR_23 = DATA / 'prior-2023-24.json'
PRIOR_24 = DATA / 'prior-2024-25.json'
ATTRS = V2.UPDATABLE
LOW_N = 30


def finite(v):
    try:
        return v is not None and float(v) == float(v)
    except (TypeError, ValueError):
        return False


def main():
    rel = V2.load_reliability()
    p23 = {c['playerId']: c for c in V2.load_json(PRIOR_23)['players']}
    p24 = {c['playerId']: c for c in V2.load_json(PRIOR_24)['players']}
    common = sorted(set(p23) & set(p24))

    per_attr = {}
    for a in ATTRS:
        d, s2, np_, nt_ = [], [], [], []
        for pid in common:
            xp, xt = p23[pid].get(a), p24[pid].get(a)
            if not (finite(xp) and finite(xt)):
                continue
            npv, ntv = V2.sample_n(p23[pid], a), V2.sample_n(p24[pid], a)
            if npv < SA.PRIOR_MIN_SAMPLE[a] or ntv < SA.PRIOR_MIN_SAMPLE[a]:
                continue
            d.append(float(xt) - max(40.0, min(99.0, float(xp))))
            s2.append(rel[a]['sigma2'] * (1.0 / ntv + 1.0 / npv))
            np_.append(npv)
            nt_.append(ntv)
        m = len(d)
        mu = sum(d) / m if m else 0.0
        var = sum((x - mu) ** 2 for x in d) / (m - 1) if m > 1 else 0.0
        mean_s2 = sum(s2) / m if m else 0.0
        delta = max(0.0, var - mean_s2)
        per_attr[a] = {'m': m, 'V': var, 'meanS2': mean_s2, 'zero': bool(m > 0 and delta == 0.0),
                       'delta2_D1_raw': delta, 'sigma2': rel[a]['sigma2'],
                       'nPriorMedian': V2.quantile(np_, 0.5) if np_ else 0.0,
                       'nTargetMedian': V2.quantile(nt_, 0.5) if nt_ else 0.0}

    elig = [a for a in ATTRS if per_attr[a]['m'] >= LOW_N]
    r_hat = (sum(per_attr[a]['delta2_D1_raw'] for a in elig)
             / sum(per_attr[a]['sigma2'] for a in elig)) if elig else 0.0
    delta2 = {'D1': {}, 'D2': {}}
    fallback = {}
    for a in ATTRS:
        low_n = per_attr[a]['m'] < LOW_N
        v = per_attr[a]['delta2_D1_raw']
        delta2['D1'][a] = r_hat * per_attr[a]['sigma2'] if low_n else v
        delta2['D2'][a] = r_hat * per_attr[a]['sigma2']
        per_attr[a]['delta2_D1_final'] = delta2['D1'][a]
        per_attr[a]['delta2_D2'] = delta2['D2'][a]
        fallback[a] = 'lowN' if low_n else ''

    deploy = {c['playerId']: c for c in V2.load_json(PRIOR_24)['players']}
    stats = {}
    for cand in ('D1', 'D2'):
        tab = V2.k_eff_table(deploy, delta2[cand], rel)
        for a in ATTRS:
            ks = [tab[p][a] for p in tab]
            ws = [10.0 / (10.0 + k) for k in ks]
            nref = rel[a]['nRef']
            lo, hi = 0.02 * nref, 50.0 * nref
            stats[(cand, a)] = {
                'median': V2.quantile(ks, 0.5), 'q1': V2.quantile(ks, 0.25), 'q3': V2.quantile(ks, 0.75),
                'w10Median': V2.quantile(ws, 0.5), 'w10Min': min(ws), 'w10Max': max(ws),
                'withinBounds': all(lo - 1e-9 <= k <= hi + 1e-9 for k in ks),
                'nPlayers': len(ks),
            }

    V2.V2_FIT.mkdir(parents=True, exist_ok=True)
    path = V2.V2_FIT / 'drift.csv'
    head = ['attr', 'm_a', 'V_a', 'meanS2_a', 'delta2_D1', 'zero_D1', 'fallback', 'delta2_D2',
            'rHat', 'sigma2', 'tau2', 'nRef', 'v1_k',
            'kEffD1_median', 'kEffD1_q1', 'kEffD1_q3', 'w10_D1_median',
            'kEffD2_median', 'kEffD2_q1', 'kEffD2_q3', 'w10_D2_median']
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(head)
        for a in ATTRS:
            pa = per_attr[a]
            s1, s2 = stats[('D1', a)], stats[('D2', a)]
            w.writerow([a, pa['m'], round(pa['V'], 6), round(pa['meanS2'], 6),
                        round(delta2['D1'][a], 6), int(pa['zero']), fallback[a] or '',
                        round(delta2['D2'][a], 6), round(r_hat, 6),
                        round(rel[a]['sigma2'], 6), round(rel[a]['tau2'], 6), round(rel[a]['nRef'], 6),
                        round(rel[a]['k'], 6),
                        round(s1['median'], 4), round(s1['q1'], 4), round(s1['q3'], 4), round(s1['w10Median'], 6),
                        round(s2['median'], 4), round(s2['q1'], 4), round(s2['q3'], 4), round(s2['w10Median'], 6)])

    sum_d = sum(delta2['D1'][a] for a in ATTRS)
    sum_s = sum(rel[a]['sigma2'] for a in ATTRS)
    doc = {
        'schemaVersion': 1,
        'sources': {
            'prior': {'file': 'data/prior-2023-24.json',
                      'sha256': sha256_file(PRIOR_23)},
            'target': {'file': 'data/prior-2024-25.json',
                       'sha256': sha256_file(PRIOR_24)},
            'reliability': {'file': 'fit/reliability.csv', 'season': '2022-25',
                            'sha256': sha256_file(FIT / 'reliability.csv')},
        },
        'formula': {
            'd': 'x_target - clip(x_prior, 40, 99)',
            'V': 'sample variance of d (ddof=1) over E_a',
            's2': 'sigma2_a * (1/n_target + 1/n_prior)',
            'delta2': 'max(0, V - mean(s2))',
            'rHat': 'sum(delta2 over m>=30) / sum(sigma2 over m>=30)',
            'kEff': 'sigma2_a / (delta2_a + sigma2_a/n_prior), clipped to [0.02*nRef, 50*nRef]',
            'tau2': 'not used in shrinkage (report comparison only)',
        },
        'populationRule': 'finite both ends and n_prior, n_target >= PRIOR_MIN_SAMPLE[attr] (full season)',
        'lowNThreshold': LOW_N,
        'rHat': r_hat,
        'attributesEligibleForRHat': elig,
        'perAttribute': {a: {k: (round(v, 6) if isinstance(v, float) else v) for k, v in per_attr[a].items()}
                         for a in ATTRS},
        'delta2': {c: {a: delta2[c][a] for a in ATTRS} for c in ('D1', 'D2')},
        'fallback': {a: fallback[a] for a in ATTRS},
        'kEffStats': {c: {a: stats[(c, a)] for a in ATTRS} for c in ('D1', 'D2')},
        'kEffPopulation': 'players in data/prior-2024-25.json (deployment prior), n^p from same card',
        'degenerate': {
            'sumDelta2_D1': sum_d, 'sumSigma2': sum_s, 'ratio': sum_d / sum_s,
            'driftNegligible': bool(sum_d <= 0.05 * sum_s),
            'rule': 'sum(delta2) <= 0.05*sum(sigma2) -> drift-negligible (v2 == v1, not adopted)',
        },
        'chosen': None,
        'candidates': {},
    }
    write_json(V2.V2_FIT / 'drift.json', doc)
    print(json.dumps({'rHat': r_hat, 'delta2_D1': delta2['D1'], 'delta2_D2': delta2['D2'],
                      'm': {a: per_attr[a]['m'] for a in ATTRS},
                      'kEffD1': {a: round(stats[('D1', a)]['median'], 2) for a in ATTRS},
                      'kEffD2': {a: round(stats[('D2', a)]['median'], 2) for a in ATTRS},
                      'degenerate': doc['degenerate']}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
