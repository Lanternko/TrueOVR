"""E-101 h1（預註冊 §1）：mid、short 用修正分區＋聯盟先驗重跑 E-090 h1。複製自 ../card-0.2.5+E097-topscale/work/h1.py，tails／slope／test 一字不改；
配對 = E-090 h1-pairs.json，只把 mid、short 換成本實驗 h1-pairs-e101.json；屬性順序與共用的 rng 照舊。
修正分區後 mid、short 的配對人數改變，共用 rng 之後的屬性抽樣序列會跟著變，所以其他 11 項不 assert，只報告是否重現 E-090；
其他屬性的開關照預註冊 §1 沿用 E-090 h1-results.json（build_e101.py 讀 E-090 檔，不讀這裡的重算值）。
用法：python -I -B reports/card-0.2.5+E101-crossera/work/h1_e101.py → h1-results.json
"""
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
E090 = OUT.parent / 'card-0.2.4+E090-onball-tail'
assert hashlib.sha256((E090 / 'h1-sources.json').read_bytes()).hexdigest() == (E090 / 'h1-sources.sha256').read_text().split()[0]
assert hashlib.sha256((OUT / 'h1-pairs-e101.json').read_bytes()).hexdigest() == (OUT / 'h1-pairs-e101.sha256').read_text().split()[0]
src = json.load(open(E090 / 'h1-sources.json', encoding='utf-8'))
pairs = json.load(open(E090 / 'work/h1-pairs.json', encoding='utf-8'))
pairs.update(json.load(open(OUT / 'h1-pairs-e101.json', encoding='utf-8'))['pairs'])
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
for a in [k for k in src if not k.startswith('_')]:
    if src[a]['source'] == 'excluded':
        res[a] = {'excluded': src[a]['reason']}
        continue
    rows = pairs[a]
    top, bot = tails(rows)
    res[a] = {'top': test(top, rng), 'bot': test(bot, rng),
              'allSlope': slope([r['prev'] for r in rows], [r['next'] for r in rows]), 'nObsAll': len(rows)}
ref = json.load(open(E090 / 'h1-results.json', encoding='utf-8'))['h1']
repro = {a: res[a] == ref[a] for a in res if a not in ('mid', 'short')}
sw = lambda v: {e: v[e]['pass'] for e in ('top', 'bot')} if 'top' in v else None
switch_same = {a: sw(res[a]) == sw(ref[a]) for a in res if a not in ('mid', 'short')}
n_pass = sum(v[e]['pass'] for v in res.values() if 'top' in v for e in ('top', 'bot'))
out = {'h1': {a: res[a] for a in ('mid', 'short')}, 'E090_h1': {a: ref[a] for a in ('mid', 'short')},
       'otherAttrsReproduceE090': repro, 'otherAttrsSwitchSameAsE090UnderShiftedRng': switch_same, 'otherAttrsRerunReportOnly': {a: res[a] for a in res if a not in ('mid', 'short')}, 'h1PairsE101Sha256': (OUT / 'h1-pairs-e101.sha256').read_text().split()[0]}
json.dump(out, open(OUT / 'h1-results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for a in ('mid', 'short'):
    for tag, v in (('E101', res[a]), ('E090', ref[a])):
        print(f"{tag} {a:6s} top b={v['top']['b']:+.3f} [{v['top']['lo90']:+.3f},{v['top']['hi90']:+.3f}] n={v['top']['nObs']:3d} {'PASS' if v['top']['pass'] else 'fail'} | "
              f"bot b={v['bot']['b']:+.3f} [{v['bot']['lo90']:+.3f},{v['bot']['hi90']:+.3f}] n={v['bot']['nObs']:3d} {'PASS' if v['bot']['pass'] else 'fail'}")
print('other attrs reproduce E-090:', repro)
print('switch same:', switch_same)
