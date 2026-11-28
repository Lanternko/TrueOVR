"""python reports/ovr-v55-finisher-fix-2025-26/bootstrap.py [mode] -> bootstrap.json

對 §3.1 的每個 Spearman 增益做成對 bootstrap（重抽球員、兩塊板用同一組重抽索引），
回答「這個 ρ 的改善能不能和抽樣雜訊分開」。驗收門檻 A1/A2 是「不比 v54 差」，所以
CI 包含 0 不影響判定；但報告必須講清楚哪一個增益是真的、哪一些只是方向對。
"""
import csv, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import shrink as S  # noqa: E402
import shrink_v2 as V  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else 'B12'
B = 4000
SEED = 20261019
rapm = {int(r['playerId']): r for r in csv.DictReader(open(S.ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}
res = {}
for v in ['v54', MODE]:
    pl = S.load(v)
    x, mc = S.board(pl, set(range(8)))
    res[v] = (pl, V.shrink_v2(pl, x, mc)[0])
pl = res['v54'][0]
rng = np.random.default_rng(SEED)
out = {'mode': MODE, 'draws': B, 'seed': SEED, 'buckets': {}}
for netcol, posscol, minposs, tag in [('pooledNet', 'pooledPoss', V.POOLED_POSS, 'pooled'),
                                      ('lastSeasonNet', 'lastSeasonPoss', V.LAST_POSS, 'last')]:
    for label, lo, hi in V.BUCKETS:
        keep = [i for i, p in enumerate(pl) if p['playerId'] in rapm and rapm[p['playerId']][posscol]
                and float(rapm[p['playerId']][posscol]) >= minposs and lo <= p['W'] < hi]
        if len(keep) < 5:
            continue
        T = np.array([float(rapm[pl[i]['playerId']][netcol]) for i in keep])
        a, b = res['v54'][1][keep], res[MODE][1][keep]
        ds = np.array([S.spearman(b[s], T[s]) - S.spearman(a[s], T[s])
                       for s in (rng.integers(0, len(keep), len(keep)) for _ in range(B))])
        out['buckets'][f'{tag} {label}'] = {'players': len(keep), 'delta': round(S.spearman(b, T) - S.spearman(a, T), 4),
                                            'ci95': [round(float(np.percentile(ds, 2.5)), 4), round(float(np.percentile(ds, 97.5)), 4)],
                                            'pDeltaPositive': round(float((ds > 0).mean()), 3)}
(Path(__file__).parent / 'bootstrap.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
for k, v in out['buckets'].items():
    print(f"{k:22s} n={v['players']:4d} d={v['delta']:+.3f} CI95=[{v['ci95'][0]:+.3f},{v['ci95'][1]:+.3f}] P(d>0)={v['pDeltaPositive']:.3f}")
