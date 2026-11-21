"""賽中防守意識加成（defenseBonus，2026-10-30 使用者）：card 0.2.7 UL6 的 D 改成每天重擬合，窗口跟著本季往後滑。
D＝E-104 L 形逐場線性擬合（reports/card-0.2.5+E104-defense-pergame-decay/e104fit.py，λ = 3000），只換時間軸：
  往年第 k 季（2022-23 = 0 … 2025-26 = 3）的場次位置 t = k·82 + slot + 0.5（slot 同 e104fit.game_u）；
  本季位置 t = 328 + (場次序號 − 0.5)/1230·82（gameId 末五碼就是序號）；
  窗口 = 最近 328 格 [c, 328 + c]，c = 聯盟已賽場數/1230·82；權重 u = (t − c)/328，u ≤ 0（滑出窗口）的 stint 不算。
c = 0 時完全等於 def-L-primary.csv（--check 核對）。本季 stints 由 scripts/build_inseason_stints.js 產生。
2026-11-04 起（R-163）fit／fit_loo 預設改成每個人自己的出賽場次當時間軸（見下面 _personal），上面的聯盟日曆軸留作 fit_calendar（DEF_AXIS=calendar）。
用法：python -I defense_bonus.py --check | python -I defense_bonus.py <c> <out.csv>"""
import csv, importlib.util, os, pickle, sys
from pathlib import Path
import numpy as np
import scipy.linalg as SL

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E104 = ROOT / 'reports/card-0.2.5+E104-defense-pergame-decay'
_spec = importlib.util.spec_from_file_location('e104fit', E104 / 'e104fit.py')
F = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(F)
RR, R = F.RR, F.RR.R
PAST = ['2022-23', '2023-24', '2024-25', '2025-26']
SEASON = '2026-27'
SLOTS, WIN, GAMES = 82, 328, 1230
CUR_STINTS = ROOT / f'reports/defense-seventh/{SEASON}/stints/stints.jsonl'
PAST_CACHE = ROOT / 'data/_inseason_build/def-obs-past.pkl'     # 往年 stint 觀測不會變，快取省每天 ~1 分鐘
FROZEN = E104 / 'def-L-primary.csv'


def load_data(with_current=True):
    if PAST_CACHE.exists():
        obs = pickle.load(open(PAST_CACHE, 'rb'))
    else:
        obs = {s: list(R.observations([s])) for s in PAST}
        PAST_CACHE.parent.mkdir(exist_ok=True)
        pickle.dump(obs, open(PAST_CACHE, 'wb'))
    if with_current and CUR_STINTS.exists():
        obs[SEASON] = list(R.observations([SEASON], reader=lambda s: open(CUR_STINTS, encoding='utf-8')))
    D = RR.Data.__new__(RR.Data)               # 同 RR.Data.__init__，只是季別不同
    D.obs = obs
    D.players = sorted({p for s in obs for o in obs[s] for p in o[2] + o[3]})
    D.pidx = {p: i for i, p in enumerate(D.players)}
    D.P = len(D.players); D.K = 2 * D.P
    D.s = {s: D._build(o) for s, o in obs.items()}
    return D


def positions(D):
    us, _ = F.game_u(D, PAST)                  # u = (k·82 + slot + 0.5)/328
    t = {s: us[s] * WIN for s in PAST}
    if SEASON in D.s:
        n = np.array([int(str(g)[-5:]) for g in D.s[SEASON]['gid']], float)
        t[SEASON] = WIN + (n - 0.5) / GAMES * SLOTS
    return t


def fit(D, c, lam=F.LAM):
    """回傳 {playerId: {'D','poss','possW'}}（同 e104fit.fit_w 的 parity=None）。"""
    t = positions(D)
    seasons = list(t)
    wu = {s: np.maximum((t[s] - c) / WIN, 0.0) for s in seasons}
    used = set()
    for s in seasons:
        used.update(np.unique(D.s[s]['X'][wu[s] > 0].indices).tolist())
    used.discard(D.K)
    pl = np.array(sorted({j % D.P for j in used}))
    cols = np.concatenate([pl, D.P + pl, [D.K]])
    n = len(pl)
    A = np.zeros((len(cols), len(cols))); b = np.zeros(len(cols))
    diagW = np.zeros(D.K + 1); diag1 = np.zeros(D.K + 1)
    for s in seasons:
        M, bs = F.weighted_normal(D, s, wu[s])
        A += M[cols][:, cols].toarray(); b += bs[cols]
        diagW += M.diagonal()
        diag1 += F.weighted_normal(D, s, (wu[s] > 0).astype(float))[0].diagonal()
    coef = RR._solve(A, b, lam, 2 * n)
    return {D.players[j]: {'D': float(coef[n + k]), 'poss': float(diag1[j] + diag1[D.P + j]),
                           'possW': float(diagW[j] + diagW[D.P + j])} for k, j in enumerate(pl)}


def fit_loo(D, c, lam=F.LAM):
    """ΔOVR 基準（R-112）：同 fit，但每個本季有 stint 的人的 D／poss／possW 改成「只拿掉他自己本季 stints」重擬合的值
    （＝他本季 0 場時今天的擬合；別人本季的比賽照算）。本季沒出賽的人＝fit 原值。
    拿掉一人的列＝對 A 做低秩減法，用 Woodbury：先算一次 G＝(A＋λI)⁻¹，每人只解 r×r（r＝他的 stint 數）。"""
    out = fit(D, c, lam)
    if SEASON not in D.s:
        return out
    t = positions(D)
    wu = {s: np.maximum((t[s] - c) / WIN, 0.0) for s in t}
    used = set()
    for s in t:
        used.update(np.unique(D.s[s]['X'][wu[s] > 0].indices).tolist())
    used.discard(D.K)
    pl = np.array(sorted({j % D.P for j in used}))
    cols = np.concatenate([pl, D.P + pl, [D.K]])
    n = len(pl)
    A = np.zeros((len(cols), len(cols))); b = np.zeros(len(cols))
    for s in t:
        M, bs = F.weighted_normal(D, s, wu[s])
        A += M[cols][:, cols].toarray(); b += bs[cols]
    pen = lam * np.eye(len(cols)); pen[2 * n, 2 * n] = 0
    G = np.linalg.inv(A + pen)
    x0 = G @ b
    d = D.s[SEASON]
    w = d['w'] * wu[SEASON]
    Xc = d['X'].tocsr()[:, cols]
    Xcsc = Xc.tocsc()
    for k, j in enumerate(pl):
        rows = np.union1d(Xcsc[:, k].indices, Xcsc[:, n + k].indices)
        rows = rows[w[rows] > 0]
        if not len(rows):
            continue
        Xr, wr = Xc[rows], w[rows]
        XG = np.asarray((Xr @ G))                          # r×m
        gb = x0 - XG.T @ (wr * d['y'][rows])               # G·(b − 自己那幾列的 Xᵀwy)
        S = np.diag(1.0 / wr) - np.asarray(Xr @ XG.T)      # W⁻¹ − X G Xᵀ
        tt = np.linalg.solve(S, Xr @ gb)
        e = out[D.players[j]]
        sq = np.asarray(Xr.multiply(Xr)[:, [k, n + k]].sum(axis=1)).ravel()
        e.update(D=float(gb[n + k] + XG[:, n + k] @ tt), poss=e['poss'] - float((d['w'][rows] * sq).sum()),
                 possW=e['possW'] - float((wr * sq).sum()))
    return out


fit_calendar, fit_loo_calendar = fit, fit_loo


# ==== R-163 個人場次時間軸 ====
# 每個人只看自己有上場的比賽（沒打的場次、賽季不佔窗口）：他有上場的 stint 權重 u＝(WIN − r − 0.5)/WIN，r＝該場在他自己出賽場次裡
# 由新到舊的序號；他沒上場的 stint 照聯盟日曆權重（只影響隊友／對手）。每人各解一次。DEF_AXIS=calendar 回聯盟日曆軸（fit_calendar）。
AXIS = os.environ.get('DEF_AXIS', 'personal')
_CACHE = {}


def _personal(D, c, lam):
    key = (id(D), c, lam, WIN)
    if key in _CACHE:
        return _CACHE[key]
    t = positions(D)
    seasons = [s for s in PAST + [SEASON] if s in D.s]
    wu = {s: np.maximum((t[s] - c) / WIN, 0.0) for s in seasons}
    K = D.K
    pen = lam * np.eye(K + 1); pen[K, K] = 0
    A0 = np.zeros((K + 1, K + 1)); b0 = np.zeros(K + 1)
    for s in seasons:
        M, bs = F.weighted_normal(D, s, wu[s])
        A0 += M.toarray(); b0 += bs
    A0 += pen
    g0 = SL.cho_solve(SL.cho_factor(A0, check_finite=False), b0, check_finite=False)   # 每人：A＝A0＋ΔM（只碰他的隊友／對手欄），Cholesky 直接解
    csc = {s: D.s[s]['X'].tocsc() for s in seasons}
    csr = {s: D.s[s]['X'].tocsr() for s in seasons}
    gnum = {s: np.array([int(g) for g in D.s[s]['gid']]) for s in seasons}

    def solve(j, rows, drop_cur):
        """rows＝{season: 他上場的 stint 列}；drop_cur＝拿掉他本季 stints（基準）。回傳 D／poss／possW。"""
        games = sorted({(k, g) for k, s in enumerate(seasons) if not (drop_cur and s == SEASON)
                        for g in gnum[s][rows[s]].tolist()}, reverse=True)
        rank = {g: i for i, g in enumerate(games)}
        dM, db = [], []
        poss = possW = 0.0
        for k, s in enumerate(seasons):
            r = rows[s]
            if not len(r):
                continue
            if drop_cur and s == SEASON:
                u = np.zeros(len(r))
            else:
                u = np.maximum((WIN - np.array([rank[(k, g)] for g in gnum[s][r].tolist()]) - 0.5) / WIN, 0.0)
            w = D.s[s]['w'][r]
            dw = w * (u - wu[s][r])
            Xr = csr[s][r]
            if np.any(dw):
                dM.append(Xr.T @ Xr.multiply(dw[:, None]))
                db.append(Xr.T @ (dw * D.s[s]['y'][r]))
            poss += float(w[u > 0].sum()); possW += float((w * u).sum())   # 每列他只出現一次（O 或 D 側），X²＝1
        if not games:
            return None
        tj = D.P + j
        if not dM:
            return {'D': float(g0[tj]), 'poss': poss, 'possW': possW}
        M = sum(dM).tocsr(); bb = np.asarray(sum(db)).ravel()
        S = np.unique(M.indices)
        A = A0.copy()
        A[np.ix_(S, S)] += M[S][:, S].toarray()
        x = SL.cho_solve(SL.cho_factor(A, overwrite_a=True, check_finite=False), b0 + bb, check_finite=False)
        return {'D': float(x[tj]), 'poss': poss, 'possW': possW}

    full, loo = {}, {}
    for j, p in enumerate(D.players):
        rows = {s: np.union1d(csc[s][:, j].indices, csc[s][:, D.P + j].indices) for s in seasons}
        e = solve(j, rows, False)
        if e is None or e['possW'] <= 0:
            continue
        full[p] = e
        if SEASON in rows and len(rows[SEASON]):
            e0 = solve(j, rows, True)
            if e0 is not None and e0['possW'] > 0:
                loo[p] = e0
        else:
            loo[p] = e
    _CACHE[key] = (full, loo)
    return full, loo


def fit(D, c, lam=F.LAM):
    """回傳 {playerId: {'D','poss','possW'}}；預設 R-163 個人場次軸，DEF_AXIS=calendar 回聯盟日曆軸。"""
    return fit_calendar(D, c, lam) if AXIS == 'calendar' else dict(_personal(D, c, lam)[0])


def fit_loo(D, c, lam=F.LAM):
    """ΔOVR 基準（R-112）：每人只拿掉自己本季 stints 重擬合；本季沒出賽的人＝fit 原值（同 fit_loo_calendar 的口徑）。"""
    return fit_loo_calendar(D, c, lam) if AXIS == 'calendar' else dict(_personal(D, c, lam)[1])


def write_csv(out, path):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['playerId', 'name', 'D', 'poss', 'possUnweighted'])
        for pid, v in sorted(out.items(), key=lambda kv: -kv[1]['D']):
            wr.writerow([pid, '', repr(v['D']), repr(v['possW']), repr(v['poss'])])


def check():
    out = fit_calendar(load_data(with_current=False), 0.0)
    ref = {int(r['playerId']): r for r in csv.DictReader(open(FROZEN, encoding='utf-8'))}
    assert set(out) == set(ref), (len(out), len(ref))
    dd = max(abs(out[p]['D'] - float(ref[p]['D'])) for p in ref)
    dp = max(abs(out[p]['possW'] - float(ref[p]['poss'])) for p in ref)
    print(f'c=0 對 def-L-primary：{len(ref)} 人，D 最大差 {dd:.2e}，possW 最大差 {dp:.2e}')
    assert dd < 1e-9 and dp < 1e-6


if __name__ == '__main__':
    if sys.argv[1] == '--check':
        check()
    else:
        o = fit(load_data(), float(sys.argv[1]))
        write_csv(o, sys.argv[2])
        print(f'c={float(sys.argv[1]):.2f}：{len(o)} 人 → {sys.argv[2]}')
