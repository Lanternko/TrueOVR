"""inseason 0.2.10：8 項屬性（drive, foulDraw, ft, mid, pass, rebound, short, tovSkill）改用 E-175 U 臂滑動窗口。

窗口＝過去四季（window_w(c)，c＝82×已賽場數/1230）＋ 2026-27 已賽場次（逐場 u 權重）。
映射鏈、收縮 k、先驗 m、池分布、錨、z 參數全部取自 card 0.2.10 的 2025-26 U 鏈（執行時重算一次，並以 tail-U.csv 驗證）。
沒有窗口資料的人：窗口和為 0，收縮到先驗 m；drive 無資料者照 E-175 設 70。
用法：W=Win8()；W.attrs_at(g_done, tabs) -> {pid: {attr: 值}}；W.day0() 即 g=0。
假設（規格沒寫）：本季 drive 的失手權重 pu 沿用 2025-26 H1 的 pu（本季還沒有 H1）。"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E175 = ROOT / 'reports/E175-sliding-window-card'
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
sys.path.insert(0, str(E175))
sys.path.insert(0, str(V61))
import e175_lib as L  # noqa: E402
import e175_card as C  # noqa: E402
sys.path.insert(0, str(HERE))
import split_dc as SD  # noqa: E402（0.2.10i：SPLIT_DC=1 時 drive 換 D 類、過去季池值換 D／加 creationJ；0 時不動）
SD.patch_e175(L, C)
import os  # noqa: E402
TOV_POSS = os.environ.get('TOV_POSS', '1') != '0'   # 0.2.12：tovSkill 改持球時間（凍結池，見 tov_live.py）；TOV_POSS=0 重現 0.2.11
if TOV_POSS:
    import tov_live as TL  # noqa: E402

TARGET, PRIOR = '2026-27', '2025-26'
DATA26 = ROOT / 'data/defense-seventh/2026-27'
ORDER = ['ft', 'tovSkill', 'rebound', 'foulDraw', 'pass', 'vol', 'astvol', 'mid', 'short', 'driveVol', 'driveEff']
G_TOTAL = 1230


def _rows(path):
    import json
    rs = json.loads(Path(path).read_text(encoding='utf-8'))['data']['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    return [dict(zip(rs['headers'], r)) for r in rs['rowSet']]


# ---------------- 投籃區域（mid／short）：有官方 area 用官方；2026-27 pbp 沒有 area／areaDetail，改用距離＋座標推導
# 規則在看 2025-26 核對結果前依座標慣例定死（NBA stats 座標：籃框原點、0.1 呎；油漆區寬 16 呎＝|x|≤80、從籃框到罰球線 14.25 呎＝y≤142.5；限制區半徑 4 呎）。
RA_FT, PAINT_X, PAINT_Y = 4.0, 80, 142.5
# 推導規則核對（F-124）：第一輪（2025-26）mid 一致率 88.0% 未過；加「佔位座標＝無法判斷」規則後用沒看過的 2024-25 核對：
# mid 97.4%／short 100%（可判斷者），無法判斷 9.3%／3.3%，過門檻（≥95%、≤10%），2026-11-01 使用者核可啟用。
# 關閉時沒有 area 的資料維持舊行為（區域不計），只多一個 WARNING。
DERIVE_ZONES = True


def _zone(a):
    """一筆 isFieldGoal==1 的 2pt 動作 -> 0＝mid、1＝short、None＝無法判斷。"""
    area = a.get('area')
    if area:
        return 0 if area == 'Mid-Range' else 1 if area in ('Restricted Area', 'In The Paint (Non-RA)') else None
    if not DERIVE_ZONES:
        return None
    d, x, y = a.get('shotDistance'), a.get('xLegacy'), a.get('yLegacy')
    if x == 0 and y == 0 and not d:               # 佔位座標（距離 0／缺、xLegacy＝yLegacy＝0）：不是真實出手位置，無法判斷、不計分子分母
        return None
    if d is not None and d <= RA_FT:
        return 1
    if x is None or y is None:
        return None
    return 1 if abs(x) <= PAINT_X and y <= PAINT_Y else 0


def game_zones(acts, zone=_zone):
    """{pid: (midA, midM, shortA, shortM)}，以及 isFieldGoal 2pt 總數。"""
    z = {}
    n2 = 0
    for a in acts:
        if a['actionType'] != '2pt' or a.get('isFieldGoal') != 1:
            continue
        n2 += 1
        k = zone(a)
        if k is None:
            continue
        v = z.setdefault(a['personId'], [0, 0, 0, 0])
        v[2 * k] += 1
        v[2 * k + 1] += a.get('shotResult') == 'Made'
    return {p: tuple(v) for p, v in z.items()}, n2


class Win8:
    def __init__(self, data26=DATA26):
        self.data26 = Path(data26)
        self.D = D = L.Data()
        self.inp = C.load_inputs()
        cap = []
        orig = L.shrink_to

        def spy(n, d, t, k):
            cap.append((np.array(t, float), float(k)))
            return orig(n, d, t, k)
        L.shrink_to = spy
        try:
            self.U = U = C.card_chain(D, self.inp, 'U')
        finally:
            L.shrink_to = orig
        assert len(cap) == len(ORDER), len(cap)
        self.prior = dict(zip(ORDER, cap))     # attr -> (m 向量（mid/short 為 PBP 尺度、未平移）, k)
        self.pids = pids = U['pids']
        self.ix = np.array([D.pidx[p] for p in pids])
        idx = {p: i for i, p in enumerate(pids)}
        self.pool_i = np.array([idx[p] for p in U['poolPids']])
        rn = U['rn']
        self.zp = {a: (rn[a][self.pool_i].mean(), rn[a][self.pool_i].std()) for a in ('vol', 'foulDraw', 'astvol', 'pass')}
        self.dz = U['info']['driveZ']
        self.shift = {a: U['info'][a + 'Shift']['shift'] for a in ('mid', 'short')}

    # ---------------- 本季（2026-27）逐場表：與 prepare_pergame／extract_pbp 同規則
    def cur_tabs(self):
        import json
        import extract_pbp as X
        from collections import defaultdict
        D = self.D
        pl = _rows(self.data26 / 'player-games.json')
        tm = _rows(self.data26 / 'team-games.json')
        by = {}
        for r in tm:
            if r['MIN']:
                by.setdefault(r['GAME_ID'], []).append(r)
        dates = {r['GAME_ID']: r['GAME_DATE'] for r in pl}
        gids = sorted((g for g in by if len(by[g]) == 2), key=lambda g: (dates.get(g, ''), g))
        gi_of = {g: i for i, g in enumerate(gids)}
        team = {(r['GAME_ID'], r['TEAM_ID']): r for g in by for r in by[g]}
        rows = []
        for r in sorted(pl, key=lambda r: (r['GAME_ID'], r['TEAM_ID'], r['PLAYER_ID'])):
            g = r['GAME_ID']
            if g not in gi_of or not r['MIN'] or r['PLAYER_ID'] not in D.pidx:
                continue
            t = team[(g, r['TEAM_ID'])]
            o = next(x for x in by[g] if x['TEAM_ID'] != r['TEAM_ID'])
            share = r['MIN'] / (t['MIN'] / 5)
            rows.append((gi_of[g], D.pidx[r['PLAYER_ID']], r['MIN'], r['FGM'], r['FGA'], r['FTM'], r['FTA'], r['REB'], r['AST'], r['TOV'],
                         share * (t['REB'] + o['REB']), max(share * t['FGM'] - r['FGM'], 0.0)))
        gi = [x[0] for x in rows]
        pi = [x[1] for x in rows]
        MIN, FGM, FGA, FTM, FTA, REB, AST, TOV, rebCh, astCh = ([float(x[j]) for x in rows] for j in range(2, 12))
        NP = D.NP
        T = lambda n, d: L.Tab(gi, pi, n, d, NP)
        t = {'ft': T(FTM, FTA), 'foulDraw': T(FTA, FGA),
             'tovSkill': T(TOV, [a + .44 * b + c_ + e for a, b, c_, e in zip(FGA, FTA, AST, TOV)]),
             'pass': T(AST, astCh), 'rebound': T(REB, rebCh),
             'vol': T(FTA, [m / 36 for m in MIN]), 'astvol': T(AST, [m / 36 for m in MIN])}
        zg, zp_, zmA, zmM, zsA, zsM = [], [], [], [], [], []
        acc = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
        pu = D.pu[PRIOR]
        npbp = n2all = nzoned = 0
        for g in gids:
            f = self.data26 / 'pbp' / f'{g}.json'
            if not f.exists():
                continue
            npbp += 1
            _, _, drive = (SD.parse_drive if SD.ON else X.parse_game)((g, f))
            zones, n2 = game_zones(json.loads(f.read_text(encoding='utf-8'))['data']['game']['actions'])
            n2all += n2
            nzoned += sum(v[0] + v[2] for v in zones.values())
            for pid, (mA, mM, sA, sM) in zones.items():
                if pid in D.pidx:
                    zg.append(gi_of[g]); zp_.append(D.pidx[pid]); zmA.append(mA); zmM.append(mM); zsA.append(sA); zsM.append(sM)
            for (pid, made, ast, ftm, cls) in drive:
                if ast or pid not in D.pidx:
                    continue
                w = 1.0 if made else pu.get(cls, 1.0)
                a = acc[(gi_of[g], D.pidx[pid])]
                a[0] += w
                a[3] += w
                if made:
                    a[2] += 2 + ftm
        if n2all >= 200 and nzoned < 0.5 * n2all:   # 上游欄位消失（L-098）：本季有大量 2pt 出手但區域幾乎全空，不能靜默當 0
            print(f'WARNING: 2026-27 pbp 區域缺失：2pt 出手 {n2all}、判得出區域 {nzoned}，mid／short 本季不會更新（area 欄位消失？）', file=sys.stderr)
        self.n_zoned = (n2all, nzoned)
        t['mid'] = L.Tab(zg, zp_, zmM, zmA, NP)
        t['short'] = L.Tab(zg, zp_, zsM, zsA, NP)
        for g_, p_, m_ in zip(gi, pi, MIN):
            acc[(g_, p_)][1] += m_
        keys = list(acc)
        v = [acc[k] for k in keys]
        gg, pp = [k[0] for k in keys], [k[1] for k in keys]
        t['driveVol'] = L.Tab(gg, pp, [x[0] for x in v], [x[1] for x in v], NP)
        t['driveEff'] = L.Tab(gg, pp, [x[2] for x in v], [x[3] for x in v], NP)
        self.n_pbp = npbp
        return t, len(gids)

    # ---------------- 窗口和
    def sums(self, attr, g, cur_tab, G, S=TARGET):
        """窗口加權 (n_w, d_w)（全 D.NP 長）。g＝已賽場數，G＝本季總場數。S 不在 SEASONS（2026-27）時，過去季從 2025-26 往回。"""
        D = self.D
        c = L.SLOTS * g / G
        w = L.window_w(c)
        n, d = np.zeros(D.NP), np.zeros(D.NP)
        base = L.SEASONS.index(S) if S in L.SEASONS else len(L.SEASONS)
        for k in range(1, 5):
            i = base - k
            if i < 0 or w[k] <= 0:
                continue
            tab = D.tab[L.SEASONS[i]].get(attr)
            if tab is None:
                continue
            nk, dk = tab.agg()
            n += w[k] * nk
            d += w[k] * dk
        if g > 0:
            u = (L.WIN - c + L.SLOTS * (cur_tab.gi + 0.5) / G) / L.WIN
            nc, dc = cur_tab.agg(0, g, w=u)
            n += nc
            d += dc
        return n, d

    # ---------------- 比率 -> 屬性值（凍結的 2025-26 U 鏈映射）
    def map_sums(self, S):
        ix, U = self.ix, self.U
        rn = {}
        for a in ORDER:
            nw, dw = (x[ix] for x in S[a])
            m, k = self.prior[a]
            r = L.shrink_to(nw, dw, m, k)
            rn[a] = r + self.shift[a] if a in self.shift else r
        zs = lambda a: (rn[a] - self.zp[a][0]) / self.zp[a][1]
        comp_fd = .75 * zs('vol') + .25 * zs('foulDraw')
        comp_pass = .5 * zs('astvol') + .5 * zs('pass')
        z = self.dz
        score = .5 * (36 * rn['driveVol'] - z['mv']) / z['sv'] + .5 * (rn['driveEff'] - z['me']) / z['se']
        has = S['driveVol'][1][ix] > 0
        M = U['mappers']
        out = {'rebound': M['rebound'](rn['rebound']), 'tovSkill': TL.vet_values(self, S, S['_pm'], S.get('_tc')) if TOV_POSS else M['tovSkill'](-rn['tovSkill']),
               'foulDraw': M['foulDrawComposite'](comp_fd), 'pass': M['passComposite'](comp_pass),
               'drive': np.where(has, M['drive'](score), 70.0)}
        for a in ('ft', 'mid', 'short'):
            v = M[a](rn[a])
            if a == 'short':
                lo = M[a].lo
                v = np.array([max(lo, min(L.CEIL, 70 + (x - 70) * f)) for x, f in zip(v, M['short_discount'])])
            out[a] = v
        return out

    def check_season_end(self):
        S, G = PRIOR, self.D.G[PRIOR]
        sums = {a: self.sums(a, G, self.D.tab[S][a], G, S) for a in ORDER}
        if TOV_POSS:
            sums['_pm'] = TL.window_pm(self, G, {'vol': self.D.tab[S]['vol']}, G, S, S)
            if TL.TOUCH:
                sums['_tc'] = TL.window_tch(self, G, {'vol': self.D.tab[S]['vol']}, G, S, S)
        out = self.map_sums(sums)
        ref = dict(self.U['mapped'])
        if TOV_POSS:      # 0.2.12：tovSkill 的基準＝卡片 tov-raw.csv（逐位元）
            import csv
            rows = list(csv.DictReader(open(TL.CARD / 'tov-raw.csv', encoding='utf-8')))
            ref['tovSkill'] = np.array([float(r['tovSkill']) for r in rows])
        return {a: float(np.abs(out[a] - ref[a]).max()) for a in C.ATTRS8}

    def attrs_at(self, g, tabs):
        S = {a: self.sums(a, g, tabs[a], G_TOTAL) for a in ORDER}
        if TOV_POSS:
            S['_pm'] = TL.window_pm(self, g, tabs, G_TOTAL, TARGET, TARGET)
            if TL.TOUCH:
                S['_tc'] = TL.window_tch(self, g, tabs, G_TOTAL, TARGET, TARGET)
        out = self.map_sums(S)
        return {int(p): {a: float(out[a][i]) for a in C.ATTRS8} for i, p in enumerate(self.pids)}

    def day0(self, tabs):
        return self.attrs_at(0, tabs)


if __name__ == '__main__':
    import time
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    t0 = time.time()
    W = Win8()
    print('load', round(time.time() - t0, 1), 's')
    print('season-end check max|diff|', W.check_season_end())
    tabs, gd = W.cur_tabs()
    print('cur games', gd, 'pbp', W.n_pbp, round(time.time() - t0, 1), 's')
    a0 = W.day0(tabs)
    a1 = W.attrs_at(gd, tabs)
    import statistics as st
    for a in C.ATTRS8:
        dd = [abs(a1[p][a] - a0[p][a]) for p in a0]
        print(a, 'mean|g_done - day0|', round(st.mean(dd), 2), 'max', round(max(dd), 2))
