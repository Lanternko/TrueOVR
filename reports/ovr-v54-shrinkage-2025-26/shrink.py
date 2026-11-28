"""Empirical-Bayes reliability shrinkage on the v54 eight-seed expected-margin board.

  python reports/ovr-v54-shrinkage-2025-26/shrink.py

Identical estimator to reports/ovr-v53-shrinkage-2025-26/shrink.py; only the input board changes
(reports/ovr-v54-2025-26/checkpoint-both-s8.jsonl instead of v53's, i.e. v53 engine + v54
reliability-aware long/short cards instead of v53's fixed 100-attempt pseudo-count cards).

Per 36 simulated minutes: x = position-centered contribution, Monte Carlo variance from the draws
(stratified by opponent), source small-sample noise kappa / W, role prior on log minutes per game.
Validated by seed split halves (even / odd seeds): shrink on one half, predict the other.
"""
import csv, json, math, statistics as st, unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
V47 = ROOT / 'reports/ovr-v47-2025-26'
EXPECTED = 5
SMALL_W, TOP, EVAL_POSS, LOW_POSS = 500, 50, 5000, 1000
FOCUS = ['Tosan Evbuomwan', 'Thanasis Antetokounmpo', 'Caleb Houstan', 'Jonathan Mogbo', 'Charles Bassey',
         'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Victor Wembanyama', 'Alex Caruso', 'Derrick White', 'Dyson Daniels']


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


def load():
    comp = {r['name']: r for r in csv.DictReader(open(V47 / 'comparison.csv', encoding='utf-8-sig'))}
    ids = {int(r['playerId']): r for r in csv.DictReader(open(V47 / 'ranking.csv', encoding='utf-8-sig'))}
    work = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/player-impact-v29/2025-26-all-player-workload.csv', encoding='utf-8-sig'))}
    players = []
    for line in open(ROOT / 'reports/ovr-v54-2025-26/checkpoint-both-s8.jsonl', encoding='utf-8'):
        r = json.loads(line); info = ids[r['playerId']]; c = comp[info['name']]
        players.append({'playerId': r['playerId'], 'name': info['name'], 'pos': info['position'], 'm': r['minutes'],
                        'games': int(c['source_games_played']), 'mpg': float(c['source_minutes_per_played_game']),
                        'W': float(c['source_games_played']) * float(c['source_minutes_per_played_game']),
                        'confident': int(work[r['playerId']]['starts']) >= 5, 'draws': r['draws']})
    return players


def board(players, seeds):
    """Position-centered per-36 x and its Monte Carlo variance from the draws with the given seed indices."""
    raw = []
    for p in players:
        by = defaultdict(list)
        for d in p['draws']:
            if d[1] in seeds:
                by[d[0]].append(d[EXPECTED])
        c = st.mean(v for vals in by.values() for v in vals)
        se2 = sum(st.variance(v) / len(v) for v in by.values()) / len(by) ** 2
        raw.append((c, se2))
    x = np.zeros(len(players)); mc = np.zeros(len(players))
    for pos in {p['pos'] for p in players}:
        pool = [i for i, p in enumerate(players) if p['pos'] == pos and p['confident']]
        b = sum(players[i]['W'] * raw[i][0] / players[i]['m'] for i in pool) / sum(players[i]['W'] for i in pool)
        for i, p in enumerate(players):
            if p['pos'] == pos:
                x[i] = (raw[i][0] - b * p['m']) / p['m'] * 36
                mc[i] = raw[i][1] * (36 / p['m']) ** 2
    return x, mc


def wls(xs, ys, ws):
    sw = ws.sum(); mx = (ws * xs).sum() / sw; my = (ws * ys).sum() / sw
    b = (ws * (xs - mx) * (ys - my)).sum() / (ws * (xs - mx) ** 2).sum()
    return my - b * mx, b


def shrink(players, x, mc):
    lmpg = np.log([p['mpg'] for p in players]); W = np.array([p['W'] for p in players])
    a, b = wls(lmpg, x, 1 / mc)
    mu = a + b * lmpg
    w = 1 / mc ** 2
    for _ in range(2):
        tau2, kappa = wls(1 / W, (x - mu) ** 2 - mc, w)
        tau2, kappa = max(tau2, 1e-6), max(kappa, 0.0)
        w = 1 / (tau2 + mc + kappa / W) ** 2
    B = tau2 / (tau2 + mc + kappa / W)
    return mu + B * (x - mu), B, {'priorIntercept': float(a), 'priorLogMinutesPerGameSlope': float(b), 'tau2Per36': float(tau2), 'kappa': float(kappa),
                                  'sourceNoiseEqualsSignalAtMinutes': float(kappa / tau2)}


def media_ranks(players):
    media = json.loads((ROOT / 'reports/model-evolution-20261016/media-ranks.json').read_text(encoding='utf-8'))
    fold = lambda s: ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower().replace('.', '').replace(' iii', '').replace(' jr', '')
    idx = {fold(p['name']): i for i, p in enumerate(players)}
    out = {}
    for p in media['players']:
        i = idx.get(fold(p['name']))
        if i is not None:
            out[i] = st.mean(p['ranks'].get(k, 101) for k in media['selectedMedia'])
    return out


def main():
    players = load(); n = len(players)
    halves = {'even': {0, 2, 4, 6}, 'odd': {1, 3, 5, 7}}
    hb = {h: board(players, s) for h, s in halves.items()}
    # G1: shrink on one half, predict the other half's raw x.
    d_all = np.zeros(n); raw_err = np.zeros(n); shr_err = np.zeros(n); hfits = {}
    for a, b in [('even', 'odd'), ('odd', 'even')]:
        xa, mca = hb[a]; xb, _ = hb[b]
        xs, _, f = shrink(players, xa, mca); hfits[a] = f
        raw_err += (xa - xb) ** 2 / 2; shr_err += (xs - xb) ** 2 / 2
    d_all = raw_err - shr_err
    m = np.array([p['m'] for p in players]); big = m >= 20
    rng = np.random.default_rng(20261018)
    boot = [d_all[rng.integers(0, n, n)].mean() for _ in range(2000)]
    g1 = {'mseRaw': float(raw_err.mean()), 'mseShrunk': float(shr_err.mean()), 'meanReduction': float(d_all.mean()),
          'reductionCI95': [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
          'minutes20Plus': {'players': int(big.sum()), 'mseRaw': float(raw_err[big].mean()), 'mseShrunk': float(shr_err[big].mean()),
                            'meanReduction': float(d_all[big].mean())},
          'minuteWeightedReduction': float((m * d_all).sum() / m.sum()), 'halfFits': hfits}
    g1['passed'] = g1['reductionCI95'][0] > 0 and g1['minutes20Plus']['meanReduction'] >= 0
    # Split-half reliability (Spearman-Brown on the rank correlation of the two halves).
    sb = lambda r: 2 * r / (1 + r)
    xs_e = shrink(players, *hb['even'])[0]; xs_o = shrink(players, *hb['odd'])[0]
    reliability = {'raw': sb(spearman(hb['even'][0], hb['odd'][0])), 'shrunk': sb(spearman(xs_e, xs_o))}
    # Full board.
    x, mc = board(players, set(range(8)))
    xs, B, fit = shrink(players, x, mc)
    rapm = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}
    def ext(min_poss):
        keep = [i for i, p in enumerate(players) if p['playerId'] in rapm and float(rapm[p['playerId']]['pooledPoss']) >= min_poss]
        N = [float(rapm[players[i]['playerId']]['pooledNet']) for i in keep]; D = [float(rapm[players[i]['playerId']]['pooledD']) for i in keep]
        return {'players': len(keep), 'net': {'raw': spearman(x[keep], N), 'shrunk': spearman(xs[keep], N)},
                'defense': {'raw': spearman(x[keep], D), 'shrunk': spearman(xs[keep], D)}}
    g2 = ext(EVAL_POSS)
    g2['passed'] = g2['net']['shrunk'] >= g2['net']['raw'] - 0.01 and g2['defense']['shrunk'] >= g2['defense']['raw'] - 0.01
    rank_raw = np.empty(n, int); rank_raw[np.argsort(-x)] = np.arange(1, n + 1)
    rank_s = np.empty(n, int); rank_s[np.argsort(-xs)] = np.arange(1, n + 1)
    W = np.array([p['W'] for p in players]); small = W < SMALL_W
    g3 = {'smallWInTop50': {'raw': int((small & (rank_raw <= TOP)).sum()), 'shrunk': int((small & (rank_s <= TOP)).sum())},
          'remainingSmallInTop50': [players[i]['name'] for i in np.argsort(rank_s) if small[i] and rank_s[i] <= TOP]}
    g3['passed'] = g3['smallWInTop50']['shrunk'] <= g3['smallWInTop50']['raw'] / 2
    mr = media_ranks(players); mi = sorted(mr)
    summary = {'preregistration': 'preregistration.md', 'players': n, 'fit': fit,
               'G1splitHalfPrediction': g1, 'G2externalRAPM': g2, 'G3bench': g3,
               'gates': {'G1': g1['passed'], 'G2': g2['passed'], 'G3': g3['passed'], 'adopt': g1['passed'] and g2['passed'] and g3['passed']},
               'supplementary': {'rapmPoss1000': ext(LOW_POSS), 'splitHalfReliability': reliability,
                                 'mediaSpearman': {'players': len(mi), 'raw': spearman(-x[mi], [-mr[i] for i in mi]), 'shrunk': spearman(-xs[mi], [-mr[i] for i in mi])},
                                 'medianShrinkFactor': {'simMinutesUnder10': float(np.median(B[m < 10])), 'simMinutes10to20': float(np.median(B[(m >= 10) & (m < 20)])),
                                                        'simMinutes20Plus': float(np.median(B[big]))}},
               'focus': {players[i]['name']: {'rawRank': int(rank_raw[i]), 'shrunkRank': int(rank_s[i]), 'B': round(float(B[i]), 3)}
                         for i in range(n) if players[i]['name'] in FOCUS}}
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    with open(OUT / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['rank', 'rawRank', 'playerId', 'name', 'position', 'simMinutes', 'sourceMinutes', 'shrunkPer36', 'rawPer36', 'shrinkFactor'])
        for i in np.argsort(rank_s):
            p = players[i]
            wr.writerow([rank_s[i], rank_raw[i], p['playerId'], p['name'], p['pos'], round(p['m'], 2), round(p['W']), round(float(xs[i]), 3), round(float(x[i]), 3), round(float(B[i]), 3)])
    print(json.dumps({k: summary[k] for k in ['fit', 'gates', 'G1splitHalfPrediction', 'G2externalRAPM', 'G3bench', 'supplementary', 'focus']}, ensure_ascii=True, indent=1))


if __name__ == '__main__':
    main()
