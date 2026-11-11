import hashlib, json
from pathlib import Path
import numpy as np
OUT = Path('.').resolve()
assert hashlib.sha256((OUT / 'h1-pairs.json').read_bytes()).hexdigest() == (OUT / 'h1-pairs.sha256').read_text().split()[0]
pairs = json.load(open(OUT / 'h1-pairs.json', encoding='utf-8'))['pairs']
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
            if p >= 90: top.append(r)
            if p <= 10: bot.append(r)
    return top, bot

def slope(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2 or np.ptp(x) == 0: return float('nan')
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
    bs = np.array(bs); ok = bs[~np.isnan(bs)]
    lo, hi = (float(np.percentile(ok, 5)), float(np.percentile(ok, 95))) if len(ok) else (float('nan'), float('nan'))
    return {'b': b, 'lo90': lo, 'hi90': hi, 'nObs': len(rows), 'nPlayers': len(pids), 'nanDraws': int(np.isnan(bs).sum()), 'pass': bool(lo > 0)}

rng = np.random.default_rng(SEED)
res = {}
for a in ('threeValue', 'help', 'pressure', 'presDisplay'):
    rows = pairs[a]
    npairs = len({r['pair'] for r in rows})
    if npairs < 2:
        res[a] = {'excluded': 'fewer than two adjacent pairs'}; continue
    top, bot = tails(rows)
    res[a] = {'top': test(top, rng), 'bot': test(bot, rng), 'allSlope': slope([r['prev'] for r in rows], [r['next'] for r in rows]), 'nObsAll': len(rows), 'nPairs': npairs}
    if a == 'presDisplay': res[a]['reportOnly'] = '預註冊：presDisplay 跟 pressure 的開關；此列為事後報告用，在 6 個檢定之後才抽樣，不影響其他抽樣序列'
out = {'h1': res, 'h1PairsSha256': (OUT / 'h1-pairs.sha256').read_text().split()[0], 'seed': SEED, 'bootstrapDraws': B_N,
       'order': 'threeValue top/bot, help top/bot, pressure top/bot (6 tests), then presDisplay report-only'}
json.dump(out, open(OUT / 'h1-results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for a, v in res.items():
    for e in ('top', 'bot'):
        t = v[e]
        print(f"{a:12s} {e} b={t['b']:+.3f} [{t['lo90']:+.3f},{t['hi90']:+.3f}] n={t['nObs']:3d} players={t['nPlayers']} {'PASS' if t['pass'] else 'fail'}")
    print('   allSlope', round(v['allSlope'], 3))
