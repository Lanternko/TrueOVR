"""E-225 共用載入：讀 build_dataset.py 的輸出。預設只准讀 split=train（L-026：測試場次與前向季凍結前不准碰）。"""
import csv, gzip, math, os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'creation', 'pressure', 'heightInches']
FEATS = ATTRS + ['mpg']   # 第一版（R-157）：15 項能力值＋本季每場上場時間；不放 OVR、不放球員 ID。T-nomin 臂丟掉最後一欄（mpg）
TRAIN_SEASONS = ['2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24', '2024-25']
FORWARD = {'2025-26', '2026-27'}
POS = {'PG': 0, 'SG': 1, 'SF': 2, 'PF': 3, 'C': 4}


def load_players(season, use_min=True):
    """pid -> (z 分數特徵, 遮罩, 卡片位置 0-4/5)；use_min=False 時沒有 mpg 欄（15 維），否則 16 維。季內 z 分數；整季常數（例：2021-22 以前 onBall/help）視為缺值。"""
    fn = os.path.join(DATA, f'players-{season}.csv')
    if not os.path.exists(fn):
        return {}
    rows = list(csv.DictReader(open(fn, encoding='utf-8')))
    feats = FEATS if use_min else ATTRS
    out = {r['pid']: [np.zeros(len(feats), np.float32), np.zeros(len(feats), np.float32), POS.get(r['pos'].split('-')[0], 5)] for r in rows}
    for k, f in enumerate(feats):
        v = [float(r[f]) for r in rows if r[f] not in ('', None)]
        if len(v) < 10 or np.std(v) < 1e-6:
            continue
        mu, sd = float(np.mean(v)), float(np.std(v))
        for r in rows:
            if r[f] not in ('', None):
                out[r['pid']][0][k] = (float(r[f]) - mu) / sd
                out[r['pid']][1][k] = 1.0
    return out


def load_rows(seasons, splits=('train',), allow_holdout=False):
    """回傳 list of dict（字串欄位原樣，數值轉 float）。allow_holdout=False 時拒讀 test／forward。"""
    if not allow_holdout:
        assert set(splits) <= {'train'}, 'E-225：凍結前不准讀 test／forward（L-026）'
        assert not (set(seasons) & FORWARD), 'E-225：2025-26／2026-27 為前向測試季，凍結前不准讀'
    out = []
    for s in seasons:
        with gzip.open(os.path.join(DATA, f'stints-{s}.csv.gz'), 'rt', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r['split'] not in splits:
                    continue
                for k in list(r):
                    if k.startswith(('poss', 'pts', 'fga', 'fgm', 'fg3', 'ftm', 'fta', 'tov', 'orb', 'drb', 'rebOpp', 'sec')):
                        r[k] = float(r[k]) if r[k] != '' else math.nan
                r['fold'] = int(r['fold'])
                for k in [f'p{x}{j}' for x in 'ab' for j in range(5)]:
                    r[k] = int(r[k])
                out.append(r)
    return out
