"""E-227 基準線：B0 聯盟平均；B1-<臂>＝和對應 Transformer 臂「同樣特徵」的加法模型（場上五人特徵 z 分數按進攻邊、防守邊各加總一組，
無交互作用、無球員 ID；缺值的 z＝0）。得分用加權 ridge（目標＝每回合得分減該季聯盟平均，權重＝回合數）；失誤率、進攻籃板率用同特徵二項 logistic
（L2，加季截距不罰）。λ 一律只在訓練 folds 1-4 內以 fold 輪流留出選，不看 fold 0（評估折）。
RAPM 臂的 RAPM 特徵與 Transformer 同源（訓練列＝out-of-fold 擬合，驗證列＝排除 fold 0 的擬合）。"""
import numpy as np
import torch

from e227_common import SEASONS

LAMS_PTS = [1.0, 10.0, 100.0, 1000.0, 10000.0]
LAMS_LOG = [1e-6, 1e-5, 1e-4, 1e-3]


def side_features(T):
    attr = T[0]; F = attr.shape[-1] // 2
    zA = attr[:, :5, :F].sum(1); zB = attr[:, 5:, :F].sum(1)
    X = torch.stack([torch.cat([zA, zB], 1), torch.cat([zB, zA], 1)], 1).reshape(-1, 2 * F)
    return X.numpy().astype(np.float64), T[3].reshape(-1, 6).numpy().astype(np.float64)


def season_onehot(rows):
    s = np.zeros((len(rows) * 2, len(SEASONS)))
    for i, r in enumerate(rows):
        k = SEASONS.index(r['season']); s[2 * i, k] = 1; s[2 * i + 1, k] = 1
    return s


def fit_ridge(X, y, w, lam):
    return np.linalg.solve(X.T @ (w[:, None] * X) + lam * np.eye(X.shape[1]), X.T @ (w * y))


def fit_logit(X, k, n, lam, iters=100):
    Xt = torch.tensor(X, dtype=torch.float64); kt = torch.tensor(k); nt = torch.tensor(n)
    m = nt > 0; Xt, kt, nt = Xt[m], kt[m], nt[m]
    w = torch.zeros(Xt.shape[1], dtype=torch.float64, requires_grad=True)
    pen = torch.ones_like(w); pen[-len(SEASONS):] = 0
    opt = torch.optim.LBFGS([w], lr=1, max_iter=iters, line_search_fn='strong_wolfe')

    def closure():
        opt.zero_grad(); z = Xt @ w
        loss = (nt * torch.nn.functional.softplus(z) - kt * z).sum() / nt.sum() + lam * (pen * w * w).sum(); loss.backward(); return loss
    opt.step(closure)
    return w.detach().numpy()


def nll_vec(p, k, n):
    p = np.clip(p, 1e-5, 1 - 1e-5)
    return np.where(n > 0, -(k * np.log(p) + (n - k) * np.log(1 - p)), 0.0)


def fit_b1(rows_train, Ttr, rows_eval, Tev):
    """Ttr／Tev＝tensors() 輸出。回傳 (pts_dev[2N], p_tov[2N], p_orb[2N], y_eval[2N,6], λ)。"""
    X, y = side_features(Ttr); S = season_onehot(rows_train); pts, poss, tov, orb, opp, mean = y.T
    rate = np.where(poss > 0, pts / np.maximum(poss, 1e-9), mean) - mean
    fold = np.repeat(np.array([r['fold'] for r in rows_train]), 2); XL = np.hstack([X, S]); folds = sorted(set(fold))
    sig = lambda z: 1 / (1 + np.exp(-z))

    def cv(fit_pred, lams, score):
        res = {lam: sum(score(fit_pred(fold != f, lam), fold == f) for f in folds) for lam in lams}
        return min(res, key=res.get)

    lam_pts = cv(lambda tr, lam: fit_ridge(X[tr], rate[tr], poss[tr], lam), LAMS_PTS, lambda w, va: (poss[va] * (rate[va] - X[va] @ w) ** 2).sum())
    lam_tov = cv(lambda tr, lam: fit_logit(XL[tr], np.minimum(tov[tr], poss[tr]), poss[tr], lam), LAMS_LOG,
                 lambda w, va: nll_vec(sig(XL[va] @ w), np.minimum(tov[va], poss[va]), poss[va]).sum())
    lam_orb = cv(lambda tr, lam: fit_logit(XL[tr], np.minimum(orb[tr], opp[tr]), opp[tr], lam), LAMS_LOG,
                 lambda w, va: nll_vec(sig(XL[va] @ w), np.minimum(orb[va], opp[va]), opp[va]).sum())
    w_pts = fit_ridge(X, rate, poss, lam_pts)
    w_tov = fit_logit(XL, np.minimum(tov, poss), poss, lam_tov); w_orb = fit_logit(XL, np.minimum(orb, opp), opp, lam_orb)
    Xe, ye = side_features(Tev); XLe = np.hstack([Xe, season_onehot(rows_eval)])
    return Xe @ w_pts, sig(XLe @ w_tov), sig(XLe @ w_orb), ye, {'pts': lam_pts, 'tov': lam_tov, 'orb': lam_orb}
