"""card／inseason 0.3.0（E-310，使用者 2026-11-23「採用並上線」）：OVR 的每 36 預測再往四季 RAPM 拉 30%。

pred' ＝ pred ＋ W·s·(r − pred)，s ＝ P/(P＋K)；pred＝屬性迴歸＋防守加成＋align、H1 封頂之後的值（封頂不管這一項）。
r ＝ 0.75 × 無先驗四季 RAPM 淨值（2022-23～2025-26，reports/impact-rapm/rapm.py fit_rapm，λ＝3000）− 同位置平均
（card 0.2.15 pos；平均用 card MIN 加權，只算回合 ≥1000 的人），P＝同一擬合的回合（攻＋守）。回合 <1000、不在 card 0.2.15 的人
（新秀、復出老將）不動。r、P 凍結在 e310-r4-card030.json（整季不更新，同 E-310 樣本外驗收用的 r4）。

用法：python -I -X utf8 reports/ovr-inseason-2026-27/live/e310_live.py freeze   （從 reports/E310-rapm-residual-ovr/fits.json 產凍結檔）
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FROZEN = HERE / 'e310-r4-card030.json'
E310 = ROOT / 'reports/E310-rapm-residual-ovr'
W, K, MIN_POSS, FACTOR = 0.3, 30000.0, 1000.0, 0.75
_T = None


def table():
    global _T
    if _T is None:
        doc = json.loads(FROZEN.read_text(encoding='utf-8'))
        c = doc['config']
        assert (c['w'], c['k'], c['minPoss'], c['factor']) == (W, K, MIN_POSS, FACTOR), c
        _T = {int(p): v for p, v in doc['players'].items()}
    return _T


def delta(pid, pred):
    """要加到 pred 的量（不在表內＝0）。"""
    v = table().get(pid)
    if v is None:
        return 0.0
    return W * v['P'] / (v['P'] + K) * (v['r'] - pred)


def freeze():
    fits = json.loads((E310 / 'fits.json').read_text(encoding='utf-8'))
    r4 = {int(p): v for p, v in fits['r4']['players'].items()}
    card = list(csv.DictReader(open(E310 / 'players.csv', encoding='utf-8')))   # playerId／pos／MIN＝card 0.2.15（e310_run.py 對名）
    mu = {}
    for pos in {c['pos'] for c in card}:
        pool = [c for c in card if c['pos'] == pos and int(c['playerId']) in r4 and r4[int(c['playerId'])]['poss'] >= MIN_POSS]
        mu[pos] = sum(float(c['MIN']) * FACTOR * r4[int(c['playerId'])]['net'] for c in pool) / sum(float(c['MIN']) for c in pool)
    players = {}
    for c in card:
        p = int(c['playerId'])
        if p in r4 and r4[p]['poss'] >= MIN_POSS:
            players[str(p)] = {'name': c['name'], 'pos': c['pos'], 'r': FACTOR * r4[p]['net'] - mu[c['pos']], 'P': float(r4[p]['poss'])}
            if c['r4']:
                assert abs(players[str(p)]['r'] - float(c['r4'])) < 6e-4, (c['name'], players[str(p)]['r'], c['r4'])
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    doc = {'version': 'card／inseason 0.3.0（E-310）',
           'config': {'w': W, 'k': K, 'minPoss': MIN_POSS, 'factor': FACTOR, 'lambda': fits['r4']['lambda'],
                      'seasons': ['2022-23', '2023-24', '2024-25', '2025-26']},
           'posMean': mu,
           'source': {'fits.json': sha(E310 / 'fits.json'), 'players.csv': sha(E310 / 'players.csv')},
           'players': players}
    FROZEN.write_text(json.dumps(doc, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'{len(players)} 人寫入 {FROZEN.name}；posMean', {k: round(v, 4) for k, v in mu.items()})


if __name__ == '__main__' and sys.argv[1:] == ['freeze']:
    sys.stdout.reconfigure(encoding='utf-8')
    freeze()
