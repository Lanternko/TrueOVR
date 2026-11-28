"""E-079 近期加權 RAPM（複製 reports/impact-rapm/rapm.py 的模型，唯一改動是季權重 w_s = d^(T - s)）。

模型（同 rapm.py）：y = 100*pts/poss，權重 = poss，y = mu + sum(進攻 O) - sum(防守 D)，截距不罰，ridge lambda。
近期加權：窗口中第 s 季的每筆 stint，權重再乘 d^(T-s)；T 是窗口最近一季，以季數計、跳過 2021-22。
XtWX、XtWy 對權重線性，所以每季各累加一次，再加權相加。
"""
import importlib.util, pickle, sys, zlib
from pathlib import Path
import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
_spec = importlib.util.spec_from_file_location('rapm_orig', ROOT / 'reports/impact-rapm/rapm.py')
R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R)

ALL_SEASONS = ['2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21',
               '2022-23', '2023-24', '2024-25', '2025-26']   # 沒有 2021-22；季數以此串列的位置計
SEASON_IDX = {s: i for i, s in enumerate(ALL_SEASONS)}
D_GRID = [1.0, 0.75, 0.5, 0.25, 0.0]
LAMBDA = 3000
LAMBDAS = R.LAMBDAS
N_FOLDS = 5
import os
CACHE = Path(os.environ.get('E079_CACHE', HERE / 'obs_cache.pkl'))  # 快取放暫存區，不進輸出資料夾


class Data:
    """每季的 stint 觀測（用 rapm.observations 讀，過濾規則完全相同），以稀疏設計矩陣表示。"""

    def __init__(self, seasons=ALL_SEASONS, cache=None):
        cache = Path(cache) if cache else CACHE
        if cache.exists():
            self.obs = pickle.load(open(cache, 'rb'))
        else:
            self.obs = {s: list(R.observations([s])) for s in ALL_SEASONS}
            cache.parent.mkdir(exist_ok=True)
            pickle.dump(self.obs, open(cache, 'wb'))
        self.players = sorted({p for s in self.obs for o in self.obs[s] for p in o[2] + o[3]})
        self.pidx = {p: i for i, p in enumerate(self.players)}
        self.P = len(self.players)
        self.K = 2 * self.P
        self.s = {}
        for s, obs in self.obs.items():
            self.s[s] = self._build(obs)

    def _build(self, obs):
        P, K = self.P, self.K
        n = len(obs)
        rows, cols, vals = [], [], []
        y = np.empty(n); w = np.empty(n); gid = []; fold = np.empty(n, dtype=int)
        for r, (_, g, op, dp, pts, poss, _, _) in enumerate(obs):
            for p in op:
                rows.append(r); cols.append(self.pidx[p]); vals.append(1.0)
            for p in dp:
                rows.append(r); cols.append(P + self.pidx[p]); vals.append(-1.0)
            rows.append(r); cols.append(K); vals.append(1.0)
            y[r] = 100 * pts / poss; w[r] = poss; gid.append(g)
            fold[r] = zlib.crc32(str(g).encode()) % N_FOLDS
        X = sp.csr_matrix((vals, (rows, cols)), shape=(n, K + 1))
        return {'X': X, 'y': y, 'w': w, 'gid': np.array(gid), 'fold': fold}

    # ---------- 正規方程 ----------
    def season_normal(self, s, mask=None):
        d = self.s[s]
        X, y, w = d['X'], d['y'], d['w']
        if mask is not None:
            X, y, w = X[mask], y[mask], w[mask]
        Xw = X.multiply(w[:, None]).tocsr()
        return (X.T @ Xw).tocsr(), np.asarray(Xw.T @ y).ravel(), float((w * y * y).sum()), float(w.sum())

    def window_weights(self, window, d):
        T = SEASON_IDX[window[-1]]
        return {s: (d ** (T - SEASON_IDX[s])) for s in window}   # 0.0 ** 0 = 1.0

    def window_cols(self, window, d):
        """窗口內有資料（權重 > 0）的球員欄位（O、D、截距）。"""
        wt = self.window_weights(window, d)
        used = set()
        for s in window:
            if wt[s] > 0:
                used.update(np.unique(self.s[s]['X'].indices))
        used.discard(self.K)
        pl = sorted(j % self.P for j in used)
        pl = sorted(set(pl))
        return np.array(pl)

    def poss_unweighted(self, window):
        """窗口內不加權的球員回合數（O 側 + D 側），同 rapm.py 的 pooledPoss。"""
        tot = np.zeros(self.K + 1)
        for s in window:
            tot += self.season_diag(s)
        return tot[:self.P] + tot[self.P:self.K]

    def season_diag(self, s):
        if not hasattr(self, '_diag'):
            self._diag = {}
        if s not in self._diag:
            A, _, _, _ = self.season_normal(s)
            self._diag[s] = A.diagonal()
        return self._diag[s]

    def fit(self, window, d, lam=LAMBDA):
        """回傳 {playerId: {'O','D','net','poss'}} 與 intercept。poss = 不加權回合數。"""
        wt = self.window_weights(window, d)
        pl = self.window_cols(window, d)
        cols = np.concatenate([pl, self.P + pl, [self.K]])
        n = len(pl)
        A = np.zeros((len(cols), len(cols))); b = np.zeros(len(cols))
        for s in window:
            if wt[s] == 0: continue
            if not hasattr(self, '_ne'): self._ne = {}
            if s not in self._ne: self._ne[s] = self.season_normal(s)
            Ms, bs, _, _ = self._ne[s]
            A += wt[s] * Ms[cols][:, cols].toarray(); b += wt[s] * bs[cols]
        coef = _solve(A, b, lam, 2 * n)
        poss = self.poss_unweighted(window)
        out = {}
        for k, j in enumerate(pl):
            O, D = float(coef[k]), float(coef[n + k])
            out[self.players[j]] = {'O': O, 'D': D, 'net': O + D, 'poss': float(poss[j])}
        return out, float(coef[-1])

    def fit_cv(self, window, d):
        """窗口內 5 折（依比賽）CV 選 lambda（照 rapm.py）；回傳 (最佳 lambda, cv 表)。
        保留集的 SSE 用同一組季權重加權。"""
        wt = self.window_weights(window, d)
        pl = self.window_cols(window, d)
        cols = np.concatenate([pl, self.P + pl, [self.K]])
        n = len(pl); Kw = 2 * n
        XtX = np.zeros((N_FOLDS, len(cols), len(cols))); Xty = np.zeros((N_FOLDS, len(cols))); yy = np.zeros(N_FOLDS); ws = np.zeros(N_FOLDS)
        if not hasattr(self, '_nef'): self._nef = {}
        for s in window:
            if wt[s] == 0: continue
            for f in range(N_FOLDS):
                key = (s, f)
                if key not in self._nef: self._nef[key] = self.season_normal(s, self.s[s]['fold'] == f)
                M, bb, y2, w2 = self._nef[key]
                XtX[f] += wt[s] * M[cols][:, cols].toarray(); Xty[f] += wt[s] * bb[cols]; yy[f] += wt[s] * y2; ws[f] += wt[s] * w2
        cv = {}
        for lam in LAMBDAS:
            sse = 0.0
            for f in range(N_FOLDS):
                tr = [g for g in range(N_FOLDS) if g != f]
                bcoef = _solve(XtX[tr].sum(0), Xty[tr].sum(0), lam, Kw)
                sse += yy[f] - 2 * bcoef @ Xty[f] + bcoef @ XtX[f] @ bcoef
            cv[lam] = float(sse / ws.sum())
        return min(cv, key=cv.get), cv


def _solve(A, b, lam, K):
    pen = lam * np.eye(A.shape[0]); pen[K, K] = 0
    return np.linalg.solve(A + pen, b)


def spearman_ranks(v):
    # 與 rapm.spearman 同：argsort 排名（無平手處理）
    o = np.argsort(v); r = np.empty(len(v)); r[o] = np.arange(len(v)); return r


def spearman(a, b):
    return float(np.corrcoef(spearman_ranks(np.array(a)), spearman_ranks(np.array(b)))[0, 1])
