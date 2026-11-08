"""E-285 評估（prereg.md 凍結後只跑一次）：測試集（5 季 split=test）與前向 2026-27（2025-26 特徵）。
淨值 MSE（5 seed 平均預測）、成對 bootstrap（以場為單位 2000 次）、ptsSide／tovLL／orbLL、比賽 Brier（k 在 fold 0 擬合）、新 4 欄排列重要性。
  python -I -X utf8 e285_eval.py
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import x_lib as X  # noqa: E402
import numpy as np, torch  # noqa: E402
import e227_eval as EV  # noqa: E402
from e227_common import SEASONS, load_rows  # noqa: E402
from e227_model import LineupNet, n_feat, predict, season_means, tensors  # noqa: E402
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
BASE, NEW = 'R2-stats', 'R2-statsX'


def nets(arm):
    out = []
    for sd in EV.SEEDS:
        n = LineupNet(n_feat(X.ARMS[arm])); n.load_state_dict(torch.load(os.path.join(HERE, 'results', 'weights', f'{arm}-{sd}.pt'), map_location='cpu')); n.eval(); out.append(n.to(DEV))
    return out


def raw(ns, T):
    return np.stack([predict(n, T, DEV, bs=16384).numpy() for n in ns])


def main():
    rows = load_rows(SEASONS); tr = [r for r in rows if r['fold'] != 0]; means = season_means(tr)
    parts = {'fold0': ([r for r in rows if r['fold'] == 0], 'val'), 'test': (EV.load_test(), 'test'), 'forward': (EV.load_forward(), 'test')}
    N = {a: nets(a) for a in X.ARMS}
    out, kfit = {}, {}
    for name, (rs, mode) in parts.items():
        mm = dict(means)
        if name == 'forward':
            mm['2025-26'] = sum(r['ptsa'] + r['ptsb'] for r in rs) / sum(r['possa'] + r['possb'] for r in rs)
        T = {a: tensors(rs, X.ARMS[a], mm, mode) for a in X.ARMS}
        P = {a: raw(N[a], T[a]) for a in X.ARMS}
        models = {a: EV.ens(P[a]) for a in X.ARMS}
        for a in X.ARMS:
            for sd in EV.SEEDS:
                models[f'{a}#{sd}'] = EV.ens(P[a][sd:sd + 1])
        ye = T[BASE][3].numpy().reshape(-1, 6)
        res, gm, act, G, Pw = EV.metrics(rs, ye, models); draws = EV.draws_for(G)
        o = {'games': G, 'stints': len(rs), 'mse': {a: round(EV.val(res, a, 'net'), 2) for a in X.ARMS},
             'seedMSE': {a: [round(EV.val(res, f'{a}#{sd}', 'net'), 2) for sd in EV.SEEDS] for a in X.ARMS},
             'side': {a: {m: round(EV.val(res, a, m), 5) for m in ('ptsSide', 'tovLL', 'orbLL')} for a in X.ARMS},
             'paired': {'net': EV.paired(res, NEW, BASE, 'net', draws), **{m: EV.paired(res, NEW, BASE, m, draws) for m in ('ptsSide', 'tovLL', 'orbLL')}},
             'game': {}}
        win = (act > 0).astype(float)
        for a in X.ARMS:
            g = gm[a]
            if name == 'fold0':
                kfit[a] = EV.fit_k(g, act)
            o['game'][a] = {'marginMSE': round(float(((act - g) ** 2).mean()), 2), 'brier': round(float(((EV.sig(kfit[a] * g) - win) ** 2).mean()), 5), 'k': round(kfit[a], 5)}
        o['game']['dBrier'] = round(o['game'][NEW]['brier'] - o['game'][BASE]['brier'], 5)
        if name == 'test':   # 新 4 欄（值＋遮罩一起）在所有 token 間打亂，看淨值 MSE 上升
            Tn = T[NEW]; y = Tn[3].numpy(); pts2, poss2 = y[..., 0].reshape(-1), y[..., 1].reshape(-1)
            pa, pb = poss2[0::2], poss2[1::2]; pw = (pa + pb) / 2; m = y[..., 5].reshape(-1)
            actual = np.where(pw > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(pw, 1e-9), 0)

            def mse(attr):
                p = EV.ens(raw(N[NEW], [attr, Tn[1], Tn[2], Tn[3]]))[0]
                pred = 100 * ((p[0::2] + m[0::2]) * pa - (p[1::2] + m[1::2]) * pb) / np.maximum(pw, 1e-9)
                return float((pw * (actual - pred) ** 2).sum() / pw.sum())
            F = n_feat('statsx'); names = X.feature_names('statsx'); b0 = mse(Tn[0]); imp = {}
            groups = {c: [names.index(c)] for c in X.XCOLS + ['stl36', 'deflections36', 'charges36', 'pf36', 'blk36', 'pressure', 'onBall', 'help']}
            groups['ALL_NEW4'] = [names.index(c) for c in X.XCOLS]
            for lab, fs in groups.items():
                idx = fs + [F + f for f in fs]; ups = []; rng = np.random.default_rng(7)
                for _ in range(2):
                    a_ = Tn[0].clone(); flat = a_.reshape(-1, a_.shape[-1]); perm = torch.from_numpy(rng.permutation(flat.shape[0]))
                    flat[:, idx] = flat[perm][:, idx]; ups.append(mse(a_) - b0)
                imp[lab] = round(float(np.mean(ups)), 3)
            o['importanceNew'] = imp
        out[name] = o
        print(name, json.dumps({k: v for k, v in o.items() if k in ('mse', 'paired', 'game')}, ensure_ascii=False), flush=True)
    json.dump(out, open(os.path.join(HERE, 'results', 'eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
