"""E-307 相鄰季穩定度（prereg §4.1）＋描述表（蓋帽 vs 干擾球、蓋帽後球權去向）。輸出 results/stability.json、results/describe.json。
用法（repo root）：python -I -X utf8 reports/E307-blk-quality/e307_stability.py"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e307_lib as L  # noqa: E402

MIN_BOTH = 500.0
BLK_BOTH = 30


def pearson(x, y):
    return float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pri = json.loads((L.HERE / 'data/priors.json').read_text(encoding='utf-8'))
    SM = {s: L.season_metrics(s, pri) for s in L.FIT}
    pairs = list(zip(L.FIT[:-1], L.FIT[1:]))
    cols_arm = list(L.ARMS)
    cols_comp = ['rRaw', 'rS', 'paRaw', 'paS', 'gsRaw', 'gsS', 'gt36Raw', 'gt36S']
    res = {'perPair': {}, 'pooled': {}, 'n': {}}
    pool_x = {c: [] for c in cols_arm + cols_comp}; pool_y = {c: [] for c in cols_arm + cols_comp}
    for a, b in pairs:
        A, B = SM[a], SM[b]
        both = [p for p in A if p in B and A[p]['min'] >= MIN_BOTH and B[p]['min'] >= MIN_BOTH and 'AE' in A[p] and 'AE' in B[p]]
        bigb = [p for p in both if A[p]['known'] >= BLK_BOTH and B[p]['known'] >= BLK_BOTH]
        pr = {}
        for c in cols_arm + cols_comp:
            ps = bigb if c in ('rRaw', 'rS', 'paRaw', 'paS', 'gsRaw', 'gsS') else both
            x = [A[p][c] for p in ps if A[p][c] is not None and B[p][c] is not None]
            y = [B[p][c] for p in ps if A[p][c] is not None and B[p][c] is not None]
            pr[c] = round(pearson(x, y), 4); pool_x[c] += x; pool_y[c] += y
        res['perPair'][f'{a}->{b}'] = pr
        res['n'][f'{a}->{b}'] = {'min500': len(both), 'blk30': len(bigb)}
    for c in pool_x:
        res['pooled'][c] = round(pearson(pool_x[c], pool_y[c]), 4)
    res['pass'] = {c: bool(res['pooled'][c] >= res['pooled']['A0'] - 0.05) for c in ('AE', 'AG', 'AV')}
    # 同季內：AE 與 A0 的相關（說明新指標和 blk36 有多不同）
    res['withinSeasonCorrWithA0'] = {}
    for c in ('AE', 'AG', 'AV'):
        x, y = [], []
        for s in L.FIT:
            ps = [p for p, d in SM[s].items() if d['min'] >= MIN_BOTH and 'AE' in d]
            x += [SM[s][p]['A0'] for p in ps]; y += [SM[s][p][c] for p in ps]
        res['withinSeasonCorrWithA0'][c] = round(pearson(x, y), 4)
    # 收縮後 retention 的真實離散度（加權 SD）
    res['priors'] = {'k': pri['k'], 'tau2': pri['tau2'], 'trueSD': {k: round(float(np.sqrt(v)), 4) for k, v in pri['tau2'].items()}}
    (L.HERE / 'results').mkdir(exist_ok=True)
    (L.HERE / 'results' / 'stability.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('pooled', 'pass', 'n', 'withinSeasonCorrWithA0')}, ensure_ascii=False, indent=1))

    # ---- 描述表：2025-26 與 2026-27 蓋帽前 20 ----
    desc = {}
    for s in ('2025-26', '2026-27'):
        ev = L.events(s); Lg = pri['league'][s]; k = pri['k']
        top = sorted(ev.items(), key=lambda kv: -kv[1]['blk_pbp'])[:25]
        nm = {}
        for ss in L.FIT:
            for p, (m, b, n) in L.minutes_blk(ss).items():
                nm[p] = n
        rows = []
        for p, e in top:
            rows.append({'pid': p, 'name': nm.get(p, str(p)), 'blk': int(e['blk_pbp']), 'gt': int(e['gt']),
                         'gtShare': round(e['gt'] / (e['blk_pbp'] + e['gt']), 3),
                         'retRaw': round(e['retained'] / e['known'], 3), 'retS': round((e['retained'] + k['k_r'] * Lg['r']) / (e['known'] + k['k_r']), 3),
                         'ptsAfterRaw': round(e['ptsAfter'] / e['known'], 3), 'ptsAfterS': round((e['ptsAfter'] + k['k_pa'] * Lg['pa']) / (e['known'] + k['k_pa']), 3),
                         'effBlk': round(e['retained'], 1)})
        desc[s] = {'league': {kk: round(float(v), 4) for kk, v in Lg.items()}, 'top': rows}
    # 多季合計（2022-23～2025-26）retention 前後段
    tot = {}
    for s in L.FIT[1:]:
        for p, e in L.events(s).items():
            t = tot.setdefault(p, [0, 0, 0, 0])
            t[0] += e['known']; t[1] += e['retained']; t[2] += e['gt']; t[3] += e['ptsAfter']
    nm = {}
    for ss in L.FIT:
        for p, (m, b, n) in L.minutes_blk(ss).items():
            nm[p] = n
    big = [(nm.get(p, p), t[0], round(t[1] / t[0], 3), t[2], round(t[3] / t[0], 3)) for p, t in tot.items() if t[0] >= 300]
    desc['fourSeason300'] = {'byRetention': sorted(big, key=lambda x: -x[2]), 'n': len(big)}
    (L.HERE / 'results' / 'describe.json').write_text(json.dumps(desc, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
