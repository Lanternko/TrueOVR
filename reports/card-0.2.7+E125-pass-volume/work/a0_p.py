"""E-125：2025-26 卡片的 pass 值。複製自 E-090 work/a0.py 的攔截法（攔 B.main 的 rank_attr 輸入），只取 pass；再加 w_vol。
（預註冊寫的 a0_e101.py:97 只處理 mid、short；pass 的 r 和池來自 E-090 a0-raw.json，所以這裡用 a0.py 的方法重現它。）
w_vol=0：r、pool 必須逐位元等於 E-090 a0-raw.json 的 pass（不做 zs）。
w_vol>0：comp = w·zs(vol)+(1−w)·zs(rate)；vol = 收縮 AST/(MIN/36)（astvol-fit.json、位置先驗、卡片位置）；zs 的池 = base 列 GP>=30 且 MPG>=20 且在卡片名單。
輸出：../a0-pass-P<w>.json（r、pool、檢查）。
用法（repo 根目錄）：python -I -B reports/card-0.2.7+E125-pass-volume/work/a0_p.py <w_vol> </dev/null
"""
import json
import shutil
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
TMP = HERE / 'tmp' / 'a0p'
TMP.mkdir(parents=True, exist_ok=True)
W_VOL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
TAG = 'P%d' % round(W_VOL * 100)
sys.path.insert(0, str(V61))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import build_attrs as B  # noqa: E402
import engine as E  # noqa: E402
from lib import LEAGUE, TEST_SEASON, SEASONS  # noqa: E402

shutil.copy(V61 / 'backtest.json', TMP / 'backtest.json')
B.D = TMP
src = (V61 / 'build_attrs.py').read_text(encoding='utf-8').splitlines()
LINE_RANK_NEW = next(i + 1 for i, s in enumerate(src) if 'vals = {p: rank_attr(sign * float(rn[i]), pool_vals)' in s)
cap = {}
_rank = B.rank_attr


def caller(fn_name):
    f = sys._getframe(2)
    while f is not None and f.f_code.co_name != fn_name:
        f = f.f_back
    return f


def rank_hook(x, pool):
    f = caller('main')
    if f is not None and f.f_lineno == LINE_RANK_NEW and f.f_locals['a'] == 'pass':
        cap.setdefault('r', []).append((x, f.f_locals['p']))
        cap['pool'] = list(pool)
    return _rank(x, pool)


B.rank_attr = rank_hook
B.main()
B.rank_attr = _rank
r_rate = {str(p): x for x, p in cap['r']}
pool_rate = cap['pool']
raw = json.load(open(E090 / 'work/a0-raw.json', encoding='utf-8'))['pass']
assert r_rate == raw['r'] and pool_rate == raw['pool'], 'a0 重現 E-090 a0-raw.json 的 pass 失敗'
chk = {'rateReproducesE090a0raw': True, 'n': len(r_rate), 'poolN': len(pool_rate)}

if W_VOL == 0:
    r_out, pool_out = r_rate, pool_rate
else:
    fit = json.load(open(OUT / 'astvol-fit.json', encoding='utf-8'))['fit']
    E.ATTR_SEASONS['astvol'] = list(SEASONS)
    E.MIN_D2['astvol'] = 300 / 36
    cache = {s: E.season_halves(s) for s in SEASONS}
    for s in SEASONS:
        acc = E._acc()
        for r in E.load_pergame(s):
            i = 0 if int(r['half']) == 1 else 2
            pid = int(r['playerId'])
            acc[pid][i] += float(r['AST'])
            acc[pid][i + 1] += float(r['MIN']) / 36
        cache[s]['astvol'] = acc
    pos_by = E.positions()
    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    cards = {}
    for t in league['teams']:
        for p in t['roster']:
            cards.setdefault(p['playerId'], p)
    pids = sorted(cards, key=lambda p: (cards[p]['name'], p))
    pos_card = {p: cards[p]['pos'] for p in pids}
    idx = {p: i for i, p in enumerate(pids)}
    cur = cache[TEST_SEASON]['astvol']
    z = [0.0] * 4
    n = np.array([cur.get(p, z)[0] + cur.get(p, z)[2] for p in pids], float)
    d = np.array([cur.get(p, z)[1] + cur.get(p, z)[3] for p in pids], float)
    dsv = E.Dataset('astvol', TEST_SEASON, cache, pos_by, ids=pids)
    pn, pd_ = defaultdict(float), defaultdict(float)
    for i, p in enumerate(pids):
        pn[pos_card[p]] += n[i]; pd_[pos_card[p]] += d[i]
    league_rate = n.sum() / d.sum()
    mv = np.full(len(pids), league_rate) if fit['prior'] == 'league' else np.array([pn[pos_card[p]] / pd_[pos_card[p]] for p in pids])
    avol = B.shrink(n, d, mv, B.Hist(dsv.hn, dsv.hd), 'c', fit)
    base = B.bench_rows('base')
    pool_pids = [r['PLAYER_ID'] for r in base if r['GP'] >= B.POOL[0] and r['MIN'] / r['GP'] >= B.POOL[1] and r['PLAYER_ID'] in idx]
    assert len(pool_pids) == len(pool_rate)
    assert [r_rate[str(p)] for p in pool_pids] == pool_rate, '池順序對不上'
    rate = np.array([r_rate[str(p)] for p in pids])
    pidx = np.array([idx[p] for p in pool_pids])
    zs = lambda x: (x - x[pidx].mean()) / x[pidx].std()
    comp = W_VOL * zs(avol) + (1 - W_VOL) * zs(rate)
    r_out = {str(p): float(comp[i]) for i, p in enumerate(pids)}
    pool_out = [float(comp[idx[p]]) for p in pool_pids]
    chk.update({'wVol': W_VOL, 'volRawMeanPool': float(np.mean((n / d)[pidx])), 'zsPoolN': len(pool_pids)})
(OUT / f'a0-pass-{TAG}.json').write_text(json.dumps({'r': r_out, 'pool': pool_out, 'check': chk}, ensure_ascii=False), encoding='utf-8')
print(TAG, chk)
