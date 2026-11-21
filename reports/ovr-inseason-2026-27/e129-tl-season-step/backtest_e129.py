"""E-129 回測（預註冊 preregistration.md；sha256 見 preregistration.sha256）。

只換 C4 的收縮權重 b：x = f·y + (1−f)·(x0 + b·(y−x0))，f=N/G 不動。
  K 族：b = n/(n + c_g·k_eff)，c_g 依開季年齡分 young(≤23)／vet；(1,1)＝基準。
  T 族：b_T = W_cur/(W_cur+W_prior)，逐場權重 max(0,1−s·j)，跨季繼續數 j，前 k 季再乘 ρ^k（k=1..3）。
回測骨架＝e111-card027/backtest_e111.py（import 後沿用，不改）；每個格點只重算 attrs → pw.predict。

用法（repo 根目錄）：python -I -B -X utf8 reports/ovr-inseason-2026-27/e129-tl-season-step/backtest_e129.py [--stop-after-phase0]
所有子程序（本程式沒有）若有則帶 CREATE_NO_WINDOW。
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import pickle
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(REPORT / 'e111-card027'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np  # noqa: E402
import backtest_e111 as E  # noqa: E402
B, BP, PA, C, SA, F, IC, V2, PW, E95 = E.B, E.BP, E.PA, E.C, E.SA, E.F, E.IC, E.V2, E.PW, E.E95
OVRPipeline, ATTRS, m = E.OVRPipeline, E.ATTRS, E.m
Kmod = B.K

E.CARDS = HERE / 'cards'                  # 027 卡寫進本目錄
E111_DEFL = REPORT / 'e111-card027' / 'defL'
E129_DEFL = HERE / 'defL'
BOX_DIR = REPORT / 'v5' / 'history'
BIO_DIR = ROOT / 'data' / 'defense-seventh'

TRAIN = ['Y1', 'Y2', 'Y3']
TEST = ['Y5', 'Y6']
ALL_S = TRAIN + TEST
NS = [3, 5, 10, 20]
NS82 = [3, 5, 10, 20, 82]
YOUNG_MAX = 23
S_GRID = [0.0025, 0.005, 0.01]
RHO_Y = [0.3, 0.5, 0.7]
RHO_V = [0.6, 0.8, 0.9]
C_Y = [0.25, 0.5, 1.0]
C_V = [0.5, 1.0, 2.0]
TIE = 0.005
BASE_MODE = ('K', 1.0, 1.0)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def wjson(path, obj):
    Path(path).write_text(json.dumps(E95.tojson(obj), ensure_ascii=False, indent=1), encoding='utf-8')


def mode_name(md):
    if md[0] == 'K':
        return f'K(cy={md[1]:g},cv={md[2]:g})'
    return f'T(s={md[1]:g},ry={md[2]:g},rv={md[3]:g})'


def all_modes():
    out = [('K', cy, cv) for cy in C_Y for cv in C_V]
    out += [('T', s_, ry, rv) for s_ in S_GRID for ry in RHO_Y for rv in RHO_V]
    return out


# ------------------------------------------------------------------ 逐場／年齡資料
def prev_season(season, k):
    y = int(season[:4]) - k
    return f'{y}-{str((y + 1) % 100).zfill(2)}'


_BOX = {}


def box_info(season):
    """{'players': {pid: first_team}, 'teamG': {team: 場數}} 或 None（檔案不存在）。"""
    if season in _BOX:
        return _BOX[season]
    p = BOX_DIR / f'box-games-{season}.csv.gz'
    if not p.exists():
        _BOX[season] = None
        return None
    first, tg, seen = {}, {}, {}
    with gzip.open(p, 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            pid, team, gid, d = int(r['playerId']), int(r['teamId']), r['gameId'], r['gameDate']
            tg.setdefault(team, set()).add(gid)
            if pid not in first or (d, gid) < first[pid][0]:
                first[pid] = ((d, gid), team)
    _BOX[season] = {'players': {pid: v[1] for pid, v in first.items()}, 'teamG': {t: len(g) for t, g in tg.items()}}
    return _BOX[season]


def season_G(season, team):
    if season == '2019-20':
        bi = box_info(season)
        return float(bi['teamG'].get(team, 82)) if bi else 82.0
    if season == '2020-21':
        return 72.0
    if season == '2011-12':
        return 66.0
    return 82.0


_AGE = {}


def ages_of(season):
    if season in _AGE:
        return _AGE[season]
    p = BIO_DIR / season / 'bio.json'
    out = {}
    if p.exists():
        rs = json.loads(p.read_text(encoding='utf-8'))['data']['resultSets'][0]
        h = rs['headers']
        ip, ia = h.index('PLAYER_ID'), h.index('AGE')
        for row in rs['rowSet']:
            if row[ia] is not None:
                out[int(row[ip])] = float(row[ia])
    _AGE[season] = out
    return out


def prior_seasons_of(s, pid, target_prior):
    """回傳 [(k, season, G)]，k=1..3 為從 chain 的 prior 往回數的曆法季（k=1 就是 prior），只含球員有 box 列的季。"""
    out = []
    for k in range(1, 4):
        sea = prev_season(target_prior, k - 1)
        bi = box_info(sea)
        if bi is None or pid not in bi['players']:
            continue
        out.append((k, sea, season_G(sea, bi['players'][pid])))
    return out


_CS = {}


def cum_weights(s_):
    if s_ not in _CS:
        j = np.arange(0, 1000)
        w = np.maximum(0.0, 1.0 - s_ * j)
        _CS[s_] = np.concatenate([[0.0], np.cumsum(w)])
    return _CS[s_]


def b_T(N, slots, s_, rho):
    """slots=[(k,G)]（球員實際在聯盟的舊季，由近到遠）。回傳 (b, W_cur, W_prior)。"""
    cs = cum_weights(s_)
    wcur = cs[N]
    off = N
    wp = 0.0
    for k, g in slots:
        g = int(g)
        wp += (rho ** k) * (cs[off + g] - cs[off])
        off += g
    if wp <= 0:
        return 1.0, wcur, wp
    return wcur / (wcur + wp), wcur, wp


# ------------------------------------------------------------------ prepare / apply
def prepare(s, N, fit, rel_, pids):
    """複製 K.c4_predict 的跳過規則；回傳逐球員 {x0, f, upd:{a:(y,n,keff)}}（stamina 最小樣本＝1，同 B.c4_run）。"""
    prior = C.CHAIN[s]['prior']
    prior_cards, _ = F.load_prior(prior)
    _, attrs0 = C.deployment(s)
    w, _ = F.windows_of(prior, N)
    usg = C.usg_prior(prior)
    undefined = fit[s]['undefined']
    frozen = [] if fit[s]['pressureOpen'] else ['pressure']
    d2 = fit[s]['delta2']
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
                n = IC.sample_of(rec, a)
                keff = V2.k_eff(d2[a], rel_[a]['sigma2'], V2.sample_n(pc, a), rel_[a]['nRef'])
                upd[a] = (y, n, keff)
            out[pid] = {'x0': x0, 'f': f, 'upd': upd}
    finally:
        SA.SEASON_MIN_SAMPLE['stamina'] = old
    return out


def apply_mode(prep, mode, N, cfix, young, slots, attrs_all):
    """回傳 (attrs for all pids in attrs_all，其他球員＝x0, wst)。"""
    attrs = {pid: x0 for pid, x0 in attrs_all.items()}
    wst = {}
    for pid, pr in prep.items():
        x0, f = pr['x0'], pr['f']
        yg = young.get(pid, False)
        if mode[0] == 'T':
            rho = mode[2] if yg else mode[3]
            bt, _, _ = b_T(N, slots[pid], mode[1], rho)
        vals = {}
        for a, (y, n, keff) in pr['upd'].items():
            if mode[0] == 'K':
                cm = mode[1] if yg else mode[2]
                k = (cfix * cm) * keff
                b = n / (n + k)
            else:
                b = bt
            wt = f + (1.0 - f) * b
            vals[a] = C.clip(x0[a] + wt * (y - x0[a]))
            if a == 'stamina':
                wst[pid] = wt
        attrs[pid] = {**x0, **vals}
    return attrs, wst


# ------------------------------------------------------------------ 安裝與每格情境
class Ctx:
    pass


def setup(t0, starts_all):
    PA.install()
    E.m.m26_load_pool(E.POOL027)
    SA.zone_of = m.m26_zone_of
    m.m27_install_zone_filter()
    IC.window_cards = m.m26_window_cards
    C.clip = m.m26_clip
    V2.FROZEN_SUMMARY = E.CARD_SUMMARY
    fz_w = json.loads(E.PRIOR027.read_text(encoding='utf-8'))['foulDrawFreeze']
    defl = {}
    for s in starts_all:
        for k in ('pred', 'ans'):
            win = C.CHAIN[s][k]
            src = E129_DEFL / f'def-L-{win}.csv'
            if not src.exists():
                src = E111_DEFL / f'def-L-{win}.csv'
            defl[str(PA.rapm_path(win).resolve())] = str(src)
    m.m27_install_ul(defl)
    seasons = sorted({C.CHAIN[s]['prior'] for s in starts_all} | {C.CHAIN[s]['target'] for s in starts_all})
    cards_info = {}
    for S in seasons:
        path, chk, fz = E.build_card027(S, fz_w)
        C.PRIOR_PATH[S] = path
        cards_info[S] = {'file': rel(path), 'sha256': sha(path), 'inWindow': chk['inWindow'], 'sampleMismatch': chk['sampleMismatch']}
        print('card', S, chk['inWindow'], chk['sampleMismatch'], f'{time.time() - t0:.0f}s', flush=True)
    F.CACHE.clear()
    C._PIPE_CACHE.clear()
    PW._CACHE.clear()
    for k in [k for k in C._CACHE if k[0] == 'win']:
        del C._CACHE[k]
    return defl, cards_info


def build_cells(t0, starts, fit, rel_, cfix, base, n095, RREPL, AR):
    gv = lambda d, mm: E95.gval('sat15', d, mm)  # noqa: E731
    ctx, info = {}, {}
    for s in starts:
        prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
        pw = PW.for_start(C, s)
        tcards, _ = C.load_card(target)
        tpipe = OVRPipeline(str(E.CARD_SUMMARY), str(PA.rapm_path(C.CHAIN[s]['ans'])), tcards)
        tp = tpipe.predict({pid: {a: float(c[a]) for a in ATTRS} for pid, c in tcards.items()})
        ap_ = {pid: tp[pid]['pred'] for pid in tcards}
        info[s] = {'answerPlayers': len(ap_)}
        mpg0, mpgT = B.season_mpg(prior), B.season_mpg(target)
        tg36 = PA.target_ovr(s)
        _, attrs0 = C.deployment(s)
        ages = ages_of(target)
        for N in NS82:
            B.POPS.setdefault(s, {})[N] = [p for p in C.population(prior, N) if p in tg36]
        for N in NS82:
            P = B.POPS[s][N]
            assert not [p for p in P if p not in ap_ or p not in mpgT], (s, N)
            win, _ = F.windows_of(prior, N)
            c = Ctx()
            c.s, c.N, c.P, c.pw, c.win, c.attrs0 = s, N, P, pw, win, attrs0
            c.cfix = cfix[s]
            c.prep = prepare(s, N, fit, rel_, P)
            c.young = {p: (ages[p] <= YOUNG_MAX) if p in ages else False for p in P}
            c.age = {p: ages.get(p) for p in P}
            c.slots = {p: [(k, g) for k, _sea, g in prior_seasons_of(s, p, prior)] for p in P}
            c.Ki = {p: len(c.slots[p]) for p in P}
            c.mpg0 = {p: mpg0.get(p, 0.0) for p in P}
            c.mpg0_all = mpg0
            c.tgR = {p: B.map_g(gv(ap_[p] - RREPL, mpgT[p]), AR) for p in P}
            c.ra = {p: B.map_g(gv(pw.ref[p]['pred'] - RREPL, mpg0.get(p, 0.0)), AR) for p in P}
            c.eRA = np.array([c.ra[p] - c.tgR[p] for p in P])
            c.nbase = n095.get((s, N))
            c.gv = gv
            c.RREPL, c.AR = RREPL, AR
            ctx[(s, N)] = c
            print('cell', s, N, len(P), f'{time.time() - t0:.0f}s', flush=True)
    return ctx, info


def run_mode(c, mode, want_attrs=False):
    attrs, wst = apply_mode(c.prep, mode, c.N, c.cfix, c.young, c.slots, c.attrs0)
    pr = c.pw.predict(attrs)
    hat = B.mpg_hat(c.mpg0_all, c.win, wst, c.P, True)
    e = np.array([B.map_g(c.gv(pr[p]['pred'] - c.RREPL, hat[p]), c.AR) - c.tgR[p] for p in c.P])
    return (e, attrs, wst) if want_attrs else e


def gate_run(Ec, Eb, starts, n095):
    return E.gate(Ec, Eb, starts, n095)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stop-after-phase0', action='store_true')
    args = ap.parse_args()
    t0 = time.time()
    pre_sha = sha(HERE / 'preregistration.md')
    assert pre_sha == (HERE / 'preregistration.sha256').read_text().split()[0], '預註冊 sha 不符'
    assert pre_sha == 'd61d881918890c03795f3e30656eb3f6d4f1bb42ded7f71adc033f910fee13ac'
    ph0 = {'experiment': 'E-129 phase 0', 'preregistrationSha256': pre_sha, 'checks': {}}

    starts_all = ['Y1', 'Y2', 'Y3', 'Y5', 'Y6']
    defl, cards_info = setup(t0, starts_all)
    ph0['cards'] = cards_info
    ph0['defL'] = {rel(k): {'file': rel(v), 'sha256': sha(v)} for k, v in defl.items()}

    pool, miss = E.pool_pairs_027()
    anc = E95.anchors_for('sat15', pool)
    RREPL, AR = anc['rRepl'], anc['repl']
    rel_ = V2.load_reliability()
    sel = json.load(open(B.E033 / 'fit.json', encoding='utf-8'))['selection']
    cfix = {s: float(sel[s]['c']) for s in E.E095_STARTS}
    fit = pickle.load(open(E.FIT_CACHE, 'rb'))
    base = {}
    for r in E.rows(E.SAT15_PRED):
        base[(r['start'], int(r['N']), int(r['playerId']))] = float(r['RG1']) - float(r['targetRepl'])
    n095 = {}
    for (s, N, _p) in base:
        n095[(s, N)] = n095.get((s, N), 0) + 1

    # ---- c0y（先試 Y1、Y2 能不能建）
    c0y = {'pass': False, 'detail': {}}
    try:
        ctx, ans_info = build_cells(t0, starts_all, fit, rel_, cfix, base, n095, RREPL, AR)
        okY = True
        for s in ('Y1', 'Y2'):
            cnt = {N: len(ctx[(s, N)].P) for N in NS82}
            c0y['detail'][s] = {'P_s(N)': cnt, 'n095': {N: n095.get((s, N)) for N in NS82},
                                'sameAsE095': all(cnt[N] == n095.get((s, N)) for N in NS82),
                                'ge200': all(cnt[N] >= 200 for N in NS)}
            okY = okY and c0y['detail'][s]['ge200']
        c0y['pass'] = bool(okY)
        c0y['note'] = '先驗卡、答案卡（OVRPipeline）、PW.for_start 都建得出來'
    except Exception as ex:  # noqa: BLE001
        import traceback
        c0y['error'] = repr(ex)
        c0y['trace'] = traceback.format_exc()[-1500:]
        ctx = None
    ph0['checks']['c0y'] = c0y

    def stop(reason):
        ph0['pass'] = False
        ph0['stopReason'] = reason
        wjson(HERE / 'phase0.json', ph0)
        (HERE / 'report-phase0-stop.txt').write_text(
            'E-129 phase 0 未通過，依預註冊停下，沒有跑 §2.3 以後。\n原因：' + reason + '\n詳見 phase0.json。\n', encoding='utf-8')
        print('PHASE0 STOP', reason, flush=True)
        return 3

    if not c0y['pass']:
        return stop('c0y 不過：' + (c0y.get('error') or 'Y1/Y2 的 P_s(N) < 200'))

    # ---- c0r：K(1,1) 重現 e111 C4（Y3、Y5、Y6）
    res111 = json.loads((REPORT / 'e111-card027' / 'results.json').read_text(encoding='utf-8'))
    c0r = {'cells': [], 'notes': []}
    ok = True
    for s in ('Y3', 'Y5', 'Y6'):
        for N in NS82:
            c = ctx[(s, N)]
            e_mine = run_mode(c, BASE_MODE)
            # 原版路徑（同 process、同 e111 作法）
            g1, w1 = B.c4_run(s, N, fit, rel_, cfix[s], 1)
            pr = c.pw.predict(g1)
            hat = B.mpg_hat(c.mpg0_all, c.win, w1, c.P, True)
            e_orig = np.array([B.map_g(c.gv(pr[p]['pred'] - RREPL, hat[p]), AR) - c.tgR[p] for p in c.P])
            maxdiff = float(np.max(np.abs(e_mine - e_orig)))
            mae_m, mae_o = float(np.abs(e_mine).mean()), float(np.abs(e_orig).mean())
            row = {'start': s, 'N': N, 'n': len(c.P), 'n095': c.nbase, 'MAE_mine': mae_m, 'MAE_orig_recompute': mae_o,
                   'maxAbsErrDiff': maxdiff, 'MAEdiff_vs_recompute': abs(mae_m - mae_o)}
            # 與 e111 results.json 比（它存 6 位小數）
            gcells = res111['gates']['main' if s != 'Y3' else 'Y3']['cells']
            gr = next((x for x in gcells if x['start'] == s and x['N'] == N), None)
            if gr is not None:
                row['MAE_results_json'] = gr['MAE_C']
                row['absDiff_vs_results_json'] = abs(round(mae_m, 6) - gr['MAE_C'])
                row['MAE_A_results_json'] = gr['MAE_A']
                row['MAE_A_mine'] = float(np.abs(c.eRA).mean())
                row['A_absDiff'] = abs(round(row['MAE_A_mine'], 6) - gr['MAE_A'])
            row['pass'] = bool(maxdiff < 1e-9 and len(c.P) == c.nbase and (gr is None or row['absDiff_vs_results_json'] < 1e-9
                                                                         and row['A_absDiff'] < 1e-9))
            ok = ok and row['pass']
            c0r['cells'].append(row)
    c0r['pass'] = bool(ok)
    c0r['notes'].append('e111 results.json 的浮點數存到小數 6 位（E95.tojson），所以 1e-9 門檻用在「同 process 未四捨五入的原版重算」，'
                        '對 results.json 則比較「本程式 MAE 四捨五入到 6 位」是否完全相等。')
    # 閘門 ④ 的基準重現：Y5/Y6 baseline gate 對 e111 gates['main']
    Ec = {(s, N): run_mode(ctx[(s, N)], BASE_MODE) for s in TEST for N in NS82}
    Eb = {(s, N): ctx[(s, N)].eRA for s in TEST for N in NS82}
    g_base = gate_run(Ec, Eb, TEST, n095)
    g_ref = res111['gates']['main']
    gok = (g_base['pass'] == g_ref['pass'])
    for N in (3, 5):
        gok = gok and abs(round(g_base['V1'][N]['U_pool'], 6) - g_ref['V1'][str(N)]['U_pool']) < 1e-9 \
            and g_base['V1'][N]['pass'] == g_ref['V1'][str(N)]['pass']
    for N in (10, 20):
        gok = gok and g_base['V2'][N]['pass'] == g_ref['V2'][str(N)]['pass']
        for s in TEST:
            gok = gok and abs(round(g_base['V2'][N]['cells'][s]['ciHi'], 6) - g_ref['V2'][str(N)]['cells'][s]['ciHi']) < 1e-9
    c0r['gateBaselineReproduces'] = bool(gok)
    c0r['gateBaseline'] = {'pass': g_base['pass'], 'U_pool': {N: g_base['V1'][N]['U_pool'] for N in (3, 5)}}
    c0r['pass'] = bool(ok and gok)
    ph0['checks']['c0r'] = c0r

    # ---- c0a：開季年齡涵蓋率（P_s(20)，Y1..Y6；Y4 另建人群）
    c0a = {'perStart': {}, 'pass': True, 'ageSemantics': {}}
    for s in ['Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6']:
        prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
        try:
            if (s, 20) in ctx:
                P = ctx[(s, 20)].P
            else:
                tg36 = PA.target_ovr(s)
                P = [p for p in C.population(prior, 20) if p in tg36]
            ag = ages_of(target)
            names = {}
            pc, _ = C.load_card(prior)
            missing = [p for p in P if p not in ag]
            c0a['perStart'][s] = {'n': len(P), 'covered': len(P) - len(missing), 'coverage': (len(P) - len(missing)) / len(P),
                                  'bioRows': len(ag), 'missing': [{'playerId': p, 'name': pc[p]['name'] if p in pc else None} for p in missing]}
            c0a['pass'] = bool(c0a['pass'] and c0a['perStart'][s]['coverage'] >= 0.99)
        except Exception as ex:  # noqa: BLE001
            c0a['perStart'][s] = {'error': repr(ex)}
            c0a['pass'] = False
    # AGE 語意：連續兩季都在 bio 的球員，AGE 差的分佈
    diffs = {}
    for s in ['Y1', 'Y2', 'Y3', 'Y5', 'Y6']:
        a1, a0 = ages_of(C.CHAIN[s]['target']), ages_of(C.CHAIN[s]['prior'])
        d = [a1[p] - a0[p] for p in a1 if p in a0]
        if d:
            diffs[s] = {'n': len(d), 'median': float(np.median(d)), 'share1': float(np.mean([x == 1 for x in d]))}
    c0a['ageSemantics'] = {'AGE(target)-AGE(prior) 連續兩季都在 bio 的球員': diffs}
    ph0['checks']['c0a'] = c0a

    # ---- c0t：T 族等價檢定
    pids_t = []
    maxd1 = maxd2 = 0.0
    for s in ['Y1', 'Y2', 'Y3', 'Y5', 'Y6']:
        c = ctx[(s, 20)]
        for p in c.P:
            sl = c.slots[p]
            if not sl:
                continue
            k1, g1_ = sl[0]
            # (1) s=0, rho=1, 只有一季舊資料(forced)、N=G → 0.5
            bb, _, _ = b_T(int(g1_), [(1, g1_)], 0.0, 1.0)
            maxd1 = max(maxd1, abs(bb - 0.5))
            # (2) rho→0（1e-12） → 1
            for s_ in S_GRID:
                b2, _, _ = b_T(20, sl, s_, 1e-12)
                maxd2 = max(maxd2, abs(b2 - 1.0))
            pids_t.append(p)
    c0t = {'n': len(pids_t), 'maxAbsDiff_b05': maxd1, 'maxAbsDiff_rho0': maxd2,
           'rho0Used': 1e-12, 'pass': bool(maxd1 < 1e-9 and maxd2 < 1e-9)}
    ph0['checks']['c0t'] = c0t

    # ---- c0k：K_i 分佈
    c0k = {'perStart': {}}
    for s in ['Y1', 'Y2', 'Y3', 'Y5', 'Y6']:
        prior = C.CHAIN[s]['prior']
        c = ctx[(s, 20)]
        dist = {k: sum(1 for p in c.P if c.Ki[p] == k) for k in range(4)}
        earliest = prev_season(prior, 2)
        c0k['perStart'][s] = {'n': len(c.P), 'Ki_dist': dist, 'earliestSeasonNeeded': earliest,
                              'earliestInBoxRange': box_info(earliest) is not None,
                              'G_used': {sea: season_G(sea, None) if sea != '2019-20' else 'per-team'
                                         for sea in [prev_season(prior, k) for k in range(0, 3)]}}
    ph0['checks']['c0k'] = c0k

    hard = {k: ph0['checks'][k]['pass'] for k in ('c0r', 'c0y', 'c0a', 'c0t')}
    ph0['hardConditions'] = hard
    ph0['pass'] = bool(all(hard.values()))
    ph0['elapsedSec'] = round(time.time() - t0, 1)
    wjson(HERE / 'phase0.json', ph0)
    print('phase0', hard, f'{time.time() - t0:.0f}s', flush=True)
    if not ph0['pass']:
        bad = [k for k, v in hard.items() if not v]
        return stop('硬條件不過：' + ','.join(bad))
    if args.stop_after_phase0:
        return 0
    return run_rest(t0, ctx, n095, base, fit, rel_, cfix, RREPL, AR)


def tie_key(md):
    if md[0] == 'K':
        return (0, abs(math.log(md[1])) + abs(math.log(md[2])), 0, 0, 0)
    return (1, 0, md[1], -md[2], -md[3])


def pick_wstar(J, tie=TIE, order=None):
    jmin = min(J.values())
    ties = [md for md in J if J[md] - jmin < tie]
    return sorted(ties, key=order or tie_key)[0], ties, jmin


def mae(e):
    return float(np.abs(e).mean())


def run_rest(t0, ctx, n095, base, fit, rel_, cfix, RREPL, AR):
    out = {'experiment': 'E-129', 'preregistrationSha256': sha(HERE / 'preregistration.md')}
    modes = all_modes()
    # ---- §2.3 訓練：Y1,Y2,Y3 × N 3/5/10/20
    rows, J = [], {}
    for md in modes:
        cells = []
        for s in TRAIN:
            for N in NS:
                v = mae(run_mode(ctx[(s, N)], md))
                cells.append(v)
                rows.append({'mode': mode_name(md), 'family': md[0], 'start': s, 'N': N, 'MAE': v})
        J[md] = float(np.mean(cells))
        print('train', mode_name(md), round(J[md], 5), f'{time.time() - t0:.0f}s', flush=True)
    with open(HERE / 'train-grid.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['mode', 'family', 'param1', 'param2', 'param3', 'J'] + [f'{s}/N{N}' for s in TRAIN for N in NS])
        for md in modes:
            per = [r['MAE'] for r in rows if r['mode'] == mode_name(md)]
            ps = list(md[1:]) + [''] * (3 - len(md[1:]))
            w.writerow([mode_name(md), md[0]] + ps + [f'{J[md]:.6f}'] + [f'{x:.6f}' for x in per])
    wstar, ties, jmin = pick_wstar(J)
    argmin = min(J, key=J.get)
    # 平手規則的替代讀法（敏感度）：只取 argmin；T 內 ρ 先比 young 再 vet 已是主讀法
    alt = {'rawArgmin': mode_name(argmin), 'tieSet': [mode_name(x) for x in sorted(ties, key=tie_key)],
           'wstarIfNoTieRule': mode_name(argmin)}
    best = {fam: mode_name(min((md for md in modes if md[0] == fam), key=J.get)) for fam in 'KT'}
    bestJ = {fam: min(J[md] for md in modes if md[0] == fam) for fam in 'KT'}
    out['train'] = {'J_baseline': J[BASE_MODE], 'Jmin': jmin, 'Wstar': mode_name(wstar), 'tie': alt, 'bestPerFamily': best,
                    'bestJPerFamily': bestJ, 'J': {mode_name(md): J[md] for md in modes}}
    print('W*', mode_name(wstar), 'Jmin', jmin, 'Jbase', J[BASE_MODE], flush=True)
    out['elapsedTrainSec'] = round(time.time() - t0, 1)
    wjson(HERE / 'results.json', out)
    if wstar == BASE_MODE:
        out['verdict'] = '沒有改善'
        out['verdictReason'] = 'W* 為 K(1,1)（基準），依 §2.3 不跑測試'
        wjson(HERE / 'results.json', out)
        return 0
    return run_test(t0, ctx, n095, wstar, out)


def run_test(t0, ctx, n095, wstar, out):
    ES = {}
    Eb, Ew = {}, {}
    for s in TEST:
        for N in NS82:
            Eb[(s, N)] = run_mode(ctx[(s, N)], BASE_MODE)
            Ew[(s, N)] = run_mode(ctx[(s, N)], wstar) if N != 82 else Eb[(s, N)]
    cells = {}
    for s in TEST:
        for N in NS:
            cells[f'{s}/N{N}'] = {'n': len(ctx[(s, N)].P), 'MAE_base': mae(Eb[(s, N)]), 'MAE_Wstar': mae(Ew[(s, N)]),
                                  'dMAE': mae(Ew[(s, N)]) - mae(Eb[(s, N)])}
    c1 = [(s, N) for s in TEST for N in (10, 20)]
    pb = B.paired_boot(Ew, Eb, c1, rng_seed=1)
    cond1 = pb['hi95'] < 0
    cond2 = all(cells[f'{s}/N{N}']['dMAE'] <= 0.05 for s, N in c1)
    cond3 = all(cells[f'{s}/N{N}']['dMAE'] <= 0.05 for s in TEST for N in (3, 5))
    Ec = {k: v for k, v in Ew.items()}
    Eba = {(s, N): ctx[(s, N)].eRA for s in TEST for N in NS82}
    g = gate_run(Ec, Eba, TEST, n095)
    cond4 = bool(g['pass'])
    if cond1 and cond2 and cond3 and cond4:
        verdict = '採用'
    elif (not cond1) and cond2 and cond3 and cond4:
        verdict = '沒有改善'
    else:
        verdict = '候選較差'
    out['test'] = {'cells': cells, 'merged4': pb, 'cond1': bool(cond1), 'cond2': bool(cond2), 'cond3': bool(cond3),
                   'cond4': cond4, 'gate': {'pass': g['pass'], 'V1': g['V1'], 'V2': g['V2']}}
    out['verdict'] = verdict
    # ---- §2.5 report-only
    rng = np.random.default_rng(1)
    sub = {}
    for s in TEST:
        for N in NS:
            c = ctx[(s, N)]
            d = np.abs(Ew[(s, N)]) - np.abs(Eb[(s, N)])
            yg = np.array([c.young[p] for p in c.P])
            for lab, msk in (('young<=23', yg), ('>=24', ~yg)):
                dd = d[msk]
                if len(dd) == 0:
                    continue
                bs = [dd[rng.integers(0, len(dd), len(dd))].mean() for _ in range(2000)]
                sub[f'{s}/N{N}/{lab}'] = {'n': int(len(dd)), 'dMAE': float(dd.mean()), 'lo5': float(np.quantile(bs, .05)),
                                         'hi95': float(np.quantile(bs, .95))}
    out['young'] = sub
    mono = {}
    for s in TEST:
        for nm, E_ in (('base', Eb), ('Wstar', Ew)):
            seq = [mae(E_[(s, N)]) for N in NS82]
            mono[f'{s}/{nm}'] = {'MAE_by_N(3,5,10,20,82)': seq,
                                  'nonIncreasing': all(seq[i + 1] <= seq[i] + 1e-12 for i in range(4))}
    out['monotonicity'] = mono
    gt10 = {}
    for s in TEST:
        for N in NS:
            gt10[f'{s}/N{N}'] = {'base': int((np.abs(Eb[(s, N)]) > 10).sum()), 'Wstar': int((np.abs(Ew[(s, N)]) > 10).sum())}
    out['gt10'] = gt10
    with open(HERE / 'test-players.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['start', 'N', 'playerId', 'age', 'young', 'K_i', 'e_base', 'e_Wstar'])
        for s in TEST:
            for N in NS:
                c = ctx[(s, N)]
                for i, p in enumerate(c.P):
                    w.writerow([s, N, p, c.age[p], int(c.young[p]), c.Ki[p], f'{Eb[(s, N)][i]:.6f}', f'{Ew[(s, N)][i]:.6f}'])
    out['elapsedSec'] = round(time.time() - t0, 1)
    wjson(HERE / 'results.json', out)
    print('verdict', verdict, pb, cond1, cond2, cond3, cond4, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
