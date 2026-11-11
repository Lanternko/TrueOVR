"""v55 修正 B：在 8 顆種子的 expected-margin 板上做經驗貝式可靠度收縮。

  python reports/ovr-v55-finisher-fix-2025-26/shrink.py <variant>   # v54 | B1 | B2 | B12 | B12_oos

估計式與 reports/ovr-v54-shrinkage-2025-26/shrink.py 逐行相同（同一個 per-36 位置中心化、
同一個對手分層蒙地卡羅變異、同一個 kappa/W 來源雜訊、同一個 log 每場分鐘角色先驗）；唯一差別
是輸入板換成本目錄的 <variant>/checkpoint-both-s8.jsonl。variant='v54' 直接讀 v54 的凍結板
（reports/ovr-v54-2025-26/checkpoint-both-s8.jsonl），這樣基準線與新變體是**同一支腳本、同一
個口徑**算出來的，不是從報告抄來的數字。
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
# 任務點名的下修對象、不誤傷對象，加上持球創造對照組。
FOCUS = ['Karlo Matković', 'Charles Bassey', 'Jaxson Hayes', 'John Collins', 'Isaiah Stewart', 'Luka Garza',
         'Jordan Walsh', 'Josh Minott',
         'Neemias Queta', 'Rudy Gobert', 'Jalen Smith', 'Robert Williams III',
         'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Luka Dončić', 'Trae Young', 'Victor Wembanyama']

BOARDS = {'v54': ROOT / 'reports/ovr-v54-2025-26/checkpoint-both-s8.jsonl',
          'v53': ROOT / 'reports/ovr-v53-2025-26/checkpoint-both-s8.jsonl'}


def board_file(variant):
    return BOARDS.get(variant, OUT / variant / 'checkpoint-both-s8.jsonl')


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


def load(variant):
    comp = {r['name']: r for r in csv.DictReader(open(V47 / 'comparison.csv', encoding='utf-8-sig'))}
    ids = {int(r['playerId']): r for r in csv.DictReader(open(V47 / 'ranking.csv', encoding='utf-8-sig'))}
    work = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/player-impact-v29/2025-26-all-player-workload.csv', encoding='utf-8-sig'))}
    players = []
    for line in open(board_file(variant), encoding='utf-8'):
        r = json.loads(line); info = ids[r['playerId']]; c = comp[info['name']]
        players.append({'playerId': r['playerId'], 'name': info['name'], 'pos': info['position'], 'm': r['minutes'],
                        'games': int(c['source_games_played']), 'mpg': float(c['source_minutes_per_played_game']),
                        'W': float(c['source_games_played']) * float(c['source_minutes_per_played_game']),
                        'confident': int(work[r['playerId']]['starts']) >= 5, 'draws': r['draws']})
    players.sort(key=lambda p: p['playerId'])
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
    print(json.dumps({'variant': variant, 'board': str(board_file(variant)), 'players': n, 'fit': fit}, indent=1))
