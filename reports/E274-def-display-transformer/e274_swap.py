"""E-274 D2：T 換人防守值。用法（5090，E227_SRC=frozen_src）：
  python e274_swap.py --prior 2023-24 --weights results-T2324/weights/T2324-{}.pt --pool pool-2023-24.json --out d2-2023-24.json
pool json＝球員池 pid 清單（str）。每組 10 人不重複（4 隊友＋5 對手＋1 備用），所有球員共用同一批陣容；x 換進隊友第 5 人，
x 已在該組隊友／對手則用備用補；位置依 hkey 排。值＝對手每 100 回合得分（5 seed 網路平均；主客位置各算一次取平均）。回傳「對手得分」（未取負）。"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, torch
from t_lib import Ctx, F, POS, SIDE, load_player_table, base_feats, KIND, LineupNet, predict


class C2(Ctx):
    def __init__(self, wpat, prior, dev):
        self.dev = dev; self.nets = []
        for sd in range(5):
            n = LineupNet(F); n.load_state_dict(torch.load(wpat.format(sd), map_location='cpu')); n.eval(); self.nets.append(n.to(dev))
        self.tab = load_player_table(prior); self.B = base_feats(prior, KIND)
        self.med_h = float(np.median([d['heightInches'] for d in self.tab.values() if d.get('heightInches') is not None]))


def swap_values(C, pool, N=3000, seed=20261108, bs=8192):
    pool = [p for p in pool if p in C.B]
    rng = np.random.default_rng(seed)
    draws = [list(rng.choice(pool, 10, replace=False)) for _ in range(N)]
    V = {p: C.vec(p) for p in pool}
    order = lambda l: sorted(l, key=C.hkey)
    A = np.stack([np.stack([V[p] for p in order(d[4:9])]) for d in draws])
    out = {}
    for x in pool:
        H = []
        for d in draws:
            m = list(d[:4])
            if x in m: m = [d[9] if q == x else q for q in m]
            H.append(m)
        # 對手含 x 的組：用備用替換 x
        Aopp = A.copy()
        for i, d in enumerate(draws):
            if x in d[4:9]:
                Aopp[i] = np.stack([V[p] for p in order([d[9] if q == x else q for q in d[4:9]])])
        Hs = np.stack([np.stack([V[p] for p in order(m + [x])]) for m in H])
        X = torch.from_numpy(np.concatenate([np.concatenate([Hs, Aopp], 1), np.concatenate([Aopp, Hs], 1)], 0))
        T = [X, POS.expand(2 * N, -1), SIDE.expand(2 * N, -1)]
        dfn = []
        for m in C.nets:
            o = predict(m, T, C.dev, bs=bs)[:, :, 0].numpy() * 100
            dfn.append(0.5 * (o[:N, 1] + o[N:, 0]))
        out[x] = float(np.mean(dfn))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--prior'); ap.add_argument('--weights'); ap.add_argument('--pool'); ap.add_argument('--out')
    ap.add_argument('--threads', type=int, default=4); ap.add_argument('--n', type=int, default=3000); a = ap.parse_args()
    torch.set_num_threads(a.threads)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    C = C2(a.weights, a.prior, dev)
    pool = [str(p) for p in json.load(open(a.pool))]
    r = swap_values(C, pool, N=a.n)
    json.dump({'prior': a.prior, 'weights': a.weights, 'n_pool': len(r), 'N': a.n, 'oppPts100': r}, open(a.out, 'w'))
    print('done', len(r))
