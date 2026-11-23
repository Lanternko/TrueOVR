"""E-309 區域威懾特徵：四因子 RAPM 的 rimShare／threeShare 防守係數（同 reports/impact-rapm/four-factors.py 設計：
每個 stint 一側＝五攻＋五守、以 fga 加權、ridge），λ 固定 300（four-factors 2022-26 五折 CV 選出的值，不再重選）。
正值＝更好的防守（對手禁區出手佔比更低／三分佔比更低）。單位：百分點（對手出手中禁區佔比）。

視窗（四季滑動、含當季，L-117）：
  T 特徵  season s ∈ 2022-23..2025-26：max(2022-23, s-3)..s，排除 E-225 測試雜湊場次（不外洩測試集）；2021-22 無分區 stints → 遮罩。
  sim     2025-26＋2026-27（全場次；不和 2022-25 RAPM 答案重疊）。
  live    2023-24..2026-27（全場次；顯示欄用）。
  card-2025-26  2022-23..2025-26（全場次；(c) 2025-26 卡片頁第二季）。

  python -I -X utf8 build_rimdet.py   （DATA_ROOT 預設主 checkout）
輸出 data/rimdet-<窗>.csv：pid, rimDet, threeDet, fgaW（防守 fga 權重）, seasons
"""
import csv, hashlib, json, os, sys
import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.environ.get('DATA_ROOT', 'D:/Projects/CODING/basketball-autochess')
LAM = 300.0
ALL = ['2022-23', '2023-24', '2024-25', '2025-26', '2026-27']


def stint_path(s):
    return os.path.join(DATA_ROOT, 'reports/defense-b1/stints.jsonl' if s == '2025-26' else f'reports/defense-seventh/{s}/stints/stints.jsonl')


def hmod(tag, gid, m):
    return int(hashlib.sha256(f'E225|{tag}|{gid}'.encode()).hexdigest()[:8], 16) % m


_CACHE = {}


def season_sides(s):
    if s in _CACHE:
        return _CACHE[s]
    out = []
    for line in open(stint_path(s), encoding='utf-8'):
        st = json.loads(line)
        if st['seconds'] <= 0 or len(st['teams']) != 2:
            continue
        for d in (0, 1):
            de, of = st['teams'][d], st['teams'][1 - d]
            o = de['opponent']
            if de['defensivePossessions'] > 0 and o.get('fga', 0) > 0:
                out.append((st['id'], of['players'], de['players'], o['fga'], o['shortA'], o['longA']))
    _CACHE[s] = out
    return out


def fit(seasons, drop_test):
    rows = [r for s in seasons for r in season_sides(s) if not (drop_test and hmod('test', r[0], 100) < 20)]
    players = sorted({p for r in rows for p in r[1] + r[2]}); ix = {p: i for i, p in enumerate(players)}; P = len(players); K = 2 * P
    ri, ci = [], []
    for n, r in enumerate(rows):
        cols = [K] + [ix[p] for p in r[1]] + [P + ix[p] for p in r[2]]
        ri += [n] * len(cols); ci += cols
    X = sp.csr_matrix((np.ones(len(ri)), (ri, ci)), shape=(len(rows), K + 1))
    w = np.array([r[3] for r in rows], float)
    A = (X.T @ sp.diags(w) @ X).toarray(); pen = LAM * np.eye(K + 1); pen[K, K] = 0
    res = {}
    for name, col in (('rimDet', 4), ('threeDet', 5)):
        y = 100 * np.array([r[col] for r in rows], float) / w
        b = np.linalg.solve(A + pen, X.T @ (w * y))
        res[name] = -b[P:K]   # sign −1：佔比越低越好
        res[name + '_intercept'] = float(b[K])
    fgaW = np.asarray(A.diagonal())[P:K]
    return players, res, fgaW, len(rows)


def write(tag, seasons, drop_test, info):
    players, res, fgaW, n = fit(seasons, drop_test)
    os.makedirs(os.path.join(HERE, 'data'), exist_ok=True)
    with open(os.path.join(HERE, 'data', f'rimdet-{tag}.csv'), 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f); wr.writerow(['pid', 'rimDet', 'threeDet', 'fgaW'])
        for i, p in enumerate(players):
            wr.writerow([p, round(float(res['rimDet'][i]), 4), round(float(res['threeDet'][i]), 4), round(float(fgaW[i]))])
    info[tag] = {'seasons': seasons, 'dropTest': drop_test, 'sides': n, 'players': len(players),
                 'rimIntercept': res['rimDet_intercept'], 'threeIntercept': res['threeDet_intercept'],
                 'sdRimDet_fgaW>=2500': float(np.std(res['rimDet'][fgaW >= 2500]))}
    print(tag, json.dumps(info[tag]), flush=True)


def main():
    info = {}
    for s in ALL[:4]:
        i = ALL.index(s)
        write(f'T-{s}', ALL[max(0, i - 3):i + 1], True, info)
    write('sim', ['2025-26', '2026-27'], False, info)
    write('live', ALL[1:5], False, info)
    write('card-2025-26', ALL[0:4], False, info)   # (c) 2025-26 卡片頁第二季
    json.dump({'lambda': LAM, 'dataRoot': DATA_ROOT, 'windows': info}, open(os.path.join(HERE, 'data', 'rimdet-info.json'), 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
