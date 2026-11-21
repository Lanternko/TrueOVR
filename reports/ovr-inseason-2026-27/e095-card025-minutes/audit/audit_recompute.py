"""E-095 稽核：獨立重算 W 版 8 格 MAE（不 import backtest_e095.py，也不 import 任何專案 py）。

起點只用 E-064 的輸出與原始資料檔：
  v5/pathA/backtest-e064/predictions-{Y5,Y6}.csv（RG1/RA 是 linear 映射後的值）、anchors.json
  v5/pathA/cards/{target}.csv（答案卡 pred）、v5/pathA/data/prior-{season}.json（整季 MIN/GP）
  ovr-v58-card-2025-26/card-H1-m0/ranking.csv + v5/data/prior-2025-26-v5.json（錨點池）
步驟：用 E-064 的 linear 錨點反推 (pred − r_repl) = invmap(RG1) × 36 / mpgHatG1，
      再用 W(m) 與重算的 W 錨點（PR1/50/99，r_repl 仍 −1.813）重新映射，並重算答案卡。
用法：python -I audit_recompute.py   → 寫 audit_recompute.json
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
V5 = HERE.parents[1] / 'v5'
E064 = V5 / 'pathA' / 'backtest-e064'
REPORT = HERE.parent / 'results.json'
CARD_H1 = HERE.parents[2] / 'ovr-v58-card-2025-26' / 'card-H1-m0'
CHAIN = {'Y5': ('2019-20', '2020-21'), 'Y6': ('2020-21', '2021-22')}
N_LIST = [3, 5, 10, 20, 82]
N_GRID = [3, 5, 10, 20]
SEED_GATE, BOOT = 20261027, 2000


def W(m):
    return (1 - math.exp(-m / 15.0)) / (1 - math.exp(-36 / 15.0))


def lin(m):
    return m / 36.0


def q_ref(ref, prc):
    return ref[int(round(prc / 100 * (len(ref) - 1)))]


def map_g(g, a):
    p1, p50, p99 = a
    return 40 + 30 * (g - p1) / (p50 - p1) if g <= p50 else 70 + 29 * (g - p50) / (p99 - p50)


def inv_map(v, a):
    p1, p50, p99 = a
    return p1 + (v - 40) * (p50 - p1) / 30 if v <= 70 else p50 + (v - 70) * (p99 - p50) / 29


def jload(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


# ---------------------------------------------------------------- 錨點池
def pool():
    rk = rows(CARD_H1 / 'ranking.csv')
    cd = {int(c['playerId']): c for c in jload(V5 / 'data' / 'prior-2025-26-v5.json')['players']}
    byname = {}
    for pid, c in cd.items():
        byname.setdefault(c['name'], []).append(pid)
    out = []
    for r in rk:
        pids = byname.get(r['name'])
        if not pids:
            continue
        o = cd[pids[0]]['observed']
        if o['MIN'] >= 500:
            out.append((float(r['predictedPer36']), o['MIN'] / o['GP']))
    return out


def anchors(pl, wf):
    pred = sorted(p for p, _ in pl)
    r = q_ref(pred, 10)
    mg = sorted(p * wf(m) for p, m in pl)
    rg = sorted((p - r) * wf(m) for p, m in pl)
    return {'main': [q_ref(mg, x) for x in (1, 50, 99)], 'repl': [q_ref(rg, x) for x in (1, 50, 99)], 'rRepl': r}


def season_mpg(season):
    d = jload(V5 / 'pathA' / 'data' / f'prior-{season}.json')
    return {int(c['playerId']): (c['observed']['MIN'] / c['observed']['GP'] if c['observed']['GP'] > 0 else 0.0)
            for c in d['players']}


def main():
    out = {}
    pl = pool()
    a064 = jload(E064 / 'anchors.json')
    aL, aW = anchors(pl, lin), anchors(pl, W)
    out['pool'] = {'n': len(pl), 'linRepl': aL['repl'], 'e064Repl': a064['repl'],
                   'linMainMaxDiffVsE064': max(abs(x - y) for x, y in zip(aL['main'], a064['main'])),
                   'linReplMaxDiffVsE064': max(abs(x - y) for x, y in zip(aL['repl'], a064['repl'])),
                   'rRepl': aL['rRepl'], 'e064RRepl': a064['rRepl'], 'W_main': aW['main'], 'W_repl': aW['repl']}
    R = aL['rRepl']
    rep = jload(REPORT)
    out['reportAnchors'] = rep['anchors']['sat15']
    out['anchorMaxDiffVsReport'] = max(abs(x - y) for k in ('main', 'repl') for x, y in
                                       zip(aW[k], rep['anchors']['sat15'][k]))
    out['W_unit'] = {str(m): W(m) for m in (0, 5, 20, 36)}

    data = {}      # (s,N) -> arrays
    chk = {}
    popsize = {}
    for s in ('Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'D1', 'D2', 'D3'):
        r0 = rows(E064 / f'predictions-{s}.csv')
        for N in N_LIST:
            popsize[(s, N)] = sum(1 for r in r0 if int(r['N']) == N)
    for s, (prior, target) in CHAIN.items():
        mT = season_mpg(target)
        ans = {int(r['playerId']): float(r['pred']) for r in rows(V5 / 'pathA' / 'cards' / f'{target}.csv')}
        for N in N_GRID + [82]:
            rr = [r for r in rows(E064 / f'predictions-{s}.csv') if int(r['N']) == N]
            pid = [int(r['playerId']) for r in rr]
            RG1l = np.array([float(r['RG1']) for r in rr])
            RAl = np.array([float(r['RA']) for r in rr])
            tgRl = np.array([float(r['targetRepl']) for r in rr])
            mhat = np.array([float(r['mpgHatG1']) for r in rr])
            m0 = np.array([float(r['mpg0']) for r in rr])
            mt = np.array([mT[p] for p in pid])
            ap = np.array([ans[p] for p in pid])
            # 答案卡自檢：linear 公式重算 targetRepl 應等於 E-064 csv
            tgR_lin = np.array([map_g((a - R) * m / 36, aL['repl']) for a, m in zip(ap, mt)])
            chk[f'{s}/N{N}/targetRepl_linear_vs_e064_maxdiff'] = float(np.abs(tgR_lin - tgRl).max())
            chk[f'{s}/N{N}/mpgTarget_vs_csv_maxdiff'] = float(np.abs(mt - np.array([float(r['mpgTarget']) for r in rr])).max())
            # 反推 (pred - r) 與 (ref - r)
            d_pred = np.array([inv_map(v, aL['repl']) for v in RG1l]) * 36 / np.where(mhat > 0, mhat, 1)
            d_ref = np.array([inv_map(v, aL['repl']) for v in RAl]) * 36 / np.where(m0 > 0, m0, 1)
            # 預測端分鐘：mhat 必須等於 m0 + w*(窗口MPG - m0)（或 m0），不含整季目標分鐘
            win = np.array([float(r['mpgWin']) if r.get('mpgWin') not in (None, '') else np.nan for r in rr]) if 'mpgWin' in rr[0] else None
            data[(s, N)] = dict(pid=pid, d_pred=d_pred, d_ref=d_ref, mhat=mhat, m0=m0, mt=mt, ap=ap,
                                tgRl=tgRl, RG1l=RG1l, RAl=RAl)
    out['answerCardChecks'] = chk
    out['answerCardChecksMax'] = max(v for k, v in chk.items() if k.endswith('targetRepl_linear_vs_e064_maxdiff'))
    out['mpgTargetChecksMax'] = max(v for k, v in chk.items() if k.endswith('mpgTarget_vs_csv_maxdiff'))

    # ---------------- 8 格 MAE
    E = {'W': {}, 'L': {}}
    for (s, N), d in data.items():
        wL = np.array([m / 36 for m in d['mhat']])
        wW = np.array([W(m) for m in d['mhat']])
        tgW = np.array([map_g((a - R) * W(m), aW['repl']) for a, m in zip(d['ap'], d['mt'])])
        rgW = np.array([map_g(dp * w, aW['repl']) for dp, w in zip(d['d_pred'], wW)])
        raW = np.array([map_g(dr * W(m), aW['repl']) for dr, m in zip(d['d_ref'], d['m0'])])
        tgGW = np.array([map_g(a * W(m), aW['main']) for a, m in zip(d['ap'], d['mt'])])
        aW_ = np.array([map_g((dr + R) * W(m), aW['main']) for dr, m in zip(d['d_ref'], d['m0'])])
        E['W'][(s, N)] = {'RG1': rgW - tgW, 'RA': raW - tgW, 'A': aW_ - tgGW}
        E['L'][(s, N)] = {'RG1': d['RG1l'] - d['tgRl'], 'RA': d['RAl'] - d['tgRl']}
    tbl = {}
    for s in ('Y5', 'Y6'):
        for N in N_GRID:
            ml = float(np.abs(E['L'][(s, N)]['RG1']).mean())
            ms = float(np.abs(E['W'][(s, N)]['RG1']).mean())
            c = rep['cmp2']['main']['cells'][f'{s}/N{N}']
            tbl[f'{s}/N{N}'] = {'n': len(E['W'][(s, N)]['RG1']), 'myLinear': ml, 'mySat15': ms, 'myDiff': ms - ml,
                                'repLinear': c['MAE_linear'], 'repSat15': c['MAE_sat15'], 'repDiff': c['diff'],
                                'dLinear': ml - c['MAE_linear'], 'dSat15': ms - c['MAE_sat15'], 'dDiff': (ms - ml) - c['diff']}
    out['mae8'] = tbl
    out['mae8MaxAbsDevFromReport'] = max(max(abs(v['dLinear']), abs(v['dSat15']), abs(v['dDiff'])) for v in tbl.values())
    out['mae8MaxDiff'] = max(v['myDiff'] for v in tbl.values())
    out['mae8AllFailThreshold'] = all(v['myDiff'] > 0.05 for v in tbl.values())

    # ---------------- (1) 閘門 V1/V2（自寫，rng 序照 E-064：STARTS 順序 × N_LIST）
    def gate(base_key, starts=('Y5', 'Y6')):
        rng = np.random.default_rng(SEED_GATE)
        order = ['Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'D1', 'D2', 'D3']
        T, res = {}, {}
        for s in order:
            for N in N_LIST:
                n = popsize[(s, N)]
                idx = rng.integers(0, n, size=(BOOT, n))
                if s in starts and N in N_GRID:
                    eC, eB = E['W'][(s, N)]['RG1'], E['W'][(s, N)][base_key]
                    T[(s, N)] = np.median(eC[idx], axis=1) - np.median(eB[idx], axis=1)
                    res[(s, N)] = {'Tpoint': float(np.median(eC) - np.median(eB)),
                                   'dMAE': float(np.abs(eC).mean() - np.abs(eB).mean()),
                                   'gt10C': int((np.abs(eC) > 10).sum()), 'gt10B': int((np.abs(eB) > 10).sum())}
        g = {'V1': {}, 'V2': {}}
        for N in (3, 5):
            U = float(np.quantile(np.mean([T[(s, N)] for s in starts], axis=0), 0.975, method='linear'))
            Ts = {s: res[(s, N)]['Tpoint'] for s in starts}
            g['V1'][N] = {'U': U, 'T_s': Ts, 'pass': bool(U <= 0.5 and all(t <= 0.25 for t in Ts.values()))}
        for N in (10, 20):
            cells = {s: {**res[(s, N)], 'pass': bool(res[(s, N)]['dMAE'] < 0 and res[(s, N)]['gt10C'] <= res[(s, N)]['gt10B'])}
                     for s in starts}
            g['V2'][N] = {'cells': cells, 'pass': all(c['pass'] for c in cells.values())}
        g['pass'] = bool(all(v['pass'] for v in g['V1'].values()) and all(v['pass'] for v in g['V2'].values()))
        return g

    out['gate_vsRA'] = gate('RA')
    out['gate_vsA_literal'] = gate('A')
    out['reportGateU'] = {m: {N: rep['gates']['sat15']['main'][m]['V1'][str(N)]['U_pool']
                              for N in (3, 5)} for m in ('vsRA', 'vsA_literalE064')}

    def conv(o):
        if isinstance(o, dict):
            return {str(k): conv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [conv(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o

    (HERE / 'audit_recompute.json').write_text(json.dumps(conv(out), ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(conv({k: out[k] for k in ('pool', 'anchorMaxDiffVsReport', 'W_unit', 'answerCardChecksMax',
                                                'mpgTargetChecksMax', 'mae8MaxAbsDevFromReport', 'mae8MaxDiff',
                                                'mae8AllFailThreshold')}), indent=1))
    for k, v in out['mae8'].items():
        print(k, v['n'], f"mine L={v['myLinear']:.4f} S={v['mySat15']:.4f} d={v['myDiff']:+.4f} | rep d={v['repDiff']:+.4f} | dev={v['dDiff']:+.5f}")
    for nm in ('gate_vsRA', 'gate_vsA_literal'):
        g = out[nm]
        print(nm, 'pass', g['pass'], {N: (round(v['U'], 3), v['pass']) for N, v in g['V1'].items()},
              {N: (v['pass'], {s: (round(c['dMAE'], 3), c['gt10C'], c['gt10B']) for s, c in v['cells'].items()}) for N, v in g['V2'].items()})
    print('report U', out['reportGateU'])


if __name__ == '__main__':
    main()
