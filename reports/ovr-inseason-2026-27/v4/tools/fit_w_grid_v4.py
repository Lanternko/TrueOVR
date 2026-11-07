"""P3：v4 的 w 網格（C1/C3 的逐項 w）與 C2 的 δ²（preregistration-v4 §2.2）。

與 v3 的差別只有資料層：W-missing 只剩 short/creation（mid 已由座標規則補回），
並多一個起點 S*（H(S*)={W,D1,D2,D3}；它的 xt 是 c_2025-26，只用來擬合 w，不判定）。
每一項：21 點 w、4 個 N 的非遞減 4 元組（1001 組），最小化 ΣM；平手 Σw 小、再字典序。
pressure：w(N=10)>0.10 才開放（v3 §3）。
輸出 v4/fit/w-grid.json、v4/fit/pairs-*.csv。
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
import inseason_common_v4 as IC
import season_attrs_v4 as SA
import v2_common as V2

GRID = [round(0.05 * k, 2) for k in range(21)]
STARTS = C.HIST + ['S*']


def tag(s):
    """檔名用（'*' 在 Windows 檔名不合法）。"""
    return 'Sstar' if s == 'S*' else s
CACHE = {}


def load_prior(season):
    key = ('prior', season)
    if key not in CACHE:
        CACHE[key] = C.load_card(season)
    return CACHE[key]


def windows_of(prior, N):
    key = ('win', prior, N)
    if key not in CACHE:
        CACHE[key] = C.windows(prior, N)
    return CACHE[key]


def y_adj_of(card, w_rec, a, usg):
    x0 = float(card[a])
    if IC.sample_of(w_rec, a) < SA.SEASON_MIN_SAMPLE[a]:
        return x0
    return C.usage_adjust({a: x0}, w_rec, a, usg)


def pair_rows(s, a, N):
    out = []
    for h in C.history_for_attr(s, a):
        prior = C.CHAIN[h]['prior']
        cards, _ = load_prior(prior)
        tgt_cards, _ = load_prior(C.CHAIN[h]['target'])
        usg = C.usg_prior(prior)
        w, _ = windows_of(prior, N)
        for pid, card in cards.items():
            if float(card['observed']['MIN']) < 500:
                continue
            tc = tgt_cards.get(pid)
            if tc is None or float(tc['observed']['MIN']) < 500:
                continue
            rec = w.get(pid)
            if rec is None or rec.get('MIN', 0.0) < 1:
                continue
            out.append({'h': h, 'pid': pid, 'x0': float(card[a]),
                        'y': y_adj_of(card, rec, a, usg.get(pid, 0.0)),
                        'n': IC.sample_of(rec, a), 'xt': float(tc[a])})
    return out


def M_of(rows, a, w):
    ds = []
    for r in rows:
        y = r['x0'] if r['n'] < SA.SEASON_MIN_SAMPLE[a] else r['y']
        ds.append(abs(C.clip(r['x0'] + w * (y - r['x0'])) - r['xt']))
    return float(np.median(ds)) if ds else None


def choose_tuple(ms):
    best = None
    for i in range(21):
        for j in range(i, 21):
            for k in range(j, 21):
                for l in range(k, 21):
                    ws = (GRID[i], GRID[j], GRID[k], GRID[l])
                    obj = sum(ms[n][w] for n, w in zip(C.N_LIST, ws))
                    key = (obj, sum(ws), ws)
                    if best is None or key < best[0]:
                        best = (key, ws, obj)
    return best[1], best[2]


def delta2_from_pairs(s):
    rel = V2.load_reliability()
    out = {}
    for a in C.UPD:
        d, s2 = [], []
        for h in C.history_for_attr(s, a):
            prior = C.CHAIN[h]['prior']
            cards, _ = load_prior(prior)
            tgt_cards, _ = load_prior(C.CHAIN[h]['target'])
            for pid, card in cards.items():
                tc = tgt_cards.get(pid)
                if tc is None:
                    continue
                npv, ntv = V2.sample_n(card, a), V2.sample_n(tc, a)
                if npv < SA.PRIOR_MIN_SAMPLE[a] or ntv < SA.PRIOR_MIN_SAMPLE[a]:
                    continue
                d.append(float(tc[a]) - C.clip(float(card[a])))
                s2.append(rel[a]['sigma2'] * (1.0 / ntv + 1.0 / npv))
        m = len(d)
        var = float(np.var(d, ddof=1)) if m > 1 else 0.0
        mean_s2 = float(np.mean(s2)) if m else 0.0
        out[a] = {'m': m, 'V': round(var, 6), 'meanS2': round(mean_s2, 6),
                  'delta2': round(max(0.0, var - mean_s2), 6), 'defined': m > 1}
    return out


def c2_predict(start, N, delta2, rel, undefined=(), frozen=()):
    prior = C.CHAIN[start]['prior']
    prior_cards, _ = load_prior(prior)
    _, attrs0 = C.deployment(start)
    w, _ = windows_of(prior, N)
    usg = C.usg_prior(prior)
    out = {}
    for pid, x0 in attrs0.items():
        rec = w.get(pid)
        pc = prior_cards.get(pid)
        vals = {}
        for a in C.UPD:
            if pc is None or a in undefined or a in frozen:
                vals[a] = x0[a]
                continue
            if rec is None or IC.sample_of(rec, a) < SA.SEASON_MIN_SAMPLE[a]:
                vals[a] = x0[a]
                continue
            y = y_adj_of(pc, rec, a, usg.get(pid, 0.0))
            n = IC.sample_of(rec, a)
            k = V2.k_eff(delta2[a], rel[a]['sigma2'], V2.sample_n(pc, a), rel[a]['nRef'])
            vals[a] = C.clip((n * y + k * x0[a]) / (n + k))
        out[pid] = {**x0, **vals}
    return out


def c1_predict(start, N, wgrid, lam=1.0):
    """C3 的逐球員屬性；λ=1 即 C1、λ=0 即 A（§2.1）。"""
    prior = C.CHAIN[start]['prior']
    prior_cards, _ = load_prior(prior)
    _, attrs0 = C.deployment(start)
    w, _ = windows_of(prior, N)
    usg = C.usg_prior(prior)
    out = {}
    for pid, x0 in attrs0.items():
        rec = w.get(pid)
        vals = {}
        for a in C.UPD:
            wv = wgrid[a][N]
            if pid not in prior_cards or rec is None or wv == 0 \
                    or IC.sample_of(rec, a) < SA.SEASON_MIN_SAMPLE[a]:
                vals[a] = x0[a]
                continue
            y = y_adj_of(prior_cards[pid], rec, a, usg.get(pid, 0.0))
            vals[a] = C.clip(x0[a] + lam * wv * (y - x0[a]))
        out[pid] = {**x0, **vals}
    return out


def raw_predict(start, N):
    prior = C.CHAIN[start]['prior']
    cards, attrs0 = C.deployment(start)
    w, _ = windows_of(prior, N)
    usg = C.usg_prior(prior)
    out = {}
    for pid, x0 in attrs0.items():
        rec = w.get(pid)
        vals = {}
        for a in C.UPD:
            if rec is None or IC.sample_of(rec, a) < SA.SEASON_MIN_SAMPLE[a]:
                vals[a] = x0[a]
            else:
                vals[a] = C.clip(y_adj_of(cards[pid], rec, a, usg.get(pid, 0.0)))
        out[pid] = {**x0, **vals}
    return out


def target_ovr(start):
    ch = C.CHAIN[start]
    if start == 'D3':
        by_name, _ = C.formal_card_ovr()
        cards, _ = load_prior(ch['prior'])
        return {pid: by_name[c['name']]['ovr'] for pid, c in cards.items() if c['name'] in by_name}
    rows = C.load_csv(C.V4_CARDS / f"{ch['target']}.csv")
    return {int(r['playerId']): float(r['ovr']) for r in rows}


def attrs_of(start, N, wgrid, lam):
    return c1_predict(start, N, wgrid, lam)


def main():
    C.V4_FIT.mkdir(parents=True, exist_ok=True)
    rel = V2.load_reliability()
    drift = V2.load_drift()
    frozen_delta2 = {a: float(v) for a, v in drift['delta2']['D1'].items()}

    grid_out, c2_out, pair_dump = {}, {}, {}
    for s in STARTS:
        pair_dump[s] = []
        grid_out[s] = {'H': C.history(s), 'judge': C.CHAIN[s]['judge'],
                       'attrs': {}, 'wMissing': C.W_MISSING if s != 'W' else {}}
        for a in C.UPD:
            entry = {'history': C.history_for_attr(s, a), 'w': {}, 'M': {}}
            ms = {}
            for N in C.N_LIST:
                rows = pair_rows(s, a, N)
                pair_dump[s].extend({'attr': a, 'N': N, 'h': r['h'], 'playerId': r['pid'],
                                     'x0': r['x0'], 'y': r['y'], 'n': r['n'], 'xt': r['xt']}
                                    for r in rows)
                vals = {w: M_of(rows, a, w) for w in GRID}
                ms[N] = vals
                entry['M'][str(N)] = [None if vals[w] is None else round(vals[w], 6) for w in GRID]
                entry.setdefault('pairCounts', {})[str(N)] = len(rows)
            if all(v is None for v in ms[3].values()):
                entry['w'] = {str(N): 0.0 for N in C.N_LIST}
                entry['note'] = 'H empty after W-missing -> frozen 0'
                grid_out[s]['attrs'][a] = entry
                continue
            ws, obj = choose_tuple(ms)
            entry['w'] = {str(N): ws[i] for i, N in enumerate(C.N_LIST)}
            entry['objective'] = round(obj, 6)
            if a == 'pressure':
                open_ = ws[2] > 0.10
                entry['pressureOpen'] = bool(open_)
                if not open_:
                    entry['w'] = {str(N): 0.0 for N in C.N_LIST}
                    entry['note'] = f'w(N=10)={ws[2]:.2f} <= 0.10 -> pressure frozen 0 (§3)'
            grid_out[s]['attrs'][a] = entry
        if s == 'W':
            c2_out[s] = {'source': 'v2/fit/drift.json D1 (frozen; H(W)=empty)',
                         'attrs': {a: {'delta2': frozen_delta2[a], 'defined': True,
                                       'm': None, 'frozenSource': True} for a in C.UPD}}
        else:
            c2_out[s] = {'source': 'H(s) pairs, v2 §2.2', 'attrs': delta2_from_pairs(s)}
        c2_out[s]['undefinedAttrs'] = sorted(a for a, v in c2_out[s]['attrs'].items()
                                             if not v.get('defined'))
        c2_out[s]['pressureFrozen'] = not grid_out[s]['attrs']['pressure'].get('pressureOpen', False)

    # 各起點 w 的摘要（含 S* 與 D3 的關係）
    wsum = {s: {a: {N: grid_out[s]['attrs'][a]['w'][str(N)] for N in C.N_LIST} for a in C.UPD}
            for s in STARTS}
    diff_d3_s = {a: {N: round(wsum['S*'][a][N] - wsum['D3'][a][N], 6) for N in C.N_LIST}
                 for a in C.UPD}
    out = {
        'spec': 'preregistration-v4 §2.2 / §3 / P3',
        'grid': GRID,
        'nList': C.N_LIST,
        'monotone': 'w3<=w5<=w10<=w20 over 1001 tuples',
        'starts': STARTS,
        'judgeStarts': C.JUDGE,
        'wMissing': C.W_MISSING,
        'w': grid_out,
        'c2': c2_out,
        'wSminusD3': diff_d3_s,
        'pairsCsv': {s: str((C.V4_FIT / f'pairs-{tag(s)}.csv').relative_to(C.ROOT)) for s in STARTS},
        'gridCells': len(STARTS) * len(C.UPD) * len(C.N_LIST) * len(GRID),
    }
    for s in STARTS:
        C.write_csv(C.V4_FIT / f'pairs-{tag(s)}.csv', pair_dump[s],
                    head=['attr', 'N', 'h', 'playerId', 'x0', 'y', 'n', 'xt'])
    C.write_json(C.V4_FIT / 'w-grid.json', out)
    print(json.dumps({
        'gridCells': out['gridCells'],
        'pressure': {s: grid_out[s]['attrs']['pressure'].get('pressureOpen') for s in STARTS},
        'w': {s: {a: [wsum[s][a][N] for N in C.N_LIST] for a in C.UPD
                  if any(wsum[s][a][N] for N in C.N_LIST)} for s in STARTS},
        'pairs': {s: grid_out[s]['attrs']['long']['pairCounts'] for s in STARTS},
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
