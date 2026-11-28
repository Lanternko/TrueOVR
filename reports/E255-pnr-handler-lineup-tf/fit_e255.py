"""E-255 5090 訓練與推論腳本（由 E-245 fit 改寫：替換 mid 欄 → 新增第 16 欄 pnr 擋拆持球；臂 T0／W00–W10／WL，無 T1）。
原 E-245 說明：
在 E-227 R2-abil 的陣容 Transformer（LineupNet，5 季 111,499 個訓練 stints，fold 0 早停，5 顆種子 0–4）上，
固定其餘 14 項能力值，只替換 mid 欄（中距離能力值，ATTRS 第 2 欄；2021-22 無分區資料，混合臂退回卡片 mid）：
- T0：不放中距離（value=0, mask=0）
- T1：現行卡片 mid
- W00, W02, W04, W05, W06, W08, W10：w ∈ {0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0} 的 (w·pv + (1-w)·pa) 季內單位變異數 z 分數
- WL：端到端可學習權重 w = sigmoid(alpha)，前 3 epoch 固定 w=0.5 暖身，第 4 epoch 起放開 alpha（lr=0.01, wd=0.0）

每臂訓練完 5 顆種子後，立即在 GPU 上輸出：
1. fold0（27,533 stints）、test（34,624 stints，split=test）、cross_test（2022-23～2025-26 用前一季球員表預測當季 split=test stints）
   的每場比賽進攻得分誤差（pts100_MSE 分子分母）、淨值誤差（net_MSE 分子分母）、失誤與進攻籃板 log-loss。
2. E-179 三季（2022-23、2023-24、2024-25，共 867 人次）每位球員在 1000 組隨機 5v5 陣容（RandomState(225)）下的：
   - off_val（個人總進攻影響力，每百回合得分提升，5 顆種子各自的值）
   - offpnr_val（個人中距離邊際進攻影響力：實際中距離能力值 vs 聯盟平均 0，每百回合得分提升，5 顆種子各自的值）
   - net_val（個人總淨值影響力，每百回合淨得分提升，5 顆種子各自的值）
3. WL 臂額外輸出 5 顆種子在最佳驗證 epoch 學到的 w = sigmoid(alpha) 及逐 epoch 軌跡。

用法（在 5090 E242 目錄）：
  python -I -B -X utf8 fit_e245.py ARM [ARM ...]
"""
import csv, gzip, hashlib, json, math, os, sys, time
import numpy as np
import torch
import torch.nn as nn

SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
E179_SEASONS = ['2022-23', '2023-24', '2024-25']
WARMS = {'W00': 0.0, 'W02': 0.2, 'W04': 0.4, 'W05': 0.5, 'W06': 0.6, 'W08': 0.8, 'W10': 1.0}
SEEDS = range(5)
POS_MAP = {'PG': 0, 'SG': 1, 'SF': 2, 'PF': 3, 'C': 4, 'G': 1, 'F': 3}

P_JSON = json.load(open('e255_players.json', encoding='utf-8'))
ATTRS = P_JSON['attrs']
NF = len(ATTRS)  # 16（E-245 的 15 欄＋pnr）
SLOT = ATTRS.index('pnr')  # E-255：新增的擋拆持球欄（T0＝不放）


def hmod(tag, gid, m):
    return int(hashlib.sha256(f'E225|{tag}|{gid}'.encode()).hexdigest()[:8], 16) % m


def load_stints(stint_dir):
    tr_rows, f0_rows, te_rows = [], [], []
    for s in SEASONS:
        path = os.path.join(stint_dir, f'stints-{s}.csv.gz')
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                for k in ('possa', 'possb', 'ptsa', 'ptsb', 'tova', 'tovb', 'orba', 'orbb', 'rebOppa', 'rebOppb', 'sec'):
                    r[k] = float(r[k]) if r[k] != '' else math.nan
                for k in [f'p{x}{j}' for x in 'ab' for j in range(5)]:
                    r[k] = int(r[k])
                r['season'] = s
                gid = r['gid']
                if hmod('test', gid, 100) < 20:
                    r['split'] = 'test'
                    r['fold'] = -1
                    te_rows.append(r)
                else:
                    r['split'] = 'train'
                    r['fold'] = hmod('fold', gid, 5)
                    if r['fold'] == 0:
                        f0_rows.append(r)
                    else:
                        tr_rows.append(r)
    return tr_rows, f0_rows, te_rows


def season_means(rows):
    out = {}
    for s in SEASONS:
        rs = [r for r in rows if r['season'] == s]
        out[s] = sum(r['ptsa'] + r['ptsb'] for r in rs) / sum(r['possa'] + r['possb'] for r in rs)
    return out


def sigma2_of(rows, means):
    num = den = 0.0
    for r in rows:
        for x in 'ab':
            p = r['poss' + x]
            if p > 0:
                num += p * (r['pts' + x] / p - means[r['season']]) ** 2
                den += p
    return num / den


def player_lookup(season, arm, mode='train'):
    """回傳 pid -> (vec[30], zv, za, rho, m3)。vec 前 15 為值，後 15 為 mask。"""
    tb = P_JSON['player_tables'][season]
    pids = tb['pids']
    bz, bm = tb['base_z'], tb['base_m']
    md = tb['modes'][mode]
    fb = tb.get('fallback', False)
    zv_arr, za_arr, zval_arr, m3_arr = md['zv'], md['za'], md['zval'], md['mask3']
    rho = md['rho']
    out = {}
    for i, pid in enumerate(pids):
        val = [bz[a][i] for a in ATTRS]
        msk = [bm[a][i] for a in ATTRS]
        zv, za, m3 = zv_arr[i], za_arr[i], m3_arr[i]
        if arm == 'T0':
            val[SLOT], msk[SLOT] = 0.0, 0.0
        elif arm == 'T1':
            pass  # 保持 base_z['ft'] 與 base_m['ft']
        elif fb:
            pass  # 2021-22：無分區資料，混合臂與 WL 都退回卡片 mid（m3=0）
        elif arm in WARMS:
            w = WARMS[arm]
            denom = math.sqrt(w * w + (1 - w) ** 2 + 2 * w * (1 - w) * rho + 1e-12)
            val[SLOT] = (w * zv + (1 - w) * za) / denom if m3 > 0 else 0.0
            msk[SLOT] = m3
        elif arm == 'WL':
            val[SLOT] = 0.0
            msk[SLOT] = m3
        else:
            raise ValueError(f'Unknown arm: {arm}')
        vec = np.array(val + msk, dtype=np.float32)
        out[pid] = (vec, float(zv), float(za), float(rho), float(m3))
    return out


def build_stint_tensors(rows, arm, means, mode='train', cross_prev=False):
    N = len(rows)
    attr = np.zeros((N, 10, 2 * NF), np.float32)
    zv_t = np.zeros((N, 10), np.float32)
    za_t = np.zeros((N, 10), np.float32)
    rho_t = np.zeros((N, 10), np.float32)
    m3_t = np.zeros((N, 10), np.float32)
    pos = np.zeros((N, 10), np.int64)
    side = np.tile(np.r_[np.zeros(5), np.ones(5)].astype(np.int64), (N, 1))
    y = np.zeros((N, 2, 6), np.float32)

    lookups = {s: player_lookup(s, arm, mode) for s in SEASONS}
    prev_map = {SEASONS[i]: SEASONS[i - 1] for i in range(1, len(SEASONS))}

    for i, r in enumerate(rows):
        s_feat = prev_map[r['season']] if cross_prev else r['season']
        lk = lookups[s_feat]
        t = 0
        for x in 'ab':
            for j in range(5):
                pid = str(r[f'{x}{j}'])
                item = lk.get(pid)
                if item is not None:
                    attr[i, t] = item[0]
                    zv_t[i, t], za_t[i, t], rho_t[i, t], m3_t[i, t] = item[1], item[2], item[3], item[4]
                pos[i, t] = r[f'p{x}{j}']
                t += 1
        for k, x in enumerate('ab'):
            y[i, k] = [r['pts' + x], r['poss' + x], r['tov' + x], r['orb' + x], r['rebOpp' + x], means[r['season']]]
    return (torch.from_numpy(attr), torch.from_numpy(pos), torch.from_numpy(side),
            torch.from_numpy(y), torch.from_numpy(zv_t), torch.from_numpy(za_t),
            torch.from_numpy(rho_t), torch.from_numpy(m3_t))


class LineupNet(nn.Module):
    def __init__(self, n_feat=16, d=64, layers=2, heads=4, ff=128, drop=0.1, learn_w=False):
        super().__init__()
        self.attr = nn.Linear(2 * n_feat, d)
        self.pos = nn.Embedding(5, d)
        self.side = nn.Embedding(2, d)
        self.cls = nn.Parameter(torch.zeros(2, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=drop, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers, enable_nested_tensor=False)
        self.head = nn.Linear(d, 3)
        self.learn_w = learn_w
        if learn_w:
            self.alpha = nn.Parameter(torch.zeros(1))

    def forward(self, attr, pos, side, zv=None, za=None, rho=None, m3=None):
        if self.learn_w and zv is not None:
            w = torch.sigmoid(self.alpha)
            denom = torch.sqrt(w * w + (1.0 - w) ** 2 + 2.0 * w * (1.0 - w) * rho + 1e-12)
            z3 = (w * zv + (1.0 - w) * za) / denom * m3
            attr = attr.clone()
            attr[..., SLOT] = z3 + (1.0 - m3) * attr[..., SLOT]  # m3=0（2021-22 退回卡片 mid；無資料者本來就是 0）
        x = self.attr(attr) + self.pos(pos) + self.side(side)
        c = self.cls.unsqueeze(0).expand(x.shape[0], -1, -1) + self.side.weight.unsqueeze(0)
        h = self.enc(torch.cat([c, x], 1))
        return self.head(h[:, :2])


def loss_fn(out, y, sigma2):
    pts, poss, tov, orb, opp, mean = y.unbind(-1)
    rate = torch.where(poss > 0, pts / poss.clamp(min=1e-6), mean) - mean
    l_pts = (poss * (out[..., 0] - rate) ** 2).sum() / poss.sum() / sigma2
    p_t = torch.sigmoid(out[..., 1]).clamp(1e-5, 1 - 1e-5)
    tv = tov.clamp(max=poss)
    l_tov = -(tv * p_t.log() + (poss - tv).clamp(min=0) * (1 - p_t).log()).sum() / poss.sum()
    p_o = torch.sigmoid(out[..., 2]).clamp(1e-5, 1 - 1e-5)
    ob = orb.clamp(max=opp)
    l_orb = -(ob * p_o.log() + (opp - ob).clamp(min=0) * (1 - p_o).log()).sum() / opp.sum().clamp(min=1)
    return l_pts + l_tov + l_orb, (l_pts.item(), l_tov.item(), l_orb.item())


def predict_batches(net, T, dev, bs=8192):
    net.eval()
    outs = []
    with torch.no_grad():
        for b in range(0, len(T[0]), bs):
            eb = min(len(T[0]), b + bs)
            if net.learn_w:
                o = net(T[0][b:eb].to(dev), T[1][b:eb].to(dev), T[2][b:eb].to(dev),
                        T[4][b:eb].to(dev), T[5][b:eb].to(dev), T[6][b:eb].to(dev), T[7][b:eb].to(dev))
            else:
                o = net(T[0][b:eb].to(dev), T[1][b:eb].to(dev), T[2][b:eb].to(dev))
            outs.append(o.cpu())
    return torch.cat(outs).numpy()


def train_seed(arm, seed, Tt, Tv, sigma2, dev, max_epochs=60, patience=5, bs=1024):
    torch.manual_seed(seed)
    np.random.seed(seed)
    learn_w = (arm == 'WL')
    net = LineupNet(NF, learn_w=learn_w).to(dev)
    if learn_w:
        base_params = [p for n, p in net.named_parameters() if n != 'alpha']
        opt = torch.optim.AdamW([
            {'params': base_params, 'lr': 1e-3, 'weight_decay': 0.1},
            {'params': [net.alpha], 'lr': 1e-2, 'weight_decay': 0.0},
        ])
    else:
        opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1)

    Tt_d = [t.to(dev) for t in Tt]
    Tv_d = [t.to(dev) for t in Tv]
    best, best_ep, best_state, bad = 1e9, 0, None, 0
    w_hist = []
    for ep in range(1, max_epochs + 1):
        if learn_w:
            net.alpha.requires_grad_(ep > 3)
        net.train()
        perm = torch.randperm(len(Tt_d[0]), device=dev)
        for b in range(0, len(perm), bs):
            ix = perm[b:b + bs]
            if learn_w:
                out = net(Tt_d[0][ix], Tt_d[1][ix], Tt_d[2][ix],
                          Tt_d[4][ix], Tt_d[5][ix], Tt_d[6][ix], Tt_d[7][ix])
            else:
                out = net(Tt_d[0][ix], Tt_d[1][ix], Tt_d[2][ix])
            loss, _ = loss_fn(out, Tt_d[3][ix], sigma2)
            opt.zero_grad()
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            if learn_w:
                vout = torch.cat([net(Tv_d[0][b:b + 4096], Tv_d[1][b:b + 4096], Tv_d[2][b:b + 4096], Tv_d[4][b:b + 4096],
                                      Tv_d[5][b:b + 4096], Tv_d[6][b:b + 4096], Tv_d[7][b:b + 4096])
                                  for b in range(0, len(Tv_d[0]), 4096)])  # 分批只為省 GPU 記憶體（5090 被他人占用），數值等價
                w_cur = float(torch.sigmoid(net.alpha).item())
                w_hist.append(round(w_cur, 5))
            else:
                vout = net(Tv_d[0], Tv_d[1], Tv_d[2])
            tot, parts = loss_fn(vout, Tv_d[3], sigma2)
        if tot.item() < best - 1e-6:
            best, best_ep, bad = tot.item(), ep, 0
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict({k: v.to(dev) for k, v in best_state.items()})
    w_best = float(torch.sigmoid(net.alpha).item()) if learn_w else WARMS.get(arm, None)
    return net, {'seed': seed, 'valLoss': round(best, 5), 'bestEpoch': best_ep, 'w_best': w_best, 'w_hist': w_hist}


def game_metrics(rows, y_np, P_seeds):
    """回傳每個評估集上的 ensemble 與單種子 MSE，以及按場次加總的分子分母供本機成對 bootstrap。"""
    pts2, poss2, tov2, orb2, opp2, mean2 = y_np.reshape(-1, 6).T
    games = list(dict.fromkeys(r['gid'] for r in rows))
    gmap = {g: k for k, g in enumerate(games)}
    G = len(games)
    gi = np.array([gmap[r['gid']] for r in rows])
    gi2 = np.repeat(gi, 2)
    possA, possB = poss2[0::2], poss2[1::2]
    Pw = (possA + possB) / 2.0
    actual_net = np.where(Pw > 0, 100.0 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw, 1e-9), 0.0)
    rate100 = 100.0 * (np.where(poss2 > 0, pts2 / np.maximum(poss2, 1e-9), mean2) - mean2)

    def calc(P_arr):
        pts_pred = P_arr[..., 0].reshape(-1)
        pts100_pred = 100.0 * pts_pred
        muA, muB = pts_pred[0::2] + mean2[0::2], pts_pred[1::2] + mean2[1::2]
        net_pred = 100.0 * (muA * possA - muB * possB) / np.maximum(Pw, 1e-9)
        num_pts = np.bincount(gi2, poss2 * (rate100 - pts100_pred) ** 2, G)
        den_pts = np.bincount(gi2, poss2, G)
        num_net = np.bincount(gi, Pw * (actual_net - net_pred) ** 2, G)
        den_net = np.bincount(gi, Pw, G)
        return (float(num_pts.sum() / den_pts.sum()),
                float(num_net.sum() / den_net.sum()),
                num_pts, den_pts, num_net, den_net)

    ens_P = P_seeds.mean(0)
    pts_mse, net_mse, n_pts, d_pts, n_net, d_net = calc(ens_P)
    seed_pts = [calc(P_seeds[s])[0] for s in range(len(P_seeds))]
    seed_net = [calc(P_seeds[s])[1] for s in range(len(P_seeds))]
    return {
        'games': G, 'stints': len(rows),
        'pts100_mse': round(pts_mse, 4), 'net_mse': round(net_mse, 4),
        'seed_pts100_mse': [round(x, 4) for x in seed_pts],
        'seed_net_mse': [round(x, 4) for x in seed_net],
        'game_num_pts': [round(float(x), 4) for x in n_pts],
        'game_den_pts': [round(float(x), 4) for x in d_pts],
        'game_num_net': [round(float(x), 4) for x in n_net],
        'game_den_net': [round(float(x), 4) for x in d_net],
    }


def eval_e179_values(nets, arm, dev, ndraw=1000):
    """對 E-179 三季（2022-23, 2023-24, 2024-25，共 867 人次）算每位球員的 off_val, offpnr_val, net_val（5 顆種子）。"""
    POS_T = torch.tensor(list(range(5)) * 2, device=dev).unsqueeze(0)
    SIDE_T = torch.tensor([0] * 5 + [1] * 5, device=dev).unsqueeze(0)
    out = {}
    for t in E179_SEASONS:
        lk = player_lookup(t, arm, mode='full')
        d = P_JSON['e179'][t]
        ids = [str(x) for x in d['ids']]
        pos = [POS_MAP[p] for p in d['pos']]
        M = len(ids)
        vecs = np.zeros((M, 2 * NF), np.float32)
        for i, pid in enumerate(ids):
            item = lk[pid]
            vec, zv, za, rho, m3 = item[0].copy(), item[1], item[2], item[3], item[4]
            vecs[i] = vec
        # 5 顆種子的實際特徵（WL 每顆種子的 w 不同）
        vecs_by_seed = []
        vecs0_by_seed = []
        for sd, net in enumerate(nets):
            v_s = vecs.copy()
            if arm == 'WL':
                w = float(torch.sigmoid(net.alpha).item())
                for i, pid in enumerate(ids):
                    _, zv, za, rho, m3 = lk[pid]
                    denom = math.sqrt(w * w + (1 - w) ** 2 + 2 * w * (1 - w) * rho + 1e-12)
                    v_s[i, SLOT] = (w * zv + (1 - w) * za) / denom if m3 > 0 else 0.0
            v0_s = v_s.copy()
            v0_s[:, SLOT] = 0.0  # 擋拆設為聯盟平均 0
            vecs_by_seed.append(torch.from_numpy(v_s).to(dev))
            vecs0_by_seed.append(torch.from_numpy(v0_s).to(dev))

        rs = np.random.RandomState(225)
        pool = {k: [i for i, q in enumerate(pos) if q == k] for k in range(5)}
        uT = rs.rand(ndraw, 5)
        uO = rs.rand(ndraw, 5)
        uR = rs.rand(ndraw)

        off_s = np.zeros((len(nets), M))
        offpnr_s = np.zeros((len(nets), M))
        net_s = np.zeros((len(nets), M))

        with torch.no_grad():
            for sd, net in enumerate(nets):
                net.eval()
                V = vecs_by_seed[sd]
                V0 = vecs0_by_seed[sd]
                PV = {k: V[pool[k]] for k in range(5)}
                tm_base = torch.stack([PV[q][(uT[:, q] * len(pool[q])).astype(int)] for q in range(5)], 1)
                op_base = torch.stack([PV[q][(uO[:, q] * len(pool[q])).astype(int)] for q in range(5)], 1)
                outs = []
                for g0 in range(0, M, 8):  # 分批 8 位球員（省 GPU 記憶體；數值與一次全算等價）
                    X_chunks = []
                    for ii in range(g0, min(M, g0 + 8)):
                        k = pos[ii]
                        me = pool[k].index(ii)
                        pk = len(pool[k])
                        jr = (uR * (pk - 1)).astype(int)
                        jr = jr + (jr >= me)
                        ta = tm_base.clone(); ta[:, k] = V[ii]
                        t0 = tm_base.clone(); t0[:, k] = V0[ii]
                        tr = tm_base.clone(); tr[:, k] = PV[k][jr]
                        X_chunks.append(torch.cat([
                            torch.cat([ta, op_base], 1),
                            torch.cat([t0, op_base], 1),
                            torch.cat([tr, op_base], 1),
                        ], 0))
                    X_all = torch.cat(X_chunks, 0)
                    N_tot = X_all.shape[0]
                    for b in range(0, N_tot, 4096):
                        eb = min(N_tot, b + 4096)
                        x = net.attr(X_all[b:eb]) + net.pos(POS_T.expand(eb - b, -1)) + net.side(SIDE_T.expand(eb - b, -1))
                        c = net.cls.unsqueeze(0).expand(eb - b, -1, -1) + net.side.weight.unsqueeze(0)
                        h = net.enc(torch.cat([c, x], 1))
                        outs.append(net.head(h[:, :2])[..., 0])
                    del X_all, X_chunks
                O_all = torch.cat(outs, 0).reshape(M, 3, ndraw, 2).cpu().numpy()
                # O_all[:, 0] = with player, O_all[:, 1] = with 3PT=0, O_all[:, 2] = replacement
                off_s[sd] = 100.0 * (O_all[:, 0, :, 0] - O_all[:, 2, :, 0]).mean(1)
                offpnr_s[sd] = 100.0 * (O_all[:, 0, :, 0] - O_all[:, 1, :, 0]).mean(1)
                net_a = (O_all[:, 0, :, 0] - O_all[:, 0, :, 1]) - (O_all[:, 2, :, 0] - O_all[:, 2, :, 1])
                net_s[sd] = 100.0 * net_a.mean(1)

        out[t] = {
            'ids': d['ids'],
            'off_val': [[round(float(x), 5) for x in off_s[s]] for s in range(len(nets))],
            'offpnr_val': [[round(float(x), 5) for x in offpnr_s[s]] for s in range(len(nets))],
            'net_val': [[round(float(x), 5) for x in net_s[s]] for s in range(len(nets))],
        }
    return out


def main():
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    stint_dir = os.environ.get('E225_STINT_DIR', '../E225-lineup-transformer/data')
    tr_rows, f0_rows, te_rows = load_stints(stint_dir)
    cross_te_rows = [r for r in te_rows if r['season'] != '2021-22']
    means = season_means(tr_rows)
    sigma2 = sigma2_of(tr_rows, means)

    for arm in sys.argv[1:]:
        t0 = time.time()
        Tt = build_stint_tensors(tr_rows, arm, means, mode='train', cross_prev=False)
        Tv = build_stint_tensors(f0_rows, arm, means, mode='train', cross_prev=False)
        Tte = build_stint_tensors(te_rows, arm, means, mode='train', cross_prev=False)
        Tcr = build_stint_tensors(cross_te_rows, arm, means, mode='full', cross_prev=True)

        nets, seed_info = [], []
        for s in SEEDS:
            net, info = train_seed(arm, s, Tt, Tv, sigma2, dev)
            nets.append(net)
            seed_info.append(info)
            print(f'[{arm}] seed {s} ep={info["bestEpoch"]} val={info["valLoss"]} w={info["w_best"]} ({time.time()-t0:.1f}s)', flush=True)

        P_f0 = np.stack([predict_batches(n, Tv, dev) for n in nets])
        P_te = np.stack([predict_batches(n, Tte, dev) for n in nets])
        P_cr = np.stack([predict_batches(n, Tcr, dev) for n in nets])

        res = {
            'arm': arm,
            'seeds': seed_info,
            'fold0': game_metrics(f0_rows, Tv[3].numpy(), P_f0),
            'test': game_metrics(te_rows, Tte[3].numpy(), P_te),
            'cross_test': game_metrics(cross_te_rows, Tcr[3].numpy(), P_cr),
            'e179': eval_e179_values(nets, arm, dev, ndraw=1000),
            'seconds': round(time.time() - t0, 1),
        }
        json.dump(res, open(f'out-{arm}.json', 'w'))
        print(f'=== DONE {arm} in {res["seconds"]}s | test pts100_mse={res["test"]["pts100_mse"]} net_mse={res["test"]["net_mse"]} ===', flush=True)


if __name__ == '__main__':
    main()
