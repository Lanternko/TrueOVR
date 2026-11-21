"""E-306 測試 M 預測（5090）：2025-26 全 1230 場，三組權重（T2425 基準、mock、mockw3），特徵＝2025-26 同季表，
抽樣與 E-228 predict_t 相同（Gumbel top-k、N=2000、rng [228, i]）。不讀比分。輸出 results/pred-mock.json。"""
import csv, gzip, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.join(HERE, 'e227_src'))
sys.path.insert(0, SRC)
import numpy as np, torch
from e227_common import load_player_table
from e227_model import LineupNet, base_feats, n_feat, predict

F = n_feat('stats'); N = 2000; PRIOR = '2025-26'
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
W = {'T2425': os.path.join(HERE, 'weights-T2425', 'T2425-{}.pt'), 'mock': os.path.join(HERE, 'results', 'weights', 'mock-{}.pt'),
     'mockw3': os.path.join(HERE, 'results', 'weights', 'mockw3-{}.pt')}
tab = load_player_table(PRIOR); B = base_feats(PRIOR, 'stats')
med_h = float(np.median([d['heightInches'] for d in tab.values() if d.get('heightInches') is not None]))
poss = 0.0; gids = set()
with gzip.open(os.path.join(SRC, 'data', f'stints-train-{PRIOR}.csv.gz'), 'rt', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['possa'] != '' and r['possb'] != '':
            poss += float(r['possa']) + float(r['possb']); gids.add(r['gid'])
avg_poss = poss / 2 / len(gids)


def vec(p):
    v = B.get(str(p))
    return np.zeros(2 * F, np.float32) if v is None else np.concatenate([v[0], v[1]]).astype(np.float32)


def hkey(p):
    d = tab.get(str(p)) or {}
    h = d.get('heightInches'); h = med_h if h is None else h
    return (h, -((d.get('pass') or 0.0) + (d.get('creation') or 0.0)), str(p))


def prep(rot):
    pids = [p for p, m in rot]; mins = np.array([m for p, m in rot], float)
    order = sorted(range(len(pids)), key=lambda j: hkey(pids[j])); rank = np.empty(len(pids), int); rank[order] = np.arange(len(pids))
    return np.stack([vec(p) for p in pids]), np.log(mins), rank


def draw(R, lm, rank, rng):
    g = lm[None, :] + rng.gumbel(size=(N, len(lm)))
    top = np.argsort(-g, axis=1)[:, :5]
    top = np.take_along_axis(top, np.argsort(rank[top], axis=1), axis=1)
    return R[top]


lin = json.load(open(os.path.join(HERE, 'lineups-2526.json'), encoding='utf-8'))
G = json.load(open(os.path.join(HERE, 'mock-games.json')))
nets = {}
for k, pat in W.items():
    nets[k] = []
    for sd in range(5):
        n = LineupNet(F); n.load_state_dict(torch.load(pat.format(sd), map_location='cpu')); n.eval(); nets[k].append(n.to(dev))
out = {k: np.zeros((5, len(G))) for k in W}; t0 = time.time()
for j, g in enumerate(G):
    i = g['i']; Rh, lh, rh = prep(lin[f'{i}h']); Ra, la, ra = prep(lin[f'{i}a'])
    rng = np.random.default_rng([228, i])
    H5, A5 = draw(Rh, lh, rh, rng), draw(Ra, la, ra, rng)
    X = torch.from_numpy(np.concatenate([np.concatenate([H5, A5], 1), np.concatenate([A5, H5], 1)], 0))
    T = [X, POS.expand(2 * N, -1), SIDE.expand(2 * N, -1)]
    for k in W:
        for s, m in enumerate(nets[k]):
            o = predict(m, T, dev, bs=8192)[:, :, 0].numpy(); d = 100.0 * (o[:, 0] - o[:, 1])
            out[k][s, j] = (0.5 * (d[:N] - d[N:])).mean() * avg_poss / 100
    if j % 200 == 0:
        print(j, len(G), round(time.time() - t0), 's', flush=True)
json.dump(dict(avg_poss=avg_poss, games=[g['i'] for g in G], margin_seed={k: v.tolist() for k, v in out.items()}),
          open(os.path.join(HERE, 'results', 'pred-mock.json'), 'w'))
print('done', round(time.time() - t0), 's')
