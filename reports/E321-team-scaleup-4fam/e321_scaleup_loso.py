"""E-321（gpu5090）：球隊 Scale-Up —— 4 家族異質集成（160 模型）＋ 年齡曲線（44 欄）＋ 4 季 4,910 場 LOSO。
4 個正交模型家族（每折各訓 10 模型，5-fold × 2 seed + A/B 對稱增強）：
  1. M2_age:      LineupNet (2L Transformer)
  2. D_add_age:   AdditiveOnlyNet (純加性個人 MLP)
  3. SetPool_age: DeepSetPairwiseNet (隊內 Mean+Max+Std 池化 + 進攻/防守雙線性交互)
  4. Ridge_age:   LinearLineupNet (強正則線性加性，超低方差錨點)"""
import argparse, csv, gzip, json, math, os, sys, time
import numpy as np
import torch
import torch.nn as nn

ALL_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
VAL_SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']


class FeatureDropout(nn.Module):
    def __init__(self, p=0.10):
        super().__init__(); self.p = p

    def forward(self, x):
        if not self.training or self.p <= 0.0: return x
        f = x.shape[-1] // 2
        keep = (torch.rand(x.shape[0], x.shape[1], f, device=x.device) >= self.p).float()
        return torch.cat([x[..., :f] * keep / (1.0 - self.p), x[..., f:] * keep], dim=-1)


class DeepSetPairwiseNet(nn.Module):
    """Family 3：隊內 Mean + Max + Std 統計池化（捕捉球星上限與陣容均衡度）＋ 隊間差值/乘積對位交互。"""
    def __init__(self, n_feat, d=64, drop=0.15):
        super().__init__()
        self.fdrop = FeatureDropout(0.10)
        self.enc = nn.Sequential(
            nn.Linear(2 * n_feat, d), nn.LayerNorm(d), nn.GELU(), nn.Dropout(drop),
            nn.Linear(d, d), nn.LayerNorm(d), nn.GELU(),
        )
        self.pos = nn.Embedding(5, d)
        # 每隊池化出 [mean, max, std] = 3d，進攻隊與防守隊合併 [own(3d), opp(3d), own-opp(3d)] = 9d
        self.team_head = nn.Sequential(
            nn.Linear(9 * d, d), nn.LayerNorm(d), nn.GELU(), nn.Dropout(drop),
            nn.Linear(d, 3),
        )

    def _pool(self, h):
        m = h.mean(1)
        mx = h.max(1).values
        sd = h.var(1, unbiased=False).clamp(min=1e-6).sqrt()
        return torch.cat([m, mx, sd], dim=-1)

    def forward(self, attr, pos, side=None):
        h = self.enc(self.fdrop(attr)) + self.pos(pos)
        pa, pb = self._pool(h[:, :5]), self._pool(h[:, 5:])
        oa = self.team_head(torch.cat([pa, pb, pa - pb], dim=-1))
        ob = self.team_head(torch.cat([pb, pa, pb - pa], dim=-1))
        return torch.stack([oa, ob], dim=1)


class LinearLineupNet(nn.Module):
    """Family 4：純線性強正則加性模型（超低方差錨點，結構完全線性不可過擬合）。"""
    def __init__(self, n_feat):
        super().__init__()
        self.w = nn.Linear(2 * n_feat, 6)
        self.pos = nn.Embedding(5, 6)
        self.bias = nn.Parameter(torch.tensor([0.0, -1.9, -1.1]))

    def forward(self, attr, pos, side=None):
        e = self.w(attr) + self.pos(pos)
        ea, eb = e[:, :5], e[:, 5:]
        pts_a = ea[..., 0].mean(1) - eb[..., 1].mean(1) + self.bias[0]
        pts_b = eb[..., 0].mean(1) - ea[..., 1].mean(1) + self.bias[0]
        tov_a = ea[..., 2].mean(1) + eb[..., 3].mean(1) + self.bias[1]
        tov_b = eb[..., 2].mean(1) + ea[..., 3].mean(1) + self.bias[1]
        orb_a = ea[..., 4].mean(1) - eb[..., 5].mean(1) + self.bias[2]
        orb_b = eb[..., 4].mean(1) - ea[..., 5].mean(1) + self.bias[2]
        return torch.stack([torch.stack([pts_a, tov_a, orb_a], -1), torch.stack([pts_b, tov_b, orb_b], -1)], 1)


def load_dob(path):
    dob = {}
    if path and os.path.exists(path):
        bd = json.load(open(path, encoding='utf-8'))
        for pid, s in (bd.get('birthdates', bd) if isinstance(bd, dict) else {}).items():
            if isinstance(s, str) and len(s) >= 4:
                try: dob[str(pid)] = int(s[:4])
                except ValueError: pass
    return dob


def build_features_age(season, e227_model, e227_common, e315_lib, dob):
    """在 41 欄多季特徵上追加 3 欄嚴格因果年齡特徵：[age_z, young_gap, old_gap]（共 44 欄）。"""
    base = e315_lib.build_features(season, e227_model, e227_common, decay=0.55, k_shrink=300.0, use_rapm=False)
    s_yr = int(season[:4])
    out = {}
    for pid, (v, m) in base.items():
        nv = np.zeros(len(v) + 3, np.float32); nm = np.zeros(len(m) + 3, np.float32)
        nv[:len(v)] = v; nm[:len(m)] = m
        if pid in dob:
            age = float(s_yr - dob[pid])
            nv[-3] = (age - 26.0) / 4.0
            nv[-2] = max(0.0, 23.0 - age) / 4.0
            nv[-1] = max(0.0, age - 31.0) / 4.0
            nm[-3:] = 1.0
        out[pid] = (nv, nm)
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


def train_one(fam, seed, Tt, Tv, s2, dev, e315_lib):
    torch.manual_seed(seed); np.random.seed(seed)
    F = Tt[0].shape[-1] // 2
    if fam == 'M2_age':
        net = e315_lib.LineupNetA1(F); wd = 0.10
    elif fam == 'D_add_age':
        net = e315_lib.AdditiveOnlyNet(F); wd = 0.15
    elif fam == 'SetPool_age':
        net = DeepSetPairwiseNet(F); wd = 0.15
    elif fam == 'Ridge_age':
        net = LinearLineupNet(F); wd = 0.50
    else:
        raise ValueError(fam)
    net = net.to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=wd)
    Tt_d = [t.to(dev) for t in Tt]; Tv_d = [t.to(dev) for t in Tv]
    best, best_state, bad = 1e9, None, 0
    for ep in range(1, 61):
        net.train(); perm = torch.randperm(len(Tt_d[0]), device=dev)
        for b in range(0, len(perm), 1024):
            ix = perm[b:b + 1024]
            loss, _ = e315_lib.loss_b0(net(Tt_d[0][ix], Tt_d[1][ix], Tt_d[2][ix]), Tt_d[3][ix], s2)
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step()
        net.eval()
        with torch.no_grad():
            outs = [net(Tv_d[0][b:b + 4096], Tv_d[1][b:b + 4096], Tv_d[2][b:b + 4096]) for b in range(0, len(Tv_d[0]), 4096)]
            tot, _ = e315_lib.loss_b0(torch.cat(outs, 0), Tv_d[3], s2)
        if tot.item() < best - 1e-6:
            best, bad = tot.item(), 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= 8: break
    net.load_state_dict(best_state); net.eval()
    return net


def predict_season(val_season, fam_nets, prior_season, feat_cache, e227_dir, data_dir, e227_common, dev):
    F = len(next(iter(feat_cache[prior_season].values()))[0])
    tab = e227_common.load_player_table(prior_season)
    B = feat_cache[prior_season]
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
    N = 1000
    out_m = {fam: np.zeros(len(games)) for fam in fam_nets}
    t0 = time.time()
    for k, g in enumerate(games):
        i = g['i']
        Rh, lh, rh = prep(lin[f'{i}h']); Ra, la, ra = prep(lin[f'{i}a'])
        rng = np.random.default_rng([321, i])
        H5 = draw(Rh, lh, rh, rng, N); A5 = draw(Ra, la, ra, rng, N)
        X = torch.from_numpy(np.concatenate([np.concatenate([H5, A5], 1), np.concatenate([A5, H5], 1)], 0)).to(dev)
        p_t = POS.expand(2 * N, -1).to(dev); s_t = SIDE.expand(2 * N, -1).to(dev)
        with torch.no_grad():
            for fam, nets in fam_nets.items():
                vals = []
                for m in nets:
                    o = m(X, p_t, s_t)[:, :, 0].cpu().numpy()
                    d = o[:, 0] - o[:, 1]
                    vals.append(float(0.5 * (d[:N].mean() - d[N:].mean())))
                out_m[fam][k] = float(np.mean(vals)) * avg_poss
        if k % 400 == 0:
            print(f'  pred {val_season} {k}/{len(games)} {round(time.time()-t0)}s', flush=True)
    return {fam: v.tolist() for fam, v in out_m.items()}, avg_poss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--e227', required=True); ap.add_argument('--e315', required=True)
    ap.add_argument('--data', required=True); ap.add_argument('--dob', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--seasons', default='2022-23,2023-24,2024-25,2025-26')
    args = ap.parse_args()

    sys.path.insert(0, args.e227); sys.path.insert(0, args.e315)
    import e227_common, e227_model, e315_lib

    os.makedirs(args.out, exist_ok=True)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    dob = load_dob(args.dob)
    feat_cache = {s: build_features_age(s, e227_model, e227_common, e315_lib, dob) for s in ALL_SEASONS}
    F = len(next(iter(feat_cache['2024-25'].values()))[0])
    print(f'E-321 loaded DOB={len(dob)}, F={F} (41 + 3 age)', flush=True)

    fams = ('M2_age', 'D_add_age', 'SetPool_age', 'Ridge_age')
    for vs in args.seasons.split(','):
        out_f = os.path.join(args.out, f'loso4f-{vs}.json')
        if os.path.exists(out_f):
            print('skip', vs, flush=True); continue
        t0 = time.time()
        tr_seasons = [s for s in ALL_SEASONS if s != vs]
        prior_s = ALL_SEASONS[ALL_SEASONS.index(vs) - 1]
        print(f'=== E-321 LOSO val={vs} (prior={prior_s}) ===', flush=True)
        rows = e227_common.load_rows(tr_seasons)
        fam_nets = {fam: [] for fam in fams}
        for fold in range(5):
            tr = [r for r in rows if r['fold'] != fold]; va = [r for r in rows if r['fold'] == fold]
            means = e227_model.season_means(tr); s2 = e227_model.sigma2_of(tr, means)
            Tt = swap_augment(build_tensors(tr, feat_cache, means, F))
            Tv = build_tensors(va, feat_cache, means, F)
            for s_i in range(2):
                sd = fold * 2 + s_i
                for fam in fams:
                    fam_nets[fam].append(train_one(fam, sd, Tt, Tv, s2, dev, e315_lib))
        print(f'  trained 40 models (4 families x 10) in {round(time.time()-t0)}s', flush=True)
        preds, avg_poss = predict_season(vs, fam_nets, prior_s, feat_cache, args.e227, args.data, e227_common, dev)
        json.dump({'val_season': vs, 'prior_season': prior_s, 'avg_poss': avg_poss, 'preds': preds}, open(out_f, 'w'))
        print(f'DONE E-321 {vs} total {round(time.time()-t0)}s', flush=True)


if __name__ == '__main__':
    main()
