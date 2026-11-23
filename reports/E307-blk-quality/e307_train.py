"""E-307 訓練：同 E-285（E-227 R2-stats 架構與超參數 lr 0.001、wd 0.1；2021-22～2025-26 split=train；folds 1-4 訓練、fold 0 早停）。
五臂同環境重訓（G3）：T0／TE／TG／TV／TX，seed 0–4。每個 seed 約 15 秒，跑完存權重；重跑同指令會跳過已存權重（可斷點續跑）。
  python -I -X utf8 e307_train.py --arm TE --seeds 0,1,2,3,4
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import x_lib as X  # noqa: E402  先 patch e227_model
import torch  # noqa: E402
from e227_common import SEASONS, load_rows  # noqa: E402
from e227_model import run, season_means, sigma2_of, tensors  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--arm', required=True, choices=list(X.ARMS)); ap.add_argument('--seeds', default='0,1,2,3,4'); a = ap.parse_args()
cfg = json.load(open(os.path.join(X.SRC, 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True)
todo = [sd for sd in map(int, a.seeds.split(',')) if not os.path.exists(os.path.join(out, 'weights', f'{a.arm}-{sd}.pt'))]
if not todo:
    print(a.arm, 'all seeds done'); sys.exit(0)
rows = load_rows(SEASONS); tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
means = season_means(tr); s2 = sigma2_of(tr, means); kind = X.ARMS[a.arm]
Tt, Tv = tensors(tr, kind, means, 'train'), tensors(va, kind, means, 'val')
print('rows', len(rows), 'train', len(tr), 'val', len(va), 'feat', Tt[0].shape[-1] // 2, 'cfg', cfg, 'dev', dev, flush=True)
for sd in todo:
    res, pred, state = run(a.arm, cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
    json.dump(res, open(os.path.join(out, f'final-{a.arm}-{sd}.json'), 'w'))
    torch.save(state, os.path.join(out, 'weights', f'{a.arm}-{sd}.pt')); print(a.arm, sd, res['valLoss'], res['bestEpoch'], res['seconds'], flush=True)
