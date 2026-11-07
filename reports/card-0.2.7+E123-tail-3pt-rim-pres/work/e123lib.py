"""E-123 共用函式（只讀既有資料；輸出只寫在 E-123 資料夾）。"""
import csv, json, math, sys, hashlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
E123 = HERE.parent
ROOT = E123.parents[1]
DATA = E123 / 'data'
V62 = ROOT / 'reports/ovr-v62-3pt-difficulty-2025-26'
sys.path.insert(0, str(V62))
import fit_3pt_difficulty as F   # noqa: E402
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
K_T = 294.667   # 凍結（預註冊 §2.1）
PICK_KIND = 'type'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct_js(x, a):
    return 100 * (sum(v < x for v in a) + .5 * sum(v == x for v in a)) / (len(a) or 1)


def attr_of(p):
    return max(40, min(99, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def raw_dir(season):
    return DATA if season == '2022-23' else V62 / 'raw'


def base_path(season):
    if season in ('2022-23', '2023-24'):
        return DATA / f'{season}-base.json'
    return ROOT / f'reports/card-0.2.0+E071-pressure/data/{season}-base.json'


def base_rows(season):
    rs = json.loads(base_path(season).read_text(encoding='utf-8'))['data']['resultSets'][0]
    return [dict(zip(rs['headers'], r)) for r in rs['rowSet']]


def t_season(season):
    """-> dict pid(int) -> dict(vol, acc, value, mu, N); 以該季 full 資料。"""
    F.RAW = raw_dir(season)
    full = F.Ds(F.load(season, 'full'))
    fr = full.rates()
    acc = full.mu + (full.M - full.expected(fr, PICK_KIND)) / (full.N + K_T)
    vol = full.feat('r36')
    mu = float(full.mu)
    rep = mu - 0.03
    rows = base_rows(season)
    prior = sum(r['FG3M'] for r in rows) / sum(r['FG3A'] for r in rows)   # D8
    out = {}
    for n, i in enumerate(full.ids):
        a = float(acc[n]) if full.N[n] > 0 else prior
        out[int(i)] = dict(name=full.names[n], vol=float(vol[n]), acc=a, value=float(vol[n] * (a - rep)), mu=mu, N=float(full.N[n]), MINtracking=float(full.MIN[n]))
    return out


# ------------------------------------------------------------------ P (pressure / presDisplay)
import importlib.util
_spec = importlib.util.spec_from_file_location('bf071', ROOT / 'reports/card-0.2.0+E071-pressure/build_force.py')
BF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BF)      # 只載入函式；不呼叫 main()
DT = ROOT / 'reports/defense-tenth/step4-t2/raw'


def _table(season, kind):
    if kind == 'base':
        p = base_path(season)
    elif season in ('2022-23', '2023-24'):
        p = DT / season / f'0-{kind}.json'
    else:
        p = ROOT / f'reports/card-0.2.0+E071-pressure/data/{season}-{kind}.json'
    rs = json.loads(p.read_text(encoding='utf-8'))['data']['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    return [dict(zip(rs['headers'], r)) for r in rs['rowSet']]


BF.table = _table
KS = json.loads((ROOT / 'reports/card-0.2.0+E071-pressure/shrink.json').read_text(encoding='utf-8'))['k']
LEAGUE_E2 = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'


def card_pool26():
    league = json.loads(LEAGUE_E2.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            c = cards.setdefault(p['playerId'], {'name': p['name'], 'GP': 0, 'MIN': 0.0})
            c['GP'] += p['observed']['GP']; c['MIN'] += p['observed']['MIN']
    return cards, {pid for pid, c in cards.items() if c['GP'] >= 30 and c['MIN'] / c['GP'] >= 20}


def p_season(season, use_card_pool=False):
    """-> dict pid -> dict(force, negzpf, pres, presDisplay, disp(raw), inPool, MIN, GP)。
    池：該季 GP>=30 且 MPG>=20（D3）；use_card_pool=True 時用卡片池（2025-26，a0P 重現）。"""
    raw, mt, L_ = BF.season_raw(season)
    comps = BF.comps_of(raw, mt)
    if use_card_pool:
        cards, pool = card_pool26()
        for pid in cards:
            if pid not in raw:
                raw[pid] = {'name': cards[pid]['name'], 'MIN': 0.0, 'GP': 0}
                comps[pid] = {c: (0.0, 0.0) for c in BF.COMPS}
    else:
        pool = {pid for pid, r in raw.items() if r['GP'] >= 30 and r['MIN'] / r['GP'] >= 20}
    shr, z, f, st = BF.force_table(comps, raw, pool, KS)
    pl = sorted(pool)
    pool_f = [f[p] for p in pl]
    pool_nz = [-z[p]['pf'] for p in pl]
    pool_d = [f[p] - 0.25 * z[p]['pf'] for p in pl]
    out = {}
    for pid in raw:
        d = f[pid] - 0.25 * z[pid]['pf']
        out[int(pid)] = dict(name=raw[pid]['name'], force=f[pid], negzpf=-z[pid]['pf'], disp=d, MIN=raw[pid]['MIN'], GP=raw[pid]['GP'], inPool=pid in pool,
                             pressure=BF.to_attribute(f[pid], pool_f), presDisplay=BF.to_attribute(d, pool_d))
    return out


# ------------------------------------------------------------------ H (help / RIM)
CURVE_DEF_RIM = [[0, .150], [40, .105], [55, .050], [70, .004], [85, -.048], [99, -.095], [120, -.125], [150, -.150]]
K_H = 200.0


def rim_path(season):
    if season == '2025-26':
        return ROOT / 'data/benchmark-source/defense-rim.json'
    return DT / season / '0-rim.json'


def inverse_h(p, curve=CURVE_DEF_RIM):
    for (a, b), (c, d) in zip(curve, curve[1:]):
        if min(b, d) <= p <= max(b, d):
            return max(40.0, min(99.0, a + (p - b) / (d - b) * (c - a)))
    return 40.0 if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else 99.0


def h_season(season):
    """-> pid -> dict(n, d, shrunk, x(=-shrunk), help(card-style 40..99), name)"""
    rs = json.loads(rim_path(season).read_text(encoding='utf-8'))['data']['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    acc = {}
    for row in rs['rowSet']:
        r = dict(zip(rs['headers'], row))
        n = r['FGA_LT_06']; pm = r['PLUSMINUS']
        if not n or pm is None: continue
        a = acc.setdefault(int(r['CLOSE_DEF_PERSON_ID']), dict(name=r['PLAYER_NAME'], n=0.0, s=0.0))
        a['n'] += n; a['s'] += pm * n
    out = {}
    for pid, a in acc.items():
        d = a['s'] / a['n']; sh = d * a['n'] / (a['n'] + K_H)
        out[pid] = dict(name=a['name'], n=a['n'], d=d, shrunk=sh, x=-sh, help=inverse_h(sh))
    return out
