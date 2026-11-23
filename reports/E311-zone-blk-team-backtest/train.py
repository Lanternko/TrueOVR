"""E-311 訓練：四臂 × 訓練到 --last（2023-24 或 2024-25），E-286 同超參數、5 seed；已存權重跳過（可續跑）。
  python -I -X utf8 train.py --arm ZG --last 2023-24"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import e311_lib as L  # noqa: E402
import torch  # noqa: E402
from e227_common import SEASONS, load_rows  # noqa: E402
from e227_model import run, season_means, sigma2_of, tensors  # noqa: E402
ap = argparse.ArgumentParser(); ap.add_argument('--arm', required=True, choices=list(L.KIND)); ap.add_argument('--last', required=True, choices=['2023-24', '2024-25'])
ap.add_argument('--seeds', default='0,1,2,3,4'); a = ap.parse_args()
cfg = json.load(open(os.path.join(L.Z.SRC, 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True)
todo = [sd for sd in map(int, a.seeds.split(',')) if not os.path.exists(os.path.join(out, 'weights', f'{a.arm}-{a.last}-{sd}.pt'))]
if not todo:
    print(a.arm, a.last, 'all seeds done'); sys.exit(0)
seas = SEASONS[:SEASONS.index(a.last) + 1]
rows = load_rows(seas); tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
means = season_means(tr); s2 = sigma2_of(tr, means); kind = L.KIND[a.arm]
Tt, Tv = tensors(tr, kind, means, 'train'), tensors(va, kind, means, 'val')
print('seasons', seas, 'train', len(tr), 'val', len(va), 'feat', Tt[0].shape[-1] // 2, 'cfg', cfg, 'dev', dev, flush=True)
for sd in todo:
    res, pred, state = run(f'{a.arm}-{a.last}', cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
    json.dump(res, open(os.path.join(out, f'final-{a.arm}-{a.last}-{sd}.json'), 'w'))
    torch.save(state, os.path.join(out, 'weights', f'{a.arm}-{a.last}-{sd}.pt')); print(a.arm, a.last, sd, res['valLoss'], res['bestEpoch'], res['seconds'], flush=True)
