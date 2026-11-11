"""E-287 T 換人進攻／防守值（E-274 e274_swap 同抽樣：3000 組、seed 20261108、所有人共用同批陣容）。
同時記錄換進 x 時「本隊每 100 回合得分」（進攻）與「對手每 100 回合得分」（防守，越低越好）。5090：
  python e287_swap.py --prior 2024-25 --weights <pat {}> --pool pool-2024-25.json --out t-2024-25.json"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
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
    off, dfn = {}, {}
    for x in pool:
        H = [[d[9] if q == x else q for q in d[:4]] for d in draws]
        Aopp = A.copy()
        for i, d in enumerate(draws):
            if x in d[4:9]:
                Aopp[i] = np.stack([V[p] for p in order([d[9] if q == x else q for q in d[4:9]])])
        Hs = np.stack([np.stack([V[p] for p in order(m + [x])]) for m in H])
        Xt = torch.from_numpy(np.concatenate([np.concatenate([Hs, Aopp], 1), np.concatenate([Aopp, Hs], 1)], 0))
        T = [Xt, POS.expand(2 * N, -1), SIDE.expand(2 * N, -1)]
        o_, d_ = [], []
        for m in C.nets:
            o = predict(m, T, C.dev, bs=bs)[:, :, 0].numpy() * 100
            o_.append(0.5 * (o[:N, 0] + o[N:, 1])); d_.append(0.5 * (o[:N, 1] + o[N:, 0]))
        off[x] = float(np.mean(o_)); dfn[x] = float(np.mean(d_))
    return off, dfn


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--prior'); ap.add_argument('--weights'); ap.add_argument('--pool'); ap.add_argument('--out')
    a = ap.parse_args()
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    C = C2(a.weights, a.prior, dev)
    off, dfn = swap_values(C, [str(p) for p in json.load(open(a.pool))])
    json.dump({'prior': a.prior, 'weights': a.weights, 'n_pool': len(off), 'ownPts100': off, 'oppPts100': dfn}, open(a.out, 'w'))
    print('done', a.prior, len(off), flush=True)
