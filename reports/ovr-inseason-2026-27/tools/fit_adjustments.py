"""S3：年齡與拿球比重調整（preregistration §3）。

年齡（§3.1）：
  A1 群組差分 Δ_group = Σ(x_{s+1}-x_s)/(人次+50)，分組用先驗季年齡段。
  A2 線性 Δx = α + β·(a_target-27)，預測 Δ = α + β·(a+1-27)。
  選擇：只在 2023-24→2024-25 轉換、兩季 MIN>=500 的球員上比 9 個主要能力值平均 MAE；
        A1 改善 >=3% 選 A1，否則 A2 改善 >=3% 選 A2，否則不調整（平手→不調整）。
拿球（§3.2）：
  U1 x = α + β·u + 位置固定效果（2022-25 全季卡）；y_adj = y_obs - β(u_obs-u_prior)。
  U2 y_adj = x0' + (y_obs-x0')·min(1,u_prior/u_obs)，只在比值 >=1.1 或 <=0.9 時套。
  選擇：兩個「先驗季→前 10 場」演練、|u_obs/u_prior-1|>=0.10 的球員、7 個能力值平均 MAE；
        U1 需在兩轉換都改善 >=3% 且都優於 U2；否則 U2 需兩轉換都改善 >=3%；否則不調整。

輸出：fit/age.json、fit/usage.json。
用法：python reports/ovr-inseason-2026-27/tools/fit_adjustments.py
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import DATA, FIT, MAIN_ATTRS, write_json
import season_attrs as SA
import inseason_common as IC

CARDS = DATA / 'season-cards-2022-25.json'
AGE_BANDS = [(0, 22, '<=22'), (23, 26, '23-26'), (27, 30, '27-30'), (31, 34, '31-34'), (35, 99, '>=35')]
PRIOR_MIN = 50.0
USAGE_ATTRS = ['long', 'mid', 'short', 'drive', 'tovSkill', 'pass', 'creation']
DRILL_N = 10


def band(age):
    for lo, hi, name in AGE_BANDS:
        if lo <= age <= hi:
            return name
    return '>=35'


def mae(pairs):
    return float(np.mean(np.abs(np.asarray(pairs, float)))) if pairs else float('nan')


def load_cards():
    doc = json.loads(CARDS.read_text(encoding='utf-8'))
    out = {}
    for season, sd in doc['seasons'].items():
        out[season] = {'cards': {int(k): v for k, v in sd['cards'].items()},
                       'priors': sd['priors'], 'pools': sd['pools'],
                       'poolPlayerIds': sd['poolPlayerIds']}
    return out


def age_fit(cards):
    pairs = [('2022-23', '2023-24'), ('2023-24', '2024-25')]
    group_sum = {a: {} for a in MAIN_ATTRS}
    group_cnt = {a: {} for a in MAIN_ATTRS}
    lin = {a: [] for a in MAIN_ATTRS}
    transition_rows = []
    for s, s1 in pairs:
        cs, cs1 = cards[s]['cards'], cards[s1]['cards']
        common = sorted(set(cs) & set(cs1))
        for pid in common:
            a_prior = cs[pid]['age']
            a_target = cs1[pid]['age']
            if a_prior is None or a_target is None:
                continue
            b = band(a_prior)
            for a in MAIN_ATTRS:
                d = cs1[pid][a] - cs[pid][a]
                group_sum[a][b] = group_sum[a].get(b, 0.0) + d
                group_cnt[a][b] = group_cnt[a].get(b, 0) + 1
                lin[a].append((a_target - 27.0, d))
        transition_rows.append({'from': s, 'to': s1, 'players': len(common)})
    deltas = {a: {b: group_sum[a][b] / (group_cnt[a][b] + PRIOR_MIN) for b in group_sum[a]}
              for a in MAIN_ATTRS}
    coef = {}
    for a in MAIN_ATTRS:
        x = np.array([p[0] for p in lin[a]], float)
        y = np.array([p[1] for p in lin[a]], float)
        X = np.c_[np.ones(len(x)), x]
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        coef[a] = {'alpha': float(beta[0]), 'beta': float(beta[1])}

    s, s1 = '2023-24', '2024-25'
    cs, cs1 = cards[s]['cards'], cards[s1]['cards']
    pop = [pid for pid in sorted(set(cs) & set(cs1))
           if cs[pid]['observed']['MIN'] >= 500 and cs1[pid]['observed']['MIN'] >= 500]
    per_attr = {a: {'none': [], 'A1': [], 'A2': []} for a in MAIN_ATTRS}
    for pid in pop:
        a_prior = cs[pid]['age']
        a_target = cs1[pid]['age']
        b = band(a_prior)
        for a in MAIN_ATTRS:
            truth = cs1[pid][a]
            base = cs[pid][a]
            v1 = max(40.0, min(99.0, base + deltas[a].get(b, 0.0)))
            v2 = max(40.0, min(99.0, base + coef[a]['alpha'] + coef[a]['beta'] * (a_target - 27.0)))
            per_attr[a]['none'].append(base - truth)
            per_attr[a]['A1'].append(v1 - truth)
            per_attr[a]['A2'].append(v2 - truth)
    mae_tab = {a: {k: mae(v) for k, v in per_attr[a].items()} for a in MAIN_ATTRS}
    mean_mae = {k: float(np.mean([mae_tab[a][k] for a in MAIN_ATTRS])) for k in ('none', 'A1', 'A2')}
    imp = {k: (mean_mae['none'] - mean_mae[k]) / mean_mae['none'] for k in ('A1', 'A2')}
    if imp['A1'] >= 0.03:
        chosen = 'A1'
    elif imp['A2'] >= 0.03:
        chosen = 'A2'
    else:
        chosen = 'none'
    reasons = {
        'rule': 'A1 if improvement>=3%; else A2 if >=3%; else none (ties -> none)',
        'improvementVsNone': {k: round(v, 6) for k, v in imp.items()},
        'population': len(pop), 'populationRule': '2023-24 & 2024-25 MIN>=500',
        'bandBasis': 'prior-season age band',
        'A2regressionX': 'age in the later (target) season - 27',
    }
    return {'transitions': transition_rows, 'groupDelta': {a: {k: round(v, 6) for k, v in deltas[a].items()} for a in MAIN_ATTRS},
            'groupCounts': {a: group_cnt[a] for a in MAIN_ATTRS},
            'linear': coef, 'evaluation': {'perAttrMAE': mae_tab, 'meanMAE': mean_mae},
            'chosen': chosen, 'reasons': reasons}


def _design_usage(cards):
    rows = []
    for season, d in cards.items():
        for pid, c in d['cards'].items():
            u = c.get('usg')
            if u is None or u <= 0:
                continue
            rows.append((c, u * 100.0))  # bio USG_PCT 是 0-1 比例，換成百分數
    return rows


def usage_regression(cards):
    rows = _design_usage(cards)
    pos = ['PG', 'SG', 'SF', 'PF', 'C']
    coef = {}
    for a in USAGE_ATTRS:
        y = np.array([c[a] for c, _ in rows], float)
        X = np.array([[1.0, u] + [1.0 if c['pos'] == p else 0.0 for p in pos[1:]] for c, u in rows], float)
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        coef[a] = {'intercept': float(beta[0]), 'slopeU': float(beta[1]),
                   'posEffects': {p: (0.0 if i == 0 else float(beta[2 + i - 1])) for i, p in enumerate(pos)}}
    return coef, len(rows)


def _age_adjust(card, age_rule, age_fit):
    out = dict(card)
    if age_rule == 'none':
        return out
    a_prior = card['age']
    a_target = a_prior + 1 if a_prior is not None else None
    for a in MAIN_ATTRS:
        if age_rule == 'A1':
            d = age_fit['groupDelta'].get(a, {}).get(band(a_prior), 0.0)
        else:
            c = age_fit['linear'][a]
            d = c['alpha'] + c['beta'] * (a_target - 27.0)
        out[a] = max(40.0, min(99.0, card[a] + d))
    return out


def usage_eval(cards, age_rule, age_fit, coef):
    pairs = [('2022-23', '2023-24'), ('2023-24', '2024-25')]
    trans = {}
    for s, s1 in pairs:
        t0 = time.time()
        sd = SA.load_season(s1)
        mapping = {'priors': cards[s]['priors'], 'pools': cards[s]['pools']}
        prior = {pid: _age_adjust(c, age_rule, age_fit) for pid, c in cards[s]['cards'].items()}
        received = IC.received_prior(s)
        win = IC.window_cards(sd, DRILL_N, mapping, cards[s]['cards'], received)
        per_attr = {a: {'n': 0, 'none': [], 'U1': [], 'U2': []} for a in USAGE_ATTRS}
        pop = 0
        for pid, w in win.items():
            pc = cards[s]['cards'].get(pid)
            if pc is None:
                continue
            u_prior = (pc.get('usg') or 0.0) * 100.0
            if u_prior <= 0:
                continue
            u_obs = w['u_proxy']
            ratio = u_obs / u_prior
            if abs(ratio - 1.0) < 0.10:
                continue
            pop += 1
            x0 = prior[pid]
            for a in USAGE_ATTRS:
                n = IC.sample_of(w, a)
                if n < SA.SEASON_MIN_SAMPLE[a]:
                    continue
                y_obs = w[a]
                truth = cards[s1]['cards'][pid][a]
                u1 = y_obs - coef[a]['slopeU'] * (u_obs - u_prior)
                if ratio >= 1.1 or ratio <= 0.9:
                    u2 = x0[a] + (y_obs - x0[a]) * min(1.0, u_prior / u_obs)
                else:
                    u2 = y_obs
                per_attr[a]['n'] += 1
                per_attr[a]['none'].append(y_obs - truth)
                per_attr[a]['U1'].append(u1 - truth)
                per_attr[a]['U2'].append(u2 - truth)
        mae_tab = {a: {k: mae(v) for k, v in per_attr[a].items() if k != 'n'} for a in USAGE_ATTRS}
        mean_mae = {k: float(np.mean([mae_tab[a][k] for a in USAGE_ATTRS if math.isfinite(mae_tab[a][k])]))
                    for k in ('none', 'U1', 'U2')}
        trans[f'{s}->{s1}'] = {'population': pop, 'sessionEligible': {a: per_attr[a]['n'] for a in USAGE_ATTRS},
                               'perAttrMAE': mae_tab, 'meanMAE': mean_mae,
                               'improvement': {k: (mean_mae['none'] - mean_mae[k]) / mean_mae['none']
                                               for k in ('U1', 'U2')},
                               }
        print(json.dumps({'usageDrill': f'{s}->{s1}', 'population': pop,
                          'meanMAE': mean_mae, 'improvement': trans[f'{s}->{s1}']['improvement']},
                         ensure_ascii=False), flush=True)
    u1_ok = all(t['improvement']['U1'] >= 0.03 for t in trans.values())
    u2_ok = all(t['improvement']['U2'] >= 0.03 for t in trans.values())
    u1_beats_u2 = all(t['meanMAE']['U1'] < t['meanMAE']['U2'] for t in trans.values())
    chosen = 'U1' if (u1_ok and u1_beats_u2) else ('U2' if u2_ok else 'none')
    reasons = {'rule': 'U1 if both transitions improve>=3% and U1<U2; else U2 if both>=3%; else none',
               'U1bothImprove': u1_ok, 'U2bothImprove': u2_ok, 'U1beatsU2': u1_beats_u2,
               'uPrior': 'official USG_PCT (prior season, x100 to official scale)',
               'uObs': 'u_proxy = 100*(FGA+0.44FTA+TOV)/on-floor team possessions (official scale); '
                       'u_proxy_per36 also recorded in window cards but not used for the ratio',
               'minSample': 'in-season minimum per attr (§1.1)'}
    return {'drills': trans, 'chosen': chosen, 'reasons': reasons}


def main():
    FIT.mkdir(parents=True, exist_ok=True)
    cards = load_cards()
    age = age_fit(cards)
    write_json(FIT / 'age.json', age)
    print(json.dumps({'ageChosen': age['chosen'], 'meanMAE': age['evaluation']['meanMAE'],
                      'improvement': age['reasons']['improvementVsNone']}, ensure_ascii=False), flush=True)
    coef, n_usage = usage_regression(cards)
    usage = usage_eval(cards, age['chosen'], age, coef)
    usage['regression'] = {'attrs': coef, 'rows': n_usage,
                           'model': 'x = intercept + slopeU*u + position fixed effects (2022-25 full cards)'}
    write_json(FIT / 'usage.json', usage)
    print(json.dumps({'usageChosen': usage['chosen']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
