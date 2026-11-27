"""E-315 訓練腳本（5090）：支援 M2_RAPM / D_add_RAPM / M2_L / D_add_L。"""
import argparse, json, os, sys, time
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from e315_lib import ARM_CFG, SEASONS_ORD, build_features, build_model, loss_b0


def build_tensors(rows, feat_cache, means, F):
    N = len(rows)
    attr = np.zeros((N, 10, 2 * F), np.float32)
    pos = np.zeros((N, 10), np.int64)
    side = np.tile(np.r_[np.zeros(5), np.ones(5)].astype(np.int64), (N, 1))
    y = np.zeros((N, 2, 6), np.float32)
    for i, r in enumerate(rows):
        Bs = feat_cache[r['season']]
        t = 0
        for x in 'ab':
            for j in range(5):
                p = Bs.get(r[x + str(j)])
                if p is not None:
                    attr[i, t, :F] = p[0]
                    attr[i, t, F:] = p[1]
                pos[i, t] = r[f'p{x}{j}']
                t += 1
        m = means[r['season']]
        for k, x in enumerate('ab'):
            y[i, k] = [r['pts' + x], r['poss' + x], r['tov' + x], r['orb' + x], r['rebOpp' + x], m]
    return [torch.from_numpy(a) for a in (attr, pos, side, y)]


def swap_augment(T):
    attr, pos, side, y = T
    return [
        torch.cat([attr, torch.cat([attr[:, 5:], attr[:, :5]], dim=1)], dim=0),
        torch.cat([pos, torch.cat([pos[:, 5:], pos[:, :5]], dim=1)], dim=0),
        torch.cat([side, side], dim=0),
        torch.cat([y, torch.stack([y[:, 1], y[:, 0]], dim=1)], dim=0),
    ]


def train_one(arm, fold, seed, Tt, Tv, sigma2, dev, max_epochs=60, patience=8, bs=1024):
    torch.manual_seed(seed)
    np.random.seed(seed)
    F = Tt[0].shape[-1] // 2
    net = build_model(arm, F).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=ARM_CFG[arm]['wd'])
    Tt_d = [t.to(dev) for t in Tt]
    Tv_d = [t.to(dev) for t in Tv]
    best, best_ep, best_state, bad, best_parts = 1e9, 0, None, 0, None
    t0 = time.time()

    for ep in range(1, max_epochs + 1):
        net.train()
        perm = torch.randperm(len(Tt_d[0]), device=dev)
        for b in range(0, len(perm), bs):
            ix = perm[b:b + bs]
            loss, _ = loss_b0(net(Tt_d[0][ix], Tt_d[1][ix], Tt_d[2][ix]), Tt_d[3][ix], sigma2)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()

        net.eval()
        with torch.no_grad():
            outs = []
            for b in range(0, len(Tv_d[0]), 4096):
                outs.append(net(Tv_d[0][b:b + 4096], Tv_d[1][b:b + 4096], Tv_d[2][b:b + 4096]))
            tot, parts = loss_b0(torch.cat(outs, dim=0), Tv_d[3], sigma2)

        if tot.item() < best - 1e-6:
            best, best_ep, bad = tot.item(), ep, 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
            best_parts = parts
        else:
            bad += 1
            if bad >= patience:
                break

    return {
        'arm': arm, 'fold': fold, 'seed': seed, 'valLoss': round(best, 5),
        'bestEpoch': best_ep, 'parts': [round(v, 5) for v in best_parts],
        'seconds': round(time.time() - t0, 1),
    }, best_state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True, choices=list(ARM_CFG))
    ap.add_argument('--last', required=True, choices=['2023-24', '2024-25'])
    ap.add_argument('--e227', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    sys.path.insert(0, args.e227)
    import e227_common, e227_model

    cfg = ARM_CFG[args.arm]
    seasons = SEASONS_ORD[:SEASONS_ORD.index(args.last) + 1]
    rows = e227_common.load_rows(seasons)
    F = e227_model.n_feat('stats') + (2 if cfg['use_rapm'] else 0)
    # 訓練時 rapm_strict_past=True：只用嚴格過去季 t < s 的 RAPM，絕不用當季！
    feat_cache = {
        s: build_features(s, e227_model, e227_common, decay=cfg['decay'], k_shrink=cfg['k'],
                          use_rapm=cfg['use_rapm'], rapm_strict_past=True)
        for s in seasons
    }
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    wdir = os.path.join(args.out, 'weights')
    os.makedirs(wdir, exist_ok=True)

    runs = [(f, f * 2 + s) for f in range(5) for s in range(2)]
    fold_cache = {}
    logs = []
    for fold, sd in runs:
        wf = os.path.join(wdir, f'{args.arm}-{args.last}-f{fold}-s{sd}.pt')
        if os.path.exists(wf):
            print('skip', wf, flush=True)
            continue
        if fold not in fold_cache:
            tr = [r for r in rows if r['fold'] != fold]
            va = [r for r in rows if r['fold'] == fold]
            means = e227_model.season_means(tr)
            s2 = e227_model.sigma2_of(tr, means)
            Tt = swap_augment(build_tensors(tr, feat_cache, means, F))
            Tv = build_tensors(va, feat_cache, means, F)
            fold_cache[fold] = (Tt, Tv, s2)
        Tt, Tv, s2 = fold_cache[fold]
        info, state = train_one(args.arm, fold, sd, Tt, Tv, s2, dev)
        torch.save(state, wf + '.tmp')
        os.replace(wf + '.tmp', wf)
        logs.append(info)
        print(f'{args.arm} {args.last} f{fold} s{sd}: val={info["valLoss"]:.5f} ep={info["bestEpoch"]} ({info["seconds"]}s)', flush=True)

    json.dump({'arm': args.arm, 'last': args.last, 'cfg': cfg, 'logs': logs},
              open(os.path.join(args.out, f'train-{args.arm}-{args.last}.json'), 'w'), indent=1)
    print('DONE train', args.arm, args.last, flush=True)


if __name__ == '__main__':
    main()
