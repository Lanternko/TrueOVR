"""E-228 T 球隊淨值預測（只吃陣容、賽前特徵、權重；不讀任何比賽結果）。
  python -I -X utf8 predict_t.py --key 2425 --weights T2425 --prior 2023-24 --out work/pred-T-2425.json    # 乾跑（樣本內，只查管線）
  python -I -X utf8 predict_t.py --key 2526 --weights T2425 --prior 2024-25 --out work/pred-T-2526.json    # 凍結前預測檔：產生後不打開、不與結果比
  python -I -X utf8 predict_t.py --key 2526 --weights E227-R2-stats --prior 2025-26 ...                    # 前向 T-full（E-227 權重）
做法（預註冊草案第 4 節）：每場每隊依分鐘比例無放回抽 5 人（Gumbel top-k＝Plackett-Luce），位置依 E-225 身高規則；
主客兩隊同批抽樣餵 Transformer，主隊當 A 與當 B 各算一次取平均（side embedding 的方向偏差），net100＝100·(A 進攻 pts/poss − B 進攻 pts/poss)；
N 組抽樣平均 → ×(聯盟每隊每場回合數/100) → 邊際；5 個模型 seed 各自輸出，另存 5 seed 平均。無擬合參數。
缺值：賽前表（prior 季）沒有的球員＝特徵全 0、遮罩 0（與 E-227 缺值處理同）；身高缺值用 prior 季身高中位數。"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t_lib import *

ap = argparse.ArgumentParser()
ap.add_argument('--key', required=True, choices=['2425', '2526']); ap.add_argument('--weights', required=True); ap.add_argument('--prior', required=True)
ap.add_argument('--out', required=True); ap.add_argument('--draws', type=int, default=2000); ap.add_argument('--rng', type=int, default=228)
ap.add_argument('--limit', type=int, default=0); ap.add_argument('--threads', type=int, default=6); ap.add_argument('--dev', default='cpu')
a = ap.parse_args(); torch.set_num_threads(a.threads)
INP = {'2425': 'inputs-2425.json', '2526': 'inputs.json'}
C = Ctx(a.weights, a.prior, a.dev)
lin = json.load(open(os.path.join(E223, f'lineups-{a.key}.json'), encoding='utf-8'))
inp = json.load(open(os.path.join(ROOT, 'reports', 'E208-team-rating', INP[a.key]), encoding='utf-8'))
G = [(g['i'], g['home'], g['away']) for g in inp['games']]    # 只取場次序號與主客；不碰比分
del inp
if a.limit: G = G[:a.limit]
n = len(G); N = a.draws; net100 = np.zeros((5, n)); drawsd = np.zeros((5, n)); t0 = time.time()
for k, (i, h, aw) in enumerate(G):
    Rh, lh, rh = C.prep(lin[f'{i}h']); Ra, la, ra = C.prep(lin[f'{i}a'])
    rng = np.random.default_rng([a.rng, i])
    x = C.net100(C.draw(Rh, lh, rh, rng, N), C.draw(Ra, la, ra, rng, N))
    net100[:, k] = x.mean(1); drawsd[:, k] = x.std(1, ddof=1)
    if k % 100 == 0: print(k, n, round(time.time() - t0), 's', flush=True)
out = dict(key=a.key, weights=a.weights, prior=a.prior, draws=N, rng=a.rng, avg_poss=C.avg_poss, med_height=C.med_h, games=[g[0] for g in G],
           home=[str(g[1]) for g in G], away=[str(g[2]) for g in G], margin_seed=(net100 * C.avg_poss / 100).tolist(), draw_sd_net100=drawsd.tolist())
json.dump(out, open(a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out), 'w'))
print('done', n, 'games', round(time.time() - t0), 's avg_poss', round(C.avg_poss, 2))
