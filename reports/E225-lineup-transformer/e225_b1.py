"""E-225 第一版基準線：B0 聯盟平均；B1-min／B1-nomin＝和對應 Transformer 臂「同樣特徵」的加法模型（場上五人能力值 z 分數加總，
進攻邊、防守邊各一組，無交互作用，無球員 ID）。得分用加權 ridge（目標＝每回合得分減該季聯盟平均，權重＝回合數）；
失誤率、進攻籃板率用同特徵的二項 logistic（L2，加季截距）。λ 一律只在訓練 folds 1-4 內做 4 折（以 fold 區分）內部驗證選，
不看 fold 0（評估折）。"""
import numpy as np
import torch

from e225_model import ARMS, SEASONS, season_means, tensors

LAMS_PTS = [1.0, 10.0, 100.0, 1000.0, 10000.0]       # ridge：penalty = lam * ||w||^2（sum 型目標，權重＝回合數）
LAMS_LOG = [1e-6, 1e-5, 1e-4, 1e-3]                  # logistic：平均每筆損失 + lam * ||w||^2


def side_features(T):
    """T＝tensors() 的輸出。回傳 X[2N, 2F]（列 2i＝A 進攻、2i+1＝B 進攻）與 y[2N,6]、season index。"""
    attr = T[0]; F = attr.shape[-1] // 2
    zA = attr[:, :5, :F].sum(1); zB = attr[:, 5:, :F].sum(1)
    XA = torch.cat([zA, zB], 1); XB = torch.cat([zB, zA], 1)
    X = torch.stack([XA, XB], 1).reshape(-1, 2 * F)
    return X.numpy().astype(np.float64), T[3].reshape(-1, 6).numpy().astype(np.float64)


def season_onehot(rows):
    s = np.zeros((len(rows) * 2, len(SEASONS)))
    for i, r in enumerate(rows):
        k = SEASONS.index(r['season']) if r['season'] in SEASONS else len(SEASONS) - 1   # 前向季（報告用）借用最近訓練季 2024-25 的截距
        s[2 * i, k] = 1; s[2 * i + 1, k] = 1
    return s


def fit_ridge(X, y, w, lam):
    A = X.T @ (w[:, None] * X) + lam * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ (w * y))


def fit_logit(X, k, n, lam, iters=100):
    """二項 logistic：k 次事件／n 次試驗（>0 才算），平均每筆（以 n 加權）損失 + lam*||w||²；X 已含季截距欄（不罰）。"""
    Xt = torch.tensor(X, dtype=torch.float64); kt = torch.tensor(k); nt = torch.tensor(n)
    m = nt > 0; Xt, kt, nt = Xt[m], kt[m], nt[m]
    w = torch.zeros(Xt.shape[1], dtype=torch.float64, requires_grad=True)
    pen_mask = torch.ones_like(w); pen_mask[-len(SEASONS):] = 0
    opt = torch.optim.LBFGS([w], lr=1, max_iter=iters, line_search_fn='strong_wolfe')

    def closure():
        opt.zero_grad(); z = Xt @ w
        nll = (nt * torch.nn.functional.softplus(z) - kt * z).sum() / nt.sum()   # 二項 NLL（略去組合常數）
        loss = nll + lam * (pen_mask * w * w).sum(); loss.backward(); return loss
    opt.step(closure)
    return w.detach().numpy()


def nll(p, k, n):
    p = np.clip(p, 1e-5, 1 - 1e-5); m = n > 0
    return -(k * np.log(p) + (n - k) * np.log(1 - p))[m].sum()


def fit_b1(rows_train, folds_train, use_min, lam_fixed=None):
    """在 rows_train（folds 1-4）上選 λ（內部以 fold 輪流留出）並以全部 rows_train 重訓。回傳 (預測函式, 選到的 λ)。"""
    means = season_means(rows_train)
    T = tensors(rows_train, use_min, means); X, y = side_features(T)
    S = season_onehot(rows_train); pts, poss, tov, orb, opp, mean = y.T
    rate = np.where(poss > 0, pts / np.maximum(poss, 1e-9), mean) - mean
    fold = np.repeat(np.array(folds_train), 2)
    XL = np.hstack([X, S])

    def cv(fit_pred, lams, score):
        res = {}
        for lam in lams:
            tot = 0.0
            for f in sorted(set(folds_train)):
                tr, va = fold != f, fold == f
                tot += score(fit_pred(tr, lam), va)
            res[lam] = tot
        return min(res, key=res.get), res

    lam_pts, _ = cv(lambda tr, lam: fit_ridge(X[tr], rate[tr], poss[tr], lam), LAMS_PTS,
                    lambda w, va: (poss[va] * (rate[va] - X[va] @ w) ** 2).sum())
    lam_tov, _ = cv(lambda tr, lam: fit_logit(XL[tr], np.minimum(tov[tr], poss[tr]), poss[tr], lam), LAMS_LOG,
                    lambda w, va: nll(1 / (1 + np.exp(-XL[va] @ w)), np.minimum(tov[va], poss[va]), poss[va]))
    lam_orb, _ = cv(lambda tr, lam: fit_logit(XL[tr], np.minimum(orb[tr], opp[tr]), opp[tr], lam), LAMS_LOG,
                    lambda w, va: nll(1 / (1 + np.exp(-XL[va] @ w)), np.minimum(orb[va], opp[va]), opp[va]))
    if lam_fixed:   # 凍結的 λ（mde-noise.json）：跳過 CV 結果，直接用
        lam_pts, lam_tov, lam_orb = lam_fixed['pts'], lam_fixed['tov'], lam_fixed['orb']
    w_pts = fit_ridge(X, rate, poss, lam_pts)
    w_tov = fit_logit(XL, np.minimum(tov, poss), poss, lam_tov)
    w_orb = fit_logit(XL, np.minimum(orb, opp), opp, lam_orb)

    def predict(rows_eval, extra_means=None):
        mm = {**means, **(extra_means or {})}
        Te = tensors(rows_eval, use_min, mm, seasons=sorted({r['season'] for r in rows_eval})); Xe, ye = side_features(Te); Se = season_onehot(rows_eval)
        XLe = np.hstack([Xe, Se])
        sig = lambda z: 1 / (1 + np.exp(-z))
        return Xe @ w_pts, sig(XLe @ w_tov), sig(XLe @ w_orb), ye   # 全部 [2N]：每回合得分偏離、失誤率、進攻籃板率

    return predict, {'pts': lam_pts, 'tov': lam_tov, 'orb': lam_orb}, means
