"""E-101 §1–§4：寫四個變體的屬性檔、量價屬性檔與 tail-summary.json。由 ../card-0.2.5+E097-topscale/work/build_e097.py 改寫。
三處改動（預註冊 §1–§3）：
- 改動一：mid、short 的 p 用本實驗 a0-e101.json（修正分區＋聯盟先驗）；mid、short 頂端／底端開關看本實驗 h1-results.json，
  midValue、shortValue 看本實驗 h1v-results.json；其他屬性開關照 E-090 h1-results.json。
- 改動二：百分位、r99、r01 對跨季合併池（2025-26 卡片本身的池＋pool/raw-<季>.json 的過去季）；每個球員季算一筆，不去重。
  池門檻：GP >= 30 且 MPG >= 20（drive 同卡片用前 41 場：GP41 >= 15 且 MPG41 >= 20）；命中率型與量價型 MIN >= 500。pressure 不改。
- 改動三：頂端尺 S = max((r99 − r90)/1.044, SD_pool)（e101g 拿掉 max）；百分位型與量價型 top = 99 + 51·(1 − e^(−(r − r99)/(1.96·S)))；
  命中率型 s = 1.96·S_p（S_p 用 MIN >= 500 合併池的 p），a99 照曲線。底端公式照 E-096，池換合併池。
變體：e101（主）、e101z（只有改動一：單季池、尺照 E-096）、e101g（e101 去掉 max）、e101w（長窗：long、ft、foulDraw、tovSkill、pass、rebound、
  physique 2015-16 起，drive 2020-21 起，其餘同 e101）。
檢查：e101z 在 mid、short、midValue、shortValue 以外和 E-096 attributes-e096.csv 逐位相同；常態合成資料 (r99 − r90)/1.044 ≈ SD。
用法（repo 根目錄）：python -I -B reports/card-0.2.5+E101-crossera/work/build_e101.py
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[1]
E090 = ROOT / 'reports/card-0.2.4+E090-onball-tail'
E096 = ROOT / 'reports/card-0.2.5+E096-tail150'
sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
import build_attrs as B  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ATTRS13 = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'creation', 'pressure']
CEIL, K_SD, PSEUDO_MIN, REP_GAP = 150.0, 1.96, 200.0, 0.03
Z9990 = 1.044   # 常態 z.99 − z.90（預註冊 §0）
MAIN = ['2022-23', '2023-24', '2024-25']
LONG = ['2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22']
LONG_ATTRS = {'long', 'ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'drive'}
CARD_SEASON = '2025-26'
raw = json.load(open(E090 / 'work/a0-raw.json', encoding='utf-8'))
H1_E090 = json.load(open(E090 / 'h1-results.json', encoding='utf-8'))['h1']
H1 = {**H1_E090, **json.load(open(OUT / 'h1-results.json', encoding='utf-8'))['h1']}
H1V = json.load(open(OUT / 'h1v-results.json', encoding='utf-8'))['h1v']
P101 = json.load(open(OUT / 'a0-e101.json', encoding='utf-8'))['p']
SEAS = {s: json.load(open(OUT / 'pool' / f'raw-{s}.json', encoding='utf-8')) for s in LONG + MAIN}
cur = {int(r['playerId']): r for r in csv.DictReader(open(E090 / 'work/current-attrs.csv', encoding='utf-8'))}
PIDS = sorted(cur)
rank = {r['name']: float(r['MIN']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.5/ranking.csv', encoding='utf-8'))}
POOL = [p for p in PIDS if rank.get(cur[p]['name'], 0) >= 500]
txt = (ROOT / 'src/constants.js').read_text(encoding='utf-8')
CURVES = {}
for name in ('CURVE_3PT', 'CURVE_MID', 'CURVE_SHORT', 'CURVE_FT'):
    body = re.search(rf'export const {name} = \[(.*?)\];', txt, re.S).group(1)
    CURVES[name] = [(float(a), float(b)) for a, b in re.findall(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', body)]


def passed(h, a, end):
    return bool(h.get(a, {}).get(end, {}).get('pass', False))


def pct(x, arr):
    return 100 * (sum(v < x for v in arr) + 0.5 * sum(v == x for v in arr)) / len(arr)


class Pool:
    """合併池；pct 同上式（小於者 + 0.5·相等者），用排序加速，結果與 pct() 同一算式。"""
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

    def anchors(self, mode):
        r90, r99, r1 = self.r_at_least(90), self.r_at_least(99), self.r_at_most(1)
        sd = float(np.std(self.v))
        gap = (r99 - r90) / Z9990
        S = max(gap, sd) if mode == 'max' else gap
        return {'r90': r90, 'r99': r99, 'r1': r1, 'SD_pool': sd, 'gapScale': gap, 'ratio': gap / sd, 'S': S,
                'insuranceActive': bool(mode == 'max' and sd > gap), 'poolN': self.n}


def attr_of(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def top_tail(d, sd):
    return 99 + (CEIL - 99) * (1 - math.exp(-max(0.0, d) / (K_SD * sd)))


def bot_tail(d, sd):
    return 40 - 15 * (1 - math.exp(-max(0.0, d) / sd))


def inverse_open(p, curve, lo, hi):
    """同 build_e090.inverse_open。"""
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if min(y0, y1) <= p <= max(y0, y1):
            return max(lo, min(hi, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    x = curve[0][0] if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else curve[-1][0]
    return max(lo, min(hi, x))


def percentile_attr_e096(vals, pool_vals, top, bot):
    """E-096 原式（e101z 用；逐位重現 E-096）。"""
    r99 = min(v for v in pool_vals if pct(v, pool_vals) >= 99)
    r1 = max(v for v in pool_vals if pct(v, pool_vals) <= 1)
    sd = float(np.std(pool_vals))
    out = {}
    for pid, x in vals.items():
        p = pct(x, pool_vals)
        if p >= 99 and top:
            out[pid] = top_tail(x - r99, sd)
        elif p <= 1 and bot:
            out[pid] = bot_tail(r1 - x, sd)
        else:
            out[pid] = attr_of(p)
    return out, {'r99': r99, 'r1': r1, 'SD': sd, 'poolN': len(pool_vals)}


def percentile_attr_merged(vals, pool, top, bot, mode):
    """改動二＋三：百分位對合併池；頂端尺 S；底端 E-096 式（SD = 合併池 SD）。"""
    an = pool.anchors(mode)
    out = {}
    for pid, x in vals.items():
        p = pool.pct(x)
        if p >= 99 and top:
            out[pid] = top_tail(x - an['r99'], an['S'])
        elif p <= 1 and bot:
            out[pid] = bot_tail(an['r1'] - x, an['SD_pool'])
        else:
            out[pid] = attr_of(p)
    return out, an


# ---------------------------------------------------------------- 合併池的原料
def in_pool(info, a):
    if info is None:
        return False
    if a == 'drive':
        return info['GP41'] >= B.POOL41[0] and info['MIN41'] / info['GP41'] >= B.POOL41[1] if info['GP41'] > 0 else False
    return info['GP'] >= B.POOL[0] and info['MIN'] / info['GP'] >= B.POOL[1] if info['GP'] > 0 else False


def window(a, var):
    if a == 'pressure':
        return []
    if var == 'e101w' and a in LONG_ATTRS:
        return [s for s in LONG + MAIN if a in SEAS[s]['attrs']]
    return MAIN


def season_vals(a, s, which):
    """過去季 s 的屬性 a：which = 'pool'（百分位型池門檻）、'min500'（命中率型）、'all'。回傳 {pid: v}。"""
    d, info = SEAS[s]['attrs'].get(a, {}), SEAS[s]['poolInfo']
    if which == 'all':
        return {int(k): v for k, v in d.items()}
    if which == 'min500':
        return {int(k): v for k, v in d.items() if info.get(k, {'MIN': 0})['MIN'] >= 500}
    return {int(k): v for k, v in d.items() if in_pool(info.get(k), a)}


def card_p(a):
    return P101[a] if a in ('mid', 'short') else raw[a]['p']


def merged_percentile_pool(a, var):
    vals = list(raw[a]['pool'])
    per = {CARD_SEASON: len(vals)}
    for s in window(a, var):
        v = season_vals(a, s, 'pool')
        vals += list(v.values())
        per[s] = len(v)
    return Pool(vals), per


def merged_curve_pool(a, var):
    vals = [card_p(a)[str(p)] for p in POOL]
    per = {CARD_SEASON: len(vals)}
    for s in window(a, var):
        v = season_vals(a, s, 'min500')
        vals += list(v.values())
        per[s] = len(v)
    return Pool(vals), per


base = {int(r['PLAYER_ID']): r for r in B.bench_rows('base')}
shots = {int(r['PLAYER_ID']): r for r in B.bench_rows('shots')}
MINv = {p: float(base[p]['MIN']) for p in PIDS}


def card_values(z):
    """2025-26 卡片的量價（E-096 §2.3 式；acc = a0-e101 的 p）。"""
    A = {p: float(shots[p][z + 'A']) if p in shots else 0.0 for p in PIDS}
    M = {p: float(shots[p][z + 'M']) if p in shots else 0.0 for p in PIDS}
    mu = sum(A[p] for p in PIDS if MINv[p] > 0) / sum(MINv[p] for p in PIDS if MINv[p] > 0)
    lg = sum(M.values()) / sum(A.values())
    rep = lg - REP_GAP
    rows = {}
    for p in PIDS:
        vol = 36 * (A[p] + PSEUDO_MIN * mu) / (MINv[p] + PSEUDO_MIN)
        acc = P101[z][str(p)]
        rows[p] = {'A': A[p], 'M': M[p], 'MIN': MINv[p], 'vol': vol, 'acc': acc, 'value': vol * (acc - rep)}
    return rows, {'muPerMin': mu, 'leagueRate': lg, 'rep': rep}


CARDVAL = {z: card_values(z) for z in ('mid', 'short')}


def merged_value_pool(k):
    rows = CARDVAL[k[:-5]][0]
    vals = [rows[p]['value'] for p in POOL]
    per = {CARD_SEASON: len(vals)}
    for s in MAIN:
        d = SEAS[s]['value'][k]
        v = [x['value'] for x in d.values() if x['MIN'] >= 500]
        vals += v
        per[s] = len(v)
    return Pool(vals), per


# ---------------------------------------------------------------- 變體
def build(var):
    merged = var != 'e101z'
    mode = 'gap' if var == 'e101g' else 'max'
    new = {pid: {} for pid in PIDS}
    summary = {}
    for a in ATTRS13:
        e = raw[a]
        top, bot = passed(H1, a, 'top'), passed(H1, a, 'bot')
        info = {'type': e['type'], 'topTail': top, 'botTail': bot}
        if e['type'] == 'percentile':
            vals = {pid: e['r'][str(pid)] for pid in PIDS if str(pid) in e['r']}
            if merged and a != 'pressure':
                pool, per = merged_percentile_pool(a, var)
                mapped, anchors = percentile_attr_merged(vals, pool, top, bot, mode)
                info.update(anchors)
                info['poolPerSeason'] = per
            else:
                mapped, anchors = percentile_attr_e096(vals, e['pool'], top, bot)
                info.update(anchors)
                if a != 'pressure':   # 單季池也報同一組錨點，方便對照
                    info['singleSeasonAnchors'] = Pool(e['pool']).anchors('max')
            for pid in PIDS:
                new[pid][a] = mapped.get(pid, float(cur[pid][a]))   # 現行填 70 的人不動
        else:
            curve = CURVES[e['curve']]
            a99 = inverse_open(99, [(y, x) for x, y in curve], -1e9, 1e9)
            pmap = card_p(a)
            lo = 0.0 if bot else 40.0
            if merged:
                pool, per = merged_curve_pool(a, var)
                an = pool.anchors(mode)
                s = K_SD * an['S']
                info.update({**an, 'poolPerSeason': per})
            else:
                sdp = float(np.std([pmap[str(p)] for p in POOL]))
                s = K_SD * sdp
                info.update({'SDp': sdp, 'singleSeasonAnchors': Pool([pmap[str(p)] for p in POOL]).anchors('max')})
            info.update({'curve': e['curve'], 'a99': a99, 'lo': lo, 'hi': CEIL if top else 99.0})
            for pid in PIDS:
                p = pmap[str(pid)]
                if top and p > a99:
                    v = 99 + (CEIL - 99) * (1 - math.exp(-(p - a99) / s)) / (1 - math.exp(-(1 - a99) / s))
                else:
                    v = inverse_open(p, curve, lo, 99.0)
                if a == 'short':
                    v = max(lo, min(CEIL, 70 + (v - 70) * e['discount'][str(pid)]))
                new[pid][a] = v
        summary[a] = info

    val = {}
    for z in ('mid', 'short'):
        rows, meta = CARDVAL[z]
        rows = {p: dict(r) for p, r in rows.items()}
        k = z + 'Value'
        top, bot = passed(H1V, k, 'top'), passed(H1V, k, 'bot')
        vals = {p: rows[p]['value'] for p in PIDS}
        if merged:
            pool, per = merged_value_pool(k)
            mapped, anchors = percentile_attr_merged(vals, pool, top, bot, mode)
            anchors = {**anchors, 'poolPerSeason': per}
        else:
            mapped, anchors = percentile_attr_e096(vals, [rows[p]['value'] for p in POOL], top, bot)
        for p in PIDS:
            v = mapped[p]
            if z == 'short':
                lo = 25.0 if bot else 40.0
                v = max(lo, min(CEIL, 70 + (v - 70) * raw['short']['discount'][str(p)]))
            rows[p]['attr'] = v
        val[k] = rows
        summary[k] = {'type': 'value', 'topTail': top, 'botTail': bot, **meta, **anchors}
    return new, val, summary


# ---------------------------------------------------------------- 各季到 99 的人數（§6；合併錨點下）
def season99(var, summary):
    out = {}
    for a in ATTRS13 + ['midValue', 'shortValue']:
        if a == 'pressure':
            continue
        info = summary[a]
        rows = {}
        seasons = [CARD_SEASON] + window(a, var) if a not in ('midValue', 'shortValue') else [CARD_SEASON] + MAIN
        for s in seasons:
            if info['type'] == 'percentile':
                pool, _ = merged_percentile_pool(a, var)
                if s == CARD_SEASON:
                    allv = {int(k): v for k, v in raw[a]['r'].items()}
                    poolv = list(raw[a]['pool'])
                else:
                    allv = season_vals(a, s, 'all')
                    poolv = list(season_vals(a, s, 'pool').values())
                rows[s] = {'pool': sum(pool.pct(v) >= 99 for v in poolv), 'poolN': len(poolv),
                           'all': sum(pool.pct(v) >= 99 for v in allv.values()), 'allN': len(allv)}
            elif info['type'] == 'curve':
                a99 = info['a99']
                if s == CARD_SEASON:
                    allv = {p: card_p(a)[str(p)] for p in PIDS}
                    poolv = [card_p(a)[str(p)] for p in POOL]
                else:
                    allv = season_vals(a, s, 'all')
                    poolv = list(season_vals(a, s, 'min500').values())
                rows[s] = {'min500': sum(v >= a99 for v in poolv), 'min500N': len(poolv),
                           'all': sum(v >= a99 for v in allv.values()), 'allN': len(allv), 'rule': 'p >= a99（short 為折扣前）'}
            else:
                pool, _ = merged_value_pool(a)
                if s == CARD_SEASON:
                    allv = [r['value'] for r in CARDVAL[a[:-5]][0].values()]
                    poolv = [CARDVAL[a[:-5]][0][p]['value'] for p in POOL]
                else:
                    d = SEAS[s]['value'][a]
                    allv = [x['value'] for x in d.values()]
                    poolv = [x['value'] for x in d.values() if x['MIN'] >= 500]
                rows[s] = {'min500': sum(pool.pct(v) >= 99 for v in poolv), 'min500N': len(poolv),
                           'all': sum(pool.pct(v) >= 99 for v in allv), 'allN': len(allv), 'rule': 'pct >= 99（short 為折扣前）'}
        out[a] = rows
    return out


# ---------------------------------------------------------------- 輸出
name = lambda p: cur[p]['name']
COUNTS = (('>99', lambda v: v > 99), ('==99', lambda v: abs(v - 99) < 1e-9), ('>=99', lambda v: v >= 99 - 1e-9), ('>120', lambda v: v > 120),
          ('>140', lambda v: v > 140), ('>=150', lambda v: v >= 150 - 1e-9), ('<40', lambda v: v < 40))


def write(path, cols):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['playerId', 'name'] + ATTRS13)
        for p in PIDS:
            w.writerow([p, name(p)] + [repr(float(cols(p, a))) for a in ATTRS13])


def write_val(path, val):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['playerId', 'name', 'inPool'] + [f'{z}{c}' for z in ('mid', 'short') for c in ('A', 'M', 'Vol', 'Acc', 'Value', 'Attr')])
        for p in PIDS:
            w.writerow([p, name(p), int(p in POOL)] + [repr(float(val[z + 'Value'][p][c])) for z in ('mid', 'short') for c in ('A', 'M', 'vol', 'acc', 'value', 'attr')])


# 合成資料檢查：常態下 (r99 − r90)/1.044 ≈ SD（S = SD）
rng = np.random.default_rng(20261030)
syn = Pool(rng.standard_normal(20000).tolist()).anchors('max')
assert abs(syn['ratio'] - 1) < 0.05, syn
synthetic = {'normal_n20000_seed20261030': {k: syn[k] for k in ('r90', 'r99', 'SD_pool', 'gapScale', 'ratio')}}
print('synthetic normal ratio', round(syn['ratio'], 4))

summaries = {'_synthetic': synthetic, '_rules': {
    'S': 'max((r99 − r90)/1.044, SD_pool)；e101g = (r99 − r90)/1.044；insuranceActive = SD_pool > (r99 − r90)/1.044（保險生效、取 SD）',
    'ratio': '(r99 − r90)/1.044 ÷ SD_pool', 'pools': '百分位型 GP>=30 且 MPG>=20（drive 前 41 場 GP41>=15 且 MPG41>=20）；命中率型、量價型 MIN>=500；2025-26 為卡片本身的池',
    'switches': 'mid、short：本實驗 h1-results.json；midValue、shortValue：本實驗 h1v-results.json；其他：E-090 h1-results.json'}}
VARS = ['e101', 'e101z', 'e101g', 'e101w']
for var in VARS:
    new, val, summary = build(var)
    for a, info in summary.items():
        vals = {p: (val[a][p]['attr'] if a in val else new[p][a]) for p in PIDS}
        info['count'] = {k: sum(f(v) for v in vals.values()) for k, f in COUNTS}
        info['above99'] = [[name(p), round(vals[p], 2)] for p in sorted(PIDS, key=lambda p: -vals[p]) if vals[p] > 99]
        info['below40'] = [[name(p), round(vals[p], 2)] for p in sorted(PIDS, key=lambda p: vals[p]) if vals[p] < 40]
    if var != 'e101z':
        summary['_season99'] = season99(var, summary)
    write(OUT / f'attributes-{var}.csv', lambda p, a: new[p][a])
    write_val(OUT / f'value-attrs-{var}.csv', val)
    summaries[var] = summary

# e101z 對照：mid、short 以外 11 項和 E-096 attributes-e096.csv 逐位相同
ref = {r['playerId']: r for r in csv.DictReader(open(E096 / 'attributes-e096.csv', encoding='utf-8'))}
mine = {r['playerId']: r for r in csv.DictReader(open(OUT / 'attributes-e101z.csv', encoding='utf-8'))}
assert set(ref) == set(mine)
bad = [(k, a) for k in ref for a in ATTRS13 if a not in ('mid', 'short') and ref[k][a] != mine[k][a]]
assert not bad, bad[:5]
summaries['_e101zControl'] = {'vsE096attributes': '11 項（mid、short 以外）582 人逐字串相同', 'mismatch': 0}
json.dump(summaries, open(OUT / 'tail-summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for var in VARS:
    print('==', var)
    for a, v in summaries[var].items():
        if a.startswith('_'):
            continue
        print(f"  {a:10s} top={v['topTail']!s:5s} bot={v['botTail']!s:5s} ratio={v.get('ratio', float('nan')):.3f} ins={v.get('insuranceActive')} "
              f"N={v.get('poolN')} {{'>99': {v['count']['>99']}, '>120': {v['count']['>120']}, '>140': {v['count']['>140']}}} top3={v['above99'][:3]}")
