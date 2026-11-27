"""E-317（gpu5090-3）：P1 滾動往前考場訓練與五臂評估（P_STATIC / P_SLOW / P_FAST / P_DUAL / P_NN）。
訓練集：2022-23～2024-25（s_idx ∈ {1,2,3}）；盲測集：2025-26 全季（s_idx=4）＋ 2026-27 本季（s_idx=5）。"""
import argparse, json, math, os, time
import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression


class RollingPlayerNet(nn.Module):
    """殘差 MLP：吃 31 維因果滾動特徵（多季底盤＋年齡＋本季累計＋近 5/10 場短窗），輸出預測發揮值。"""
    def __init__(self, in_dim, d=128, drop=0.15):
        super().__init__()
        self.inp = nn.Sequential(nn.Linear(in_dim, d), nn.LayerNorm(d), nn.GELU())
        self.b1 = nn.Sequential(nn.Linear(d, d), nn.LayerNorm(d), nn.GELU(), nn.Dropout(drop), nn.Linear(d, d), nn.LayerNorm(d))
        self.b2 = nn.Sequential(nn.Linear(d, d), nn.LayerNorm(d), nn.GELU(), nn.Dropout(drop), nn.Linear(d, d), nn.LayerNorm(d))
        self.head = nn.Linear(d, 1)

    def forward(self, x):
        h = self.inp(x)
        h = h + self.b1(h)
        h = h + self.b2(h)
        return self.head(h).squeeze(-1)


def to_ovr_scale(raw, ref_raw):
    """將原始發揮分數線性映射到 OVR 量尺（ref PR50→70, PR90→88），嚴格單調不改排序。"""
    p50 = float(np.percentile(ref_raw, 50))
    p90 = float(np.percentile(ref_raw, 90))
    return 70.0 + (raw - p50) * (18.0 / max(1e-6, p90 - p50))


def eval_arm(name, ovr_all, y_next, y_fut5, meta, tr_mask, te_masks):
    """計算：下一場 GmSc Spearman/R²、未來 5 場 GmSc Spearman/R²、下一場勝負 Brier、相鄰場次 |ΔOVR| 中位/P95。"""
    # 在訓練季擬合「兩隊分鐘加權 OVR 差 → 主隊勝率」Logistic（單一斜率＋主場截距，嚴格無洩漏）
    def game_feats(mask):
        idx = np.where(mask)[0]
        by_g = {}
        for i in idx:
            gid = int(meta[i, 2]); is_h = int(meta[i, 4]); mn = float(meta[i, 5]); win = int(meta[i, 6])
            g = by_g.setdefault(gid, [0.0, 0.0, 0.0, 0.0, -1])  # h_sum, h_m, a_sum, a_m, h_win
            if is_h:
                g[0] += ovr_all[i] * mn; g[1] += mn; g[4] = win
            else:
                g[2] += ovr_all[i] * mn; g[3] += mn
        X_g, y_g = [], []
        for gid, (hs, hm, as_, am, hw) in sorted(by_g.items()):
            if hm > 100 and am > 100 and hw in (0, 1):
                X_g.append([(hs / hm) - (as_ / am)])
                y_g.append(hw)
        return np.array(X_g), np.array(y_g)

    Xtr_g, ytr_g = game_feats(tr_mask)
    clf = LogisticRegression(C=1.0).fit(Xtr_g, ytr_g)

    res = {}
    for tag, m in te_masks.items():
        ix = np.where(m)[0]
        o = ovr_all[ix]; yn = y_next[ix]; y5 = y_fut5[ix]
        rho1 = float(spearmanr(o, yn)[0])
        rho5 = float(spearmanr(o, y5)[0])
        # R²（在測試季上用訓練季線性回歸尺度或相關平方）
        r2_1 = float(np.corrcoef(o, yn)[0, 1] ** 2)
        r2_5 = float(np.corrcoef(o, y5)[0, 1] ** 2)

        Xg, yg = game_feats(m)
        p = np.clip(clf.predict_proba(Xg)[:, 1], 1e-6, 1.0 - 1e-6)
        brier = float(((p - yg) ** 2).mean())

        # 相鄰場次 |ΔOVR|（同球員、本季第 2 場起）
        prev = meta[ix, 7].astype(int)
        valid = prev >= 0
        deltas = np.abs(ovr_all[ix[valid]] - ovr_all[prev[valid]])
        d_med = float(np.median(deltas)) if len(deltas) else 0.0
        d_p95 = float(np.percentile(deltas, 95)) if len(deltas) else 0.0

        res[tag] = {
            'n_rows': int(len(ix)), 'n_games': int(len(yg)),
            'next_rho': round(rho1, 4), 'next_r2': round(r2_1, 4),
            'fut5_rho': round(rho5, 4), 'fut5_r2': round(r2_5, 4),
            'game_brier': round(brier, 5),
            'delta_med': round(d_med, 3), 'delta_p95': round(d_p95, 3),
            'smooth_pass': bool(d_med <= 0.8 and d_p95 <= 2.5),
        }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    D = np.load(args.data)
    X, y_next, y_fut5, meta = D['X'], D['y_next'], D['y_fut5'], D['meta']
    s_idx = meta[:, 0].astype(int)
    tr_mask = (s_idx >= 1) & (s_idx <= 3)      # 2022-23, 2023-24, 2024-25
    te25_mask = (s_idx == 4)                   # 2025-26 全季
    te26_mask = (s_idx == 5)                   # 2026-27 本季
    te_all = te25_mask | te26_mask
    te_masks = {'2025-26': te25_mask, '2026-27': te26_mask, 'combined': te_all}

    # 標準化（只用訓練季）
    mu = X[tr_mask].mean(0); sd = X[tr_mask].std(0) + 1e-6
    Xz = (X - mu) / sd

    # 1. 四組公式對照臂（純因果）
    # 欄位索引：0=prior_g36, 9=prior_mpg, 12=age_z, 13=young, 14=old, 15=log1p(c_min), 17=c_mpg, 18=c_g36, 27=ew5_gs, 28=ew10_gs, 29=ew5_min, 30=ew10_min
    prior_gs = X[:, 0] * X[:, 9] / 36.0
    c_min = np.expm1(X[:, 15])
    cur_gs = X[:, 18] * X[:, 17] / 36.0

    # P_STATIC：純多季靜態底盤
    raw_static = prior_gs
    # P_SLOW：現行慢窗口 w = c_min / (c_min + 500)
    w_slow = c_min / (c_min + 500.0)
    raw_slow = (1.0 - w_slow) * prior_gs + w_slow * cur_gs
    # P_FAST：過度劇烈近 5 場 EWMA（60% 近 5 場＋40% 底盤）
    raw_fast = 0.4 * prior_gs + 0.6 * X[:, 27]
    # P_DUAL：雙時間尺度自適應（年齡修正底盤 ＋ 自適應中層 k=280 ＋ 溫和近 10 場殘差 0.15）
    age_adj = 0.8 * X[:, 13] - 0.6 * X[:, 14]
    w_mid = c_min / (c_min + 280.0)
    base_dual = prior_gs + age_adj
    raw_dual = (1.0 - w_mid) * base_dual + w_mid * (0.85 * cur_gs + 0.15 * X[:, 28])

    # 2. P_NN（gpu5090-3 訓練 RollingPlayerNet，多目標：下一場＋未來5場＋相鄰平滑罰項！）
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    prev_idx = meta[:, 7].astype(int)
    # 內部驗證折用 2024-25（s_idx==3），訓練用 2022-23 + 2023-24（s_idx ∈ {1,2}）；找到最佳 epoch 後 5-seed ensemble 用全部 1..3
    Xt_tr = torch.from_numpy(Xz[tr_mask]).to(dev)
    yn_tr = torch.from_numpy(y_next[tr_mask]).to(dev)
    y5_tr = torch.from_numpy(y_fut5[tr_mask]).to(dev)
    # 建立 tr_mask 內部的 prev 索引對照（用於相鄰場次平滑正則！）
    tr_indices = np.where(tr_mask)[0]
    g2l = {int(g): l for l, g in enumerate(tr_indices)}
    prev_local = np.array([g2l.get(int(prev_idx[g]), -1) for g in tr_indices], dtype=np.int64)
    has_prev_t = torch.from_numpy(prev_local >= 0).to(dev)
    prev_local_t = torch.from_numpy(np.maximum(0, prev_local)).to(dev)

    # 跑三種平滑罰項 λ ∈ {0.0 (無平滑), 0.3 (中度平滑), 1.0 (強平滑)}，各 5 seed ensemble
    nn_arms = {}
    t0 = time.time()
    Xt_all = torch.from_numpy(Xz).to(dev)
    for lam, tag in ((0.0, 'P_NN_lam0'), (0.3, 'P_NN_lam03'), (1.0, 'P_NN_lam10')):
        preds = []
        for sd in range(5):
            torch.manual_seed(317 + sd); np.random.seed(317 + sd)
            net = RollingPlayerNet(Xz.shape[1]).to(dev)
            opt = torch.optim.AdamW(net.parameters(), lr=1.5e-3, weight_decay=0.05)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=25, eta_min=1e-4)
            Ntr = len(Xt_tr)
            for ep in range(25):
                net.train()
                perm = torch.randperm(Ntr, device=dev)
                for b in range(0, Ntr, 2048):
                    ix = perm[b:b + 2048]
                    p_cur = net(Xt_tr[ix])
                    loss_pred = 0.35 * ((p_cur - yn_tr[ix]) ** 2).mean() + 0.65 * ((p_cur - y5_tr[ix]) ** 2).mean()
                    if lam > 0:
                        hp = has_prev_t[ix]
                        if hp.any():
                            p_prev = net(Xt_tr[prev_local_t[ix[hp]]])
                            loss_sm = ((p_cur[hp] - p_prev) ** 2).mean()
                        else:
                            loss_sm = 0.0
                        loss = loss_pred + lam * loss_sm
                    else:
                        loss = loss_pred
                    opt.zero_grad(); loss.backward()
                    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                    opt.step()
                sched.step()
            net.eval()
            with torch.no_grad():
                out = [net(Xt_all[b:b + 8192]).cpu().numpy() for b in range(0, len(Xt_all), 8192)]
                preds.append(np.concatenate(out))
        nn_arms[tag] = np.mean(preds, axis=0)
        print(f'Trained {tag} (5 seeds) in {round(time.time()-t0, 1)}s', flush=True)

    arms_raw = {
        'P_STATIC': raw_static, 'P_SLOW': raw_slow, 'P_FAST': raw_fast, 'P_DUAL': raw_dual,
        **nn_arms,
    }
    results = {}
    print('\n=== E-317 P1 ROLLING FORWARD RESULTS (2025-26 + 2026-27) ===')
    for name, raw in arms_raw.items():
        ovr = to_ovr_scale(raw, raw[tr_mask])
        r = eval_arm(name, ovr, y_next, y_fut5, meta, tr_mask, te_masks)
        results[name] = r
        c = r['combined']
        print(f"  {name:11s}: NextRho={c['next_rho']:.4f} (R2={c['next_r2']:.4f}) | Fut5Rho={c['fut5_rho']:.4f} (R2={c['fut5_r2']:.4f}) | GameBrier={c['game_brier']:.5f} | dMed={c['delta_med']:.3f} dP95={c['delta_p95']:.3f} smooth={c['smooth_pass']}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(results, open(args.out, 'w', encoding='utf-8'), indent=2)
    print('DONE E-317', flush=True)


if __name__ == '__main__':
    main()
