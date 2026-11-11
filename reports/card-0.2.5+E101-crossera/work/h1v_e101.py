"""E-101 h1v（預註冊 §1）：修正分區＋聯盟先驗後重跑 E-096 h1v。複製自 ../card-0.2.5+E097-topscale/work/h1v.py（其本身一字不改複製自 E-096），只改說明與輸入檔名。
用法：python -I -B reports/card-0.2.5+E101-crossera/work/h1v_e101.py → h1v-results.json
"""
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
assert hashlib.sha256((OUT / 'h1v-pairs-e101.json').read_bytes()).hexdigest() == (OUT / 'h1v-pairs-e101.sha256').read_text().split()[0]
src_ = json.load(open(OUT / 'h1v-pairs-e101.json', encoding='utf-8'))
B_N, SEED = 2000, 20261029


def pct(x, arr):
    arr = np.asarray(arr)
    return 100 * ((arr < x).sum() + 0.5 * (arr == x).sum()) / len(arr)


def tails(rows):
    by = {}
    for r in rows:
        by.setdefault(r['pair'], []).append(r)
    top, bot = [], []
    for pr, rs in by.items():
        prev = [r['prev'] for r in rs]
        for r in rs:
            p = pct(r['prev'], prev)
            if p >= 90:
                top.append(r)
            if p <= 10:
                bot.append(r)
    return top, bot


def slope(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2 or np.ptp(x) == 0:
        return float('nan')
    xc = x - x.mean()
    return float((xc * (y - y.mean())).sum() / (xc * xc).sum())


def test(rows, rng):
    pids = sorted({r['pid'] for r in rows})
    by = {p: [r for r in rows if r['pid'] == p] for p in pids}
    b = slope([r['prev'] for r in rows], [r['next'] for r in rows])
    bs = []
    for _ in range(B_N):
        draw = rng.integers(0, len(pids), len(pids))
        rr = [r for i in draw for r in by[pids[i]]]
        bs.append(slope([r['prev'] for r in rr], [r['next'] for r in rr]))
    bs = np.array(bs)
    ok = bs[~np.isnan(bs)]
    lo, hi = (float(np.percentile(ok, 5)), float(np.percentile(ok, 95))) if len(ok) else (float('nan'), float('nan'))
    return {'b': b, 'lo90': lo, 'hi90': hi, 'nObs': len(rows), 'nPlayers': len(pids), 'nanDraws': int(np.isnan(bs).sum()), 'pass': bool(lo > 0)}


rng = np.random.default_rng(SEED)
res = {}
for a, rows in src_['pairs'].items():
    top, bot = tails(rows)
    res[a] = {'top': test(top, rng), 'bot': test(bot, rng),
              'allSlope': slope([r['prev'] for r in rows], [r['next'] for r in rows]), 'nObsAll': len(rows)}
out = {'h1v': res, 'h1vPairsE101Sha256': (OUT / 'h1v-pairs-e101.sha256').read_text().split()[0]}
json.dump(out, open(OUT / 'h1v-results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for a, v in res.items():
    print(f"{a:11s} top b={v['top']['b']:+.3f} [{v['top']['lo90']:+.3f},{v['top']['hi90']:+.3f}] n={v['top']['nObs']:3d} {'PASS' if v['top']['pass'] else 'fail'} | "
          f"bot b={v['bot']['b']:+.3f} [{v['bot']['lo90']:+.3f},{v['bot']['hi90']:+.3f}] n={v['bot']['nObs']:3d} {'PASS' if v['bot']['pass'] else 'fail'} | all {v['allSlope']:+.3f}")
