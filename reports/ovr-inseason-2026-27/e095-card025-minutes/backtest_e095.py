"""E-095 回測：新賽季 OVR 分鐘權重由線性 m/36 改為飽和 W(m)（card 0.2.5，R-047）。預註冊 preregistration.md（sha256 66000292…）。

只 import v5/tools/backtest_e064.py（不改它）。副版 RG1 = map_g((pred_G1 − r_repl) × weight(MPG_hat), 錨點)，
weight = m/36（linear，等於 E-064 的 RG1）或 W(m)（sat15）。答案卡用同一條式子（答案卡 pred、整季 MPG、同一組錨點）。
r_repl 沿用 E-064 回測自己算的 −1.813（錨點池 pred 第 10 百分位）；PR1／50／99 依分鐘模式重算。

流程：u → 線上程式 025 模式輸出的 L1、c0L（讀既有輸出）→ linear 重現 E-064（c0）→ c1（讀 npm test 結果）；前置任一不過就停（exit 3），不算 sat15。
用法：python -I backtest_e095.py [--minutes {both,linear,sat15}] [--cache fit.pkl]
輸出（本資料夾）：results.json、report-details.md、predictions-{linear,sat15}.csv。
"""
import argparse
import csv
import hashlib
import json
import math
import pickle
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / 'v5' / 'tools'
sys.path.insert(0, str(TOOLS))

import numpy as np  # noqa: E402
import backtest_e064 as B  # noqa: E402
import backtest_pathA as BP  # noqa: E402
import pathA_common as PA  # noqa: E402
from pathA_common import base as C, SA  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402
import v2_common as V2  # noqa: E402
import pointwise_pipeline as PW  # noqa: E402

ROOT = B.ROOT
STARTS = B.STARTS
N_LIST = BP.N_LIST
N_GRID = B.N_GRID
SEED_GATE = B.SEED_GATE
E064_OUT = PA.PATHA / 'backtest-e064'
E089 = ROOT / 'reports/card-0.2.4+E089-minutes-saturation/results.json'
LIVE_OUT = HERE
MAIN = ['Y5', 'Y6']
SETS = {'main': ['Y5', 'Y6'], 'Y3': ['Y3'], 'D': ['D1', 'D2', 'D3']}


def sat_w(m):
    return (1.0 - math.exp(-m / 15.0)) / (1.0 - math.exp(-36.0 / 15.0))


def gval(mode, d, m):
    """g = d × weight(m)。linear 照 E-064 的運算順序 d·m/36（逐位元重現）。"""
    return d * m / 36 if mode == 'linear' else d * sat_w(m)


def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


# ------------------------------------------------------------------ 錨點
def pool_pairs():
    """與 backtest_e064.compute_anchors 相同的池：[(predictedPer36, 場均分鐘)]（MIN>=500）。"""
    rk = C.load_csv(B.FROZEN_CARD / 'ranking.csv')
    cd, _ = F.load_prior('2025-26')
    byname = {}
    for pid, c in cd.items():
        byname.setdefault(c['name'], []).append(pid)
    pool = []
    for r in rk:
        pids = byname.get(r['name'])
        if not pids:
            continue
        o = cd[pids[0]]['observed']
        if o['MIN'] >= 500:
            pool.append((float(r['predictedPer36']), o['MIN'] / o['GP']))
    return pool


def anchors_for(mode, pool):
    pred = sorted(p for p, _ in pool)
    r_repl = B.q_ref(pred, 10)
    main_g = sorted(gval(mode, p, m) for p, m in pool)
    rep_g = sorted(gval(mode, p - r_repl, m) for p, m in pool)
    return {'main': [B.q_ref(main_g, x) for x in (1, 50, 99)], 'repl': [B.q_ref(rep_g, x) for x in (1, 50, 99)],
            'rRepl': r_repl}


# ------------------------------------------------------------------ 前置
def check_u():
    exp = {0.0: 0.0, 36.0: 1.0, 5.0: 0.31175, 20.0: 0.80987}
    got = {str(k): sat_w(k) for k in exp}
    diff = {str(k): abs(sat_w(k) - v) for k, v in exp.items()}
    ok = diff['0.0'] < 1e-5 and diff['36.0'] < 1e-5 and diff['5.0'] < 1e-5 and diff['20.0'] < 1e-5
    return {'pass': bool(ok), 'W': got, 'absDiff': diff, 'threshold': '|差| < 1e-5'}


def check_c0L():
    a, b = HERE / 'out-024-before', HERE / 'out-024-after'
    d = {}
    for f in ('ranking.csv', 'no-prior.csv'):
        d[f] = {'before': sha(a / f), 'after': sha(b / f)}
        d[f]['same'] = d[f]['before'] == d[f]['after']
    ma, mb = read_json(a / 'meta.json'), read_json(b / 'meta.json')
    ia = {k: v['sha256'] for k, v in ma['inputs'].items()}
    ib = {k: v['sha256'] for k, v in mb['inputs'].items()}
    d['inputsSame'] = ia == ib
    d['dataCutoff'] = ma['dataCutoff']
    d['runCodeShaBefore'] = (HERE / 'logs' / 'run_c4_live.before.sha256').read_text().split()[0]
    d['runCodeShaAfter'] = sha(ROOT / 'reports/ovr-inseason-2026-27/live/run_c4_live.py')
    d['pass'] = bool(d['ranking.csv']['same'] and d['no-prior.csv']['same'] and d['inputsSame'])
    return d


def check_L1():
    out = HERE / 'out-025'
    meta = read_json(out / 'meta.json')
    new = read_json(E089)['report_only']['card']['new']
    anc_diff = max(abs(x - y) for x, y in zip(meta['e064Anchors'], [new['anchors'][k] for k in ('PR1', 'PR50', 'PR99')]))
    rr_diff = abs(meta['e064RRepl'] - new['r_repl'])
    diffs = []
    for r in rows(out / 'ranking.csv'):
        if r['formalOVR'] != '':
            diffs.append((abs(float(r['lastOVR']) - float(r['formalOVR'])), r['name'], r['lastOVR'], r['formalOVR']))
    diffs.sort(reverse=True)
    mx = diffs[0][0]
    n_gt05 = sum(1 for x in diffs if x[0] > 0.05 + 1e-9)
    return {'pass': bool(mx <= 0.1 + 1e-9 and anc_diff == 0.0 and rr_diff == 0.0 and meta['cardMode'] == '025'),
            'matchedPlayers': len(diffs), 'maxAbsLastOvrVsCard025': mx, 'top3': [list(x) for x in diffs[:3]],
            'nGt0.05': n_gt05, 'anchorsMaxAbsDiffVsE089': anc_diff, 'rReplDiff': rr_diff, 'anchors': meta['e064Anchors'],
            'threshold': '|lastOVR − card 0.2.5 ovr| ≤ 0.1（兩邊都是 1 位小數，容許 1e-9 浮點誤差）；錨點與 E-089 差 0',
            'note': '只能核對有出賽、進 ranking.csv 的球員（ref 只輸出這些人）；lastOVR 已四捨五入到 1 位'}


def check_c1():
    ex = HERE / 'logs' / 'npm-test.exit'
    v = ex.read_text().strip() if ex.exists() else None
    return {'pass': v == '0', 'exit': v}


# ------------------------------------------------------------------ 閘門（v5 §2 V1∧V2，與 E-064 gate() 相同）
def gate(Ec, Eb, starts):
    rng = np.random.default_rng(SEED_GATE)
    results, Tb = [], {}
    for s in STARTS:
        for N in N_LIST:
            eA, eC = Eb[(s, N)], Ec[(s, N)]
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
            cells[s] = {'dMAE': r['dMAE'], 'gt10C': r['gt10C'], 'gt10A': r['gt10A'], 'ciHi': r['dMAE_hi'], 'pass': bool(ok)}
        out['V2'][N] = {'cells': cells, 'pass': all(c['pass'] for c in cells.values())}
    out['pass'] = bool(all(v['pass'] for v in out['V1'].values()) and all(v['pass'] for v in out['V2'].values()))
    return out


def tojson(o):
    if isinstance(o, dict):
        return {str(k): tojson(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [tojson(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return round(float(o), 6)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


# ------------------------------------------------------------------ 線上頁 025 對 024（只報告）
def live_diff():
    a = {r['playerId']: r for r in rows(HERE / 'out-024-after' / 'ranking.csv')}
    b = {r['playerId']: r for r in rows(HERE / 'out-025' / 'ranking.csv')}
    assert set(a) == set(b)
    ids = list(a)
    d = {i: float(b[i]['ovr']) - float(a[i]['ovr']) for i in ids}
    ad = sorted(abs(v) for v in d.values())
    top = lambda t: sorted(t.values(), key=lambda r: int(r['rank']))[:20]  # noqa: E731
    t24, t25 = top(a), top(b)
    n24, n25 = {r['name'] for r in t24}, {r['name'] for r in t25}
    byname24 = {r['name']: r for r in a.values()}
    byname25 = {r['name']: r for r in b.values()}

    def ent(name):
        x, y = byname24[name], byname25[name]
        return {'name': name, 'team': y['team'], 'N': int(y['N']), 'MPGhat': float(y['MPGhat']), 'predNew': float(y['predNew']),
                'ovr024': float(x['ovr']), 'rank024': int(x['rank']), 'ovr025': float(y['ovr']), 'rank025': int(y['rank'])}

    ranked = list(b.values())
    low = sorted([r for r in ranked if float(r['MPGhat']) < 26], key=lambda r: -float(r['predNew']))[:5]
    full = sorted([r for r in ranked if float(r['MPGhat']) >= 32], key=lambda r: -float(a[r['playerId']]['ovr']))[:5]
    caruso = byname25.get('Alex Caruso')
    return {
        'n': len(ids), 'absDeltaMedian': float(np.median(ad)), 'absDeltaMax': ad[-1], 'gt10': sum(1 for x in ad if x > 10),
        'gt5': sum(1 for x in ad if x > 5), 'medianSigned': float(np.median(list(d.values()))),
        'top20_024': [{'rank': int(r['rank']), 'name': r['name'], 'ovr': float(r['ovr'])} for r in t24],
        'top20_025': [{'rank': int(r['rank']), 'name': r['name'], 'ovr': float(r['ovr'])} for r in t25],
        'entered': [ent(n) for n in sorted(n25 - n24, key=lambda n: int(byname25[n]['rank']))],
        'left': [ent(n) for n in sorted(n24 - n25, key=lambda n: int(byname24[n]['rank']))],
        'lowMinutesHighEff': [ent(r['name']) for r in low], 'fullMinutesStarters': [ent(r['name']) for r in full],
        'caruso': ent('Alex Caruso') if caruso else None,
        'rule': '低分鐘高效率＝MPGhat < 26 者中 predNew（用人回歸每 36 預測）最高 5 人；打滿分鐘先發＝MPGhat ≥ 32 者中 024 OVR 最高 5 人（規則在看結果前訂，只報告）'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--minutes', choices=['both', 'linear', 'sat15'], default='both')
    ap.add_argument('--cache', default=str(HERE / 'cache' / 'fit.pkl'))
    args = ap.parse_args()
    modes = ['linear', 'sat15'] if args.minutes == 'both' else [args.minutes]
    PA.install()
    res = {'experiment': 'E-095', 'version': 'inseason 0.2.4a+E095', 'prereg_sha256': sha(HERE / 'preregistration.md'),
           'minutesModes': modes}
    assert res['prereg_sha256'] == '66000292b8f4e4e4c12ea1687147bf9b537ec767a5b9605145ae21367936db71'

    # ---- 前置（不需回測）
    pre = {'u': check_u(), 'c0L': check_c0L(), 'L1': check_L1(), 'c1': check_c1()}
    res['prereq'] = pre
    print({k: v['pass'] for k, v in pre.items()}, flush=True)

    # ---- 資料
    rel = V2.load_reliability()
    sel = json.load(open(B.E033 / 'fit.json', encoding='utf-8'))['selection']
    cfix = {s: float(sel[s]['c']) for s in STARTS}
    cache = Path(args.cache)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        fit = pickle.load(open(cache, 'rb'))
    else:
        fit = B.fit_all()
        pickle.dump(fit, open(cache, 'wb'))
    pool = pool_pairs()
    anc = {m: anchors_for(m, pool) for m in ('linear', 'sat15')}
    RREPL = anc['linear']['rRepl']
    assert anc['sat15']['rRepl'] == RREPL

    # ---- 每格輸入（與模式無關）
    cells = {}
    for s in STARTS:
        assert B.answer_monotone_check(s), s
        pw = PW.for_start(C, s)
        prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
        mpg0, mpgT = B.season_mpg(prior), B.season_mpg(target)
        ap_ = B.answer_pred(s)
        tg36 = PA.target_ovr(s)
        for N in N_LIST:
            B.POPS.setdefault(s, {})[N] = [p for p in C.population(prior, N) if p in tg36]
        for N in N_LIST:
            P = B.POPS[s][N]
            assert not [p for p in P if p not in ap_ or p not in mpgT], (s, N)
            win, _ = F.windows_of(prior, N)
            g1, w1 = B.c4_run(s, N, fit, rel, cfix[s], 1)
            pr = pw.predict(g1)
            hat = B.mpg_hat(mpg0, win, w1, P, True)
            cells[(s, N)] = {'P': P, 'ap': {p: ap_[p] for p in P}, 'mpgT': {p: mpgT[p] for p in P},
                             'mpg0': {p: mpg0.get(p, 0.0) for p in P}, 'hat': hat,
                             'pred': {p: pr[p]['pred'] for p in P}, 'ref': {p: pw.ref[p]['pred'] for p in P}}
        print('cells', s, flush=True)

    def evaluate(mode):
        a = anc[mode]
        AM, AR = a['main'], a['repl']
        E = {k: {} for k in ('RG1', 'RA', 'A')}
        pred_rows = []
        for (s, N), c in cells.items():
            P = c['P']
            tgG = {p: B.map_g(gval(mode, c['ap'][p], c['mpgT'][p]), AM) for p in P}
            tgR = {p: B.map_g(gval(mode, c['ap'][p] - RREPL, c['mpgT'][p]), AR) for p in P}
            rg1 = {p: B.map_g(gval(mode, c['pred'][p] - RREPL, c['hat'][p]), AR) for p in P}
            ra = {p: B.map_g(gval(mode, c['ref'][p] - RREPL, c['mpg0'][p]), AR) for p in P}
            aa = {p: B.map_g(gval(mode, c['ref'][p], c['mpg0'][p]), AM) for p in P}
            E['RG1'][(s, N)] = np.array([rg1[p] - tgR[p] for p in P])
            E['RA'][(s, N)] = np.array([ra[p] - tgR[p] for p in P])
            E['A'][(s, N)] = np.array([aa[p] - tgG[p] for p in P])
            for p in P:
                pred_rows.append({'start': s, 'N': N, 'playerId': p, 'targetGame': round(tgG[p], 4), 'targetRepl': round(tgR[p], 4),
                                  'A': round(aa[p], 4), 'RA': round(ra[p], 4), 'RG1': round(rg1[p], 4),
                                  'mpg0': round(c['mpg0'][p], 3), 'mpgHatG1': round(c['hat'][p], 3), 'mpgTarget': round(c['mpgT'][p], 3)})
        return E, pred_rows

    EV = {}
    EV['linear'], prl = evaluate('linear')

    # ---- (c0) linear 重現 E-064
    a064 = read_json(E064_OUT / 'anchors.json')
    c0 = {'anchorsRepl_equal': anc['linear']['repl'] == a064['repl'], 'anchorsMain_equal': anc['linear']['main'] == a064['main'],
          'rRepl_equal': RREPL == a064['rRepl'], 'rRepl': RREPL, 'anchorsRepl': anc['linear']['repl'], 'perStart': {}}
    byk = {}
    for r in prl:
        byk[(r['start'], r['N'], r['playerId'])] = r
    mx_all, exact_all, n_all = 0.0, 0, 0
    for s in STARTS:
        ref_rows = rows(E064_OUT / f'predictions-{s}.csv')
        mx, ex, n, miss = 0.0, 0, 0, 0
        for r in ref_rows:
            m = byk.get((s, int(r['N']), int(r['playerId'])))
            if m is None:
                miss += 1
                continue
            for k in ('targetGame', 'targetRepl', 'A', 'RA', 'RG1', 'mpg0', 'mpgHatG1', 'mpgTarget'):
                d = abs(float(m[k]) - float(r[k]))
                mx = max(mx, d)
                ex += d == 0.0
                n += 1
        c0['perStart'][s] = {'rowsE064': len(ref_rows), 'rowsMine': sum(1 for k in byk if k[0] == s), 'missing': miss,
                             'cellsCompared': n, 'exact': ex, 'maxAbsDiff': mx}
        mx_all, exact_all, n_all = max(mx_all, mx), exact_all + ex, n_all + n
    c0.update({'maxAbsDiff': mx_all, 'exact': exact_all, 'cellsCompared': n_all})
    c0['pass'] = bool(c0['anchorsRepl_equal'] and c0['rRepl_equal'] and mx_all < 1e-9
                      and all(v['missing'] == 0 and v['rowsE064'] == v['rowsMine'] for v in c0['perStart'].values()))
    c0['note'] = '比對 E-064 predictions-{start}.csv 的 targetGame/targetRepl/A/RA/RG1/mpg 欄（四捨五入 4 位後）與 anchors.json'
    pre['c0'] = c0
    ok = all(pre[k]['pass'] for k in ('u', 'c0L', 'c1', 'L1', 'c0'))
    res['prereqAllPass'] = ok
    print('prereq', {k: v['pass'] for k, v in pre.items()}, flush=True)
    res['anchors'] = anc
    if not ok or args.minutes == 'linear':
        res['judged'] = False
        res['note'] = '前置未全過或只跑 linear：不算 sat15、不看 (1)(2)' if not ok else '只跑 linear'
        (HERE / 'results.json').write_text(json.dumps(tojson(res), ensure_ascii=False, indent=1), encoding='utf-8')
        return 0 if ok else 3

    EV['sat15'], prs = evaluate('sat15')
    for m, pr_rows in (('linear', prl), ('sat15', prs)):
        with open(HERE / f'predictions-{m}.csv', 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(pr_rows[0].keys()))
            w.writeheader()
            w.writerows(pr_rows)

    # ---- (1) 閘門：RG1-sat15 對 W 答案卡。主基準＝同一尺度的先驗卡 RA；另列 E-064 gate1Repl 的字面寫法（基準 A）
    gates = {'sat15': {}, 'linear': {}}
    for m in ('sat15', 'linear'):
        for nm, ss in SETS.items():
            gates[m][nm] = {'vsRA': gate(EV[m]['RG1'], EV[m]['RA'], ss), 'vsA_literalE064': gate(EV[m]['RG1'], EV[m]['A'], ss)}
    # ---- (2) 8 格 MAE 差
    def mae(E, k, c):
        return float(np.abs(E[k][c]).mean())

    def cmp_cells(ss):
        out = {}
        for s in ss:
            for N in N_GRID:
                c = (s, N)
                ml, ms = mae(EV['linear'], 'RG1', c), mae(EV['sat15'], 'RG1', c)
                out[f'{s}/N{N}'] = {'n': len(B.POPS[s][N]), 'MAE_linear': ml, 'MAE_sat15': ms, 'diff': ms - ml,
                                    'signed_linear': float(EV['linear']['RG1'][c].mean()), 'signed_sat15': float(EV['sat15']['RG1'][c].mean())}
        mxd = max(v['diff'] for v in out.values())
        cl = [(s, N) for s in ss for N in N_GRID]
        return {'cells': out, 'maxDiff': mxd, 'pass2': bool(mxd <= 0.05),
                'boot': B.paired_boot(EV['sat15']['RG1'], EV['linear']['RG1'], cl)}
    cmp2 = {nm: cmp_cells(ss) for nm, ss in SETS.items()}
    g1 = gates['sat15']['main']['vsRA']['pass']
    g1_lit = gates['sat15']['main']['vsA_literalE064']['pass']
    res['judged'] = True
    res['verdict'] = {'1': g1, '1_literalE064Baseline': g1_lit, '2': cmp2['main']['pass2'],
                      'outcome': ('(1)(2) 都過' if g1 and cmp2['main']['pass2'] else '(1) 過、(2) 不過' if g1 else '(1) 不過'),
                      'baselineNote': '(1) 主判定用同尺度先驗卡 RA 當 V1/V2 的基準（RG1 與 RA 都對同一答案卡 targetRepl）；E-064 gate1Repl 沿用 non-repl A，另列'}
    res['gates'] = gates
    res['cmp2'] = cmp2

    # ---- 只報告：MPG0 三分位（各起點自己的三分位），N=5、10
    ter = []
    for s in MAIN:
        for N in (5, 10):
            m0 = np.array([cells[(s, N)]['mpg0'][p] for p in cells[(s, N)]['P']])
            lo, hi = np.quantile(m0, [1 / 3, 2 / 3])
            for g, mask in (('low', m0 <= lo), ('mid', (m0 > lo) & (m0 <= hi)), ('high', m0 > hi)):
                row = {'start': s, 'N': N, 'group': g, 'n': int(mask.sum()), 'mpg0_lo': float(m0[mask].min()), 'mpg0_hi': float(m0[mask].max())}
                for m in ('linear', 'sat15'):
                    e = EV[m]['RG1'][(s, N)][mask]
                    row[f'signed_{m}'] = float(e.mean())
                    row[f'MAE_{m}'] = float(np.abs(e).mean())
                ter.append(row)
    res['tertile'] = ter
    res['live'] = live_diff()
    (HERE / 'results.json').write_text(json.dumps(tojson(res), ensure_ascii=False, indent=1), encoding='utf-8')
    print('verdict', res['verdict'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
