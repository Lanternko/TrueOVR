"""v55 修正 B 的 v2 收縮（模擬分鐘 >=20 不收縮，10->20 線性斜坡）＋驗收指標。

  python reports/ovr-v55-finisher-fix-2025-26/shrink_v2.py <variant>   # v54 | B1 | B2 | B12 | B12_oos
  python reports/ovr-v55-finisher-fix-2025-26/shrink_v2.py all         # 全部 + summary.json

收縮規則與 reports/ovr-v54-shrinkage-2025-26/shrink_v2.py 逐字相同。與 v55-bench-prior 的差別
（預先登錄 §6 已登錄）：
  1. BUCKETS 多一個合併的 `1300+`（任務背景數字就是三桶 + 全體的口徑）。
  2. **所有**變體都算 bucketSpearmanVsPooledRAPM 與 bucketSpearmanVsLastSeasonRAPM
     （bench-prior 只對 AC_oos 算後者）；單季目標用 lastSeasonPoss>=500，與 bench-prior 報告
     「樣本外補驗」那張表同口徑（不是 bucket_spearman 的預設 5000，那會讓 <800 桶變成 n=0）。
  3. 多了 A4 用的吃餅組／創造組平均名次變化（分組凍結於 frozen-groups.json），以 v54 為基準。
"""
import csv, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import shrink as S  # noqa: E402
from shrink import board, spearman, ROOT, OUT, EVAL_POSS, LOW_POSS, FOCUS, board_file  # noqa: E402

LO, HI = 10, 20
BUCKETS = [('<800', 0, 800), ('800-1300', 800, 1300), ('1300+', 1300, float('inf')), ('all', 0, float('inf'))]
POOLED_POSS, LAST_POSS = 5000, 500
VARIANTS = ['v54', 'B1', 'B2', 'B12', 'B12_oos']
GROUPS = json.loads((OUT / 'frozen-groups.json').read_text(encoding='utf-8'))


def shrink_v2(players, x, mc):
    _, B, fit = S.shrink(players, x, mc)
    m = np.array([p['m'] for p in players]); lmpg = np.log([p['mpg'] for p in players])
    mu = fit['priorIntercept'] + fit['priorLogMinutesPerGameSlope'] * lmpg
    B2 = B + (1 - B) * np.clip((m - LO) / (HI - LO), 0, 1)
    return mu + B2 * (x - mu), B2, fit, mu + B * (x - mu)


def ranks(v):
    r = np.empty(len(v), int); r[np.argsort(-v)] = np.arange(1, len(v) + 1); return r


def bucket_spearman(players, x, x2, rapm, netcol, posscol, min_poss):
    out = {}
    for label, lo, hi in BUCKETS:
        keep = [i for i, p in enumerate(players) if p['playerId'] in rapm and rapm[p['playerId']][posscol]
                and float(rapm[p['playerId']][posscol]) >= min_poss and lo <= p['W'] < hi]
        if len(keep) < 5:
            out[label] = {'players': len(keep), 'raw': None, 'v2': None}
            continue
        N = [float(rapm[players[i]['playerId']][netcol]) for i in keep]
        out[label] = {'players': len(keep), 'raw': spearman(x[keep], N), 'v2': spearman(x2[keep], N)}
    return out


def run_variant(variant):
    players = S.load(variant); n = len(players)
    m = np.array([p['m'] for p in players]); big = m >= HI
    hb = {h: board(players, s) for h, s in {'even': {0, 2, 4, 6}, 'odd': {1, 3, 5, 7}}.items()}
    raw_err = np.zeros(n); v2_err = np.zeros(n); v1_err = np.zeros(n)
    for a, b in [('even', 'odd'), ('odd', 'even')]:
        xa, mca = hb[a]; xb, _ = hb[b]
        x2h, _, _, x1h = shrink_v2(players, xa, mca)
        raw_err += (xa - xb) ** 2 / 2; v2_err += (x2h - xb) ** 2 / 2; v1_err += (x1h - xb) ** 2 / 2
    x, mc = board(players, set(range(8)))
    x2, B2, fit, x1 = shrink_v2(players, x, mc)
    rapm = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}

    def ext(min_poss):
        keep = [i for i, p in enumerate(players) if p['playerId'] in rapm and float(rapm[p['playerId']]['pooledPoss']) >= min_poss]
        N = [float(rapm[players[i]['playerId']]['pooledNet']) for i in keep]
        D = [float(rapm[players[i]['playerId']]['pooledD']) for i in keep]
        return {'players': len(keep), **{k: {'raw': spearman(x[keep], T), 'v1': spearman(x1[keep], T), 'v2': spearman(x2[keep], T)} for k, T in [('net', N), ('defense', D)]}}

    r0, r1, r2 = ranks(x), ranks(x1), ranks(x2)
    summary = {
        'variant': variant, 'board': str(board_file(variant)), 'players': n, 'fit': fit,
        'splitHalfMSE': {'raw': float(raw_err.mean()), 'v1': float(v1_err.mean()), 'v2': float(v2_err.mean())},
        'startersUnshrunk': int(big.sum()),
        'externalRAPM': {'poss5000': ext(EVAL_POSS), 'poss1000': ext(LOW_POSS)},
        'bucketSpearmanVsPooledRAPM': bucket_spearman(players, x, x2, rapm, 'pooledNet', 'pooledPoss', POOLED_POSS),
        'bucketSpearmanVsLastSeasonRAPM': bucket_spearman(players, x, x2, rapm, 'lastSeasonNet', 'lastSeasonPoss', LAST_POSS),
        'rank': {str(p['playerId']): int(r2[i]) for i, p in enumerate(players)},
        'rawRank': {str(p['playerId']): int(r0[i]) for i, p in enumerate(players)},
        'top30': [players[i]['name'] for i in np.argsort(r2)[:30]],
        'focus': {players[i]['name']: {'rawRank': int(r0[i]), 'v1Rank': int(r1[i]), 'v2Rank': int(r2[i]), 'sourceMinutes': round(players[i]['W'])}
                  for i in range(n) if players[i]['name'] in FOCUS},
    }
    vdir = OUT / variant
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / 'summary-v2.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    with open(vdir / 'ranking-v2.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'rawRank', 'v1Rank', 'playerId', 'name', 'position', 'simMinutes', 'sourceMinutes', 'v2Per36', 'rawPer36', 'shrinkFactor'])
        for i in np.argsort(r2):
            p = players[i]
            wr.writerow([r2[i], r0[i], r1[i], p['playerId'], p['name'], p['pos'], round(p['m'], 2), round(p['W']), round(float(x2[i]), 3), round(float(x[i]), 3), round(float(B2[i]), 3)])
    return summary


def a4(base, cand):
    """A4：Karlo v2 名次下降 >=10，且吃餅組平均 Δrank 比創造組低 >=10（Δ = v54 名次 - 新名次）。"""
    br, cr = base['rank'], cand['rank']

    def delta(pid):
        k = str(pid)
        return br[k] - cr[k] if k in br and k in cr else None

    out = {}
    for key in ['finishers', 'creators']:
        ds = [d for d in (delta(g['playerId']) for g in GROUPS['groups'][key]) if d is not None]
        out[key] = {'players': len(ds), 'meanRankChange': float(np.mean(ds)), 'medianRankChange': float(np.median(ds))}
    karlo = next(g for g in GROUPS['focus'] if g['name'] == 'Karlo Matković')['playerId']
    out['karlo'] = {'v54Rank': br[str(karlo)], 'rank': cr[str(karlo)], 'change': delta(karlo)}
    out['finisherMinusCreator'] = out['finishers']['meanRankChange'] - out['creators']['meanRankChange']
    out['karloDropsAtLeast10'] = out['karlo']['change'] <= -10
    out['gapAtMostMinus10'] = out['finisherMinusCreator'] <= -10
    out['passed'] = bool(out['karloDropsAtLeast10'] and out['gapAtMostMinus10'])
    return out


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'all'
    variants = VARIANTS if arg == 'all' else [arg]
    results = {}
    for v in variants:
        if not board_file(v).exists():
            print(json.dumps({'variant': v, 'skipped': 'checkpoint not found yet'})); continue
        results[v] = run_variant(v)
        r = results[v]
        print(json.dumps({'variant': v, 'players': r['players'],
                          'pooled': {k: (None if d['v2'] is None else round(d['v2'], 3)) for k, d in r['bucketSpearmanVsPooledRAPM'].items()},
                          'last': {k: (None if d['v2'] is None else round(d['v2'], 3)) for k, d in r['bucketSpearmanVsLastSeasonRAPM'].items()},
                          'defense': round(r['externalRAPM']['poss5000']['defense']['v2'], 3)}, ensure_ascii=True))
    if arg == 'all' and 'v54' in results:
        base = results['v54']
        out = {'variants': {v: {'bucketSpearmanVsPooledRAPM': r['bucketSpearmanVsPooledRAPM'],
                                'bucketSpearmanVsLastSeasonRAPM': r['bucketSpearmanVsLastSeasonRAPM'],
                                'defenseSpearman': r['externalRAPM']['poss5000']['defense'],
                                'focus': r['focus']} for v, r in results.items()},
               'a4': {v: a4(base, r) for v, r in results.items() if v != 'v54'}}
        (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
        print(json.dumps(out['a4'], ensure_ascii=True, indent=1))
