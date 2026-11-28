"""E-286 描述：2026-27 目前戰力排行，E-285 全資料權重 B vs X（run_t 同口徑，兩臂同抽樣）。本機 CPU 輕量。
  python -I -X utf8 current.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from x286 import ctx, X, T, np, torch, REP  # noqa: E402
sys.path.insert(0, os.path.join(REP, 'E229-transformer-vs-m0-forward'))
import e229_live  # noqa: E402
from e227_model import predict  # noqa: E402
ROOT = os.path.dirname(REP)
TR = json.load(open(os.path.join(ROOT, 'data', 'season-source-2026-27', 'team-ratings.json'), encoding='utf-8'))
W = os.path.join(REP, 'E285-transformer-def-inputs', 'results', 'weights')
N_OPP = 70


def main():
    torch.set_num_threads(4)
    today = TR['today'] if isinstance(TR['today'], str) else TR['dataCutoff']
    ldir = os.path.join(e229_live.LIVE_ROOT, TR['dataCutoff'])
    ldir = ldir if os.path.exists(os.path.join(ldir, 'ranking.csv')) else e229_live.live_dir()
    teams = TR['teams']; tids = sorted(teams)
    rots = {t: [(int(r['pid']), float(r['min'])) for r in teams[t]['c']['rotation']] for t in tids}
    names = {p: 1 for r in rots.values() for p, _ in r}
    T.KIND, T.F = 'stats', X.n_feat('stats')
    B41, tab, info = e229_live.build(today, ldir, names)
    ext = X.base_feats('2025-26', 'statsx')
    k = len(X.XCOLS); out = {}
    for arm, wn in (('B', 'R2-stats'), ('X', 'R2-statsX')):
        C = ctx(arm, os.path.join(W, wn + '-{}.pt'), '2025-26')
        if arm == 'B':
            C.B = B41
        else:
            z = (np.zeros(k, np.float32), np.zeros(k, np.float32))
            C.B = {p: (np.concatenate([v, (ext[p][0][-k:] if p in ext else z[0])]), np.concatenate([m, (ext[p][1][-k:] if p in ext else z[1])]))
                   for p, (v, m) in B41.items()}
        C.tab = tab; C.med_h = float(np.median([d['heightInches'] for d in tab.values() if d.get('heightInches') is not None]))
        prep = {t: C.prep(rots[t]) for t in tids}
        pos = torch.tensor(list(range(5)) * 2).unsqueeze(0); side = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
        res = {}
        for t in tids:
            rng = np.random.default_rng([229, int(t), sum(map(ord, 'c'))])
            opp = np.concatenate([C.draw(*prep[o], rng, N_OPP) for o in tids if o != t]); own = C.draw(*prep[t], rng, len(opp)); n = len(own)
            Xt = torch.from_numpy(np.concatenate([np.concatenate([own, opp], 1), np.concatenate([opp, own], 1)], 0))
            Tn = [Xt, pos.expand(2 * n, -1), side.expand(2 * n, -1)]; pf = pa = 0.0
            for m in C.nets:
                o = predict(m, Tn, C.dev, bs=8192)[:, :, 0].numpy()
                pf += 100.0 * 0.5 * (o[:n, 0].mean() + o[n:, 1].mean()) / len(C.nets)
                pa += 100.0 * 0.5 * (o[:n, 1].mean() + o[n:, 0].mean()) / len(C.nets)
            res[t] = {'ortg': float(pf), 'drtg': float(pa), 'net': float(pf - pa)}
        out[arm] = res
    rk = lambda d: {t: i + 1 for i, t in enumerate(sorted(d, key=lambda t: -d[t]))}
    nB, nX, nL = ({t: out[a][t]['net'] for t in tids} for a in ('B', 'X')), None, {t: teams[t]['c']['net'] for t in tids}
    nB, nX = list(nB)
    rB, rX, rL = rk(nB), rk(nX), rk(nL)
    dB = {t: -out['B'][t]['drtg'] for t in tids}; dX = {t: -out['X'][t]['drtg'] for t in tids}
    rdB, rdX = rk(dB), rk(dX)
    rows = sorted(({'team': teams[t]['abbr'], 'W': teams[t]['W'], 'L': teams[t]['L'], 'liveNet': round(nL[t], 2), 'liveRank': rL[t],
                    'netB': round(nB[t], 2), 'rankB': rB[t], 'netX': round(nX[t], 2), 'rankX': rX[t],
                    'defRankB': rdB[t], 'defRankX': rdX[t], 'dDef': round(dX[t] - dB[t], 2)} for t in tids), key=lambda r: r['rankX'])
    from scipy.stats import spearmanr
    summ = {'today': today, 'liveDir': os.path.basename(ldir), 'rho_B_X': float(spearmanr([nB[t] for t in tids], [nX[t] for t in tids])[0]),
            'rho_live_B': float(spearmanr([nL[t] for t in tids], [nB[t] for t in tids])[0]), 'info': info}
    json.dump({'summary': summ, 'rows': rows}, open(os.path.join(HERE, 'results', 'current.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False)[:400])
    for r in rows:
        print(r)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
