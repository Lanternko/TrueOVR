"""E-297 評估（prereg.md 凍結後只跑一次）。
第一階段（fold 0）：base 殘差／實際淨值 對 五人 z 和差 的加權斜率＋以場 bootstrap。
第二階段：每臂對 base 的測試／前向淨值 MSE、成對 bootstrap、比賽 Brier（k 在 fold 0 擬合）、護欄；ALL／SEL 測試集置換重要度。
  python -I -X utf8 eval.py
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import o_lib as X  # noqa: E402
import numpy as np, torch  # noqa: E402
import e227_eval as EV  # noqa: E402
from e227_common import SEASONS, load_rows  # noqa: E402
from e227_model import LineupNet, n_feat, predict, season_means, tensors, base_feats  # noqa: E402
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
W = os.path.join(HERE, 'results', 'weights')


def arms():
    a = ['base'] + ['+' + c for c in X.OB] + ['ALL']
    if os.path.exists(os.path.join(HERE, 'results', 'sel.json')) and X.arm_cols('SEL'):
        a.append('SEL')
    return a


def nets(arm):
    out = []
    for sd in EV.SEEDS:
        n = LineupNet(n_feat(X.kind_of(arm))); n.load_state_dict(torch.load(os.path.join(W, f'{arm}-{sd}.pt'), map_location='cpu')); n.eval(); out.append(n.to(DEV))
    return out


def raw(ns, T):
    return np.stack([predict(n, T, DEV, bs=16384).numpy() for n in ns])


def stage1(rows, means, Nb, draws_seed=20261109):
    """fold 0：五人 z 和差 D（A−B）對 base 殘差與實際淨值的加權斜率（每 1 單位 z 和差，每 100 回合）。"""
    T = tensors(rows, 'stats', means, 'val'); ye = T[3].numpy().reshape(-1, 6)
    pts, ptov, porb = EV.ens(raw(Nb, T))
    pts2, poss2, mean2 = ye[:, 0], ye[:, 1], ye[:, 5]
    pa, pb = poss2[0::2], poss2[1::2]; Pw = (pa + pb) / 2
    act = np.where(Pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw, 1e-9), 0)
    pred = 100 * ((pts[0::2] + mean2[0::2]) * pa - (pts[1::2] + mean2[1::2]) * pb) / np.maximum(Pw, 1e-9)
    res = act - pred
    kind = 'ob:' + '+'.join(X.OB); B = {s: base_feats(s, kind) for s in {r['season'] for r in rows}}; F0 = n_feat('stats')
    D = np.zeros((len(rows), len(X.OB)))
    for i, r in enumerate(rows):
        Bs = B[r['season']]
        for sgn, x in ((1, 'a'), (-1, 'b')):
            for j in range(5):
                p = Bs.get(r[x + str(j)])
                if p is not None:
                    D[i] += sgn * p[0][F0:]
    games = list(dict.fromkeys(r['gid'] for r in rows)); gmap = {g: k for k, g in enumerate(games)}; gi = np.array([gmap[r['gid']] for r in rows]); G = len(games)
    rng = np.random.default_rng(draws_seed); dr = np.stack([np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(2000)]).astype(float)
    out = {}
    for j, c in enumerate(X.OB):
        d = D[:, j]; o = {}
        for lab, y in (('residual', res), ('actual', act)):
            S = np.stack([np.bincount(gi, v, G) for v in (Pw, Pw * d, Pw * y, Pw * d * d, Pw * d * y)])   # [5, G]

            def slope(s):
                w, sd_, sy, sdd, sdy = s
                return (sdy - sd_ * sy / w) / (sdd - sd_ * sd_ / w)
            pt = slope(S.sum(1)); bs = slope(S @ dr.T)
            lo, hi = np.percentile(bs, [5, 95])
            o[lab] = {'slope': round(float(pt), 4), 'ci90': [round(float(lo), 4), round(float(hi), 4)]}
        o['sdLineupDiff'] = round(float(np.sqrt(np.average(d * d, weights=Pw))), 3)
        out[c] = o
    return out


def main():
    rows = load_rows(SEASONS); tr = [r for r in rows if r['fold'] != 0]; means = season_means(tr)
    A = arms(); N = {a: nets(a) for a in A}; BASE = 'base'
    out = {'arms': A, 'selected': X.arm_cols('SEL') if 'SEL' in A else []}
    f0 = [r for r in rows if r['fold'] == 0]
    out['stage1'] = stage1(f0, means, N[BASE]); print('stage1', json.dumps(out['stage1'], ensure_ascii=False), flush=True)
    parts = {'fold0': (f0, 'val'), 'test': (EV.load_test(), 'test'), 'forward': (EV.load_forward(), 'test')}
    kfit = {}
    for name, (rs, mode) in parts.items():
        mm = dict(means)
        if name == 'forward':
            mm['2025-26'] = sum(r['ptsa'] + r['ptsb'] for r in rs) / sum(r['possa'] + r['possb'] for r in rs)
        P, models = {}, {}
        for a in A:
            T = tensors(rs, X.kind_of(a), mm, mode)
            if a == BASE:
                ye = T[3].numpy().reshape(-1, 6); Tbase = T
            P[a] = raw(N[a], T); models[a] = EV.ens(P[a])
            if (a in ('ALL', 'SEL') and name == 'test') or (a == 'ALL' and name == 'fold0'):
                P[a + ':T'] = T
        res, gm, act, G, Pw = EV.metrics(rs, ye, models); draws = EV.draws_for(G)
        win = (act > 0).astype(float); o = {'games': G, 'stints': len(rs), 'arm': {}}
        for a in A:
            if name == 'fold0':
                kfit[a] = EV.fit_k(gm[a], act)
            r_ = {'mse': round(EV.val(res, a, 'net'), 3), 'brier': round(float(((EV.sig(kfit[a] * gm[a]) - win) ** 2).mean()), 5),
                  'side': {m: round(EV.val(res, a, m), 6) for m in ('ptsSide', 'tovLL', 'orbLL')}}
            if a != BASE:
                r_['dNet'] = EV.paired(res, a, BASE, 'net', draws)
                r_['dSide'] = {m: EV.paired(res, a, BASE, m, draws)['point'] for m in ('ptsSide', 'tovLL', 'orbLL')}
            o['arm'][a] = r_
        for a in A:
            if a != BASE:
                o['arm'][a]['dBrier'] = round(o['arm'][a]['brier'] - o['arm'][BASE]['brier'], 5)
        if name in ('test', 'fold0'):
            o['importance'] = {}
            for a in ('ALL', 'SEL'):
                if a not in A or a + ':T' not in P:
                    continue
                Tn = P[a + ':T']; y = Tn[3].numpy(); pts2, poss2 = y[..., 0].reshape(-1), y[..., 1].reshape(-1)
                pa, pb = poss2[0::2], poss2[1::2]; pw = (pa + pb) / 2; m = y[..., 5].reshape(-1)
                actual = np.where(pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(pw, 1e-9), 0)

                def mse(attr):
                    p = EV.ens(raw(N[a], [attr, Tn[1], Tn[2], Tn[3]]))[0]
                    pred = 100 * ((p[0::2] + m[0::2]) * pa - (p[1::2] + m[1::2]) * pb) / np.maximum(pw, 1e-9)
                    return float((pw * (actual - pred) ** 2).sum() / pw.sum())
                kind = X.kind_of(a); F = n_feat(kind); names = X.feature_names(kind); b0 = mse(Tn[0]); imp = {}
                groups = {c: [names.index(c)] for c in X.arm_cols(a) + ['creation', 'long', 'screenAst36', 'usg', 'astPct', 'rebound', 'oreb36']}
                groups['ALL_OB'] = [names.index(c) for c in X.arm_cols(a)]
                for lab, fs in groups.items():
                    idx = fs + [F + f for f in fs]; ups = []; rng = np.random.default_rng(7)
                    for _ in range(2):
                        a_ = Tn[0].clone(); flat = a_.reshape(-1, a_.shape[-1]); perm = torch.from_numpy(rng.permutation(flat.shape[0]))
                        flat[:, idx] = flat[perm][:, idx]; ups.append(mse(a_) - b0)
                    imp[lab] = round(float(np.mean(ups)), 3)
                o['importance'][a] = imp
        out[name] = o
        print(name, json.dumps({a: {k: v for k, v in o['arm'][a].items() if k in ('mse', 'dNet', 'dBrier')} for a in A}, ensure_ascii=False), flush=True)
    json.dump(out, open(os.path.join(HERE, 'results', 'eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('EVAL_DONE')


if __name__ == '__main__':
    main()
