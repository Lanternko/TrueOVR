"""E-285 訓練：E-227 R2-stats 同架構、同超參數（tuning.json R2-stats：lr 0.001、wd 0.1）、同資料（2021-22～2025-26 split=train；folds 1-4 訓練、fold 0 早停）。
兩臂同一環境重訓（G3）：R2-stats（基準）、R2-statsX（＋mtov36、fOn36、fOff36、fGen36）。5 seed。
  python -I -X utf8 e285_train.py --arm R2-statsX --seeds 0,1,2,3,4
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import x_lib as X  # noqa: E402  先 patch e227_model
import numpy as np, torch  # noqa: E402
from e227_common import SEASONS, load_rows  # noqa: E402
from e227_model import run, season_means, sigma2_of, tensors  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--arm', required=True, choices=list(X.ARMS)); ap.add_argument('--seeds', default='0,1,2,3,4'); a = ap.parse_args()
cfg = json.load(open(os.path.join(X.SRC, 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
rows = load_rows(SEASONS); tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
means = season_means(tr); s2 = sigma2_of(tr, means); kind = X.ARMS[a.arm]
Tt, Tv = tensors(tr, kind, means, 'train'), tensors(va, kind, means, 'val')
print('rows', len(rows), 'train', len(tr), 'val', len(va), 'feat', Tt[0].shape[-1] // 2, 'cfg', cfg, 'dev', dev, flush=True)
out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True)
for sd in map(int, a.seeds.split(',')):
    res, pred, state = run(a.arm, cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
    json.dump(res, open(os.path.join(out, f'final-{a.arm}-{sd}.json'), 'w'))
    torch.save(state, os.path.join(out, 'weights', f'{a.arm}-{sd}.pt')); print(a.arm, sd, res['valLoss'], res['bestEpoch'], res['seconds'], flush=True)
