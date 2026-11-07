"""E-225 凍結設定下重訓並存權重（只讀 split=train；folds 1-4 訓練、fold 0 早停，seed 0-4）。
用途：final 當時沒存權重，這裡用凍結超參（tuning.json selected）重訓，輸出 results/weights/<arm>-<seed>.pt，
並與當時存的 results/preds-<arm>-<seed>.npy 比對（驗證可重現）。不改任何設定。
用法：python e225_train_save.py --arm T-min --seeds 0,1,2,3,4
"""
import argparse, json, os, sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_common import HERE, load_rows
from e225_model import ARMS, SEASONS, run, season_means, sigma2_of, tensors


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--arm', required=True); ap.add_argument('--seeds', default='0,1,2,3,4')
    a = ap.parse_args(); dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    rows = load_rows(SEASONS)
    tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
    means = season_means(tr); s2 = sigma2_of(tr, means)
    Tt, Tv = tensors(tr, ARMS[a.arm], means), tensors(va, ARMS[a.arm], means)
    cfg = json.load(open(os.path.join(HERE, 'tuning.json'), encoding='utf-8'))['selected'][a.arm]
    os.makedirs(os.path.join(HERE, 'results', 'weights'), exist_ok=True); rep = {}
    for sd in map(int, a.seeds.split(',')):
        info, pred, state = run(a.arm, cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
        torch.save(state, os.path.join(HERE, 'results', 'weights', f'{a.arm}-{sd}.pt'))
        old = np.load(os.path.join(HERE, 'results', f'preds-{a.arm}-{sd}.npy'))
        rep[sd] = {'valLoss': info['valLoss'], 'bestEpoch': info['bestEpoch'], 'maxAbsDiffVsFinal': float(np.abs(old - pred).max())}
        print(a.arm, sd, rep[sd], flush=True)
    json.dump({'arm': a.arm, 'cfg': cfg, 'seeds': rep}, open(os.path.join(HERE, 'results', 'weights', f'retrain-{a.arm}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
