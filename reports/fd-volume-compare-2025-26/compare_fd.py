"""製造犯規（FD）定義比較：探索性、事後（使用者看到 SGA 排名才提出），不作採用依據（R-007、L-026）。

候選（都取池內百分位，池 = GP>=30 且 MPG>=20，和卡片相同；1–99 封頂）：
  rate = FTA/FGA（現行卡片的原始定義，未做 v61 歷史拉回）
  vol  = FTA/36
  mix  = 0.5·z(rate) + 0.5·z(vol)（z 用池內平均／標準差）
看三件事：
  1. 排行：前 15 名、SGA 等人名次、候選之間的 Spearman。
  2. 穩定度：2024-25 對 2025-26 同一定義的相關（兩季都在池內的人）。
  3. 價值（半樣本外）：FD 只用一半比賽算（A = gameId 偶數、B = 奇數，和 RAPM 分半同切法），
     答案 = 另一半 RAPM pooledNet（ovr-v58-holdout-2025-26/rapm-{A,B}.csv），人群 pooledPoss>=2500 且在池內。
     OLS：答案 ~ card 0.2.0 其他 14 個屬性 + FD 候選；報 FD 係數（每 10 點）、SE、t、相對於「不放 FD」的 ΔR²。
     注意：其他屬性是全季卡片值（對答案半是樣本內），三個候選共用，所以只比候選之間的差。
用法：python -I reports/fd-volume-compare-2025-26/compare_fd.py → results.json、report.md
"""
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GAMES = ROOT / 'data/season-source/player-games.json'
HIST = ROOT / 'reports/ovr-v61-shrink-history-2025-26/history/pergame-2024-25.csv.gz'
CARD = ROOT / 'reports/card-0.2.0/ranking.csv'
PRED = ROOT / 'reports/card-0.1.2+E064-pergame/primary/pred.csv'
RAPM = ROOT / 'reports/ovr-v58-holdout-2025-26'
POOL_GP, POOL_MPG, THR = 30, 20, 2500
OTHER = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina',
         'creation', 'pressure']
CANDS = ['rate', 'vol', 'mix']
WATCH = ['Shai Gilgeous-Alexander', 'Giannis Antetokounmpo', 'Luka Dončić', 'Joel Embiid', 'Jalen Brunson', 'Rudy Gobert',
         'Steven Adams', 'Dwight Powell', 'James Harden', 'Trae Young']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def season_2526():
    rs = json.loads(GAMES.read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(rs['headers'])}
    acc = {k: defaultdict(lambda: [0, 0.0, 0, 0]) for k in ('full', 'A', 'B')}   # gp, min, fta, fga
    for r in rs['rowSet']:
        if r[h['MIN']] is None:
            continue
        half = 'A' if int(r[h['GAME_ID']]) % 2 == 0 else 'B'
        for k in ('full', half):
            a = acc[k][r[h['PLAYER_ID']]]
            a[0] += 1; a[1] += r[h['MIN']]; a[2] += r[h['FTA']]; a[3] += r[h['FGA']]
    return acc


def season_2425():
    acc = defaultdict(lambda: [0, 0.0, 0, 0])
    with gzip.open(HIST, 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            a = acc[int(r['playerId'])]
            a[0] += 1; a[1] += float(r['MIN']); a[2] += int(r['FTA']); a[3] += int(r['FGA'])
    return acc


def candidates(acc, pool_ids):
    """回傳 {cand: {pid: 百分位}}；池外的人也對池內分布取百分位。"""
    ids = [p for p, a in acc.items() if a[3] > 0 and a[1] > 0]
    raw = {'rate': {p: acc[p][2] / acc[p][3] for p in ids}, 'vol': {p: 36 * acc[p][2] / acc[p][1] for p in ids}}
    pool = [p for p in pool_ids if p in raw['rate']]
    z = {}
    for c in ('rate', 'vol'):
        v = np.array([raw[c][p] for p in pool]); mu, sd = v.mean(), v.std()
        z[c] = {p: (raw[c][p] - mu) / sd for p in ids}
    raw['mix'] = {p: 0.5 * z['rate'][p] + 0.5 * z['vol'][p] for p in ids}
    out = {}
    for c in CANDS:
        ref = np.sort([raw[c][p] for p in pool])
        out[c] = {p: float(np.clip(100 * np.searchsorted(ref, raw[c][p], side='right') / len(ref), 1, 99)) for p in ids}
    return out, raw


def pool_of(acc):
    return {p for p, a in acc.items() if a[0] >= POOL_GP and a[1] / a[0] >= POOL_MPG}


def ols(X, y):
    X1 = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    res = y - X1 @ b
    s2 = res @ res / (len(y) - X1.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X1.T @ X1)))
    r2 = 1 - res @ res / ((y - y.mean()) @ (y - y.mean()))
    return b, se, r2


def main():
    acc = season_2526()
    pool = pool_of(acc['full'])
    pid = {r['name']: int(r['playerId']) for r in csv.DictReader(open(PRED, encoding='utf-8'))}
    name = {v: k for k, v in pid.items()}
    card = {r['name']: r for r in csv.DictReader(open(CARD, encoding='utf-8'))}
    full, raw = candidates(acc['full'], pool)
    out = {'sources': {str(p.relative_to(ROOT)): sha(p) for p in (GAMES, HIST, CARD, PRED, RAPM / 'rapm-A.csv', RAPM / 'rapm-B.csv')},
           'poolN': len(pool), 'note': '探索性、事後，不作採用依據'}

    # 1. 排行（只排卡片上的人，和網站一致）
    on_card = [pid[n] for n in card if n in pid and pid[n] in full['rate']]
    rank = {}
    for c in CANDS:
        order = sorted(on_card, key=lambda p: (-full[c][p], -raw[c][p]))
        rank[c] = {p: i + 1 for i, p in enumerate(order)}
        out[f'top15_{c}'] = [(name[p], round(full[c][p], 1), round(raw['rate'][p], 3), round(raw['vol'][p], 1)) for p in order[:15]]
    out['watch'] = {n: {c: {'pct': round(full[c][pid[n]], 1), 'rank': rank[c][pid[n]]} for c in CANDS}
                    | {'FTA/FGA': round(raw['rate'][pid[n]], 3), 'FTA/36': round(raw['vol'][pid[n]], 1),
                       'cardFoulDraw': float(card[n]['foulDraw'])}
                    for n in WATCH if n in pid and pid[n] in full['rate'] and n in card}
    pl = [p for p in on_card if p in pool]
    out['spearmanInPool'] = {f'{a}~{b}': round(float(spearmanr([full[a][p] for p in pl], [full[b][p] for p in pl])[0]), 3)
                             for a, b in (('rate', 'vol'), ('rate', 'mix'), ('vol', 'mix'))}
    out['spearmanCardFoulDraw'] = {c: round(float(spearmanr([full[c][p] for p in pl], [float(card[name[p]]['foulDraw']) for p in pl])[0]), 3)
                                   for c in CANDS}

    # 2. 穩定度
    prev = season_2425()
    pprev = pool_of(prev)
    prevc, prevraw = candidates(prev, pprev)
    both = sorted(pool & pprev)
    out['stability'] = {'n': len(both)} | {c: {'pearsonRaw': round(float(np.corrcoef([prevraw[c][p] for p in both], [raw[c][p] for p in both])[0, 1]), 3),
                                               'spearman': round(float(spearmanr([prevc[c][p] for p in both], [full[c][p] for p in both])[0]), 3)}
                                           for c in CANDS}

    # 3. 價值（FD 用一半，答案用另一半）
    halves = {h: candidates(acc[h], pool)[0] for h in 'AB'}
    val = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        rap = {int(r['playerId']): r for r in csv.DictReader(open(RAPM / f'rapm-{ev}.csv', encoding='utf-8-sig')) if r['playerId']}
        ppl = sorted(p for p in pool if p in rap and float(rap[p]['pooledPoss']) >= THR and p in name and name[p] in card
                     and all(p in halves[fit][c] for c in CANDS))
        y = np.array([float(rap[p]['pooledNet']) for p in ppl])
        Xo = np.array([[float(card[name[p]][a]) for a in OTHER] for p in ppl]) / 10
        _, _, r2_0 = ols(Xo, y)
        d = {'n': len(ppl), 'r2_noFD': round(r2_0, 4)}
        for c in CANDS + ['cardFoulDraw']:
            fd = np.array([float(card[name[p]]['foulDraw']) if c == 'cardFoulDraw' else halves[fit][c][p] for p in ppl]) / 10
            b, se, r2 = ols(np.column_stack([Xo, fd]), y)
            d[c] = {'coefPer10': round(float(b[-1]), 4), 'se': round(float(se[-1]), 4), 't': round(float(b[-1] / se[-1]), 2),
                    'dR2': round(r2 - r2_0, 4)}
        val[f'FD{fit}->RAPM{ev}'] = d
    out['value'] = val
    out['valueNote'] = 'cardFoulDraw 是全季卡片值（對答案半樣本內），只作參考；rate/vol/mix 只用另一半比賽。'
    (HERE / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
