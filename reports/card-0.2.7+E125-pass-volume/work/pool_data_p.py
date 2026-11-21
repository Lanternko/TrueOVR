"""E-101 改動二（預註冊 §2）：逐季算全部名單的原始值，存 pool/raw-<季>.json，供跨季合併池用。
逐季程式複製自 ../card-0.2.4+E090-onball-tail/work/h1_data.py（v61_season、seventh_season、onball_season、season_min_gp、shrunk、full_nd），改動：
  - v61_season 不算 mid、short（mid、short 改用 h1_e101_data.py 的修正分區＋聯盟先驗 p，work/tmp/zones-seasons-e101.json）；
  - drive 只在 V61 DRIVE_SEASONS（2020-21 起）算；creation 只在 dependence-audit 有的季（2022-23 起）；onBall 只在 E-060 components 有的季（2022-23 起）；
  - 輸出全部名單，不只是配對。
季別：主版本 2022-23..2024-25（2025-26 用卡片本身的值，不在這裡）；e101w 長窗另算 2015-16..2021-22（只算 long、ft、foulDraw、tovSkill、pass、rebound、physique、drive(2020-21 起)）。
每人另存池門檻需要的 MIN、GP（V61 pergame，GP = MIN>0 的場數，同 h1_data.season_min_gp）、MIN41、GP41（前 41 場，half==1）。
對照：2022-23..2024-25 的值必須逐位元等於 E-090 work/h1-pairs.json 裡同一人同一季的 prev／next（mid、short 除外）。
用法（repo 根目錄）：python -I -B reports/card-0.2.5+E101-crossera/work/pool_data.py
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[1]
# E-125 唯一新增選項：w_vol（argv[1]，預設 0）。pass 每季值 = w_vol*zs(vol)+(1-w_vol)*zs(rate)；w_vol=0 直接用原 rate，不做 zs。
W_VOL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
TAG = 'P%d' % round(W_VOL * 100)
E101 = ROOT / 'reports/card-0.2.5+E101-crossera'
ASTFIT = json.load(open(OUT / 'astvol-fit.json', encoding='utf-8'))['fit']
R = ROOT / 'reports'
V61 = R / 'ovr-v61-shrink-history-2025-26'
E090 = R / 'card-0.2.4+E090-onball-tail'
sys.path.insert(0, str(V61))
import engine as E  # noqa: E402
import build_attrs as B  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
MAIN = ['2022-23', '2023-24', '2024-25']
LONG = ['2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22']
LONG_ATTRS = ['long', 'ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'drive']
prod = json.load(open(V61 / 'backtest.json', encoding='utf-8'))['production']
volfit = json.load(open(E090 / 'work/tmp/e070/vol-fit.json', encoding='utf-8'))['fit']


def jrs(path):
    d = json.load(open(path, encoding='utf-8'))
    rs = d['data']['resultSets'] if 'data' in d else d['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    return [dict(zip(rs['headers'], r)) for r in rs['rowSet']]


# ---------------------------------------------------------------- V61 歷史快取（同 E-090 h1_data）
cache = {s: E.season_halves(s) for s in E.SEASONS}
E.ATTR_SEASONS['vol'] = list(E.SEASONS)
E.MIN_D2['vol'] = 300 / 36
E.ATTR_SEASONS['astvol'] = list(E.SEASONS)
E.MIN_D2['astvol'] = 300 / 36
for s in E.SEASONS:
    acc = E._acc()
    for r in E.load_pergame(s):
        i = 0 if int(r['half']) == 1 else 2
        pid = int(r['playerId'])
        acc[pid][i] += float(r['FTA'])
        acc[pid][i + 1] += float(r['MIN']) / 36
    cache[s]['vol'] = acc
    acc2 = E._acc()
    for r in E.load_pergame(s):
        i = 0 if int(r['half']) == 1 else 2
        pid = int(r['playerId'])
        acc2[pid][i] += float(r['AST'])
        acc2[pid][i + 1] += float(r['MIN']) / 36
    cache[s]['astvol'] = acc2
pos_by = E.positions()


def season_min_gp(s, half1=False):
    mins, gp = defaultdict(float), defaultdict(int)
    for r in E.load_pergame(s):
        if half1 and r['half'] != '1':
            continue
        m = float(r['MIN'])
        pid = int(r['playerId'])
        mins[pid] += m
        gp[pid] += m > 0
    return mins, gp


def shrunk(attr, s, pids, fit, n, d, pos, method='c'):
    ds = E.Dataset(attr, s, cache, pos_by, ids=pids)
    league_rate = n.sum() / d.sum()
    pn, pd_ = defaultdict(float), defaultdict(float)
    for i, p in enumerate(pids):
        pn[pos[p]] += n[i]; pd_[pos[p]] += d[i]
    m = np.full(len(pids), league_rate) if fit['prior'] == 'league' else np.array([pn[pos[p]] / pd_[pos[p]] for p in pids])
    return B.shrink(n, d, m, B.Hist(ds.hn, ds.hd), method, fit)


def full_nd(attr, s, pids):
    z = [0.0] * 4
    cur = cache[s][attr]
    return (np.array([cur.get(p, z)[0] + cur.get(p, z)[2] for p in pids], float),
            np.array([cur.get(p, z)[1] + cur.get(p, z)[3] for p in pids], float))


def v61_season(s, method='c'):
    """同 E-090 h1_data.v61_season，但不算 mid、short；drive 只在有 PBP drive 的季。"""
    mins, gp = season_min_gp(s)
    pids = sorted(p for p in mins if mins[p] > 0)
    pos = {p: E.pos_lookup(pos_by, p, s) for p in pids}
    out, att = {}, {}
    for a in ('ft', 'tovSkill', 'pass', 'rebound', 'foulDraw'):
        assert prod[a]['selected'] == 'c'
        n, d = full_nd(a, s, pids)
        rn = shrunk(a, s, pids, prod[a]['fit'], n, d, pos, method)
        sign = -1.0 if a == 'tovSkill' else 1.0
        out[a] = {p: sign * float(rn[i]) for i, p in enumerate(pids)}
        if a == 'ft':
            att[a] = {p: float(d[i]) for i, p in enumerate(pids)}
    # foulDraw w075
    n, d = full_nd('vol', s, pids)
    vol = shrunk('vol', s, pids, volfit, n, d, pos, method)
    rate = np.array([out['foulDraw'][p] for p in pids])
    inp = np.array([gp[p] >= B.POOL[0] and mins[p] / gp[p] >= B.POOL[1] for p in pids])
    zs = lambda x: (x - x[inp].mean()) / x[inp].std()
    comp = 0.75 * zs(vol) + 0.25 * zs(rate)
    out['foulDraw'] = {p: float(comp[i]) for i, p in enumerate(pids)}
    # pass w_vol（E-125；w_vol=0 保留原 rate 值，不做 zs）
    if W_VOL > 0:
        n, d = full_nd('astvol', s, pids)
        avol = shrunk('astvol', s, pids, ASTFIT, n, d, pos, method)
        prate = np.array([out['pass'][p] for p in pids])
        pcomp = W_VOL * zs(avol) + (1 - W_VOL) * zs(prate)
        out['pass'] = {p: float(pcomp[i]) for i, p in enumerate(pids)}
    # drive（前 41 場）
    if s in E.DRIVE_SEASONS:
        dv, de = cache[s]['driveVol'], cache[s]['driveEff']
        z4 = [0.0] * 4
        mins41 = np.array([dv.get(p, z4)[1] for p in pids], float)
        nv = np.array([dv.get(p, z4)[0] for p in pids], float)
        pts = np.array([de.get(p, z4)[0] for p in pids], float)
        nW = np.array([de.get(p, z4)[1] for p in pids], float)
        _, gp41 = season_min_gp(s, half1=True)
        g = np.array([gp41.get(p, 0) for p in pids], float)
        inpool = (g >= B.POOL41[0]) & (mins41 / np.where(g > 0, g, 1) >= B.POOL41[1])
        comp = prod['drive']['components']
        rv = 36 * shrunk('driveVol', s, pids, comp['driveVol']['c'], nv, mins41, pos, method)
        re_ = shrunk('driveEff', s, pids, comp['driveEff']['c'], pts, nW, pos, method)
        sc = .5 * (rv - rv[inpool].mean()) / rv[inpool].std() + .5 * (re_ - re_[inpool].mean()) / re_[inpool].std()
        out['drive'] = {p: float(sc[i]) for i, p in enumerate(pids) if mins41[i] > 0}
    return out, att


DEP = json.load(open(R / 'player-impact-v30/dependence-audit.json', encoding='utf-8'))


def seventh_season(s):
    pg = jrs(ROOT / f'data/defense-seventh/{s}/player-games.json')
    tot = defaultdict(lambda: defaultdict(float))
    for r in pg:
        t = tot[int(r['PLAYER_ID'])]
        for k in ('FG3M', 'FG3A', 'FGA', 'MIN'):
            t[k] += float(r[k] or 0)
    lg = sum(t['FG3M'] for t in tot.values()) / sum(t['FG3A'] for t in tot.values())
    out = {'long': {p: (t['FG3M'] + 100 * lg) / (t['FG3A'] + 100) for p, t in tot.items()}}
    att = {'long': {p: t['FG3A'] for p, t in tot.items()}}
    bio = jrs(ROOT / f'data/defense-seventh/{s}/bio.json')
    out['physique'] = {int(b['PLAYER_ID']): float(b['PLAYER_HEIGHT_INCHES']) + float(b['PLAYER_WEIGHT']) / 10
                       for b in bio if b['PLAYER_HEIGHT_INCHES'] and float(b['PLAYER_WEIGHT'] or 0) > 0}
    dep = {int(r['playerId']): r['sourceDependence'] for se in DEP['seasons'] if se['season'] == s for r in se['rows']}
    if dep:
        out['creation'] = {p: (1 - float(dep[p])) * t['FGA'] / max(t['MIN'], 1) * 36 for p, t in tot.items() if dep.get(p) is not None}
    return out, att


E060 = R / 'card-0.1.1+E060-onball-targeting'
USE_T = json.load(open(E060 / 'stability.json', encoding='utf-8'))['T_included']


def onball_season(s):
    out = {}
    for r in csv.DictReader(open(E060 / f'components-{s}.csv', encoding='utf-8')):
        try:
            if USE_T and r['zT'] == '':
                continue
            out[int(r['pid'])] = float(r['zC3']) + float(r['zB']) - (float(r['zT']) if USE_T else 0.0)
        except ValueError:
            continue
    return out


zones = json.load(open(HERE / 'tmp/zones-seasons-e101.json', encoding='utf-8'))
ref = json.load(open(E090 / 'work/h1-pairs.json', encoding='utf-8'))
(OUT / ('pool-' + TAG)).mkdir(exist_ok=True)
control = {}
manifest = {}
for s in LONG + MAIN:
    o1, t1 = v61_season(s)
    o2, t2 = seventh_season(s)
    attrs = {**o1, **o2}
    att = {**t1, **t2}
    if s in MAIN:
        attrs['onBall'] = onball_season(s)
        for z in ('mid', 'short'):
            attrs[z] = {int(k): v['p'] for k, v in zones[z][s].items()}
            att[z] = {int(k): v['A'] for k, v in zones[z][s].items()}
    else:
        attrs = {a: v for a, v in attrs.items() if a in LONG_ATTRS}
    mins, gp = season_min_gp(s)
    mins41, gp41 = season_min_gp(s, half1=True)
    allp = sorted(set(mins) | set().union(*[set(v) for v in attrs.values()]))
    rec = {
        'season': s,
        'window': 'main' if s in MAIN else 'e101w-only',
        'attrs': {a: {str(p): v for p, v in sorted(attrs[a].items())} for a in sorted(attrs)},
        'attempts': {a: {str(p): v for p, v in sorted(att[a].items())} for a in sorted(att)},
        'value': ({z + 'Value': {k: {'p': v['p'], 'A': v['A'], 'M': v['M'], 'MIN': v['MIN'], 'value': v['value']} for k, v in zones[z][s].items()}
                   for z in ('mid', 'short')} if s in MAIN else {}),
        'poolInfo': {str(p): {'MIN': mins.get(p, 0.0), 'GP': gp.get(p, 0), 'MIN41': mins41.get(p, 0.0), 'GP41': gp41.get(p, 0)} for p in allp},
        'rules': {'pool': f'GP >= {B.POOL[0]} 且 MIN/GP >= {B.POOL[1]}（drive：GP41 >= {B.POOL41[0]} 且 MIN41/GP41 >= {B.POOL41[1]}）；命中率型與量價型 MIN >= 500',
                  'directions': '百分位型越大越好（tovSkill 已取負號）；曲線型 = 收縮後命中率 p；mid、short = 修正分區＋聯盟先驗',
                  'source': 'work/pool_data.py（複製自 E-090 work/h1_data.py）'},
    }
    if s in MAIN:   # 對照：同一人同一季的值必須等於 E-090 配對裡的 prev／next
        nchk, bad = 0, []
        for a, rows in ref.items():
            if a in ('mid', 'short') or (a == 'pass' and W_VOL > 0):   # 新 pass 值本來就不等於 E-090 配對裡的舊值
                continue
            for r in rows:
                s0, s1 = r['pair'][:7], r['pair'][-7:]
                for ss, key in ((s0, 'prev'), (s1, 'next')):
                    if ss == s:
                        nchk += 1
                        if attrs[a].get(r['pid']) != r[key]:
                            bad.append([a, r['pid'], key])
        control[s] = {'checked': nchk, 'mismatch': len(bad), 'examples': bad[:5]}
        assert not bad, (s, bad[:5])
    p = OUT / ('pool-' + TAG) / f'raw-{s}.json'
    p.write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
    manifest[p.name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'attrs': {a: len(v) for a, v in rec['attrs'].items()}}
    print(s, manifest[p.name]['attrs'], flush=True)
(OUT / ('pool-' + TAG) / 'manifest.json').write_text(json.dumps({'files': manifest, 'controlVsE090Pairs': control}, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(control))
