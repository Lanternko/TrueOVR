"""探索性：R2-stats-nost 的個人價值 v2（同 e227_value.new_values、同 4000 抽樣、RandomState(225)）。在 5090 跑：
  E225_E227_SRC 用 E227_SRC=frozen_src；讀 ../results/value-prep.json（凍結），輸出 results/value-raw-nost.json。"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, torch
from ns_common import ARM, strip_np
import e227_value as ev
from e227_model import LineupNet
PARENT = os.path.join(HERE, '..')
pr = json.load(open(os.path.join(PARENT, 'results', 'value-prep.json'), encoding='utf-8'))
dev = sys.argv[1] if len(sys.argv) > 1 else 'cuda'
torch.set_num_threads(8)
feats = strip_np(np.array(pr['feats']['R2-stats'], np.float32)); nf = pr['nfeat']['R2-stats'] - 1
assert feats.shape[-1] == 2 * nf, (feats.shape, nf)
nets = []
for sd in range(5):
    n = LineupNet(nf); n.load_state_dict(torch.load(os.path.join(HERE, 'results', 'weights', f'{ARM}-{sd}.pt'), map_location='cpu')); n.eval(); nets.append(n.to(dev))
modal = pr['modal']; tg = list(range(len(pr['pids'])))
out = {'ndraw': 4000, 'n': len(tg), 'pids': pr['pids'], 'names': pr['names'], 'modalPos': modal, 'min': pr['min'], 'new': {ARM: ev.new_values(nets, feats, modal, 4000, 225, tg, dev).tolist()}}
json.dump(out, open(os.path.join(HERE, 'results', 'value-raw-nost.json'), 'w'))
print('done')
