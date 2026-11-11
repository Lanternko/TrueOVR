"""E-228 T-2425：E-227 R2-stats 同架構、同超參數（tuning.json 的 R2-stats：lr 0.001、wd 0.1，不重調），
只用 2021-22～2024-25 的 split=train stint 重訓；folds 1-4 訓練、fold 0 驗證早停；5 seed。
E227_SRC 指向凍結的 E-227 程式與 data/（5090 上是 ./frozen_src）。不改凍結檔。
  CUDA_VISIBLE_DEVICES= python e228_train.py --seeds 0,1,2,3,4      # CPU
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.join(os.path.dirname(HERE), 'E227-lineup-transformer-r2'))
sys.path.insert(0, SRC)
import numpy as np, torch
from e227_common import load_rows
from e227_model import run, season_means, sigma2_of, tensors

SEASONS_T = ['2021-22', '2022-23', '2023-24', '2024-25']
KIND = 'stats'
ap = argparse.ArgumentParser(); ap.add_argument('--seeds', default='0,1,2,3,4'); ap.add_argument('--threads', type=int, default=6); a = ap.parse_args()
torch.set_num_threads(a.threads)
cfg = json.load(open(os.path.join(SRC, 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
rows = load_rows(SEASONS_T); tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
means = season_means(tr); s2 = sigma2_of(tr, means)
Tt, Tv = tensors(tr, KIND, means, 'train'), tensors(va, KIND, means, 'val')
print('rows', len(rows), 'train', len(tr), 'val', len(va), 'feat', Tt[0].shape[-1] // 2, 'cfg', cfg, 'dev', dev, flush=True)
out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True)
json.dump({'seasonMeans': means, 'sigma2': s2, 'cfg': cfg, 'seasons': SEASONS_T}, open(os.path.join(out, 'train-meta.json'), 'w'))
for sd in map(int, a.seeds.split(',')):
    res, pred, state = run('T-2425', cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
    json.dump(res, open(os.path.join(out, f'final-T2425-{sd}.json'), 'w'))
    torch.save(state, os.path.join(out, 'weights', f'T2425-{sd}.pt')); print('T-2425', sd, res['valLoss'], res['bestEpoch'], res['seconds'], flush=True)
