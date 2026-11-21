"""E-084：用人回歸的訓練目標改成 2025-26 單季 RAPM（預註冊 preregistration.md，凍結，sha256 見 preregistration.sha256）。
由 reports/card-0.2.2+E073-usage-evidence/e075.py 複製，加開關 --target {pooled,season}（預設 pooled，必須與 E-075 完全相同），
再加 season 模式的評估（照 reports/card-0.2.3+E081-age-residual/e081.py 的定義）。差異見 diff-e075.txt、diff-e081.txt。
用法（repo 根目錄；先跑 pooled 做 (c0)，過了才跑 season）：
  PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 python reports/card-0.2.3+E084-current-target/e084.py --target pooled
  PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 python reports/card-0.2.3+E084-current-target/e084.py --target season
輸出：pooled → work/pooled/（c0.json、ranking.csv 為 card 0.2.3 格式）；season → ranking.csv（候選，card 0.2.3 格式）、results.json、work/season/。
(c1) 讀 npm-test.exit、(c3) 讀 evaluation.json；這兩個檔不存在時 results.json 標 pending，補齊後再跑一次本腳本即可（決定性，ranking.csv 不變）。
全部決定性；bootstrap seed 1。"""
import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
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
E075D = ROOT / 'reports/card-0.2.2+E073-usage-evidence'
E081D = ROOT / 'reports/card-0.2.3+E081-age-residual'
E082D = ROOT / 'reports/card-0.2.3+E082-position-shares'
C023 = ROOT / 'reports/card-0.2.3/ranking.csv'
C022_PUB = ROOT / 'reports/card-0.2.2/ranking.csv'
W = HERE / 'work'
TARGET = 'pooled'   # main() 依 --target 改寫；pipeline 預設讀這個
AGE_GROUPS = [('<=23', lambda a: a <= 23), ('24-27', lambda a: 24 <= a <= 27), ('28-30', lambda a: 28 <= a <= 30), ('>=31', lambda a: a >= 31)]
NAMED = ['Paolo Banchero', 'Jalen Williams', 'Jalen Johnson']
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
    # E-084：fit 半季只用 2025-26 比賽的 RAPM（E-081 的 rapm1，唯讀）與 card 0.2.3 檔
    D['rapm1'] = {h_: {int(r['playerId']): {k_: float(r[k_]) for k_ in ('net', 'O', 'D', 'poss')} | {'name': r['name']}
                       for r in csv.DictReader((E081D / f'rapm1-{h_}.csv').open(encoding='utf-8'))} for h_ in 'AB'}
    D['card023_rows'] = list(csv.DictReader(C023.open(encoding='utf-8')))
    D['card023'] = {r['name']: r for r in D['card023_rows']}
    D['card022_pub_rows'] = list(csv.DictReader(C022_PUB.open(encoding='utf-8')))
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


def r_metrics(ovr1, names, MIN, mpg_card, Fmask, rows_in_order, mpg_alt=None):
    o = ovr1
    sand, dru, shep = o['Payton Sandfort'], o['Andre Drummond'], o['Reed Sheppard']
    big = np.array([o[names[i]] for i in range(len(names)) if MIN[i] >= 1000])
    pr10 = float(np.sort(big)[int(round(0.1 * (len(big) - 1)))])
    fmed = float(np.median([o[names[i]] for i in range(len(names)) if Fmask[i]]))
    r1 = {'value': {'Sandfort': sand, 'Drummond': dru, 'Sheppard': shep}, 'threshold': 'Sandfort < min(Drummond, Sheppard)', 'pass': bool(sand < min(dru, shep))}
    r2 = {'value': {'F_n': int(Fmask.sum()), 'F_median_ovr': fmed, 'MIN>=1000_n': int(len(big)), 'MIN>=1000_PR10': pr10}, 'threshold': 'F 中位數 < MIN>=1000 的 PR10', 'pass': bool(fmed < pr10)}
    tr = team_rho(rows_in_order)
    base = D['_r3_base']
    r3 = {'value': {'candidate_median_std': tr['median_std'], 'card023_median_std': base['median_std'], 'n_teams': tr['n_teams'],
                    'reportOnly_origScript_v15_candidate': tr['median_orig_v15'], 'reportOnly_origScript_v15_card023': base['median_orig_v15']},
          'threshold': '候選中位數(標準 Spearman、第15/16小平均) >= card 0.2.3 同算法中位數', 'pass': bool(tr['median_std'] >= base['median_std'])}
    g_lo = np.array([o[names[i]] for i in range(len(names)) if MIN[i] < 100])
    pr90 = float(np.sort(g_lo)[int(round(0.9 * (len(g_lo) - 1)))])
    gr = np.array([o[names[i]] for i in range(len(names)) if MIN[i] >= 1000 and 12 <= mpg_card[i] <= 22])
    gmed = float(np.median(gr))
    r4 = {'value': {'MIN<100_n': int(len(g_lo)), 'MIN<100_PR90': pr90, 'MIN>=1000_and_12<=MPG<=22_n': int(len(gr)), 'group_median': gmed},
          'threshold': 'MIN<100 組 PR90 < MIN>=1000 且 12<=MPG<=22 組中位數（嚴格小於）', 'pass': bool(pr90 < gmed)}
    if mpg_alt is not None:   # 只報告：MPG 分組改用 card 0.2.3 的 mpg 欄（預註冊沒寫，E-075 原式用 card 0.2.2 的 mpg）
        gr2 = np.array([o[names[i]] for i in range(len(names)) if MIN[i] >= 1000 and 12 <= mpg_alt[i] <= 22])
        r4['reportOnly_mpg_from_card023'] = {'group_n': int(len(gr2)), 'group_median': float(np.median(gr2)), 'pass': bool(pr90 < float(np.median(gr2)))}
    return {'R1': r1, 'R2': r2, 'R3': r3, 'R4': r4}, tr


# ================================================================ 整條管線
def pipeline(o, pools, target='pooled', full_report=False):
    C = classify(o)
    k = 9 if o['age_terms'] else 4
    prim, fitpred, rapm, nm2pid = D['prim'], D['fitpred'], D['rapm'], D['nm2pid']
    SF = {h: scope_feats(h, fitpred[h], C, o) for h in 'AB'}
    SFfull = scope_feats('full', prim, C, o)

    # 訓練列：方向 fit→ev 的係數用「ev 半季特徵 → RAPM_fit」，人群 = pools[ev+fit]
    train, dropped = {}, {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        names_t = pools[ev + fit]
        if target == 'season':   # E-084 §2：人群不變，在 rapm1 找不到的人只從訓練列剔除
            r1 = D['rapm1'][fit]
            dropped[fit + ev] = [n for n in names_t if nm2pid[n] not in r1]
            names_t = [n for n in names_t if nm2pid[n] in r1]
        sf = SF[ev]
        sel = np.array([sf['idx'][nm2pid[n]] for n in names_t])
        X = design(sf, sel, k)
        if target == 'season':   # E-084 §2：訓練目標 = fit 半季只用 2025-26 比賽的 RAPM net；權重 = 其 poss
            yv = np.array([D['rapm1'][fit][nm2pid[n]]['net'] for n in names_t])
            w = np.array([D['rapm1'][fit][nm2pid[n]]['poss'] for n in names_t])
        else:
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
        pid_d = [nm2pid[n] for n in names_d]
        r1e = D['rapm1'][ev]
        mpg_ev = np.array([D['mpgh'][ev][q][1] for q in pid_d])
        netN = np.array([r1e[q]['net'] if q in r1e else np.nan for q in pid_d])
        age_d = np.array([float(D['age'][q]) if D['age'].get(q) is not None else np.nan for q in pid_d])
        dirs[dn] = {'names': names_d, 'ans': ans, 'net': net, 'base': g_b[sel], 'cand': g_c[sel], 'p': sf['p'][sel], 'pn': pn[sel], 'rr': rr,
                    'pid': pid_d, 'age': age_d, 'mpg_ev': mpg_ev, 'netN': netN}
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
        D['_r3_base'] = team_rho([(r['name'], float(r['MIN']), float(r['ovr'])) for r in D['card023_rows']])
    rows_in_order = [(r['name'], float(r['MIN']), float(r['ovr'])) for r in rows_new]
    mpg022 = np.array([float(card022[n]['mpg']) for n in names])
    mpg023 = np.array([float(D['card023'][n]['mpg']) for n in names])
    R, tr = r_metrics(ovr1, names, MIN, mpg022, Fmask, rows_in_order, mpg_alt=mpg023)
    out.update(R)
    out['card'] = {'r_repl': new['r'], 'anchors': new['anchors'], 'F_n': int(Fmask.sum())}
    out['train_info'] = {'target': target, 'n_AB': len(train['AB']['y']), 'n_BA': len(train['BA']['y']),
                         'dropped_from_training_rows': {dn: {'n': len(v), 'names': v} for dn, v in dropped.items()}}
    # card 0.2.3 格式的 ranking 列（build_card_023.py：rank、ovr、mpg、gRepl 取新值，其餘欄位取 card 0.2.2 依姓名）
    pub = {r['name']: r for r in D['card022_pub_rows']}
    cols23 = list(D['card022_pub_rows'][0].keys())
    rows23 = []
    for k_, r in enumerate(rows_new, 1):
        oo = dict(pub[r['name']])
        oo['rank'] = str(k_)
        oo['ovr'], oo['mpg'], oo['gRepl'] = r['ovr'], r['mpgAvail'], r['gRepl']
        rows23.append(oo)
    out['_aux'] = {'cols23': cols23, 'rows23': rows23, 'pred_new': pred_new, 'names': names, 'MIN': MIN, 'age': sf['age'], 'dirs': dirs,
                   'ovr1': ovr1, 'coef_raw': coef, 'train': train, 'Xc': Xc, 'yc': yc, 'wc': wc, 'gc': gc}
    return out




# ================================================================ E-084 評估（照 e081.py 的定義；人群 = E-075 pools[dn]）
def pct(x):
    """0-1 百分位名次，同分取平均名次：(avg_rank - 1) / (n - 1)（同 e081.py）。"""
    return (rankdata(x) - 1.0) / (len(x) - 1.0)


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return float('nan')
    return float(np.corrcoef(ra, rb)[0, 1])


DNS = ('AB', 'BA')


def season_eval(cdirs, bdirs):
    """候選（cdirs）對基準（bdirs，card 0.2.3）。答案 N = rapm1 net × mpg_ev；答案 Q = E-064 ans（pooledNet × mpg）。
    S = Spearman(年齡, u)，u = pct(答案) − pct(卡片)，在「有年齡且有 rapm1」的人群上算一次（重抽內不重排，同 e081 主分析）。
    rho_N：答案 N，限有 rapm1 的人；rho_Q：答案 Q，全 pools[dn]；c4：rho(pn, netN) − rho(p, netN)，限有 rapm1 的人。
    bootstrap：master = pools 名單聯集（排序），default_rng(1)，ix 兩方向共用、候選與基準共用。"""
    E = {}
    for dn in DNS:
        c, b = cdirs[dn], bdirs[dn]
        assert c['names'] == b['names'] and np.array_equal(c['pid'], b['pid']) and np.array_equal(c['p'], b['p']), '候選與基準人群不一致'
        age, netN = c['age'], c['netN']
        keep = ~np.isnan(age) & ~np.isnan(netN)
        hasN = ~np.isnan(netN)
        ansN = netN * c['mpg_ev']
        ansQ = c['ans']
        ik = np.where(keep)[0]
        e = {'age': age, 'keep': keep, 'hasN': hasN, 'ansN': ansN, 'ansQ': ansQ, 'netN': netN, 'cand_c': c['cand'], 'cand_b': b['cand'],
             'p': c['p'], 'pn': c['pn'], 'names': c['names']}
        for tag, g in (('c', c['cand']), ('b', b['cand'])):
            for ak, ans in (('N', ansN), ('Q', ansQ)):
                u = np.full(len(age), np.nan)
                u[ik] = pct(ans[ik]) - pct(g[ik])
                e['u' + ak + tag] = u
        e['gm'] = {g: np.array([(not np.isnan(a)) and f(a) for a in age]) for g, f in AGE_GROUPS}
        e['n_kept'] = int(keep.sum())
        e['n_hasN'] = int(hasN.sum())
        E[dn] = e

    def stats(sel):
        r = defaultdict(list)
        for dn in DNS:
            e, s = E[dn], sel[dn]
            sk = s[e['keep'][s]]
            sn = s[e['hasN'][s]]
            for tag in ('c', 'b'):
                for ak in ('N', 'Q'):
                    u = e['u' + ak + tag]
                    r[f'S{ak}_{tag}'].append(spearman(e['age'][sk], u[sk]))
                    for g, _ in AGE_GROUPS:
                        m = e['gm'][g][sk]
                        r[f'g{ak}_{tag}_{g}'].append(float(u[sk][m].mean()) if m.any() else float('nan'))
                cd = e['cand_' + tag]
                r[f'rhoN_{tag}'].append(rho(cd[sn], e['ansN'][sn]))
                r[f'rhoQ_{tag}'].append(rho(cd[s], e['ansQ'][s]))
            r['c4_c'].append(rho(e['pn'][sn], e['netN'][sn]))
            r['c4_b'].append(rho(e['p'][sn], e['netN'][sn]))
        return r

    def red(r):
        return {k: float(np.nanmean(v)) for k, v in r.items()}

    full = {dn: np.arange(len(E[dn]['age'])) for dn in DNS}
    raw = stats(full)
    pt = red(raw)
    master = sorted(set(E['AB']['names']) | set(E['BA']['names']))
    NN = len(master)
    mp_ = {dn: np.array([{n: i for i, n in enumerate(E[dn]['names'])}.get(n, -1) for n in master]) for dn in DNS}
    rng = np.random.default_rng(1)
    boots = defaultdict(list)
    for _ in range(NBOOT):
        ix = rng.integers(0, NN, NN)
        sel = {}
        for dn in DNS:
            s = mp_[dn][ix]
            sel[dn] = s[s >= 0]
        for k_, v in red(stats(sel)).items():
            boots[k_].append(v)

    def ci(b):
        b = np.array(b, dtype=float)
        return [float(np.nanpercentile(b, 5)), float(np.nanpercentile(b, 95))]

    def diff_of(a, b):
        return {'point': pt[a] - pt[b], 'ci90': ci(np.array(boots[a]) - np.array(boots[b]))}
    res = {'n': {dn: {'pool': len(E[dn]['age']), 'kept_age_rapm1': E[dn]['n_kept'], 'with_rapm1': E[dn]['n_hasN']} for dn in DNS},
           'master_size': NN, 'n_boot': NBOOT, 'seed': 1}
    for tag, nm in (('c', 'cand'), ('b', 'card023')):
        for ak in ('N', 'Q'):
            res[f'S_{ak}_{nm}'] = {'point': pt[f'S{ak}_{tag}'], 'ci90': ci(boots[f'S{ak}_{tag}']),
                                   'per_direction': {dn: raw[f'S{ak}_{tag}'][i] for i, dn in enumerate(DNS)}}
            res[f'groups_{ak}_{nm}'] = {g: {'mean_u': pt[f'g{ak}_{tag}_{g}'], 'ci90': ci(boots[f'g{ak}_{tag}_{g}']),
                                            'n': {dn: int(E[dn]['gm'][g][E[dn]['keep']].sum()) for dn in DNS},
                                            'mean_u_dir': {dn: raw[f'g{ak}_{tag}_{g}'][i] for i, dn in enumerate(DNS)}} for g, _ in AGE_GROUPS}
        res[f'rho_N_{nm}'] = {'point': pt[f'rhoN_{tag}'], 'per_direction': {dn: raw[f'rhoN_{tag}'][i] for i, dn in enumerate(DNS)}}
        res[f'rho_Q_{nm}'] = {'point': pt[f'rhoQ_{tag}'], 'per_direction': {dn: raw[f'rhoQ_{tag}'][i] for i, dn in enumerate(DNS)}}
    res['dS_N'] = diff_of('SN_c', 'SN_b')            # (b)
    res['dS_Q'] = diff_of('SQ_c', 'SQ_b')            # 只報告
    res['dRho_N'] = diff_of('rhoN_c', 'rhoN_b')      # (c2N)
    res['dRho_Q'] = diff_of('rhoQ_c', 'rhoQ_b')      # (c2Q)
    res['c4'] = {'point': pt['c4_c'] - pt['c4_b'], 'ci90': ci(np.array(boots['c4_c']) - np.array(boots['c4_b'])),
                 'rho_pn': {dn: raw['c4_c'][i] for i, dn in enumerate(DNS)}, 'rho_p': {dn: raw['c4_b'][i] for i, dn in enumerate(DNS)}}
    res['checks'] = {
        'b': {'value': res['dS_N'], 'threshold': 'ΔS_N 下界 > 0', 'pass': bool(res['dS_N']['ci90'][0] > 0)},
        'c2N': {'value': res['dRho_N'], 'threshold': 'Δρ_N 下界 > -0.02', 'pass': bool(res['dRho_N']['ci90'][0] > -0.02)},
        'c2Q': {'value': res['dRho_Q'], 'threshold': 'Δρ_Q 下界 > -0.05', 'pass': bool(res['dRho_Q']['ci90'][0] > -0.05)},
        'c4': {'value': {'delta': res['c4']['point'], 'ci90': res['c4']['ci90'], 'rho_pn': res['c4']['rho_pn'], 'rho_p': res['c4']['rho_p']},
               'threshold': '下界 > 0', 'pass': bool(res['c4']['ci90'][0] > 0)}}
    return res


# ================================================================ (c0)
def leaves(x, pre=''):
    if isinstance(x, dict):
        for k_, v in x.items():
            yield from leaves(v, pre + '/' + str(k_))
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from leaves(v, pre + f'[{i}]')
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield pre, float(x)


def write_rank(path, cols, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def rank_equal(pa, pb, tol=1e-9):
    """兩個 ranking.csv 共同欄位：字串須相同，兩邊都能轉數字者最大差 < tol。回傳 (ok, maxdiff)。"""
    ra = list(csv.DictReader(open(pa, encoding='utf-8')))
    rb = list(csv.DictReader(open(pb, encoding='utf-8')))
    if len(ra) != len(rb) or list(ra[0].keys()) != list(rb[0].keys()):
        return False, None
    md = 0.0
    for x, y in zip(ra, rb):
        for c_ in x:
            if x[c_] == y[c_]:
                continue
            try:
                d_ = abs(float(x[c_]) - float(y[c_]))
            except ValueError:
                return False, None
            md = max(md, d_)
            if not d_ < tol:
                return False, None
    return True, md


def run_c0(pools):
    res = pipeline(BASE_OPTS, pools, 'pooled')
    e075 = jload(E075D / 'results.json')
    ok_val, md = True, 0.0
    for tag in ('c2', 'c4'):
        a = dict(leaves(res[tag]['value']))
        b = dict(leaves(e075['checks'][tag]['value']))
        if set(a) != set(b):
            ok_val = False
            continue
        md = max(md, max(abs(a[k_] - b[k_]) for k_ in a))
    ok_val = bool(ok_val and md < 1e-9)
    aux = res['_aux']
    pth = W / 'pooled/ranking.csv'
    write_rank(pth, aux['cols23'], aux['rows23'])
    sha_eq = bool(sha(pth) == sha(C023))
    cols_ok, md_r = (True, 0.0) if sha_eq else rank_equal(pth, C023)
    coef_ok = bool(all(abs(res['coef'][dn][k_] - e075['coefficients'][dn][k_]) < 1e-9 for dn in ('AB', 'BA', 'card') for k_ in COEF_NAMES))
    passed = bool(ok_val and (sha_eq or cols_ok))
    c0 = {'pass': passed, 'c2_c4_equal_E075': ok_val, 'ranking_sha256_equal_card023': sha_eq, 'ranking_shared_cols_equal': bool(cols_ok),
          'coefficients_equal_E075': coef_ok, 'ranking_sha256': sha(pth), 'card023_sha256': sha(C023)}
    if passed:   # 只在通過時記數字（預註冊 §4：不過就停，不看誤差數字）
        c0['max_diff_c2_c4'] = md
        c0['max_diff_ranking_numeric'] = md_r
    (W / 'pooled').mkdir(parents=True, exist_ok=True)
    (W / 'pooled/c0.json').write_text(json.dumps(c0, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k_: v for k_, v in c0.items() if isinstance(v, bool)}, ensure_ascii=False))
    return 0 if passed else 1


# ================================================================ season 模式
def strip_aux(o):
    return {k_: v for k_, v in o.items() if k_ != '_aux'}


def gates_of(res, ev, c1=None, c3=None):
    """res = pipeline 輸出（R2–R4）；ev = season_eval 輸出。c1、c3 為 None 表示尚未取得。"""
    return {'c1': c1, 'b': ev['checks']['b']['pass'], 'c2N': ev['checks']['c2N']['pass'], 'c2Q': ev['checks']['c2Q']['pass'], 'c3': c3,
            'c4': ev['checks']['c4']['pass'], 'R2': res['R2']['pass'], 'R3': res['R3']['pass'], 'R4': res['R4']['pass']}


def decide(c0_pass, g, ev):
    allg = {'c0': c0_pass, **g}
    fails = [k_ for k_, v in allg.items() if v is False]
    pend = [k_ for k_, v in allg.items() if v is None]
    if fails:
        if g['b'] and (g['c2N'] is False or g['c2Q'] is False):
            return '偏差有修、準度有損（不採用，交使用者）', fails
        return '不通過（不採用）', fails
    if pend:
        return '待 ' + '、'.join(pend), fails
    return ('通過（MINOR）' if ev['checks']['c2N']['value']['ci90'][0] > 0 else '通過（PATCH）'), fails


def read_c1():
    p = HERE / 'npm-test.exit'
    return None if not p.exists() else bool(p.read_text(encoding='utf-8').strip() == '0')


def read_c3():
    p = HERE / 'evaluation.json'
    if not p.exists():
        return None, None
    ev = jload(p)
    cand = {c['label']: c for c in ev['candidates']}
    if 'E084' not in cand or 'card-0.2.3' not in cand:
        return None, None
    a, b = cand['E084']['gates'], cand['card-0.2.3']['gates']
    info = {'E084': {'pass': a['pass'], 'of': a['of']}, 'card-0.2.3': {'pass': b['pass'], 'of': b['of']}}
    return bool(a['pass'] >= b['pass'] and a['of'] == b['of']), info


def run_season(pools):
    c0 = jload(W / 'pooled/c0.json')
    assert c0.get('pass') is True, '(c0) 未通過：不得跑 season'
    base = pipeline(BASE_OPTS, pools, 'pooled')
    main_ = pipeline(BASE_OPTS, pools, 'season')
    bA, mA = base['_aux'], main_['_aux']
    ev = season_eval(mA['dirs'], bA['dirs'])
    # 理智檢查：基準（card 0.2.3 的半季值）在這裡算出的 S_N 應等於 E-081 results.json
    r81 = jload(E081D / 'results.json')
    san = {'S_N_point_equal_E081': bool(abs(ev['S_N_card023']['point'] - r81['S_N']['point']) < 1e-9),
           'S_Q_point_equal_E081': bool(abs(ev['S_Q_card023']['point'] - r81['S_Q']['point']) < 1e-9)}
    c1 = read_c1()
    c3, c3info = read_c3()
    g = gates_of(main_, ev, c1, c3)
    verdict, fails = decide(True, g, ev)
    write_rank(HERE / 'ranking.csv', mA['cols23'], mA['rows23'])
    sens = {}
    for tag, upd in (('s1', {'inactive_noreason_to_coach': True}), ('s2', {'suspected': False}), ('s3', {'age_terms': False})):
        o = dict(BASE_OPTS)
        o.update(upd)
        sr = pipeline(o, pools, 'season')
        se = season_eval(sr['_aux']['dirs'], bA['dirs'])
        s_ = strip_aux(sr)
        s_['season_eval'] = {k_: se[k_] for k_ in ('S_N_cand', 'S_Q_cand', 'dS_N', 'dS_Q', 'dRho_N', 'dRho_Q', 'c4', 'checks')}
        s_['gates'] = gates_of(sr, se)
        sens[tag] = s_
    names, MIN, age = mA['names'], mA['MIN'], mA['age']
    rows23 = mA['rows23']
    old = D['card023']
    nm_idx = {n: i for i, n in enumerate(names)}
    named = {}
    for nm in NAMED:
        r_, o_ = next(x for x in rows23 if x['name'] == nm), old[nm]
        named[nm] = {'age': age[nm_idx[nm]], 'ovr_new': float(r_['ovr']), 'rank_new': int(r_['rank']), 'ovr_card023': float(o_['ovr']),
                     'rank_card023': int(o_['rank']), 'MIN': float(MIN[nm_idx[nm]])}
    top20 = [{'rank': int(r_['rank']), 'name': r_['name'], 'ovr': float(r_['ovr']), 'rank_card023': int(old[r_['name']]['rank']),
              'ovr_card023': float(old[r_['name']]['ovr'])} for r_ in rows23[:20]]
    chg = []
    for r_ in rows23:
        o_ = old[r_['name']]
        chg.append({'name': r_['name'], 'age': age[nm_idx[r_['name']]], 'MIN': float(MIN[nm_idx[r_['name']]]), 'ovr_new': float(r_['ovr']),
                    'ovr_card023': float(o_['ovr']), 'delta': float(r_['ovr']) - float(o_['ovr']), 'rank_new': int(r_['rank']),
                    'rank_card023': int(o_['rank'])})
    chg20 = sorted(chg, key=lambda x: (-abs(x['delta']), x['name']))[:20]
    big = [i for i in range(len(names)) if MIN[i] >= 1000]
    ovr_new = {x['name']: float(x['ovr']) for x in rows23}
    agegrp = {}
    for gname, f in AGE_GROUPS:
        ii = [i for i in big if age[i] is not None and f(age[i])]
        agegrp[gname] = {'n': len(ii), 'median_ovr_new': float(np.median([ovr_new[names[i]] for i in ii])) if ii else None,
                         'median_ovr_card023': float(np.median([float(old[names[i]]['ovr']) for i in ii])) if ii else None}
    agegrp['no_age_n'] = int(sum(1 for i in big if age[i] is None))
    pstd = {'MIN>=1000_n': len(big), 'pred_new_std_new': float(np.std(mA['pred_new'][big])), 'pred_new_std_card023': float(np.std(bA['pred_new'][big])),
            'ddof': 0, 'pred_new_mean_new': float(np.mean(mA['pred_new'][big])), 'pred_new_mean_card023': float(np.mean(bA['pred_new'][big]))}
    e075 = jload(E075D / 'results.json')
    coef_ci = {}
    for dn in ('AB', 'BA', 'card'):
        if dn == 'card':
            bc = boot_coefs(mA['Xc'], mA['yc'], mA['wc'], mA['gc'])
        else:
            t = mA['train'][dn]
            bc = boot_coefs(t['X'], t['y'], t['w'], t['pid'])
        coef_ci[dn] = {nm: {'coef': float(mA['coef_raw'][dn][j]), 'ci90': [float(np.percentile(bc[:, j], 5)), float(np.percentile(bc[:, j], 95))]}
                       for j, nm in enumerate(COEF_NAMES[:len(mA['coef_raw'][dn])])}
    e082 = jload(E082D / 'results.json')
    e082_pass = bool(str(e082.get('verdict', '')).startswith('通過'))
    sec5 = {'baseline': 'card 0.2.3（不等 E-082）', 'e082_verdict_read_only': e082.get('verdict'), 'e082_passed': e082_pass,
            'merged_version': ('E-082 與 E-084 皆通過，須另跑合併版（未跑）' if e082_pass and verdict.startswith('通過')
                               else '合併版待 E-082' if not e082_pass else '本版未全過，不跑合併版')}
    inputs = {}
    for p in (E081D / 'rapm1-A.csv', E081D / 'rapm1-B.csv', E081D / 'results.json', E082D / 'results.json', C023, C022_PUB, E075D / 'results.json',
              E075D / 'e075.py', E081D / 'e081.py', HERE / 'preregistration.md', HERE / 'e084.py', HERE / 'evaluate.mjs'):
        inputs[p.relative_to(ROOT).as_posix()] = sha(p)
    results = {
        'experiment': 'E-084', 'version': 'card 0.2.3+E084', 'baseline': 'card 0.2.3（reports/card-0.2.3/ranking.csv）',
        'target': 'season（fit 半季只用 2025-26 比賽的 rapm1 net／poss）', 'verdict': verdict, 'failed_checks': fails,
        'verdict_rule': '預註冊 §4：全過=通過（c2N 下界>0 為 MINOR，否則 PATCH）；(b) 過但 c2N／c2Q 沒過=偏差有修、準度有損（不採用）；其他沒過=不採用',
        'checks': {'c0': c0, 'c1': {'value': c1, 'threshold': 'npm test exit 0', 'pass': c1},
                   'b': ev['checks']['b'], 'c2N': ev['checks']['c2N'], 'c2Q': ev['checks']['c2Q'],
                   'c3': {'value': c3info, 'threshold': 'E084 閘數 >= card 0.2.3（18/19）', 'pass': c3},
                   'c4': ev['checks']['c4'],
                   'R1_reportOnly': main_['R1'], 'R2': main_['R2'], 'R3': main_['R3'], 'R4': main_['R4']},
        'season_eval': ev, 'sanity_vs_E081': san,
        'legacy_e075_style': {'c2': main_['c2'], 'c4': main_['c4'],
                              'note': '只報告：E-075 原式（c4 的 net 仍是 pooledNet），不是 E-084 判準'},
        'coefficients': main_['coef'], 'coefficients_E075': e075['coefficients'], 'coefficient_ci': coef_ci, 'coefficient_ci_E075': e075.get('coefficient_ci'),
        'training': main_['train_info'], 'population': main_['population'],
        'named_players': named, 'top20': top20, 'largest_ovr_changes': chg20, 'age_group_median_ovr_MIN1000': agegrp, 'pred_new_dispersion': pstd,
        'card': main_['card'], 'sensitivities': sens, 'section5': sec5,
        'ranking_csv_sha256': sha(HERE / 'ranking.csv'), 'preregistration_sha256': sha(HERE / 'preregistration.md'), 'inputs_sha256': inputs,
        'generator': 'reports/card-0.2.3+E084-current-target/e084.py --target season'}
    (HERE / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(json.dumps({'verdict': verdict, 'failed': fails, 'gates': g, 'sanity': san,
                      'S_N_cand': ev['S_N_cand']['point'], 'S_N_card023': ev['S_N_card023']['point'], 'dS_N': ev['dS_N'],
                      'dRho_N': ev['dRho_N'], 'dRho_Q': ev['dRho_Q'], 'c4': ev['c4']['ci90']}, ensure_ascii=False, indent=1, default=float))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=['pooled', 'season'], default='pooled')
    a = ap.parse_args()
    exp = (HERE / 'preregistration.sha256').read_text(encoding='utf-8').split()[0]
    assert sha(HERE / 'preregistration.md') == exp, '預註冊 sha256 與凍結值不同'
    load_data()
    pools = build_pools()
    return run_c0(pools) if a.target == 'pooled' else run_season(pools)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
