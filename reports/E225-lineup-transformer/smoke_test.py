"""E-225 管線 smoke test（第一版兩臂 T-min／T-nomin）：極小 Transformer、CPU、幾個 epoch，只確認管線通、驗證損失會下降。
只用 2023-24 的 split=train（folds 1-4 訓練、fold 0 驗證）；不讀 test／前向季（e225_common 會擋）。不寫任何準度結論。
用法：python -I -X utf8 reports/E225-lineup-transformer/smoke_test.py
"""
import json, os, sys, time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_common import HERE, load_rows
from e225_model import ARMS, LineupNet, loss_fn, sigma2_of, tensors

SEASON = '2023-24'
torch.manual_seed(0); np.random.seed(0)


def main():
    t0 = time.time()
    rows = load_rows([SEASON])
    tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
    means = {SEASON: sum(r['ptsa'] + r['ptsb'] for r in tr) / sum(r['possa'] + r['possb'] for r in tr)}
    s2 = sigma2_of(tr, means)
    out = {'season': SEASON, 'trainStints': len(tr), 'valStints': len(va), 'arms': {}}
    for arm, use_min in ARMS.items():
        Tt, Tv = tensors(tr, use_min, means), tensors(va, use_min, means)
        # 位置索引必須 0-4 且每邊五個位置各一（推定規則的性質）
        assert Tt[1].max() <= 4 and (Tt[1][:, :5].sort(1).values == torch.arange(5)).all()
        net = LineupNet(Tt[0].shape[-1] // 2, d=32, layers=1, heads=2, ff=64); opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-2)
        hist = []
        with torch.no_grad():
            net.eval(); hist.append(round(loss_fn(net(*Tv[:3]), Tv[3], s2)[0].item(), 4))
        for ep in range(5):
            net.train(); perm = torch.randperm(len(Tt[0]))
            for b in range(0, len(perm), 512):
                ix = perm[b:b + 512]
                loss, _ = loss_fn(net(*(t[ix] for t in Tt[:3])), Tt[3][ix], s2)
                opt.zero_grad(); loss.backward(); opt.step()
            with torch.no_grad():
                net.eval(); hist.append(round(loss_fn(net(*Tv[:3]), Tv[3], s2)[0].item(), 4))
        out['arms'][arm] = {'featDim': Tt[0].shape[-1] // 2, 'params': sum(p.numel() for p in net.parameters()), 'valLoss': hist, 'decreased': hist[-1] < hist[0]}
        print(arm, hist, flush=True)
    out['seconds'] = round(time.time() - t0, 1); out['note'] = '只確認管線；不是準度結論。test／前向季未讀。'
    json.dump(out, open(os.path.join(HERE, 'smoke-test.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('pipeline ok' if all(v['decreased'] for v in out['arms'].values()) else 'WARN: val loss not decreasing')


if __name__ == '__main__':
    main()
