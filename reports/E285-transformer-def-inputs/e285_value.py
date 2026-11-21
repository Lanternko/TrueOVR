"""E-285 個人價值（E-227 e227_value 同算法、同母體、同亂數）：2025-26 上場 ≥1000 分鐘；固定在最常出現的位置；
其餘隊友與對手按位置從同位置母體抽 4000 組（RandomState(225)）；價值＝他 vs 隨機同位置真人；A、B 兩邊平均；5 seed 平均。
另外拆成進攻（本隊每 100 回合得分差）與防守（對手每 100 回合失分差，正＝少失分）。兩臂：R2-stats、R2-statsX。
  python -I -X utf8 e285_value.py
"""
import csv, gzip, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import x_lib as X  # noqa: E402
import numpy as np, torch  # noqa: E402
from e227_model import LineupNet, base_feats, n_feat, predict  # noqa: E402
SEASON, NDRAW = '2025-26', 4000
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
E225 = os.path.join(os.path.dirname(X.SRC), 'E225-lineup-transformer', 'data')


def pts_of(nets, A, B):
    n = A.shape[0]; T = [torch.cat([A, B], 1), POS.expand(n, -1), SIDE.expand(n, -1)]
    P = np.stack([predict(m, T, DEV, bs=16384).numpy() for m in nets])
    return 100 * P[:, :, 0, 0].mean(0), 100 * P[:, :, 1, 0].mean(0)   # A 得分率、B 得分率（相對聯盟平均）


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
        aA, bA = pts_of(nets, torch.cat([ta, tr]), torch.cat([op, op]))     # 他在 A 邊
        aB, bB = pts_of(nets, torch.cat([op, op]), torch.cat([ta, tr]))     # 他在 B 邊
        off[p] = 0.5 * ((aA[:NDRAW] - aA[NDRAW:]).mean() + (bB[:NDRAW] - bB[NDRAW:]).mean())
        dfn[p] = -0.5 * ((bA[:NDRAW] - bA[NDRAW:]).mean() + (aB[:NDRAW] - aB[NDRAW:]).mean())
        if p % 40 == 0:
            print(f'  {p}/{len(modal)} {time.time() - t0:.0f}s', flush=True)
    return off, dfn


def main():
    secs, posw = {}, {}
    with gzip.open(os.path.join(E225, f'stints-{SEASON}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            s = float(r['sec'])
            for x in 'ab':
                for j in range(5):
                    pid = r[f'{x}{j}']; secs[pid] = secs.get(pid, 0) + s
                    posw.setdefault(pid, np.zeros(5))[int(r[f'p{x}{j}'])] += s
    pl = {r['pid']: r for r in csv.DictReader(open(os.path.join(X.SRC, 'data', f'players-{SEASON}.csv'), encoding='utf-8'))}
    B = {a: base_feats(SEASON, k) for a, k in X.ARMS.items()}
    elig = sorted(p for p, s in secs.items() if s / 60 >= 1000 and p in pl and all(p in B[a] for a in B))
    modal = [int(posw[p].argmax()) for p in elig]
    out = {'season': SEASON, 'ndraw': NDRAW, 'pids': elig, 'names': [pl[p]['name'] for p in elig], 'modal': modal,
           'min': [round(secs[p] / 60, 1) for p in elig], 'arms': {}}
    for a, k in X.ARMS.items():
        F = n_feat(k); PV = np.array([np.concatenate([B[a][p][0], B[a][p][1]]) for p in elig], np.float32)
        nets = []
        for sd in range(5):
            n = LineupNet(F); n.load_state_dict(torch.load(os.path.join(HERE, 'results', 'weights', f'{a}-{sd}.pt'), map_location='cpu')); n.eval(); nets.append(n.to(DEV))
        print(a, len(elig), flush=True)
        o, d = values(nets, PV, modal)
        out['arms'][a] = {'off': o.tolist(), 'def': d.tolist(), 'net': (o + d).tolist()}
    json.dump(out, open(os.path.join(HERE, 'results', 'value.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('done')


if __name__ == '__main__':
    main()
