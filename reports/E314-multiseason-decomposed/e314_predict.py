"""E-314 球隊預測腳本（5090）：支援 M1（用 A1 權重＋多季特徵）、M2、D1、M2D1、D_add。
用法：
  python e314_predict.py --arm M2 --key 2425 --last 2023-24 --prior 2023-24 --rep /path/to/reports --wdir ./results/weights --out ./work/pred-M2-2425-prior.json
"""
import argparse, csv, gzip, glob, json, os, sys, time
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from e314_lib import build_model, multi_season_feats


def predict_batch(net, T, dev, bs=8192):
    net.eval()
    outs = []
    with torch.no_grad():
        for b in range(0, len(T[0]), bs):
            outs.append(net(T[0][b:b + bs].to(dev), T[1][b:b + bs].to(dev), T[2][b:b + bs].to(dev)).cpu())
    return torch.cat(outs, dim=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True, choices=['M1', 'M2', 'D1', 'M2D1', 'D_add'])
    ap.add_argument('--key', required=True, choices=['2425', '2526'])
    ap.add_argument('--last', required=True)
    ap.add_argument('--prior', required=True)
    ap.add_argument('--rep', required=True)
    ap.add_argument('--wdir', required=True)
    ap.add_argument('--wprefix', default=None, help='Override weight prefix (e.g. A1 for M1)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--draws', type=int, default=2000)
    ap.add_argument('--rng', type=int, default=228)
    args = ap.parse_args()

    if os.path.exists(args.out):
        print('skip', args.out, flush=True)
        return

    e227 = os.path.join(args.rep, 'E227-lineup-transformer-r2')
    sys.path.insert(0, e227)
    import e227_common, e227_model

    F = e227_model.n_feat('stats')
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    wpref = args.wprefix or args.arm
    wfiles = sorted(glob.glob(os.path.join(args.wdir, f'{wpref}-{args.last}-f*-s*.pt')))
    assert wfiles, f'no weights found for {wpref}-{args.last} in {args.wdir}'

    nets = []
    for wf in wfiles:
        n = build_model(args.arm, F)
        n.load_state_dict(torch.load(wf, map_location='cpu'))
        n.eval()
        nets.append(n.to(dev))

    use_multi = args.arm in ('M1', 'M2', 'M2D1', 'D_add')
    tab = e227_common.load_player_table(args.prior)
    B = multi_season_feats(args.prior, e227_model, e227_common) if use_multi else e227_model.base_feats(args.prior, 'stats')
    med_h = float(np.median([d['heightInches'] for d in tab.values() if d.get('heightInches') is not None]))

    poss = 0.0
    gids = set()
    with gzip.open(os.path.join(e227, 'data', f'stints-train-{args.prior}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['possa'] != '' and r['possb'] != '':
                poss += float(r['possa']) + float(r['possb'])
                gids.add(r['gid'])
    avg_poss = poss / 2 / len(gids)

    def vec(p):
        v = B.get(str(p))
        return np.zeros(2 * F, np.float32) if v is None else np.concatenate([v[0], v[1]]).astype(np.float32)

    def hkey(p):
        d = tab.get(str(p)) or {}
        h = d.get('heightInches')
        h = med_h if h is None else h
        return (h, -((d.get('pass') or 0.0) + (d.get('creation') or 0.0)), str(p))

    def prep(rot):
        pids = [p for p, m in rot]
        mins = np.array([m for p, m in rot], float)
        order = sorted(range(len(pids)), key=lambda j: hkey(pids[j]))
        rank = np.empty(len(pids), int)
        rank[order] = np.arange(len(pids))
        return np.stack([vec(p) for p in pids]), np.log(mins), rank

    def draw(R, lm, rank, rng, N):
        g = lm[None, :] + rng.gumbel(size=(N, len(lm)))
        top = np.argsort(-g, axis=1)[:, :5]
        top = np.take_along_axis(top, np.argsort(rank[top], axis=1), axis=1)
        return R[top]

    POS = torch.tensor(list(range(5)) * 2).unsqueeze(0)
    SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)

    inp_name = 'inputs-2425.json' if args.key == '2425' else 'inputs.json'
    lin = json.load(open(os.path.join(args.rep, 'E223-team-rating', 'work', f'lineups-{args.key}.json'), encoding='utf-8'))
    inp = json.load(open(os.path.join(args.rep, 'E208-team-rating', inp_name), encoding='utf-8'))
    G = [(g['i'], g['home'], g['away']) for g in inp['games']]
    del inp

    n = len(G)
    N = args.draws
    M = len(nets)
    net100 = np.zeros((M, n), dtype=np.float64)
    t0 = time.time()

    for k, (i, h, aw) in enumerate(G):
        Rh, lh, rh = prep(lin[f'{i}h'])
        Ra, la, ra = prep(lin[f'{i}a'])
        rng = np.random.default_rng([args.rng, i])
        H5 = draw(Rh, lh, rh, rng, N)
        A5 = draw(Ra, la, ra, rng, N)
        X = torch.from_numpy(np.concatenate([np.concatenate([H5, A5], 1), np.concatenate([A5, H5], 1)], 0))
        T = [X, POS.expand(2 * N, -1), SIDE.expand(2 * N, -1)]
        for s, m in enumerate(nets):
            o = predict_batch(m, T, dev, bs=8192)[:, :, 0].numpy()
            d = 100.0 * (o[:, 0] - o[:, 1])
            net100[s, k] = float(np.mean(0.5 * (d[:N] - d[N:])))
        if k % 300 == 0:
            print(f'{args.arm} {args.key}({args.prior}) {k}/{n} {round(time.time() - t0)}s', flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out = dict(
        arm=args.arm, key=args.key, last=args.last, prior=args.prior, use_multi=use_multi,
        n_models=M, draws=N, rng=args.rng, avg_poss=avg_poss,
        games=[g[0] for g in G], home=[str(g[1]) for g in G], away=[str(g[2]) for g in G],
        margin_seed=(net100 * avg_poss / 100.0).tolist(),
    )
    json.dump(out, open(args.out, 'w'))
    print(f'DONE predict {args.arm} {args.key}({args.prior}) M={M} {round(time.time() - t0)}s', flush=True)


if __name__ == '__main__':
    main()
