"""E-297 換人值（E-285 e285_value 同算法、同母體 2025-26 ≥1000 分鐘、同亂數 RandomState(225)、4000 組、5 seed 平均）。
臂 ALL#mask＝ALL 權重但 12 個無球欄（值與遮罩）全清 0，供第三階段 ΔT_off。每臂存 results/value-<臂>.json。
  python -I -X utf8 value.py --arms base,+cut36,...
"""
import argparse, csv, gzip, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import o_lib as X  # noqa: E402
import numpy as np, torch  # noqa: E402
from e227_model import LineupNet, base_feats, n_feat, predict  # noqa: E402
SEASON, NDRAW = '2025-26', 4000
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
E225 = os.path.join(os.path.dirname(X.SRC), 'E225-lineup-transformer', 'data')


def pts_of(nets, A, B):
    n = A.shape[0]; T = [torch.cat([A, B], 1), POS.expand(n, -1), SIDE.expand(n, -1)]
    P = np.stack([predict(m, T, DEV, bs=16384).numpy() for m in nets])
    return 100 * P[:, :, 0, 0].mean(0), 100 * P[:, :, 1, 0].mean(0)


def values(nets, PV_all, modal):
    pool = {k: [i for i in range(len(modal)) if modal[i] == k] for k in range(5)}
    PV = {k: torch.from_numpy(PV_all[pool[k]]) for k in range(5)}
    rs = np.random.RandomState(225); uT = rs.rand(NDRAW, 5); uO = rs.rand(NDRAW, 5); uR = rs.rand(NDRAW)
    off, dfn = np.zeros(len(modal)), np.zeros(len(modal)); t0 = time.time()
    for p in range(len(modal)):
        k = modal[p]; me = pool[k].index(p); pk = len(pool[k]); tm, op = [], []
        for q in range(5):
            n = len(pool[q]); tm.append(PV[q][(uT[:, q] * n).astype(int)])
            if q == k:
                j = (uO[:, q] * (n - 1)).astype(int); j = j + (j >= me); op.append(PV[q][j])
            else:
                op.append(PV[q][(uO[:, q] * n).astype(int)])
        tm = torch.stack(tm, 1); op = torch.stack(op, 1)
        jr = (uR * (pk - 1)).astype(int); jr = jr + (jr >= me)
        ta, tr = tm.clone(), tm.clone(); ta[:, k] = PV[k][me]; tr[:, k] = PV[k][jr]
        aA, bA = pts_of(nets, torch.cat([ta, tr]), torch.cat([op, op]))
        aB, bB = pts_of(nets, torch.cat([op, op]), torch.cat([ta, tr]))
        off[p] = 0.5 * ((aA[:NDRAW] - aA[NDRAW:]).mean() + (bB[:NDRAW] - bB[NDRAW:]).mean())
        dfn[p] = -0.5 * ((bA[:NDRAW] - bA[NDRAW:]).mean() + (aB[:NDRAW] - aB[NDRAW:]).mean())
        if p % 60 == 0:
            print(f'  {p}/{len(modal)} {time.time() - t0:.0f}s', flush=True)
    return off, dfn


def population():
    secs, posw = {}, {}
    with gzip.open(os.path.join(E225, f'stints-{SEASON}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            s = float(r['sec'])
            for x in 'ab':
                for j in range(5):
                    pid = r[f'{x}{j}']; secs[pid] = secs.get(pid, 0) + s
                    posw.setdefault(pid, np.zeros(5))[int(r[f'p{x}{j}'])] += s
    pl = {r['pid']: r for r in csv.DictReader(open(os.path.join(X.SRC, 'data', f'players-{SEASON}.csv'), encoding='utf-8'))}
    Ball = base_feats(SEASON, 'ob:' + '+'.join(X.OB))
    elig = sorted(p for p, s in secs.items() if s / 60 >= 1000 and p in pl and p in Ball)
    return elig, [int(posw[p].argmax()) for p in elig], pl, secs


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--arms', required=True); a = ap.parse_args()
    elig, modal, pl, secs = population()
    for arm in a.arms.split(','):
        src = arm.split('#')[0]; kind = X.kind_of(src); F = n_feat(kind); B = base_feats(SEASON, kind)
        PV = np.array([np.concatenate([B[p][0], B[p][1]]) for p in elig], np.float32)
        if arm.endswith('#mask'):
            F0 = n_feat('stats'); PV[:, F0:F] = 0; PV[:, F + F0:] = 0
        nets = []
        for sd in range(5):
            n = LineupNet(F); n.load_state_dict(torch.load(os.path.join(HERE, 'results', 'weights', f'{src}-{sd}.pt'), map_location='cpu')); n.eval(); nets.append(n.to(DEV))
        print(arm, len(elig), flush=True)
        o, d = values(nets, PV, modal)
        json.dump({'season': SEASON, 'ndraw': NDRAW, 'arm': arm, 'pids': elig, 'names': [pl[p]['name'] for p in elig], 'modal': modal,
                   'min': [round(secs[p] / 60, 1) for p in elig], 'off': o.tolist(), 'def': d.tolist(), 'net': (o + d).tolist()},
                  open(os.path.join(HERE, 'results', f'value-{arm}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('VALUE_DONE', a.arms)


if __name__ == '__main__':
    main()
