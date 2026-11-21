"""E-306 訓練（5090）：E-227 R2-stats 同架構同超參數，舊季 train stint ＋ 新季 stint（全部進訓練折），舊季 fold 0 驗證早停，5 seed。
  python e306_train.py --arm full|fullw3|cut|cutw3|mock|mockw3
已存在的 seed 權重會跳過（中斷後同指令重跑自動接續）。"""
import argparse, csv, gzip, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.join(HERE, 'e227_src'))
sys.path.insert(0, SRC)
import numpy as np, torch
import e227_common
import e227_model
from e227_common import load_rows
from e227_model import run, season_means, sigma2_of, tensors

S5 = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
#        舊季        新季檔                    日期上限        複製  2026-27 特徵
ARMS = {'full':   (S5,      'stints-2627.csv.gz',       None,         1, 'feat-full.npz'),
        'fullw3': (S5,      'stints-2627.csv.gz',       None,         3, 'feat-full.npz'),
        'cut':    (S5,      'stints-2627.csv.gz',       '2026-11-06', 1, 'feat-cut.npz'),
        'cutw3':  (S5,      'stints-2627.csv.gz',       '2026-11-06', 3, 'feat-cut.npz'),
        'mock':   (S5[:4],  'stints-2526-first.csv.gz', None,         1, None),
        'mockw3': (S5[:4],  'stints-2526-first.csv.gz', None,         3, None)}
ap = argparse.ArgumentParser(); ap.add_argument('--arm', required=True, choices=list(ARMS)); ap.add_argument('--seeds', default='0,1,2,3,4')
ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
torch.set_num_threads(a.threads)
seasons, extra_file, cut, mult, feat = ARMS[a.arm]


def load_extra(path, cut):
    out = []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if cut and r['date'] > cut:
                continue
            for k in list(r):
                if k.startswith(('poss', 'pts', 'fga', 'fgm', 'fg3', 'ftm', 'fta', 'tov', 'orb', 'drb', 'rebOpp', 'sec')):
                    r[k] = float(r[k]) if r[k] != '' else math.nan
            r['fold'] = 1
            for k in [f'p{x}{j}' for x in 'ab' for j in range(5)]:
                r[k] = int(r[k])
            out.append(r)
    return out


if feat:      # 2026-27：特徵表直接注入（與線上推論同一份 live 混合表）
    if '2026-27' not in e227_common.SEASONS:
        e227_common.SEASONS.append('2026-27')      # e227_model.season_means 讀同一個 list
    z = np.load(os.path.join(HERE, feat))
    e227_model._CACHE[('2026-27', 'stats')] = {str(p): (z['vals'][i], z['mask'][i]) for i, p in enumerate(z['pids'])}
cfg = json.load(open(os.path.join(SRC, 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
base = load_rows(seasons); extra = load_extra(os.path.join(HERE, extra_file), cut)
extra = [r for r in extra if not any(math.isnan(r[k + x]) for x in 'ab' for k in ('poss', 'pts', 'tov', 'orb', 'rebOpp'))]
tr = [r for r in base if r['fold'] != 0] + extra * mult; va = [r for r in base if r['fold'] == 0]
means = season_means(tr); s2 = sigma2_of(tr, means)
Tt, Tv = tensors(tr, 'stats', means, 'train'), tensors(va, 'stats', means, 'val')
cover = float(Tt[0][-len(extra):, :, 41:].mean()) if extra else 0.0      # 新季列的特徵遮罩覆蓋率
out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True)
meta = {'arm': a.arm, 'seasons': seasons, 'extraRows': len(extra), 'extraGames': len({r['gid'] for r in extra}), 'mult': mult, 'cut': cut,
        'train': len(tr), 'val': len(va), 'seasonMeans': means, 'sigma2': s2, 'cfg': cfg, 'extraMaskCover': cover, 'dev': dev}
json.dump(meta, open(os.path.join(out, f'meta-{a.arm}.json'), 'w')); print(json.dumps(meta), flush=True)
for sd in map(int, a.seeds.split(',')):
    wf = os.path.join(out, 'weights', f'{a.arm}-{sd}.pt')
    if os.path.exists(wf):
        print('skip', a.arm, sd, flush=True); continue
    res, pred, state = run(a.arm, cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
    json.dump(res, open(os.path.join(out, f'final-{a.arm}-{sd}.json'), 'w'))
    torch.save(state, wf + '.tmp'); os.replace(wf + '.tmp', wf)
    print(a.arm, sd, res['valLoss'], res['bestEpoch'], res['seconds'], flush=True)
