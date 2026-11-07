"""E-133 回測（預註冊 preregistration.md；sha256 見 preregistration.sha256）。
分項目遺忘率：δ² 分年齡（M1）＋季內直線遞減權重（M2-a/b/c）；指數曲線只報告。
骨架＝e129-tl-season-step/backtest_e129.py（import e133_lib 後沿用 e111 骨架，不改）。
用法（e133-attr-decay 目錄）：python -I -B -X utf8 backtest_e133.py [--stop-after-phase0]
本程式沒有子程序；若有一律 CREATE_NO_WINDOW。
"""
import argparse
import csv
import json
import math
import pickle
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e133_lib as L  # noqa: E402
from e133_lib import (E, B, PA, C, SA, F, IC, V2, PW, E95, OVRPipeline, ATTRS, m, Kmod, np, HERE, REPORT,  # noqa: E402
                      TRAIN, TEST, ALL_RUN, HIST_ALL, NS, NS82, S0, CANDS, TIE, sha, rel, wjson)

POP_MIN = 200
_WCACHE = {}
_SDCACHE = {}


# ------------------------------------------------------------------ 加權視窗
def wagg(sd, game_map=None):
    """SA.aggregate 的加權版：列若帶 '_w'，GP += _w；沒有 '_w' 時與原版逐位相同。"""
    stats = {}
    for pid, b in sd['box'].items():
        keep = game_map.get(pid) if game_map is not None else None
        rows = [r for r in b['rows'] if keep is None or r['GAME_ID'] in keep]
        if not rows:
            continue
        s = {k: 0.0 for k in SA.BOX_KEYS}
        s['GP'] = 0
        for r in rows:
            for k in SA.BOX_KEYS:
                s[k] += r[k]
            s['GP'] += r.get('_w', 1)
        s['name'] = b['name']
        s['midM'] = s['midA'] = s['shortM'] = s['shortA'] = 0
        for r in rows:
            sh = sd['shots'].get((pid, r['GAME_ID']))
            if sh:
                for k in ('midM', 'midA', 'shortM', 'shortA'):
                    s[k] += sh[k]
        s['MPG'] = SA.safe(s['MIN'], s['GP'])
        s['possDen'] = s['FGA'] + 0.44 * s['FTA'] + s['AST'] + s['TOV']
        stats[pid] = s
    return stats


def exp_h(sa, n=20):
    """指數 h：前 n 場權重和＝直線 Σ max(0,1−sa·j)。"""
    target = sum(max(0.0, 1.0 - sa * j) for j in range(n))
    if target >= n - 1e-12:
        return 0.0
    lo, hi = 0.0, 50.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if sum(math.exp(-mid * j) for j in range(n)) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def wfun_of(spec):
    kind, p = spec
    if kind == 'lin':
        return lambda j: max(0.0, 1.0 - p * j)
    return lambda j: math.exp(-p * j)


def wrec(s, N, spec):
    """加權視窗卡 {pid: window card}；spec=('lin',sa) 或 ('exp',h)。快取。"""
    key = (s, N, spec[0], round(float(spec[1]), 14))
    if key in _WCACHE:
        return _WCACHE[key]
    prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
    if target not in _SDCACHE:
        sd = C.load_target_season(target)
        _SDCACHE[target] = (sd, IC.team_game_index(sd))
    sd, idx = _SDCACHE[target]
    wf = wfun_of(spec)
    box, shots = {}, {}
    for pid, b in sd['box'].items():
        rows = []
        for r in b['rows']:
            tg = idx.get((r['TEAM_ID'], r['GAME_ID']), 10 ** 9)
            if tg > N:
                continue
            w = wf(N - tg)
            if w <= 0:
                continue
            rr = dict(r)
            for k in SA.BOX_KEYS:
                rr[k] = r[k] * w
            rr['_w'] = w
            rows.append(rr)
            sh = sd['shots'].get((pid, r['GAME_ID']))
            if sh:
                shots[(pid, r['GAME_ID'])] = {k: (v * w if isinstance(v, (int, float)) else v) for k, v in sh.items()}
        if rows:
            box[pid] = {**b, 'rows': rows}
    sdw = dict(sd)
    sdw['box'], sdw['shots'] = box, shots
    prior_cards, _ = C.load_card(prior)
    received = IC.received_prior(prior)
    old = SA.aggregate
    SA.aggregate = wagg
    try:
        out = IC.window_cards(sdw, 10 ** 4, C.mapping_for(prior), prior_cards, received)
    finally:
        SA.aggregate = old
    _WCACHE[key] = out
    return out


# ------------------------------------------------------------------ δ²、u_a
def d2_tables(fit, rel_):
    """per start：pooled(pickle)、pooled_recomp、young、vet 的 {a:{m,delta2,defined}}，與實際採用的 d2grp（含回退）。"""
    out = {}
    for s in ALL_RUN:
        tgt = C.CHAIN[s]['target']
        pooled_re = L.delta2_pairs(s, None)
        young = L.delta2_pairs(s, L.is_young)
        vet = L.delta2_pairs(s, L.is_vet)
        use = {'young': {}, 'vet': {}}
        fb = []
        for a in C.UPD:
            for g, tab in (('young', young), ('vet', vet)):
                ok = tab[a]['m'] >= 30 and tab[a]['defined']
                use[g][a] = tab[a]['delta2'] if ok else float(fit[s]['delta2'][a])
                if not ok:
                    fb.append({'start': s, 'attr': a, 'group': g, 'm': tab[a]['m']})
        out[s] = {'pooled': {a: float(fit[s]['delta2'][a]) for a in C.UPD}, 'pooled_recomp': pooled_re,
                  'young': young, 'vet': vet, 'use': use, 'fallback': fb}
    return out


def u_tables(fit, rel_):
    """u_a＝(δ²/σ²)／中位數；中位數取各起點「可更新、非 undefined、非凍結」的項目。"""
    out = {}
    for s in ALL_RUN:
        undefined = fit[s]['undefined']
        frozen = [] if fit[s]['pressureOpen'] else ['pressure']
        el = [a for a in C.UPD if a not in undefined and a not in frozen]
        r = {a: float(fit[s]['delta2'][a]) / rel_[a]['sigma2'] for a in el}
        med = float(np.median(list(r.values())))
        out[s] = {'ratio': r, 'median': med, 'u': {a: (r[a] / med if a in r else 0.0) for a in C.UPD}}
    return out


# ------------------------------------------------------------------ prepare / 候選
class Ctx:
    pass


def prepare(s, N, fit, rel_, pids):
    prior = C.CHAIN[s]['prior']
    prior_cards, _ = F.load_prior(prior)
    _, attrs0 = C.deployment(s)
    w, _ = F.windows_of(prior, N)
    usg = C.usg_prior(prior)
    undefined = fit[s]['undefined']
    frozen = [] if fit[s]['pressureOpen'] else ['pressure']
    out = {}
    old = SA.SEASON_MIN_SAMPLE['stamina']
    SA.SEASON_MIN_SAMPLE['stamina'] = 1
    try:
        for pid in pids:
            x0 = attrs0[pid]
            rec = w.get(pid)
            pc = prior_cards.get(pid)
            f = min(N / Kmod.G_of(s, pid), 1.0)
            upd = {}
            for a in C.UPD:
                if pc is None or a in undefined or a in frozen:
                    continue
                if rec is None or IC.sample_of(rec, a) < SA.SEASON_MIN_SAMPLE[a]:
                    continue
                y = F.y_adj_of(pc, rec, a, usg.get(pid, 0.0))
                upd[a] = (y, IC.sample_of(rec, a), V2.sample_n(pc, a))
            out[pid] = {'x0': x0, 'f': f, 'pc': pc, 'usg': usg.get(pid, 0.0), 'upd': upd}
    finally:
        SA.SEASON_MIN_SAMPLE['stamina'] = old
    return out


def cand_def(name, wstar_s0=None):
    """回傳 (kind, s0)。kind: B0 / M1 / M2 / EXP。"""
    if name == 'B0':
        return 'B0', 0.0
    if name == 'M1':
        return 'M1', 0.0
    if name in S0:
        return 'M2', S0[name]
    if name == 'EXP':
        return 'EXP', wstar_s0
    raise KeyError(name)


def calc(c, name, wstar_s0=None, pooled_groups=False, s0_override=None):
    """回傳 attrs, wst, bs{(pid,a):b}。"""
    kind, s0 = cand_def(name, wstar_s0)
    if s0_override is not None:
        kind, s0 = 'M2', s0_override
    rel_ = c.rel_
    attrs = dict(c.attrs0)
    wst, bs = {}, {}
    ut = c.u['u']
    for pid, pr in c.prep.items():
        x0, f = pr['x0'], pr['f']
        grp = c.grp.get(pid)
        vals = {}
        for a, (y, n, npv) in pr['upd'].items():
            if kind == 'B0' or grp is None or pooled_groups:
                d2 = c.d2pool[a]
            else:
                d2 = c.d2use[grp][a]
            keff = V2.k_eff(d2, rel_[a]['sigma2'], npv, rel_[a]['nRef'])
            k = c.cfix * keff
            if kind in ('B0', 'M1'):
                b = n / (n + k)
                wt = f + (1.0 - f) * b
                v = x0[a] + wt * (y - x0[a])
            else:
                sa = s0 * ut[a]
                spec = ('lin', sa) if kind == 'M2' else ('exp', exp_h(sa))
                rw = wrec(c.s, c.N, spec).get(pid)
                if rw is None:
                    ne, yw = 0.0, x0[a]
                else:
                    ne = IC.sample_of(rw, a)
                    yw = C.usage_adjust({a: float(pr['pc'][a])}, rw, a, pr['usg'])
                b = ne / (ne + k) if ne > 0 else 0.0
                wt = f + (1.0 - f) * b
                v = x0[a] + f * (y - x0[a]) + (1.0 - f) * b * (yw - x0[a])
            vals[a] = C.clip(v)
            bs[(pid, a)] = b
            if a == 'stamina':
                wst[pid] = wt
        attrs[pid] = {**x0, **vals}
    return attrs, wst, bs


def run_cand(c, name, **kw):
    attrs, wst, _ = calc(c, name, **kw)
    pr = c.pw.predict(attrs)
    hat = B.mpg_hat(c.mpg0_all, c.win, wst, c.P, True)
    return np.array([B.map_g(c.gv(pr[p]['pred'] - c.RREPL, hat[p]), c.AR) - c.tgR[p] for p in c.P])


def build_cells(t0, starts, fit, rel_, cfix, n095, RREPL, AR, D2, U):
    gv = lambda d, mm: E95.gval('sat15', d, mm)  # noqa: E731
    ctx, info = {}, {}
    for s in starts:
        prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
        pw = PW.for_start(C, s)
        tcards, _ = C.load_card(target)
        if s in TEST:
            # D 起點：答案卡用 v5 鏈既有的答案卡 pred（D1/D2＝v5-min csv，D3＝正式卡 predictedPer36；v5 沒有可供 OVRPipeline 用的 D3 答案 RAPM 檔）
            ap_ = B.answer_pred(s)
            info[s] = {'answerPlayers': len(ap_), 'answerSource': 'v5 answer_pred'}
        else:
            tpipe = OVRPipeline(str(E.CARD_SUMMARY), str(PA.rapm_path(C.CHAIN[s]['ans'])), tcards)
            tp = tpipe.predict({pid: {a: float(c[a]) for a in ATTRS} for pid, c in tcards.items()})
            ap_ = {pid: tp[pid]['pred'] for pid in tcards}
            info[s] = {'answerPlayers': len(ap_), 'answerSource': 'OVRPipeline(027 target card)'}
        mpg0, mpgT = B.season_mpg(prior), B.season_mpg(target)
        tg36 = PA.target_ovr(s)
        _, attrs0 = C.deployment(s)
        ages = L.ages_of(target)
        for N in NS82:
            B.POPS.setdefault(s, {})[N] = [p for p in C.population(prior, N) if p in tg36]
        for N in NS82:
            P = B.POPS[s][N]
            assert not [p for p in P if p not in ap_ or p not in mpgT], (s, N)
            win, _ = F.windows_of(prior, N)
            c = Ctx()
            c.s, c.N, c.P, c.pw, c.win, c.attrs0 = s, N, P, pw, win, attrs0
            c.cfix = cfix[s]
            c.rel_ = rel_
            c.prep = prepare(s, N, fit, rel_, P)
            c.age = {p: ages.get(p) for p in P}
            c.grp = {p: ('young' if ages[p] <= L.YOUNG_MAX else 'vet') for p in P if p in ages}
            c.young = {p: c.grp.get(p) == 'young' for p in P}
            c.d2pool, c.d2use, c.u = D2[s]['pooled'], D2[s]['use'], U[s]
            c.mpg0_all = mpg0
            c.tgR = {p: B.map_g(gv(ap_[p] - RREPL, mpgT[p]), AR) for p in P}
            c.ra = {p: B.map_g(gv(pw.ref[p]['pred'] - RREPL, mpg0.get(p, 0.0)), AR) for p in P}
            c.eRA = np.array([c.ra[p] - c.tgR[p] for p in P])
            c.nbase = n095.get((s, N))
            c.gv, c.RREPL, c.AR = gv, RREPL, AR
            ctx[(s, N)] = c
        print('cells', s, {N: len(ctx[(s, N)].P) for N in NS82}, f'{time.time() - t0:.0f}s', flush=True)
    return ctx, info


def mae(e):
    return float(np.abs(e).mean())


def pick_wstar(J, tie=TIE):
    jmin = min(J.values())
    ties = [c for c in CANDS if J[c] - jmin < tie]
    return ties[0], ties, jmin


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stop-after-phase0', action='store_true')
    args = ap.parse_args()
    t0 = time.time()
    pre_sha = sha(HERE / 'preregistration.md')
    assert pre_sha == (HERE / 'preregistration.sha256').read_text().split()[0], '預註冊 sha 不符'
    assert pre_sha.startswith('b01a4229') and pre_sha.endswith('5bdc'), '預註冊 sha 與派工訊息不符'
    ph0 = {'experiment': 'E-133 phase 0', 'preregistrationSha256': pre_sha, 'checks': {}}

    def stop(reason):
        ph0['pass'] = False
        ph0['stopReason'] = reason
        wjson(HERE / 'phase0.json', ph0)
        (HERE / 'report-phase0-stop.md').write_text(
            '# E-133 phase 0 未通過\n\n依預註冊 §2.2 停下，沒有跑 §2.3 以後，沒有輸出任何候選誤差。\n\n原因：' + reason +
            '\n\n數字與可能原因見 phase0.json 與下方。\n\n```\n' + json.dumps(E95.tojson(ph0['checks']), ensure_ascii=False, indent=1)[:6000] + '\n```\n',
            encoding='utf-8')
        print('PHASE0 STOP', reason, flush=True)
        return 3

    defl, cards_info = L.setup(t0, ALL_RUN, HIST_ALL)
    ph0['cards'] = cards_info
    ph0['defL'] = {rel(k): {'file': rel(v), 'sha256': sha(v)} for k, v in defl.items()}
    pool, miss = E.pool_pairs_027()
    anc = E95.anchors_for('sat15', pool)
    RREPL, AR = anc['rRepl'], anc['repl']
    rel_ = V2.load_reliability()
    sel = json.load(open(B.E033 / 'fit.json', encoding='utf-8'))['selection']
    cfix = {s: float(sel[s]['c']) for s in E.E095_STARTS}
    fit = pickle.load(open(E.FIT_CACHE, 'rb'))
    n095 = {}
    for r in E.rows(E.SAT15_PRED):
        k = (r['start'], int(r['N']))
        n095[k] = n095.get(k, 0) + 1
    print('B.BOOT', B.BOOT, flush=True)

    # ---- c0d（分年齡 δ²）與 u_a
    D2 = d2_tables(fit, rel_)
    U = u_tables(fit, rel_)
    c0d = {'minPairs': 30, 'perStart': {}, 'fallback': []}
    for s in ALL_RUN:
        c0d['perStart'][s] = {a: {'young_m': D2[s]['young'][a]['m'], 'vet_m': D2[s]['vet'][a]['m'],
                                  'pooled_m_recomp': D2[s]['pooled_recomp'][a]['m']} for a in C.UPD}
        c0d['fallback'] += D2[s]['fallback']
    c0d['nFallbackCells'] = len(c0d['fallback'])
    c0d['nCells'] = len(ALL_RUN) * len(C.UPD) * 2
    c0d['pass'] = True      # 規格是「不足的格回退並列出」，本身不會失敗
    ph0['checks']['c0d'] = c0d
    ph0['delta2'] = {s: {'pooled_pickle': D2[s]['pooled'],
                         'pooled_recomp': {a: D2[s]['pooled_recomp'][a]['delta2'] for a in C.UPD},
                         'young': {a: D2[s]['young'][a]['delta2'] for a in C.UPD},
                         'vet': {a: D2[s]['vet'][a]['delta2'] for a in C.UPD},
                         'used_young': D2[s]['use']['young'], 'used_vet': D2[s]['use']['vet']} for s in ALL_RUN}
    ph0['u_a'] = {s: {'median': U[s]['median'], 'u': U[s]['u']} for s in ALL_RUN}

    # delta2-by-age.csv
    with open(HERE / 'delta2-by-age.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['start', 'attr', 'sigma2', 'nRef', 'delta2_pooled_pickle', 'delta2_pooled_recomp', 'm_pooled', 'delta2_young', 'm_young',
                    'delta2_vet', 'm_vet', 'used_young', 'used_vet', 'young_fallback', 'vet_fallback', 'u_a',
                    'oldShare_pooled', 'oldShare_young', 'oldShare_vet'])
        for s in ALL_RUN:
            for a in C.UPD:
                sg, nr = rel_[a]['sigma2'], rel_[a]['nRef']
                sh = lambda d: (sg / nr) / (d + sg / nr) if (d + sg / nr) > 0 else float('nan')  # noqa: E731
                yu, vu = D2[s]['use']['young'][a], D2[s]['use']['vet'][a]
                w.writerow([s, a, sg, nr, D2[s]['pooled'][a], D2[s]['pooled_recomp'][a]['delta2'], D2[s]['pooled_recomp'][a]['m'],
                            D2[s]['young'][a]['delta2'], D2[s]['young'][a]['m'], D2[s]['vet'][a]['delta2'], D2[s]['vet'][a]['m'],
                            yu, vu, int(not (D2[s]['young'][a]['m'] >= 30 and D2[s]['young'][a]['defined'])),
                            int(not (D2[s]['vet'][a]['m'] >= 30 and D2[s]['vet'][a]['defined'])), U[s]['u'][a],
                            sh(D2[s]['pooled'][a]), sh(yu), sh(vu)])

    # ---- c0D
    c0D = {'pass': False, 'detail': {}}
    try:
        ctx, ans_info = build_cells(t0, ALL_RUN, fit, rel_, cfix, n095, RREPL, AR, D2, U)
        ok = True
        for s in ALL_RUN:
            cnt = {N: len(ctx[(s, N)].P) for N in NS82}
            c0D['detail'][s] = {'P_s(N)': cnt, 'n095': {N: n095.get((s, N)) for N in NS82},
                                'sameAsE095': all(cnt[N] == n095.get((s, N)) for N in NS82), 'ge200': all(cnt[N] >= POP_MIN for N in NS),
                                'answerPlayers': ans_info[s]['answerPlayers']}
            if s in TEST:
                ok = ok and c0D['detail'][s]['ge200']
        c0D['pass'] = bool(ok)
        c0D['note'] = '先驗卡、答案卡（OVRPipeline）、PW.for_start、P_s(N) 在 027 下建得出來'
    except Exception as ex:  # noqa: BLE001
        import traceback
        c0D['error'] = repr(ex)
        c0D['trace'] = traceback.format_exc()[-2000:]
        ctx = None
    ph0['checks']['c0D'] = c0D
    if not c0D['pass']:
        return stop('c0D 不過：' + (c0D.get('error') or 'P_s(N) < 200'))

    # ---- c0r
    res111 = json.loads((REPORT / 'e111-card027' / 'results.json').read_text(encoding='utf-8'))
    c0r = {'cells': []}
    ok = True
    for s in ('Y3', 'Y5', 'Y6'):
        for N in NS82:
            c = ctx[(s, N)]
            e_mine = run_cand(c, 'B0')
            g1, w1 = B.c4_run(s, N, fit, rel_, cfix[s], 1)
            pr = c.pw.predict(g1)
            hat = B.mpg_hat(c.mpg0_all, c.win, w1, c.P, True)
            e_orig = np.array([B.map_g(c.gv(pr[p]['pred'] - RREPL, hat[p]), AR) - c.tgR[p] for p in c.P])
            maxdiff = float(np.max(np.abs(e_mine - e_orig)))
            row = {'start': s, 'N': N, 'n': len(c.P), 'n095': c.nbase, 'MAE_mine': mae(e_mine), 'maxAbsErrDiff': maxdiff}
            gcells = res111['gates']['main' if s != 'Y3' else 'Y3']['cells']
            gr = next((x for x in gcells if x['start'] == s and x['N'] == N), None)
            if gr is not None:
                row['absDiff_vs_results_json'] = abs(round(mae(e_mine), 6) - gr['MAE_C'])
                row['A_absDiff'] = abs(round(float(np.abs(c.eRA).mean()), 6) - gr['MAE_A'])
            row['pass'] = bool(maxdiff < 1e-9 and len(c.P) == c.nbase and
                               (gr is None or (row['absDiff_vs_results_json'] < 1e-9 and row['A_absDiff'] < 1e-9)))
            ok = ok and row['pass']
            c0r['cells'].append(row)
    Ec = {(s, N): run_cand(ctx[(s, N)], 'B0') for s in ('Y5', 'Y6') for N in NS82}
    Eb = {(s, N): ctx[(s, N)].eRA for s in ('Y5', 'Y6') for N in NS82}
    g_base = E.gate(Ec, Eb, ['Y5', 'Y6'], n095)
    g_ref = res111['gates']['main']
    gok = (g_base['pass'] == g_ref['pass'])
    for N in (3, 5):
        gok = gok and abs(round(g_base['V1'][N]['U_pool'], 6) - g_ref['V1'][str(N)]['U_pool']) < 1e-9 \
            and g_base['V1'][N]['pass'] == g_ref['V1'][str(N)]['pass']
    for N in (10, 20):
        gok = gok and g_base['V2'][N]['pass'] == g_ref['V2'][str(N)]['pass']
        for s in ('Y5', 'Y6'):
            gok = gok and abs(round(g_base['V2'][N]['cells'][s]['ciHi'], 6) - g_ref['V2'][str(N)]['cells'][s]['ciHi']) < 1e-9
    c0r['gateBaselineReproduces'] = bool(gok)
    c0r['pass'] = bool(ok and gok)
    ph0['checks']['c0r'] = c0r
    print('c0r', c0r['pass'], f'{time.time() - t0:.0f}s', flush=True)

    # ---- c0e / c0g
    c0e = {'e1_M1pooled_vs_B0': {}, 'e2_M2s0zero_vs_M1': {}, 'e3_w1_neff_y': {}}
    mx1 = mx2 = 0.0
    t_e = time.time()
    # ③ 在 w≡1 時 n_eff、y_w 與視窗合計；同時是 c0g 的逐項檢查
    g_ok = {a: {'n': 0, 'maxDn': 0.0, 'maxDy': 0.0} for a in C.UPD}
    for s in ALL_RUN:
        for N in NS:
            c = ctx[(s, N)]
            rw = wrec(s, N, ('lin', 0.0))
            for pid, pr in c.prep.items():
                r1 = rw.get(pid)
                for a, (y, n, npv) in pr['upd'].items():
                    g = g_ok[a]
                    if r1 is None:
                        g['maxDn'] = max(g['maxDn'], n)
                        continue
                    yw = C.usage_adjust({a: float(pr['pc'][a])}, r1, a, pr['usg'])
                    g['n'] += 1
                    g['maxDn'] = max(g['maxDn'], abs(IC.sample_of(r1, a) - n))
                    g['maxDy'] = max(g['maxDy'], abs(yw - y))
    c0e['e3_w1_neff_y'] = {'perAttr': g_ok, 'tWeightedWindows': round(time.time() - t_e, 1)}
    e3 = all(v['maxDn'] < 1e-9 and v['maxDy'] < 1e-9 for v in g_ok.values() if v['n'] > 0)
    for s in ALL_RUN:
        for N in NS82:
            c = ctx[(s, N)]
            a_b, w_b, _ = calc(c, 'B0')
            a_p, w_p, _ = calc(c, 'M1', pooled_groups=True)
            a_m1, w_m1, _ = calc(c, 'M1')
            for pid in c.P:
                for a in ATTRS:
                    mx1 = max(mx1, abs(a_b[pid][a] - a_p[pid][a]))
            for pid in w_b:
                mx1 = max(mx1, abs(w_b[pid] - w_p[pid]))
            if N != 82:
                a_z, w_z, _ = calc(c, 'M2-a', s0_override=0.0)
                for pid in c.P:
                    for a in ATTRS:
                        mx2 = max(mx2, abs(a_m1[pid][a] - a_z[pid][a]))
                for pid in w_m1:
                    mx2 = max(mx2, abs(w_m1[pid] - w_z[pid]))
    c0e['e1_M1pooled_vs_B0'] = {'maxAbsDiff': mx1, 'pass': bool(mx1 < 1e-9)}
    c0e['e2_M2s0zero_vs_M1'] = {'maxAbsDiff': mx2, 'pass': bool(mx2 < 1e-9)}
    c0e['e3_w1_neff_y']['pass'] = bool(e3)
    c0e['pass'] = bool(mx1 < 1e-9 and mx2 < 1e-9 and e3)
    ph0['checks']['c0e'] = c0e
    unsplit = [a for a in C.UPD if g_ok[a]['n'] == 0]
    frozen_names = sorted({a for s in ALL_RUN for a in (fit[s]['undefined'] + ([] if fit[s]['pressureOpen'] else ['pressure']))})
    cg = {'splittable': [a for a in C.UPD if g_ok[a]['n'] > 0 and a not in frozen_names],
          'unsplittable_s_a_zero': sorted(set(unsplit) | set(a for a in ('pressure',) if not any(fit[s]['pressureOpen'] for s in ALL_RUN))),
          'undefinedInSomeStart_notUpdatedThere': {s: sorted(fit[s]['undefined']) for s in ALL_RUN if fit[s]['undefined']},
          'note': 'pressure 在所有起點凍結（樣本 0，pressureOpen=False），沒有逐場資料，s_a=0；undefined 屬性（若有）也不更新'}
    cg['nUPD'] = len(C.UPD)
    cg['pass'] = bool(len(cg['unsplittable_s_a_zero']) * 2 <= len(C.UPD))
    ph0['checks']['c0g'] = cg
    print('c0e', c0e['pass'], mx1, mx2, 'c0g', cg['pass'], f'{time.time() - t0:.0f}s', flush=True)

    # ---- c0x（訓練起點；N=20 為判準格，其他 N 一併列出）
    c0x = {'perStart': {}, 'dropped': [], 'criterionN': 20}
    for s in TRAIN:
        row = {}
        for N in NS:
            c = ctx[(s, N)]
            bsall = {nm: calc(c, nm)[2] for nm in CANDS}
            diff = 0
            for pid in c.P:
                d = False
                for a in c.prep[pid]['upd']:
                    vs = [bsall[nm][(pid, a)] for nm in CANDS]
                    if max(vs) - min(vs) > 1e-12:
                        d = True
                        break
                diff += d
            row[N] = {'n': len(c.P), 'nDiff': diff, 'frac': diff / len(c.P)}
        c0x['perStart'][s] = row
        if row[20]['frac'] < 0.05:
            c0x['dropped'].append(s)
    train_ok = [s for s in TRAIN if s not in c0x['dropped']]
    c0x['trainUsed'] = train_ok
    c0x['pass'] = len(train_ok) >= 2
    ph0['checks']['c0x'] = c0x

    hard = {k: ph0['checks'][k]['pass'] for k in ('c0r', 'c0D', 'c0e', 'c0g', 'c0x')}
    ph0['hardConditions'] = hard
    ph0['pass'] = bool(all(hard.values()))
    ph0['elapsedSec'] = round(time.time() - t0, 1)
    wjson(HERE / 'phase0.json', ph0)
    print('phase0', hard, f'{time.time() - t0:.0f}s', flush=True)
    if not ph0['pass']:
        return stop('硬條件不過：' + ','.join(k for k, v in hard.items() if not v))
    if args.stop_after_phase0:
        return 0
    return run_rest(t0, ctx, n095, train_ok, D2, U, rel_)


def run_rest(t0, ctx, n095, train_ok, D2, U, rel_):
    out = {'experiment': 'E-133', 'preregistrationSha256': sha(HERE / 'preregistration.md'), 'trainUsed': train_ok,
           'u_a': {s: U[s]['u'] for s in ALL_RUN}, 'u_median': {s: U[s]['median'] for s in ALL_RUN}}
    rows, J = [], {}
    for nm in CANDS:
        cells = []
        for s in train_ok:
            for N in NS:
                v = mae(run_cand(ctx[(s, N)], nm))
                cells.append(v)
                rows.append({'cand': nm, 'start': s, 'N': N, 'MAE': v})
        J[nm] = float(np.mean(cells))
        print('train', nm, round(J[nm], 5), f'{time.time() - t0:.0f}s', flush=True)
    with open(HERE / 'train.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['cand', 'start', 'N', 'MAE'])
        for r in rows:
            w.writerow([r['cand'], r['start'], r['N'], f"{r['MAE']:.6f}"])
        for nm in CANDS:
            w.writerow([nm, 'J', 'mean', f'{J[nm]:.6f}'])
    wstar, ties, jmin = pick_wstar(J)
    out['train'] = {'J': J, 'Jmin': jmin, 'Wstar': wstar, 'tieSet': ties, 'rawArgmin': min(J, key=J.get)}
    print('W*', wstar, J, flush=True)
    wjson(HERE / 'results.json', out)
    if wstar == 'B0':
        out['verdict'] = '沒有改善'
        out['verdictReason'] = 'W* 為 B0，依 §2.3 不跑測試'
        wjson(HERE / 'results.json', out)
        return 0
    return run_test(t0, ctx, n095, wstar, out)


def run_test(t0, ctx, n095, wstar, out):
    s0w = 0.0 if wstar == 'M1' else S0[wstar]
    Eb, Ew, Ex = {}, {}, {}
    for s in TEST:
        for N in NS82:
            Eb[(s, N)] = run_cand(ctx[(s, N)], 'B0')
            if N == 82:
                Ew[(s, N)] = Eb[(s, N)]
                Ex[(s, N)] = Eb[(s, N)]
            else:
                Ew[(s, N)] = run_cand(ctx[(s, N)], wstar)
                Ex[(s, N)] = Ew[(s, N)] if wstar == 'M1' else run_cand(ctx[(s, N)], 'EXP', wstar_s0=s0w)
        print('test cells', s, f'{time.time() - t0:.0f}s', flush=True)
    rng = np.random.default_rng(1)

    def boot(d):
        idx = rng.integers(0, len(d), size=(2000, len(d)))
        bs = d[idx].mean(axis=1)
        return float(np.quantile(bs, .05)), float(np.quantile(bs, .95))

    cells = {}
    for s in TEST:
        for N in NS:
            d = np.abs(Ew[(s, N)]) - np.abs(Eb[(s, N)])
            lo, hi = boot(d)
            cells[f'{s}/N{N}'] = {'n': len(ctx[(s, N)].P), 'MAE_B0': mae(Eb[(s, N)]), 'MAE_Wstar': mae(Ew[(s, N)]),
                                  'dMAE': float(d.mean()), 'lo5': lo, 'hi95': hi,
                                  'MAE_exp': mae(Ex[(s, N)]), 'dMAE_exp': mae(Ex[(s, N)]) - mae(Eb[(s, N)])}
    c1 = [(s, N) for s in TEST for N in (10, 20)]
    pb = B.paired_boot(Ew, Eb, c1, rng_seed=1)
    pbx = B.paired_boot(Ex, Eb, c1, rng_seed=1)
    cond1 = pb['hi95'] < 0
    cond2 = all(cells[f'{s}/N{N}']['dMAE'] <= 0.05 for s, N in c1)
    cond3 = all(cells[f'{s}/N{N}']['dMAE'] <= 0.05 for s in TEST for N in (3, 5))
    Eba = {(s, N): ctx[(s, N)].eRA for s in TEST for N in NS82}
    g = E.gate(Ew, Eba, TEST, n095)
    cond4 = bool(g['pass'])
    if cond1 and cond2 and cond3 and cond4:
        verdict = '採用候選'
    elif (not cond1) and cond2 and cond3 and cond4:
        verdict = '沒有改善'
    else:
        verdict = '候選較差'
    out['test'] = {'Wstar': wstar, 's0': s0w, 'cells': cells, 'merged6': pb, 'merged6_exp': pbx, 'cond1': bool(cond1), 'cond2': bool(cond2),
                   'cond3': bool(cond3), 'cond4': cond4, 'gate': {'pass': g['pass'], 'V1': g['V1'], 'V2': g['V2']}}
    out['verdict'] = verdict
    sub = {}
    for s in TEST:
        for N in NS:
            c = ctx[(s, N)]
            d = np.abs(Ew[(s, N)]) - np.abs(Eb[(s, N)])
            for lab in ('young', 'vet'):
                msk = np.array([c.grp.get(p) == lab for p in c.P])
                dd = d[msk]
                if len(dd) < 2:
                    continue
                lo, hi = boot(dd)
                sub[f'{s}/N{N}/{lab}'] = {'n': int(len(dd)), 'dMAE': float(dd.mean()), 'lo5': lo, 'hi95': hi}
    out['subgroups'] = sub
    mono, gt10 = {}, {}
    for s in TEST:
        for nm, E_ in (('B0', Eb), ('Wstar', Ew), ('exp', Ex)):
            seq = [mae(E_[(s, N)]) for N in NS82]
            mono[f'{s}/{nm}'] = {'MAE_by_N(3,5,10,20,82)': seq, 'nonIncreasing': all(seq[i + 1] <= seq[i] + 1e-12 for i in range(4))}
        for N in NS:
            gt10[f'{s}/N{N}'] = {'B0': int((np.abs(Eb[(s, N)]) > 10).sum()), 'Wstar': int((np.abs(Ew[(s, N)]) > 10).sum()),
                                 'exp': int((np.abs(Ex[(s, N)]) > 10).sum())}
    out['monotonicity'], out['gt10'] = mono, gt10
    out['exp_h'] = {a: exp_h(s0w * U[a]) for a in C.UPD} if False else None
    with open(HERE / 'test-players.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['start', 'N', 'playerId', 'age', 'young', 'e_B0', 'e_Wstar', 'e_exp'])
        for s in TEST:
            for N in NS:
                c = ctx[(s, N)]
                for i, p in enumerate(c.P):
                    w.writerow([s, N, p, c.age[p], int(c.young[p]), f'{Eb[(s, N)][i]:.6f}', f'{Ew[(s, N)][i]:.6f}', f'{Ex[(s, N)][i]:.6f}'])
    out['elapsedSec'] = round(time.time() - t0, 1)
    wjson(HERE / 'results.json', out)
    print('verdict', verdict, pb, cond1, cond2, cond3, cond4, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
