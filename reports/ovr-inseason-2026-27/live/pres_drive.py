"""壓迫（pressure／presDisplay）與切入（drive）賽中解凍（2026-11-01）。

做法同 rookie_defense.py 的 onBall／help：
- 老將：四季窗口逐場線性遞減（rookie_defense.window_weights(c)、units 同一套）。每季先算「原始累計量」，乘該季權重相加，
  再除以這個人有資料那幾季的 units 和（下限＝他各季權重的最大值），然後套卡片公式；常數全部凍結在 2025-26。
- 新秀（沒有先驗卡）：本季有資料就用本季值（w=1，R-075）。
- 算不出的人維持先驗卡。

pressure（card 0.2.7b 的實際路徑＝E-071 force → E-123 合併池百分位＋h1 尾巴）：
  分量 stl、defl、chg（count, MIN/36）、mtov（tov−exp, poss/100）、pf（count, MIN/36），k＝E-071 shrink.json；
  mtov 的期望值每季用該季的進攻方失誤率算（build_force.season_raw），(tov−exp, poss) 再照窗口權重相加。
  收縮目標 m、池平均／標準差＝2025-26 卡片池（252 人，GP≥30 且 MPG≥20）；force＝(z_stl＋z_defl＋z_mtov＋0.5·z_chg)/3.5，
  presDisplay 用 disp＝force − 0.25·z_pf；兩者都對 E-123 四季合併池（work/season-values.json）取百分位，頂端尾巴照 E-123 h1。
drive（card 0.2.7b＝E-101 合併池百分位＋E-090 h1 尾巴，底下是 v61 方法 c）：
  vol＝36·(nv＋k·Tv)/(min＋k)、eff＝(pts＋k·Te)/(nW＋k)，k＝90.509668；Tv／Te＝卡片的歷史目標（2022-23～2024-25，λ＝0.5、kh＝32、
  同位置平均 m 凍結在 2025-26 前 41 場），score＝0.5·z(vol)＋0.5·z(eff)（平均／標準差凍結在 2025-26 卡片池），
  再對 E-101 合併池（2025-26＋2022-23～2024-25）取百分位，頂底尾巴照 E-101。
  權重：被助攻進球 0、未助攻進球 1、失手＝該季該類別的未助攻比例（每季用自己的出手算）。
  窗口用各季全季的量（卡片用前 41 場是 v60 的歷史包袱；--check 才用前 41 場重現卡片）。

用法：python -I -X utf8 pres_drive.py --check   （全部權重給 2025-26，逐人對照先驗卡 pressure／drive／presDisplay）
開關：環境變數 UNFREEZE_PD（預設 1；設 0 時 run_c4_live_rookie.py 完全不呼叫本檔，輸出逐位元同解凍前）。
"""
import csv
import gzip
import importlib.util
import io
import json
import math
import os
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import rookie_defense as RD  # noqa: E402
import split_dc as SD  # noqa: E402（0.2.10i：SPLIT_DC=1 時 drive 換 D 類候選、合併池換 D 類池值；0 時不動）

ON = os.environ.get('UNFREEZE_PD', '1') != '0'
SEASON = '2026-27'
CARD = '2025-26'
PAST = RD.PAST                       # 2022-23 .. 2025-26
CUR = ROOT / 'data/defense-seventh' / SEASON
E071 = ROOT / 'reports/card-0.2.0+E071-pressure'
E123 = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
E090 = ROOT / 'reports/card-0.2.4+E090-onball-tail'
E101 = ROOT / 'reports/card-0.2.5+E101-crossera'
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
DT = ROOT / 'reports/defense-tenth/step4-t2/raw'
LEAGUE_E2 = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
PRIOR_CARD = RD.PRIOR_CARD
CEIL, K_SD, Z9990 = 150.0, 1.96, 1.044
POOL41 = (15, 20)
GROUP = {'PG': 'G', 'SG': 'G', 'SF': 'F', 'PF': 'F', 'C': 'C'}


# ------------------------------------------------------------------ 映射（build_e101.py 的 Pool／attr_of／尾巴逐行複製）
class Pool:
    def __init__(self, vals):
        self.v = [float(x) for x in vals]
        self.s = np.sort(np.array(self.v))
        self.n = len(self.v)

    def pct(self, x):
        lo = int(np.searchsorted(self.s, x, 'left'))
        hi = int(np.searchsorted(self.s, x, 'right'))
        return 100 * (lo + 0.5 * (hi - lo)) / self.n

    def r_at_least(self, q):
        return min(v for v in self.s.tolist() if self.pct(v) >= q)

    def r_at_most(self, q):
        return max(v for v in self.s.tolist() if self.pct(v) <= q)

    def anchors(self, mode='max'):
        r90, r99, r1 = self.r_at_least(90), self.r_at_least(99), self.r_at_most(1)
        sd = float(np.std(self.v))
        gap = (r99 - r90) / Z9990
        S = max(gap, sd) if mode == 'max' else gap
        return {'r90': r90, 'r99': r99, 'r1': r1, 'SD_pool': sd, 'S': S, 'poolN': self.n}


def attr_of(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def top_tail(d, sd):
    return 99 + (CEIL - 99) * (1 - math.exp(-max(0.0, d) / (K_SD * sd)))


def bot_tail(d, sd):
    return 40 - 15 * (1 - math.exp(-max(0.0, d) / sd))


class Mapper:
    """percentile_attr_merged 的單值版（同式）。"""
    def __init__(self, vals, top, bot):
        self.pool = Pool(vals)
        self.an = self.pool.anchors('max')
        self.top, self.bot = top, bot

    def __call__(self, x):
        p = self.pool.pct(x)
        if p >= 99 and self.top:
            return top_tail(x - self.an['r99'], self.an['S'])
        if p <= 1 and self.bot:
            return bot_tail(self.an['r1'] - x, self.an['SD_pool'])
        return attr_of(p)


def _rs(path):
    rs = json.loads(Path(path).read_text(encoding='utf-8'))['data']['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    return [dict(zip(rs['headers'], r)) for r in rs['rowSet']]


@lru_cache(None)
def _cur_games():
    return _rs(CUR / 'player-games.json')


# ------------------------------------------------------------------ pressure
_spec = importlib.util.spec_from_file_location('bf071_live', E071 / 'build_force.py')
BF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BF)           # 只載入函式
KS = json.loads((E071 / 'shrink.json').read_text(encoding='utf-8'))['k']
COMPS = BF.COMPS


def _cur_base():
    """本季 base 表（player-games 加總：MIN、GP、STL、PF；MIN 是逐場整數分鐘）。"""
    acc = {}
    for r in _cur_games():
        a = acc.setdefault(r['PLAYER_ID'], {'PLAYER_ID': r['PLAYER_ID'], 'PLAYER_NAME': r['PLAYER_NAME'], 'MIN': 0.0, 'GP': 0, 'STL': 0.0, 'PF': 0.0})
        a['MIN'] += float(r['MIN'] or 0); a['GP'] += 1
        a['STL'] += float(r['STL'] or 0); a['PF'] += float(r['PF'] or 0)
    return list(acc.values())


def p_table(season, kind):
    """各季原始表：路徑同 e123lib._table；本季讀 data/defense-seventh/2026-27。"""
    if season == SEASON:
        return _cur_base() if kind == 'base' else _rs(CUR / 'tracking' / f'{kind}.json')
    if kind == 'base':
        p = (E123 / 'data' if season in ('2022-23', '2023-24') else E071 / 'data') / f'{season}-base.json'
    elif season in ('2022-23', '2023-24'):
        p = DT / season / f'0-{kind}.json'
    else:
        p = E071 / 'data' / f'{season}-{kind}.json'
    return _rs(p)


BF.table = p_table


def _p_comps(season):
    raw, mt, _ = BF.season_raw(season)
    return raw, BF.comps_of(raw, mt)


@lru_cache(None)
def _p_comps_past(season):
    return _p_comps(season)


def p_comps(season):
    return _p_comps(season) if season == SEASON else _p_comps_past(season)


@lru_cache(None)
def p_frozen():
    """2025-26 卡片池的收縮目標 m、池平均／標準差（e123lib.p_season(use_card_pool=True) 同式）＋ E-123 合併池映射。"""
    raw, comps = (dict(x) for x in p_comps(CARD))
    league = json.loads(LEAGUE_E2.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            c = cards.setdefault(p['playerId'], {'name': p['name'], 'GP': 0, 'MIN': 0.0})
            c['GP'] += p['observed']['GP']; c['MIN'] += p['observed']['MIN']
    pool = {pid for pid, c in cards.items() if c['GP'] >= 30 and c['MIN'] / c['GP'] >= 20}
    for pid in cards:
        if pid not in raw:
            raw[pid] = {'name': cards[pid]['name'], 'MIN': 0.0, 'GP': 0}
            comps[pid] = {c: (0.0, 0.0) for c in COMPS}
    _, _, _, st = BF.force_table(comps, raw, pool, KS)
    sv = json.loads((E123 / 'work/season-values.json').read_text(encoding='utf-8'))['vals']['P']
    h1 = json.loads((E123 / 'h1-results.json').read_text(encoding='utf-8'))['h1']['pressure']
    top, bot = bool(h1['top']['pass']), bool(h1['bot']['pass'])   # presDisplay 兩端跟 pressure（E-123 預註冊 §2.3）
    seas = ['2022-23', '2023-24', '2024-25', '2025-26']
    mp = Mapper([float(v['force']) for s in seas for v in sv[s].values() if v['inPool']], top, bot)
    md = Mapper([float(v['disp']) for s in seas for v in sv[s].values() if v['inPool']], top, bot)
    return st, mp, md


def p_value(n, d):
    """窗口累計 (n, d) → 收縮後分量、z、force、disp、pressure、presDisplay（算式同 build_force.force_table）。"""
    st, mp, md = p_frozen()
    m, mu, sd = st['poolRatio'], st['poolMean'], st['poolSd']
    shr = {c: (n[c] + KS[c] * m[c]) / (d[c] + KS[c]) for c in COMPS}
    z = {c: (shr[c] - mu[c]) / sd[c] for c in COMPS}
    force = (z['stl'] + z['defl'] + z['mtov'] + 0.5 * z['chg']) / 3.5
    disp = force - 0.25 * z['pf']
    return {'pressure': mp(force), 'presDisplay': md(disp), 'force': force, 'disp': disp,
            'shr': shr, 'minW': d['stl'] * 36}


def p_window(parts):
    """parts：[(季, 權重, units, (raw, comps))] → {pid: p_value(...)}。有資料＝出現在該季 base 表。"""
    acc, fu = {}, {}
    for s, w, u, (raw, comps) in parts:
        for pid in raw:
            a = acc.setdefault(pid, {c: [0.0, 0.0] for c in COMPS})
            for c in COMPS:
                a[c][0] += w * comps[pid][c][0]
                a[c][1] += w * comps[pid][c][1]
            f = fu.setdefault(pid, [0.0, 0.0]); f[0] += u; f[1] = max(f[1], w)
    out = {}
    for pid, a in acc.items():
        div = max(fu[pid])
        if div <= 0:
            continue
        out[pid] = p_value({c: a[c][0] / div for c in COMPS}, {c: a[c][1] / div for c in COMPS})
    return out


# ------------------------------------------------------------------ drive
def _gz(path):
    with gzip.open(SD.drive_path(path), 'rb') as fh:
        return list(csv.DictReader(io.TextIOWrapper(fh, encoding='utf-8')))


def _pu(shots):
    """v61 engine.drive_weights：類別未助攻比例。"""
    made, un = defaultdict(int), defaultdict(int)
    for s in shots:
        if s['made']:
            made[s['cls']] += 1
            un[s['cls']] += not s['assisted']
    return {k: un[k] / made[k] for k in made}


def _cur_drive_shots():
    sys.path.insert(0, str(V61))
    try:
        import extract_pbp as XP   # noqa: E402（v61 的 parse_game：卡片 drive 的 PBP 解析，同一份程式）
    finally:
        sys.path.remove(str(V61))
    shots, gids = [], set()
    for p in sorted((CUR / 'pbp').glob('*.json')):
        gid, _, drive = (SD.parse_drive if SD.ON else XP.parse_game)((p.stem, p))
        gids.add(gid)
        shots += [{'gid': gid, 'pid': int(a), 'made': m, 'assisted': ast, 'ftmade': ft, 'cls': cls} for a, m, ast, ft, cls in drive]
    return shots, gids


def drive_counts(season, half=None, pu_half=None):
    """{pid: [nv, min, pts, nW, gp]}。half＝1／2 只算那半季（--check 用 1）；pu_half：失手權重只用那半季的出手（卡片用 1），None＝同計數範圍。
    本季：PBP 有檔的場才算分鐘（缺 PBP 的場不算，免得分母多算）。"""
    if season == SEASON:
        shots, gids = _cur_drive_shots()
        rows = [r for r in _cur_games() if r['GAME_ID'] in gids]
        mins = [(int(r['PLAYER_ID']), float(r['MIN'] or 0)) for r in rows]
        use = shots
        pu = _pu(shots)
    else:
        pg = _gz(V61 / 'history' / f'pergame-{season}.csv.gz')
        half_of = {r['gameId']: int(r['half']) for r in pg}
        keep = lambda g: g in half_of and (half is None or half_of[g] == half)
        mins = [(int(r['playerId']), float(r['MIN'])) for r in pg if keep(r['gameId'])]
        shots = [{'gid': r['gameId'], 'pid': int(r['playerId']), 'made': int(r['made']), 'assisted': int(r['assisted']),
                  'ftmade': int(r['ftmade']), 'cls': r['cls']} for r in _gz(V61 / 'history' / f'pbp-drive-{season}.csv.gz')]
        use = [s for s in shots if keep(s['gid'])]
        ph = pu_half if pu_half is not None else half
        pu = _pu([s for s in shots if s['gid'] in half_of and (ph is None or half_of[s['gid']] == ph)])
    out = {}
    get = lambda p: out.setdefault(p, [0.0, 0.0, 0.0, 0.0, 0])
    for pid, m in mins:
        x = get(pid); x[1] += m; x[4] += 1
    for s in use:
        if s['assisted'] and s['made']:
            continue                      # 被助攻進球權重 0（engine：not made and assisted 也跳過）
        if s['assisted'] and not s['made']:
            continue
        w = 1.0 if s['made'] else pu.get(s['cls'], 1.0)
        x = get(s['pid'])
        x[0] += w; x[3] += w
        if s['made']:
            x[2] += 2 + s['ftmade']
    return out


@lru_cache(None)
def _drive_past(season, half=None, pu_half=None):
    return drive_counts(season, half, pu_half)


def drive_counts_c(season, half=None, pu_half=None):
    return drive_counts(season, half, pu_half) if season == SEASON else _drive_past(season, half, pu_half)


@lru_cache(None)
def d_frozen():
    """卡片 drive 的凍結件：每人歷史目標 Tv／Te、同位置平均、z 的平均／標準差、E-101 合併池映射。全部只用 2025-26 以前。"""
    fit = json.loads((V61 / 'backtest.json').read_text(encoding='utf-8'))['production']['drive']
    assert fit['selected'] == 'c'
    fv, fe = fit['components']['driveVol']['c'], fit['components']['driveEff']['c']
    assert fv['prior'] == fe['prior'] == 'position'
    league = json.loads(LEAGUE_E2.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            cards.setdefault(p['playerId'], p)
    pids = sorted(cards, key=lambda p: (cards[p]['name'], p))
    pos_card = {p: cards[p]['pos'] for p in pids}
    prior = {p['playerId']: p for p in json.load(open(PRIOR_CARD, encoding='utf-8'))['players']}
    allp = pids + sorted(p for p in prior if p not in pos_card)
    pos_all = {**{p: prior[p]['pos'] for p in prior}, **pos_card}
    c26 = drive_counts_c(CARD, 1)
    z5 = [0.0] * 5
    col = lambda i: np.array([c26.get(p, z5)[i] for p in pids], float)
    nv, mins, pts, nW, gp = col(0), col(1), col(2), col(3), col(4)
    inpool = (gp >= POOL41[0]) & (mins / np.where(gp > 0, gp, 1) >= POOL41[1])
    # 同位置平均（build_attrs：2025-26 前 41 場、卡片 pids、卡片位置）；新秀 G／F／C 用合併組
    m = {}
    for key, n_, d_ in (('v', nv, mins), ('e', pts, nW)):
        pn, pd_, gn, gd = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
        for i, p in enumerate(pids):
            pn[pos_card[p]] += n_[i]; pd_[pos_card[p]] += d_[i]
            gn[GROUP[pos_card[p]]] += n_[i]; gd[GROUP[pos_card[p]]] += d_[i]
        m[key] = {**{q: pn[q] / pd_[q] for q in pn}, **{q: gn[q] / gd[q] for q in gn}, None: n_.sum() / d_.sum()}
    # 歷史目標（engine.hist_target：最近 3 季全季量，失手權重用各季上半季）
    hs = ['2024-25', '2023-24', '2022-23']
    hc = [drive_counts_c(s, None, 1) for s in hs]
    hn = {k: np.array([[h.get(p, z5)[i] for p in allp] for h in hc], float) for k, i in (('v', 0), ('e', 2))}
    hd = {k: np.array([[h.get(p, z5)[i] for p in allp] for h in hc], float) for k, i in (('v', 1), ('e', 3))}
    T = {}
    for key, f_ in (('v', fv), ('e', fe)):
        mm = np.array([m[key].get(pos_all.get(p), m[key][None]) for p in allp])
        w = np.array([f_['lam'] ** j for j in range(3)])[:, None]
        t = ((w * hn[key]).sum(0) + f_['kh'] * mm) / ((w * hd[key]).sum(0) + f_['kh'])
        T[key] = {p: float(t[i]) for i, p in enumerate(allp)}
    # z 的平均／標準差：2025-26 卡片的拉回後比率（前 41 場）在卡片池
    ix = {p: i for i, p in enumerate(allp)}
    tv = np.array([T['v'][p] for p in pids]); te = np.array([T['e'][p] for p in pids])
    vol = 36 * np.where(mins + fv['k'] > 0, (nv + fv['k'] * tv) / (mins + fv['k']), tv)
    eff = np.where(nW + fe['k'] > 0, (pts + fe['k'] * te) / (nW + fe['k']), te)
    stats = (vol[inpool].mean(), vol[inpool].std(), eff[inpool].mean(), eff[inpool].std())
    # E-101 合併池：2025-26 卡片池＋2022-23～2024-25（GP41≥15 且 MPG41≥20）；尾巴開關照 E-090 h1（E-101 的 H1＝{**E090, **E101}）
    raw = json.load(open(E090 / 'work/a0-raw.json', encoding='utf-8'))['drive']
    pdD = SD.pool_drive_D() if SD.ON else None
    vals = list(pdD['D_pool2526'] if SD.ON else raw['pool'])
    for s in ('2022-23', '2023-24', '2024-25'):
        sd_ = json.load(open(E101 / 'pool' / f'raw-{s}.json', encoding='utf-8'))
        info = sd_['poolInfo']
        for k, v in (pdD['D'][s] if SD.ON else sd_['attrs']['drive']).items():
            q = info.get(k)
            if q is not None and q['GP41'] > 0 and q['GP41'] >= POOL41[0] and q['MIN41'] / q['GP41'] >= POOL41[1]:
                vals.append(v)
    h1 = {**json.load(open(E090 / 'h1-results.json', encoding='utf-8'))['h1'], **json.load(open(E101 / 'h1-results.json', encoding='utf-8'))['h1']}
    mp = Mapper(vals, bool(h1['drive']['top']['pass']), bool(h1['drive']['bot']['pass']))
    return {'kv': fv['k'], 'ke': fe['k'], 'T': T, 'm': m, 'stats': stats, 'map': mp, 'pids': pids, 'pos': pos_all,
            'inpool': {p for i, p in enumerate(pids) if inpool[i]}, 'c26': c26}


def d_value(N, pos=None, pid=None):
    """窗口累計 [nv, min, pts, nW] → drive 屬性（同卡片公式；沒有歷史的人 T＝同位置平均）。"""
    F = d_frozen()
    tv = F['T']['v'].get(pid, F['m']['v'].get(pos, F['m']['v'][None]))
    te = F['T']['e'].get(pid, F['m']['e'].get(pos, F['m']['e'][None]))
    nv, mins, pts, nW = N
    vol = 36 * ((nv + F['kv'] * tv) / (mins + F['kv']))
    eff = (pts + F['ke'] * te) / (nW + F['ke'])
    mv, sv, me, se = F['stats']
    score = .5 * (vol - mv) / sv + .5 * (eff - me) / se
    return {'drive': F['map'](score), 'score': score, 'vol': vol, 'eff': eff}


def d_window(parts, pos=None, use_hist=True):
    """parts：[(季, 權重, units, counts)] → {pid: d_value}。有資料＝該季有上場分鐘。use_hist=False：T 一律用同位置平均（新秀）。"""
    acc, fu = {}, {}
    for s, w, u, cnt in parts:
        for pid, x in cnt.items():
            if x[1] <= 0:
                continue
            a = acc.setdefault(pid, [0.0, 0.0, 0.0, 0.0])
            for i in range(4):
                a[i] += w * x[i]
            f = fu.setdefault(pid, [0.0, 0.0]); f[0] += u; f[1] = max(f[1], w)
    pos = pos or {}
    F = d_frozen()
    out = {}
    for pid, a in acc.items():
        div = max(fu[pid])
        if div <= 0 or a[1] <= 0:
            continue
        p = pos.get(pid) or F['pos'].get(pid)
        out[pid] = d_value([x / div for x in a], p, pid if use_hist else None)
    return out


# ------------------------------------------------------------------ 對外
def veteran(c, cur=True):
    """老將四季窗口：{pid: {'pressure', 'presDisplay', 'drive', 'force', 'shr', 'minW'}}、權重。本季資料沒有就只用往年四季。
    cur=False：同一個 c 的權重但不讀本季（＝本季 0 場時的值；ΔOVR 基準用，R-112）。"""
    ww = RD.window_weights(c)
    seasons = list(PAST) + ([SEASON] if cur and c > 0 and (CUR / 'tracking/hustle.json').exists() else [])
    ww = {s: ww[s] for s in seasons if s in ww}
    units = {s: ww[s] * (c / RD.SLOTS if s == SEASON else 1.0) for s in ww}
    pp = p_window([(s, ww[s], units[s], p_comps(s)) for s in ww])
    dd = d_window([(s, ww[s], units[s], drive_counts_c(s)) for s in ww])
    return merge(pp, dd), ww


def inseason(pos=None):
    """新秀本季值（w=1）：{pid: {...}}。pos：{pid: G/F/C}（drive 的同位置平均）。"""
    if not (CUR / 'tracking/hustle.json').exists():
        return {}
    pp = p_window([(SEASON, 1.0, 1.0, p_comps(SEASON))])
    dd = d_window([(SEASON, 1.0, 1.0, drive_counts_c(SEASON))], pos, use_hist=False)
    return merge(pp, dd)


def merge(pp, dd):
    out = {}
    for pid, v in pp.items():
        out.setdefault(pid, {}).update(v)
    for pid, v in dd.items():
        out.setdefault(pid, {})['drive'] = v['drive']
    return out


def check():
    """全部權重給 2025-26（pressure 全季、drive 前 41 場＝卡片的定義），逐人對照先驗卡。"""
    card = {p['playerId']: p for p in json.load(open(PRIOR_CARD, encoding='utf-8'))['players']}
    pp = p_window([(CARD, 1.0, 1.0, p_comps(CARD))])
    F = d_frozen()
    dd = d_window([(CARD, 1.0, 1.0, F['c26'])])
    res = {}

    def stat(key, got, want, rnd=None):
        d = [abs(got[p] - want[p]) for p in want if p in got]
        res[key] = {'n': len(d), 'maxAbs': max(d), 'n>0.1': sum(x > 0.1 for x in d)}
    stat('pressure', {p: v['pressure'] for p, v in pp.items()}, {p: float(c['pressure']) for p, c in card.items()})
    stat('presDisplay(card 0.1 位)', {p: v['presDisplay'] for p, v in pp.items()},
         {p: float(c['presDisplay']) for p, c in card.items() if c.get('presDisplay') not in (None, '')})
    stat('drive', {p: v['drive'] for p, v in dd.items()}, {p: float(c['drive']) for p, c in card.items()})
    # 沒資料的人（drive：前 41 場沒上場 → 卡片 70；pressure：不在 2025-26 base）＝賽中維持先驗卡
    res['noData'] = {'pressure': sorted(p for p in card if p not in pp), 'drive': len([p for p in card if p not in dd])}
    # 中間量：drive score 對 E-090 a0-raw.json 的卡片 r
    raw = json.load(open(E090 / 'work/a0-raw.json', encoding='utf-8'))['drive']['r']
    ds = [abs(dd[int(k)]['score'] - v) for k, v in raw.items() if int(k) in dd]
    res['driveScoreVsCardR'] = {'n': len(ds), 'maxAbs': max(ds)}
    an = F['map'].an
    ref = json.load(open(E101 / 'tail-summary.json', encoding='utf-8'))['e101']['drive']
    res['driveAnchorsVsE101'] = {k: abs(an[k] - ref[k]) for k in ('r90', 'r99', 'r1', 'SD_pool', 'S')} | {'poolN': [an['poolN'], ref['poolN']]}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--check' in sys.argv:
        check()
    else:
        import time
        t = time.time()
        v, ww = veteran(13.0)
        print(len(v), ww, round(time.time() - t, 1))
