"""E-312 訓練（5090）：E-306 e306_train 同配方（R2-stats、本季 ×1、舊季 fold 0 早停），臂 B（stats）／TG（sG），seed 0–9。
  python e312_train.py --arm B|TG --test cut|mock
資料讀 ../e306（stints、feat-cut.npz、e227_src）；TG 的 2026-27 表讀 ship/feat-cut-tg.npz、其他季讀 ship/x307（E-307 x_lib＋feat）。
已存在的 seed 權重會跳過（中斷後同指令重跑自動接續）。"""
import argparse, csv, gzip, importlib.util, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
E306 = os.environ.get('E306_DIR', os.path.join(os.path.dirname(HERE), 'e306'))
SRC = os.environ.setdefault('E227_SRC', os.path.join(E306, 'e227_src'))
sys.path.insert(0, SRC)
import numpy as np, torch
import e227_common
import e227_model
spec = importlib.util.spec_from_file_location('x307', os.path.join(HERE, 'ship', 'x307', 'x_lib.py'))
X = importlib.util.module_from_spec(spec); spec.loader.exec_module(X)          # 會 patch e227_model.base_feats／n_feat
from e227_common import load_rows
from e227_model import run, season_means, sigma2_of, tensors

S5 = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
TESTS = {'cut': (S5, 'stints-2627.csv.gz', '2026-11-06'), 'mock': (S5[:4], 'stints-2526-first.csv.gz', None)}
KIND = {'B': 'stats', 'TG': 'sG'}
ap = argparse.ArgumentParser(); ap.add_argument('--arm', required=True, choices=list(KIND)); ap.add_argument('--test', required=True, choices=list(TESTS))
ap.add_argument('--seeds', default=','.join(map(str, range(10)))); ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
torch.set_num_threads(a.threads)
seasons, extra_file, cut = TESTS[a.test]; kind = KIND[a.arm]


def load_extra(path, cut):      # 同 e306_train.load_extra
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


if a.test == 'cut':      # 2026-27：特徵表直接注入（B＝E-306 feat-cut；TG＝同表 blk36 欄換 AG）
    if '2026-27' not in e227_common.SEASONS:
        e227_common.SEASONS.append('2026-27')
    zb = np.load(os.path.join(E306, 'feat-cut.npz'))
    e227_model._CACHE[('2026-27', 'stats')] = {str(p): (zb['vals'][i], zb['mask'][i]) for i, p in enumerate(zb['pids'])}
    if kind == 'sG':
        zt = np.load(os.path.join(HERE, 'ship', 'feat-cut-tg.npz'))
        X._XC[('2026-27', 'sG')] = {str(p): (zt['vals'][i], zt['mask'][i]) for i, p in enumerate(zt['pids'])}
cfg = json.load(open(os.path.join(SRC, 'tuning.json'), encoding='utf-8'))['selected']['R2-stats']
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
base = load_rows(seasons); extra = load_extra(os.path.join(E306, extra_file), cut)
extra = [r for r in extra if not any(math.isnan(r[k + x]) for x in 'ab' for k in ('poss', 'pts', 'tov', 'orb', 'rebOpp'))]
tr = [r for r in base if r['fold'] != 0] + extra; va = [r for r in base if r['fold'] == 0]
means = season_means(tr); s2 = sigma2_of(tr, means)
Tt, Tv = tensors(tr, kind, means, 'train'), tensors(va, kind, means, 'val')
F = e227_model.n_feat(kind)
cover = float(Tt[0][-len(extra):, :, F:].mean()) if extra else 0.0
tag = f'{a.arm}-{a.test}'
out = os.path.join(HERE, 'results'); os.makedirs(os.path.join(out, 'weights'), exist_ok=True)
meta = {'arm': a.arm, 'kind': kind, 'test': a.test, 'seasons': seasons, 'extraRows': len(extra), 'extraGames': len({r['gid'] for r in extra}), 'cut': cut,
        'train': len(tr), 'val': len(va), 'seasonMeans': means, 'sigma2': s2, 'cfg': cfg, 'extraMaskCover': cover, 'dev': dev, 'nFeat': F}
json.dump(meta, open(os.path.join(out, f'meta-{tag}.json'), 'w')); print(json.dumps(meta), flush=True)
for sd in map(int, a.seeds.split(',')):
    wf = os.path.join(out, 'weights', f'{tag}-{sd}.pt')
    if os.path.exists(wf):
        print('skip', tag, sd, flush=True); continue
    res, pred, state = run(tag, cfg['lr'], cfg['wd'], sd, Tt, Tv, s2, dev, return_state=True)
    json.dump(res, open(os.path.join(out, f'final-{tag}-{sd}.json'), 'w'))
    torch.save(state, wf + '.tmp'); os.replace(wf + '.tmp', wf)
    print(tag, sd, res['valLoss'], res['bestEpoch'], res['seconds'], flush=True)
