"""E-175 稽核：獨立重算用的核心（不 import e175_lib／e175_card／e175_backtest）。

只讀預註冊指定的輸入：V61 backtest.json／history、R-076 window_weights 公式（rookie_defense.py:241-254，自己重寫）、
0.2.9a 建卡鏈的凍結輸入（池、開關、曲線、折扣）。映射器依 card-0.2.7+E125 build_e101_p.py:70-149,183-200,239-285 自己寫。
"""
import csv
import gzip
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / 'reports'
V61 = R / 'ovr-v61-shrink-history-2025-26'
HIST = V61 / 'history'
E101 = R / 'card-0.2.5+E101-crossera'
E090 = R / 'card-0.2.4+E090-onball-tail'
E125 = R / 'card-0.2.7+E125-pass-volume'
E070 = R / 'card-0.2.0+E070-foul-volume'
BENCH = ROOT / 'data/benchmark-source'

SEASONS = [f'{y}-{str(y + 1)[2:]}' for y in range(2014, 2026)]
LOAD = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
ZONE_S = ['2022-23', '2023-24', '2024-25', '2025-26']
DRIVE_S = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
MIN_D2 = {'ft': 30, 'foulDraw': 100, 'tovSkill': 150, 'pass': 150, 'rebound': 400, 'mid': 30, 'short': 40, 'driveVol': 200, 'driveEff': 30}
SLOTS, WIN = 82, 328
ATTRS8 = ['drive', 'foulDraw', 'ft', 'mid', 'pass', 'rebound', 'short', 'tovSkill']
MAXH = 3


def jl(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def gzrows(p):
    with gzip.open(p, 'rt', encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def attr_seasons(t):
    if t in ('mid', 'short'):
        return ZONE_S
    if t in ('driveVol', 'driveEff'):
        return DRIVE_S
    return SEASONS


# ------------------------------------------------------------------ 資料
class DB:
    def __init__(self):
        pg = {s: gzrows(HIST / f'pergame-{s}.csv.gz') for s in LOAD}
        zn = {s: gzrows(E101 / 'history' / f'pbp-zones-{s}.csv.gz') for s in ZONE_S}
        dr = {s: gzrows(HIST / f'pbp-drive-{s}.csv.gz') for s in DRIVE_S}
        ids = set()
        for s in LOAD:
            ids |= {int(r['playerId']) for r in pg[s]}
            ids |= {int(r['playerId']) for r in zn.get(s, [])}
            ids |= {int(r['playerId']) for r in dr.get(s, [])}
        self.pids = sorted(ids)
        self.pix = {p: i for i, p in enumerate(self.pids)}
        self.NP = len(self.pids)
        self.G, self.tab, self.h1 = {}, {}, {}
        self.pu = {}
        for s in LOAD:
            dates = self._dates(s)
            gids = sorted({r['gameId'] for r in pg[s]}, key=lambda g: (dates.get(g, ''), g))
            gi = {g: i for i, g in enumerate(gids)}
            self.G[s] = len(gids)
            rows = pg[s]
            ghalf = {}
            for r in rows:
                ghalf[r['gameId']] = r['half']
            self.h1[s] = np.array([ghalf[g] == '1' for g in gids])        # 依日期序的場次是否屬 V61 的 H1（half 欄）
            g_ = np.array([gi[r['gameId']] for r in rows])
            p_ = np.array([self.pix[int(r['playerId'])] for r in rows])
            col = lambda k: np.array([float(r[k]) for r in rows])
            FGA, FTA, FTM, AST, TOV, REB, MIN = (col(k) for k in ('FGA', 'FTA', 'FTM', 'AST', 'TOV', 'REB', 'MIN'))
            t = {'ft': (FTM, FTA), 'foulDraw': (FTA, FGA), 'tovSkill': (TOV, FGA + .44 * FTA + AST + TOV), 'pass': (AST, col('astCh')),
                 'rebound': (REB, col('rebCh')), 'vol': (FTA, MIN / 36), 'astvol': (AST, MIN / 36)}
            T = {k: (g_, p_, n, d) for k, (n, d) in t.items()}
            if s in zn:
                z = [r for r in zn[s] if r['gameId'] in gi]
                zg = np.array([gi[r['gameId']] for r in z]); zp = np.array([self.pix[int(r['playerId'])] for r in z])
                T['mid'] = (zg, zp, np.array([float(r['midM']) for r in z]), np.array([float(r['midA']) for r in z]))
                T['short'] = (zg, zp, np.array([float(r['shortM']) for r in z]), np.array([float(r['shortA']) for r in z]))
            if s in dr:
                T['driveVol'], T['driveEff'], self.pu[s] = self._drive(dr[s], gi, ghalf, g_, p_, MIN)
            self.tab[s] = {k: tuple(v) for k, v in T.items()}

    @staticmethod
    def _dates(s):
        d = ROOT / 'data/season-source' if s == '2025-26' else ROOT / 'data/defense-seventh' / s
        rs = jl(d / 'player-games.json')['data']['resultSets']
        rs = rs[0] if isinstance(rs, list) else rs
        h = rs['headers']
        return {r[h.index('GAME_ID')]: r[h.index('GAME_DATE')] for r in rs['rowSet']}

    def _drive(self, shots, gi, ghalf, mg, mp, MIN):
        made, un = defaultdict(int), defaultdict(int)
        for r in shots:
            if ghalf.get(r['gameId']) == '1' and int(r['made']):
                made[r['cls']] += 1
                un[r['cls']] += int(r['assisted']) == 0
        pu = {k: un[k] / made[k] for k in made}
        acc = defaultdict(lambda: [0.0, 0.0, 0.0])      # (gi, pi) -> [Σw, minutes, points]
        for r in shots:
            g = gi.get(r['gameId'])
            if g is None or int(r['assisted']):
                continue
            ma = int(r['made'])
            w = 1.0 if ma else pu.get(r['cls'], 1.0)
            a = acc[(g, self.pix[int(r['playerId'])])]
            a[0] += w
            if ma:
                a[2] += 2 + int(r['ftmade'])
        for g, p, m in zip(mg, mp, MIN):
            acc[(int(g), int(p))][1] += m
        ks = list(acc)
        kg = np.array([k[0] for k in ks]); kp = np.array([k[1] for k in ks]); v = np.array([acc[k] for k in ks])
        return (kg, kp, v[:, 0], v[:, 1]), (kg, kp, v[:, 2], v[:, 0]), pu

    # ---- 聚合
    def agg(self, s, t, lo=0, hi=10 ** 9, w=None):
        g, p, n, d = self.tab[s][t]
        m = (g >= lo) & (g < hi)
        ww = 1.0 if w is None else w(g[m])
        return (np.bincount(p[m], weights=n[m] * ww, minlength=self.NP), np.bincount(p[m], weights=d[m] * ww, minlength=self.NP))


def positions():
    by = defaultdict(dict)
    for r in csv.DictReader(open(HIST / 'positions.csv', encoding='utf-8')):
        by[int(r['playerId'])][r['season']] = r['pos']
    return by


def pos_of(by, pid, s):
    d = by.get(pid)
    if not d:
        return 'UNK'
    if s in d:
        return d[s]
    return d[sorted(d, key=lambda x: abs(SEASONS.index(x) - SEASONS.index(s)))[0]]


# ------------------------------------------------------------------ 比率
def prior(n, d, kind, posv):
    if kind == 'league':
        return np.full(len(n), n.sum() / d.sum())
    lg = n.sum() / d.sum()
    pn, pd_ = defaultdict(float), defaultdict(float)
    for i in range(len(n)):
        pn[posv[i]] += n[i]; pd_[posv[i]] += d[i]
    r = {p: pn[p] / pd_[p] for p in pn if pd_[p] > 0}
    return np.array([r.get(posv[i], lg) for i in range(len(n))])


def causal_m(db, s, g, t, kind, posv):
    if g > 0:
        n, d = db.agg(s, t, 0, g)
    else:
        n, d = db.agg(SEASONS[SEASONS.index(s) - 1], t)
    return prior(n, d, kind, posv)


def shrink(n, d, t, k):
    den = d + k
    return np.where(den > 0, (n + k * t) / np.where(den > 0, den, 1), t)


def hist_seas(t, s):
    av = [x for x in attr_seasons(t) if SEASONS.index(x) < SEASONS.index(s)]
    return sorted(av, key=lambda x: -SEASONS.index(x))[:MAXH]


def hist_T(db, t, s, m, lam, kh):
    num = kh * m
    den = np.full(db.NP, float(kh))
    for j, h in enumerate(hist_seas(t, s)):
        n, d = db.agg(h, t)
        num = num + lam ** j * n
        den = den + lam ** j * d
    return num / den


def rate_V(db, t, s, g, fit, m):
    n, d = db.agg(s, t, 0, g)
    return shrink(n, d, hist_T(db, t, s, m, fit['lam'], fit['kh']), fit['k'])


def past_w(c, scale=1.0):
    out = {}
    for k in range(1, 5):
        b = WIN - c - SLOTS * (k - 1)
        a = b - SLOTS
        out[k] = scale * (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * WIN * SLOTS)
    return out


def window_sums(db, t, s, g, scale=1.0):
    """R-076 窗口加權的 (n_w, d_w)：過去季 = 季總量 × 該季平均 u；本季 = 逐場 × 該場 u。scale=0.5 即 window_weights 回傳值（含 /2）。"""
    G = db.G[s]
    c = SLOTS * g / G
    n, d = np.zeros(db.NP), np.zeros(db.NP)
    for k, w in past_w(c, scale).items():
        i = SEASONS.index(s) - k
        if i < 0 or w <= 0 or SEASONS[i] not in db.tab or t not in db.tab[SEASONS[i]]:
            continue
        a, b = db.agg(SEASONS[i], t)
        n += w * a; d += w * b
    if g > 0:
        a, b = db.agg(s, t, 0, g, w=lambda gi: scale * (WIN - c + SLOTS * (gi + 0.5) / G) / WIN)
        n += a; d += b
    return n, d


def rate_U(db, t, s, g, fit, m, scale=1.0):
    n, d = window_sums(db, t, s, g, scale)
    return shrink(n, d, m, fit['k'])


# ------------------------------------------------------------------ 映射器（E-101 合併池＋尾端）
CEIL, KSD, Z9990 = 150.0, 1.96, 1.044


def curves():
    txt = (ROOT / 'src/constants.js').read_text(encoding='utf-8')
    out = {}
    for nm in ('CURVE_MID', 'CURVE_SHORT', 'CURVE_FT'):
        body = re.search(rf'export const {nm} = \[(.*?)\];', txt, re.S).group(1)
        out[nm] = [(float(a), float(b)) for a, b in re.findall(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', body)]
    return out


def attr_of_pct(p):
    return np.clip(np.where(p < 50, 40 + (p - 1) * 30 / 49, 70 + (p - 50) * 29 / 49), 40.0, 99.0)


def inv_open(p, curve, lo, hi):
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]; x1, y1 = curve[i]
        if min(y0, y1) <= p <= max(y0, y1):
            return max(lo, min(hi, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    x = curve[0][0] if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else curve[-1][0]
    return max(lo, min(hi, x))


class PoolA:
    def __init__(self, vals):
        self.s = np.sort(np.asarray(vals, float))
        self.n = len(self.s)

    def pct(self, x):
        x = np.asarray(x, float)
        lo = np.searchsorted(self.s, x, 'left'); hi = np.searchsorted(self.s, x, 'right')
        return 100 * (lo + 0.5 * (hi - lo)) / self.n

    def anchors(self):
        pc = self.pct(self.s)
        r90, r99, r1 = self.s[pc >= 90].min(), self.s[pc >= 99].min(), self.s[pc <= 1].max()
        sd = float(np.std(self.s))
        return {'r90': float(r90), 'r99': float(r99), 'r1': float(r1), 'SD': sd, 'S': max((r99 - r90) / Z9990, sd), 'N': self.n}


class PctMap:
    def __init__(self, vals, top, bot):
        self.pool = PoolA(vals); self.an = self.pool.anchors(); self.top, self.bot = top, bot

    def __call__(self, x):
        x = np.atleast_1d(np.asarray(x, float))
        p = self.pool.pct(x)
        out = attr_of_pct(p)
        a = self.an
        if self.top:
            m = p >= 99
            out = np.where(m, 99 + (CEIL - 99) * (1 - np.exp(-np.maximum(0, x - a['r99']) / (KSD * a['S']))), out)
        if self.bot:
            m = (p <= 1) & ~(p >= 99)
            out = np.where(m, 40 - 15 * (1 - np.exp(-np.maximum(0, a['r1'] - x) / a['SD'])), out)
        return out


class CurveMap:
    def __init__(self, curve, vals, top, bot):
        self.curve, self.top, self.bot = curve, top, bot
        self.a99 = inv_open(99, [(y, x) for x, y in curve], -1e9, 1e9)
        self.an = PoolA(vals).anchors()
        self.s = KSD * self.an['S']
        self.lo = 0.0 if bot else 40.0

    def __call__(self, x):
        x = np.atleast_1d(np.asarray(x, float))
        out = np.empty(len(x))
        for i, p in enumerate(x):
            if self.top and p > self.a99:
                out[i] = 99 + (CEIL - 99) * (1 - math.exp(-(p - self.a99) / self.s)) / (1 - math.exp(-(1 - self.a99) / self.s))
            else:
                out[i] = inv_open(p, self.curve, self.lo, 99.0)
        return out


# ------------------------------------------------------------------ 0.2.9a 季末（V）鏈：自己重寫，產生映射器與重現用的屬性值
def load_inputs():
    bt = jl(V61 / 'backtest.json')
    league = jl(R / 'ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json')
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            cards.setdefault(p['playerId'], p)

    def bench(nm):
        rs = jl(BENCH / f'{nm}.json')['data']['resultSets']
        rs = rs[0] if isinstance(rs, list) else rs
        return rs
    base = {r[bench('base')['headers'].index('PLAYER_ID')]: dict(zip(bench('base')['headers'], r)) for r in bench('base')['rowSet']}
    shots = {r[0]: {'shortM': r[6] + r[9], 'shortA': r[7] + r[10], 'midM': r[12], 'midA': r[13]} for r in bench('shots')['rowSet']}
    return {'bt': bt, 'cards': cards, 'base': base, 'shots': shots,
            'disc': {r['name']: r['discountFactor'] for r in jl(R / 'ovr-v55-card-E-2025-26/season-league-E2-lam0.4-finish-discount-log.json')},
            'h1': {**jl(E090 / 'h1-results.json')['h1'], **jl(E101 / 'h1-results.json')['h1']},
            'seas': {s: jl(E125 / 'pool-P50' / f'raw-{s}.json') for s in ('2022-23', '2023-24', '2024-25')},
            'rank_min': {r['name']: float(r['MIN']) for r in csv.DictReader(open(R / 'card-0.2.5/ranking.csv', encoding='utf-8'))},
            'volfit': jl(E070 / 'vol-fit.json')['fit'], 'astfit': jl(E125 / 'astvol-fit.json')['fit']}


def prod_fit(bt, a):
    f = dict(bt['production'][a]['fit'])
    return f


class Chain:
    """2025-26 季末、卡片名單 582 人的 V（0.2.9a）屬性與映射器。arm='U' 時比率換成窗口版（同一條映射鏈）。"""

    def __init__(self, db, inp, arm='V', scale=1.0):
        S = '2025-26'
        bt, cards, base, shots = inp['bt'], inp['cards'], inp['base'], inp['shots']
        pids = sorted(cards, key=lambda p: (cards[p]['name'], p))
        self.pids, self.names = pids, [cards[p]['name'] for p in pids]
        ix = np.array([db.pix[p] for p in pids]); self.ix = ix
        posc = [cards[p]['pos'] for p in pids]
        bfit = lambda a: dict(bt['attrs'][a]['fit']['b'])
        fv = {'vol': inp['volfit'], 'astvol': inp['astfit']}
        ufit = {a: bfit(a) for a in ('ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'mid', 'short')}
        ufit['vol'] = {'k': inp['volfit']['k'], 'prior': inp['volfit']['prior']}
        ufit['astvol'] = {'k': inp['astfit']['k'], 'prior': inp['astfit']['prior']}
        for key in ('driveVol', 'driveEff'):
            ufit[key] = dict(bt['production']['drive']['components'][key]['b'])
        rn = {}

        def full(t, mask=None):
            n, d = (db.agg(S, t) if mask is None else self._mask_agg(db, S, t, mask))
            return n[ix], d[ix]

        def hist(t):
            hn, hd = [], []
            for h in hist_seas(t, S):
                a, b = db.agg(h, t)
                hn.append(a[ix]); hd.append(b[ix])
            return hn, hd

        def rate(t, fit, n, d, shift=0.0, m=None, nw=None, dw=None):
            if arm == 'U':
                fit = ufit[t]
            if m is None:
                m = np.full(len(pids), n.sum() / d.sum()) if fit['prior'] == 'league' else prior(n, d, 'position', posc)
            if arm == 'U':
                return shrink(nw, dw, m + shift, fit['k'])
            hn, hd = hist(t)
            num = fit['kh'] * m; den = np.full(len(pids), float(fit['kh']))
            for j in range(len(hn)):
                num = num + fit['lam'] ** j * hn[j]; den = den + fit['lam'] ** j * hd[j]
            return shrink(n, d, num / den + shift, fit['k'])

        def usum(t):
            a, b = window_sums(db, t, S, db.G[S], scale)
            return a[ix], b[ix]
        for a in ('ft', 'tovSkill', 'rebound', 'foulDraw', 'pass'):
            n, d = full(a)
            nw, dw = usum(a) if arm == 'U' else (None, None)
            rn[a] = rate(a, prod_fit(bt, a), n, d, nw=nw, dw=dw)
        for a in ('vol', 'astvol'):
            n, d = full(a)
            nw, dw = usum(a) if arm == 'U' else (None, None)
            rn[a] = rate(a, fv[a], n, d, nw=nw, dw=dw)
        self.shift = {}
        for a in ('mid', 'short'):
            n = np.array([shots.get(p, {}).get(a + 'M', 0) for p in pids], float)
            d = np.array([shots.get(p, {}).get(a + 'A', 0) for p in pids], float)
            pn, pdn = full(a)
            lp = pn.sum() / pdn.sum()
            sh = n.sum() / d.sum() - lp
            self.shift[a] = float(sh)
            fit = prod_fit(bt, a)
            if arm == 'U':
                nw, dw = usum(a)
                m = np.full(len(pids), lp) if ufit[a]['prior'] == 'league' else prior(pn, pdn, 'position', posc)
                rn[a] = shrink(nw, dw, m, ufit[a]['k']) + sh
            else:
                hn, hd = hist(a)
                num = fit['kh'] * lp; den = float(fit['kh'])
                for j in range(len(hn)):
                    num = num + fit['lam'] ** j * hn[j]; den = den + fit['lam'] ** j * hd[j]
                rn[a] = (n + fit['k'] * (num / den + sh)) / (d + fit['k'])
        # drive：前 41 場（V61 的 H1）為基礎
        h1m = db.h1[S]
        comp = bt['production']['drive']['components']
        dr = {}
        for key in ('driveVol', 'driveEff'):
            n, d = self._mask_agg(db, S, key, h1m)
            n, d = n[ix], d[ix]
            nw, dw = usum(key) if arm == 'U' else (None, None)
            dr[key] = rate(key, comp[key]['c'], n, d, nw=nw, dw=dw)
            if key == 'driveVol':
                mins41, has = d, (dw > 0 if arm == 'U' else d > 0)
        g41 = defaultdict(int)
        for r in gzrows(HIST / f'pergame-{S}.csv.gz'):
            if r['half'] == '1':
                g41[int(r['playerId'])] += 1
        gp = np.array([g41.get(p, 0) for p in pids], float)
        in41 = (gp >= 15) & (mins41 / np.where(gp > 0, gp, 1) >= 20)
        rv, re_ = 36 * dr['driveVol'], dr['driveEff']
        self.dz = {'mv': rv[in41].mean(), 'sv': rv[in41].std(), 'me': re_[in41].mean(), 'se': re_[in41].std()}
        rn['drive'] = .5 * (rv - self.dz['mv']) / self.dz['sv'] + .5 * (re_ - self.dz['me']) / self.dz['se']
        self.rn = rn
        # 組合（池內 z）
        pool = [p for p in pids if p in base and base[p]['GP'] >= 30 and base[p]['MIN'] / base[p]['GP'] >= 20]
        pi_ = np.array([pids.index(p) for p in pool])
        self.pool_i = pi_
        zs = lambda x: (x - x[pi_].mean()) / x[pi_].std()
        self.zp = {k: (rn[k][pi_].mean(), rn[k][pi_].std()) for k in ('vol', 'foulDraw', 'astvol', 'pass')}
        comp_fd = .75 * zs(rn['vol']) + .25 * zs(rn['foulDraw'])
        comp_ps = .5 * zs(rn['astvol']) + .5 * zs(rn['pass'])
        self.comp = {'foulDraw': comp_fd, 'pass': comp_ps}
        # 映射
        h1 = inp['h1']; seas = inp['seas']; cv = curves()
        ps = lambda a, k: bool(h1.get(a, {}).get(k, {}).get('pass', False))
        okinfo = lambda i, a: (i is not None and ((i['GP41'] > 0 and i['GP41'] >= 15 and i['MIN41'] / i['GP41'] >= 20) if a == 'drive'
                                                  else (i['GP'] > 0 and i['GP'] >= 30 and i['MIN'] / i['GP'] >= 20)))

        def past_pct(a):
            v = []
            for s, sd in seas.items():
                v += [x for k, x in sd['attrs'].get(a, {}).items() if okinfo(sd['poolInfo'].get(k), a)]
            return v

        def past_500(a):
            v = []
            for s, sd in seas.items():
                v += [x for k, x in sd['attrs'].get(a, {}).items() if sd['poolInfo'].get(k, {'MIN': 0})['MIN'] >= 500]
            return v
        sel = lambda x: list(np.asarray(x)[pi_])
        self.map = {}
        self.mapped = {}
        self.map['rebound'] = PctMap(sel(rn['rebound']) + past_pct('rebound'), ps('rebound', 'top'), ps('rebound', 'bot'))
        self.mapped['rebound'] = self.map['rebound'](rn['rebound'])
        self.map['tovSkill'] = PctMap(sel(-rn['tovSkill']) + past_pct('tovSkill'), ps('tovSkill', 'top'), ps('tovSkill', 'bot'))
        self.mapped['tovSkill'] = self.map['tovSkill'](-rn['tovSkill'])
        for a in ('foulDraw', 'pass'):
            self.map[a + 'Comp'] = PctMap(sel(self.comp[a]) + past_pct(a), ps(a, 'top'), ps(a, 'bot'))
            self.mapped[a] = self.map[a + 'Comp'](self.comp[a])
            self.map[a + 'Rate'] = PctMap(sel(rn[a]), ps(a, 'top'), ps(a, 'bot'))      # 產出者的比率層映射（池＝2025-26 池內比率，不併過去季）
        dp = list(rn['drive'][in41]) + past_pct('drive')
        self.map['drive'] = PctMap(dp, ps('drive', 'top'), ps('drive', 'bot'))
        self.mapped['drive'] = np.where(has, self.map['drive'](rn['drive']), 70.0)
        self.has_drive = has
        pool500 = [i for i, nm in enumerate(self.names) if inp['rank_min'].get(nm, 0) >= 500]
        for a, cn in (('ft', 'CURVE_FT'), ('mid', 'CURVE_MID'), ('short', 'CURVE_SHORT')):
            m = CurveMap(cv[cn], list(rn[a][pool500]) + past_500(a), ps(a, 'top'), ps(a, 'bot'))
            self.map[a] = m
            v = m(rn[a])
            if a == 'short':
                f = np.array([inp['disc'][nm] for nm in self.names])
                v = np.array([max(m.lo, min(CEIL, 70 + (x - 70) * k)) for x, k in zip(v, f)])
            self.mapped[a] = v

    @staticmethod
    def _mask_agg(db, s, t, gmask):
        g, p, n, d = db.tab[s][t]
        m = gmask[g]
        return (np.bincount(p[m], weights=n[m], minlength=db.NP), np.bincount(p[m], weights=d[m], minlength=db.NP))
