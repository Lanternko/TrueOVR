"""E-082 (c2Q)／(c2N)。基準 = card 0.2.3 半季 g（off 跑的 dirs.json['cand']）；候選 = on 跑的 dirs.json['cand']。
同一個 ans，ρ 差；bootstrap 同 E-075 b2：seed 1、2000 次、母群姓名（兩方向聯集）、兩方向平均、5%–95%。
用法：PYTHONDONTWRITEBYTECODE=1 python -I c2.py <Q|N>   輸出 work/c2<Q|N>.json
Q：ans = pooledNet[ev] × mpgh[ev]（dirs.json['ans']）。
N：ans = rapm1-{ev}.csv 的 net × mpgh[ev] 的 mpg（按姓名對；對不到的球員從該方向剔除並計數）。
"""
import csv, hashlib, json, os, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E064 = ROOT / 'reports/card-0.1.2+E064-pergame'
sys.path.insert(0, str(E064))
from evaluate_e064 import rho, read  # noqa: E402
which = sys.argv[1]
off = json.load(open(HERE / 'out/off/work/dirs.json', encoding='utf-8'))
on = json.load(open(HERE / 'out/on/work/dirs.json', encoding='utf-8'))
res = {'which': which, 'dirs': {}}
dat = {}
for dn in ('AB', 'BA'):
    assert off[dn]['names'] == on[dn]['names'], '母群不同'
    assert off[dn]['ans'] == on[dn]['ans'], 'ans 不同'
    names = off[dn]['names']
    base = np.array(off[dn]['cand']); cand = np.array(on[dn]['cand'])
    ev = dn[1]
    if which == 'Q':
        ans = np.array(on[dn]['ans']); keep = np.ones(len(names), bool); miss = []
    else:
        f = ROOT / f'reports/card-0.2.3+E081-age-residual/rapm1-{ev}.csv'
        r1 = {r['name']: float(r['net']) for r in read(f)}
        pid = {r['name']: int(r['playerId']) for r in read(f)}
        # mpgh[ev]：E064 mpg-{ev}.csv（playerId → mpg），與 e082.py 的 D['mpgh'] 同來源
        mp = {int(r['playerId']): float(r['mpg']) for r in read(E064 / f'mpg-{ev}.csv')}
        # 姓名 → playerId：用 e082 母群所用的 nm2pid（來自 rapm-A/B；此處由 rapm1 csv 的 playerId 欄對上）
        keep = np.array([n in r1 for n in names]); miss = [n for n in names if n not in r1]
        ans = np.array([r1[n] * mp[pid[n]] if n in r1 else np.nan for n in names])
    dat[dn] = dict(names=names, base=base, cand=cand, ans=ans, keep=keep)
    res['dirs'][dn] = {'n_pool': len(names), 'n_used': int(keep.sum()), 'missing': miss}
master = sorted(set(dat['AB']['names']) | set(dat['BA']['names']))
NN = len(master)
mp_ = {}
for dn, d in dat.items():
    idx = {n: i for i, n in enumerate(d['names']) if d['keep'][i]}
    mp_[dn] = np.array([idx.get(n, -1) for n in master])
pt = {dn: (rho(d['cand'][d['keep']], d['ans'][d['keep']]), rho(d['base'][d['keep']], d['ans'][d['keep']])) for dn, d in dat.items()}
delta = float(np.mean([a - b for a, b in pt.values()]))
rng = np.random.default_rng(1)
bb = []
for _ in range(2000):
    ix = rng.integers(0, NN, NN); dd = []
    for dn, d in dat.items():
        s = mp_[dn][ix]; s = s[s >= 0]
        dd.append(rho(d['cand'][s], d['ans'][s]) - rho(d['base'][s], d['ans'][s]))
    bb.append(float(np.mean(dd)))
lo, hi = float(np.percentile(bb, 5)), float(np.percentile(bb, 95))
res.update({'delta': delta, 'ci90': [lo, hi], 'rho_cand': {k: v[0] for k, v in pt.items()}, 'rho_base': {k: v[1] for k, v in pt.items()},
            'threshold': '下界 > -0.02', 'pass': bool(lo > -0.02), 'lower_gt_0': bool(lo > 0), 'nMaster': NN})
if which == 'N':
    res['rapm1_sha256'] = {x: hashlib.sha256((ROOT / f'reports/card-0.2.3+E081-age-residual/rapm1-{x}.csv').read_bytes()).hexdigest() for x in 'AB'}
(HERE / 'work').mkdir(exist_ok=True)
(HERE / 'work' / f'c2{which}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + chr(10), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, indent=1)[:1800])
