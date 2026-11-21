"""E-227 只報告項：個人價值 v2（沿用 E-225 追問 e225_value_v2 的新算法，不改演算法）。
母體：2025-26 上場 ≥1000 分鐘的球員（分鐘取自 E-225 完整 stints 的秒數，只用秒數，不看結果）。特徵用 2025-26（RAPM 用 key none）。
他固定在最常出現的位置；其餘 4 個隊友位置、對手 5 人都按位置從同位置母體真人抽（對手不抽到他自己）；4000 組共用亂數 RandomState(225)；
價值＝抽樣平均預測淨值（每100回合）－同一批抽樣把他換成隨機同位置真人的平均淨值；A 邊與 B 邊各算一次取平均；5 seed 平均。
四個模型：R2-abil、R2-stats、R2-stats-rapm（E-227 權重）與 E-225 T-nomin（E-225 權重，E-225 特徵版面，2025-26 特徵重算）。
  python -I -X utf8 e227_value.py --prep            # 本機：產生 results/value-prep.json（特徵向量、位置、分鐘）
  python -I -X utf8 e227_value.py --run [--dev cuda] [--limit N]   # 5090：讀 prep＋權重，寫 results/value-raw.json
"""
import argparse, json, os, sys, time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = range(5)
SEASON = '2025-26'
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)


def prep():
    import csv, gzip
    from e227_common import ARMS, ATTRS
    from e227_model import base_feats, n_feat
    from e227_common import load_rapm
    ROOT = os.path.dirname(os.path.dirname(HERE)); E225 = os.path.join(ROOT, 'reports', 'E225-lineup-transformer')
    secs, posw = {}, {}
    with gzip.open(os.path.join(E225, 'data', f'stints-{SEASON}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            s = float(r['sec'])
            for x in 'ab':
                for j in range(5):
                    pid = r[f'{x}{j}']; secs[pid] = secs.get(pid, 0) + s
                    posw.setdefault(pid, np.zeros(5))[int(r[f'p{x}{j}'])] += s
    pl = {r['pid']: r for r in csv.DictReader(open(os.path.join(HERE, 'data', f'players-{SEASON}.csv'), encoding='utf-8'))}
    feats = {}
    for arm, kind in ARMS.items():
        B = base_feats(SEASON, kind); R = load_rapm(SEASON, 'none') if kind == 'stats-rapm' else None
        F = n_feat(kind); F0 = F - (2 if kind == 'stats-rapm' else 0); d = {}
        for p, (v, m) in B.items():
            vec = np.zeros(2 * F, np.float32); vec[:F0] = v; vec[F:F + F0] = m
            if R is not None:
                q = R.get(p)
                if q is not None and q[2] > 0:
                    vec[F0], vec[F0 + 1] = q[0], q[1]; vec[F + F0] = vec[F + F0 + 1] = 1.0
            d[p] = vec
        feats[arm] = d
    # E-225 T-nomin：E-225 的特徵版面，2025-26 特徵重算
    sys.path.insert(0, E225)
    import e225_common as c5
    P5 = c5.load_players(SEASON, False)   # T-nomin 臂＝能力值 only? 以 e225_model.ARMS 為準，下面核對
    import e225_model as m5
    um = m5.ARMS['T-nomin']; P5 = c5.load_players(SEASON, um); F5 = len(c5.FEATS) if um else len(c5.ATTRS)
    feats['E225-T-nomin'] = {p: np.concatenate([v[0], v[1]]).astype(np.float32) for p, v in P5.items()}
    nfeat = {**{a: n_feat(k) for a, k in ARMS.items()}, 'E225-T-nomin': F5}
    elig = sorted(p for p, s in secs.items() if s / 60 >= 1000 and p in pl and all(p in feats[a] for a in feats))
    out = {'season': SEASON, 'pids': elig, 'names': [pl[p]['name'] for p in elig], 'modal': [int(posw[p].argmax()) for p in elig],
           'min': [round(secs[p] / 60, 1) for p in elig], 'nfeat': nfeat,
           'feats': {a: [feats[a][p].tolist() for p in elig] for a in feats}}
    json.dump(out, open(os.path.join(HERE, 'results', 'value-prep.json'), 'w'))
    print('eligible', len(elig), 'E225 um', um, 'F5', F5)


def load_nets(arm, F, E225W):
    from e227_model import LineupNet
    nets = []
    for sd in SEEDS:
        fn = os.path.join(E225W, f'T-nomin-{sd}.pt') if arm == 'E225-T-nomin' else os.path.join(HERE, 'results', 'weights', f'{arm}-{sd}.pt')
        n = LineupNet(F); n.load_state_dict(torch.load(fn, map_location='cpu')); n.eval(); nets.append(n)
    return nets


def net_of(nets, A, B, dev):
    from e227_model import predict
    n = A.shape[0]; T = [torch.cat([A, B], 1), POS.expand(n, -1), SIDE.expand(n, -1)]
    T = [t.to(dev) for t in T]
    outs = []
    for m in nets:
        o = predict(m, T, dev, bs=16384)
        outs.append(o.cpu().numpy())
    P = np.stack(outs)
    return 100 * (P[:, :, 0, 0] - P[:, :, 1, 0]).mean(0)


def new_values(nets, PV_all, modal, ndraw, seed, tg, dev):
    pool = {k: [i for i in range(len(modal)) if modal[i] == k] for k in range(5)}
    PV = {k: torch.from_numpy(PV_all[pool[k]]) for k in range(5)}
    rs = np.random.RandomState(seed)
    uT = rs.rand(ndraw, 5); uO = rs.rand(ndraw, 5); uR = rs.rand(ndraw)
    res = np.zeros(len(tg)); t0 = time.time()
    for ii, p in enumerate(tg):
        k = modal[p]; me = pool[k].index(p); pk = len(pool[k]); tm, op = [], []
        for q in range(5):
            n = len(pool[q]); tm.append(PV[q][(uT[:, q] * n).astype(int)])
            if q == k:
                j = (uO[:, q] * (n - 1)).astype(int); j = j + (j >= me); op.append(PV[q][j])
            else:
                op.append(PV[q][(uO[:, q] * n).astype(int)])
        tm = torch.stack(tm, 1); op = torch.stack(op, 1)
        jr = (uR * (pk - 1)).astype(int); jr = jr + (jr >= me)
        repl = PV[k][jr]; mine = PV[k][me].unsqueeze(0).expand(ndraw, -1)

        def team(slot):
            t = tm.clone(); t[:, k] = slot; return t
        ta, tr = team(mine), team(repl)
        nA = net_of(nets, torch.cat([ta, tr]), torch.cat([op, op]), dev)
        nB = -net_of(nets, torch.cat([op, op]), torch.cat([ta, tr]), dev)
        res[ii] = 0.5 * ((nA[:ndraw] - nA[ndraw:]).mean() + (nB[:ndraw] - nB[ndraw:]).mean())
        if ii % 40 == 0:
            print(f'  {ii}/{len(tg)} {time.time() - t0:.0f}s', flush=True)
    return res


def run(a):
    torch.set_num_threads(8)
    pr = json.load(open(os.path.join(HERE, 'results', 'value-prep.json'), encoding='utf-8'))
    modal = pr['modal']; n = len(pr['pids']); tg = list(range(a.limit if a.limit else n))
    E225W = a.e225w
    out = {'ndraw': a.ndraw, 'n': len(tg), 'pids': pr['pids'][:len(tg)], 'names': pr['names'][:len(tg)], 'modalPos': modal[:len(tg)], 'min': pr['min'][:len(tg)], 'new': {}}
    for arm in pr['feats']:
        print(arm, flush=True)
        nets = [m.to(a.dev) for m in load_nets(arm, pr['nfeat'][arm], E225W)]
        out['new'][arm] = new_values(nets, np.array(pr['feats'][arm], np.float32), modal, a.ndraw, 225, tg, a.dev).tolist()
    json.dump(out, open(os.path.join(HERE, 'results', 'value-raw.json' if not a.limit else 'value-raw-limit.json'), 'w'))
    print('done')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--prep', action='store_true'); ap.add_argument('--run', action='store_true')
    ap.add_argument('--ndraw', type=int, default=4000); ap.add_argument('--limit', type=int, default=0); ap.add_argument('--dev', default='cpu')
    ap.add_argument('--e225w', default=os.path.join(os.path.dirname(os.path.dirname(HERE)), 'reports', 'E225-lineup-transformer', 'results', 'weights'))
    a = ap.parse_args()
    if a.prep:
        prep()
    if a.run:
        run(a)
