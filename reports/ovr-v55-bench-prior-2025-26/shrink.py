"""Empirical-Bayes reliability shrinkage on a v55 eight-seed expected-margin board.

  python reports/ovr-v55-bench-prior-2025-26/shrink.py <variant>   # variant in A|C|AC|AC_oos

Identical estimator to reports/ovr-v54-shrinkage-2025-26/shrink.py; only the input board changes
(reports/ovr-v55-bench-prior-2025-26/<variant>/checkpoint-both-s8.jsonl instead of v54's, i.e. v53
engine + one of v55's four shooting-card variants instead of v54's reliability-aware cards).

Per 36 simulated minutes: x = position-centered contribution, Monte Carlo variance from the draws
(stratified by opponent), source small-sample noise kappa / W, role prior on log minutes per game.
"""
import csv, json, math, statistics as st, sys, unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
V47 = ROOT / 'reports/ovr-v47-2025-26'
EXPECTED = 5
SMALL_W, TOP, EVAL_POSS, LOW_POSS = 500, 50, 5000, 1000
FOCUS = ['Tosan Evbuomwan', 'Thanasis Antetokounmpo', 'Caleb Houstan', 'Jonathan Mogbo', 'Charles Bassey',
         'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Victor Wembanyama', 'Alex Caruso', 'Derrick White', 'Dyson Daniels',
         'Kevon Looney', 'Karlo Matković', 'David Roddy', 'Jeremy Sochan']


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


def load(variant):
    comp = {r['name']: r for r in csv.DictReader(open(V47 / 'comparison.csv', encoding='utf-8-sig'))}
    ids = {int(r['playerId']): r for r in csv.DictReader(open(V47 / 'ranking.csv', encoding='utf-8-sig'))}
    work = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/player-impact-v29/2025-26-all-player-workload.csv', encoding='utf-8-sig'))}
    players = []
    cf = OUT / variant / 'checkpoint-both-s8.jsonl'
    for line in open(cf, encoding='utf-8'):
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


if __name__ == '__main__':
    variant = sys.argv[1]
    players = load(variant); n = len(players)
    x, mc = board(players, set(range(8)))
    xs, B, fit = shrink(players, x, mc)
    print(json.dumps({'variant': variant, 'players': n, 'fit': fit}, indent=1))
