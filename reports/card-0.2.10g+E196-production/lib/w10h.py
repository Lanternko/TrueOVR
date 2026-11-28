"""inseason／card 0.2.12（E-185）：long、creation、threeValue、MPG 改 E-175 U 臂四季滑動窗口。Win10 繼承 Win8（8 項不變），多做：
  long       n＝窗口 FG3M、d＝窗口 FG3A；p＝(n+100·m)/(d+100)，m＝本季（已賽場次）聯盟三分%，本季 0 場用上一季；CURVE_3PT 反函數＋E-101 合併池＋尾巴。
  creation   窗口 FGA／窗口 MIN；r＝(1−creationDependence)·FGA/max(MIN,1)·36（creationDependence 外部角色係數維持 2025-26 現值）；百分位型＋合併池＋尾巴；不收縮。
  threeValue vol＝窗口 3PA／窗口 MIN×36；acc＝(n_w+K·mu)/(d_w+K)，n_w：有逐季 abilityC 的季＝abilityC×該季加權 3PA，沒有的季＝原始 FG3M；
             value＝vol×(acc−(mu−0.03))；池／尾巴由呼叫端處理（卡片端 build_card_0211.py、賽中端 run_c4_live.three_value_columns）。
  mpg        MPG_hat＝Σu·MIN／Σu·GP（過去季＝季總量×季權重；本季逐場 u）；窗口長度 L（季數）可調，L＝4 即屬性窗口。
窗口權重、映射器、池與開關全部取自 card 0.2.10 的 U 鏈（Win8），沒有新參數（只有 MPG 的 L，由 mpg_select.py 只用 2024-25 選）。
用法：W=Win10()；tabs,gd=W.cur_tabs()；W.attrs_at(gd,tabs)（含 long、creation）；W.mpg_at(gd,tabs)；W.tv_raw(gd,tabs)。"""
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

import w8h as W8   # E-196：HEAD 版複本

L, C = W8.L, W8.C
ROOT, HERE = W8.ROOT, W8.HERE
TARGET, PRIOR, G_TOTAL = W8.TARGET, W8.PRIOR, W8.G_TOTAL
SEASONS10 = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
K_LONG = 100.0
THREE_K = 294.667
THREE_REP_GAP = 0.03
ABIL_JSON = ROOT / 'reports/card-0.2.12/abilityC-by-season.json'
DEP_CSV = ROOT / 'reports/player-impact-v41/2025-26-player-validation.csv'
EXTRA = ('long', 'creation')
TV_MEMBERS = HERE / 'tvpool-members-card0210f.json'   # E-191b P1m：各過去季 SV 人群（build_tvpool_0210f.py 由 season-values.json 凍結）
TV_POOL_MIN = 500                                     # P1m：窗口加權 MIN 門檻


def wL(c, nseas=4):
    """window_w 的 L 季版（nseas＝4 時與 L.window_w 逐位元相同）。c＝本季已過格數。"""
    win = nseas * L.SLOTS
    w = {}
    for k in range(1, nseas + 1):
        b = win - c - L.SLOTS * (k - 1)
        a = b - L.SLOTS
        w[k] = (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * win * L.SLOTS)
    return w


def season_path(s):
    return ROOT / 'data/season-source/player-games.json' if s == '2025-26' else ROOT / 'data/defense-seventh' / s / 'player-games.json'


def curve3pt():
    txt = (ROOT / 'src/constants.js').read_text(encoding='utf-8')
    body = re.search(r'export const CURVE_3PT = \[(.*?)\];', txt, re.S).group(1)
    return [(float(a), float(b)) for a, b in re.findall(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', body)]


def make_tabs(NP, gi, pi, MIN, F3M, F3A, FGA, G, lg_gi, lg3m, lg3a):
    """一季的逐場表：f3＝(FG3M,FG3A)、cr＝(FGA,MIN)、tpa＝(FG3A,MIN)、mpg＝(MIN,1)；lg＝每場聯盟 (FG3M,FG3A)（供 m）。"""
    T = lambda n, d: L.Tab(gi, pi, n, d, NP)
    ml, al = np.zeros(G), np.zeros(G)
    np.add.at(ml, np.asarray(lg_gi, int), lg3m)
    np.add.at(al, np.asarray(lg_gi, int), lg3a)
    return {'f3': T(F3M, F3A), 'cr': T(FGA, MIN), 'tpa': T(F3A, MIN), 'mpg': T(MIN, [1.0] * len(MIN)), 'lg': (ml, al)}


def _num(r, k):
    return float(r[k] or 0)


def season_tabs(D, s):
    """過去季 s 的逐場表。場次序號 gi 與 D.gids[s] 相同；球員用 D.pidx（不在名單的人只進聯盟合計）。"""
    rows = W8._rows(season_path(s))
    gi_of = {g: i for i, g in enumerate(D.gids[s])}
    rows = [r for r in rows if r['MIN'] and r['GAME_ID'] in gi_of]
    sel = [r for r in rows if r['PLAYER_ID'] in D.pidx]
    f = lambda k: [_num(r, k) for r in sel]
    return make_tabs(D.NP, [gi_of[r['GAME_ID']] for r in sel], [D.pidx[r['PLAYER_ID']] for r in sel], f('MIN'), f('FG3M'), f('FG3A'), f('FGA'),
                     D.G[s], [gi_of[r['GAME_ID']] for r in rows], [_num(r, 'FG3M') for r in rows], [_num(r, 'FG3A') for r in rows])


def lg_total(tabs):
    return float(tabs['lg'][0].sum()), float(tabs['lg'][1].sum())


class Win10(W8.Win8):
    def __init__(self, data26=W8.DATA26):
        super().__init__(data26)
        D, inp = self.D, self.inp
        self.T10 = {s: season_tabs(D, s) for s in SEASONS10}
        names = [inp['cards'][p]['name'] for p in self.pids]
        dep = {r['name']: float(r['creationDependence_sourceRole']) for r in csv.DictReader(open(DEP_CSV, encoding='utf-8-sig'))}
        self.dep = np.array([dep[n] for n in names])      # 缺名字就 KeyError（卡片名單全有；L-026 不補預設）
        self.min500_i = np.array([i for i, n in enumerate(names) if inp['rank_min'].get(n, 0) >= 500])
        ab = json.loads(ABIL_JSON.read_text(encoding='utf-8'))['seasons'] if ABIL_JSON.exists() else {}
        self.abil = {}
        for s, d in ab.items():
            a = np.full(D.NP, np.nan)
            for k, v in d.items():
                if int(k) in D.pidx:
                    a[D.pidx[int(k)]] = v['acc']
            self.abil[s] = a
        self.curve3 = curve3pt()
        self._build_extra_maps()

    # ---------------- 本季逐場表（與 Win8.cur_tabs 同一套 gi）
    def cur_tabs(self):
        t, gd = super().cur_tabs()
        D = self.D
        pl = W8._rows(self.data26 / 'player-games.json')
        tm = W8._rows(self.data26 / 'team-games.json')
        by = {}
        for r in tm:
            if r['MIN']:
                by.setdefault(r['GAME_ID'], []).append(r)
        dates = {r['GAME_ID']: r['GAME_DATE'] for r in pl}
        gids = sorted((g for g in by if len(by[g]) == 2), key=lambda g: (dates.get(g, ''), g))
        gi_of = {g: i for i, g in enumerate(gids)}
        assert len(gids) == gd
        rows = [r for r in pl if r['MIN'] and r['GAME_ID'] in gi_of]
        sel = sorted((r for r in rows if r['PLAYER_ID'] in D.pidx), key=lambda r: (r['GAME_ID'], r['TEAM_ID'], r['PLAYER_ID']))
        f = lambda k: [_num(r, k) for r in sel]
        t.update(make_tabs(D.NP, [gi_of[r['GAME_ID']] for r in sel], [D.pidx[r['PLAYER_ID']] for r in sel], f('MIN'), f('FG3M'), f('FG3A'), f('FGA'),
                           max(gd, 1), [gi_of[r['GAME_ID']] for r in rows], [_num(r, 'FG3M') for r in rows], [_num(r, 'FG3A') for r in rows]))
        return t, gd

    def season_cur(self, s):
        """卡片端：當季（2025-26）整季逐場表。"""
        return self.T10[s], self.D.G[s]

    # ---------------- 窗口和（過去季 = 季總量 × 權重；本季 = 逐場 u）
    def sums10(self, name, g, cur, G, S=TARGET, nseas=4, abil=False):
        c = L.SLOTS * g / G
        w = wL(c, nseas)
        win = nseas * L.SLOTS
        base = L.SEASONS.index(S) if S in L.SEASONS else len(L.SEASONS)
        n, d = np.zeros(self.D.NP), np.zeros(self.D.NP)
        for k in range(1, nseas + 1):
            i = base - k
            if i < 0 or w[k] <= 0:
                continue
            s = L.SEASONS[i]
            tab = self.T10.get(s, {}).get(name)
            if tab is None:
                continue
            nk, dk = tab.agg()
            if abil and s in self.abil:
                nk = np.where(np.isnan(self.abil[s]), nk, self.abil[s] * dk)
            n += w[k] * nk
            d += w[k] * dk
        if g > 0:
            tab = cur[name]
            u = (win - c + L.SLOTS * (tab.gi + 0.5) / G) / win
            nc, dc = tab.agg(0, g, w=u)
            if abil and S in self.abil:
                nc = np.where(np.isnan(self.abil[S]), nc, self.abil[S] * dc)
            n += nc
            d += dc
        return n, d

    def lg_rate(self, g, cur, S=TARGET):
        """long 的收縮先驗 m：本季已賽 g 場的聯盟三分%；本季 0 場（或沒出手）用上一季全季。"""
        ml, al = cur['lg']
        if g > 0 and al[:g].sum() > 0:
            return float(ml[:g].sum() / al[:g].sum())
        prev = L.SEASONS[L.SEASONS.index(S) - 1] if S in L.SEASONS else L.SEASONS[-1]
        m, a = lg_total(self.T10[prev])
        return m / a

    # ---------------- long、creation 的映射器（2025-26 季末窗口值＋過去季凍結池；同 e175_card.card_chain 的 U 臂做法）
    def _past(self, a, rule):
        v = []
        for s in C.MAIN:
            d, info = self.inp['seas'][s]['attrs'].get(a, {}), self.inp['seas'][s]['poolInfo']
            if rule == 'min500':
                v += [x for k, x in d.items() if info.get(k, {'MIN': 0})['MIN'] >= 500]
            else:
                v += [x for k, x in d.items() if (i := info.get(k)) is not None and i['GP'] > 0 and i['GP'] >= L.POOL_GP and i['MIN'] / i['GP'] >= L.POOL_MPG]
        return v

    def _flags(self, a):
        h = self.inp['h1']
        return C.passed(h, a, 'top'), C.passed(h, a, 'bot')

    def _long_p(self, g, cur, G, S):
        n, d = (x[self.ix] for x in self.sums10('f3', g, cur, G, S))
        return L.shrink_to(n, d, self.lg_rate(g, cur, S), K_LONG)

    def _creation_r(self, g, cur, G, S):
        n, d = (x[self.ix] for x in self.sums10('cr', g, cur, G, S))
        return (1 - self.dep) * n / np.maximum(d, 1.0) * 36

    def _build_extra_maps(self):
        cur, G = self.season_cur(PRIOR)
        p = self._long_p(G, cur, G, PRIOR)
        top, bot = self._flags('long')
        self.long_map = L.CurveMapper(self.curve3, list(p[self.min500_i]) + self._past('long', 'min500'), top, bot)
        r = self._creation_r(G, cur, G, PRIOR)
        top, bot = self._flags('creation')
        self.creation_map = L.PctMapper(list(r[self.pool_i]) + self._past('creation', 'pool'), top, bot)
        self.end = {'long': self.long_map(p), 'creation': self.creation_map(r)}   # 2025-26 季末（c=82）窗口值，卡片端用

    def extra_at(self, g, tabs, S=TARGET, G=G_TOTAL):
        """{'long': 向量, 'creation': 向量}（卡片名單順序）。"""
        return {'long': self.long_map(self._long_p(g, tabs, G, S)), 'creation': self.creation_map(self._creation_r(g, tabs, G, S))}

    def attrs_at(self, g, tabs):
        out = super().attrs_at(g, tabs)
        ex = self.extra_at(g, tabs)
        for i, p in enumerate(self.pids):
            for a in EXTRA:
                out[int(p)][a] = float(ex[a][i])
        return out

    # ---------------- MPG、threeValue 的窗口輸入
    def mpg_at(self, g, tabs, S=TARGET, G=G_TOTAL, nseas=4):
        """{pid: MPG_hat}（Σu·MIN／Σu·GP；窗口內沒出賽者不在其中）。"""
        n, d = self.sums10('mpg', g, tabs, G, S, nseas)
        return {int(p): float(n[i] / d[i]) for i, p in enumerate(self.D.pids) if d[i] > 0}

    def tv_raw(self, g, tabs, S=TARGET, G=G_TOTAL, nseas=4):
        """threeValue 的窗口原料（全 D.NP 長）：(n_w 難度調整後分子, a_w 加權 3PA, min_w 加權 MIN)。"""
        n, a = self.sums10('f3', g, tabs, G, S, nseas, abil=True)
        _, mn = self.sums10('tpa', g, tabs, G, S, nseas)
        return n, a, mn

    @staticmethod
    def tv_value(n, a, mn, mu):
        """vol×(acc−rep)；窗口 MIN＝0 者回 NaN。"""
        acc = (n + THREE_K * mu) / (a + THREE_K)
        vol = np.where(mn > 0, a / np.where(mn > 0, mn, 1) * 36, np.nan)
        return vol, acc, vol * (acc - (mu - THREE_REP_GAP))

    def tv_past_pool(self, s, members=None):
        """E-191b P1m 的過去季人群：t ∈ {s−3..s−1} 且有 SV 人群者，各取「以 t 結尾的窗口 threeValue 原值」，
        只收該季 SV 名單內、在 D.pidx、窗口加權 MIN>=500、非 NaN 者。回 {t: {pid: value}}（t 升冪）。"""
        mem = members if members is not None else json.loads(TV_MEMBERS.read_text(encoding='utf-8'))['seasons']
        y = int(s[:4])
        out = {}
        for t in sorted(mem):
            if not y - 3 <= int(t[:4]) <= y - 1:
                continue
            cur, G = self.season_cur(t)
            n, a, mn = self.tv_raw(G, cur, t, G, 4)
            m_, a_ = lg_total(self.T10[t])
            _, _, val = self.tv_value(n, a, mn, m_ / a_)
            out[t] = {int(p): float(val[self.D.pidx[int(p)]]) for p in mem[t]
                      if int(p) in self.D.pidx and mn[self.D.pidx[int(p)]] >= TV_POOL_MIN and not np.isnan(val[self.D.pidx[int(p)]])}
        return out

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    W = Win10()
    # 1) L=4 權重與 L.window_w 逐位元相同
    for c in (0.0, 5.3, 40.0, 82.0):
        assert wL(c, 4) == L.window_w(c), c
    print('wL(4) == L.window_w OK')
    # 2) V 臂重現：原始鏈（全季 + 聯盟 m）的 long、creation 對 tail-e123a.csv
    tail = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv', encoding='utf-8'))}
    cur, G = W.season_cur(PRIOR)
    n, d = (x[W.ix] for x in W.T10[PRIOR]['f3'].agg())
    m, a_ = lg_total(W.T10[PRIOR])
    p_v = L.shrink_to(n, d, m / a_, K_LONG)
    lm = L.CurveMapper(W.curve3, list(p_v[W.min500_i]) + W._past('long', 'min500'), *W._flags('long'))
    v = lm(p_v)
    print('V long vs tail-e123a max|diff|', max(abs(v[i] - float(tail[int(p)]['long'])) for i, p in enumerate(W.pids)))
    # creation 的 V 臂原鏈用聯盟 JSON 的 observed（分鐘有小數）；player-games 的 MIN 是整數，r 最多差 0.7，所以這裡用 JSON 的 r 驗公式
    lg = json.load(open(ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json', encoding='utf-8'))
    tot = {}
    for team in lg['teams']:
        for p in team['roster']:
            t_ = tot.setdefault(p['name'], {'FGA': 0.0, 'MIN': 0.0, 'GP': 0})
            for k in t_:
                t_[k] += p['observed'][k]
    nm = [W.inp['cards'][p]['name'] for p in W.pids]
    r2 = np.array([(1 - W.dep[i]) * tot[n]['FGA'] / max(tot[n]['MIN'], 1) * 36 for i, n in enumerate(nm)])
    pool2 = [r2[i] for i, n in enumerate(nm) if tot[n]['GP'] >= 30 and tot[n]['MIN'] / tot[n]['GP'] >= 20]
    v = L.PctMapper(pool2 + W._past('creation', 'pool'), *W._flags('creation'))(r2)
    print('V creation (JSON r) vs tail-e123a max|diff|', max(abs(v[i] - float(tail[int(p)]['creation'])) for i, p in enumerate(W.pids)))
    print('end (U c=82) long/creation sample', W.end['long'][:3], W.end['creation'][:3])
