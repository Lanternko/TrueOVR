"""E-123：合併池尾巴 -> work/tail-new.csv、work/def-new.csv、three-value-e123.csv、work/presDisplay-new.csv、tail-summary.json。
公式與常數照 E-101 build_e101.py（Pool、percentile_attr_merged、top_tail、bot_tail、inverse_open 逐字沿用）；H 照 D1（曲線型、x = −shrunk、不含位置項）。
h1 開哪端照 h1-results.json（預註冊 §4）；不看結果挑任何參數（L-026）。從本資料夾根目錄跑：python -I -X utf8 work/build_tails.py
"""
import csv, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
E123 = HERE.parent
ROOT = E123.parents[1]
sys.path.insert(0, str(HERE))
import e123lib as L   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
CEIL, K_SD = 150.0, 1.96
Z9990 = 1.044
SEASONS = L.SEASONS
CARD = '2025-26'

TAIL_SRC = ROOT / 'reports/card-0.2.5+E101-crossera/attributes-e101.csv'
DEF_SRC = ROOT / 'reports/card-0.1.1+E060-onball-targeting/defense-attributes-e060.csv'
TV_SRC = ROOT / 'reports/card-0.1.1+E057-three-value/three-value.csv'
C027 = ROOT / 'reports/card-0.2.7/ranking.csv'


# ---------------- 以下逐字沿用 E-101 build_e101.py ----------------
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
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if min(y0, y1) <= p <= max(y0, y1):
            return max(lo, min(hi, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    x = curve[0][0] if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else curve[-1][0]
    return max(lo, min(hi, x))


def percentile_attr_merged(vals, pool, top, bot, mode):
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
# ---------------- 沿用結束 ----------------

COUNTS = (('>99', lambda v: v > 99), ('==99', lambda v: abs(v - 99) < 1e-9), ('>=99', lambda v: v >= 99 - 1e-9), ('>120', lambda v: v > 120),
          ('>140', lambda v: v > 140), ('>=150', lambda v: v >= 150 - 1e-9), ('<40', lambda v: v < 40))

H1 = json.loads((E123 / 'h1-results.json').read_text(encoding='utf-8'))['h1']
SV = json.loads((HERE / 'season-values.json').read_text(encoding='utf-8'))['vals']
passed = lambda part, end: bool(H1[part][end]['pass'])
# presDisplay 的兩端跟 pressure 的 h1（預註冊 §2.3）；presDisplay 自己的 h1 只報告
TOP = {'threeValue': passed('threeValue', 'top'), 'help': passed('help', 'top'), 'pressure': passed('pressure', 'top'), 'presDisplay': passed('pressure', 'top')}
BOT = {'threeValue': passed('threeValue', 'bot'), 'help': passed('help', 'bot'), 'pressure': passed('pressure', 'bot'), 'presDisplay': passed('pressure', 'bot')}

# ---------------- 現行值與人群 ----------------
tail_rows = list(csv.DictReader(open(TAIL_SRC, encoding='utf-8')))
tail_hdr = list(tail_rows[0].keys())
PIDS = [int(r['playerId']) for r in tail_rows]
name = {int(r['playerId']): r['name'] for r in tail_rows}
def_rows = list(csv.DictReader(open(DEF_SRC, encoding='utf-8')))
def_hdr = list(def_rows[0].keys())
assert [int(r['playerId']) for r in def_rows] == PIDS or set(int(r['playerId']) for r in def_rows) == set(PIDS)
def_by = {int(r['playerId']): r for r in def_rows}
tv_rows = list(csv.DictReader(open(TV_SRC, encoding='utf-8')))
tv_by = {int(r['playerId']): r for r in tv_rows}
assert set(tv_by) == set(PIDS), (len(tv_by), len(PIDS))
card_by_name = {r['name']: r for r in csv.DictReader(open(C027, encoding='utf-8'))}
cur_pd = {p: float(card_by_name[name[p]]['presDisplay']) for p in PIDS if name[p] in card_by_name}
assert len(cur_pd) == len(PIDS), [name[p] for p in PIDS if p not in cur_pd][:5]

cur = {
    'threeValue': {p: float(tv_by[p]['tv_main']) for p in PIDS},
    'help': {p: float(def_by[p]['new_help']) for p in PIDS},
    'pressure': {p: float(next(r for r in tail_rows if int(r['playerId']) == p)['pressure']) for p in PIDS},
    'presDisplay': cur_pd,
}
pool_ids = {'T': {}, 'H': {}, 'P': {}}
S_ = lambda part, s: SV[part][s]
poolT = lambda s: [float(v['value']) for v in S_('T', s).values() if (v['MIN'] or 0) >= 500]
poolH = lambda s: [float(v['x']) for v in S_('H', s).values() if (v['MIN'] or 0) >= 500 and v['n'] > 0]
poolPf = lambda s: [float(v['force']) for v in S_('P', s).values() if v['inPool']]
poolPd = lambda s: [float(v['disp']) for v in S_('P', s).values() if v['inPool']]

new, summary = {}, {}

# ---------------- T：threeValue（百分位型，E-057 的 value 當原始量） ----------------
nl = json.loads((L.V62 / 'new-long.json').read_text(encoding='utf-8'))
tv26 = S_('T', CARD)
has = {p for p in PIDS if str(p) in nl and str(p) in tv26}
poolsT = {s: poolT(s) for s in SEASONS}
PT = Pool([x for s in SEASONS for x in poolsT[s]])
valsT = {p: float(tv26[str(p)]['value']) for p in has}
mappedT, anT = percentile_attr_merged(valsT, PT, TOP['threeValue'], BOT['threeValue'], 'max')
new['threeValue'] = {p: mappedT.get(p, 70.0) for p in PIDS}      # 沒有三分資料者給 70（同 E-057）
summary['threeValue'] = dict(type='value(percentile)', topTail=TOP['threeValue'], botTail=BOT['threeValue'], **anT,
                             poolPerSeason={s: len(poolsT[s]) for s in SEASONS}, note=f'card players with data {len(has)}/{len(PIDS)}; rest 70')

# ---------------- H：help（曲線型，D1） ----------------
MIRROR = [(float(a), -float(y)) for a, y in L.CURVE_DEF_RIM]   # (attr, x)；x = −shrunk
A99 = inverse_open(99, [(y, a) for a, y in MIRROR], -1e9, 1e9)   # 同 E-101：a99 = curve 在 99 的 x
poolsH = {s: poolH(s) for s in SEASONS}
PH = Pool([x for s in SEASONS for x in poolsH[s]])
anH = PH.anchors('max')
sH = K_SD * anH['S']
loH = 0.0 if BOT['help'] else 40.0
h26 = S_('H', CARD)
newH = {}
for p in PIDS:
    e = h26.get(str(p))
    if e is None or not e['n'] > 0:
        newH[p] = cur['help'][p]            # 沒資料者維持現行（70）
        continue
    x = float(e['x'])
    if TOP['help'] and x > A99:
        newH[p] = 99 + (CEIL - 99) * (1 - math.exp(-(x - A99) / sH))
    else:
        newH[p] = inverse_open(x, MIRROR, loH, 99.0)
new['help'] = newH
summary['help'] = dict(type='curve(D1)', topTail=TOP['help'], botTail=BOT['help'], **anH, a99=A99, lo=loH, hi=CEIL if TOP['help'] else 99.0,
                       poolPerSeason={s: len(poolsH[s]) for s in SEASONS})

# ---------------- P：pressure、presDisplay（百分位型，D3 的池） ----------------
p26 = S_('P', CARD)
for key, pool_fn, fld in (('pressure', poolPf, 'force'), ('presDisplay', poolPd, 'disp')):
    pools = {s: pool_fn(s) for s in SEASONS}
    PP = Pool([x for s in SEASONS for x in pools[s]])
    vals = {p: float(p26[str(p)][fld]) for p in PIDS if str(p) in p26}
    mapped, an = percentile_attr_merged(vals, PP, TOP[key], BOT[key], 'max')
    new[key] = {p: mapped.get(p, cur[key][p]) for p in PIDS}
    summary[key] = dict(type='percentile', topTail=TOP[key], botTail=BOT[key], **an, poolPerSeason={s: len(pools[s]) for s in SEASONS},
                        note=f'card players with value {len(vals)}/{len(PIDS)}; rest keep current')
    summary[key]['_pool'] = PP

# 單季池對照（只為檢查程式：用 2025-26 單季池、不開尾巴，應重現現行值）
chk = {}
P26 = Pool(poolPf(CARD))
single, _ = percentile_attr_merged({p: float(p26[str(p)]['force']) for p in PIDS if str(p) in p26}, P26, False, False, 'max')
chk['pressure_single_pool_no_tail_vs_cur_maxdiff'] = max(abs(single[p] - cur['pressure'][p]) for p in single)
Pd26 = Pool(poolPd(CARD))
single_d, _ = percentile_attr_merged({p: float(p26[str(p)]['disp']) for p in PIDS if str(p) in p26}, Pd26, False, False, 'max')
chk['presDisplay_single_pool_no_tail_vs_cur_maxdiff'] = max(abs(single_d[p] - cur['presDisplay'][p]) for p in single_d)
print('check', chk)

# help：範圍內（40..99）的人新值四捨五入後應等於現行 new_help
inrange = [p for p in PIDS if 40 <= new['help'][p] <= 99 and abs(new['help'][p] - cur['help'][p]) > 1e-12]
mism = [(name[p], round(new['help'][p], 1), cur['help'][p]) for p in inrange if round(new['help'][p], 1) != cur['help'][p]]
chk['help_inrange_changed_after_round1'] = len(mism)
chk['help_inrange_mismatch_examples'] = mism[:6]
print('help in-range mismatches after rounding:', len(mism), mism[:6])

# ---------------- 統計、名單 ----------------
for key in ('threeValue', 'help', 'pressure', 'presDisplay'):
    info = summary[key]
    vals = new[key]
    info['count'] = {k: sum(f(v) for v in vals.values()) for k, f in COUNTS}
    info['above99'] = [[name[p], round(vals[p], 2)] for p in sorted(PIDS, key=lambda p: -vals[p]) if vals[p] > 99]
    info['above120'] = [[n, v] for n, v in info['above99'] if v > 120]
    info['above140'] = [[n, v] for n, v in info['above99'] if v > 140]
    info['below40'] = [[name[p], round(vals[p], 2)] for p in sorted(PIDS, key=lambda p: vals[p]) if vals[p] < 40]
    info['exactly99'] = [name[p] for p in PIDS if abs(vals[p] - 99) < 1e-9]
    info['cur_count'] = {k: sum(f(v) for v in cur[key].values()) for k, f in COUNTS}
    info['cur_exactly99'] = [name[p] for p in PIDS if abs(cur[key][p] - 99) < 1e-9]

# 各季到 99 的人數（合併錨點下，該季池內與該季全部有值者）
season99 = {}
for key, part in (('threeValue', 'T'), ('help', 'H'), ('pressure', 'P'), ('presDisplay', 'P')):
    rows = {}
    for s in SEASONS:
        if key == 'threeValue':
            poolv = poolsT[s]; allv = [float(v['value']) for v in S_('T', s).values()]; PL = PT
        elif key == 'help':
            poolv = poolsH[s]; allv = [float(v['x']) for v in S_('H', s).values() if v['n'] > 0]; PL = PH
        else:
            fld = 'force' if key == 'pressure' else 'disp'
            poolv = [float(v[fld]) for v in S_('P', s).values() if v['inPool']]; allv = [float(v[fld]) for v in S_('P', s).values()]; PL = summary[key]['_pool']
        if key == 'help':
            rows[s] = {'pool': sum(v >= A99 for v in poolv), 'poolN': len(poolv), 'all': sum(v >= A99 for v in allv), 'allN': len(allv), 'rule': 'x >= a99'}
        else:
            rows[s] = {'pool': sum(PL.pct(v) >= 99 for v in poolv), 'poolN': len(poolv), 'all': sum(PL.pct(v) >= 99 for v in allv), 'allN': len(allv), 'rule': 'merged pct >= 99'}
    season99[key] = rows
for key in ('pressure', 'presDisplay'):
    summary[key].pop('_pool')

# 指定球員（5.3）
NAMED = {'threeValue': ['Curry', 'Knueppel', 'Murray', 'Isaiah Joe', 'Edwards', 'Kennard', 'Portis'],
         'help': ['Wembanyama', 'Isaiah Stewart', 'Kalkbrenner', 'Holmgren', 'Mobley', 'Gobert'],
         'pressure': ['Thybulle', 'Caruso', 'Dru Smith', 'Cason Wallace', 'Ausar Thompson', 'Diabat', 'Paul Reed'],
         'presDisplay': ['Thybulle', 'Caruso', 'Dru Smith', 'Cason Wallace', 'Ausar Thompson', 'Diabat', 'Paul Reed']}
named = {}
for key, ks in NAMED.items():
    named[key] = {}
    for k in ks:
        named[key][k] = [[name[p], round(cur[key][p], 2), round(new[key][p], 2)] for p in PIDS if k in name[p]]

summaries = {'_rules': {
    'S': 'max((r99 − r90)/1.044, SD_pool)；insuranceActive = SD_pool > (r99 − r90)/1.044',
    'pools': 'T: MIN>=500（D4/D7）；H: MIN>=500 且 n>0，x = −shrunk（D1）；P: GP>=30 且 MPG>=20，2025-26 為卡片池 252 人（D3）；四季合併、每個球員季一筆',
    'switches': 'h1-results.json；presDisplay 兩端跟 pressure（§2.3）',
    'order': 'threeValue 只顯示不進 OVR（R-024）；help、pressure 進卡片鏈；presDisplay 只顯示，由 e123.py cards 階段覆寫進 ranking.csv'},
    'checks': chk, 'e123': summary, '_season99': season99, '_named': named}
(E123 / 'tail-summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=1), encoding='utf-8')

# ---------------- 輸出 csv ----------------
with open(HERE / 'tail-new.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n')
    w.writerow(tail_hdr)
    for r in tail_rows:
        pid = int(r['playerId'])
        w.writerow([repr(float(new['pressure'][pid])) if h == 'pressure' else r[h] for h in tail_hdr])
with open(HERE / 'def-new.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n')
    w.writerow(def_hdr)
    for r in def_rows:
        pid = int(r['playerId'])
        w.writerow([str(round(float(new['help'][pid]), 1)) if h == 'new_help' else r[h] for h in def_hdr])
with open(E123 / 'three-value-e123.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n')
    w.writerow(['playerId', 'name', 'team', 'MIN', 'long', 'vol', 'acc', 'value_main', 'tv_main_cur', 'tv_main_new'])
    for r in tv_rows:
        pid = int(r['playerId'])
        w.writerow([r['playerId'], r['name'], r['team'], r['MIN'], r['long'], r['vol'], r['acc'], r['value_main'], r['tv_main'], repr(float(new['threeValue'][pid]))])
with open(HERE / 'presDisplay-new.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n')
    w.writerow(['playerId', 'name', 'presDisplay_cur', 'presDisplay_new'])
    for p in PIDS:
        w.writerow([p, name[p], cur['presDisplay'][p], repr(float(new['presDisplay'][p]))])

for key in ('threeValue', 'help', 'pressure', 'presDisplay'):
    i = summary[key]
    print('==', key, 'top', i['topTail'], 'bot', i['botTail'], 'poolN', i['poolN'], 'r90', round(i['r90'], 4), 'r99', round(i['r99'], 4), 'ratio', round(i['ratio'], 3),
          'insurance', i['insuranceActive'], 'S', round(i['S'], 4))
    print('   cur', i['cur_count'], i['cur_exactly99'])
    print('   new', i['count'])
    print('   >120', i['above120'], '\n   <40', i['below40'][:8])
print('season99', json.dumps({k: {s: (v['pool'], v['all']) for s, v in d.items()} for k, d in season99.items()}))
