"""E-227 共用常數與載入（R-159）。資料全在本目錄 data/；只含 split=train 的 stint（測試場次與 2026-27 不進此目錄）。
切分規則與 E-225 build_dataset.py 完全相同（sha256('E225|test|'+gid) 前 8 位 mod 100 < 20 → test；sha256('E225|fold|'+gid) 前 8 位 mod 5 → fold）。"""
import csv, gzip, math, os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'creation', 'pressure', 'heightInches']
# 統計向量（26 欄），class -> columns
STAT_CLASSES = {
    'hustle': ['deflections36', 'cont2pt36', 'cont3pt36', 'charges36', 'looseO36', 'looseD36', 'boxoutO36', 'boxoutD36', 'screenAst36'],
    'rimthree': ['rimDiff', 'rimFGA36', 'threeDiff', 'threeFGA36'],
    'matchup': ['oppPtsPerPoss', 'oppFGpct'],
    'box': ['stl36', 'blk36', 'pf36', 'oreb36', 'dreb36'],
    'adv': ['usg', 'astPct', 'ts', 'orebPct', 'drebPct', 'tovPct'],
}
STATS = [c for cl in STAT_CLASSES.values() for c in cl]
MIN_MINUTES = 200
POS_N = 5
ARMS = {'R2-abil': 'abil', 'R2-stats': 'stats', 'R2-stats-rapm': 'stats-rapm'}
RAPM_LAMBDA = 3000.0


def arm_cols(kind):
    """回傳這個臂用到的特徵欄：('attr'|'stat'|'rapm', name)"""
    cols = [('attr', a) for a in ATTRS]
    if kind in ('stats', 'stats-rapm'):
        cols += [('stat', s) for s in STATS]
    if kind == 'stats-rapm':
        cols += [('rapm', 'off'), ('rapm', 'def')]
    return cols


def _z(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 10 or np.std(v) < 1e-9:
        return None
    return float(np.mean(v)), float(np.std(v))


def load_player_table(season):
    """pid(str) -> {col: float|None}（能力值＋統計；<200 分鐘的統計為 None）。z 分數在 build_players 時不算，這裡回原值。"""
    out = {}
    with open(os.path.join(DATA, f'players-{season}.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out[r['pid']] = {k: (float(v) if v not in ('', None) else None) for k, v in r.items() if k not in ('pid', 'name', 'pos')}
    with open(os.path.join(DATA, f'stats-{season}.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            d = out.setdefault(r['pid'], {})
            for k, v in r.items():
                if k not in ('pid', 'name'):
                    d[k] = float(v) if v not in ('', None) else None
    return out


def load_rapm(season, excl):
    """excl: 排除的 folds 字串（如 '0'、'0-3'、'none'）。回傳 pid -> (off, def, mask)，已除以該次擬合的標準差。"""
    fn = os.path.join(DATA, f'rapm-{season}-excl{excl}.csv')
    out = {}
    with open(fn, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out[r['pid']] = (float(r['off']), float(r['def']), float(r['exposed']))
    return out


def load_rows(seasons=SEASONS):
    out = []
    for s in seasons:
        with gzip.open(os.path.join(DATA, f'stints-train-{s}.csv.gz'), 'rt', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                assert r['split'] == 'train'
                for k in list(r):
                    if k.startswith(('poss', 'pts', 'fga', 'fgm', 'fg3', 'ftm', 'fta', 'tov', 'orb', 'drb', 'rebOpp', 'sec')):
                        r[k] = float(r[k]) if r[k] != '' else math.nan
                r['fold'] = int(r['fold'])
                for k in [f'p{x}{j}' for x in 'ab' for j in range(5)]:
                    r[k] = int(r[k])
                out.append(r)
    return out
