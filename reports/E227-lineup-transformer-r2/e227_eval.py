"""E-227 評估（R-159；改編自凍結的 E-225 e225_eval.py）。凍結後才用 --target test；凍結前只准 --target fold0（只讀 split=train 的 fold 0 乾跑）。
讀 results/weights/<臂>-<seed>.pt（15 組）與凍結的 B1（folds 1-4 訓練；λ 重新 CV 後必須等於 mde-noise.json 的 b1Lambda，否則中止）。本機 CPU 推論。
測試列：E-225 完整 stints（reports/E225-lineup-transformer/data/stints-<季>.csv.gz）依雜湊規則重切 split=test（2025-26 檔案標 forward，以雜湊為準）；
RAPM 特徵用全部 train 場次擬合的版本（key none）。前向 2026-27：沒有該季的統計表，球員特徵用 2025-26 的表與 RAPM(none)，聯盟均值用 2026-27 自己的（偏離，報告註明）。
  python -I -X utf8 e227_eval.py --target fold0
  python -I -X utf8 e227_eval.py --target test       # 凍結後，只跑一次（L-026）
"""
import argparse, csv, gzip, hashlib, json, math, os, sys, time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e227_b1 import fit_b1
from e227_common import ARMS, ATTRS, HERE, SEASONS, STAT_CLASSES, STATS, load_rows
from e227_model import LineupNet, n_feat, predict, season_means, tensors

B = 2000
SEEDS = range(5)
ROOT = os.path.dirname(os.path.dirname(HERE))
E225 = os.path.join(ROOT, 'reports', 'E225-lineup-transformer', 'data')
torch.set_num_threads(6)


def sig(x):
    return 1 / (1 + np.exp(-x))


def hmod(tag, gid, m):
    return int(hashlib.sha256(f'E225|{tag}|{gid}'.encode()).hexdigest()[:8], 16) % m


def read_stints(path, keep):
    out = []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if not keep(r):
                continue
            for k in list(r):
                if k.startswith(('poss', 'pts', 'fga', 'fgm', 'fg3', 'ftm', 'fta', 'tov', 'orb', 'drb', 'rebOpp', 'sec')):
                    r[k] = float(r[k]) if r[k] != '' else math.nan
            r['fold'] = -1
            for k in [f'p{x}{j}' for x in 'ab' for j in range(5)]:
                r[k] = int(r[k])
            out.append(r)
    return out


def load_test():
    rows = []
    for s in SEASONS:
        rs = read_stints(os.path.join(E225, f'stints-{s}.csv.gz'), lambda r: hmod('test', r['gid'], 100) < 20)
        for r in rs:
            r['split'] = 'test'; r['season'] = s
        rows += rs
    return rows


def load_forward(max_date_gids=None):
    rs = read_stints(os.path.join(E225, 'stints-2026-27.csv.gz'), lambda r: True)
    for r in rs:
        r['realSeason'] = '2026-27'; r['season'] = '2025-26'   # 特徵與 RAPM 查 2025-26 的表
    return rs


def load_nets(arm):
    F = n_feat(ARMS[arm]); nets = []
    for sd in SEEDS:
        n = LineupNet(F); n.load_state_dict(torch.load(os.path.join(HERE, 'results', 'weights', f'{arm}-{sd}.pt'), map_location='cpu')); n.eval(); nets.append(n)
    return nets


def t_raw(nets, T):
    return np.stack([predict(n, T, 'cpu').numpy() for n in nets])   # [S, N, 2, 3]


def ens(P):
    return P[..., 0].mean(0).reshape(-1), sig(P[..., 1]).mean(0).reshape(-1), sig(P[..., 2]).mean(0).reshape(-1)


def ll(p, k, n):
    p = np.clip(p, 1e-5, 1 - 1e-5); k = np.minimum(k, n)
    return np.where(n > 0, -(k * np.log(p) + (n - k) * np.log(1 - p)), 0.0)


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
    return {'point': round(pt, 5), 'ci90': [round(float(lo), 5), round(float(hi), 5)], 'halfWidth90': round(float((hi - lo) / 2), 5)}


def fit_k(pred, act):
    best = None
    for k in np.exp(np.linspace(np.log(1e-4), np.log(1.0), 400)):
        p = np.clip(sig(k * pred), 1e-9, 1 - 1e-9); w = act > 0
        l = -(np.log(p[w]).sum() + np.log(1 - p[~w]).sum())
        if best is None or l < best[0]:
            best = (l, k)
    return float(best[1])


class Ctx:
    """訓練折（folds 1-4）上擬合 B1，並在所有要評估的集合上一次預測（B1 的 CV 只做一次）。"""
    def __init__(self, parts, lam_frozen):
        rows = load_rows(SEASONS)
        self.tr = [r for r in rows if r['fold'] != 0]; self.fold0 = [r for r in rows if r['fold'] == 0]
        self.means = season_means(self.tr)
        self.parts = parts   # name -> (rows, mode)
        self.nets = {a: load_nets(a) for a in ARMS}
        self.mm = {}
        for name, (rs, mode) in parts.items():
            mm = dict(self.means)
            if any('realSeason' in r for r in rs):
                mm['2025-26'] = sum(r['ptsa'] + r['ptsb'] for r in rs) / sum(r['possa'] + r['possb'] for r in rs)   # 前向季自己的聯盟每回合得分
            self.mm[name] = mm
        self.T = {(name, a): tensors(rs, ARMS[a], self.mm[name], mode) for name, (rs, mode) in parts.items() for a in ARMS}
        self.P = {}                                  # (part, arm) -> [S,N,2,3]
        self.models = {name: {} for name in parts}; self.ye = {}
        allrows = [r for name in parts for r in parts[name][0]]
        sizes = [len(parts[name][0]) for name in parts]; off = np.r_[0, np.cumsum(sizes)]
        self.lam = {}
        for a, kind in ARMS.items():
            Tev = [torch.cat([self.T[(name, a)][i] for name in parts]) for i in range(4)]
            t0 = time.time()
            pts, ptov, porb, ye, self.lam[a] = fit_b1(self.tr, tensors(self.tr, kind, self.means, 'train'), allrows, Tev)
            assert self.lam[a] == lam_frozen[a], f'B1 λ 與凍結值不同：{a} {self.lam[a]} vs {lam_frozen[a]}'
            print('B1', a, self.lam[a], f'{time.time() - t0:.0f}s', flush=True)
            for k, name in enumerate(parts):
                sl = slice(2 * off[k], 2 * off[k + 1])
                self.models[name]['B1-' + kind] = (pts[sl], ptov[sl], porb[sl]); self.ye.setdefault(name, ye[sl])
        for name in parts:
            for a in ARMS:
                self.P[(name, a)] = t_raw(self.nets[a], self.T[(name, a)])
                self.models[name][a] = ens(self.P[(name, a)])
            rs = parts[name][0]
            sea2 = np.repeat([r['season'] for r in rs], 2)
            tv = {s: sum(r['tova'] + r['tovb'] for r in self.tr if r['season'] == s) / sum(r['possa'] + r['possb'] for r in self.tr if r['season'] == s) for s in SEASONS}
            ob = {s: sum(r['orba'] + r['orbb'] for r in self.tr if r['season'] == s) / sum(r['rebOppa'] + r['rebOppb'] for r in self.tr if r['season'] == s) for s in SEASONS}
            self.models[name]['B0'] = (np.zeros(len(sea2)), np.array([tv[s] for s in sea2]), np.array([ob[s] for s in sea2]))


def evaluate_set(ctx, name, label, kfit, mde, guard):
    ev = ctx.parts[name][0]; models = dict(ctx.models[name]); ye = ctx.ye[name]
    # 5 seed 各自的淨值 MSE（只當分布報告）
    for a in ARMS:
        for sd in SEEDS:
            P = ctx.P[(name, a)][sd:sd + 1]
            models[f'{a}#{sd}'] = ens(P)
    res, gm, act, G, Pw = metrics(ev, ye, models); draws = draws_for(G)
    main = [k for k in res if '#' not in k]
    out = {'label': label, 'games': G, 'stints': len(ev), 'poss': round(float(Pw.sum() * 2)),
           'mse': {k: round(val(res, k, 'net'), 2) for k in main},
           'seedMSE': {a: [round(val(res, f'{a}#{sd}', 'net'), 2) for sd in SEEDS] for a in ARMS},
           'side': {k: {m: round(val(res, k, m), 5) for m in ('ptsSide', 'tovLL', 'orbLL')} for k in main}, 'paired': {}, 'game': {}}
    A0 = 'R2-abil'
    for a, kind in ARMS.items():
        b1 = 'B1-' + kind
        out['paired'][f'{a}−{b1}'] = paired(res, a, b1, 'net', draws)
        out['paired'][f'{b1}−B0'] = paired(res, b1, 'B0', 'net', draws)
        out['paired'][f'{a}−B0'] = paired(res, a, 'B0', 'net', draws)
        if a != A0:
            p = paired(res, a, A0, 'net', draws); p['guard'] = {m: paired(res, a, A0, m, draws) for m in ('ptsSide', 'tovLL', 'orbLL')}
            out['paired'][f'{a}−{A0}'] = p
            out['paired'][f'{a}−{b1}']['guard'] = {m: paired(res, a, b1, m, draws) for m in ('ptsSide', 'tovLL', 'orbLL')}
    out['paired']['R2-stats-rapm−R2-stats'] = paired(res, 'R2-stats-rapm', 'R2-stats', 'net', draws)
    win = (act > 0).astype(float)
    for k in main:
        g = gm[k]; mse = float(((act - g) ** 2).mean())
        kk = kfit.get(k) if kfit is not None else fit_k(g, act)
        brier = float(((sig(kk * g) - win) ** 2).mean()) if k != 'B0' else 0.25
        out['game'][k] = {'marginMSE': round(mse, 2), 'brier': round(brier, 5), 'k': round(kk, 5) if k != 'B0' else None}
    if mde is not None:
        out['verdict'] = {}
        for a in ('R2-stats', 'R2-stats-rapm'):
            p = out['paired'][f'{a}−{A0}']; m_ = mde[a]
            j1 = bool(p['point'] <= -m_ and p['ci90'][1] < 0)
            g2 = {m: {'point': p['guard'][m]['point'], 'threshold': guard[a][m], 'ok': bool(p['guard'][m]['point'] <= guard[a][m])} for m in ('ptsSide', 'tovLL', 'orbLL')}
            out['verdict'][a] = {'judge1': {'point': p['point'], 'ci90': p['ci90'], 'needAtMost': -m_, 'pass': j1}, 'judge2': g2, 'judge2pass': all(v['ok'] for v in g2.values())}
    return out, gm, act


def feature_names(kind):
    return ATTRS + (STATS if kind != 'abil' else []) + (['rapmOff', 'rapmDef'] if kind == 'stats-rapm' else [])


def importance(ctx, name, reps=2):
    """排列重要性：在 ev 上把某一項（值與遮罩一起）在全部球員 token 間打亂，看 5 seed 平均預測的淨值 MSE 上升；另算類別（整類一起打亂）。"""
    out = {}
    for arm, kind in ARMS.items():
        F = n_feat(kind); names = feature_names(kind); T = ctx.T[(name, arm)]
        y = T[3].numpy(); pts2, poss2 = y[..., 0].reshape(-1), y[..., 1].reshape(-1)
        possA, possB = poss2[0::2], poss2[1::2]; Pw = (possA + possB) / 2
        actual = np.where(Pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw, 1e-9), 0); m = y[..., 5].reshape(-1)

        def mse(attr):
            P = ens(t_raw(ctx.nets[arm], [attr, T[1], T[2], T[3]]))[0]
            muA, muB = P[0::2] + m[0::2], P[1::2] + m[1::2]
            pred = 100 * (muA * possA - muB * possB) / np.maximum(Pw, 1e-9)
            return float((Pw * (actual - pred) ** 2).sum() / Pw.sum())
        base = mse(T[0]); N = T[0].shape[0]
        groups = {'abil': [names.index(c) for c in ATTRS]}
        for cl, cols in STAT_CLASSES.items():
            if kind != 'abil':
                groups['stat:' + cl] = [names.index(c) for c in cols]
        if kind == 'stats-rapm':
            groups['rapm'] = [names.index('rapmOff'), names.index('rapmDef')]
        singles = {c: [i] for i, c in enumerate(names)}
        res = {}
        for label, fs in {**{'g:' + k: v for k, v in groups.items()}, **singles}.items():
            idx = fs + [F + f for f in fs]; ups = []
            rng = np.random.default_rng(7)
            for _ in range(reps):
                a = T[0].clone(); perm = torch.from_numpy(rng.permutation(N * 10)); flat = a.reshape(N * 10, -1)
                flat[:, idx] = flat[perm][:, idx]   # 同一排列搬動整組欄位（值與遮罩一起）
                ups.append(mse(a) - base)
            res[label] = round(float(np.mean(ups)), 3)
        out[arm] = {'baseMSE': round(base, 2), 'groups': {k[2:]: v for k, v in sorted(res.items(), key=lambda kv: -kv[1]) if k.startswith('g:')},
                    'features': dict(sorted(((k, v) for k, v in res.items() if not k.startswith('g:')), key=lambda kv: -kv[1]))}
        print('importance', arm, flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--target', required=True, choices=['fold0', 'test']); a = ap.parse_args()
    mj = json.load(open(os.path.join(HERE, 'mde-noise.json'), encoding='utf-8'))
    mde = {arm: mj['arms'][arm]['mde'] for arm in ('R2-stats', 'R2-stats-rapm')}
    guard = {arm: {m: mj['arms'][arm]['guard2VsAbil'][m]['threshold'] for m in ('ptsSide', 'tovLL', 'orbLL')} for arm in ('R2-stats', 'R2-stats-rapm')}
    rows = load_rows(SEASONS); fold0 = [r for r in rows if r['fold'] == 0]
    parts = {'fold0': (fold0, 'val')}
    if a.target == 'test':
        parts['test'] = (load_test(), 'test'); parts['forward'] = (load_forward(), 'test')
    else:
        parts['dry'] = ([r for r in fold0 if r['season'] == '2024-25'], 'val')
    ctx = Ctx(parts, mj['b1Lambda'])
    f0, gm0, act0 = evaluate_set(ctx, 'fold0', 'fold0 (weights early-stopped on fold 0)', None, mde, guard)
    kfit = {k: v['k'] for k, v in f0['game'].items()}
    out = {'target': a.target, 'mde': mde, 'guardThresholds': guard, 'b1Lambda': ctx.lam, 'fold0': f0}
    if a.target == 'fold0':
        out['dry'], _, _ = evaluate_set(ctx, 'dry', 'dry (fold0 2024-25)', kfit, mde, guard)
        out['importance'] = importance(ctx, 'dry', reps=1)
    else:
        out['test'], _, _ = evaluate_set(ctx, 'test', 'test (5 seasons, split=test, RAPM key none)', kfit, mde, guard)
        fw = ctx.parts['forward'][0]
        out['forward'], _, _ = evaluate_set(ctx, 'forward', 'forward 2026-27 (prior-season features)', kfit, None, guard)
        out['forward']['note'] = {'games': len({r['gid'] for r in fw}), 'preFreezeGames': len({r['gid'] for r in fw}), 'postFreezeGames': 0,
                                  'features': '2025-26 表＋RAPM(none)；聯盟均值＝2026-27 自己的每回合得分'}
        out['importance'] = importance(ctx, 'test')
    fn = os.path.join(HERE, 'results', 'eval-fold0-dry.json' if a.target == 'fold0' else 'test-results.json')
    json.dump(out, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(fn)


if __name__ == '__main__':
    main()
