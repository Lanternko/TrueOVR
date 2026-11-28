"""E-228 評估：T 預測 vs 比賽結果。2025-26 在預註冊凍結（存在 FREEZE.txt）之前拒絕執行。
  python -I -X utf8 eval_t.py --key 2425 --pred work/pred-T-2425.json --out dryrun-2425.json   # 乾跑：樣本內，只查管線
方法同 E-223 eval_oos／fit_train：p＝Φ((邊際±H)/σ)（H=2.5、σ=12），Brier 逐場、勝場 MAE 逐隊；成對場次 bootstrap 2000 次、rng 20261102、90% 區間。"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
E223 = os.path.join(os.path.dirname(HERE), 'E223-team-rating'); sys.path.insert(0, E223)
import numpy as np
from scipy.stats import spearmanr
from e223_lib import *      # H, SIGMA, CARDS, SEASONS, load_card, wins_mae
from fit_train import features, brier

ap = argparse.ArgumentParser(); ap.add_argument('--key', required=True); ap.add_argument('--pred', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
if a.key == '2526' and not os.path.exists(os.path.join(HERE, 'FREEZE.txt')):
    sys.exit('拒絕：2025-26 的 T 預測不得在預註冊凍結前與結果比對（缺 FREEZE.txt）')
P = json.load(open(os.path.join(HERE, a.pred) if not os.path.isabs(a.pred) else a.pred))
zmap, zmiss, info = load_card(CARDS / SEASONS[a.key]['card'])
F = features(a.key, zmap, zmiss)
y, ids, home, away = F['y'], F['ids'], F['home'], F['away']; n = len(y)
assert P['games'] == list(range(n)) and P['home'] == list(home) and P['away'] == list(away), '場次順序不一致'
MS = np.array(P['margin_seed']); mT = MS.mean(0)
pred = {'B0': F['b0'] + H, 'M0': F['m0'] + H, 'T': mT + H, 'MIX': 0.5 * mT + 0.5 * F['m0'] + H}
for s in range(MS.shape[0]):
    pred[f'T_seed{s}'] = MS[s] + H
pg = {k: brier(v, y) for k, v in pred.items()}
out = dict(key=a.key, n=n, weights=P['weights'], prior=P['prior'], draws=P['draws'], avg_poss=P['avg_poss'],
           brier={k: float(v[0].mean()) for k, v in pg.items()}, win_mae={k: wins_mae(v[1], y, home, away, ids) for k, v in pg.items()})
rng = np.random.default_rng(20261102); boots = [rng.integers(0, n, n) for _ in range(2000)]
def pair(x, z, metric):
    if metric == 'brier':
        v = np.array([pg[x][0][ix].mean() - pg[z][0][ix].mean() for ix in boots])
    else:
        v = np.array([wins_mae(pg[x][1], y, home, away, ids, ix) - wins_mae(pg[z][1], y, home, away, ids, ix) for ix in boots])
    return dict(diff=float(v.mean()), lo=float(np.percentile(v, 5)), hi=float(np.percentile(v, 95)))
out['pairs'] = {f'{x}-{z}': {m: pair(x, z, m) for m in ('brier', 'win')} for x, z in (('T', 'M0'), ('T', 'B0'), ('MIX', 'M0'))}
out['point'] = {'brier T-M0': out['brier']['T'] - out['brier']['M0'], 'winMAE T-M0': out['win_mae']['T'] - out['win_mae']['M0']}
MDE_B, MDE_W = 0.0100, 1.25
out['judgment'] = {'J1 不更差 (Brier(T)-Brier(M0) 90%上界 < 0.0100)': bool(out['pairs']['T-M0']['brier']['hi'] < MDE_B),
                   'J2 不壞 (wins-MAE(T)-MAE(M0) 點估計 <= 1.25)': bool(out['point']['winMAE T-M0'] <= MDE_W)}
# 紀錄項：30 隊排名 Spearman（預測勝場 vs 實際勝場；T vs M0 預測的相關）
def wins(p):
    w = {t: 0.0 for t in ids}
    for i in range(n): w[home[i]] += p[i]; w[away[i]] += 1 - p[i]
    return np.array([w[t] for t in ids])
aw = {t: 0.0 for t in ids}
for i in range(n): aw[home[i]] += y[i]; aw[away[i]] += 1 - y[i]
act = np.array([aw[t] for t in ids])
out['spearman_vs_actual_wins'] = {k: float(spearmanr(wins(pg[k][1]), act)[0]) for k in ('B0', 'M0', 'T', 'MIX')}
out['spearman_T_vs_M0_predwins'] = float(spearmanr(wins(pg['T'][1]), wins(pg['M0'][1]))[0])
# 管線合理性
out['scale'] = dict(margin_T_mean=float(mT.mean()), margin_T_sd=float(mT.std()), margin_M0_mean=float(F['m0'].mean()), margin_M0_sd=float(F['m0'].std()),
                    corr_T_M0=float(np.corrcoef(mT, F['m0'])[0, 1]), corr_T_B0=float(np.corrcoef(mT, F['b0'])[0, 1]),
                    actual_margin_sd=float(F['d'].std()), actual_home_margin_mean=float(F['d'].mean()))
# 單 seed 抽樣雜訊：各 seed 與 5 seed 平均的邊際差、Brier 差
sd_seed = MS.std(0, ddof=1)
out['noise'] = dict(per_game_margin_sd_across_seeds_mean=float(sd_seed.mean()), per_game_margin_sd_across_seeds_median=float(np.median(sd_seed)),
                    single_seed_brier=[out['brier'][f'T_seed{s}'] for s in range(MS.shape[0])], mean5_brier=out['brier']['T'],
                    single_seed_winmae=[out['win_mae'][f'T_seed{s}'] for s in range(MS.shape[0])], mean5_winmae=out['win_mae']['T'],
                    draw_se_net100_mean=float(np.mean(np.array(P['draw_sd_net100'])) / np.sqrt(P['draws'])))
json.dump(out, open(os.path.join(HERE, a.out), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
