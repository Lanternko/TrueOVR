"""E-070：vol = FTA/36 的收縮（只用 <2025-26 的季擬合）＋ 收縮檢查 ＋ 組合 foulDraw 屬性。
用法：python -X utf8 e070_vol.py   → vol-fit.json、attributes-w075/attributes-new.csv、attributes-w0/attributes-new.csv
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
V61 = HERE.parent / 'ovr-v61-shrink-history-2025-26'
sys.path.insert(0, str(V61))
import engine as E
import build_attrs as B
from lib import *  # noqa

W_VOL, W_RATE = 0.75, 0.25
E.ATTR_SEASONS['vol'] = list(SEASONS)
E.MIN_D2['vol'] = 300 / 36


def build_vol(season):
    """{pid: [n1,d1,n2,d2]}，n=FTA，d=MIN/36。"""
    acc = E._acc()
    for r in E.load_pergame(season):
        i = 0 if int(r['half']) == 1 else 2
        pid = int(r['playerId'])
        acc[pid][i] += float(r['FTA'])
        acc[pid][i + 1] += float(r['MIN']) / 36
    return acc


def main():
    cache = {s: E.season_halves(s) for s in SEASONS}
    for s in SEASONS:
        cache[s]['vol'] = build_vol(s)
    pos_by = E.positions()
    ts = [s for s in SEASONS if SEASONS.index(s) < SEASONS.index(TEST_SEASON) and E.hist_seasons('vol', s)]
    fit = E.fit_attr('vol', ts, cache, pos_by)
    # 預註冊：方法 (c)
    fc = fit['c']
    # 收縮檢查：2025-26 後半季 MAE
    ds = E.Dataset('vol', TEST_SEASON, cache, pos_by)
    m = ds.m_league if fc['prior'] == 'league' else ds.m_pos
    y = ds.target
    chk = {'n': int(len(y)), 'shrunk': E.mae(E.pred_c(ds, m, fc['k'], fc['lam'], fc['kh']), y),
           'k0': E.mae(E.pred_c(ds, m, 0.0, fc['lam'], fc['kh']), y), 'firstHalfOnly': E.mae(E.pred_a(ds, ds.m_league), y)}
    out = {'fit': {k: fc[k] for k in ('k', 'lam', 'kh', 'prior', 'trainMae')}, 'trainSeasons': ts, 'trainN': fit['trainN'], 'trainA': fit['trainA'],
           'cAll': fit['cAll'], 'shrinkCheck2025_26': chk, 'minD2': 300 / 36}
    (HERE / 'vol-fit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))

    # ---- 生產值 ----
    bt = json.loads((V61 / 'backtest.json').read_text(encoding='utf-8'))
    ratefit = bt['production']['foulDraw']
    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            cards.setdefault(p['playerId'], p)
    pids = sorted(cards, key=lambda p: (cards[p]['name'], p))
    pos_card = {p: cards[p]['pos'] for p in pids}
    base = B.bench_rows('base')
    pool = [r for r in base if r['GP'] >= B.POOL[0] and r['MIN'] / r['GP'] >= B.POOL[1]]
    idx = {p: i for i, p in enumerate(pids)}
    cur = cache[TEST_SEASON]['vol']
    z = [0.0] * 4
    n = np.array([cur.get(p, z)[0] + cur.get(p, z)[2] for p in pids], float)
    d = np.array([cur.get(p, z)[1] + cur.get(p, z)[3] for p in pids], float)
    dsv = E.Dataset('vol', TEST_SEASON, cache, pos_by, ids=pids)
    pn, pd_ = defaultdict(float), defaultdict(float)
    for i, p in enumerate(pids):
        pn[pos_card[p]] += n[i]; pd_[pos_card[p]] += d[i]
    league_rate = n.sum() / d.sum()
    mv = np.full(len(pids), league_rate) if fc['prior'] == 'league' else np.array([pn[pos_card[p]] / pd_[pos_card[p]] for p in pids])
    vol_rate = B.shrink(n, d, mv, B.Hist(dsv.hn, dsv.hd), 'c', fc)
    raw_vol = np.where(d > 0, n / np.where(d > 0, d, 1), league_rate)

    rows = list(csv.DictReader(open(V61 / 'attributes-new.csv', encoding='utf-8')))
    assert [int(r['playerId']) for r in rows] == pids, 'order mismatch'
    rate = np.array([float(r['rate_foulDraw']) for r in rows])
    in_pool = [p for p in pids if p in {r['PLAYER_ID'] for r in pool}]
    pidx = np.array([idx[p] for p in in_pool])
    def zs(x):
        return (x - x[pidx].mean()) / x[pidx].std()     # ddof=0（母體），實作選擇，見 report
    comp_by_w = {}
    for tag, w in (('w0', 0.0), ('w075', W_VOL)):
        if w == 0.0:
            comp = rate
        else:
            comp = w * zs(vol_rate) + (1 - w) * zs(rate)
        pv = [float(comp[idx[p]]) for p in in_pool]
        fd = np.array([B.rank_attr(float(comp[i]), pv) for i in range(len(pids))])
        comp_by_w[tag] = (comp, fd)
        outdir = HERE / f'attributes-{tag}'
        outdir.mkdir(exist_ok=True)
        hdr = list(rows[0].keys()) + ['raw_vol', 'rate_vol', 'foulDraw_pctile_pool', 'foulDraw_composite']
        with open(outdir / 'attributes-new.csv', 'w', encoding='utf-8', newline='') as fh:
            wr = csv.writer(fh, lineterminator='\n')
            wr.writerow(hdr)
            for i, r in enumerate(rows):
                r2 = dict(r)
                if w != 0.0:
                    r2['new_foulDraw'] = f'{fd[i]:.6f}'   # w=0：保留 V61 原值（c0 逐位元重現）
                wr.writerow([r2[k] for k in rows[0].keys()] + [f'{raw_vol[i]:.6f}', f'{vol_rate[i]:.6f}', '', f'{comp[i]:.6f}'])
    old_fd = np.array([float(r['new_foulDraw']) for r in rows])
    diff0 = float(np.max(np.abs(comp_by_w['w0'][1] - old_fd)))
    print('w0 max diff vs V61 new_foulDraw', diff0, 'pool in cards', len(in_pool), 'of', len(pool))
    (HERE / 'attrs-check.json').write_text(json.dumps({'w0MaxAbsDiffVsV61': diff0, 'poolInCards': len(in_pool), 'poolRows': len(pool),
        'w075MeanAbsChange': float(np.mean(np.abs(comp_by_w['w075'][1] - old_fd))), 'w075MaxAbsChange': float(np.max(np.abs(comp_by_w['w075'][1] - old_fd)))}, indent=2) + '\n')


if __name__ == '__main__':
    main()
