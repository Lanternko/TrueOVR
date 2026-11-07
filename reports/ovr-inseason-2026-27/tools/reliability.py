"""S2：2022-23..2024-25 季內分半信度與 k（preregistration §1.2）。

每個能力值、每季：
  1. 逐球員出賽依 (GAME_DATE, GAME_ID) 排序，奇數場=A、偶數場=B。
  2. 兩半各算原始統計量，用該季全季凍結映射（同一 pool／曲線）轉成能力值 y_A,y_B。
  3. 合格球員＝全季 n 達 §1.1 先驗季最低樣本、且兩半都有出賽；算 Pearson r_half、
     Spearman-Brown r_s=2r/(1+r)。
  4. n_ref＝合格球員全季 n 中位數；k_s=n_ref(1-r_s)/r_s。
  5. k_a=median_s k_s，夾 [0.02·n_ref, 50·n_ref]；r_s<=0.05 的季標記不可更新（k_s=50·n_ref）。
  6. sigma2_s=n_ref·Var(y_A-y_B)/4；sigma2_a=median_s；tau2_a=sigma2_a/k_a。

pressure 的分半沿用 four-factors 自身的 reliability 慣例（全域 game-hash 奇偶），
因為四因子模型是聯盟層級擬合，逐球員奇偶分半需要每人重跑一次模型；
其餘 10 項照 §1.2 的逐球員奇偶分半。此偏離在 backtest/report.md 揭露。

輸出：fit/reliability.csv（每季＋ALL 列）、fit/half-residuals.csv（供 S5 相關矩陣）。
用法：python reports/ovr-inseason-2026-27/tools/reliability.py
"""
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import DATA, FIT, UPDATABLE, attr, percentile, write_json
import season_attrs as SA
import four_factors_2022_25 as FF

N_BOOT_SEED = None  # 無隨機成分
SEASON_FLOOR = 0.05
CLIP_LO, CLIP_HI = 0.02, 50.0
N_OF = {'long': 'fg3a', 'mid': 'midA', 'short': 'shortA', 'ft': 'fta', 'drive': 'fga',
        'tovSkill': 'possDen', 'pass': 'min', 'rebound': 'min', 'stamina': 'gp',
        'creation': 'min', 'pressure': 'defensePossessions'}


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return float('nan')
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def pearson(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) < 3 or a.std() == 0 or b.std() == 0:
        return float('nan')
    return float(np.corrcoef(a, b)[0, 1])


def pressure_season(sd, pool_ids):
    """回傳 (pool 值, 全季 weight, A/B 的 value/weight)。只擬合 tovNonSteal。"""
    rows = list(FF.sides([sd['season']]))
    players = sorted({p for r in rows for p in r[1] + r[2]})
    fit_full, info_full = FF.fit(rows, players, 'tovNonSteal')
    value_full = {p: fit_full[p]['defense'] for p in players}
    weight_full = {p: fit_full[p]['defenseWeight'] for p in players}
    pool = [value_full[p] for p in pool_ids if p in value_full]
    halves = {}
    for h in (0, 1):
        sub = [r for r in rows if FF.fold_of(r[0], 2) == h]
        fit_h, _ = FF.fit(sub, players, 'tovNonSteal')
        halves[h] = {'value': {p: fit_h[p]['defense'] for p in players},
                     'weight': {p: fit_h[p]['defenseWeight'] for p in players}}
    return {'pool': pool, 'weight': weight_full, 'halves': halves,
            'rows': len(rows), 'players': len(players),
            'lambda': info_full['lambda']}


def collect_season(season):
    t0 = time.time()
    sd = SA.load_season(season)
    stats = SA.aggregate(sd)
    raw = SA.raw_with_box(sd, stats)
    mapping = SA.build_mapping(sd, stats, raw)
    full = SA.compute_attrs(sd, stats, mapping)
    halves_map = SA.half_game_sets(sd)
    pr = pressure_season(sd, mapping['pool'])
    pressure_meta = {'lambda': pr['lambda'], 'stintRows': pr['rows'],
                     'players': pr['players'], 'pool': len(pr['pool'])}
    halves = {}
    for H in ('A', 'B'):
        gm = {pid: halves_map[pid][H] for pid in halves_map}
        stats_h = SA.aggregate(sd, gm)
        raw_h = SA.raw_with_box(sd, stats_h, gm)
        # pressure：全域 hash 半
        h = 0 if H == 'A' else 1
        raw_h['pressure'] = {pid: pr['halves'][h]['value'].get(pid, 0.0) for pid in stats_h}
        mapping_h = {**mapping, 'raw': raw_h,
                     'pools': {**mapping['pools'], 'pressure': pr['pool']}}
        cards_h = SA.compute_attrs(sd, stats_h, mapping_h, pressure_raw=raw_h['pressure'])
        for pid in cards_h:
            cards_h[pid]['sample']['defensePossessions'] = pr['halves'][h]['weight'].get(pid, 0.0)
            cards_h[pid]['sample']['pressureFull'] = pr['weight'].get(pid, 0.0)
        halves[H] = cards_h
    out = {'season': season, 'full': full, 'halves': halves, 'nPlayers': len(full),
           'pressure': pressure_meta, 'seconds': round(time.time() - t0, 1)}
    print(json.dumps({'season': season, 'players': len(full), 'seconds': out['seconds'],
                      'pressure': pressure_meta}, ensure_ascii=False), flush=True)
    return out


def main():
    FIT.mkdir(parents=True, exist_ok=True)
    season_rows, all_rows, residual_rows = [], [], []
    for season in SA.SEASONS:
        data = collect_season(season)
        full, A, B = data['full'], data['halves']['A'], data['halves']['B']
        for a in UPDATABLE:
            key = N_OF[a]
            ys = {'A': [], 'B': [], 'full': [], 'resid': []}
            for pid, card in full.items():
                if pid not in A or pid not in B:
                    continue
                n_full = card['sample'].get(key, 0.0)
                if a == 'pressure':
                    n_full = A[pid]['sample'].get('pressureFull', 0.0)
                nA = A[pid]['sample'].get(key, 0.0)
                nB = B[pid]['sample'].get(key, 0.0)
                if n_full < SA.PRIOR_MIN_SAMPLE[a] or nA <= 0 or nB <= 0:
                    continue
                ys['A'].append(A[pid][a])
                ys['B'].append(B[pid][a])
                ys['full'].append(n_full)
                ys['resid'].append(A[pid][a] - B[pid][a])
            r_half = pearson(ys['A'], ys['B'])
            n_ref = median(ys['full'])
            r_s = 2 * r_half / (1 + r_half) if math.isfinite(r_half) and r_half > -1 else float('nan')
            updatable = not (not math.isfinite(r_s) or r_s <= SEASON_FLOOR)
            k_s = (n_ref * (1 - r_s) / r_s) if updatable else (CLIP_HI * n_ref)
            var_d = float(np.var(np.array(ys['resid'], float), ddof=1)) if len(ys['resid']) > 1 else float('nan')
            sigma2 = n_ref * var_d / 4.0 if math.isfinite(var_d) else float('nan')
            season_rows.append({
                'attr': a, 'season': season, 'eligiblePlayers': len(ys['A']),
                'rHalf': round(r_half, 6) if math.isfinite(r_half) else '',
                'rSB': round(r_s, 6) if math.isfinite(r_s) else '',
                'nRef': round(n_ref, 4), 'k': round(k_s, 4) if math.isfinite(k_s) else '',
                'sigma2': round(sigma2, 6) if math.isfinite(sigma2) else '',
                'note': '' if updatable else 'rSB<=0.05 -> k=50*nRef (not updatable)',
            })
            for pid, card in full.items():
                if pid not in A or pid not in B:
                    continue
                n_full = card['sample'].get(key, 0.0)
                if a == 'pressure':
                    n_full = A[pid]['sample'].get('pressureFull', 0.0)
                if n_full < SA.PRIOR_MIN_SAMPLE[a]:
                    continue
                residual_rows.append({'season': season, 'playerId': pid, 'attr': a,
                                      'resid': round(A[pid][a] - B[pid][a], 6)})
        print(json.dumps({'season': season, 'done': True}, ensure_ascii=False), flush=True)

    for a in UPDATABLE:
        rs = [r for r in season_rows if r['attr'] == a and r['rSB'] != '']
        ks = [r['k'] for r in rs]
        s2 = [r['sigma2'] for r in rs if r['sigma2'] != '']
        nrefs = [r['nRef'] for r in rs]
        n_ref_a = median(nrefs)
        k_a = median(ks)
        lo, hi = CLIP_LO * n_ref_a, CLIP_HI * n_ref_a
        k_clip = max(lo, min(hi, k_a))
        sigma2_a = median(s2)
        all_rows.append({
            'attr': a, 'season': '2022-25', 'eligiblePlayers': sum(r['eligiblePlayers'] for r in rs),
            'rSB': round(median([r['rSB'] for r in rs]), 6),
            'nRef': round(n_ref_a, 4), 'k': round(k_clip, 4),
            'kRaw': round(k_a, 4), 'kLo': round(lo, 4), 'kHi': round(hi, 4),
            'sigma2': round(sigma2_a, 6), 'tau2': round(sigma2_a / k_clip, 6),
            'seasonsUsed': len(rs),
            'note': 'k clipped' if abs(k_clip - k_a) > 1e-9 else '',
        })

    fields = ['attr', 'season', 'eligiblePlayers', 'rHalf', 'rSB', 'nRef', 'k', 'sigma2',
              'kRaw', 'kLo', 'kHi', 'tau2', 'seasonsUsed', 'note']
    with open(FIT / 'reliability.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in season_rows + all_rows:
            w.writerow({k: r.get(k, '') for k in fields})
    with open(FIT / 'half-residuals.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['season', 'playerId', 'attr', 'resid'])
        w.writeheader()
        w.writerows(residual_rows)
    summary = {'attrs': len(all_rows),
               'allHaveK': all(r['k'] != '' for r in all_rows),
               'rSBin01': sum(1 for r in all_rows if 0 < r['rSB'] < 1),
               'rows': all_rows}
    write_json(DATA / 'reliability-summary.json', summary)
    print(json.dumps({'allHaveK': summary['allHaveK'], 'rSBin01': summary['rSBin01'],
                      'attrs': [(r['attr'], r['rSB'], r['k'], r['tau2']) for r in all_rows]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
