"""E-227 訓練 stint RAPM（嚴格只用 split=train）：單季、脊迴歸 λ=3000、進攻欄＋防守欄、權重＝回合數、目標＝每回合得分減該季平均。
防洩漏設計：
  key '0'    ：排除 fold 0 → 供「fold 0 驗證列」的特徵（驗證列的結果沒進這份擬合）。
  key '0-k'  ：排除 fold 0 與 fold k（k=1..4）→ 供「訓練列在 fold k」的特徵（out-of-fold，自己的場次沒進擬合；fold 0 完全不碰）。
  key 'none' ：全部 train；key 'k'（k=0..4）：只排除 fold k（保留給凍結後的最終訓練用，調參階段不使用）。
輸出每個 key：data/rapm-<季>-excl<key>.csv（pid, off, def, exposed）；off／def 除以該次擬合曝光球員係數的標準差（>0 代表進攻愈強／防守端對手得分愈多＝防守愈差，原符號不翻）。
測試場次從未寫入 data/，因此 test stint 不可能進入擬合。"""
import csv, json, os

import numpy as np
import scipy.sparse as sp

from e227_common import DATA, HERE, RAPM_LAMBDA, SEASONS, load_rows


def fit(rows, lam, mean):
    pids = sorted({r[f'{x}{j}'] for r in rows for x in 'ab' for j in range(5)}); ix = {p: i for i, p in enumerate(pids)}; P = len(pids)
    ri, ci, y, w = [], [], [], []; n = 0
    for r in rows:
        for off, de, po, pt in (('a', 'b', r['possa'], r['ptsa']), ('b', 'a', r['possb'], r['ptsb'])):
            if not po > 0:
                continue
            for j in range(5):
                ri += [n, n]; ci += [ix[r[f'{off}{j}']], P + ix[r[f'{de}{j}']]]
            y.append(pt / po - mean); w.append(po); n += 1
    X = sp.csr_matrix((np.ones(len(ri)), (ri, ci)), shape=(n, 2 * P)); y = np.array(y); w = np.array(w)
    A = (X.T @ sp.diags(w) @ X).toarray() + lam * np.eye(2 * P)
    beta = np.linalg.solve(A, X.T @ (w * y))
    expo = np.asarray((X.T @ w[:, None]).ravel() > 0)
    return pids, beta[:P], beta[P:], expo[:P] | expo[P:]


def main():
    rows_all = load_rows(SEASONS); keys = ['none', '0', '1', '2', '3', '4', '0-1', '0-2', '0-3', '0-4']; rep = {}
    for s in SEASONS:
        rows = [r for r in rows_all if r['season'] == s]
        mean = sum(r['ptsa'] + r['ptsb'] for r in rows) / sum(r['possa'] + r['possb'] for r in rows)
        for k in keys:
            ex = set() if k == 'none' else set(int(c) for c in k.split('-'))
            sub = [r for r in rows if r['fold'] not in ex]
            pids, off, de, expo = fit(sub, RAPM_LAMBDA, mean)
            so, sd = off[expo].std(), de[expo].std()
            with open(os.path.join(DATA, f'rapm-{s}-excl{k}.csv'), 'w', encoding='utf-8', newline='') as f:
                w = csv.writer(f, lineterminator='\n'); w.writerow(['pid', 'off', 'def', 'exposed'])
                for p, a, b, e in zip(pids, off, de, expo):
                    w.writerow([p, round(a / so, 6), round(b / sd, 6), int(e)])
            rep[f'{s}|{k}'] = {'stints': len(sub), 'players': int(expo.sum()), 'sdOff': round(float(so), 5), 'sdDef': round(float(sd), 5)}
            print(s, k, rep[f'{s}|{k}'], flush=True)
    json.dump(rep, open(os.path.join(HERE, 'rapm-fits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
