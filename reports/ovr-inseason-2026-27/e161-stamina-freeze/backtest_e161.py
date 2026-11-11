"""E-161 回測：新賽季 OVR 上場時間只算一次（R-105）。預註冊 preregistration.md（sha256 5b8a67e9…）。

只 import v5/tools/backtest_e064.py（不改它）。副版、線性分鐘、E-064 錨點與 r_repl 全照 E-064：
  RG1  = map_g((pred_G1  − r_repl) × MPG_hat / 36, 錨點)   能力值含 stamina 1 場更新（E-064 原樣）
  RG1F = map_g((pred_G1F − r_repl) × MPG_hat / 36, 錨點)   stamina 留先驗卡值；MPG_hat 同 RG1（G1 的 stamina w）
答案卡：答案卡 pred、整季 MPG、同一組錨點（E-064 targetRepl）。

流程：c0L、u（讀 out/ 下線上三份輸出）→ c1（讀 npm test 結果）→ RG1 重現 E-064（c0）；前置任一不過就停（exit 3）。
用法：python -I backtest_e161.py [--cache fit.pkl]
輸出（本資料夾）：results.json、predictions.csv。
"""
import argparse
import csv
import hashlib
import json
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
import c4_v5 as K  # noqa: E402
import pointwise_pipeline as PW  # noqa: E402

ROOT = B.ROOT
STARTS = B.STARTS
N_LIST = BP.N_LIST
N_GRID = B.N_GRID
SEED_GATE = B.SEED_GATE
E064_OUT = PA.PATHA / 'backtest-e064'
E095_CACHE = HERE.parent / 'e095-card025-minutes' / 'cache' / 'fit.pkl'
OUT = HERE / 'out'
MAIN = ['Y5', 'Y6']
SETS = {'main': ['Y5', 'Y6'], 'Y3': ['Y3'], 'D': ['D1', 'D2', 'D3']}
PREREG_SHA = '5b8a67e9b7999f6cc4e0ff3a6adb41eabffde5a5da54c9e7d34385e32053f664'
WATCH = ['Jalen Williams', 'Chet Holmgren', 'Nikola Jokić']


def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


# ------------------------------------------------------------------ 前置
def check_c0L():
    """out/orig＝改程式前、out/def＝改程式後預設（同一份資料），ranking／no-prior 逐位元相同；meta 以 JSON 比（dict 順序不定）。"""
    a, b = OUT / 'orig', OUT / 'def'
    d = {f: sha(a / f) == sha(b / f) for f in ('ranking.csv', 'no-prior.csv', 'README.md')}
    d['metaJsonEqual'] = read_json(a / 'meta.json') == read_json(b / 'meta.json')
    d['dataCutoff'] = read_json(b / 'meta.json')['dataCutoff']
    d['pass'] = bool(d['ranking.csv'] and d['no-prior.csv'] and d['metaJsonEqual'])
    return d


def check_u():
    """STAMINA_FREEZE=1（out/frz）對預設（out/def）：stamina 以外 15 項能力值差 0、stamina＝開季卡值、MPGhat 差 0。"""
    a = {r['playerId']: r for r in rows(OUT / 'def' / 'ranking.csv')}
    b = {r['playerId']: r for r in rows(OUT / 'frz' / 'ranking.csv')}
    pc, _ = F.load_prior('2025-26')
    attrs = [x for x in ('long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique',
                         'onBall', 'help', 'heightInches', 'creation', 'pressure')]
    other = max(abs(float(a[i][k]) - float(b[i][k])) for i in a for k in attrs if a[i][k] != '')
    mpg = max(abs(float(a[i]['MPGhat']) - float(b[i]['MPGhat'])) for i in a if a[i]['MPGhat'] != '')
    st_bad, n_cmp = [], 0
    for i in b:
        c = pc.get(int(i))
        if c is None or b[i]['stamina'] == '':
            continue
        x0 = float(c['stamina'])
        n_cmp += 1
        if abs(float(b[i]['stamina']) - x0) > 0.05 + 1e-9:
            st_bad.append((b[i]['name'], b[i]['stamina'], x0))
    meta = read_json(OUT / 'frz' / 'meta.json')
    return {'pass': bool(set(a) == set(b) and other == 0.0 and mpg == 0.0 and n_cmp > 0 and not st_bad and 'staminaFreeze' in meta),
            'sameIds': set(a) == set(b), 'otherAttrsMaxAbs': other, 'MPGhatMaxAbs': mpg, 'staminaNotPrior': st_bad[:5],
            'nStaminaNotPrior': len(st_bad), 'nStaminaCompared': n_cmp, 'note': 'stamina＝開季卡值：ranking 一位小數對先驗卡 stamina，容差 0.05'}


def check_c1():
    ex = HERE / 'logs' / 'npm-test.exit'
    v = ex.read_text().strip() if ex.exists() else None
    return {'pass': v == '0', 'exit': v}


# ------------------------------------------------------------------ 閘門（v5 §2 V1∧V2，同 E-095 gate()）
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


# ------------------------------------------------------------------ 線上（只報告）
def live_diff():
    a = {r['playerId']: r for r in rows(OUT / 'def' / 'ranking.csv')}
    b = {r['playerId']: r for r in rows(OUT / 'frz' / 'ranking.csv')}
    d = {i: float(b[i]['ovr']) - float(a[i]['ovr']) for i in a}
    ad = sorted(abs(v) for v in d.values())
    top = lambda t: sorted(t.values(), key=lambda r: int(r['rank']))[:20]  # noqa: E731
    na, nb = {r['name'] for r in top(a)}, {r['name'] for r in top(b)}
    by_a, by_b = {r['name']: r for r in a.values()}, {r['name']: r for r in b.values()}

    def ent(n):
        x, y = by_a[n], by_b[n]
        return {'name': n, 'N': int(y['N']), 'MPGhat': float(y['MPGhat'] or 0), 'staminaDef': x['stamina'], 'staminaFrz': y['stamina'],
                'ovrDef': float(x['ovr']), 'rankDef': int(x['rank']), 'ovrFrz': float(y['ovr']), 'rankFrz': int(y['rank'])}
    big = sorted(a, key=lambda i: -abs(d[i]))[:10]
    return {'n': len(d), 'absDeltaMedian': float(np.median(ad)), 'absDeltaMax': ad[-1], 'gt3': sum(1 for x in ad if x > 3),
            'entered': [ent(n) for n in sorted(nb - na)], 'left': [ent(n) for n in sorted(na - nb)],
            'watch': [ent(n) for n in WATCH if n in by_a], 'biggest': [ent(a[i]['name']) for i in big]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=str(E095_CACHE))
    args = ap.parse_args()
    PA.install()
    res = {'experiment': 'E-161', 'version': 'inseason 0.2.9+E161', 'prereg_sha256': sha(HERE / 'preregistration.md')}
    assert res['prereg_sha256'] == PREREG_SHA

    pre = {'c0L': check_c0L(), 'u': check_u(), 'c1': check_c1()}
    res['prereq'] = pre
    print({k: v['pass'] for k, v in pre.items()}, flush=True)

    rel = V2.load_reliability()
    sel = json.load(open(B.E033 / 'fit.json', encoding='utf-8'))['selection']
    cfix = {s: float(sel[s]['c']) for s in STARTS}
    cache = Path(args.cache)
    if cache.exists():
        fit = pickle.load(open(cache, 'rb'))
        res['fitCache'] = {'path': str(cache.relative_to(ROOT)), 'sha256': sha(cache)}
    else:
        fit = B.fit_all()
        own = HERE / 'cache' / 'fit.pkl'
        own.parent.mkdir(parents=True, exist_ok=True)
        pickle.dump(fit, open(own, 'wb'))
        res['fitCache'] = {'path': str(own.relative_to(ROOT)), 'built': True}
    a064 = read_json(E064_OUT / 'anchors.json')
    AR, RREPL = a064['repl'], a064['rRepl']

    E = {'RG1': {}, 'RG1F': {}, 'RA': {}}
    pred_rows, dmpg = [], {}
    stamina_check = {'maxAbsFrozenVsPrior': 0.0}
    for s in STARTS:
        assert B.answer_monotone_check(s), s
        pw = PW.for_start(C, s)
        prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
        mpg0, mpgT = B.season_mpg(prior), B.season_mpg(target)
        ap_ = B.answer_pred(s)
        tg36 = PA.target_ovr(s)
        _, a0 = C.deployment(s)
        for N in N_LIST:
            B.POPS.setdefault(s, {})[N] = [p for p in C.population(prior, N) if p in tg36]
        for N in N_LIST:
            P = B.POPS[s][N]
            win, _ = F.windows_of(prior, N)
            g1, w1 = B.c4_run(s, N, fit, rel, cfix[s], 1)
            frozen = ([] if fit[s]['pressureOpen'] else ['pressure']) + ['stamina']
            gf = K.c4_predict(s, N, fit[s]['delta2'], rel, cfix[s], fit[s]['undefined'], frozen)
            stamina_check['maxAbsFrozenVsPrior'] = max(stamina_check['maxAbsFrozenVsPrior'],
                                                       max(abs(gf[p]['stamina'] - a0[p]['stamina']) for p in P))
            pr1, prf = pw.predict(g1), pw.predict(gf)
            hat = B.mpg_hat(mpg0, win, w1, P, True)
            tgR = {p: B.map_g((ap_[p] - RREPL) * mpgT[p] / 36, AR) for p in P}
            rg1 = {p: B.map_g((pr1[p]['pred'] - RREPL) * hat[p] / 36, AR) for p in P}
            rgf = {p: B.map_g((prf[p]['pred'] - RREPL) * hat[p] / 36, AR) for p in P}
            ra = {p: B.map_g((pw.ref[p]['pred'] - RREPL) * mpg0.get(p, 0.0) / 36, AR) for p in P}
            E['RG1'][(s, N)] = np.array([rg1[p] - tgR[p] for p in P])
            E['RG1F'][(s, N)] = np.array([rgf[p] - tgR[p] for p in P])
            E['RA'][(s, N)] = np.array([ra[p] - tgR[p] for p in P])
            dmpg[(s, N)] = np.array([(win[p]['MIN'] / win[p]['GP'] if p in win and win[p]['GP'] > 0 else mpg0.get(p, 0.0))
                                     - mpg0.get(p, 0.0) for p in P])
            for p in P:
                pred_rows.append({'start': s, 'N': N, 'playerId': p, 'targetRepl': round(tgR[p], 4), 'RA': round(ra[p], 4),
                                  'RG1': round(rg1[p], 4), 'RG1F': round(rgf[p], 4), 'mpg0': round(mpg0.get(p, 0.0), 3),
                                  'mpgHatG1': round(hat[p], 3), 'mpgTarget': round(mpgT[p], 3)})
        print('cells', s, flush=True)
    res['staminaFrozenCheck'] = stamina_check

    # ---- (c0) RG1 重現 E-064
    byk = {(r['start'], r['N'], r['playerId']): r for r in pred_rows}
    c0 = {'perStart': {}}
    mx_all = 0.0
    for s in STARTS:
        ref_rows = rows(E064_OUT / f'predictions-{s}.csv')
        mx, miss = 0.0, 0
        for r in ref_rows:
            m = byk.get((s, int(r['N']), int(r['playerId'])))
            if m is None:
                miss += 1
                continue
            for k in ('targetRepl', 'RA', 'RG1', 'mpg0', 'mpgHatG1', 'mpgTarget'):
                mx = max(mx, abs(float(m[k]) - float(r[k])))
        c0['perStart'][s] = {'rowsE064': len(ref_rows), 'rowsMine': sum(1 for k in byk if k[0] == s), 'missing': miss, 'maxAbsDiff': mx}
        mx_all = max(mx_all, mx)
    c0['maxAbsDiff'] = mx_all
    c0['pass'] = bool(mx_all < 1e-9 and all(v['missing'] == 0 and v['rowsE064'] == v['rowsMine'] for v in c0['perStart'].values()))
    c0['note'] = '比對 E-064 predictions-{start}.csv（四捨五入 4 位後）'
    pre['c0'] = c0
    ok = all(pre[k]['pass'] for k in ('c0L', 'u', 'c1', 'c0')) and stamina_check['maxAbsFrozenVsPrior'] == 0.0
    res['prereqAllPass'] = bool(ok)
    print('prereq', {k: v['pass'] for k, v in pre.items()}, stamina_check, flush=True)
    with open(HERE / 'predictions.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(pred_rows[0].keys()))
        w.writeheader()
        w.writerows(pred_rows)
    if not ok:
        res['judged'] = False
        res['note'] = '前置未全過：不看 (1)(2)'
        (HERE / 'results.json').write_text(json.dumps(tojson(res), ensure_ascii=False, indent=1), encoding='utf-8')
        return 3

    # ---- (1) 閘門：RG1F 對同尺度先驗卡 RA（同 E-095 主判定）
    gates = {nm: {'RG1F': gate(E['RG1F'], E['RA'], ss), 'RG1': gate(E['RG1'], E['RA'], ss)} for nm, ss in SETS.items()}

    # ---- (2) 8 格 MAE 差
    def cmp_cells(ss):
        out = {}
        for s in ss:
            for N in N_GRID:
                c = (s, N)
                m1, mf = float(np.abs(E['RG1'][c]).mean()), float(np.abs(E['RG1F'][c]).mean())
                out[f'{s}/N{N}'] = {'n': len(B.POPS[s][N]), 'MAE_RG1': m1, 'MAE_RG1F': mf, 'diff': mf - m1,
                                    'signed_RG1': float(E['RG1'][c].mean()), 'signed_RG1F': float(E['RG1F'][c].mean())}
        cl = [(s, N) for s in ss for N in N_GRID]
        mxd = max(v['diff'] for v in out.values())
        return {'cells': out, 'maxDiff': mxd, 'pass2': bool(mxd <= 0.05), 'boot': B.paired_boot(E['RG1F'], E['RG1'], cl)}
    cmp2 = {nm: cmp_cells(ss) for nm, ss in SETS.items()}
    g1 = gates['main']['RG1F']['pass']
    res['judged'] = True
    res['verdict'] = {'1': g1, '2': cmp2['main']['pass2'],
                      'outcome': '(1)(2) 都過' if g1 and cmp2['main']['pass2'] else '(1) 過、(2) 不過' if g1 else '(1) 不過'}
    res['gates'] = gates
    res['cmp2'] = cmp2

    # ---- 只報告：本季場均分鐘 − MPG0 三分位，N=3、5
    ter = []
    for s in MAIN:
        for N in (3, 5):
            dm = dmpg[(s, N)]
            lo, hi = np.quantile(dm, [1 / 3, 2 / 3])
            for g, mask in (('down', dm <= lo), ('flat', (dm > lo) & (dm <= hi)), ('up', dm > hi)):
                row = {'start': s, 'N': N, 'group': g, 'n': int(mask.sum()), 'dMPG_lo': float(dm[mask].min()), 'dMPG_hi': float(dm[mask].max())}
                for k in ('RG1', 'RG1F'):
                    e = E[k][(s, N)][mask]
                    row[f'signed_{k}'] = float(e.mean())
                    row[f'MAE_{k}'] = float(np.abs(e).mean())
                ter.append(row)
    res['tertile'] = ter
    res['live'] = live_diff()
    (HERE / 'results.json').write_text(json.dumps(tojson(res), ensure_ascii=False, indent=1), encoding='utf-8')
    print('verdict', res['verdict'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
