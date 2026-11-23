"""E-312 測試 M 預測（5090）：2025-26 全 1230 場，B-mock／TG-mock 各 10 seed（另附 E-306 舊 mock 5 seed 當重現對照），
特徵＝2025-26 同季表（B：stats；TG：sG），抽樣同 e306_predict_mock（Gumbel top-k、N=2000、rng [228, i]），兩臂共用同一組抽樣索引。
不讀比分。輸出 results/pred-mock.json（已存在就跳過）。"""
import csv, gzip, importlib.util, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
E306 = os.environ.get('E306_DIR', os.path.join(os.path.dirname(HERE), 'e306'))
SRC = os.environ.setdefault('E227_SRC', os.path.join(E306, 'e227_src'))
sys.path.insert(0, SRC)
import numpy as np, torch
from e227_common import load_player_table
import e227_model
spec = importlib.util.spec_from_file_location('x307', os.path.join(HERE, 'ship', 'x307', 'x_lib.py'))
X = importlib.util.module_from_spec(spec); spec.loader.exec_module(X)
from e227_model import LineupNet, predict

OUT = os.path.join(HERE, 'results', 'pred-mock.json')
if os.path.exists(OUT):
    print('skip', OUT); sys.exit(0)
N = 2000; PRIOR = '2025-26'
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
ARMS = {'B': ('stats', os.path.join(HERE, 'results', 'weights', 'B-mock-{}.pt'), 10),
        'TG': ('sG', os.path.join(HERE, 'results', 'weights', 'TG-mock-{}.pt'), 10),
        'E306mock': ('stats', os.path.join(HERE, 'ship', 'e306w', 'mock-{}.pt'), 5)}
ARMS = {k: v for k, v in ARMS.items() if os.path.exists(v[1].format(0))}
tab = load_player_table(PRIOR)
BF = {k: X.base_feats(PRIOR, kind) for k, (kind, _, _) in ARMS.items()}
FN = {k: X.n_feat(kind) for k, (kind, _, _) in ARMS.items()}
med_h = float(np.median([d['heightInches'] for d in tab.values() if d.get('heightInches') is not None]))
poss = 0.0; gids = set()
with gzip.open(os.path.join(SRC, 'data', f'stints-train-{PRIOR}.csv.gz'), 'rt', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['possa'] != '' and r['possb'] != '':
            poss += float(r['possa']) + float(r['possb']); gids.add(r['gid'])
avg_poss = poss / 2 / len(gids)


def vec(k, p):
    v = BF[k].get(str(p)); F = FN[k]
    return np.zeros(2 * F, np.float32) if v is None else np.concatenate([v[0], v[1]]).astype(np.float32)


def hkey(p):
    d = tab.get(str(p)) or {}
    h = d.get('heightInches'); h = med_h if h is None else h
    return (h, -((d.get('pass') or 0.0) + (d.get('creation') or 0.0)), str(p))


def prep(rot):
    pids = [p for p, m in rot]; mins = np.array([m for p, m in rot], float)
    order = sorted(range(len(pids)), key=lambda j: hkey(pids[j])); rank = np.empty(len(pids), int); rank[order] = np.arange(len(pids))
    return pids, np.log(mins), rank


def draw_idx(lm, rank, rng):
    g = lm[None, :] + rng.gumbel(size=(N, len(lm)))
    top = np.argsort(-g, axis=1)[:, :5]
    return np.take_along_axis(top, np.argsort(rank[top], axis=1), axis=1)


lin = json.load(open(os.path.join(E306, 'lineups-2526.json'), encoding='utf-8'))
G = json.load(open(os.path.join(E306, 'mock-games.json')))
nets = {}
for k, (kind, pat, ns) in ARMS.items():
    nets[k] = []
    for sd in range(ns):
        n = LineupNet(FN[k]); n.load_state_dict(torch.load(pat.format(sd), map_location='cpu')); n.eval(); nets[k].append(n.to(dev))
out = {k: np.zeros((len(nets[k]), len(G))) for k in ARMS}; t0 = time.time()
for j, g in enumerate(G):
    i = g['i']; ph, lh, rh = prep(lin[f'{i}h']); pa, la, ra = prep(lin[f'{i}a'])
    rng = np.random.default_rng([228, i])
    ih, ia = draw_idx(lh, rh, rng), draw_idx(la, ra, rng)
    for k in ARMS:
        Rh = np.stack([vec(k, p) for p in ph]); Ra = np.stack([vec(k, p) for p in pa])
        H5, A5 = Rh[ih], Ra[ia]
        Xt = torch.from_numpy(np.concatenate([np.concatenate([H5, A5], 1), np.concatenate([A5, H5], 1)], 0))
        T = [Xt, POS.expand(2 * N, -1), SIDE.expand(2 * N, -1)]
        for s, m in enumerate(nets[k]):
            o = predict(m, T, dev, bs=8192)[:, :, 0].numpy(); d = 100.0 * (o[:, 0] - o[:, 1])
            out[k][s, j] = (0.5 * (d[:N] - d[N:])).mean() * avg_poss / 100
    if j % 200 == 0:
        print(j, len(G), round(time.time() - t0), 's', flush=True)
json.dump(dict(avg_poss=avg_poss, games=[g['i'] for g in G], first=[g['first'] for g in G], margin_seed={k: v.tolist() for k, v in out.items()}),
          open(OUT + '.tmp', 'w'))
os.replace(OUT + '.tmp', OUT)
print('done', round(time.time() - t0), 's')
