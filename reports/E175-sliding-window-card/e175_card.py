"""E-175 步驟 1：本實驗自己寫的 V 臂程式，重算 2025-26 季末的 8 項屬性（0.2.9a 的算法），並建立「比率→屬性值」映射器。

鏈（見 stage1-methods.md）：V61 方法 c 收縮比率 rn → foulDraw（E-070 w=0.75）／pass（E-125 w=0.5）加量的組合 → E-101 合併池映射（百分位型＋尾端、
命中率型曲線反函數＋尾端、short 乘折扣）。過去季的池值（pool-P50/raw-<季>.json）與開關（h1-results.json）是凍結輸入，不重算。
"""
import csv
from collections import defaultdict

import numpy as np

import e175_lib as L

ATTRS8 = ['drive', 'foulDraw', 'ft', 'mid', 'pass', 'rebound', 'short', 'tovSkill']
MAIN = ['2022-23', '2023-24', '2024-25']


def load_inputs():
    bt = L.jload(L.V61 / 'backtest.json')
    league = L.jload(L.LEAGUE)
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            cards.setdefault(p['playerId'], p)
    pids = sorted(cards, key=lambda p: (cards[p]['name'], p))
    disc = {r['name']: r['discountFactor'] for r in L.jload(L.DISCOUNT_LOG)}
    h1 = {**L.jload(L.E090 / 'h1-results.json')['h1'], **L.jload(L.E101 / 'h1-results.json')['h1']}
    seas = {s: L.jload(L.E125 / 'pool-P50' / f'raw-{s}.json') for s in MAIN}
    rank_min = {r['name']: float(r['MIN']) for r in csv.DictReader(open(L.R / 'card-0.2.5/ranking.csv', encoding='utf-8'))}

    def bench(name):
        rs = L.jload(L.BENCH / f'{name}.json')['data']['resultSets']
        rs = rs[0] if isinstance(rs, list) else rs
        if name == 'shots':
            return {r[0]: {'shortM': r[6] + r[9], 'shortA': r[7] + r[10], 'midM': r[12], 'midA': r[13]} for r in rs['rowSet']}
        return {r[rs['headers'].index('PLAYER_ID')]: dict(zip(rs['headers'], r)) for r in rs['rowSet']}
    return {'bt': bt, 'cards': cards, 'pids': pids, 'disc': disc, 'h1': h1, 'seas': seas, 'rank_min': rank_min,
            'base': bench('base'), 'shots': bench('shots'),
            'volfit': L.jload(L.E070 / 'vol-fit.json')['fit'], 'astfit': L.jload(L.E125 / 'astvol-fit.json')['fit']}


def passed(h, a, end):
    return bool(h.get(a, {}).get(end, {}).get('pass', False))


def prod_fit(inp, a):
    """0.2.9a 實際用的 V 參數：backtest.json production 的方法 c；mid／short 的先驗是聯盟（E-101 改動一，k／kh／λ 不變）。"""
    f = dict(inp['bt']['production'][a]['fit'])
    if a in ('mid', 'short'):
        f['prior'] = 'league'
    return f


def u_fits(inp):
    """U 臂的收縮參數（backtest.json 方法 b）；vol／astvol 沒有 b 版，沿用它們 fit 的 k 與先驗（§3 只報告，規格沒寫，列入假設）。"""
    bt = inp['bt']
    uf = {a: dict(bt['attrs'][a]['fit']['b']) for a in ('ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'mid', 'short')}
    uf['vol'] = {'k': inp['volfit']['k'], 'prior': inp['volfit']['prior']}
    uf['astvol'] = {'k': inp['astfit']['k'], 'prior': inp['astfit']['prior']}
    for key in ('driveVol', 'driveEff'):
        uf[key] = dict(bt['production']['drive']['components'][key]['b'])
    return uf


def card_chain(D, inp, arm='V'):
    """arm='V'：0.2.9a（按季分塊）；arm='U'：2025-26 季末的滑動窗口版（同一條映射鏈，只換比率）。"""
    UF = u_fits(inp)
    """回傳 dict：rn（卡片名單順序的收縮後比率）、mapped（屬性值）、mappers（供預測誤差用）、診斷資訊。"""
    pids = inp['pids']
    ix = np.array([D.pidx[p] for p in pids])
    cards, base, shots, bt = inp['cards'], inp['base'], inp['shots'], inp['bt']
    pos_card = [cards[p]['pos'] for p in pids]
    names = [cards[p]['name'] for p in pids]
    cur = L.TEST
    out = {'pids': pids, 'names': names, 'rn': {}, 'mapped': {}, 'mappers': {}, 'info': {}}

    def full(attr, season=cur):
        n, d = D.tab[season][attr].agg()
        return n[ix], d[ix]

    def rate_of(attr, fit, n=None, d=None, shift=0.0, m_override=None, nw=None, dw=None):
        n, d = full(attr) if n is None else (n, d)
        if arm == 'U':
            fit = UF[attr]
        kind = fit['prior']
        if m_override is not None:
            m = m_override
        elif kind == 'league':
            m = np.full(len(pids), n.sum() / d.sum())
        else:
            m = L.prior_vec(n, d, 'position', pos_card)
        if arm == 'U':
            if nw is None:
                nw, dw = (x[ix] for x in L.u_sums(D, attr, cur, D.G[cur]))
            return L.shrink_to(nw, dw, m + shift, fit['k'])
        hn, hd = L.hist_arrays(D, attr, cur)
        t = L.hist_target(hn[:, ix], hd[:, ix], m, fit['lam'], fit['kh']) + shift
        return L.shrink_to(n, d, t, fit['k'])

    # ---- 箱型五項＋兩個量價分量（全季，卡片名單的人）----
    rn = {}
    for a in ('ft', 'tovSkill', 'rebound', 'foulDraw', 'pass'):
        rn[a] = rate_of(a, prod_fit(inp, a))
    rn['vol'] = rate_of('vol', inp['volfit'])
    rn['astvol'] = rate_of('astvol', inp['astfit'])

    # ---- mid、short：shots.json 全季（卡片尺度）＋ E-101 PBP 分區的歷史目標，平移 聯盟 shots.json 命中率 − 聯盟 PBP 命中率 ----
    for a in ('mid', 'short'):
        n = np.array([shots.get(p, {}).get(a + 'M', 0) for p in pids], float)
        d = np.array([shots.get(p, {}).get(a + 'A', 0) for p in pids], float)
        pn, pdn = full(a)
        l_pbp = pn.sum() / pdn.sum()
        shift = n.sum() / d.sum() - l_pbp
        fit = prod_fit(inp, a)
        if arm == 'U':
            # U：PBP 分區的窗口加權和（本季逐場 u），先驗＝backtest.json 方法 b 的種類（PBP 尺度），收縮後平移到卡片尺度
            nw, dw = (x[ix] for x in L.u_sums(D, a, cur, D.G[cur]))
            m = np.full(len(pids), l_pbp) if UF[a]['prior'] == 'league' else L.prior_vec(pn, pdn, 'position', pos_card)
            rn[a] = L.shrink_to(nw, dw, m, UF[a]['k']) + shift
            out['info'][a + 'Shift'] = {'leagueShots': float(n.sum() / d.sum()), 'leaguePbp': float(l_pbp), 'shift': float(shift)}
            continue
        hn, hd = L.hist_arrays(D, a, cur)
        t = L.hist_target(hn[:, ix], hd[:, ix], np.full(len(pids), l_pbp), fit['lam'], fit['kh']) + shift
        rn[a] = (n + fit['k'] * t) / (d + fit['k'])
        out['info'][a + 'Shift'] = {'leagueShots': float(n.sum() / d.sum()), 'leaguePbp': float(l_pbp), 'shift': float(shift)}

    # ---- drive：前 41 場（H1）基礎；vol 與 eff 各自收縮，再 0.5·z(vol)＋0.5·z(eff)（池內 z）----
    h1g = D.h1[cur]
    h1_mask = np.array([g in h1g for g in D.gids[cur]])
    dv, de = D.tab[cur]['driveVol'], D.tab[cur]['driveEff']
    # H1 = 2025-26 前 41 場（trainGames 574 場；pergame 的 half 欄）。不一定是日期序的前 574 場，所以用遮罩
    nv, mins = dv.agg_games(h1_mask)
    pts, nW = de.agg_games(h1_mask)
    nv, mins, pts, nW = nv[ix], mins[ix], pts[ix], nW[ix]
    comp = bt['production']['drive']['components']
    drv = {}
    for key, (n, d) in (('driveVol', (nv, mins)), ('driveEff', (pts, nW))):
        if arm == 'U':
            nw, dw = (x[ix] for x in L.u_sums(D, key, cur, D.G[cur]))
            drv[key] = rate_of(key, comp[key]['c'], n=n, d=d, nw=nw, dw=dw)
            if key == 'driveVol':
                uvol_d = dw
        else:
            drv[key] = rate_of(key, comp[key]['c'], n=n, d=d)
    rv, re_ = 36 * drv['driveVol'], drv['driveEff']
    pg = L.read_gz(L.HIST / f'pergame-{cur}.csv.gz')
    gp41 = defaultdict(int)
    for r in pg:
        if r['half'] == '1':
            gp41[int(r['playerId'])] += 1
    gp = np.array([gp41.get(p, 0) for p in pids], float)
    inpool41 = (gp >= L.POOL41_GP) & (mins / np.where(gp > 0, gp, 1) >= L.POOL41_MPG)
    has = (uvol_d > 0) if arm == 'U' else (mins > 0)
    mv, sv, me, se = rv[inpool41].mean(), rv[inpool41].std(), re_[inpool41].mean(), re_[inpool41].std()
    score = .5 * (rv - mv) / sv + .5 * (re_ - me) / se
    rn['drive'] = score
    out['info']['driveZ'] = {'mv': float(mv), 'sv': float(sv), 'me': float(me), 'se': float(se), 'poolN': int(inpool41.sum())}
    out['drive_parts'] = {'vol': rv, 'eff': re_, 'has': has, 'inpool41': inpool41}

    # ---- 組合：foulDraw w=.75、pass w=.5（池內 z，母體 SD）----
    idx = {p: i for i, p in enumerate(pids)}
    pool_pids = [p for p in pids if p in base and base[p]['GP'] >= L.POOL_GP and base[p]['MIN'] / base[p]['GP'] >= L.POOL_MPG]
    pidx_ = np.array([idx[p] for p in pool_pids])
    zs = lambda x: (x - x[pidx_].mean()) / x[pidx_].std()
    comp_fd = .75 * zs(rn['vol']) + .25 * zs(rn['foulDraw'])
    comp_pass = .5 * zs(rn['astvol']) + .5 * zs(rn['pass'])
    out['rn'] = rn
    out['rn_comp'] = {'foulDraw': comp_fd, 'pass': comp_pass}
    out['poolPids'] = pool_pids

    # ---- 映射 ----
    h1 = inp['h1']
    cv = L.curves()
    seas = inp['seas']
    for s in MAIN:
        assert seas[s]['season'] == s

    def info_ok(info, a):
        if info is None:
            return False
        if a == 'drive':
            return info['GP41'] > 0 and info['GP41'] >= L.POOL41_GP and info['MIN41'] / info['GP41'] >= L.POOL41_MPG
        return info['GP'] > 0 and info['GP'] >= L.POOL_GP and info['MIN'] / info['GP'] >= L.POOL_MPG

    def past_pool(a):
        v = []
        for s in MAIN:
            d, info = seas[s]['attrs'].get(a, {}), seas[s]['poolInfo']
            v += [x for k, x in d.items() if info_ok(info.get(k), a)]
        return v

    def past_min500(a):
        v = []
        for s in MAIN:
            d, info = seas[s]['attrs'].get(a, {}), seas[s]['poolInfo']
            v += [x for k, x in d.items() if info.get(k, {'MIN': 0})['MIN'] >= 500]
        return v

    # 百分位型：rebound、tovSkill（取負）、foulDraw、pass（組合）、drive（分數）
    def pct_attr(a, vals, pool_vals_2526, has_mask=None):
        mp = L.PctMapper(list(pool_vals_2526) + past_pool(a), passed(h1, a, 'top'), passed(h1, a, 'bot'))
        v = mp(vals)
        if has_mask is not None:
            v = np.where(has_mask, v, 70.0)
        return v, mp

    inpool_rank = {p: True for p in pool_pids}
    sel = lambda x: [float(x[idx[p]]) for p in pool_pids]
    out['mapped']['rebound'], out['mappers']['rebound'] = pct_attr('rebound', rn['rebound'], sel(rn['rebound']))
    out['mapped']['tovSkill'], mp = pct_attr('tovSkill', -rn['tovSkill'], sel(-rn['tovSkill']))
    out['mappers']['tovSkill'] = mp
    out['mapped']['foulDraw'], out['mappers']['foulDrawComposite'] = pct_attr('foulDraw', comp_fd, sel(comp_fd))
    out['mapped']['pass'], out['mappers']['passComposite'] = pct_attr('pass', comp_pass, sel(comp_pass))
    # drive 池＝前 41 場池（GP41>=15 且 MPG41>=20）內有資料者
    drive_pool = [float(score[i]) for i in range(len(pids)) if inpool41[i]]
    out['mapped']['drive'], out['mappers']['drive'] = pct_attr('drive', score, drive_pool, has_mask=has)

    # 預測誤差用的「比率層」映射（foulDraw、pass 只取 V61 比率本身；池＝同一批池內球員的 2025-26 季末比率，不併過去季）
    for a in ('foulDraw', 'pass'):
        mp = L.PctMapper(sel(rn[a]), passed(h1, a, 'top'), passed(h1, a, 'bot'))
        out['mappers'][a + 'Rate'] = mp

    # 命中率型：ft、mid、short
    rank_min = inp['rank_min']
    POOL = [p for p in pids if rank_min.get(cards[p]['name'], 0) >= 500]
    pool_i = np.array([idx[p] for p in POOL])
    for a, cname in (('ft', 'CURVE_FT'), ('mid', 'CURVE_MID'), ('short', 'CURVE_SHORT')):
        pv = list(rn[a][pool_i]) + past_min500(a)
        mp = L.CurveMapper(cv[cname], pv, passed(h1, a, 'top'), passed(h1, a, 'bot'))
        v = mp(rn[a])
        if a == 'short':
            d = np.array([inp['disc'][nm] for nm in names])
            lo = mp.lo
            out['mappers']['short_discount'] = d
            v = np.array([max(lo, min(L.CEIL, 70 + (x - 70) * f)) for x, f in zip(v, d)])
        out['mapped'][a] = v
        out['mappers'][a] = mp
    out['inpool'] = {'percentileN': len(pool_pids), 'min500N': len(POOL)}
    return out
