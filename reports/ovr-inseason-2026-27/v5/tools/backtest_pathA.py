"""Path A 回測：A／C3／C4（preregistration-v5 §2–§3、errata-c4 §3–§6、disclosure-pointwise-ovr）。

起點：Y1..Y6、D1..D3（Y0 沒有先驗卡）。新鮮主判定候選 Y3/Y5/Y6，再經 §3.2 門檻（|E|≥3、|E_eff|≥2）
與 §2.1 母體下限（P<200 → 暖身）。D1–D3 只算次要。

1. w_h(N)：每個起點自己的 H（fit_w_grid_v4 的 pair_rows / M_of / choose_tuple，pressure 照 w10>0.10）。
   E_eff = E 中 w 不退化（H 非空）的起點。
2. δ²_h：fit_w_grid_v4.delta2_from_pairs（只用 H(h)）。
3. C3：λ_s(N) 在 E_eff(s) 上挑，N=3/5 用中位絕對誤差、N=10/20 用 MAE，起點等權；平手取小 λ；λ_82=λ_20。
   C4：一個 c 套全部 N，J = 四個 N 的 J_N 平均；平手（≤1e-9）取大 c。
   E_eff 為空時 λ=1、c=1（沒有資訊 → 照公式本身）。
4. 賽中 OVR 一律用 pointwise_pipeline（A 與原管線相同）；答案卡照 pathA_common.target_ovr。
5. Bootstrap：C3、C4 各一個 rng（seed 20261027），起點照鏈順序、N 由小到大，每格都抽。
輸出 v5/pathA/backtest/{fit.json, results.csv, results.json, report-*.csv, predictions-<start>.csv}。
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pathA_common as PA  # noqa: E402
from pathA_common import base as C  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402
import v2_common as V2  # noqa: E402
import c4_v5 as K  # noqa: E402
import pointwise_pipeline as PW  # noqa: E402
import v5_common as V5C  # noqa: E402
from ovr_common import ATTRS  # noqa: E402

SEED = 20261027
BOOT = 2000
TIE = 1e-9
N_LIST = [3, 5, 10, 20, 82]
N_SEL = [3, 5, 10, 20]
N_FIT = {82: 20}
LAMS = [round(0.05 * k, 2) for k in range(21)]
C_GRID = K.C_GRID
STARTS = PA.BUILT
OUT = PA.PA_BACKTEST


def fit_n(N):
    return N_FIT.get(N, N)


# ---------------------------------------------------------------- 1. w-grid
_ROWS = {}


def rows_h(h, a, N):
    key = (h, a, N)
    if key not in _ROWS:
        saved = C.history_for_attr
        C.history_for_attr = lambda s, at: [h]
        try:
            _ROWS[key] = F.pair_rows(None, a, N)
        finally:
            C.history_for_attr = saved
    return _ROWS[key]


def fit_w(s):
    ent = {'attrs': {}}
    for a in C.UPD:
        hs = C.history_for_attr(s, a)
        e = {'history': hs}
        if not hs:
            e['w'] = {N: 0.0 for N in N_SEL}
            e['note'] = 'H empty -> 0'
            if a == 'pressure':
                e['pressureOpen'] = False
            ent['attrs'][a] = e
            continue
        ms = {}
        for N in N_SEL:
            rows = [r for h in hs for r in rows_h(h, a, N)]
            ms[N] = {w: F.M_of(rows, a, w) for w in F.GRID}
            e.setdefault('pairs', {})[N] = len(rows)
        if all(v is None for v in ms[3].values()):
            e['w'] = {N: 0.0 for N in N_SEL}
            e['note'] = 'no pairs -> 0'
            if a == 'pressure':
                e['pressureOpen'] = False
            ent['attrs'][a] = e
            continue
        ws, obj = F.choose_tuple(ms)
        e['w'] = {N: ws[i] for i, N in enumerate(N_SEL)}
        e['objective'] = obj
        if a == 'pressure':
            e['pressureOpen'] = bool(ws[2] > 0.10)
            if not e['pressureOpen']:
                e['w'] = {N: 0.0 for N in N_SEL}
        ent['attrs'][a] = e
    ent['nonDegenerate'] = any(ent['attrs'][a].get('history') for a in C.UPD)
    ent['pressureOpen'] = ent['attrs']['pressure'].get('pressureOpen', False)
    ent['wg'] = {a: {N: ent['attrs'][a]['w'][fit_n(N)] for N in N_LIST} for a in C.UPD}
    return ent


# ---------------------------------------------------------------- 2. 預測與誤差
def errors(pred, tgt, P):
    return np.array([pred[p]['ovr'] - tgt[p] for p in P], float)


def stat(e, N):
    a = np.abs(e)
    return float(np.median(a)) if N in (3, 5) else float(np.mean(a))


def metrics(e):
    a = np.abs(e)
    return {'medianAbs': float(np.median(a)), 'MAE': float(np.mean(a)),
            'signedMedian': float(np.median(e)), 'gt10': int(np.sum(a > 10))}


def argmin_key(J, grid, prefer_small):
    best = None
    for g in grid:
        v = J[g]
        if best is None or v < best[1] - TIE or (abs(v - best[1]) <= TIE and
                                                   ((g < best[0]) if prefer_small else (g > best[0]))):
            best = (g, v)
    return best[0]


def plateau(J, grid, pick, log=False):
    jmin = J[pick]
    i = grid.index(pick)
    lo = hi = i
    while lo - 1 >= 0 and J[grid[lo - 1]] <= jmin * 1.01 + TIE:
        lo -= 1
    while hi + 1 < len(grid) and J[grid[hi + 1]] <= jmin * 1.01 + TIE:
        hi += 1
    if log:
        return math.log2(grid[hi] / grid[lo])
    return grid[hi] - grid[lo]


def boot(rng, eA, eC):
    n = len(eA)
    idx = rng.integers(0, n, size=(BOOT, n))
    T = np.median(eC[idx], axis=1) - np.median(eA[idx], axis=1)
    dM = np.abs(eC[idx]).mean(axis=1) - np.abs(eA[idx]).mean(axis=1)
    q = lambda x, p: float(np.quantile(x, p, method='linear'))  # noqa: E731
    return T, {'T_lo': q(T, 0.025), 'T_hi': q(T, 0.975),
               'dMAE_lo': q(dM, 0.025), 'dMAE_hi': q(dM, 0.975)}


def target_attrs(start):
    if start.startswith('Y'):
        path = PA.answer_card_path(start)
    else:
        path = V5C.ANS_CARD.get(start)
        if path is None:
            return None
    rows = C.load_csv(path)
    if not rows or any(a not in rows[0] for a in ATTRS):
        return None
    return {int(r['playerId']): {a: float(r[a]) for a in ATTRS} for r in rows}


def main():
    PA.install()
    OUT.mkdir(parents=True, exist_ok=True)
    rel = V2.load_reliability()

    # 1–2. 每個起點的 w、δ²
    fit = {}
    for s in STARTS:
        fit[s] = fit_w(s)
        d2, und, raw = K.delta2_info(s)
        fit[s].update({'delta2': d2, 'undefined': und, 'delta2Raw': raw})
        print('fit', s, 'nonDeg', fit[s]['nonDegenerate'], 'pressureOpen', fit[s]['pressureOpen'],
              'undef', und, flush=True)

    # 各起點的候選網格預測
    tg, pops, E = {}, {}, {}
    for h in STARTS:
        tg[h] = PA.target_ovr(h)
        pw = PW.for_start(C, h)
        prior = C.CHAIN[h]['prior']
        pops[h] = {N: [p for p in C.population(prior, N) if p in tg[h]] for N in N_LIST}
        frozen = [] if fit[h]['pressureOpen'] else ['pressure']
        E[h] = {'A': {N: errors(pw.ref, tg[h], pops[h][N]) for N in N_LIST}, 'C3': {}, 'C4': {}, 'B': {}}
        for N in N_LIST:
            P = pops[h][N]
            E[h]['B'][N] = errors(pw.predict(F.raw_predict(h, N)), tg[h], P)
            for lam in LAMS:
                E[h]['C3'][(lam, N)] = errors(pw.predict(F.c1_predict(h, N, fit[h]['wg'], lam)), tg[h], P)
            for c in C_GRID:
                E[h]['C4'][(c, N)] = errors(pw.predict(K.c4_predict(
                    h, N, fit[h]['delta2'], rel, c, fit[h]['undefined'], frozen)), tg[h], P)
        print('grid', h, {N: len(pops[h][N]) for N in N_LIST}, flush=True)

    # 3. λ、c 的選擇與穩定度
    sel = {}
    for s in STARTS:
        Es = PA.E_of(s)
        Eeff = [h for h in Es if h in STARTS and fit[h]['nonDegenerate']]
        rec = {'E': Es, 'Eeff': Eeff, 'lambda': {}, 'Jlambda': {}, 'lambdaStability': {},
               'lambdaSensitivity': {}}

        def pick_lam(hs, N, obj_n=None, pooled=False):
            on = obj_n or N
            if pooled:
                J = {l: stat(np.concatenate([E[h]['C3'][(l, N)] for h in hs]), on) for l in LAMS}
            else:
                J = {l: float(np.mean([stat(E[h]['C3'][(l, N)], on) for h in hs])) for l in LAMS}
            return argmin_key(J, LAMS, True), J

        def pick_c(hs):
            J = {c: float(np.mean([np.mean([stat(E[h]['C4'][(c, N)], N) for h in hs]) for N in N_SEL]))
                 for c in C_GRID}
            return argmin_key(J, C_GRID, False), J

        for N in N_SEL:
            if not Eeff:
                rec['lambda'][N] = 1.0
                continue
            lam, J = pick_lam(Eeff, N)
            rec['lambda'][N] = lam
            rec['Jlambda'][N] = J
            loo = [abs(pick_lam([h for h in Eeff if h != x], N)[0] - lam) for x in Eeff] if len(Eeff) > 1 else []
            swap = pick_lam(Eeff, N, obj_n=10 if N in (3, 5) else 3)[0]
            pooled = pick_lam(Eeff, N, pooled=True)[0]
            pw_ = plateau(J, LAMS, lam)
            rec['lambdaStability'][N] = {'plateau': pw_, 'looMaxChange': max(loo) if loo else None,
                                         'swapObjective': swap, 'swapDiff': abs(swap - lam),
                                         'unstable': bool(pw_ > 0.30 or (loo and max(loo) > 0.30))}
            rec['lambdaSensitivity'][N] = {'pooledPlayers': pooled, 'swappedObjective': swap}
        rec['lambda'][82] = rec['lambda'][20]
        if Eeff:
            c, Jc = pick_c(Eeff)
            loo = [abs(math.log2(pick_c([h for h in Eeff if h != x])[0] / c)) for x in Eeff] if len(Eeff) > 1 else []
            rec.update({'c': c, 'Jc': Jc, 'cStability': {
                'plateauLog2': plateau(Jc, C_GRID, c, log=True),
                'looMaxLog2Change': max(loo) if loo else None}})
        else:
            rec.update({'c': 1.0, 'Jc': None, 'cStability': None, 'cNote': 'E_eff empty -> c=1'})
        P_ok = all(len(pops[s][N]) >= 200 for N in N_SEL)
        rec['judgeCandidate'] = bool(PA.CHAIN_U[s].get('judge'))
        rec['judged'] = bool(rec['judgeCandidate'] and len(Es) >= 3 and len(Eeff) >= 2 and P_ok)
        rec['P_ok'] = P_ok
        if rec['judgeCandidate'] and not rec['judged']:
            rec['downgrade'] = f'|E|={len(Es)}, |E_eff|={len(Eeff)}, P>=200: {P_ok}'
        sel[s] = rec
        print('sel', s, 'Eeff', Eeff, 'lam', rec['lambda'], 'c', rec['c'], 'judged', rec['judged'], flush=True)

    # 4. 選定參數下的逐格指標與 bootstrap
    rng = {'C3': np.random.default_rng(SEED), 'C4': np.random.default_rng(SEED)}
    results, Tb = [], {}
    for s in STARTS:
        for N in N_LIST:
            eA = E[s]['A'][N]
            eC = {'B': E[s]['B'][N], 'C3': E[s]['C3'][(sel[s]['lambda'][N], N)],
                  'C4': E[s]['C4'][(sel[s]['c'], N)]}
            r = {'start': s, 'N': N, 'P': len(eA), 'judged': sel[s]['judged'],
                 'role': ('fresh' if sel[s]['judged'] else
                          ('fresh-downgraded' if sel[s]['judgeCandidate'] else
                           ('secondary' if s.startswith('D') else 'warmup'))),
                 'lambda': sel[s]['lambda'][N], 'c': sel[s]['c']}
            mA = metrics(eA)
            r.update({f'{k}_A': v for k, v in mA.items()})
            for key, e in eC.items():
                m = metrics(e)
                r.update({f'{k}_{key}': v for k, v in m.items()})
                if key == 'B':
                    continue
                r[f'T_{key}'] = m['signedMedian'] - mA['signedMedian']
                r[f'dMAE_{key}'] = m['MAE'] - mA['MAE']
                T, b = boot(rng[key], eA, e)
                Tb[(key, s, N)] = T
                r.update({f'{k}_{key}': v for k, v in b.items()})
            results.append(r)

    # 閘門
    def verdict(key, starts):
        out = {'starts': starts, 'V1': {}, 'V2': {}}
        if not starts:
            out['pass'] = None
            out['note'] = '從缺（沒有新鮮主判定起點）'
            return out
        for N in (3, 5):
            Tbar = np.mean([Tb[(key, s, N)] for s in starts], axis=0)
            U = float(np.quantile(Tbar, 0.975, method='linear'))
            Ts = {s: next(r[f'T_{key}'] for r in results if r['start'] == s and r['N'] == N) for s in starts}
            out['V1'][N] = {'U_pool': U, 'T_s': Ts,
                            'pass': bool(U <= 0.50 and all(t <= 0.25 for t in Ts.values()))}
        for N in (10, 20):
            cells = {}
            for s in starts:
                r = next(x for x in results if x['start'] == s and x['N'] == N)
                ok = r[f'dMAE_{key}'] < 0 and r[f'gt10_{key}'] <= r['gt10_A']
                cells[s] = {'dMAE': r[f'dMAE_{key}'], 'gt10C': r[f'gt10_{key}'], 'gt10A': r['gt10_A'],
                            'ciHi': r[f'dMAE_hi_{key}'], 'pass': bool(ok),
                            'strength': ('強' if r[f'dMAE_hi_{key}'] < 0 else '方向一致') if ok else '不過',
                            'material': bool(abs(r[f'dMAE_{key}']) >= 0.10)}
            out['V2'][N] = {'cells': cells, 'pass': all(c['pass'] for c in cells.values())}
        out['pass'] = bool(all(v['pass'] for v in out['V1'].values()) and
                           all(v['pass'] for v in out['V2'].values()))
        return out

    fresh = [s for s in STARTS if sel[s]['judged']]
    fresh_plus = [s for s in STARTS if sel[s]['judgeCandidate']]
    secondary = [s for s in STARTS if s.startswith('D')]
    gates = {key: {'main': verdict(key, fresh),
                   'sensitivityAllCandidates': verdict(key, fresh_plus),
                   'secondaryD': verdict(key, secondary)} for key in ('C3', 'C4')}
    c4ok, c3ok = gates['C4']['main']['pass'], gates['C3']['main']['pass']
    final = ('C4' if c4ok else 'C3' if c3ok else 'A') if fresh else '從缺→A'

    # 5. errata §5 報告
    mono, n82, mins = [], [], []
    rank_starts = fresh_plus + secondary
    for s in rank_starts:
        for key in ('A', 'C3', 'C4'):
            seq = [next(r for r in results if r['start'] == s and r['N'] == N)[f'MAE_{key}'] for N in N_LIST]
            row = {'start': s, 'cand': key, **{f'MAE_N{N}': v for N, v in zip(N_LIST, seq)}}
            if key == 'C4':
                rises = [(N_LIST[i], N_LIST[i + 1], seq[i + 1] - seq[i]) for i in range(len(seq) - 1)
                         if seq[i + 1] - seq[i] > 0.10]
                row['nonMonotone'] = bool(rises)
                det = []
                for n1, n2, d in rises:
                    P1, P2 = pops[s][n1], pops[s][n2]
                    e1 = dict(zip(P1, np.abs(E[s]['C4'][(sel[s]['c'], n1)])))
                    e2 = dict(zip(P2, np.abs(E[s]['C4'][(sel[s]['c'], n2)])))
                    both = [(e2[p] - e1[p], p) for p in P2 if p in e1]
                    top = sorted(both, reverse=True)[:5]
                    cards_s = F.load_prior(C.CHAIN[s]['prior'])[0]
                    names = {q: cards_s[q].get('name', '') for q in cards_s}
                    det.append({'from': n1, 'to': n2, 'rise': d, 'P_from': len(P1), 'P_to': len(P2),
                                'newPlayers': len([p for p in P2 if p not in e1]),
                                'top': [{'pid': p, 'name': names.get(p, ''), 'absErrRise': x} for x, p in top]})
                row['rises'] = det
            mono.append(row)

        ta = target_attrs(s)
        if ta is not None:
            pw = PW.for_start(C, s)
            frozen = [] if fit[s]['pressureOpen'] else ['pressure']
            a82 = K.c4_predict(s, 82, fit[s]['delta2'], rel, sel[s]['c'], fit[s]['undefined'], frozen)
            P = [p for p in pops[s][82] if p in ta]
            upd = set(C.UPD)
            vers = {
                'C4': a82,
                'swapUpdatable': {p: {a: (ta[p][a] if (p in ta and a in upd) else a82[p][a]) for a in ATTRS} for p in a82},
                'swapFrozen': {p: {a: (ta[p][a] if (p in ta and a not in upd) else a82[p][a]) for a in ATTRS} for p in a82},
                'swapAll': {p: (ta[p] if p in ta else a82[p]) for p in a82},
            }
            row = {'start': s, 'P': len(P)}
            for k, a in vers.items():
                e = errors(pw.predict(a), tg[s], P)
                row[f'MAE_{k}'] = float(np.mean(np.abs(e)))
                row[f'medianAbs_{k}'] = float(np.median(np.abs(e)))
            n82.append(row)

        for N in N_LIST:
            w, _ = F.windows_of(C.CHAIN[s]['prior'], N)
            P = pops[s][N]
            mpg = np.array([w[p]['MIN'] / max(w[p]['GP'], 1) for p in P])
            grp = {'<15': mpg < 15, '15-28': (mpg >= 15) & (mpg < 28), '>=28': mpg >= 28}
            for g, m in grp.items():
                row = {'start': s, 'N': N, 'group': g, 'n': int(m.sum())}
                for key, e in (('A', E[s]['A'][N]), ('C3', E[s]['C3'][(sel[s]['lambda'][N], N)]),
                               ('C4', E[s]['C4'][(sel[s]['c'], N)])):
                    row[f'MAE_{key}'] = float(np.mean(np.abs(e[m]))) if m.any() else None
                mins.append(row)

    # 預測檔
    for s in STARTS:
        rows = []
        for N in N_LIST:
            P = pops[s][N]
            for i, p in enumerate(P):
                rows.append({'N': N, 'playerId': p, 'target': round(tg[s][p], 4),
                             'A': round(tg[s][p] + E[s]['A'][N][i], 4),
                             'B': round(tg[s][p] + E[s]['B'][N][i], 4),
                             'C3': round(tg[s][p] + E[s]['C3'][(sel[s]['lambda'][N], N)][i], 4),
                             'C4': round(tg[s][p] + E[s]['C4'][(sel[s]['c'], N)][i], 4)})
        C.write_csv(OUT / f'predictions-{s}.csv', rows, head=['N', 'playerId', 'target', 'A', 'B', 'C3', 'C4'])

    rnd = lambda v: round(v, 6) if isinstance(v, float) else v  # noqa: E731
    C.write_csv(OUT / 'results.csv', [{k: rnd(v) for k, v in r.items()} for r in results])
    C.write_csv(OUT / 'report-monotone.csv', [{k: rnd(v) for k, v in r.items() if k != 'rises'} for r in mono])
    C.write_csv(OUT / 'report-n82.csv', [{k: rnd(v) for k, v in r.items()} for r in n82])
    C.write_csv(OUT / 'report-minutes.csv', [{k: rnd(v) for k, v in r.items()} for r in mins])

    def jsonable(o):
        if isinstance(o, dict):
            return {str(k): jsonable(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [jsonable(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return round(float(o), 6)
        if isinstance(o, np.integer):
            return int(o)
        return o

    fit_out = {s: {k: v for k, v in fit[s].items() if k != 'delta2Raw'} for s in STARTS}
    for s in STARTS:
        fit_out[s]['delta2Raw'] = fit[s]['delta2Raw']
    C.write_json(OUT / 'fit.json', jsonable({'fit': fit_out, 'selection': sel}))
    C.write_json(OUT / 'results.json', jsonable({
        'spec': 'preregistration-v5 §2–§3 + errata-c4 + disclosure-pointwise-ovr',
        'seed': SEED, 'boot': BOOT, 'fresh': fresh, 'freshCandidates': fresh_plus,
        'gates': gates, 'final': final, 'monotone': mono, 'n82': n82,
        'pathAFiles': {'equiv': 'v5/pathA/backtest/c4-equiv.json'},
    }))
    print(json.dumps(jsonable({'fresh': fresh, 'final': final,
                               'C4': {k: gates['C4']['main'].get(k) for k in ('pass', 'V1', 'V2')},
                               'C3': {k: gates['C3']['main'].get(k) for k in ('pass', 'V1', 'V2')}}),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
