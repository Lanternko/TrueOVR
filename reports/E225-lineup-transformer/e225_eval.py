"""E-225 第一版評估（R-157）。凍結後才用 --target test；凍結前只准 --target fold0（只讀 split=train 的 fold 0，當乾跑）。
讀 results/weights/<arm>-<seed>.pt（凍結設定重訓的 5 seed）與凍結的 B1（fit_b1，folds 1-4 訓練、λ 內部 CV）。本機 CPU 推論，不需上傳測試資料。
解除硬擋：只在這支評估腳本裡用 load_rows(..., allow_holdout=True)；e225_common 預設不改。

  python -I -X utf8 e225_eval.py --target fold0   # 乾跑，不碰 test／前向
  python -I -X utf8 e225_eval.py --target test    # 凍結後：主測試＋前向＋只報告項（只跑一次，L-026）
"""
import argparse, json, os, sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_b1 import fit_b1
from e225_common import ATTRS, FEATS, HERE, load_players, load_rows
from e225_model import ARMS, SEASONS, LineupNet, predict, season_means, tensors

B = 2000
SEEDS = range(5)
torch.set_num_threads(4)


def sig(x):
    return 1 / (1 + np.exp(-x))


def load_nets(arm):
    F = len(FEATS) if ARMS[arm] else len(ATTRS); nets = []
    for sd in SEEDS:
        n = LineupNet(F); n.load_state_dict(torch.load(os.path.join(HERE, 'results', 'weights', f'{arm}-{sd}.pt'))); n.eval(); nets.append(n)
    return nets


def t_raw(nets, T):
    return np.stack([predict(n, T, 'cpu').numpy() for n in nets])   # [S, N, 2, 3]


def ens(P):
    """P[S,N,2,3] -> (pts_dev[2N], p_tov[2N], p_orb[2N])，5 seed 平均預測（得分取平均、機率取平均）。"""
    return P[..., 0].mean(0).reshape(-1), sig(P[..., 1]).mean(0).reshape(-1), sig(P[..., 2]).mean(0).reshape(-1)


def ll(p, k, n):
    p = np.clip(p, 1e-5, 1 - 1e-5); k = np.minimum(k, n)
    return np.where(n > 0, -(k * np.log(p) + (n - k) * np.log(1 - p)), 0.0)


class Ctx:
    def __init__(self, lam_frozen):
        rows = load_rows(SEASONS)
        self.tr = [r for r in rows if r['fold'] != 0]; self.fold0 = [r for r in rows if r['fold'] == 0]
        self.means = season_means(self.tr)
        self.nets = {a: load_nets(a) for a in ARMS}
        self.b1 = {}; self.lam = {}
        for a, um in ARMS.items():
            self.b1[a], self.lam[a], _ = fit_b1(self.tr, [r['fold'] for r in self.tr], um, lam_fixed=lam_frozen[a])
        self.tv = {s: sum(r['tova'] + r['tovb'] for r in self.tr if r['season'] == s) / sum(r['possa'] + r['possb'] for r in self.tr if r['season'] == s) for s in SEASONS}
        self.ob = {s: sum(r['orba'] + r['orbb'] for r in self.tr if r['season'] == s) / sum(r['rebOppa'] + r['rebOppb'] for r in self.tr if r['season'] == s) for s in SEASONS}

    def season_mean_for(self, ev):
        """前向季沒有訓練季聯盟均值：用該季自己的聯盟每回合得分（對所有模型相同的常數）。"""
        mm = dict(self.means)
        for s in sorted({r['season'] for r in ev} - set(SEASONS)):
            rs = [r for r in ev if r['season'] == s]; mm[s] = sum(r['ptsa'] + r['ptsb'] for r in rs) / sum(r['possa'] + r['possb'] for r in rs)
        return mm

    def models(self, ev, force_extra=False):
        mm = self.season_mean_for(ev); extra = {s: v for s, v in mm.items() if s not in SEASONS}
        out = {}; ye = None
        for a, um in ARMS.items():
            pts, ptov, porb, ye = self.b1[a](ev, extra if extra else None)
            out['B1-' + a[2:]] = (pts, ptov, porb)
            T = tensors(ev, um, mm, seasons=sorted({r['season'] for r in ev}))
            out[a] = ens(t_raw(self.nets[a], T))
        sea2 = np.repeat([r['season'] if r['season'] in SEASONS else '2024-25' for r in ev], 2)
        out['B0'] = (np.zeros(len(sea2)), np.array([self.tv[s] for s in sea2]), np.array([self.ob[s] for s in sea2]))
        return out, ye


def metrics(ev, ye, models):
    pts2, poss2, tov2, orb2, opp2, mean2 = ye.T
    games = list(dict.fromkeys(r['gid'] for r in ev)); gmap = {g: k for k, g in enumerate(games)}; G = len(games)
    gi = np.array([gmap[r['gid']] for r in ev]); gi2 = np.repeat(gi, 2)
    possA, possB = poss2[0::2], poss2[1::2]; Pw = (possA + possB) / 2
    actual = np.where(Pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw, 1e-9), 0)
    rate = np.where(poss2 > 0, pts2 / np.maximum(poss2, 1e-9), mean2) - mean2
    ref = {}
    for r in ev:
        ref.setdefault(r['gid'], r['teama'])
    sign = np.array([1.0 if r['teama'] == ref[r['gid']] else -1.0 for r in ev])
    act_margin = np.bincount(gi, sign * (pts2[0::2] - pts2[1::2]), G)
    res, gm = {}, {}
    for name, (pts, ptov, porb) in models.items():
        muA, muB = pts[0::2] + mean2[0::2], pts[1::2] + mean2[1::2]
        pred = 100 * (muA * possA - muB * possB) / np.maximum(Pw, 1e-9)
        res[name] = {'net': (np.bincount(gi, Pw * (actual - pred) ** 2, G), np.bincount(gi, Pw, G)),
                     'ptsSide': (np.bincount(gi2, poss2 * (rate - pts) ** 2, G), np.bincount(gi2, poss2, G)),
                     'tovLL': (np.bincount(gi2, ll(ptov, tov2, poss2), G), np.bincount(gi2, poss2, G)),
                     'orbLL': (np.bincount(gi2, ll(porb, orb2, opp2), G), np.bincount(gi2, opp2, G))}
        gm[name] = np.bincount(gi, sign * (muA * possA - muB * possB), G)
    return res, gm, act_margin, G, Pw


def draws_for(G, seed=20261103):
    rng = np.random.default_rng(seed)
    return np.stack([np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(B)]).astype(float)


def val(res, k, met):
    n, d = res[k][met]; return float(n.sum() / d.sum())


def paired(res, a, b, met, draws):
    na, da = res[a][met]; nb, db = res[b][met]
    d = (draws @ na) / (draws @ da) - (draws @ nb) / (draws @ db); pt = val(res, a, met) - val(res, b, met)
    lo, hi = np.percentile(d, [5, 95])
    return {'point': round(pt, 5), 'ci90': [round(float(lo), 5), round(float(hi), 5)]}


def fit_k(pred, act):
    best = None
    for k in np.exp(np.linspace(np.log(1e-4), np.log(1.0), 400)):
        p = np.clip(sig(k * pred), 1e-9, 1 - 1e-9); w = act > 0
        l = -(np.log(p[w]).sum() + np.log(1 - p[~w]).sum())
        if best is None or l < best[0]:
            best = (l, k)
    return float(best[1])


def evaluate_set(ctx, ev, label, kfit, mde, guard):
    models, ye = ctx.models(ev)
    res, gm, act, G, Pw = metrics(ev, ye, models); draws = draws_for(G)
    out = {'label': label, 'games': G, 'stints': len(ev), 'poss': round(float(Pw.sum() * 2)),
           'mse': {k: round(val(res, k, 'net'), 2) for k in res},
           'side': {k: {m: round(val(res, k, m), 5) for m in ('ptsSide', 'tovLL', 'orbLL')} for k in res}, 'paired': {}, 'game': {}}
    for a in ARMS:
        b1 = 'B1-' + a[2:]
        out['paired'][f'{a}−{b1}'] = paired(res, a, b1, 'net', draws)
        out['paired'][f'{b1}−B0'] = paired(res, b1, 'B0', 'net', draws)
        out['paired'][f'{a}−B0'] = paired(res, a, 'B0', 'net', draws)
        out['paired'][f'{a}−{b1}'].update({'guard': {m: paired(res, a, b1, m, draws) for m in ('ptsSide', 'tovLL', 'orbLL')}})
    out['paired']['T-min−T-nomin'] = paired(res, 'T-min', 'T-nomin', 'net', draws)
    # 比賽層級：一場 stints 加總的淨得分（分），MSE 與勝負 Brier（k 用 fold 0 的預測擬合，不用 test）
    win = (act > 0).astype(float)
    for k, g in gm.items():
        mse = float(((act - g) ** 2).mean())
        kk = kfit.get(k) if kfit is not None else fit_k(g, act)
        brier = float(((sig(kk * g) - win) ** 2).mean()) if k != 'B0' else 0.25
        out['game'][k] = {'marginMSE': round(mse, 2), 'brier': round(brier, 5), 'k': round(kk, 5) if k != 'B0' else None}
    # 判定
    if mde is not None:
        out['verdict'] = {}
        for a in ARMS:
            b1 = 'B1-' + a[2:]; p = out['paired'][f'{a}−{b1}']
            j1 = bool(p['point'] <= -mde and p['ci90'][1] < 0)
            g2 = {m: {'point': p['guard'][m]['point'], 'threshold': guard[a][m], 'ok': bool(p['guard'][m]['point'] <= guard[a][m])} for m in ('ptsSide', 'tovLL', 'orbLL')}
            out['verdict'][a] = {'judge1': {'point': p['point'], 'ci90': p['ci90'], 'needAtMost': -mde, 'pass': j1}, 'judge2': g2, 'judge2pass': all(v['ok'] for v in g2.values())}
    return out, gm, act


# ---------- 只報告項 ----------
def player_values(ctx, minutes_splits):
    """2024-25（核心季）上場 ≥1000 分鐘的球員，放進聯盟平均陣容的淨值變化（每 100 回合），兩臂各 5 seed 平均。"""
    rows = load_rows(['2024-25'], splits=minutes_splits, allow_holdout=True)
    secs, posw = {}, {}
    for r in rows:
        for x in 'ab':
            for j in range(5):
                pid = r[f'{x}{j}']; secs[pid] = secs.get(pid, 0) + r['sec']; w = posw.setdefault(pid, np.zeros(5)); w[r[f'p{x}{j}']] += r['sec']
    pl = {r['pid']: r for r in __import__('csv').DictReader(open(os.path.join(HERE, 'data', 'players-2024-25.csv'), encoding='utf-8'))}
    elig = [p for p, s in secs.items() if s / 60 >= 1000 and str(p) in pl]
    out = {}; vals = {}
    for arm, um in ARMS.items():
        P = load_players('2024-25', um); F = len(FEATS) if um else len(ATTRS)
        modal = {p: int(posw[p].argmax()) for p in elig}
        med = np.zeros((5, 2 * F), np.float32)
        for k in range(5):
            ids = [p for p in elig if modal[p] == k]
            V = np.stack([P[str(p)][0] for p in ids]); M = np.stack([P[str(p)][1] for p in ids])
            for f in range(F):
                have = M[:, f] > 0
                med[k, f] = np.median(V[have, f]) if have.any() else 0; med[k, F + f] = 1.0 if have.any() else 0.0
        pos = torch.tensor(list(range(5)) * 2).unsqueeze(0); side = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)

        def net_of(attrA, attrB):
            """attrA／attrB：[n,5,2F] 以位置 0-4 排列；回傳 5 seed 平均的 100·(μA−μB)。"""
            n = attrA.shape[0]; attr = torch.cat([attrA, attrB], 1)
            T = [attr, pos.expand(n, -1), side.expand(n, -1)]
            P_ = np.stack([predict(m, T, 'cpu').numpy() for m in ctx.nets[arm]])
            return 100 * (P_[:, :, 0, 0] - P_[:, :, 1, 0]).mean(0)
        base = torch.from_numpy(med).unsqueeze(0)
        n0 = net_of(base, base)[0]
        ids = elig; A = base.repeat(len(ids), 1, 1); Bm = base.repeat(len(ids), 1, 1)
        for i, p in enumerate(ids):
            v = torch.from_numpy(np.concatenate([P[str(p)][0], P[str(p)][1]]))
            A[i, modal[p]] = v; Bm[i, modal[p]] = v
        nA = net_of(A, base.repeat(len(ids), 1, 1)) - n0           # 他在 A 邊
        nB = net_of(base.repeat(len(ids), 1, 1), Bm) - n0           # 他在 B 邊（淨值是 A−B，取負）
        vals[arm] = {p: float(0.5 * (nA[i] - nB[i])) for i, p in enumerate(ids)}
        # 五中鋒 vs 均衡
        c5 = base[:, 4:5].repeat(1, 5, 1)
        out.setdefault('fiveC', {})[arm] = round(float(net_of(c5, base)[0] - n0), 3)
    avg = {p: (vals['T-min'][p] + vals['T-nomin'][p]) / 2 for p in elig}
    vals['avg'] = avg
    rep = {}
    for key, v in vals.items():
        ps = sorted(elig, key=lambda p: -v[p]); vr = {p: i + 1 for i, p in enumerate(ps)}
        orank = {p: i + 1 for i, p in enumerate(sorted(elig, key=lambda p: -float(pl[str(p)]['ovr'])))}
        d = {p: vr[p] - orank[p] for p in elig}   # >0：OVR 名次比價值名次好（高估）
        a_, b_ = np.array([vr[p] for p in elig], float), np.array([orank[p] for p in elig], float)
        sp = float(np.corrcoef(a_, b_)[0, 1])
        row = lambda p: {'pid': str(p), 'name': pl[str(p)]['name'], 'pos': pl[str(p)]['pos'], 'ovr': round(float(pl[str(p)]['ovr']), 1), 'valueRank': vr[p], 'ovrRank': orank[p], 'value': round(v[p], 3), 'diff': d[p], 'min': round(secs[p] / 60)}
        rep[key] = {'n': len(elig), 'spearman': round(sp, 4), 'top20': [row(p) for p in ps[:20]],
                    'overrated15': [row(p) for p in sorted(elig, key=lambda p: -d[p])[:15]], 'underrated15': [row(p) for p in sorted(elig, key=lambda p: d[p])[:15]]}
    out['valueRanking'] = rep
    return out


def importance(ctx, ev, reps=3):
    """能力值排列重要性：在 ev 上把某一項（值與遮罩一起）在全部球員 token 間打亂，看 5 seed 平均預測的淨值 MSE 上升。"""
    mm = ctx.season_mean_for(ev); res_all = {}
    for arm, um in ARMS.items():
        F = len(FEATS) if um else len(ATTRS); names = (FEATS if um else ATTRS)
        T = tensors(ev, um, mm, seasons=sorted({r['season'] for r in ev}))
        y = T[3].numpy(); pts2, poss2 = y[..., 0].reshape(-1), y[..., 1].reshape(-1)
        possA, possB = poss2[0::2], poss2[1::2]; Pw = (possA + possB) / 2
        actual = np.where(Pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw, 1e-9), 0); m = y[..., 5].reshape(-1)

        def mse(attr):
            P = ens(t_raw(ctx.nets[arm], [attr, T[1], T[2], T[3]]))[0]
            muA, muB = P[0::2] + m[0::2], P[1::2] + m[1::2]
            pred = 100 * (muA * possA - muB * possB) / np.maximum(Pw, 1e-9)
            return float((Pw * (actual - pred) ** 2).sum() / Pw.sum())
        base = mse(T[0]); rng = np.random.default_rng(7); N = T[0].shape[0]; rows = {}
        for f in range(F):
            ups = []
            for _ in range(reps):
                a = T[0].clone(); perm = torch.from_numpy(rng.permutation(N * 10))
                flat = a.reshape(N * 10, -1); idx = [f, F + f]
                flat[:, idx] = flat[perm][:, idx]
                ups.append(mse(a) - base)
            rows[names[f]] = round(float(np.mean(ups)), 3)
        res_all[arm] = {'baseMSE': round(base, 2), 'increase': dict(sorted(rows.items(), key=lambda kv: -kv[1]))}
    return res_all


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--target', required=True, choices=['fold0', 'test']); a = ap.parse_args()
    mde_j = json.load(open(os.path.join(HERE, 'mde-noise.json'), encoding='utf-8'))
    mde = mde_j['mde']['value']; guard = {arm: {m: mde_j['arms'][arm]['guard2'][m]['threshold'] for m in ('ptsSide', 'tovLL', 'orbLL')} for arm in ARMS}
    ctx = Ctx(mde_j['b1Lambda'])
    assert all(ctx.lam[arm] == mde_j['b1Lambda'][arm] for arm in ARMS), f'B1 λ 與凍結值不同：{ctx.lam}'
    # fold 0（拿來擬合勝負的 k；兩個 target 都先算）
    f0, gm0, act0 = evaluate_set(ctx, ctx.fold0, 'fold0 (retrained weights)', None, mde, guard)
    kfit = {k: v['k'] for k, v in f0['game'].items()}
    out = {'target': a.target, 'mde': mde, 'guardThresholds': guard, 'b1Lambda': ctx.lam, 'fold0': f0}
    if a.target == 'fold0':
        # 乾跑：用 fold 0 的 2024-25 列演練前向路徑與只報告項（訓練季資料，不碰 test／前向）
        ev = [r for r in ctx.fold0 if r['season'] == '2024-25']
        out['fwdDry'], _, _ = evaluate_set(ctx, ev, 'dry (fold0 2024-25)', kfit, mde, guard)
        out['report'] = player_values(ctx, ('train',)); out['importance'] = importance(ctx, ev, reps=1)
    else:
        test = load_rows(SEASONS, splits=('test',), allow_holdout=True)
        out['test'], _, _ = evaluate_set(ctx, test, 'test (core 4 seasons, split=test)', kfit, mde, guard)
        for s in ('2025-26', '2026-27'):
            ev = load_rows([s], splits=('forward',), allow_holdout=True)
            out['forward-' + s], _, _ = evaluate_set(ctx, ev, f'forward {s}', kfit, None, guard)
        out['report'] = player_values(ctx, ('train', 'test')); out['importance'] = importance(ctx, test)
    fn = os.path.join(HERE, 'results', 'eval-fold0-dry.json' if a.target == 'fold0' else 'test-results.json')
    json.dump(out, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(fn)


if __name__ == '__main__':
    main()
