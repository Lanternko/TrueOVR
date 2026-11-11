"""E-227 只報告項：五中鋒 vs 均衡陣容。母體＝value-prep.json（2025-26 ≥1000 分鐘者，特徵 2025-26）。
A 隊＝5 個隨機中鋒（modal 位置 4，不重複）、位置 token 全為 4；B 隊＝每個位置各抽 1 人（位置 token 0..4）。4000 組，RandomState(227)。
輸出：各臂（5 seed 平均）A 對 B 的淨值（每100回合，A 邊 B 邊平均），以及 A 隊對 A 隊自己（均衡隊對均衡隊）的對照 0 點。"""
import json, os, sys
import numpy as np, torch
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from e227_model import LineupNet, predict
pr = json.load(open(os.path.join(HERE, 'results', 'value-prep.json'), encoding='utf-8'))
modal = np.array(pr['modal']); N = 4000; rs = np.random.RandomState(227)
pool = {k: np.where(modal == k)[0] for k in range(5)}
SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
cen = np.stack([rs.choice(pool[4], 5, replace=False) for _ in range(N)])
bal = np.stack([[rs.choice(pool[k]) for k in range(5)] for _ in range(N)])
bal2 = np.stack([[rs.choice(pool[k]) for k in range(5)] for _ in range(N)])
out = {'nCenters': int(len(pool[4])), 'draws': N, 'arms': {}}
for arm in ['R2-abil', 'R2-stats', 'R2-stats-rapm', 'E225-T-nomin']:
    F = torch.from_numpy(np.array(pr['feats'][arm], np.float32))
    nets = []
    for sd in range(5):
        fn = os.path.join(HERE, '..', 'E225-lineup-transformer', 'results', 'weights', f'T-nomin-{sd}.pt') if arm == 'E225-T-nomin' else os.path.join(HERE, 'results', 'weights', f'{arm}-{sd}.pt')
        m = LineupNet(pr['nfeat'][arm]); m.load_state_dict(torch.load(fn, map_location='cpu')); m.eval(); nets.append(m)

    def net(ia, pa, ib, pb):
        T = [torch.cat([F[ia], F[ib]], 1), torch.cat([torch.tensor(pa), torch.tensor(pb)], 1), SIDE.expand(len(ia), -1)]
        P = np.stack([predict(m, T, 'cpu', bs=4096).numpy() for m in nets])
        return 100 * (P[:, :, 0, 0] - P[:, :, 1, 0]).mean(0)
    pc = [[4] * 5] * N; pb = [list(range(5))] * N
    a = net(cen, pc, bal, pb); b = -net(bal, pb, cen, pc)
    c = net(bal2, pb, bal, pb); d = -net(bal, pb, bal2, pb)
    v = 0.5 * (a + b); ctrl = 0.5 * (c + d)
    out['arms'][arm] = {'centersMinusBalanced': round(float(v.mean()), 3), 'sd': round(float(v.std()), 3), 'shareCentersWin': round(float((v > 0).mean()), 3),
                        'control_balancedVsBalanced': round(float(ctrl.mean()), 3)}
    print(arm, out['arms'][arm], flush=True)
json.dump(out, open(os.path.join(HERE, 'results', 'centers.json'), 'w'), ensure_ascii=False, indent=1)
