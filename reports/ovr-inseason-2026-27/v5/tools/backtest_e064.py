"""E-064 賽中端：OVR 改為每場影響力（含上場時間）。預註冊：
reports/card-0.1.2+E064-pergame/preregistration.md §2、§4（sha256 c86a2811...）。

不改既有檔。管線照 E-033（backtest_pathA.py）：fit_w / delta2_info / c4_predict / PointwisePipeline 原樣呼叫；
每場版只是對 PointwisePipeline.predict()['pred'] 乘 MPG_hat/36 後用每場錨點映射（後處理）。

模式
  off  每 36 OVR（E-033 原樣）→ 對照 predictions-Y5/Y6.csv 的 A、B、C4、target（判定 0）
  A    先驗卡每場版  pred_ref × MPG0 / 36
  G0   MPG0（不更新），stamina 能力值照現行（最低樣本 5）
  G5   MPG0 + w(MPG_win − MPG0)，最低樣本 5
  G1   同上，最低樣本 1（stamina 能力值也改 1 場）
  RA/RG0/RG1  副版（替補水準）：(pred − r_repl) × MPG / 36
c 固定用 E-033 fit.json 各起點選定值（Y3=0.7，其餘 1），不重選。
輸出 v5/pathA/backtest-e064/。
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest_pathA as BP  # noqa: E402
import pathA_common as PA  # noqa: E402
from pathA_common import base as C, SA  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402
import v2_common as V2  # noqa: E402
import c4_v5 as K  # noqa: E402
import pointwise_pipeline as PW  # noqa: E402

ROOT = C.ROOT
OUT = PA.PATHA / 'backtest-e064'
E033 = PA.PATHA / 'backtest'
STARTS = PA.BUILT
N_LIST = BP.N_LIST
N_GRID = [3, 5, 10, 20]
SEED_GATE = 20261027
SEED_G = 1
BOOT = 2000
FROZEN_CARD = ROOT / 'reports/ovr-v58-card-2025-26/card-H1-m0'


def q_ref(ref, prc):
    return ref[int(round(prc / 100 * (len(ref) - 1)))]


# ------------------------------------------------------------------ 錨點
def compute_anchors():
    """凍結摘要（v58 H1-m0 的 2025-26 卡）原本算 scaleAnchorsPer36 的池，改用 g 重算（§2）。"""
    rk = C.load_csv(FROZEN_CARD / 'ranking.csv')
    cd, _ = F.load_prior('2025-26')
    byname = {}
    for pid, c in cd.items():
        byname.setdefault(c['name'], []).append(pid)
    pool, miss = [], 0
    for r in rk:
        pids = byname.get(r['name'])
        if not pids:
            miss += 1
            continue
        o = cd[pids[0]]['observed']
        if o['MIN'] >= 500:
            pool.append((float(r['predictedPer36']), o['MIN'] / o['GP']))
    summ = json.load(open(FROZEN_CARD / 'summary.json', encoding='utf-8'))
    pred = sorted(p for p, _ in pool)
    per36 = [q_ref(pred, x) for x in (1, 50, 99)]
    main_g = sorted(p * m / 36 for p, m in pool)
    r_repl = q_ref(pred, 10)
    rep_g = sorted((p - r_repl) * m / 36 for p, m in pool)
    out = {
        'pool': 'ranking.csv(card-H1-m0) predictedPer36 (3位小數) × observed.MIN/GP(F.load_prior 2025-26), MIN>=500',
        'poolN': len(pool), 'unmatchedNames': miss,
        'per36Recomputed': per36, 'per36Frozen': [summ['scaleAnchorsPer36'][k] for k in ('PR1', 'PR50', 'PR99')],
        'main': [q_ref(main_g, x) for x in (1, 50, 99)],
        'repl': [q_ref(rep_g, x) for x in (1, 50, 99)], 'rRepl': r_repl,
        'quantile': 'ref[int(round(prc/100*(len(ref)-1)))] 升冪',
    }
    return out


def map_g(g, a):
    p1, p50, p99 = a
    return 40 + 30 * (g - p1) / (p50 - p1) if g <= p50 else 70 + 29 * (g - p50) / (p99 - p50)


# ------------------------------------------------------------------ 資料
_MPG = {}


def season_mpg(season):
    if season not in _MPG:
        cd, _ = F.load_prior(season)
        _MPG[season] = {pid: (c['observed']['MIN'] / c['observed']['GP'] if c['observed']['GP'] > 0 else 0.0)
                        for pid, c in cd.items()}
    return _MPG[season]


def answer_pred(s):
    """答案卡 pred（映射前）。Y、D1、D2 取答案卡 csv 的 pred 欄；D3 取正式卡 predictedPer36（同 target_ovr 的對名方式）。"""
    if s == 'D3':
        by_name, _ = C.formal_card_ovr()
        cards, _ = C.deployment('D3')
        return {pid: float(by_name[c['name']]['row']['predictedPer36']) for pid, c in cards.items()
                if c['name'] in by_name}
    import v5_common as V5C
    path = PA.answer_card_path(s) if s.startswith('Y') else V5C.ANS_CARD[s]
    return {int(r['playerId']): float(r['pred']) for r in C.load_csv(path)}


def answer_monotone_check(s):
    """答案卡 ovr 是 pred 的單調函數（確認 pred 欄就是映射前的值）。"""
    if s == 'D3':
        return True
    import v5_common as V5C
    path = PA.answer_card_path(s) if s.startswith('Y') else V5C.ANS_CARD[s]
    rows = sorted(((float(r['pred']), float(r['ovr'])) for r in C.load_csv(path)))
    return all(rows[i + 1][1] >= rows[i][1] - 1e-9 for i in range(len(rows) - 1))


def fit_all():
    fit = {}
    for s in STARTS:
        fit[s] = BP.fit_w(s)
        d2, und, raw = K.delta2_info(s)
        fit[s].update({'delta2': d2, 'undefined': und, 'delta2Raw': raw})
        print('fit', s, 'pressureOpen', fit[s]['pressureOpen'], 'undef', und, flush=True)
    return fit


# ------------------------------------------------------------------ 預測
def c4_run(s, N, fit, rel, c, min_stamina):
    frozen = [] if fit[s]['pressureOpen'] else ['pressure']
    old = SA.SEASON_MIN_SAMPLE['stamina']
    SA.SEASON_MIN_SAMPLE['stamina'] = min_stamina
    diag = []
    try:
        attrs = K.c4_predict(s, N, fit[s]['delta2'], rel, c, fit[s]['undefined'], frozen, diag=diag)
    finally:
        SA.SEASON_MIN_SAMPLE['stamina'] = old
    wst = {d['pid']: d['w'] for d in diag if d['attr'] == 'stamina'}
    return attrs, wst


def mpg_hat(mpg0, win, wst, pids, use_w):
    out = {}
    for p in pids:
        m0 = mpg0.get(p, 0.0)
        rec = win.get(p)
        if use_w and p in wst and rec is not None and rec['GP'] > 0:
            out[p] = m0 + wst[p] * (rec['MIN'] / rec['GP'] - m0)
        else:
            out[p] = m0
    return out


def stats(e):
    a = np.abs(e)
    return {'n': int(len(e)), 'MAE': float(a.mean()), 'medianAbs': float(np.median(a)),
            'signedMean': float(e.mean()), 'signedMedian': float(np.median(e)), 'gt10': int(np.sum(a > 10))}


def paired_boot(eG, eB, cells, rng_seed=SEED_G):
    """eG/eB[(s,N)] = 有號誤差陣列（同一 P 順序），cells=[(s,N)...]。
    球員配對：每個起點對「該起點各 N 母體聯集」重抽 BOOT 次（起點照序、同一 rng），格內用重抽權重。
    合併 MAE 差 = 各格 (MAE_G − MAE_B) 的等權平均。回傳點估計與 90% 區間（百分位 5、95）。"""
    rng = np.random.default_rng(rng_seed)
    by_s = {}
    for s, N in cells:
        by_s.setdefault(s, []).append(N)
    diffs = []
    point = []
    for s, Ns in by_s.items():
        univ = sorted(set(p for N in Ns for p in POPS[s][N]))
        pos = {p: i for i, p in enumerate(univ)}
        n = len(univ)
        idx = rng.integers(0, n, size=(BOOT, n))
        cnt = np.zeros((BOOT, n))
        for b in range(BOOT):
            cnt[b] = np.bincount(idx[b], minlength=n)
        for N in Ns:
            ii = np.array([pos[p] for p in POPS[s][N]])
            w = cnt[:, ii]
            d = np.abs(eG[(s, N)]) - np.abs(eB[(s, N)])
            diffs.append((w @ d) / w.sum(axis=1))
            point.append(float(d.mean()))
    D = np.mean(diffs, axis=0)
    return {'point': float(np.mean(point)), 'lo5': float(np.quantile(D, 0.05, method='linear')),
            'hi95': float(np.quantile(D, 0.95, method='linear')), 'cells': len(cells)}


POPS = {}


def main():
    PA.install()
    OUT.mkdir(parents=True, exist_ok=True)
    rel = V2.load_reliability()
    sel = json.load(open(E033 / 'fit.json', encoding='utf-8'))['selection']
    cfix = {s: float(sel[s]['c']) for s in STARTS}
    judged = [s for s in STARTS if sel[s]['judged']]
    print('c', cfix, 'judged', judged, flush=True)

    anc = compute_anchors()
    for k in ('main', 'repl'):
        assert anc[k][0] < anc[k][1] < anc[k][2]
    assert all(abs(a - b) < 1e-3 for a, b in zip(anc['per36Recomputed'], anc['per36Frozen'])), anc
    json.dump(anc, open(OUT / 'anchors.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('anchors', anc, flush=True)
    AM, AR, RREPL = anc['main'], anc['repl'], anc['rRepl']

    import pickle
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if cache and cache.exists():
        fit = pickle.load(open(cache, 'rb'))
    else:
        fit = fit_all()
        if cache:
            pickle.dump(fit, open(cache, 'wb'))

    MODES = ['off', 'A', 'G0', 'G5', 'G1', 'RA', 'RG0', 'RG1']
    E = {m: {} for m in MODES}       # E[m][(s,N)] 有號誤差（對每場答案；off 另對 E-033 每 36 答案）
    E['B36'], E['A36'], E['C4_vs_game'], E['A_vs_game'] = {}, {}, {}, {}
    extra = {}
    pred_rows = {s: [] for s in STARTS}
    for s in STARTS:
        assert answer_monotone_check(s), s
        tg36 = PA.target_ovr(s)
        pw = PW.for_start(C, s)
        prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
        mpg0 = season_mpg(prior)
        mpgT = season_mpg(target)
        ap = answer_pred(s)
        for N in N_LIST:
            POPS.setdefault(s, {})[N] = [p for p in C.population(prior, N) if p in tg36]
        for N in N_LIST:
            P = POPS[s][N]
            miss = [p for p in P if p not in ap or p not in mpgT]
            assert not miss, (s, N, miss[:5])
            tgG = {p: map_g(ap[p] * mpgT[p] / 36, AM) for p in P}
            tgR = {p: map_g((ap[p] - RREPL) * mpgT[p] / 36, AR) for p in P}
            win, _ = F.windows_of(prior, N)
            std, wstd = c4_run(s, N, fit, rel, cfix[s], SA.SEASON_MIN_SAMPLE['stamina'])
            g1, w1 = c4_run(s, N, fit, rel, cfix[s], 1)
            pr_std, pr_g1 = pw.predict(std), pw.predict(g1)
            # off（每 36）
            pr_B = pw.predict(F.raw_predict(s, N))
            E['off'][(s, N)] = np.array([pr_std[p]['ovr'] - tg36[p] for p in P])
            E['B36'][(s, N)] = np.array([pr_B[p]['ovr'] - tg36[p] for p in P])
            E['A36'][(s, N)] = np.array([pw.ref[p]['ovr'] - tg36[p] for p in P])
            E['C4_vs_game'][(s, N)] = np.array([pr_std[p]['ovr'] - tgG[p] for p in P])
            E['A_vs_game'][(s, N)] = np.array([pw.ref[p]['ovr'] - tgG[p] for p in P])
            hat = {'G0': mpg_hat(mpg0, win, wstd, P, False), 'G5': mpg_hat(mpg0, win, wstd, P, True),
                   'G1': mpg_hat(mpg0, win, w1, P, True)}
            prs = {'G0': pr_std, 'G5': pr_std, 'G1': pr_g1}
            predG = {}
            for m in ('G0', 'G5', 'G1'):
                predG[m] = {p: map_g(prs[m][p]['pred'] * hat[m][p] / 36, AM) for p in P}
                E[m][(s, N)] = np.array([predG[m][p] - tgG[p] for p in P])
                if m == 'G5':
                    continue
                predG['R' + m] = {p: map_g((prs[m][p]['pred'] - RREPL) * hat[m][p] / 36, AR) for p in P}
                E['R' + m][(s, N)] = np.array([predG['R' + m][p] - tgR[p] for p in P])
            predG['A'] = {p: map_g(pw.ref[p]['pred'] * mpg0.get(p, 0.0) / 36, AM) for p in P}
            E['A'][(s, N)] = np.array([predG['A'][p] - tgG[p] for p in P])
            predG['RA'] = {p: map_g((pw.ref[p]['pred'] - RREPL) * mpg0.get(p, 0.0) / 36, AR) for p in P}
            E['RA'][(s, N)] = np.array([predG['RA'][p] - tgR[p] for p in P])
            extra[(s, N)] = {'mpg0': np.array([mpg0.get(p, 0.0) for p in P]),
                             'nStaminaUpd5': len(wstd), 'nStaminaUpd1': len(w1)}
            for p in P:
                rec = win.get(p)
                pred_rows[s].append({
                    'N': N, 'playerId': p, 'targetGame': round(tgG[p], 4), 'targetRepl': round(tgR[p], 4),
                    'target36': round(tg36[p], 4),
                    'off': round(pr_std[p]['ovr'], 4), 'A': round(predG['A'][p], 4),
                    'G0': round(predG['G0'][p], 4), 'G5': round(predG['G5'][p], 4), 'G1': round(predG['G1'][p], 4),
                    'RA': round(predG['RA'][p], 4), 'RG1': round(predG['RG1'][p], 4),
                    'mpg0': round(mpg0.get(p, 0.0), 3),
                    'mpgWin': round(rec['MIN'] / rec['GP'], 3) if rec and rec['GP'] > 0 else '',
                    'wStamina5': round(wstd[p], 5) if p in wstd else '',
                    'wStamina1': round(w1[p], 5) if p in w1 else '',
                    'mpgHatG5': round(hat['G5'][p], 3), 'mpgHatG1': round(hat['G1'][p], 3),
                    'mpgTarget': round(mpgT[p], 3)})
        print('cells', s, {N: len(POPS[s][N]) for N in N_LIST},
              'stamina upd N=5 (5g/1g):', extra[(s, 5)]['nStaminaUpd5'], extra[(s, 5)]['nStaminaUpd1'], flush=True)

    # ---------------- (0) 關掉開關重現 E-033
    chk = {}
    for s in ('Y5', 'Y6'):
        ref = {}
        for r in csv.DictReader(open(E033 / f'predictions-{s}.csv', encoding='utf-8')):
            ref[(int(r['N']), int(r['playerId']))] = r
        mx, nmiss, nrows, nexact = 0.0, 0, 0, 0
        for N in N_LIST:
            tg36 = PA.target_ovr(s)
            for i, p in enumerate(POPS[s][N]):
                r = ref.get((N, p))
                if r is None:
                    nmiss += 1
                    continue
                t = tg36[p]
                mine = {'target': t, 'A': t + E['A36'][(s, N)][i], 'B': t + E['B36'][(s, N)][i],
                        'C4': t + E['off'][(s, N)][i]}
                for k, v in mine.items():
                    d = abs(round(v, 4) - float(r[k]))
                    mx = max(mx, d)
                    nexact += d == 0.0
                    nrows += 1
        chk[s] = {'cellsCompared': nrows, 'exactAfterRound4': nexact, 'maxAbsDiffRound4': mx,
                  'rowsNotInE033File': nmiss, 'rowsInE033File': len(ref)}
    chk['pass'] = bool(all(chk[s]['maxAbsDiffRound4'] < 1e-9 and chk[s]['rowsNotInE033File'] == 0
                           and chk[s]['cellsCompared'] == 4 * chk[s]['rowsInE033File'] for s in ('Y5', 'Y6')))
    print('check0', chk, flush=True)

    # ---------------- (1) 原閘門（v5 §2 V1∧V2）對先驗卡每場版 A
    def gate(key, starts):
        rng = np.random.default_rng(SEED_GATE)
        results, Tb = [], {}
        for s in STARTS:
            for N in N_LIST:
                eA, eC = E['A'][(s, N)], E[key][(s, N)]
                mA, mC = BP.metrics(eA), BP.metrics(eC)
                T, b = BP.boot(rng, eA, eC)
                Tb[(s, N)] = T
                results.append({'start': s, 'N': N, 'T': mC['signedMedian'] - mA['signedMedian'],
                                'dMAE': mC['MAE'] - mA['MAE'], 'gt10C': mC['gt10'], 'gt10A': mA['gt10'],
                                'dMAE_hi': b['dMAE_hi'], 'dMAE_lo': b['dMAE_lo']})
        out = {'starts': starts, 'V1': {}, 'V2': {}}
        for N in (3, 5):
            Tbar = np.mean([Tb[(s, N)] for s in starts], axis=0)
            U = float(np.quantile(Tbar, 0.975, method='linear'))
            Ts = {s: next(r['T'] for r in results if r['start'] == s and r['N'] == N) for s in starts}
            out['V1'][N] = {'U_pool': U, 'T_s': Ts, 'pass': bool(U <= 0.50 and all(t <= 0.25 for t in Ts.values()))}
        for N in (10, 20):
            cells = {}
            for s in starts:
                r = next(x for x in results if x['start'] == s and x['N'] == N)
                ok = r['dMAE'] < 0 and r['gt10C'] <= r['gt10A']
                cells[s] = {'dMAE': r['dMAE'], 'gt10C': r['gt10C'], 'gt10A': r['gt10A'], 'ciHi': r['dMAE_hi'],
                            'pass': bool(ok)}
            out['V2'][N] = {'cells': cells, 'pass': all(c['pass'] for c in cells.values())}
        out['pass'] = bool(all(v['pass'] for v in out['V1'].values()) and all(v['pass'] for v in out['V2'].values()))
        return out

    SETS = {'main': ['Y5', 'Y6'], 'Y3': ['Y3'], 'sens': ['Y3', 'Y5', 'Y6'], 'D': ['D1', 'D2', 'D3']}
    gates = {k: {nm: gate(k, ss) for nm, ss in SETS.items()} for k in ('G0', 'G5', 'G1')}
    gatesR = {k: {nm: gate(k, ss) for nm, ss in SETS.items()} for k in ('RG0', 'RG1')}

    # ---------------- (2)(3) G1/G5 對 G0；G1 對 G5
    def cellsof(ss):
        return [(s, N) for s in ss for N in N_GRID]

    def cmp(key, base, ss):
        cells = cellsof(ss)
        d = {f'{s}/N{N}': float(np.abs(E[key][(s, N)]).mean() - np.abs(E[base][(s, N)]).mean()) for s, N in cells}
        return {'cellDiff': d, 'maxCellDiff': max(d.values()), 'pass2': bool(max(d.values()) <= 0.05),
                'boot': paired_boot(E[key], E[base], cells), }

    cmps = {}
    for nm, ss in SETS.items():
        cmps[nm] = {'G1_vs_G0': cmp('G1', 'G0', ss), 'G5_vs_G0': cmp('G5', 'G0', ss), 'G1_vs_G5': cmp('G1', 'G5', ss),
                    'RG1_vs_RG0': cmp('RG1', 'RG0', ss)}
        for k in ('G1_vs_G0', 'G5_vs_G0'):
            cmps[nm][k]['pass3'] = bool(cmps[nm][k]['boot']['hi95'] < 0)

    def passes(key):
        g = gates[key]['main']['pass']
        c = cmps['main'][f'{key}_vs_G0']
        return {'0': chk['pass'], '1': g, '2': c['pass2'], '3': c['pass3'],
                'all': bool(chk['pass'] and g and c['pass2'] and c['pass3'])}

    verdict = {'G1': passes('G1'), 'G5': passes('G5')}
    adopted = 'G1' if verdict['G1']['all'] else 'G5' if verdict['G5']['all'] else 'G0'
    print('verdict', verdict, 'adopted', adopted, flush=True)

    # ---------------- 只報告
    cell_tbl = []
    for s in STARTS:
        for N in N_LIST:
            row = {'start': s, 'N': N, 'P': len(POPS[s][N])}
            for k in ('off', 'A', 'G0', 'G5', 'G1', 'RA', 'RG0', 'RG1', 'C4_vs_game', 'A_vs_game', 'A36', 'B36'):
                st = stats(E[k][(s, N)])
                row.update({f'{kk}_{k}': round(v, 6) if isinstance(v, float) else v for kk, v in st.items()
                            if kk in ('MAE', 'medianAbs', 'signedMean', 'gt10')})
            cell_tbl.append(row)
    ter = []
    for s in STARTS:
        for N in (5, 10):
            m0 = extra[(s, N)]['mpg0']
            lo, hi = np.quantile(m0, [1 / 3, 2 / 3])
            grp = {'low': m0 <= lo, 'mid': (m0 > lo) & (m0 <= hi), 'high': m0 > hi}
            for gname, mask in grp.items():
                row = {'start': s, 'N': N, 'group': gname, 'n': int(mask.sum()),
                       'mpg0_lo': round(float(m0[mask].min()), 2), 'mpg0_hi': round(float(m0[mask].max()), 2)}
                for k in ('A', 'G0', 'G5', 'G1'):
                    e = E[k][(s, N)][mask]
                    row[f'signed_{k}'] = round(float(e.mean()), 4)
                    row[f'MAE_{k}'] = round(float(np.abs(e).mean()), 4)
                ter.append(row)

    def tojson(o):
        if isinstance(o, dict):
            return {str(k): tojson(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [tojson(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return round(float(o), 6)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o

    for s in STARTS:
        C.write_csv(OUT / f'predictions-{s}.csv', pred_rows[s], head=list(pred_rows[s][0].keys()))
    C.write_csv(OUT / 'results.csv', cell_tbl)
    C.write_csv(OUT / 'report-mpg0-tertile.csv', ter)
    ver = {'prereg': 'reports/card-0.1.2+E064-pergame/preregistration.md', 'cFixed': cfix, 'judgedE033': judged,
           'anchors': anc, 'check0': chk, 'gate1': gates, 'gate1Repl': gatesR, 'comparisons': cmps,
           'verdict': verdict, 'adopted': adopted,
           'seeds': {'gate': SEED_GATE, 'G': SEED_G, 'boot': BOOT}}
    json.dump(tojson(ver), open(OUT / 'verdict.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('done', adopted)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
