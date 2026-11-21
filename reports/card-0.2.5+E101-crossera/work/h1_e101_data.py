"""E-101 改動一（預註冊 §1）：修正分區＋聯盟先驗後重組 h1（mid、short）與 h1v（midValue、shortValue）的相鄰季配對。不算斜率。
複製自 ../card-0.2.5+E097-topscale/work/h1_league_data.py；改動：
  - cache 參數化：V61 分區（對照）與 E-101 修正分區（engine.read_gz_csv 經 e101_zones 改讀本資料夾 history/）各建一份；
  - 2025-26 的 p：E-101 用本實驗 a0-e101.json；
  - 拿掉「人群必須和 E-090 相同」的 assert（修正分區改變各季 mid／short 出手數，出手門檻 PSEUDO 篩出的人群會變；照舊規則，人數另報）。
人群、出手門檻、配對規則、VAL 公式全照舊。
對照：V61 分區＋位置先驗必須逐位元重現 E-090 h1-pairs.json（mid、short）與 E-096 h1v-pairs.json；
      V61 分區＋聯盟先驗必須逐位元重現 E-097 h1-pairs-league.json 與 E-097 h1v-pairs.json。
輸出：h1-pairs-e101.json（mid、short）、h1v-pairs-e101.json（midValue、shortValue），各附 .sha256；
      work/tmp/zones-seasons-e101.json（四季每人 p、出手 A、命中 M、量價 value，供合併池用）。
用法（repo 根目錄）：python -I -B reports/card-0.2.5+E101-crossera/work/h1_e101_data.py
"""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[1]
R = ROOT / 'reports'
V61 = R / 'ovr-v61-shrink-history-2025-26'
E090 = R / 'card-0.2.4+E090-onball-tail'
E096 = R / 'card-0.2.5+E096-tail150'
E097 = R / 'card-0.2.5+E097-topscale'
sys.path.insert(0, str(V61))
sys.path.insert(0, str(HERE))
import engine as E  # noqa: E402
import build_attrs as B  # noqa: E402
import e101_zones as Z  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEASONS4 = ['2022-23', '2023-24', '2024-25', '2025-26']
PAIRS = [('2022-23', '2023-24'), ('2023-24', '2024-25'), ('2024-25', '2025-26')]
MIN_PAIR, PSEUDO_MIN, REP_GAP = 500, 200.0, 0.03
ZONES = ('mid', 'short')
prod = json.load(open(V61 / 'backtest.json', encoding='utf-8'))['production']
PSEUDO = {z: prod[z]['fit']['k'] for z in ZONES}
A0 = {'position': {z: v['p'] for z, v in json.load(open(E090 / 'work/a0-raw.json', encoding='utf-8')).items() if z in ZONES},
      'league97': json.load(open(E097 / 'a0-league.json', encoding='utf-8'))['league'],
      'e101': json.load(open(OUT / 'a0-e101.json', encoding='utf-8'))['p']}
Z.use(False, E)
CACHE_V61 = {s: E.season_halves(s) for s in E.SEASONS}
Z.use(True, E)
CACHE_E101 = {s: E.season_halves(s) for s in E.SEASONS}
Z.use(False, E)
assert len(Z.reads()) == 4, Z.reads()
pos_by = E.positions()
shots = {r['PLAYER_ID']: r for r in B.bench_rows('shots')}
bb = {r['PLAYER_ID']: r for r in B.bench_rows('base')}


def season_min(s):
    mins = defaultdict(float)
    for r in E.load_pergame(s):
        mins[int(r['playerId'])] += float(r['MIN'])
    return mins


def shrunk(cache, attr, s, pids, fit, n, d, pos):
    """同 E-090 h1_data.shrunk／E-096 h1v_data.shrunk（方法 c）。"""
    ds = E.Dataset(attr, s, cache, pos_by, ids=pids)
    league_rate = n.sum() / d.sum()
    pn, pd_ = defaultdict(float), defaultdict(float)
    for i, p in enumerate(pids):
        pn[pos[p]] += n[i]; pd_[pos[p]] += d[i]
    m = np.full(len(pids), league_rate) if fit['prior'] == 'league' else np.array([pn[pos[p]] / pd_[pos[p]] for p in pids])
    return B.shrink(n, d, m, B.Hist(ds.hn, ds.hd), 'c', fit)


def full_nd(cache, attr, s, pids):
    z = [0.0] * 4
    cur = cache[s][attr]
    return (np.array([cur.get(p, z)[0] + cur.get(p, z)[2] for p in pids], float),
            np.array([cur.get(p, z)[1] + cur.get(p, z)[3] for p in pids], float))


MINS = {s: season_min(s) for s in SEASONS4}


def build(cache, prior, a0):
    P, ATT, VAL, INFO, FULL = {z: {} for z in ZONES}, {z: {} for z in ZONES}, {z: {} for z in ZONES}, {}, {z: {} for z in ZONES}
    for s in SEASONS4:
        mins = MINS[s]
        pids = sorted(p for p in mins if mins[p] > 0)
        pos = {p: E.pos_lookup(pos_by, p, s) for p in pids}
        for z in ZONES:
            assert prod[z]['selected'] == 'c'
            fit = {**prod[z]['fit'], 'prior': prior}
            n, d = full_nd(cache, z, s, pids)
            if s == '2025-26':
                P[z][s] = {int(k): float(v) for k, v in a0[z].items()}
                ATT[z][s] = {p: float(shots[p][z + 'A']) if p in shots else 0.0 for p in bb}
            else:
                rn = shrunk(cache, z, s, pids, fit, n, d, pos)
                P[z][s] = {p: float(rn[i]) for i, p in enumerate(pids)}
                ATT[z][s] = {p: float(d[i]) for i, p in enumerate(pids)}
            mn = np.array([mins[p] for p in pids])
            mu = d.sum() / mn.sum()
            rep = n.sum() / d.sum() - REP_GAP
            VAL[z][s] = {p: 36 * (d[i] + PSEUDO_MIN * mu) / (mins[p] + PSEUDO_MIN) * (P[z][s][p] - rep)
                         for i, p in enumerate(pids) if p in P[z][s]}
            FULL[z][s] = {p: {'p': P[z][s][p], 'A': float(d[i]), 'M': float(n[i]), 'MIN': float(mins[p]), 'value': VAL[z][s][p]}
                          for i, p in enumerate(pids) if p in P[z][s]}
            INFO[f'{z} {s}'] = {'players': len(VAL[z][s]), 'muPerMin': float(mu), 'leagueRate': float(n.sum() / d.sum()), 'rep': float(rep)}
    h1, h1v, per = {}, {}, {}
    for z in ZONES:
        rows, rowsv = [], []
        for s0, s1 in PAIRS:
            r0, r1 = P[z][s0], P[z][s1]
            ok = [p for p in r0 if p in r1 and MINS[s0].get(p, 0) >= MIN_PAIR and MINS[s1].get(p, 0) >= MIN_PAIR]
            ok = [p for p in ok if ATT[z][s0].get(p, 0) >= PSEUDO[z] and ATT[z][s1].get(p, 0) >= PSEUDO[z]]
            rows += [{'pid': p, 'pair': f'{s0}→{s1}', 'prev': r0[p], 'next': r1[p]} for p in sorted(ok)]
            v0, v1 = VAL[z][s0], VAL[z][s1]
            okv = [p for p in v0 if p in v1 and MINS[s0].get(p, 0) >= MIN_PAIR and MINS[s1].get(p, 0) >= MIN_PAIR]
            per[f'{z} {s0}→{s1}'] = len(okv)
            rowsv += [{'pid': p, 'pair': f'{s0}→{s1}', 'prev': v0[p], 'next': v1[p]} for p in sorted(okv)]
        h1[z] = rows
        h1v[z + 'Value'] = rowsv
    return h1, h1v, per, INFO, FULL


# 對照 1：V61 分區＋位置先驗重現 E-090／E-096
h1c, h1vc, _, _, _ = build(CACHE_V61, 'position', A0['position'])
ref1 = json.load(open(E090 / 'work/h1-pairs.json', encoding='utf-8'))
refv = json.load(open(E096 / 'h1v-pairs.json', encoding='utf-8'))['pairs']
for z in ZONES:
    assert h1c[z] == ref1[z], z
    assert h1vc[z + 'Value'] == refv[z + 'Value'], z
# 對照 2：V61 分區＋聯盟先驗重現 E-097
h1c2, h1vc2, _, _, _ = build(CACHE_V61, 'league', A0['league97'])
ref97 = json.load(open(E097 / 'h1-pairs-league.json', encoding='utf-8'))['pairs']
ref97v = json.load(open(E097 / 'h1v-pairs.json', encoding='utf-8'))['pairs']
for z in ZONES:
    assert h1c2[z] == ref97[z], z
    assert h1vc2[z + 'Value'] == ref97v[z + 'Value'], z
print('control: V61 zones reproduce E-090/E-096 (position) and E-097 (league) pairs exactly')

h1, h1v, per, info, full = build(CACHE_E101, 'league', A0['e101'])
popchg = {}
for z in ZONES:
    a = {(r['pid'], r['pair']) for r in h1[z]}
    b = {(r['pid'], r['pair']) for r in ref1[z]}
    av = {(r['pid'], r['pair']) for r in h1v[z + 'Value']}
    bv = {(r['pid'], r['pair']) for r in refv[z + 'Value']}
    popchg[z] = {'nE101': len(a), 'nE090': len(b), 'added': len(a - b), 'dropped': len(b - a)}
    popchg[z + 'Value'] = {'nE101': len(av), 'nE096': len(bv), 'added': len(av - bv), 'dropped': len(bv - av)}
rules = {'zones': '本資料夾 history/pbp-zones-<季>.csv.gz（Mid-Range 且 shotDistance<8 → short）',
         'prior': "mid、short 方法 c 收縮的先驗 m = 該季聯盟平均（fit['prior']='league'），k／kh／lam 照 V61 production",
         'h1': '人群、出手門檻、tails／OLS／bootstrap 同 E-090 h1-sources.json _rules', 'h1v': '同 E-096 h1v-pairs.json rules',
         'populationChangeVsE090E096': popchg}
for name, obj in (('h1-pairs-e101.json', {'pairs': h1, 'rules': rules}),
                  ('h1v-pairs-e101.json', {'pairs': h1v, 'perPair': per, 'seasons': info, 'rules': rules})):
    p = OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / name.replace('.json', '.sha256')).write_text(hashlib.sha256(p.read_bytes()).hexdigest() + f'  {name}\n', encoding='utf-8')
(HERE / 'tmp' / 'zones-seasons-e101.json').write_text(
    json.dumps({z: {s: {str(k): v for k, v in full[z][s].items()} for s in SEASONS4} for z in ZONES}), encoding='utf-8')
print(json.dumps({'perPair': per, 'nH1': {z: len(h1[z]) for z in ZONES}, 'population': popchg, 'info': info}, ensure_ascii=False))
