"""E-316（gpu5090）：T1 四季輪換盲測（Leave-One-Season-Out：2022-23～2025-26，4,920 場）。
每折遮住 val_season，用其餘 4 季（2021-22～2025-26 扣 val_season）訓練 ENS_MD（10×M2 + 10×D_add），
再推論 val_season 全部 1,230 場（嚴格只用 val_season-1 賽前多季特徵），最後跑 C0/C1/C2/C3/C3_ENS 評估。"""
import argparse, csv, gzip, json, math, os, sys, time
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
ALL_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
VAL_SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']


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
                    attr[i, t, :F] = p[0]; attr[i, t, F:] = p[1]
                pos[i, t] = r[f'p{x}{j}']; t += 1
        m = means[r['season']]
        for k, x in enumerate('ab'):
            y[i, k] = [r['pts' + x], r['poss' + x], r['tov' + x], r['orb' + x], r['rebOpp' + x], m]
    return [torch.from_numpy(a) for a in (attr, pos, side, y)]


def swap_augment(T):
    attr, pos, side, y = T
    return [
        torch.cat([attr, torch.cat([attr[:, 5:], attr[:, :5]], 1)], 0),
        torch.cat([pos, torch.cat([pos[:, 5:], pos[:, :5]], 1)], 0),
        torch.cat([side, side], 0),
        torch.cat([y, torch.stack([y[:, 1], y[:, 0]], 1)], 0),
    ]


def train_one(arch, fold, seed, Tt, Tv, s2, dev, e315_lib):
    torch.manual_seed(seed); np.random.seed(seed)
    F = Tt[0].shape[-1] // 2
    net = (e315_lib.LineupNetA1(F) if arch == 'lineup' else e315_lib.AdditiveOnlyNet(F)).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=(0.10 if arch == 'lineup' else 0.15))
    Tt_d = [t.to(dev) for t in Tt]; Tv_d = [t.to(dev) for t in Tv]
    best, best_state, bad = 1e9, None, 0
    for ep in range(1, 61):
        net.train()
        perm = torch.randperm(len(Tt_d[0]), device=dev)
        for b in range(0, len(perm), 1024):
            ix = perm[b:b + 1024]
            loss, _ = e315_lib.loss_b0(net(Tt_d[0][ix], Tt_d[1][ix], Tt_d[2][ix]), Tt_d[3][ix], s2)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
        net.eval()
        with torch.no_grad():
            outs = [net(Tv_d[0][b:b + 4096], Tv_d[1][b:b + 4096], Tv_d[2][b:b + 4096]) for b in range(0, len(Tv_d[0]), 4096)]
            tot, _ = e315_lib.loss_b0(torch.cat(outs, 0), Tv_d[3], s2)
        if tot.item() < best - 1e-6:
            best, bad = tot.item(), 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= 8:
                break
    net.load_state_dict(best_state); net.eval()
    return net


def predict_season(val_season, m2_nets, da_nets, prior_season, e227_dir, data_dir, e227_common, e227_model, e315_lib, dev):
    F = e227_model.n_feat('stats')
    tab = e227_common.load_player_table(prior_season)
    B = e315_lib.build_features(prior_season, e227_model, e227_common, decay=0.55, k_shrink=300.0, use_rapm=False)
    med_h = float(np.median([d['heightInches'] for d in tab.values() if d.get('heightInches') is not None]))

    poss = 0.0; gids = set()
    with gzip.open(os.path.join(e227_dir, 'data', f'stints-train-{prior_season}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['possa'] != '' and r['possb'] != '':
                poss += float(r['possa']) + float(r['possb']); gids.add(r['gid'])
    avg_poss = poss / 2.0 / len(gids)

    def vec(p):
        v = B.get(str(p))
        return np.zeros(2 * F, np.float32) if v is None else np.concatenate([v[0], v[1]]).astype(np.float32)

    def hkey(p):
        d = tab.get(str(p)) or {}
        h = d.get('heightInches'); h = med_h if h is None else h
        return (h, -((d.get('pass') or 0.0) + (d.get('creation') or 0.0)), str(p))

    def prep(rot):
        pids = [p for p, m in rot]; mins = np.array([m for p, m in rot], float)
        order = sorted(range(len(pids)), key=lambda j: hkey(pids[j]))
        rank = np.empty(len(pids), int); rank[order] = np.arange(len(pids))
        return np.stack([vec(p) for p in pids]), np.log(mins), rank

    def draw(R, lm, rank, rng, N):
        g = lm[None, :] + rng.gumbel(size=(N, len(lm)))
        top = np.argsort(-g, axis=1)[:, :5]
        return R[np.take_along_axis(top, np.argsort(rank[top], axis=1), axis=1)]

    games = json.load(open(os.path.join(data_dir, f't1-games-{val_season}.json'), encoding='utf-8'))['games']
    lin = json.load(open(os.path.join(data_dir, f't1-lineups-{val_season}.json'), encoding='utf-8'))
    POS = torch.tensor(list(range(5)) * 2).unsqueeze(0)
    SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
    N = 1000  # 1000 抽樣 × 10 模型，4 季 4,920 場約 3 分鐘跑完，SE < 0.05 分
    m_m2 = np.zeros(len(games)); m_da = np.zeros(len(games))
    t0 = time.time()

    for k, g in enumerate(games):
        i = g['i']
        Rh, lh, rh = prep(lin[f'{i}h']); Ra, la, ra = prep(lin[f'{i}a'])
        rng = np.random.default_rng([316, i])
        H5 = draw(Rh, lh, rh, rng, N); A5 = draw(Ra, la, ra, rng, N)
        X = torch.from_numpy(np.concatenate([np.concatenate([H5, A5], 1), np.concatenate([A5, H5], 1)], 0)).to(dev)
        p_t = POS.expand(2 * N, -1).to(dev); s_t = SIDE.expand(2 * N, -1).to(dev)
        with torch.no_grad():
            o_m2 = [0.5 * ((m(X, p_t, s_t)[:, :, 0].cpu().numpy()[:N, 0] - m(X, p_t, s_t)[:, :, 0].cpu().numpy()[:N, 1]).mean()
                           - (m(X, p_t, s_t)[:, :, 0].cpu().numpy()[N:, 0] - m(X, p_t, s_t)[:, :, 0].cpu().numpy()[N:, 1]).mean())
                    for m in m2_nets]
            o_da = [0.5 * ((m(X, p_t, s_t)[:, :, 0].cpu().numpy()[:N, 0] - m(X, p_t, s_t)[:, :, 0].cpu().numpy()[:N, 1]).mean()
                           - (m(X, p_t, s_t)[:, :, 0].cpu().numpy()[N:, 0] - m(X, p_t, s_t)[:, :, 0].cpu().numpy()[N:, 1]).mean())
                    for m in da_nets]
        m_m2[k] = float(np.mean(o_m2)) * avg_poss
        m_da[k] = float(np.mean(o_da)) * avg_poss
        if k % 400 == 0:
            print(f'  pred {val_season} {k}/{len(games)} {round(time.time()-t0)}s', flush=True)
    return m_m2.tolist(), m_da.tolist(), avg_poss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--e227', required=True)
    ap.add_argument('--e315', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seasons', default='2022-23,2023-24,2024-25,2025-26')
    args = ap.parse_args()

    sys.path.insert(0, args.e227)
    sys.path.insert(0, args.e315)
    import e227_common, e227_model, e315_lib

    os.makedirs(args.out, exist_ok=True)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    F = e227_model.n_feat('stats')
    feat_cache = {s: e315_lib.build_features(s, e227_model, e227_common, decay=0.55, k_shrink=300.0, use_rapm=False) for s in ALL_SEASONS}

    for vs in args.seasons.split(','):
        out_f = os.path.join(args.out, f'loso-{vs}.json')
        if os.path.exists(out_f):
            print('skip', vs, flush=True); continue
        t0 = time.time()
        tr_seasons = [s for s in ALL_SEASONS if s != vs]
        prior_s = ALL_SEASONS[ALL_SEASONS.index(vs) - 1]
        print(f'=== LOSO val={vs} (train={tr_seasons}, prior={prior_s}) ===', flush=True)
        rows = e227_common.load_rows(tr_seasons)
        m2_nets, da_nets = [], []
        for fold in range(5):
            tr = [r for r in rows if r['fold'] != fold]
            va = [r for r in rows if r['fold'] == fold]
            means = e227_model.season_means(tr); s2 = e227_model.sigma2_of(tr, means)
            Tt = swap_augment(build_tensors(tr, feat_cache, means, F))
            Tv = build_tensors(va, feat_cache, means, F)
            for s_i in range(2):
                sd = fold * 2 + s_i
                m2_nets.append(train_one('lineup', fold, sd, Tt, Tv, s2, dev, e315_lib))
                da_nets.append(train_one('add', fold, sd, Tt, Tv, s2, dev, e315_lib))
        print(f'  trained 20 models in {round(time.time()-t0)}s', flush=True)
        m_m2, m_da, avg_poss = predict_season(vs, m2_nets, da_nets, prior_s, args.e227, args.data, e227_common, e227_model, e315_lib, dev)
        json.dump({'val_season': vs, 'prior_season': prior_s, 'avg_poss': avg_poss, 'm_m2': m_m2, 'm_da': m_da}, open(out_f, 'w'))
        print(f'DONE LOSO {vs} total {round(time.time()-t0)}s', flush=True)


if __name__ == '__main__':
    main()
