"""E-315 上線權重重訓（5090）：全五季（2021-22～2025-26）多季滑動窗口特徵 ＋ 2026-27 本季 stint（×1，同 E-306 R3）。
支援 --arm M2_full（LineupNet 10 模型）或 --arm D_add_full（AdditiveOnlyNet 10 模型）。"""
import argparse, csv, gzip, json, math, os, sys, time
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from e315_lib import AdditiveOnlyNet, LineupNetA1, SEASONS_ORD, build_features, loss_b0


def load_extra(path):
    out = []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            for k in list(r):
                if k.startswith(('poss', 'pts', 'fga', 'fgm', 'fg3', 'ftm', 'fta', 'tov', 'orb', 'drb', 'rebOpp', 'sec')):
                    r[k] = float(r[k]) if r[k] != '' else math.nan
            r['fold'] = -1  # 本季全部進訓練折（同 E-306 R3）
            for k in [f'p{x}{j}' for x in 'ab' for j in range(5)]:
                r[k] = int(r[k])
            if not any(math.isnan(r[k + x]) for x in 'ab' for k in ('poss', 'pts', 'tov', 'orb', 'rebOpp')):
                out.append(r)
    return out


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


def train_one(arch, fold, seed, Tt, Tv, sigma2, dev, max_epochs=60, patience=8, bs=1024):
    torch.manual_seed(seed); np.random.seed(seed)
    F = Tt[0].shape[-1] // 2
    net = (LineupNetA1(F) if arch == 'lineup' else AdditiveOnlyNet(F)).to(dev)
    wd = 0.10 if arch == 'lineup' else 0.15
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=wd)
    Tt_d = [t.to(dev) for t in Tt]; Tv_d = [t.to(dev) for t in Tv]
    best, best_ep, best_state, bad = 1e9, 0, None, 0
    t0 = time.time()
    for ep in range(1, max_epochs + 1):
        net.train()
        perm = torch.randperm(len(Tt_d[0]), device=dev)
        for b in range(0, len(perm), bs):
            ix = perm[b:b + bs]
            loss, _ = loss_b0(net(Tt_d[0][ix], Tt_d[1][ix], Tt_d[2][ix]), Tt_d[3][ix], sigma2)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
        net.eval()
        with torch.no_grad():
            outs = [net(Tv_d[0][b:b + 4096], Tv_d[1][b:b + 4096], Tv_d[2][b:b + 4096]) for b in range(0, len(Tv_d[0]), 4096)]
            tot, _ = loss_b0(torch.cat(outs, 0), Tv_d[3], sigma2)
        if tot.item() < best - 1e-6:
            best, best_ep, bad = tot.item(), ep, 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    return {'fold': fold, 'seed': seed, 'valLoss': round(best, 5), 'bestEpoch': best_ep, 'seconds': round(time.time() - t0, 1)}, best_state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', required=True, choices=['M2_full', 'D_add_full'])
    ap.add_argument('--e227', required=True)
    ap.add_argument('--e306', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    sys.path.insert(0, args.e227)
    import e227_common, e227_model
    if '2026-27' not in e227_common.SEASONS:
        e227_common.SEASONS.append('2026-27')

    F = e227_model.n_feat('stats')
    base = e227_common.load_rows(SEASONS_ORD)
    extra = load_extra(os.path.join(args.e306, 'stints-2627.csv.gz'))
    feat_cache = {s: build_features(s, e227_model, e227_common, decay=0.55, k_shrink=300.0, use_rapm=False) for s in SEASONS_ORD}
    z = np.load(os.path.join(args.e306, 'feat-full.npz'))
    feat_cache['2026-27'] = {str(p): (z['vals'][i], z['mask'][i]) for i, p in enumerate(z['pids'])}

    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    wdir = os.path.join(args.out, 'weights_full')
    os.makedirs(wdir, exist_ok=True)
    arch = 'lineup' if args.arm == 'M2_full' else 'add'

    logs = []
    for fold in range(5):
        tr = [r for r in base if r['fold'] != fold] + extra
        va = [r for r in base if r['fold'] == fold]
        means = e227_model.season_means(tr)
        s2 = e227_model.sigma2_of(tr, means)
        Tt = swap_augment(build_tensors(tr, feat_cache, means, F))
        Tv = build_tensors(va, feat_cache, means, F)
        for s_i in range(2):
            sd = fold * 2 + s_i
            wf = os.path.join(wdir, f'{args.arm}-f{fold}-s{sd}.pt')
            if os.path.exists(wf):
                print('skip', wf, flush=True); continue
            info, state = train_one(arch, fold, sd, Tt, Tv, s2, dev)
            torch.save(state, wf + '.tmp'); os.replace(wf + '.tmp', wf)
            logs.append(info)
            print(f'{args.arm} f{fold} s{sd}: val={info["valLoss"]:.5f} ep={info["bestEpoch"]} ({info["seconds"]}s)', flush=True)

    json.dump({'arm': args.arm, 'extraRows': len(extra), 'logs': logs}, open(os.path.join(args.out, f'meta-{args.arm}.json'), 'w'), indent=1)
    print('DONE', args.arm, flush=True)


if __name__ == '__main__':
    main()
