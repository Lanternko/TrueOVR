"""E-175 共用函式庫（只讀輸入；全部是本實驗自己寫的程式，不 import V61 的 engine／build_attrs）。

內容：
1. 資料：逐場逐人的 (分子, 分母) 表（按聯盟日期排序的場次序號 gi），八項屬性＋兩個量價分量（vol、astvol）。
2. V 臂（按季分塊，V61 方法 c）與 U 臂（R-076 滑動窗口）的比率函式。
3. 比率→屬性量尺的映射（E-101 合併池＋尾端，0.2.9a 現行）。
輸入檔路徑與 sha256 由 inputs_manifest() 彙整，寫進 results.json。
"""
import csv
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = ROOT / 'reports'
V61 = R / 'ovr-v61-shrink-history-2025-26'
HIST = V61 / 'history'
E101 = R / 'card-0.2.5+E101-crossera'
E090 = R / 'card-0.2.4+E090-onball-tail'
E125 = R / 'card-0.2.7+E125-pass-volume'
E070 = R / 'card-0.2.0+E070-foul-volume'
BENCH = ROOT / 'data/benchmark-source'
LEAGUE = R / 'ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
DISCOUNT_LOG = R / 'ovr-v55-card-E-2025-26/season-league-E2-lam0.4-finish-discount-log.json'

SEASONS = [f'{y}-{str(y + 1)[2:]}' for y in range(2014, 2026)]
ZONE_SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
DRIVE_SEASONS = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
TEST = '2025-26'
TOTAL_GAMES = 1230
H1_FRACTION = 574 / 1230
BOX = ['ft', 'foulDraw', 'tovSkill', 'pass', 'rebound']
EXTRA = ['vol', 'astvol']
ATTR_SEASONS = {a: list(SEASONS) for a in BOX + EXTRA}
ATTR_SEASONS.update({'mid': ZONE_SEASONS, 'short': ZONE_SEASONS, 'driveVol': DRIVE_SEASONS, 'driveEff': DRIVE_SEASONS})
MIN_D2 = {'ft': 30, 'foulDraw': 100, 'tovSkill': 150, 'pass': 150, 'rebound': 400, 'mid': 30, 'short': 40, 'driveVol': 200, 'driveEff': 30}
MAX_HIST = 3
SLOTS, WIN = 82, 4 * 82
CEIL, K_SD, Z9990 = 150.0, 1.96, 1.044
POOL_GP, POOL_MPG = 30, 20
POOL41_GP, POOL41_MPG = 15, 20


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for c in iter(lambda: fh.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def read_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def jload(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ------------------------------------------------------------------ 資料
def game_dates(season):
    d = ROOT / 'data/season-source' if season == TEST else ROOT / 'data/defense-seventh' / season
    rs = jload(d / 'player-games.json')['data']['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    h = rs['headers']
    ig, idt = h.index('GAME_ID'), h.index('GAME_DATE')
    return {r[ig]: r[idt] for r in rs['rowSet']}


class Tab:
    """一個 (季, 屬性) 的逐場列：gi 場次序號、pi 球員索引、n 分子、d 分母。"""

    def __init__(self, gi, pi, n, d, NP):
        self.gi, self.pi = np.asarray(gi, np.int32), np.asarray(pi, np.int32)
        self.n, self.d = np.asarray(n, float), np.asarray(d, float)
        self.NP = NP

    def agg(self, lo=0, hi=10 ** 9, w=None):
        """gi 在 [lo, hi) 的列加總成稠密向量 (n, d)；w 是逐列權重（與 gi 同長）。"""
        m = (self.gi >= lo) & (self.gi < hi)
        ww = np.ones(m.sum()) if w is None else np.asarray(w)[m]
        n = np.bincount(self.pi[m], weights=self.n[m] * ww, minlength=self.NP)
        d = np.bincount(self.pi[m], weights=self.d[m] * ww, minlength=self.NP)
        return n, d


    def agg_games(self, gmask):
        """gmask：長度 G 的布林陣列（哪些場次計入）。"""
        m = np.asarray(gmask)[self.gi]
        return (np.bincount(self.pi[m], weights=self.n[m], minlength=self.NP),
                np.bincount(self.pi[m], weights=self.d[m], minlength=self.NP))


class Data:
    def __init__(self, seasons=SEASONS):
        pg = {s: read_gz(HIST / f'pergame-{s}.csv.gz') for s in seasons}
        zone = {s: read_gz(E101 / 'history' / f'pbp-zones-{s}.csv.gz') for s in seasons if s in ZONE_SEASONS}
        drv = {s: read_gz(HIST / f'pbp-drive-{s}.csv.gz') for s in seasons if s in DRIVE_SEASONS}
        pids = set()
        for s in seasons:
            pids |= {int(r['playerId']) for r in pg[s]}
            if s in zone:
                pids |= {int(r['playerId']) for r in zone[s]}
            if s in drv:
                pids |= {int(r['playerId']) for r in drv[s]}
        self.pids = sorted(pids)
        self.pidx = {p: i for i, p in enumerate(self.pids)}
        self.NP = NP = len(self.pids)
        self.tab, self.G, self.gids, self.h1, self.pu = {}, {}, {}, {}, {}
        for s in seasons:
            dates = game_dates(s)
            gset = {r['gameId'] for r in pg[s]}
            order = sorted(gset, key=lambda g: (dates.get(g, ''), g))
            gi_of = {g: i for i, g in enumerate(order)}
            self.G[s], self.gids[s] = len(order), order
            self.h1[s] = {r['gameId'] for r in pg[s] if r['half'] == '1'}
            rows = pg[s]
            gi = [gi_of[r['gameId']] for r in rows]
            pi = [self.pidx[int(r['playerId'])] for r in rows]
            f = lambda k: [float(r[k]) for r in rows]
            FGA, FTA, FTM, AST, TOV, REB, MIN = (f(k) for k in ('FGA', 'FTA', 'FTM', 'AST', 'TOV', 'REB', 'MIN'))
            astCh, rebCh = f('astCh'), f('rebCh')
            T = lambda n, d: Tab(gi, pi, n, d, NP)
            t = {'ft': T(FTM, FTA), 'foulDraw': T(FTA, FGA),
                 'tovSkill': T(TOV, [a + .44 * b + c + e for a, b, c, e in zip(FGA, FTA, AST, TOV)]),
                 'pass': T(AST, astCh), 'rebound': T(REB, rebCh),
                 'vol': T(FTA, [m / 36 for m in MIN]), 'astvol': T(AST, [m / 36 for m in MIN])}
            if s in zone:
                zr = [r for r in zone[s] if r['gameId'] in gi_of]
                zg, zp = [gi_of[r['gameId']] for r in zr], [self.pidx[int(r['playerId'])] for r in zr]
                t['mid'] = Tab(zg, zp, [int(r['midM']) for r in zr], [int(r['midA']) for r in zr], NP)
                t['short'] = Tab(zg, zp, [int(r['shortM']) for r in zr], [int(r['shortA']) for r in zr], NP)
            if s in drv:
                t['driveVol'], t['driveEff'], self.pu[s] = self._drive(drv[s], gi_of, self.h1[s], gi, pi, MIN, NP)
            self.tab[s] = t

    def _drive(self, shots, gi_of, h1, mgi, mpi, MIN, NP):
        """突破分量。失手權重＝該類別「未助攻進球／進球」，只用 H1（前 41 場）的出手（v60 build_drive 的 weighted 模式）。
        vol：分子 Σw（被助攻者不算），分母＝出賽分鐘；eff：分子＝2＋罰球進數（未助攻進球），分母 Σw。"""
        made, un = defaultdict(int), defaultdict(int)
        for r in shots:
            if r['gameId'] in h1 and int(r['made']):
                made[r['cls']] += 1
                un[r['cls']] += not int(r['assisted'])
        pu = {k: un[k] / made[k] for k in made}
        acc = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])   # (gi, pidx) -> [Σw, MIN, pts, Σw]
        for r in shots:
            g = gi_of.get(r['gameId'])
            if g is None or int(r['assisted']):
                continue
            ma = int(r['made'])
            w = 1.0 if ma else pu.get(r['cls'], 1.0)
            a = acc[(g, self.pidx[int(r['playerId'])])]
            a[0] += w
            a[3] += w
            if ma:
                a[2] += 2 + int(r['ftmade'])
        for g, p, m in zip(mgi, mpi, MIN):
            acc[(g, p)][1] += m
        keys = list(acc)
        gg, pp = [k[0] for k in keys], [k[1] for k in keys]
        v = [acc[k] for k in keys]
        vol = Tab(gg, pp, [x[0] for x in v], [x[1] for x in v], NP)
        eff = Tab(gg, pp, [x[2] for x in v], [x[3] for x in v], NP)
        return vol, eff, pu


# ------------------------------------------------------------------ 位置、先驗、V 臂、U 臂
def positions_by():
    by = defaultdict(dict)
    for r in csv.DictReader(open(HIST / 'positions.csv', encoding='utf-8')):
        by[int(r['playerId'])][r['season']] = r['pos']
    return by


def pos_lookup(by, pid, season):
    d = by.get(pid)
    if not d:
        return 'UNK'
    if season in d:
        return d[season]
    return d[sorted(d, key=lambda s: abs(SEASONS.index(s) - SEASONS.index(season)))[0]]


def hist_seasons(attr, season):
    """season 之前、該屬性有資料的最近 ≤3 季（最近的在前）。"""
    avail = [s for s in ATTR_SEASONS[attr] if SEASONS.index(s) < SEASONS.index(season)]
    return sorted(avail, key=lambda s: -SEASONS.index(s))[:MAX_HIST]


def hist_arrays(D, attr, season):
    hn, hd = np.zeros((MAX_HIST, D.NP)), np.zeros((MAX_HIST, D.NP))
    for j, h in enumerate(hist_seasons(attr, season)):
        hn[j], hd[j] = D.tab[h][attr].agg()
    return hn, hd


def hist_target(hn, hd, m, lam, kh):
    w = np.array([lam ** j for j in range(MAX_HIST)])[:, None]
    return ((w * hn).sum(0) + kh * m) / ((w * hd).sum(0) + kh)


def shrink_to(n, d, t, k):
    den = d + k
    return np.where(den > 0, (n + k * t) / np.where(den > 0, den, 1), t)


def prior_vec(n, d, kind, posv, members=None):
    """聯盟（標量）或同位置（向量）比率。members：參與加總的球員索引遮罩（預設全部）。"""
    mem = np.ones(len(n), bool) if members is None else members
    if kind == 'league':
        return np.full(len(n), n[mem].sum() / d[mem].sum())
    lg = n[mem].sum() / d[mem].sum()
    pn, pd_ = defaultdict(float), defaultdict(float)
    for i in np.nonzero(mem)[0]:
        pn[posv[i]] += n[i]
        pd_[posv[i]] += d[i]
    rate = {p: pn[p] / pd_[p] for p in pn if pd_[p] > 0}
    return np.array([rate.get(posv[i], lg) for i in range(len(n))])


def causal_prior(D, attr, S, g, kind, posv):
    """預測用的先驗 m(t)：只用 t 以前的資料（t＝0 時用上一季全季）。"""
    if g > 0:
        n, d = D.tab[S][attr].agg(0, g)
    else:
        prev = SEASONS[SEASONS.index(S) - 1]
        n, d = D.tab[prev][attr].agg()
    return prior_vec(n, d, kind, posv)


def v_rate(D, attr, S, g, fit, m):
    """V 臂：(n_t + k·T)/(d_t + k)，T＝前 ≤3 季 λ 加權歷史目標。"""
    n, d = D.tab[S][attr].agg(0, g)
    hn, hd = hist_arrays(D, attr, S)
    return shrink_to(n, d, hist_target(hn, hd, m, fit['lam'], fit['kh']), fit['k'])


def window_w(c):
    """R-076 window_weights(c)（未除以 2.0）：past season k（1＝最近一季）的權重＝窗口內那段 u 的積分 ÷ 82。c＝本季已過格數。"""
    w = {}
    for k in range(1, 5):
        b = WIN - c - SLOTS * (k - 1)
        a = b - SLOTS
        w[k] = (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * WIN * SLOTS)
    return w


def u_sums(D, attr, S, g):
    """U 臂窗口加權後的 (n_w, d_w)：過去季 = 季總量 × window_w，本季 t 以前的每場 × 該場的 u。"""
    c = SLOTS * g / D.G[S]
    w = window_w(c)
    n, d = np.zeros(D.NP), np.zeros(D.NP)
    for k in range(1, 5):
        i = SEASONS.index(S) - k
        if i < 0 or w[k] <= 0:
            continue
        tab = D.tab[SEASONS[i]].get(attr)
        if tab is None:
            continue
        nk, dk = tab.agg()
        n += w[k] * nk
        d += w[k] * dk
    if g > 0:
        tab = D.tab[S][attr]
        u = (WIN - c + SLOTS * (tab.gi + 0.5) / D.G[S]) / WIN
        nc, dc = tab.agg(0, g, w=u)
        n += nc
        d += dc
    return n, d


def u_rate(D, attr, S, g, fit_b, m):
    n, d = u_sums(D, attr, S, g)
    return shrink_to(n, d, m, fit_b['k'])


# ------------------------------------------------------------------ 映射（E-101 合併池；0.2.9a 現行）
def curves():
    txt = (ROOT / 'src/constants.js').read_text(encoding='utf-8')
    out = {}
    for name in ('CURVE_MID', 'CURVE_SHORT', 'CURVE_FT'):
        body = re.search(rf'export const {name} = \[(.*?)\];', txt, re.S).group(1)
        out[name] = [(float(a), float(b)) for a, b in re.findall(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', body)]
    return out


def attr_of(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def top_tail(d, sd):
    return 99 + (CEIL - 99) * (1 - math.exp(-max(0.0, d) / (K_SD * sd)))


def bot_tail(d, sd):
    return 40 - 15 * (1 - math.exp(-max(0.0, d) / sd))


def inverse_open(p, curve, lo, hi):
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if min(y0, y1) <= p <= max(y0, y1):
            return max(lo, min(hi, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    x = curve[0][0] if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else curve[-1][0]
    return max(lo, min(hi, x))


class Pool:
    """合併池：百分位＝(小於者＋0.5·相等者)/N；錨點 r90、r99、r1、SD、S＝max((r99−r90)/1.044, SD)。"""

    def __init__(self, vals):
        self.s = np.sort(np.array([float(x) for x in vals]))
        self.n = len(self.s)

    def pct(self, x):
        lo = np.searchsorted(self.s, x, 'left')
        hi = np.searchsorted(self.s, x, 'right')
        return 100 * (lo + 0.5 * (hi - lo)) / self.n

    def anchors(self):
        s = self.s
        pc = self.pct(s)
        r90, r99, r1 = float(s[pc >= 90].min()), float(s[pc >= 99].min()), float(s[pc <= 1].max())
        sd = float(np.std(s))
        gap = (r99 - r90) / Z9990
        return {'r90': r90, 'r99': r99, 'r1': r1, 'SD_pool': sd, 'gapScale': gap, 'S': max(gap, sd), 'poolN': self.n}


class PctMapper:
    """百分位型：x → 屬性值。頂端 p≥99 且 top 開 → 99+51(1−e^{−(x−r99)/(1.96S)})；底端 p≤1 且 bot 開 → 40−15(1−e^{−(r1−x)/SD})。"""

    def __init__(self, pool_vals, top, bot):
        self.pool = Pool(pool_vals)
        self.an = self.pool.anchors()
        self.top, self.bot = bool(top), bool(bot)

    def __call__(self, x):
        x = np.atleast_1d(np.asarray(x, float))
        p = self.pool.pct(x)
        out = np.empty(len(x))
        for i, (xi, pi_) in enumerate(zip(x, p)):
            if pi_ >= 99 and self.top:
                out[i] = top_tail(xi - self.an['r99'], self.an['S'])
            elif pi_ <= 1 and self.bot:
                out[i] = bot_tail(self.an['r1'] - xi, self.an['SD_pool'])
            else:
                out[i] = attr_of(float(pi_))
        return out


class CurveMapper:
    """命中率型：x（卡片尺度的收縮後命中率）→ 屬性值，曲線反函數；p>a99 且 top 開則走頂端指數尾。"""

    def __init__(self, curve, pool_vals, top, bot):
        self.curve, self.top, self.bot = curve, bool(top), bool(bot)
        self.a99 = inverse_open(99, [(y, x) for x, y in curve], -1e9, 1e9)
        self.an = Pool(pool_vals).anchors()
        self.s = K_SD * self.an['S']
        self.lo = 0.0 if self.bot else 40.0

    def __call__(self, x):
        x = np.atleast_1d(np.asarray(x, float))
        out = np.empty(len(x))
        for i, p in enumerate(x):
            if self.top and p > self.a99:
                out[i] = 99 + (CEIL - 99) * (1 - math.exp(-(p - self.a99) / self.s)) / (1 - math.exp(-(1 - self.a99) / self.s))
            else:
                out[i] = inverse_open(p, self.curve, self.lo, 99.0)
        return out
