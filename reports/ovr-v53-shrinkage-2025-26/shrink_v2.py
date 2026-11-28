"""Revised shrinkage: starters (sim minutes >= 20) unshrunk, linear ramp from 10 to 20 (see preregistration-v2.md).

  python reports/ovr-v53-shrinkage-2025-26/shrink_v2.py

Same estimator as shrink.py; only the shrinkage factor changes: B' = B + (1 - B) * clip((m - 10) / 10, 0, 1).
"""
import csv, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import shrink as S  # noqa: E402
from shrink import load, board, spearman, media_ranks, ROOT, OUT, SMALL_W, TOP, EVAL_POSS, LOW_POSS, FOCUS  # noqa: E402

LO, HI = 10, 20


def shrink_v2(players, x, mc):
    _, B, fit = S.shrink(players, x, mc)
    m = np.array([p['m'] for p in players]); lmpg = np.log([p['mpg'] for p in players])
    mu = fit['priorIntercept'] + fit['priorLogMinutesPerGameSlope'] * lmpg
    B2 = B + (1 - B) * np.clip((m - LO) / (HI - LO), 0, 1)
    return mu + B2 * (x - mu), B2, fit, mu + B * (x - mu)


def ranks(v):
    r = np.empty(len(v), int); r[np.argsort(-v)] = np.arange(1, len(v) + 1); return r


def main():
    players = load(); n = len(players)
    m = np.array([p['m'] for p in players]); big = m >= HI; W = np.array([p['W'] for p in players])
    hb = {h: board(players, s) for h, s in {'even': {0, 2, 4, 6}, 'odd': {1, 3, 5, 7}}.items()}
    raw_err = np.zeros(n); v2_err = np.zeros(n); v1_err = np.zeros(n)
    for a, b in [('even', 'odd'), ('odd', 'even')]:
        xa, mca = hb[a]; xb, _ = hb[b]
        x2, _, _, x1 = shrink_v2(players, xa, mca)
        raw_err += (xa - xb) ** 2 / 2; v2_err += (x2 - xb) ** 2 / 2; v1_err += (x1 - xb) ** 2 / 2
    d = raw_err - v2_err
    rng = np.random.default_rng(20261018)
    ci = lambda v: [float(np.percentile(s, q)) for s in [[v[rng.integers(0, len(v), len(v))].mean() for _ in range(2000)]] for q in (2.5, 97.5)]
    small_m = ~big
    g1 = {'all': {'mseRaw': float(raw_err.mean()), 'mseV2': float(v2_err.mean()), 'meanReduction': float(d.mean()), 'ci95': ci(d)},
          'minutesUnder20': {'players': int(small_m.sum()), 'mseRaw': float(raw_err[small_m].mean()), 'mseV2': float(v2_err[small_m].mean()),
                             'meanReduction': float(d[small_m].mean()), 'ci95': ci(d[small_m])},
          'minutes20Plus': {'players': int(big.sum()), 'meanReduction': float(d[big].mean())},
          'v1ForReference': {'all': float((raw_err - v1_err).mean()), 'minutesUnder20': float((raw_err - v1_err)[small_m].mean()),
                             'minutes20Plus': float((raw_err - v1_err)[big].mean())}}
    g1['passed'] = g1['all']['ci95'][0] > 0 and g1['minutesUnder20']['ci95'][0] > 0
    sb = lambda r: 2 * r / (1 + r)
    rel = {'raw': sb(spearman(hb['even'][0], hb['odd'][0])),
           'v1': sb(spearman(shrink_v2(players, *hb['even'])[3], shrink_v2(players, *hb['odd'])[3])),
           'v2': sb(spearman(shrink_v2(players, *hb['even'])[0], shrink_v2(players, *hb['odd'])[0]))}
    x, mc = board(players, set(range(8)))
    x2, B2, fit, x1 = shrink_v2(players, x, mc)
    rapm = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}

    def ext(min_poss):
        keep = [i for i, p in enumerate(players) if p['playerId'] in rapm and float(rapm[p['playerId']]['pooledPoss']) >= min_poss]
        N = [float(rapm[players[i]['playerId']]['pooledNet']) for i in keep]; D = [float(rapm[players[i]['playerId']]['pooledD']) for i in keep]
        return {'players': len(keep), **{k: {'raw': spearman(x[keep], T), 'v1': spearman(x1[keep], T), 'v2': spearman(x2[keep], T)} for k, T in [('net', N), ('defense', D)]}}
    g2 = ext(EVAL_POSS)
    g2['passed'] = g2['net']['v2'] >= g2['net']['raw'] - 0.01 and g2['defense']['v2'] >= g2['defense']['raw'] - 0.01
    r0, r1, r2 = ranks(x), ranks(x1), ranks(x2)
    small = W < SMALL_W
    g3 = {'smallWInTop50': {'raw': int((small & (r0 <= TOP)).sum()), 'v1': int((small & (r1 <= TOP)).sum()), 'v2': int((small & (r2 <= TOP)).sum())},
          'remainingSmallInTop50': [players[i]['name'] for i in np.argsort(r2) if small[i] and r2[i] <= TOP]}
    g3['passed'] = g3['smallWInTop50']['v2'] <= g3['smallWInTop50']['raw'] / 2
    g4 = {'starterSpearman': spearman(x2[big], x[big])}
    g4['passed'] = g4['starterSpearman'] > 1 - 1e-9
    moved = np.abs(r2[big] - r0[big])
    passed_starters = [players[i]['name'] for i in np.argsort(r2) if not big[i] and r2[i] <= 50 and r0[i] > 50]
    mr = media_ranks(players); mi = sorted(mr)
    med = lambda v: spearman(-v[mi], [-mr[i] for i in mi])
    summary = {'preregistration': 'preregistration-v2.md', 'players': n, 'fit': fit,
               'G1splitHalfPrediction': g1, 'G2externalRAPM': g2, 'G3bench': g3, 'G4starterOrder': g4,
               'gates': {'G1': g1['passed'], 'G2': g2['passed'], 'G3': g3['passed'], 'G4': g4['passed'],
                         'adopt': g1['passed'] and g2['passed'] and g3['passed'] and g4['passed']},
               'supplementary': {'rapmPoss1000': ext(LOW_POSS), 'splitHalfReliability': rel,
                                 'mediaSpearman': {'raw': med(x), 'v1': med(x1), 'v2': med(x2)},
                                 'starterRankChange': {'median': float(np.median(moved)), 'max': int(moved.max())},
                                 'nonStartersEnteringTop50': passed_starters},
               'top30': [players[i]['name'] for i in np.argsort(r2)[:30]],
               'focus': {players[i]['name']: {'rawRank': int(r0[i]), 'v1Rank': int(r1[i]), 'v2Rank': int(r2[i])} for i in range(n) if players[i]['name'] in FOCUS}}
    (OUT / 'summary-v2.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(OUT / 'ranking-v2.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'rawRank', 'v1Rank', 'playerId', 'name', 'position', 'simMinutes', 'sourceMinutes', 'v2Per36', 'rawPer36', 'shrinkFactor'])
        for i in np.argsort(r2):
            p = players[i]
            wr.writerow([r2[i], r0[i], r1[i], p['playerId'], p['name'], p['pos'], round(p['m'], 2), round(p['W']), round(float(x2[i]), 3), round(float(x[i]), 3), round(float(B2[i]), 3)])
    print(json.dumps({k: summary[k] for k in ['gates', 'G1splitHalfPrediction', 'G2externalRAPM', 'G3bench', 'G4starterOrder', 'supplementary', 'top30', 'focus']}, ensure_ascii=True, indent=1))


if __name__ == '__main__':
    main()
