"""E-228 共用：載入權重、賽前特徵、位置規則、抽樣、淨值。不讀任何比賽結果。"""
import csv, gzip, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
E227 = os.environ.get('E227_SRC', os.path.join(ROOT, 'reports', 'E227-lineup-transformer-r2'))
E223 = os.path.join(ROOT, 'reports', 'E223-team-rating', 'work')
sys.path.insert(0, E227)
import numpy as np, torch
from e227_common import load_player_table
from e227_model import LineupNet, base_feats, n_feat, predict

KIND = 'stats'; F = n_feat(KIND)
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)


class Ctx:
    def __init__(self, weights, prior, dev='cpu'):
        W = {'T2425': os.path.join(HERE, 'results', 'weights', 'T2425-{}.pt'),
             'E227-R2-stats': os.path.join(E227, 'results', 'weights', 'R2-stats-{}.pt')}[weights]
        self.dev = dev; self.nets = []
        for sd in range(5):
            n = LineupNet(F); n.load_state_dict(torch.load(W.format(sd), map_location='cpu')); n.eval(); self.nets.append(n.to(dev))
        self.tab = load_player_table(prior); self.B = base_feats(prior, KIND)
        self.med_h = float(np.median([d['heightInches'] for d in self.tab.values() if d.get('heightInches') is not None]))
        poss = 0.0; gids = set()      # 聯盟每隊每場回合數：prior 季 split=train 的 stint（賽前資訊）
        with gzip.open(os.path.join(E227, 'data', f'stints-train-{prior}.csv.gz'), 'rt', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r['possa'] != '' and r['possb'] != '':
                    poss += float(r['possa']) + float(r['possb']); gids.add(r['gid'])
        self.avg_poss = poss / 2 / len(gids)

    def vec(self, p):
        v = self.B.get(str(p))      # 賽前表沒有的人：全 0、遮罩 0
        return np.zeros(2 * F, np.float32) if v is None else np.concatenate([v[0], v[1]]).astype(np.float32)

    def hkey(self, p):      # E-225 infer_positions：身高升冪，平手 pass+creation 高者在前，再用 pid；缺身高用中位數
        d = self.tab.get(str(p)) or {}
        h = d.get('heightInches'); h = self.med_h if h is None else h
        return (h, -((d.get('pass') or 0.0) + (d.get('creation') or 0.0)), str(p))

    def prep(self, rot):
        pids = [p for p, m in rot]; mins = np.array([m for p, m in rot], float)
        order = sorted(range(len(pids)), key=lambda j: self.hkey(pids[j])); rank = np.empty(len(pids), int); rank[order] = np.arange(len(pids))
        return np.stack([self.vec(p) for p in pids]), np.log(mins), rank

    @staticmethod
    def draw(R, lm, rank, rng, N):
        g = lm[None, :] + rng.gumbel(size=(N, len(lm)))          # Gumbel top-k＝依分鐘比例無放回
        top = np.argsort(-g, axis=1)[:, :5]
        top = np.take_along_axis(top, np.argsort(rank[top], axis=1), axis=1)   # 依身高規則排成位置 0..4
        return R[top]

    def net100(self, H5, A5):
        """H5、A5：[N,5,2F]（位置已排）。回傳 [5 seed, N]：H 隊視角每 100 回合淨值（H 當 A 與 H 當 B 各算一次取平均）。"""
        N = len(H5)
        X = torch.from_numpy(np.concatenate([np.concatenate([H5, A5], 1), np.concatenate([A5, H5], 1)], 0))
        T = [X, POS.expand(2 * N, -1), SIDE.expand(2 * N, -1)]; out = np.zeros((len(self.nets), N))
        for s, m in enumerate(self.nets):
            o = predict(m, T, self.dev, bs=8192)[:, :, 0].numpy(); d = 100.0 * (o[:, 0] - o[:, 1])
            out[s] = 0.5 * (d[:N] - d[N:])
        return out
