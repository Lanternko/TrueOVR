"""E-297 訓練：E-227 R2-stats 同架構、超參數、切分；臂見 o_lib。另存每 seed 的 fold 0 預測（前向選擇用）。
  python -I -X utf8 train.py --arms base,+cut36,... --seeds 0,1,2,3,4
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import o_lib as X  # noqa: E402
import numpy as np, torch  # noqa: E402
from e227_common import SEASONS, load_rows  # noqa: E402
from e227_model import run, season_means, sigma2_of, tensors  # noqa: E402

CFG = json.load(open(os.path.join(X.SRC, 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
_D = {}


def data():
    if not _D:
        rows = load_rows(SEASONS); tr = [r for r in rows if r['fold'] != 0]; va = [r for r in rows if r['fold'] == 0]
        means = season_means(tr); _D.update(tr=tr, va=va, means=means, s2=sigma2_of(tr, means))
    return _D


def train_arm(arm, seeds, cols=None):
    """cols 給定時用該欄集（前向選擇暫時臂，名稱 arm 只用於存檔）。"""
    D = data(); kind = ('ob:' + '+'.join(cols) if cols else 'stats') if cols is not None else X.kind_of(arm)
    Tt, Tv = tensors(D['tr'], kind, D['means'], 'train'), tensors(D['va'], kind, D['means'], 'val')
    out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True); os.makedirs(os.path.join(out, 'fold0'), exist_ok=True)
    for sd in seeds:
        wp = os.path.join(out, 'weights', f'{arm}-{sd}.pt')
        if os.path.exists(wp):
            continue
        res, pred, state = run(arm, CFG['lr'], CFG['wd'], sd, Tt, Tv, D['s2'], DEV, return_state=True)
        res['kind'] = kind
        json.dump(res, open(os.path.join(out, f'final-{arm}-{sd}.json'), 'w'))
        np.save(os.path.join(out, 'fold0', f'{arm}-{sd}.npy'), pred.astype(np.float32))
        torch.save(state, wp); print(arm, sd, kind, round(res['valLoss'], 5), res['bestEpoch'], res['seconds'], flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--arms', required=True); ap.add_argument('--seeds', default='0,1,2,3,4'); a = ap.parse_args()
    for arm in a.arms.split(','):
        train_arm(arm, list(map(int, a.seeds.split(','))))
