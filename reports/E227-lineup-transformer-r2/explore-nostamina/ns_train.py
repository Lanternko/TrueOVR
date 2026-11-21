"""訓練 R2-stats-nost（同 e227_tune.py 的 final 模式；超參數取 tuning.json 的 R2-stats；folds 1-4 訓練、fold 0 驗證早停）。
  python ns_train.py --arm R2-stats-nost --seeds 0,1,2,3,4
  python ns_train.py --arm R2-stats-check --seeds 0     # 完整 R2-stats 重訓一個 seed，檢查管線可重現（對 results/final-R2-stats-0.json 的 valLoss 2.00596）
"""
import argparse, json, os

import numpy as np
import torch

from ns_common import HERE, KIND, SEASONS, SRC, strip
from e227_common import ARMS
from e227_model import run, season_means, sigma2_of, tensors
from e227_common import load_rows

ap = argparse.ArgumentParser(); ap.add_argument('--arm', default='R2-stats-nost'); ap.add_argument('--seeds', default='0,1,2,3,4'); a = ap.parse_args()
cfg = json.load(open(os.path.join(os.path.dirname(HERE), 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
rows = load_rows(SEASONS); tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
means = season_means(tr); s2 = sigma2_of(tr, means)
Tt, Tv = tensors(tr, KIND, means, 'train'), tensors(va, KIND, means, 'val')
if a.arm == 'R2-stats-nost':
    Tt, Tv = strip(Tt), strip(Tv)
print('features', Tt[0].shape[-1] // 2, 'cfg', cfg, 'dev', dev, flush=True)
out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True)
for sd in map(int, a.seeds.split(',')):
    res, pred, state = run(a.arm, cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
    json.dump(res, open(os.path.join(out, f'final-{a.arm}-{sd}.json'), 'w'))
    np.save(os.path.join(out, f'preds-{a.arm}-{sd}.npy'), pred)
    torch.save(state, os.path.join(out, 'weights', f'{a.arm}-{sd}.pt')); print(a.arm, sd, res['valLoss'], res['bestEpoch'], flush=True)
