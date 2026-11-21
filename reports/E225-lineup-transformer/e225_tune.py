"""E-225 調參／驗證折訓練（只讀 split=train；folds 1-4 訓練、fold 0 驗證）。
tune ：python e225_tune.py tune --shard i --nshards n   -> results/tune-<arm>-<lr>-<wd>-<seed>.json
final：python e225_tune.py final --arm T-min --seeds 0,1,2,3,4 -> results/final-<arm>-<seed>.json 與 preds-<arm>-<seed>.npy（fold 0 原始輸出）
"""
import argparse, itertools, json, os, sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_common import HERE, load_rows
from e225_model import ARMS, SEASONS, run, season_means, sigma2_of, tensors

LRS, WDS, SEEDS = [3e-4, 1e-3, 3e-3], [0.01, 0.1], [0, 1, 2]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mode'); ap.add_argument('--shard', type=int, default=0); ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--arm'); ap.add_argument('--seeds', default='0,1,2,3,4'); ap.add_argument('--out', default=os.path.join(HERE, 'results'))
    ap.add_argument('--maxjobs', type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    rows = load_rows(SEASONS)
    tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
    means = season_means(tr); s2 = sigma2_of(tr, means)
    cache = {}

    def data(arm):
        if arm not in cache:
            cache[arm] = (tensors(tr, ARMS[arm], means), tensors(va, ARMS[arm], means))
        return cache[arm]

    if a.mode == 'tune':
        jobs = [(arm, lr, wd, sd) for arm, lr, wd, sd in itertools.product(ARMS, LRS, WDS, SEEDS)]
        done = 0
        for k, (arm, lr, wd, sd) in enumerate(jobs):
            if k % a.nshards != a.shard:
                continue
            fn = os.path.join(a.out, f'tune-{arm}-{lr}-{wd}-{sd}.json')
            if os.path.exists(fn):
                continue
            Tt, Tv = data(arm)
            res, _ = run(arm, lr, wd, sd, Tt, Tv, s2, dev)
            json.dump(res, open(fn, 'w')); print(fn, res['valLoss'], res['bestEpoch'], res['seconds'], flush=True)
            done += 1
            if a.maxjobs and done >= a.maxjobs:
                break
    else:
        cfg = json.load(open(os.path.join(HERE, 'tuning.json')))['selected'][a.arm]
        Tt, Tv = data(a.arm)
        for sd in map(int, a.seeds.split(',')):
            res, pred = run(a.arm, cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev)
            json.dump(res, open(os.path.join(a.out, f'final-{a.arm}-{sd}.json'), 'w'))
            np.save(os.path.join(a.out, f'preds-{a.arm}-{sd}.npy'), pred); print(a.arm, sd, res['valLoss'], res['bestEpoch'], flush=True)


if __name__ == '__main__':
    main()
