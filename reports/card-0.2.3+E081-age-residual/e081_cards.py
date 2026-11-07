"""E-081 用：複製自 reports/card-0.2.2+E073-usage-evidence/e075.py。演算法不改，只在主規格「半季評估」之後輸出 names／cand／ans／pid，然後停止（不跑敏感度、不寫卡片）。
原 docstring：E-075：E-073（把教練用人當成能力的直接證據）移到 card 0.2.2 重跑（預註冊 preregistration.md，凍結；方法本體為 card-0.2.0+E073 的 preregistration.md 與 supplement-1.md）。
用法（repo 根目錄）：
  PYTHONDONTWRITEBYTECODE=1 python reports/card-0.2.2+E073-usage-evidence/e075.py
輸出：ranking.csv（候選）、results.json、work/c0/ranking.csv（開關全關，(c0)）、work/report_data.json（report.md 用的明細）。
(c1) 讀 npm-test.exit、(c3) 讀 evaluation.json；這兩個檔不存在時 results.json 標 pending，補齊後再跑一次本腳本即可（決定性，ranking.csv 不變）。
全部決定性；bootstrap seed 1。"""
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E064 = ROOT / 'reports/card-0.1.2+E064-pergame'
E072 = ROOT / 'reports/card-0.2.0+E069-fringe-repl'
C022 = ROOT / 'reports/card-0.2.2/cards/P1'
W = HERE / 'work'
sys.path.insert(0, str(E064))
from evaluate_e064 import rho, read, FROZEN, V58, THR, MIN_G  # noqa: E402  (唯讀匯入；呼叫端設 PYTHONDONTWRITEBYTECODE=1)

POOL_MIN = 500
F_MIN_AP, F_MAX_RATE = 20, 0.5
SUS_MIN_PLAYED, SUS_MIN_AVG, SUS_RUN = 10, 24.0, 3     # §2 疑似輪休（寫死）
AGE_Y, AGE_V, D_THR = 23, 31, 0.35                      # §3.1（寫死）
NBOOT = 2000
OKC = 1610612760
COEF_NAMES = ['b0', 'b1_p', 'b2_L', 'b3_a', 'b4_y', 'b5_v', 'b6_yL', 'b7_vL', 'b8_ydL']
INJ_KEYS = ('INJURY', 'ILLNESS', 'CONCUSSION', 'RECONDITIONING', 'PERSONAL', 'SUSPENSION', 'NOT_WITH_TEAM', 'TRADE')
COACH_CODES = ('DNP_COACH', 'INACTIVE_COACH', 'INACTIVE_GLEAGUE_ON_ASSIGNMENT', 'INACTIVE_GLEAGUE_TWOWAY')
CLS_NAMES = {'P': '有出賽', 'R': '輪休', 'U': '傷病／不可上場', 'S': '疑似輪休', 'C': '教練不用'}
G5 = ['Payton Sandfort', 'Nikola Topić', 'Andre Drummond', 'Reed Sheppard', 'Jared McCain', 'Kennedy Chandler', 'Cody Williams', 'Isaiah Collier',
      'Ace Bailey', 'Branden Carlson', 'Brooks Barnhizer', 'Tyler Kolek', 'Cason Wallace', 'Isaiah Joe', 'Aaron Wiggins', 'Ty Jerome',
      'Tyrese Maxey', 'Walker Kessler', 'Giannis Antetokounmpo', 'Alex Caruso']
TEAM5 = ['UTA', 'WAS', 'BKN', 'SAC', 'DAL']

BASE_OPTS = {'inactive_noreason_to_coach': False, 'suspected': True, 'age_terms': True}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def qf(vals, mask, prc):
    ref = np.sort(np.asarray(vals)[mask])
    return float(ref[int(round(prc / 100 * (len(ref) - 1)))])


def two_segment(x, p1, p50, p99):
    return np.where(x <= p50, 40 + 30 * (x - p1) / (p50 - p1), 70 + 29 * (x - p50) / (p99 - p50))


def load_pred(path):
    rows = read(path)
    return {int(r['playerId']): {'name': r['name'], 'pos': r['pos'], 'MIN': float(r['MIN']), 'pred': float(r['pred']),
                                  'mpg': float(r['mpg']) if r['mpg'] != '' else float('nan')} for r in rows}


def jload(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ================================================================ 資料（只讀一次）
D = {}


def load_data():
    pg = jload(ROOT / 'data/season-source/player-games.json')['data']['resultSets'][0]
    h = pg['headers']
    ip, it, ia, im, ig = (h.index(k) for k in ('PLAYER_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'MIN', 'GAME_ID'))
    tmin = {s: defaultdict(lambda: defaultdict(float)) for s in ('A', 'B', 'full')}
    abbr = {}
    pl_games = defaultdict(int)
    for r in pg['rowSet']:
        abbr[r[it]] = r[ia]
        if r[im]:
            s = 'A' if int(r[ig]) % 2 == 0 else 'B'
            tmin[s][r[ip]][r[it]] += r[im]
            tmin['full'][r[ip]][r[it]] += r[im]
            pl_games[r[ip]] += 1
    D['tmin'], D['abbr'], D['pg_played_games'] = tmin, abbr, pl_games
    D['hm'] = {s: {p: sum(v.values()) for p, v in tmin[s].items()} for s in 'AB'}
    tg = jload(ROOT / 'data/season-source/team-games.json')['data']['resultSets'][0]
    h = tg['headers']
    it, ig, idt, iw = h.index('TEAM_ID'), h.index('GAME_ID'), h.index('GAME_DATE'), h.index('WL')
    sch = defaultdict(list)
    wl = defaultdict(lambda: [0, 0])
    for r in tg['rowSet']:
        sch[r[it]].append((r[idt], int(r[ig])))
        wl[r[it]][1] += 1
        wl[r[it]][0] += 1 if r[iw] == 'W' else 0
    D['sched'] = {t: [g for _, g in sorted(v)] for t, v in sch.items()}
    D['sidx'] = {t: {g: i for i, g in enumerate(v)} for t, v in D['sched'].items()}
    D['winrate'] = {t: w / n for t, (w, n) in wl.items()}
    bio = jload(ROOT / 'data/benchmark-source/bio.json')['data']['resultSets'][0]
    h = bio['headers']
    ipp, iag = h.index('PLAYER_ID'), h.index('AGE')
    D['age'] = {r[ipp]: r[iag] for r in bio['rowSet'] if r[iag] is not None}
    D['dnp'] = jload(ROOT / 'data/season-source/dnp-2025-26.json')
    D['prim'] = load_pred(C022 / 'primary/pred.csv')
    D['fitpred'] = {h_: load_pred(C022 / f'fit{h_}/pred.csv') for h_ in 'AB'}
    D['fitsum'] = {h_: jload(C022 / f'fit{h_}/pergame-summary.json') for h_ in 'AB'}
    D['mpgh'] = {h_: {int(r['playerId']): (int(r['gp']), float(r['mpg'])) for r in read(E064 / f'mpg-{h_}.csv')} for h_ in 'AB'}
    D['rapm'] = {h_: {r['name']: r for r in read(V58 / f'rapm-{h_}.csv') if r['name']} for h_ in 'AB'}
    D['base'] = list(csv.DictReader((C022 / 'primary/ranking.csv').open(encoding='utf-8')))
    D['pgr'] = {r['name']: r for r in csv.DictReader((C022 / 'primary/pergame-repl.csv').open(encoding='utf-8'))}
    D['card022_rows'] = list(csv.DictReader((C022 / 'card/ranking.csv').open(encoding='utf-8')))
    D['card022'] = {r['name']: r for r in D['card022_rows']}
    D['e072_rows'] = list(csv.DictReader((E072 / 'ranking.csv').open(encoding='utf-8')))
    D['e072'] = {r['name']: r for r in D['e072_rows']}
    D['nm2pid'] = {v['name']: p for p, v in D['prim'].items()}
    # 每人主要球隊（全季，MIN 最多；同分取 team id 小者）
    D['main_full'] = {p: max(sorted(v.items()), key=lambda kv: kv[1])[0] for p, v in tmin['full'].items()}
    # 最後一場所屬球隊（dnp json）
    last = {}
    for gid, g in D['dnp']['games'].items():
        for pid, tid, *_ in g['players']:
            if int(gid) > last.get(pid, (0, 0))[0]:
                last[pid] = (int(gid), tid)
    D['last_team'] = {p: v[1] for p, v in last.items()}


# ================================================================ §2 分類
def base_class(status, reason, mn, o):
    if mn > 0:
        return 'P'
    if 'REST' in reason:
        return 'R'
    if any(k in reason for k in INJ_KEYS):
        return 'U'
    if reason in COACH_CODES:
        return 'C'
    if reason == '':
        if status == 'ACTIVE':
            return 'C'
        if status == 'INACTIVE':
            return 'C' if o['inactive_noreason_to_coach'] else 'U'
    return 'U'   # 其他表上沒列的原因碼


def classify(o):
    rows = []
    for gid, g in D['dnp']['games'].items():
        gi = int(gid)
        for pid, tid, status, reason, mn, old in g['players']:
            rows.append([pid, tid, gi, base_class(status, reason, mn, o), mn, old])
    sus_detail = defaultdict(lambda: [0, 0.0])   # (pid,tid) -> [疑似輪休場數, 該隊有出賽場次平均分鐘]
    if o['suspected']:
        by = defaultdict(list)
        for k, r in enumerate(rows):
            by[(r[0], r[1])].append(k)
        for (pid, tid), ks in by.items():
            played = [rows[k][4] for k in ks if rows[k][3] == 'P']
            if len(played) < SUS_MIN_PLAYED or float(np.mean(played)) < SUS_MIN_AVG:
                continue
            seq = ['X'] * len(D['sched'][tid])
            where = {}
            for k in ks:
                i = D['sidx'][tid][rows[k][2]]
                seq[i] = rows[k][3]
                where[i] = k
            i = 0
            while i < len(seq):
                if seq[i] != 'C':
                    i += 1
                    continue
                j = i
                while j + 1 < len(seq) and seq[j + 1] == 'C':
                    j += 1
                if j - i + 1 < SUS_RUN:
                    for q in range(i, j + 1):
                        rows[where[q]][3] = 'S'
                        sus_detail[(pid, tid)][0] += 1
                    sus_detail[(pid, tid)][1] = float(np.mean(played))
                i = j + 1
    # 彙總
    cnt = defaultdict(int)
    agg = defaultdict(lambda: {s: [0, 0] for s in ('A', 'B')})     # pid -> half -> [A_p, played]
    cls_by_pid = defaultdict(lambda: defaultdict(int))
    old_ap = defaultdict(lambda: [0, 0])                            # E-072 A_p, played（全季）
    for pid, tid, gi, c, mn, old in rows:
        cnt[c] += 1
        cls_by_pid[pid][c] += 1
        s = 'A' if gi % 2 == 0 else 'B'
        if c in ('P', 'C'):
            agg[pid][s][0] += 1
        if c == 'P':
            agg[pid][s][1] += 1
        if old in ('played', 'coach'):
            old_ap[pid][0] += 1
        if old == 'played':
            old_ap[pid][1] += 1
    return {'rows': rows, 'cnt': dict(cnt), 'agg': agg, 'cls_by_pid': cls_by_pid, 'old_ap': old_ap, 'sus': dict(sus_detail)}


# ================================================================ 特徵與回歸
def scope_feats(scope, predmap, C, o):
    """scope in A/B/full。回傳以 pid 排序的陣列 dict。MIN：半季 = player-games 該半季加總；全季 = 卡片 MIN（pred.csv）。"""
    pids = sorted(predmap)
    n = len(pids)
    p = np.array([predmap[q]['pred'] for q in pids])
    mpg0 = np.array([0.0 if np.isnan(predmap[q]['mpg']) else predmap[q]['mpg'] for q in pids])
    if scope == 'full':
        MIN = np.array([predmap[q]['MIN'] for q in pids])
        ap = np.array([C['agg'][q]['A'][0] + C['agg'][q]['B'][0] if q in C['agg'] else 0 for q in pids])
        pl = np.array([C['agg'][q]['A'][1] + C['agg'][q]['B'][1] if q in C['agg'] else 0 for q in pids])
    else:
        MIN = np.array([D['hm'][scope].get(q, 0.0) for q in pids])
        ap = np.array([C['agg'][q][scope][0] if q in C['agg'] else 0 for q in pids])
        pl = np.array([C['agg'][q][scope][1] if q in C['agg'] else 0 for q in pids])
    has = ap > 0
    mp = np.where(has, MIN / np.where(has, ap, 1), mpg0)
    L = np.log1p(mp)
    a = np.where(has, pl / np.where(has, ap, 1), 0.0)
    age = [D['age'].get(q) for q in pids]
    y = np.array([1.0 if (x is not None and x <= AGE_Y) else 0.0 for x in age])
    v = np.array([1.0 if (x is not None and x >= AGE_V) else 0.0 for x in age])
    mainm = []
    for q in pids:
        tm = D['tmin'][scope].get(q)
        mainm.append(max(sorted(tm.items()), key=lambda kv: kv[1])[0] if tm else None)
    d = np.array([1.0 if (t is not None and D['winrate'][t] < D_THR) else 0.0 for t in mainm])
    return {'pids': pids, 'idx': {q: i for i, q in enumerate(pids)}, 'p': p, 'MIN': MIN, 'ap': ap, 'pl': pl, 'has': has, 'mp': mp, 'mpg0': mpg0,
            'L': L, 'a': a, 'y': y, 'v': v, 'd': d, 'age': age, 'main': mainm, 'n': n}


def design(sf, sel, k, p=None):
    p = sf['p'][sel] if p is None else p
    L, a, y, v, d = (sf[c][sel] for c in 'L a y v d'.split())
    cols = [np.ones_like(p), p, L, a, y, v, y * L, v * L, y * d * L]
    return np.column_stack(cols[:k])


def wls(X, y, w):
    sw = np.sqrt(w)
    return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def boot_coefs(X, y, w, groups, seed=1):
    """refit bootstrap：依球員（groups = 每列的球員代號）重抽 NBOOT 次。回傳 (NBOOT,k) 係數矩陣。"""
    rng = np.random.default_rng(seed)
    uniq = sorted(set(groups))
    rows_of = defaultdict(list)
    for i, g in enumerate(groups):
        rows_of[g].append(i)
    out = np.zeros((NBOOT, X.shape[1]))
    for b in range(NBOOT):
        draw = rng.integers(0, len(uniq), len(uniq))
        ix = [i for q in draw for i in rows_of[uniq[q]]]
        out[b] = wls(X[ix], y[ix], w[ix])
    return out


# ================================================================ 母群
def build_pools():
    rapm, fitpred, mpgh, nm2pid = D['rapm'], D['fitpred'], D['mpgh'], D['nm2pid']
    k2 = {r['name']: float(r['overall2k']) for r in read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    sets = [set(r['name'] for r in read(ROOT / p)) for p in FROZEN]
    for sc in ('0.5', '1.0'):
        for fit in 'AB':
            for k in ('E2', 'F2', 'G3', 'H1-m0'):
                sets.append(set(r['name'] for r in read(V58 / f'fit{fit}-scale{sc}' / k / 'ranking.csv')))
    common_v58 = set.intersection(*sets) & set(k2)
    names = {v['name'] for v in D['prim'].values()}
    common = common_v58 & names & {fitpred['A'][p]['name'] for p in fitpred['A']} & {fitpred['B'][p]['name'] for p in fitpred['B']}
    pools = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        pools[fit + ev] = sorted(n for n in common if n in rapm[ev] and float(rapm[ev][n]['pooledPoss']) >= THR
                                 and all(nm2pid[n] in mpgh[h] and mpgh[h][nm2pid[n]][0] >= MIN_G for h in 'AB'))
    return pools


# ================================================================ R 指標
def std_rho(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def orig_rank(x, order):
    idx = sorted(range(len(x)), key=lambda i: (x[i], order[i]))
    r = np.empty(len(x))
    for k, i in enumerate(idx):
        r[i] = k
    return r


def team_rho(rows):
    """rows：依檔案順序的 [(name, MIN, ovr)]。回傳標準 Spearman 的隊內 ρ、原腳本算法的隊內 ρ、各隊名單。"""
    by = defaultdict(list)
    for k, (nm, mn, ov) in enumerate(rows):
        if mn < 100:
            continue
        t = D['main_full'][D['nm2pid'][nm]]
        by[t].append((nm, mn, ov, k))
    std, orig, members = {}, {}, {}
    for t, v in by.items():
        if len(v) < 6:
            continue
        ab = D['abbr'][t]
        mns, ovs, od = [x[1] for x in v], [x[2] for x in v], [x[3] for x in v]
        std[ab] = std_rho(mns, ovs)
        orig[ab] = float(np.corrcoef(orig_rank(mns, od), orig_rank(ovs, od))[0, 1])
        members[ab] = [(x[0], x[1], x[2]) for x in v]
    s = sorted(std.values())
    o = sorted(orig.values())
    return {'std': std, 'orig': orig, 'members': members, 'n_teams': len(std),
            'median_std': float(np.median(s)), 'median_orig_v15': float(o[15]), 'median_orig_avg': float(np.median(o))}


def r_metrics(ovr1, names, MIN, mpg_card, Fmask, rows_in_order):
    o = ovr1
    sand, dru, shep = o['Payton Sandfort'], o['Andre Drummond'], o['Reed Sheppard']
    big = np.array([o[names[i]] for i in range(len(names)) if MIN[i] >= 1000])
    pr10 = float(np.sort(big)[int(round(0.1 * (len(big) - 1)))])
    fmed = float(np.median([o[names[i]] for i in range(len(names)) if Fmask[i]]))
    r1 = {'value': {'Sandfort': sand, 'Drummond': dru, 'Sheppard': shep}, 'threshold': 'Sandfort < min(Drummond, Sheppard)', 'pass': bool(sand < min(dru, shep))}
    r2 = {'value': {'F_n': int(Fmask.sum()), 'F_median_ovr': fmed, 'MIN>=1000_n': int(len(big)), 'MIN>=1000_PR10': pr10}, 'threshold': 'F 中位數 < MIN>=1000 的 PR10', 'pass': bool(fmed < pr10)}
    tr = team_rho(rows_in_order)
    base = D['_r3_base']
    r3 = {'value': {'candidate_median_std': tr['median_std'], 'card022_median_std': base['median_std'], 'n_teams': tr['n_teams'],
                    'reportOnly_origScript_v15_candidate': tr['median_orig_v15'], 'reportOnly_origScript_v15_card022': base['median_orig_v15']},
          'threshold': '候選中位數(標準 Spearman、第15/16小平均) >= card 0.2.2 同算法中位數', 'pass': bool(tr['median_std'] >= base['median_std'])}
    g_lo = np.array([o[names[i]] for i in range(len(names)) if MIN[i] < 100])
    pr90 = float(np.sort(g_lo)[int(round(0.9 * (len(g_lo) - 1)))])
    gr = np.array([o[names[i]] for i in range(len(names)) if MIN[i] >= 1000 and 12 <= mpg_card[i] <= 22])
    gmed = float(np.median(gr))
    r4 = {'value': {'MIN<100_n': int(len(g_lo)), 'MIN<100_PR90': pr90, 'MIN>=1000_and_12<=MPG<=22_n': int(len(gr)), 'group_median': gmed},
          'threshold': 'MIN<100 組 PR90 < MIN>=1000 且 12<=MPG<=22 組中位數（嚴格小於）', 'pass': bool(pr90 < gmed)}
    return {'R1': r1, 'R2': r2, 'R3': r3, 'R4': r4}, tr


# ================================================================ 整條管線
def pipeline(o, pools, full_report=False, half_only=False):
    C = classify(o)
    k = 9 if o['age_terms'] else 4
    prim, fitpred, rapm, nm2pid = D['prim'], D['fitpred'], D['rapm'], D['nm2pid']
    SF = {h: scope_feats(h, fitpred[h], C, o) for h in 'AB'}
    SFfull = scope_feats('full', prim, C, o)

    # 訓練列：方向 fit→ev 的係數用「ev 半季特徵 → RAPM_fit」，人群 = pools[ev+fit]
    train = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        names_t = pools[ev + fit]
        sf = SF[ev]
        sel = np.array([sf['idx'][nm2pid[n]] for n in names_t])
        X = design(sf, sel, k)
        yv = np.array([float(rapm[fit][n]['pooledNet']) for n in names_t])
        w = np.array([float(rapm[fit][n]['pooledPoss']) for n in names_t])
        train[fit + ev] = {'X': X, 'y': yv, 'w': w, 'pid': [nm2pid[n] for n in names_t], 'L': sf['L'][sel], 'a': sf['a'][sel]}
    coef = {dn: wls(t['X'], t['y'], t['w']) for dn, t in train.items()}
    Xc = np.vstack([train['AB']['X'], train['BA']['X']])
    yc = np.concatenate([train['AB']['y'], train['BA']['y']])
    wc = np.concatenate([train['AB']['w'], train['BA']['w']])
    gc = train['AB']['pid'] + train['BA']['pid']
    coef['card'] = wls(Xc, yc, wc)

    # ---- 半季評估（c2、c4）
    dirs = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        dn = fit + ev
        sf = SF[fit]
        n_all = np.arange(sf['n'])
        Xa = design(sf, n_all, k)
        pn = np.where(sf['has'], Xa @ coef[dn], sf['p'])
        fp = fitpred[fit]
        MINf = np.array([fp[q]['MIN'] for q in sf['pids']])
        pool = MINf >= POOL_MIN
        rr_base = D['fitsum'][fit]['rRepl_PR10_of_pred']
        assert abs(qf(sf['p'], pool, 10) - rr_base) < 1e-9, 'fitX 的 PR10 與 E064 summary 不同'
        rr = qf(pn, pool, 10)
        g_c = (pn - rr) * sf['mp'] / 36
        g_b = (sf['p'] - rr_base) * sf['mpg0'] / 36
        names_d = pools[dn]
        sel = np.array([sf['idx'][nm2pid[n]] for n in names_d])
        net = np.array([float(rapm[ev][n]['pooledNet']) for n in names_d])
        ans = np.array([float(rapm[ev][n]['pooledNet']) * D['mpgh'][ev][nm2pid[n]][1] for n in names_d])
        dirs[dn] = {'names': names_d, 'ans': ans, 'net': net, 'base': g_b[sel], 'cand': g_c[sel], 'p': sf['p'][sel], 'pn': pn[sel], 'rr': rr}
    rho_tab = {dn: {'c2_base': rho(d['base'], d['ans']), 'c2_cand': rho(d['cand'], d['ans']),
                    'c4_base': rho(d['p'], d['net']), 'c4_cand': rho(d['pn'], d['net'])} for dn, d in dirs.items()}
    rng = np.random.default_rng(1)
    master = sorted(set(pools['AB']) | set(pools['BA']))
    NN = len(master)
    mp_ = {dn: np.array([{n: i for i, n in enumerate(d['names'])}.get(n, -1) for n in master]) for dn, d in dirs.items()}
    b2, b4 = [], []
    for _ in range(NBOOT):
        ix = rng.integers(0, NN, NN)
        d2, d4 = [], []
        for dn, d in dirs.items():
            s = mp_[dn][ix]
            s = s[s >= 0]
            d2.append(rho(d['cand'][s], d['ans'][s]) - rho(d['base'][s], d['ans'][s]))
            d4.append(rho(d['pn'][s], d['net'][s]) - rho(d['p'][s], d['net'][s]))
        b2.append(float(np.mean(d2)))
        b4.append(float(np.mean(d4)))
    out = {'opts': dict(o), 'coef': {dn: dict(zip(COEF_NAMES[:k], map(float, c))) for dn, c in coef.items()}}
    for tag, bb in (('c2', b2), ('c4', b4)):
        pt = float(np.mean([rho_tab[dn][tag + '_cand'] - rho_tab[dn][tag + '_base'] for dn in dirs]))
        lo, hi = float(np.percentile(bb, 5)), float(np.percentile(bb, 95))
        out[tag] = {'value': {'delta': pt, 'ci90': [lo, hi], 'rho_cand': {dn: rho_tab[dn][tag + '_cand'] for dn in dirs},
                              'rho_base': {dn: rho_tab[dn][tag + '_base'] for dn in dirs}},
                    'threshold': ('下界 > -0.02' if tag == 'c2' else '下界 > 0'), 'pass': bool(lo > (-0.02 if tag == 'c2' else 0.0))}
    out['population'] = {'AB': len(pools['AB']), 'BA': len(pools['BA']), 'union': NN}
    if half_only:   # E-081：只加輸出
        out['_dirs'] = {dn: {'names': d['names'], 'pid': [int(nm2pid[n]) for n in d['names']], 'cand': [float(x) for x in d['cand']],
                             'ans': [float(x) for x in d['ans']], 'mpg_ev': [float(D['mpgh'][dn[1]][nm2pid[n]][1]) for n in d['names']],
                             'age': [D['age'].get(nm2pid[n]) for n in d['names']]} for dn, d in dirs.items()}
        out['_master'] = master
        return out

    # ---- 卡片
    sf = SFfull
    pids, N = sf['pids'], sf['n']
    names = [prim[q]['name'] for q in pids]
    MIN = sf['MIN']
    Xf = design(sf, np.arange(N), k)
    pred_new = np.where(sf['has'], Xf @ coef['card'], sf['p'])
    pool = MIN >= POOL_MIN
    mpg_card = sf['mpg0']

    def card_from(pr, mp):
        r = qf(pr, pool, 10)
        g = (pr - r) * mp / 36
        p1, p50, p99 = qf(g, pool, 1), qf(g, pool, 50), qf(g, pool, 99)
        return {'r': r, 'g': g, 'mpg': mp, 'anchors': {'PR1': p1, 'PR50': p50, 'PR99': p99}, 'ovr': two_segment(g, p1, p50, p99)}
    off = card_from(sf['p'], mpg_card)
    new = card_from(pred_new, sf['mp'])
    idx = {n: i for i, n in enumerate(names)}
    base = D['base']
    cols = list(base[0].keys()) + ['mpg', 'gRepl', 'ovr36']
    card022, e072 = D['card022'], D['e072']
    rate = np.where(sf['has'], sf['pl'] / np.where(sf['has'], sf['ap'], 1), np.nan)
    ap072 = np.array([C['old_ap'][q][0] if q in C['old_ap'] else 0 for q in pids])

    def assemble(res, extras=None):
        rows = []
        for r in base:
            i = idx[r['name']]
            oo = dict(r)
            oo['ovr36'] = r['ovr']
            oo['ovr'] = f"{res['ovr'][i]:.1f}"
            oo['mpg'] = f"{res['mpg'][i]:.2f}"
            oo['gRepl'] = f"{res['g'][i]:.4f}"
            oo['_sort'] = float(res['ovr'][i])
            if extras:
                oo.update(extras(i))
            rows.append(oo)
        return sorted(rows, key=lambda x: -x['_sort'])

    def extras(i):
        return {'Ap': int(sf['ap'][i]), 'playRate': '' if np.isnan(rate[i]) else f'{rate[i]:.3f}', 'mpgAvail': f"{sf['mp'][i]:.2f}",
                'age': '' if sf['age'][i] is None else sf['age'][i], 'p': f"{sf['p'][i]:.4f}", 'predNew': f"{pred_new[i]:.4f}",
                'Ap072': int(ap072[i]), 'ovr022': card022[names[i]]['ovr'], 'rank022': card022[names[i]]['rank']}
    cols2 = cols + ['Ap', 'playRate', 'mpgAvail', 'age', 'p', 'predNew', 'Ap072', 'ovr022', 'rank022']
    rows_c0 = assemble(off)
    rows_new = assemble(new, extras)
    ovr1 = {n: float(f"{new['ovr'][idx[n]]:.1f}") for n in names}
    ovr1_off = {n: float(f"{off['ovr'][idx[n]]:.1f}") for n in names}
    Fmask = np.array([(sf['ap'][i] >= F_MIN_AP) and (sf['pl'][i] / sf['ap'][i] < F_MAX_RATE) and MIN[i] > 0 if sf['ap'][i] > 0 else False for i in range(N)])
    # R3 基準（card 0.2.2 的檔案順序、同算法）
    if '_r3_base' not in D:
        D['_r3_base'] = team_rho([(r['name'], float(r['MIN']), float(r['ovr'])) for r in D['card022_rows']])
    rows_in_order = [(r['name'], float(r['MIN']), float(r['ovr'])) for r in rows_new]
    mpg022 = np.array([float(card022[n]['mpg']) for n in names])
    R, tr = r_metrics(ovr1, names, MIN, mpg022, Fmask, rows_in_order)
    out.update(R)
    out['card'] = {'r_repl': new['r'], 'anchors': new['anchors'], 'F_n': int(Fmask.sum())}

    if not full_report:
        return out
    # ================= 只有主跑才算的明細
    (W / 'c0').mkdir(parents=True, exist_ok=True)
    for path, rws, cl in ((W / 'c0/ranking.csv', rows_c0, cols), (HERE / 'ranking.csv', rows_new, cols2)):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cl, extrasaction='ignore', lineterminator='\n')
            w.writeheader()
            for i, oo in enumerate(rws, 1):
                oo = dict(oo)
                oo['rank'] = i
                w.writerow(oo)
    maxdiff = max(abs(off['ovr'][idx[n]] - float(D['pgr'][n]['ovr'])) for n in names)
    s0 = sha(W / 'c0/ranking.csv')
    c022 = sha(C022 / 'card/ranking.csv')
    out['c0'] = {'value': {'c0_ranking_sha256': s0, 'card022_sha256': c022, 'byteIdentical': s0 == c022, 'maxAbsOvrDiffVsPergameRepl': float(maxdiff)},
                 'threshold': 'sha256 相同，或數值最大差 < 1e-9', 'pass': bool(s0 == c022 or maxdiff < 1e-9)}
    rank_new = {r['name']: k_ for k_, r in enumerate(rows_new, 1)}

    rep = {}
    # ---- 分類
    cnt = C['cnt']
    old_cnt = D['dnp']['categoryCounts']
    rep['class_counts'] = {CLS_NAMES[c]: cnt.get(c, 0) for c in 'PRUSC'}
    rep['class_counts_E072_cat'] = {'played': 0, 'coach': 0, 'unavail': 0}
    for r in C['rows']:
        rep['class_counts_E072_cat'][r[5]] += 1
    sus = []
    for (pid, tid), (n, avg) in sorted(C['sus'].items(), key=lambda kv: -kv[1][0]):
        sus.append({'name': prim[pid]['name'], 'team': D['abbr'][tid], 'games': n, 'avgMIN_with_team': avg})
    rep['suspected'] = sus
    rep['suspected_total'] = int(sum(s['games'] for s in sus))
    rs = []
    for pid, cc in C['cls_by_pid'].items():
        if pid not in prim:
            continue
        if cc.get('R', 0) + cc.get('S', 0) >= 5:
            i = sf['idx'][pid]
            ap_o, pl_o = C['old_ap'][pid]
            rs.append({'name': prim[pid]['name'], 'rest': cc.get('R', 0), 'suspected': cc.get('S', 0), 'Ap072': ap_o,
                       'rate072': (pl_o / ap_o if ap_o else None), 'Ap': int(sf['ap'][i]), 'rate': (None if np.isnan(rate[i]) else float(rate[i]))})
    rep['rest_players'] = sorted(rs, key=lambda x: -(x['rest'] + x['suspected']))
    # 與 player-games 對照
    mism = []
    for pid in pids:
        pl_dnp = sum(1 for _ in ())  # placeholder, 下面實算
    pl_by = defaultdict(int)
    for r in C['rows']:
        if r[3] == 'P':
            pl_by[r[0]] += 1
    mism = [(prim[q]['name'], pl_by.get(q, 0), D['pg_played_games'].get(q, 0)) for q in pids if pl_by.get(q, 0) != D['pg_played_games'].get(q, 0)]
    minmis = [(prim[q]['name'], float(prim[q]['MIN']), D['hm']['A'].get(q, 0.0) + D['hm']['B'].get(q, 0.0)) for q in pids
              if abs(prim[q]['MIN'] - D['hm']['A'].get(q, 0.0) - D['hm']['B'].get(q, 0.0)) > 0.5]
    rep['crosscheck'] = {'played_games_mismatch_n': len(mism), 'played_games_mismatch_head': mism[:10],
                         'MIN_card_vs_playergames_mismatch_n': len(minmis), 'MIN_mismatch_head': minmis[:10],
                         'players_without_bio_age': int(sum(1 for x in sf['age'] if x is None)),
                         'players_without_bio_age_names_head': [names[i] for i in range(N) if sf['age'][i] is None][:15],
                         'players_Ap0': [names[i] for i in range(N) if sf['ap'][i] == 0]}
    # ---- 回歸
    ci = {}
    for dn in ('AB', 'BA', 'card'):
        if dn == 'card':
            bc = boot_coefs(Xc, yc, wc, gc)
        else:
            t = train[dn]
            bc = boot_coefs(t['X'], t['y'], t['w'], t['pid'])
        ci[dn] = {nm: {'coef': float(coef[dn][j]), 'ci90': [float(np.percentile(bc[:, j], 5)), float(np.percentile(bc[:, j], 95))]} for j, nm in enumerate(COEF_NAMES[:k])}
    rep['coef_ci'] = ci
    Lall = np.concatenate([train['AB']['L'], train['BA']['L']])
    aall = np.concatenate([train['AB']['a'], train['BA']['a']])
    Lr, ar = (float(Lall.min()), float(Lall.max())), (float(aall.min()), float(aall.max()))
    hs = sf['has']
    outL = hs & ((sf['L'] < Lr[0]) | (sf['L'] > Lr[1]))
    outA = hs & ((sf['a'] < ar[0]) | (sf['a'] > ar[1]))
    rep['fit_range'] = {'L': Lr, 'a': ar, 'train_n': int(len(Lall)), 'train_n_AB': len(train['AB']['y']), 'train_n_BA': len(train['BA']['y']),
                        'train_y_n': int(np.sum(np.concatenate([[1]] * 0 + [train[d_]['X'][:, 4] for d_ in ('AB', 'BA')]))) if k > 4 else None,
                        'card_outside_L': int(outL.sum()), 'card_outside_a': int(outA.sum()), 'card_outside_either': int((outL | outA).sum()),
                        'card_players_with_Ap': int(hs.sum()),
                        'pred_new_min': float(pred_new.min()), 'pred_new_min_name': names[int(np.argmin(pred_new))],
                        'pred_new_PR1_all': float(np.percentile(pred_new, 1)), 'pred_new_PR1_MIN500pool': qf(pred_new, pool, 1),
                        'pred_new_PR10_pool(r_repl)': new['r'], 'p_PR10_pool': off['r'],
                        'train_d_ones_in_rows': int(np.sum(np.concatenate([train[d_]['X'][:, 8] != 0 for d_ in ('AB', 'BA')]))) if k > 4 else None}
    # ---- 分佈
    ovr022 = {n: float(card022[n]['ovr']) for n in names}
    ovr072 = {n: float(e072[n]['ovr']) for n in names}
    grp = {'<100': MIN < 100, '100-300': (MIN >= 100) & (MIN < 300), '300-1000': (MIN >= 300) & (MIN < 1000), '>=1000': MIN >= 1000}
    rep['groups'] = {kk: {'n': int(m_.sum()), 'median_E073': float(np.median([ovr1[names[i]] for i in range(N) if m_[i]])),
                          'median_card022': float(np.median([ovr022[names[i]] for i in range(N) if m_[i]])),
                          'median_E072': float(np.median([ovr072[names[i]] for i in range(N) if m_[i]]))} for kk, m_ in grp.items()}
    big = MIN >= 1000
    rep['gNeg_MIN1000'] = {'card022': int(((off['g'] < 0) & big).sum()), 'E073': int(((new['g'] < 0) & big).sum())}
    top20 = [{'rank': k_, 'name': r['name'], 'pos': r['pos'], 'ovr': r['ovr'], 'rank022': r['rank022'], 'ovr022': r['ovr022']} for k_, r in enumerate(rows_new[:20], 1)]
    rep['top20'] = top20
    rep['bigsTop10'] = [t['name'] for t in top20[:10] if t['pos'] in ('C', 'PF')]
    top10_022 = sorted(card022.values(), key=lambda r: int(r['rank']))[:10]
    rep['bigsTop10_card022'] = [r['name'] for r in top10_022 if r['pos'] in ('C', 'PF')]
    # ---- R-035
    base_tr = D['_r3_base']
    rep['r035'] = {'teams': {ab: {'cand': tr['std'][ab], 'card022': base_tr['std'].get(ab)} for ab in sorted(tr['std'])},
                   'orig_script': {'cand_v15': tr['median_orig_v15'], 'card022_v15': base_tr['median_orig_v15'],
                                   'cand_avg': tr['median_orig_avg'], 'card022_avg': base_tr['median_orig_avg']},
                   'within_team': {}}
    for ab in TEAM5:
        mem = sorted(tr['members'].get(ab, []), key=lambda x: -x[1])
        rep['r035']['within_team'][ab] = [{'name': nm, 'MIN': mn, 'ovr': ov, 'ovr022': ovr022[nm], 'rank_in_team': j + 1} for j, (nm, mn, ov) in enumerate(mem)]
    old = []
    for i in range(N):
        a_ = sf['age'][i]
        if a_ is not None and a_ >= 33 and MIN[i] >= 500:
            old.append({'name': names[i], 'age': a_, 'MIN': float(MIN[i]), 'ovr': ovr1[names[i]], 'rank': rank_new[names[i]],
                        'ovr022': ovr022[names[i]], 'rank022': int(card022[names[i]]['rank'])})
    rep['age33'] = sorted(old, key=lambda x: x['rank'])
    # ---- G5、OKC
    g5 = []
    for n in G5:
        if n not in idx:
            g5.append({'name': n, 'missing': True})
            continue
        i = idx[n]
        g5.append({'name': n, 'MIN': float(MIN[i]), 'Ap': int(sf['ap'][i]), 'playRate': None if np.isnan(rate[i]) else float(rate[i]),
                   'mpgAvail': float(sf['mp'][i]), 'age': sf['age'][i], 'p': float(sf['p'][i]), 'predNew': float(pred_new[i]),
                   'ovr': ovr1[n], 'rank': rank_new[n], 'ovr022': ovr022[n], 'rank022': int(card022[n]['rank'])})
    rep['G5'] = g5
    okc = [i for i, q in enumerate(pids) if D['last_team'].get(q) == OKC and MIN[i] >= 300]
    okc.sort(key=lambda i: -new['ovr'][i])
    ord022 = sorted(okc, key=lambda i: -ovr022[names[i]])
    rep['OKC'] = [{'name': names[i], 'MIN': float(MIN[i]), 'ovr': ovr1[names[i]], 'ovr022': ovr022[names[i]], 'rank_in_team': j + 1, 'rank022_in_team': ord022.index(i) + 1}
                  for j, i in enumerate(okc)]
    rep['anchors'] = {'card022': off['anchors'], 'E073': new['anchors']}
    out['_report'] = rep
    out['_ovr1'] = ovr1
    return out


def main():
    load_data()
    pools = build_pools()
    r = pipeline(BASE_OPTS, pools, half_only=True)
    ref = jload(ROOT / 'reports/card-0.2.2+E073-usage-evidence/results.json')['checks']['c2']['value']
    k0 = {'delta': [r['c2']['value']['delta'], ref['delta']], 'ci90': [r['c2']['value']['ci90'], ref['ci90']],
          'rho_cand': [r['c2']['value']['rho_cand'], ref['rho_cand']], 'rho_base': [r['c2']['value']['rho_base'], ref['rho_base']]}
    diffs = [abs(r['c2']['value']['delta'] - ref['delta']), abs(r['c2']['value']['ci90'][0] - ref['ci90'][0]), abs(r['c2']['value']['ci90'][1] - ref['ci90'][1])]
    for dn in ('AB', 'BA'):
        diffs += [abs(r['c2']['value']['rho_cand'][dn] - ref['rho_cand'][dn]), abs(r['c2']['value']['rho_base'][dn] - ref['rho_base'][dn])]
    k0_out = {'maxAbsDiff': max(diffs), 'pass': bool(max(diffs) < 1e-9), 'values_this_run_vs_E075': k0, 'threshold': '< 1e-9'}
    out = {'k0': k0_out, 'population': r['population'], 'dirs': r['_dirs'], 'master': r['_master'],
           'sha256': {'e075.py': sha(ROOT / 'reports/card-0.2.2+E073-usage-evidence/e075.py'),
                      'results.json(E-075)': sha(ROOT / 'reports/card-0.2.2+E073-usage-evidence/results.json')}}
    (HERE / 'cards.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'k0': k0_out, 'population': r['population']}, ensure_ascii=False, indent=1))
    assert k0_out['pass'], '(k0) 自檢失敗，停下回報'


if __name__ == '__main__':
    main()
