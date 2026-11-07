"""E-069 第一階段（role-card）：r_sec／passSec 擬合與 h1、h2、h3 判定，產生 handle.csv、results.json、report.md。
用法（repo 根目錄）：python reports/handle-E069/handle_e069.py
定義與閘門照 preregistration.md §2、§3 與補充 1，數字看過後不改。無子程序。
"""
import copy
import csv
import gzip
import hashlib
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
sys.path.insert(0, str(V61))
import engine as E  # noqa
from build_attrs import Hist, attr_of, pct, rank_attr, shrink  # noqa

FIT = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25']
TEST = '2025-26'
ALLS = FIT + [TEST]
POOL = (30, 20)
G5 = ['Doncic', 'Gilgeous-Alexander', 'Brunson', 'Haliburton', 'Jokic', 'Derrick White', 'Hauser', 'Gobert', 'Caruso', 'Westbrook', 'Pritchard', 'McCain']
ATTRS = {'rsec': 20, 'passSec': 150}          # 下半季分母下限（預註冊 §3.2：持球分鐘 ≥20、傳球數 ≥150）
for a in ATTRS:
    E.ATTR_SEASONS[a] = list(ALLS)
E.MIN_D2['rsec'] = 20
E.MIN_D2['passSec'] = 150     # d2 = 傳球數＋失誤 ≥ 150 是傳球數 ≥ 150 的必要條件；之後再用傳球數過濾

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    for t in ('.', ',', "'", '-'):
        s = s.replace(t, ' ')
    w = [x for x in s.split() if x not in ('jr', 'sr', 'ii', 'iii', 'iv')]
    return ' '.join(w)


def trk(season, measure, seg):
    d = json.loads((HERE / 'raw' / season / f'{measure}-{seg}.json').read_text(encoding='utf-8'))['data']
    rs = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
    return {r[0]: dict(zip(rs['headers'], r)) for r in rs['rowSet']}


def load_pbp(season):
    halves = json.loads((HERE / 'game-halves.json').read_text(encoding='utf-8'))[season]
    out = defaultdict(lambda: [[0, 0], [0, 0]])   # pid -> [[ctl_h1, ctl_h2],[pass_h1, pass_h2]]
    miss = 0
    with gzip.open(HERE / f'pbp-tov-{season}.csv.gz', 'rt', encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            h = halves.get(r['gameId'])
            if h is None:
                miss += 1
                continue
            i = int(h[0]) - 1
            pid = int(r['playerId'])
            out[pid][0][i] += int(r['ctl'])
            out[pid][1][i] += int(r['pass'])
    return out, miss


def build_cache():
    cache, info = {}, {}
    for s in ALLS:
        pbp, miss = load_pbp(s)
        pos = {h: trk(s, 'Possessions', h) for h in ('H1', 'H2')}
        pas = {h: trk(s, 'Passing', h) for h in ('H1', 'H2')}
        rsec, psec = {}, {}
        for pid in set(pos['H1']) | set(pos['H2']):
            c = pbp.get(pid, [[0, 0], [0, 0]])[0]
            rsec[pid] = [c[0], pos['H1'].get(pid, {}).get('TIME_OF_POSS', 0.0), c[1], pos['H2'].get(pid, {}).get('TIME_OF_POSS', 0.0)]
        for pid in set(pas['H1']) | set(pas['H2']):
            p = pbp.get(pid, [[0, 0], [0, 0]])[1]
            q1, q2 = pas['H1'].get(pid, {}).get('PASSES_MADE', 0), pas['H2'].get(pid, {}).get('PASSES_MADE', 0)
            psec[pid] = [p[0], q1 + p[0], p[1], q2 + p[1]]
        tracked = set(rsec) | set(psec)
        dropped = {'ctl': sum(v[0][0] + v[0][1] for k, v in pbp.items() if k not in tracked),
                   'pass': sum(v[1][0] + v[1][1] for k, v in pbp.items() if k not in tracked)}
        cache[s] = {'rsec': rsec, 'passSec': psec, '_half_of': {}}
        info[s] = {'pbpGamesNotInHalves': miss, 'pbpTovNotInTracking': dropped,
                   'leagueCtl': sum(v[0] + v[2] for v in rsec.values()), 'leagueTOF': sum(v[1] + v[3] for v in rsec.values()),
                   'leaguePassTov': sum(v[0] + v[2] for v in psec.values()), 'leaguePassDen': sum(v[1] + v[3] for v in psec.values())}
    return cache, info


def subset(ds, mask):
    o = copy.copy(ds)
    for f in ('n1', 'd1', 'n2', 'd2', 'target', 'm_league', 'm_pos'):
        setattr(o, f, getattr(ds, f)[mask])
    o.hn, o.hd = ds.hn[:, mask], ds.hd[:, mask]
    o.pids = [p for p, k in zip(ds.pids, mask) if k]
    return o


def dataset(attr, season, cache, pos_by):
    ds = E.Dataset(attr, season, cache, pos_by)
    if attr == 'passSec':
        ds = subset(ds, (ds.d2 - ds.n2) >= 150)     # 下半季傳球數 ≥150
    return ds


def fit(attr, cache, pos_by):
    ds = E.stack([dataset(attr, s, cache, pos_by) for s in FIT])
    b = {p: E.fit_b(ds, p) for p in ('league', 'position')}
    c = {p: E.fit_c(ds, p) for p in ('league', 'position')}
    fb = min(b.values(), key=lambda f: f['trainMae'])
    fc = min(c.values(), key=lambda f: f['trainMae'])
    ta = E.mae(E.pred_a(ds, ds.m_league), ds.target)
    cands = [('a', ta, {}), ('b', fb['trainMae'], fb), ('c', fc['trainMae'], fc)]
    sel = cands[0]
    for x in cands[1:]:
        if x[1] < sel[1] - 1e-15:
            sel = x
    return {'trainN': int(len(ds.target)), 'trainMae': {'a': ta, 'b': fb['trainMae'], 'c': fc['trainMae']},
            'b': fb, 'c': fc, 'bAll': b, 'cAll': c, 'selected': sel[0], 'params': sel[2]}


def boot(diff):
    rng = np.random.default_rng(1)
    n = len(diff)
    idx = rng.integers(0, n, size=(2000, n))
    m = diff[idx].mean(1)
    return float(np.percentile(m, 5)), float(np.percentile(m, 95))


def test(attr, fitres, cache, pos_by):
    ds = dataset(attr, TEST, cache, pos_by)
    y = ds.target
    preds = {'a': E.predict(ds, 'a', {}), 'b': E.predict(ds, 'b', fitres['b']), 'c': E.predict(ds, 'c', fitres['c'])}
    sel = fitres['selected']
    maes = {k: E.mae(v, y) for k, v in preds.items()}
    diff = np.abs(preds[sel] - y) - np.abs(preds['a'] - y)
    lo, hi = boot(diff)
    return {'n': int(len(y)), 'mae': maes, 'selected': sel, 'diffSelMinusA': float(diff.mean()), 'ci90': [lo, hi],
            'pass': bool(hi < 0),
            'infoOnly': {k: {'diffMinusA': float((np.abs(preds[k] - y) - np.abs(preds['a'] - y)).mean()),
                             'ci90': list(boot(np.abs(preds[k] - y) - np.abs(preds['a'] - y)))} for k in ('b', 'c')}}


def main():
    cache, cinfo = build_cache()
    pos_by = E.positions()
    # ---- h3 基準：card 0.2.0 檔案 sha256（前）----
    card_files = [ROOT / 'reports/card-0.2.0/ranking.csv', ROOT / 'reports/card-0.2.0/summary.json']
    sha_before = {p.name: sha(p) for p in card_files}

    fits = {a: fit(a, cache, pos_by) for a in ATTRS}
    tests = {a: test(a, fits[a], cache, pos_by) for a in ATTRS}
    used = {a: (fits[a]['selected'] if tests[a]['pass'] else 'a') for a in ATTRS}

    # ---- 卡片球員與池 ----
    league = json.loads(E.LEAGUE.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            cards.setdefault(p['playerId'], p)
    pids = sorted(cards, key=lambda p: (cards[p]['name'], p))
    pos_card = {p: cards[p]['pos'] for p in pids}
    bdoc = json.loads((E.BENCH / 'base.json').read_text(encoding='utf-8'))['data']['resultSets']
    bdoc = bdoc[0] if isinstance(bdoc, list) else bdoc
    base = [dict(zip(bdoc['headers'], r)) for r in bdoc['rowSet']]
    pool_ids = {r['PLAYER_ID'] for r in base if r['GP'] >= POOL[0] and r['MIN'] / r['GP'] >= POOL[1]}
    inpool = np.array([p in pool_ids for p in pids])

    # ---- 2025-26 全季 n、d ----
    pbp_full, _ = load_pbp(TEST)
    posF, pasF = trk(TEST, 'Possessions', 'FULL'), trk(TEST, 'Passing', 'FULL')
    chk = {'maxAbsTOF_H1plusH2_minus_FULL': max(abs(cache[TEST]['rsec'].get(p, [0, 0, 0, 0])[1] + cache[TEST]['rsec'].get(p, [0, 0, 0, 0])[3] - posF[p]['TIME_OF_POSS']) for p in posF),
           'maxAbsPasses_H1plusH2_minus_FULL': max(abs(cache[TEST]['passSec'].get(p, [0, 0, 0, 0])[1] + cache[TEST]['passSec'].get(p, [0, 0, 0, 0])[3]
                                                      - cache[TEST]['passSec'].get(p, [0, 0, 0, 0])[0] - cache[TEST]['passSec'].get(p, [0, 0, 0, 0])[2] - pasF[p]['PASSES_MADE']) for p in pasF)}
    ctl = np.array([sum(pbp_full.get(p, [[0, 0], [0, 0]])[0]) for p in pids], float)
    ptv = np.array([sum(pbp_full.get(p, [[0, 0], [0, 0]])[1]) for p in pids], float)
    tof = np.array([posF.get(p, {}).get('TIME_OF_POSS', 0.0) for p in pids], float)
    mins = np.array([posF.get(p, {}).get('MIN', 0.0) for p in pids], float)
    passes = np.array([pasF.get(p, {}).get('PASSES_MADE', 0.0) for p in pids], float)
    dpass = passes + ptv
    missing_trk = [cards[p]['name'] for p in pids if p not in posF]

    def prod(attr, n, d):
        ds = E.Dataset(attr, TEST, cache, pos_by, ids=pids)
        lr = n.sum() / d.sum()
        pn, pd_ = defaultdict(float), defaultdict(float)
        for i, p in enumerate(pids):
            pn[pos_card[p]] += n[i]; pd_[pos_card[p]] += d[i]
        m_pos = np.array([pn[pos_card[p]] / pd_[pos_card[p]] for p in pids])
        sel = fits[attr]['selected']
        fp = fits[attr]['params']
        m = np.full(len(pids), lr) if fp.get('prior', 'league') == 'league' else m_pos
        raw = np.where(d > 0, n / np.where(d > 0, d, 1), lr)
        shr = raw if sel == 'a' else shrink(n, d, m, Hist(ds.hn, ds.hd), sel, fp)
        return raw, shr, (shr if used[attr] == sel else raw)

    r_raw, r_shr, r_use = prod('rsec', ctl, tof)
    p_raw, p_shr, p_use = prod('passSec', ptv, dpass)
    vol = np.where(mins > 0, tof / np.where(mins > 0, mins, 1) * 36, 0.0)

    def zs(x):
        return (x - x[inpool].mean()) / x[inpool].std()
    handle_raw = .5 * zs(-r_use) + .5 * zs(vol)
    pool_h = [float(x) for x in handle_raw[inpool]]
    handle = np.array([rank_attr(float(x), pool_h) for x in handle_raw])
    pool_p = [float(-x) for x in p_use[inpool]]
    passSec = np.array([rank_attr(float(-x), pool_p) for x in p_use])

    rows = []
    for i, p in enumerate(pids):
        rows.append({'playerId': p, 'name': cards[p]['name'], 'pos': pos_card[p], 'season': TEST,
                     'r_sec_raw': r_raw[i], 'r_sec_shrunk': r_shr[i], 'r_sec_used': r_use[i], 'vol': vol[i], 'handle': handle[i], 'handle_raw': handle_raw[i],
                     'passSec': passSec[i], 'passTov_rate_raw': p_raw[i], 'passTov_rate_shrunk': p_shr[i],
                     'TIME_OF_POSS': tof[i], 'ctlTov': ctl[i], 'passTov': ptv[i], 'passes': passes[i], 'inPool': int(inpool[i])})
    cols = ['playerId', 'name', 'pos', 'season', 'r_sec_raw', 'r_sec_shrunk', 'r_sec_used', 'vol', 'handle', 'passSec', 'TIME_OF_POSS', 'ctlTov', 'passTov', 'passes',
            'passTov_rate_raw', 'passTov_rate_shrunk', 'handle_raw', 'inPool']
    with open(HERE / 'handle.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] if isinstance(r[c], (int, str)) else f'{float(r[c]):.6f}' for c in cols])

    # ---- 2K27 ρ ----
    k27 = {}
    with open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            k27[norm(r['name'])] = r
    rho = {}
    for key, col, sub in (('handle', 'Ball Handle', handle), ('passSec', 'Pass Accuracy', passSec)):
        for popname, mask in (('pool', inpool), ('allCard', np.ones(len(pids), bool))):
            xs, ys = [], []
            for i, p in enumerate(pids):
                r = k27.get(norm(cards[p]['name']))
                if r and mask[i] and r[col] != '':
                    xs.append(sub[i]); ys.append(float(r[col]))
            rr = spearmanr(xs, ys)
            rho[f'{key}_{popname}'] = {'rho': float(rr.statistic), 'n': len(xs), 'col': col}
    unmatched = [cards[p]['name'] for p in pids if norm(cards[p]['name']) not in k27]

    # ---- G5、前後 20 ----
    order = sorted([i for i in range(len(pids)) if inpool[i]], key=lambda i: (-handle[i], -handle_raw[i], pids[i]))
    rank_h = {pids[i]: k + 1 for k, i in enumerate(order)}
    order_p = sorted([i for i in range(len(pids)) if inpool[i]], key=lambda i: (-passSec[i], pids[i]))
    rank_p = {pids[i]: k + 1 for k, i in enumerate(order_p)}
    g5 = []
    for key in G5:
        hit = [i for i, p in enumerate(pids) if norm(key) in norm(cards[p]['name']) or norm(key).replace(' ', '') in norm(cards[p]['name']).replace(' ', '')]
        for i in hit:
            p = pids[i]
            g5.append({'query': key, 'name': cards[p]['name'], 'inPool': bool(inpool[i]), 'handle': float(handle[i]), 'rankHandle': rank_h.get(p), 'passSec': float(passSec[i]), 'rankPassSec': rank_p.get(p),
                       'vol': float(vol[i]), 'r_sec_raw': float(r_raw[i]), 'r_sec_used': float(r_use[i]), 'TIME_OF_POSS': float(tof[i]), 'ctlTov': int(ctl[i]), 'passTov': int(ptv[i]), 'passes': int(passes[i])})
    brief = lambda i: {'name': cards[pids[i]]['name'], 'pos': pos_card[pids[i]], 'handle': float(handle[i]), 'passSec': float(passSec[i]), 'vol': float(vol[i]), 'r_sec_raw': float(r_raw[i]), 'r_sec_used': float(r_use[i]), 'TIME_OF_POSS': float(tof[i])}
    top20 = [brief(i) for i in order[:20]]
    bot20 = [brief(i) for i in order[::-1][:20]]

    # ---- h3 ----
    sha_after = {p.name: sha(p) for p in card_files}
    h3 = {'before': sha_before, 'after': sha_after, 'pass': sha_before == sha_after,
          'note': '本腳本只讀 card 0.2.0 檔，不寫入；新欄位只在 handle.csv'}

    boundaries = json.loads((HERE / 'boundaries.json').read_text(encoding='utf-8'))
    sub = json.loads((HERE / 'pbp-tov-subtypes.json').read_text(encoding='utf-8'))
    man = json.loads((HERE / 'pbp-tov-manifest.json').read_text(encoding='utf-8'))
    res = {'seasons': {'fit': FIT, 'test': TEST}, 'fits': fits, 'tests': tests, 'used': used, 'cache': cinfo, 'trackingSum': chk,
           'h1': {'attr': 'r_sec', **tests['rsec']}, 'h2': {'attr': 'passSec', **tests['passSec']}, 'h3': h3,
           'production': {'poolSize': int(inpool.sum()), 'cardPlayers': len(pids), 'cardPlayersNotInTracking': missing_trk,
                          'leagueRate': {'rsec': float(ctl.sum() / tof.sum()), 'passSec': float(ptv.sum() / dpass.sum())}},
           'rho2k27': rho, 'unmatched2k27': unmatched, 'g5': g5, 'top20': top20, 'bottom20': bot20,
           'boundaries': boundaries, 'subtypes': sub, 'manifest': man,
           'sha256': {'handle.csv': sha(HERE / 'handle.csv'), 'preregistration.md': sha(HERE / 'preregistration.md'), 'addendum': sha(HERE / 'preregistration-addendum-1.md')}}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'fits': {a: {k: fits[a][k] for k in ('selected', 'params', 'trainMae', 'trainN')} for a in ATTRS}, 'tests': tests, 'used': used, 'rho': rho, 'h3': h3['pass'], 'chk': chk}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
