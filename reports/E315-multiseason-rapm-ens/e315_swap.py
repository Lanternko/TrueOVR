"""E-315 個人 T-swap 腳本（5090）。"""
import argparse, glob, json, os, sys, time
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from e315_lib import ARM_CFG, build_features, build_model


def predict_batch(net, T, dev, bs=8192):
    net.eval()
    outs = []
    with torch.no_grad():
        for b in range(0, len(T[0]), bs):
            outs.append(net(T[0][b:b + bs].to(dev), T[1][b:b + bs].to(dev), T[2][b:b + bs].to(dev)).cpu())
    return torch.cat(outs, dim=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True, choices=list(ARM_CFG))
    ap.add_argument('--last', required=True)
    ap.add_argument('--season', required=True)
    ap.add_argument('--e227', required=True)
    ap.add_argument('--wdir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--N', type=int, default=3000)
    ap.add_argument('--seed', type=int, default=20261108)
    args = ap.parse_args()

    if os.path.exists(args.out):
        print('skip', args.out, flush=True)
        return

    sys.path.insert(0, args.e227)
    import e227_common, e227_model

    cfg = ARM_CFG[args.arm]
    F = e227_model.n_feat('stats') + (2 if cfg['use_rapm'] else 0)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    wfiles = sorted(glob.glob(os.path.join(args.wdir, f'{args.arm}-{args.last}-f*-s*.pt')))
    nets = []
    for wf in wfiles:
        n = build_model(args.arm, F)
        n.load_state_dict(torch.load(wf, map_location='cpu'))
        n.eval()
        nets.append(n.to(dev))

    tab = e227_common.load_player_table(args.season)
    single_B = e227_model.base_feats(args.season, 'stats')
    B = build_features(args.season, e227_model, e227_common, decay=cfg['decay'], k_shrink=cfg['k'],
                       use_rapm=cfg['use_rapm'], rapm_strict_past=False)
    pool = sorted(single_B.keys())
    med_h = float(np.median([d['heightInches'] for d in tab.values() if d.get('heightInches') is not None]))

    def vec(p):
        v = B[p]
        return np.concatenate([v[0], v[1]]).astype(np.float32)

    def hkey(p):
        d = tab.get(p) or {}
        h = d.get('heightInches'); h = med_h if h is None else h
        return (h, -((d.get('pass') or 0.0) + (d.get('creation') or 0.0)), p)

    rng = np.random.default_rng(args.seed); N = args.N
    draws = [list(rng.choice(pool, 10, replace=False)) for _ in range(N)]
    V = {p: vec(p) for p in pool}
    order = lambda l: sorted(l, key=hkey)
    A = np.stack([np.stack([V[p] for p in order(d[4:9])]) for d in draws])
    POS = torch.tensor(list(range(5)) * 2).unsqueeze(0)
    SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)

    off, dfn = {}, {}
    t0 = time.time()
    for idx, x in enumerate(pool):
        H = [[d[9] if q == x else q for q in d[:4]] for d in draws]
        Aopp = A.copy()
        for i, d in enumerate(draws):
            if x in d[4:9]:
                Aopp[i] = np.stack([V[p] for p in order([d[9] if q == x else q for q in d[4:9]])])
        Hs = np.stack([np.stack([V[p] for p in order(m + [x])]) for m in H])
        Xt = torch.from_numpy(np.concatenate([np.concatenate([Hs, Aopp], 1), np.concatenate([Aopp, Hs], 1)], 0))
        T = [Xt, POS.expand(2 * N, -1), SIDE.expand(2 * N, -1)]
        o_, d_ = [], []
        for m in nets:
            o = predict_batch(m, T, dev, bs=8192)[:, :, 0].numpy() * 100.0
            o_.append(0.5 * (o[:N, 0] + o[N:, 1])); d_.append(0.5 * (o[:N, 1] + o[N:, 0]))
        off[x] = float(np.mean(o_)); dfn[x] = float(np.mean(d_))
        if idx % 150 == 0:
            print(f'swap {args.arm} {args.season} {idx}/{len(pool)} {round(time.time() - t0)}s', flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump({'arm': args.arm, 'last': args.last, 'season': args.season, 'n_models': len(nets),
               'n_pool': len(off), 'ownPts100': off, 'oppPts100': dfn}, open(args.out, 'w'))
    print(f'DONE swap {args.arm} {args.season} {len(off)} players {round(time.time() - t0)}s', flush=True)


if __name__ == '__main__':
    main()
