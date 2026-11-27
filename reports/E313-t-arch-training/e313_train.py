"""E-313 訓練腳本（5090）：支援 B0 / A1 / A2 / A3 / A4，切點 last ∈ {2023-24, 2024-25}。
用法：
  python e313_train.py --arm A3 --last 2023-24 --e227 /path/to/E227-lineup-transformer-r2 --out ./results
"""
import argparse, json, math, os, sys, time
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from e313_models import build_model, loss_b0, loss_a2

ALL_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']


def build_tensors(rows, base_cache, means, F):
    """建立 attr[N,10,2F], pos[N,10], side[N,10], y[N,2,9]（pts,poss,tov,orb,rebOpp,mean,fga,efg_num,ftm）。"""
    N = len(rows)
    attr = np.zeros((N, 10, 2 * F), np.float32)
    pos = np.zeros((N, 10), np.int64)
    side = np.tile(np.r_[np.zeros(5), np.ones(5)].astype(np.int64), (N, 1))
    y = np.zeros((N, 2, 9), np.float32)
    for i, r in enumerate(rows):
        Bs = base_cache[r['season']]
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
            fga = r.get('fga' + x, 0.0)
            fgm = r.get('fgm' + x, 0.0)
            fg3m = r.get('fg3m' + x, 0.0)
            ftm = r.get('ftm' + x, 0.0)
            if math.isnan(fga): fga = 0.0
            if math.isnan(fgm): fgm = 0.0
            if math.isnan(fg3m): fg3m = 0.0
            if math.isnan(ftm): ftm = 0.0
            y[i, k] = [r['pts' + x], r['poss' + x], r['tov' + x], r['orb' + x], r['rebOpp' + x], m,
                       fga, fgm + 0.5 * fg3m, ftm]
    return [torch.from_numpy(a) for a in (attr, pos, side, y)]


def swap_augment(T):
    """A/B 雙向對稱增強：樣本數 ×2。"""
    attr, pos, side, y = T
    attr_s = torch.cat([attr[:, 5:], attr[:, :5]], dim=1)
    pos_s = torch.cat([pos[:, 5:], pos[:, :5]], dim=1)
    y_s = torch.stack([y[:, 1], y[:, 0]], dim=1)
    return [
        torch.cat([attr, attr_s], dim=0),
        torch.cat([pos, pos_s], dim=0),
        torch.cat([side, side], dim=0),
        torch.cat([y, y_s], dim=0),
    ]


def compute_stats(y_tr):
    """計算訓練集標準化常數（只用訓練折）。"""
    pts, poss, _, _, _, mean, fga, efg_num, ftm = y_tr.unbind(-1)
    rate = torch.where(poss > 0, pts / poss.clamp(min=1e-6), mean) - mean
    s2 = float(((poss * rate ** 2).sum() / poss.sum().clamp(min=1e-6)).item())

    poss_min = torch.minimum(poss[:, 0], poss[:, 1])
    net = rate[:, 0] - rate[:, 1]
    s2_net = float(((poss_min * net ** 2).sum() / poss_min.sum().clamp(min=1e-6)).item())

    fga_sum = fga.sum().clamp(min=1e-6)
    mean_efg = float((efg_num.sum() / fga_sum).item())
    efg_r = torch.where(fga > 0, efg_num / fga.clamp(min=1e-6), torch.tensor(mean_efg)) - mean_efg
    s2_efg = float(((fga * efg_r ** 2).sum() / fga_sum).item())

    mean_ftr = float((ftm.sum() / fga_sum).item())
    ftr_r = torch.where(fga > 0, ftm / fga.clamp(min=1e-6), torch.tensor(mean_ftr)) - mean_ftr
    s2_ftr = float(((fga * ftr_r ** 2).sum() / fga_sum).item())

    return {
        'sigma2': max(s2, 1e-4),
        'sigma2_net': max(s2_net, 1e-4),
        'mean_efg': mean_efg,
        'sigma2_efg': max(s2_efg, 1e-4),
        'mean_ftr': mean_ftr,
        'sigma2_ftr': max(s2_ftr, 1e-4),
    }


def train_one(arm, fold, seed, Tt, Tv, stats, dev, max_epochs=60, bs=1024):
    torch.manual_seed(seed)
    np.random.seed(seed)
    F = Tt[0].shape[-1] // 2
    net = build_model(arm, F).to(dev)
    use_a2 = arm in ('A2', 'A3', 'A4')
    patience = 5 if arm == 'B0' else 8
    lr = 1e-3
    wd = 0.1
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=wd)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max_epochs, eta_min=1e-5) if use_a2 else None
    lfn = loss_a2 if use_a2 else loss_b0

    Tt_d = [t.to(dev) for t in Tt]
    Tv_d = [t.to(dev) for t in Tv]
    best, best_ep, best_state, bad, best_parts = 1e9, 0, None, 0, None
    t0 = time.time()

    for ep in range(1, max_epochs + 1):
        net.train()
        perm = torch.randperm(len(Tt_d[0]), device=dev)
        for b in range(0, len(perm), bs):
            ix = perm[b:b + bs]
            out = net(Tt_d[0][ix], Tt_d[1][ix], Tt_d[2][ix])
            loss, _, _ = lfn(out, Tt_d[3][ix], stats)
            opt.zero_grad()
            loss.backward()
            if use_a2:
                torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
        if sched is not None:
            sched.step()

        net.eval()
        with torch.no_grad():
            outs = []
            for b in range(0, len(Tv_d[0]), 4096):
                outs.append(net(Tv_d[0][b:b + 4096], Tv_d[1][b:b + 4096], Tv_d[2][b:b + 4096]))
            vout = torch.cat(outs, dim=0)
            _, score, parts = lfn(vout, Tv_d[3], stats)

        if score < best - 1e-6:
            best, best_ep, bad = score, ep, 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
            best_parts = parts
        else:
            bad += 1
            if bad >= patience:
                break

    info = {
        'arm': arm, 'fold': fold, 'seed': seed, 'valScore': round(best, 5),
        'bestEpoch': best_ep, 'parts': [round(v, 5) for v in best_parts],
        'params': sum(p.numel() for p in net.parameters()),
        'seconds': round(time.time() - t0, 1),
    }
    return info, best_state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True, choices=['B0', 'A1', 'A2', 'A3', 'A4'])
    ap.add_argument('--last', required=True, choices=['2023-24', '2024-25'])
    ap.add_argument('--e227', required=True, help='Path to E227-lineup-transformer-r2')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    sys.path.insert(0, args.e227)
    from e227_common import load_rows
    from e227_model import base_feats, n_feat, season_means

    seasons = ALL_SEASONS[:ALL_SEASONS.index(args.last) + 1]
    rows = load_rows(seasons)
    F = n_feat('stats')
    base_cache = {s: base_feats(s, 'stats') for s in seasons}
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'

    wdir = os.path.join(args.out, 'weights')
    os.makedirs(wdir, exist_ok=True)

    # 決定 (fold, seed) 清單
    if args.arm == 'B0':
        runs = [(0, sd) for sd in range(5)]
    else:
        runs = [(f, f * 2 + s) for f in range(5) for s in range(2)]

    # 依 fold 分組快取 tensor，避免重複建置
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
            means = season_means(tr)
            Tt = build_tensors(tr, base_cache, means, F)
            Tv = build_tensors(va, base_cache, means, F)
            if args.arm != 'B0':
                Tt = swap_augment(Tt)
            stats = compute_stats(Tt[3])
            fold_cache[fold] = (Tt, Tv, stats)
        Tt, Tv, stats = fold_cache[fold]
        info, state = train_one(args.arm, fold, sd, Tt, Tv, stats, dev)
        torch.save(state, wf + '.tmp')
        os.replace(wf + '.tmp', wf)
        logs.append(info)
        print(f'{args.arm} {args.last} f{fold} s{sd}: val={info["valScore"]:.5f} ep={info["bestEpoch"]} ({info["seconds"]}s) parts={info["parts"]}', flush=True)

    meta_path = os.path.join(args.out, f'train-{args.arm}-{args.last}.json')
    json.dump({'arm': args.arm, 'last': args.last, 'seasons': seasons, 'runs': runs, 'logs': logs}, open(meta_path, 'w'), indent=1)
    print('DONE train', args.arm, args.last, flush=True)


if __name__ == '__main__':
    main()
