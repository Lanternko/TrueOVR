"""E-286 球隊預測（E-228 predict_t 同口徑；不讀比分）。
  python -I -X utf8 predict.py --arm X --key 2526 --last 2024-25 --prior 2024-25 --out work/pred-X-2526-prior.json"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from x286 import ctx, T, np, torch  # noqa: E402
ap = argparse.ArgumentParser()
ap.add_argument('--arm', required=True, choices=['B', 'X']); ap.add_argument('--key', required=True, choices=['2425', '2526'])
ap.add_argument('--last', required=True); ap.add_argument('--prior', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--draws', type=int, default=2000); ap.add_argument('--rng', type=int, default=228); ap.add_argument('--dev', default='cuda' if torch.cuda.is_available() else 'cpu')
a = ap.parse_args()
C = ctx(a.arm, os.path.join(HERE, 'results', 'weights', f'{a.arm}-{a.last}-{{}}.pt'), a.prior, a.dev)
INP = {'2425': 'inputs-2425.json', '2526': 'inputs.json'}
lin = json.load(open(os.path.join(T.E223, f'lineups-{a.key}.json'), encoding='utf-8'))
inp = json.load(open(os.path.join(T.ROOT, 'reports', 'E208-team-rating', INP[a.key]), encoding='utf-8'))
G = [(g['i'], g['home'], g['away']) for g in inp['games']]; del inp
n = len(G); N = a.draws; net100 = np.zeros((5, n)); t0 = time.time()
for k, (i, h, aw) in enumerate(G):
    Rh, lh, rh = C.prep(lin[f'{i}h']); Ra, la, ra = C.prep(lin[f'{i}a'])
    rng = np.random.default_rng([a.rng, i])
    net100[:, k] = C.net100(C.draw(Rh, lh, rh, rng, N), C.draw(Ra, la, ra, rng, N)).mean(1)
    if k % 300 == 0: print(k, n, round(time.time() - t0), 's', flush=True)
out = dict(arm=a.arm, key=a.key, last=a.last, prior=a.prior, draws=N, rng=a.rng, avg_poss=C.avg_poss, games=[g[0] for g in G],
           home=[str(g[1]) for g in G], away=[str(g[2]) for g in G], margin_seed=(net100 * C.avg_poss / 100).tolist())
os.makedirs(os.path.dirname(os.path.join(HERE, a.out)), exist_ok=True)
json.dump(out, open(os.path.join(HERE, a.out), 'w'))
print('done', a.arm, a.key, a.prior, n, round(time.time() - t0), 's')
