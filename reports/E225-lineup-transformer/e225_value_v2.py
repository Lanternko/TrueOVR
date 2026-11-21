"""E-225 追問（只報告項）：個人價值新算法＋與外部指標相關。不動凍結判定與測試結果。
新算法：他固定在最常出現的推論位置；其餘 4 個隊友位置從 2024-25 上場 ≥1000 分鐘的真人（同位置）抽，用真人自己的特徵；
對手 5 人也按位置從真人抽；4000 組共用亂數（所有球員同一批抽樣）；他放 A 邊與 B 邊各算一次。
價值＝抽樣平均的預測淨值（每 100 回合）－同一批抽樣下把他的位置換成隨機同位置真人的平均淨值。兩臂×5 seed 平均。
  python -I -X utf8 e225_value_v2.py [--ndraw 4000]
"""
import argparse, csv, html, json, os, re, sys, time, unicodedata
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e225_common import ATTRS, FEATS, HERE, load_players, load_rows
from e225_model import ARMS, LineupNet, predict

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SEEDS = range(5)
torch.set_num_threads(8)


def norm(n):
    n = unicodedata.normalize('NFKD', html.unescape(n)).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[.']", '', n); n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n)
    return re.sub(r'[^a-z]', '', n)


def load_nets(arm):
    F = len(FEATS) if ARMS[arm] else len(ATTRS); nets = []
    for sd in SEEDS:
        n = LineupNet(F); n.load_state_dict(torch.load(os.path.join(HERE, 'results', 'weights', f'{arm}-{sd}.pt'))); n.eval(); nets.append(n)
    return nets


POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)


def net_of(nets, A, B):
    """A,B：[n,5,2F]（位置 0-4 排列）。回傳 5 seed 平均的 100·(μA−μB)。"""
    n = A.shape[0]; T = [torch.cat([A, B], 1), POS.expand(n, -1), SIDE.expand(n, -1)]
    P = np.stack([predict(m, T, 'cpu', bs=8192).numpy() for m in nets])
    return 100 * (P[:, :, 0, 0] - P[:, :, 1, 0]).mean(0)


def eligible():
    rows = load_rows(['2024-25'], splits=('train', 'test'), allow_holdout=True)
    secs, posw = {}, {}
    for r in rows:
        for x in 'ab':
            for j in range(5):
                pid = r[f'{x}{j}']; secs[pid] = secs.get(pid, 0) + r['sec']
                posw.setdefault(pid, np.zeros(5))[r[f'p{x}{j}']] += r['sec']
    pl = {r['pid']: r for r in csv.DictReader(open(os.path.join(HERE, 'data', 'players-2024-25.csv'), encoding='utf-8'))}
    elig = sorted(p for p, s in secs.items() if s / 60 >= 1000 and str(p) in pl)
    return elig, {p: int(posw[p].argmax()) for p in elig}, {p: secs[p] / 60 for p in elig}, pl


def old_values(nets, P, elig, modal, F, tg):
    med = np.zeros((5, 2 * F), np.float32)
    for k in range(5):
        ids = [p for p in elig if modal[p] == k]
        V = np.stack([P[str(p)][0] for p in ids]); M = np.stack([P[str(p)][1] for p in ids])
        for f in range(F):
            have = M[:, f] > 0
            med[k, f] = np.median(V[have, f]) if have.any() else 0; med[k, F + f] = 1.0 if have.any() else 0.0
    base = torch.from_numpy(med).unsqueeze(0); n0 = net_of(nets, base, base)[0]
    A = base.repeat(len(tg), 1, 1); Bm = base.repeat(len(tg), 1, 1)
    for i, p in enumerate(tg):
        v = torch.from_numpy(np.concatenate([P[str(p)][0], P[str(p)][1]])); A[i, modal[p]] = v; Bm[i, modal[p]] = v
    nA = net_of(nets, A, base.repeat(len(tg), 1, 1)) - n0; nB = net_of(nets, base.repeat(len(tg), 1, 1), Bm) - n0
    return 0.5 * (nA - nB)


def new_values(nets, P, elig, modal, F, ndraw, rng_state, tg):
    pool = {k: [p for p in elig if modal[p] == k] for k in range(5)}
    PV = {k: torch.from_numpy(np.stack([np.concatenate([P[str(p)][0], P[str(p)][1]]) for p in pool[k]])) for k in range(5)}
    rs = np.random.RandomState(rng_state)
    # 共用亂數：每組抽樣、每個位置一個 [0,1) 的值（隊友、對手、替換各一份），映射成該位置池內的索引
    uT = rs.rand(ndraw, 5); uO = rs.rand(ndraw, 5); uR = rs.rand(ndraw)
    res = np.zeros(len(tg)); t0 = time.time()
    for i, p in enumerate(tg):
        k = modal[p]; me = pool[k].index(p); pk = len(pool[k])
        tm, op = [], []
        for q in range(5):
            n = len(pool[q])
            tm.append(PV[q][(uT[:, q] * n).astype(int)])
            if q == k:   # 對手同位置不准抽到他自己：在去掉他的池內抽
                j = (uO[:, q] * (n - 1)).astype(int); j = j + (j >= me); op.append(PV[q][j])
            else:
                op.append(PV[q][(uO[:, q] * n).astype(int)])
        tm = torch.stack(tm, 1); op = torch.stack(op, 1)
        jr = (uR * (pk - 1)).astype(int); jr = jr + (jr >= me)
        repl = PV[k][jr]
        mine = PV[k][me].unsqueeze(0).expand(ndraw, -1)
        def team(slot):
            t = tm.clone(); t[:, k] = slot; return t
        ta, tr = team(mine), team(repl)
        # A 邊：[他的隊 vs 對手]；B 邊：[對手 vs 他的隊]（淨值取 A−B，B 邊要取負）
        nA = net_of(nets, torch.cat([ta, tr]), torch.cat([op, op]))
        nB = -net_of(nets, torch.cat([op, op]), torch.cat([ta, tr]))
        v = 0.5 * ((nA[:ndraw] - nA[ndraw:]).mean() + (nB[:ndraw] - nB[ndraw:]).mean())
        res[i] = v
        if i % 40 == 0:
            print(f'  {i}/{len(tg)} {time.time() - t0:.0f}s', flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--ndraw', type=int, default=4000); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    elig, modal, mins, pl = eligible()
    tg = elig[:a.limit] if a.limit else elig
    print('eligible', len(elig), flush=True)
    new, old = {}, {}
    for arm, um in ARMS.items():
        P = load_players('2024-25', um); F = len(FEATS) if um else len(ATTRS); nets = load_nets(arm)
        print(arm, 'old', flush=True); old[arm] = old_values(nets, P, elig, modal, F, tg)
        print(arm, 'new', flush=True); new[arm] = new_values(nets, P, elig, modal, F, a.ndraw, 225, tg)
    out = {'ndraw': a.ndraw, 'n': len(tg), 'pids': [str(p) for p in tg], 'modalPos': [modal[p] for p in tg], 'min': [round(mins[p], 1) for p in tg],
           'new': {k: v.tolist() for k, v in new.items()}, 'old': {k: v.tolist() for k, v in old.items()}}
    json.dump(out, open(os.path.join(HERE, 'results', 'value-v2-raw.json' if a.limit == 0 else 'value-v2-raw-limit.json'), 'w'))
    print('done')


if __name__ == '__main__':
    main()
