"""E-224 評估（預註冊 §4–§5）。沒有任何擬合參數：OLD、A5、B5 都是未擬合的 M0 型態（H、σ 為 E-208 凍結值）。
用法：python -I -X utf8 eval_e224.py <2425|2526>      輸出 work/eval-e224-<season>.json 並印出摘要。
OLD＝E-223 的 M0 模擬檔 reports/E223-team-rating/work/sims-<season>；A5／B5＝work/out-<a5|b5>-<season>/o-*.json。
預測主減客＝(Net_主 − Net_客) + H（各臂對自己的平均置中不影響差值），p＝Φ(·/12)。"""
import glob, json, os, sys
HERE0 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE0, '..', 'E223-team-rating'))
import numpy as np
from scipy.stats import spearmanr
from e223_lib import load_season, H, SIGMA, wins_mae, HERE as E223
from fit_train import brier

key = sys.argv[1]
W = os.path.join(HERE0, 'work')
MDE_B, MDE_W = 0.0100, 1.25            # 預註冊 §5 凍結
S = load_season(key); G = S['games']; n = len(G)
home = np.array([g['home'] for g in G]); away = np.array([g['away'] for g in G])
y = np.array([float(g['hs'] > g['as']) for g in G]); ids = sorted(S['inp']['teams'])
abbr = {t: S['inp']['teams'][t]['abbr'] for t in ids}

# ---- 載入各臂：key＝2*i+(side=='a')；統一成 per[key] = list of (n, msum)（OLD 一個對手、新臂五個對手）----
def load_old():
    d = {}
    for f in glob.glob(os.path.join(E223, 'work', f'sims-{key}', 'o-*.json')):
        for r in json.load(open(f))['res']:
            d[r['key']] = [(r['n'], r['msum'])]
    return d
def load_new(tag):
    d = {}
    fs = glob.glob(os.path.join(W, f'out-{tag}-{key}', 'o-*.json')); assert fs, tag
    for f in fs:
        for r in json.load(open(f))['res']:
            d[r['key']] = [(o['n'], o['msum']) for o in r['opp']]
    return d
ARMS = {'OLD': load_old(), 'A5': load_new('a5'), 'B5': load_new('b5')}
for a, d in ARMS.items():
    assert len(d) == 2 * n, (a, len(d), 2 * n)
mean_m = lambda a, k: sum(m for _, m in ARMS[a][k]) / sum(c for c, _ in ARMS[a][k])   # 該陣容對該臂所有對手的平均分差

dh = {a: np.array([mean_m(a, 2 * g['i']) - mean_m(a, 2 * g['i'] + 1) for g in G]) + H for a in ARMS}
pg = {a: brier(dh[a], y) for a in ARMS}
out = dict(season=key, n=n, MDE_B=MDE_B, MDE_W=MDE_W,
           brier={a: float(pg[a][0].mean()) for a in ARMS}, win_mae={a: wins_mae(pg[a][1], y, home, away, ids) for a in ARMS})

# ---- 成對 bootstrap（以場重抽 2000 次、rng 20261103、90% 區間）----
rng = np.random.default_rng(20261103); boots = [rng.integers(0, n, n) for _ in range(2000)]
def pair(x, z, metric):
    if metric == 'brier': v = np.array([pg[x][0][ix].mean() - pg[z][0][ix].mean() for ix in boots])
    else: v = np.array([wins_mae(pg[x][1], y, home, away, ids, ix) - wins_mae(pg[z][1], y, home, away, ids, ix) for ix in boots])
    return dict(diff=float(v.mean()), lo=float(np.percentile(v, 5)), hi=float(np.percentile(v, 95)))
PAIRS = (('B5', 'OLD'), ('A5', 'OLD'), ('B5', 'A5'))
out['pairs'] = {f'{x}-{z}': {m: pair(x, z, m) for m in ('brier', 'win')} for x, z in PAIRS}

# ---- 判定 ----
d_b = out['brier']['B5'] - out['brier']['OLD']; d_w = out['win_mae']['B5'] - out['win_mae']['OLD']
out['H2'] = dict(brier_regress=d_b, win_regress=d_w, ok=bool(d_b <= MDE_B and d_w <= MDE_W))
out['Q2_improved_this_season'] = bool(d_b <= -MDE_B)   # B5 Brier 比 OLD 低 ≥ MDE_B（兩季都成立才算有改善，由報告合併）

# ---- Q1 排名：各隊「全部名單的該臂平均分差」再平均成賽季平均 Net ----
def team_net(a):
    acc = {t: [] for t in ids}
    for g in G:
        acc[g['home']].append(mean_m(a, 2 * g['i'])); acc[g['away']].append(mean_m(a, 2 * g['i'] + 1))
    return {t: float(np.mean(v)) for t, v in acc.items()}
net = {a: team_net(a) for a in ARMS}
def ranks(d):   # 1＝最強
    order = sorted(ids, key=lambda t: -d[t]); return {t: i + 1 for i, t in enumerate(order)}
rk = {a: ranks(net[a]) for a in ARMS}
rho = lambda a, b: float(spearmanr([net[a][t] for t in ids], [net[b][t] for t in ids])[0])
out['Q1'] = dict(rho_B5_OLD=rho('B5', 'OLD'), rho_A5_OLD=rho('A5', 'OLD'), rho_B5_A5=rho('B5', 'A5'))
chg = sorted(ids, key=lambda t: -abs(rk['B5'][t] - rk['OLD'][t]))
out['Q1']['top3_rank_change_B5_vs_OLD'] = [dict(team=abbr[t], old=rk['OLD'][t], b5=rk['B5'][t]) for t in chg[:3]]

# ---- Q3 置中：各臂分差總平均（全部陣容）----
out['Q3_mean_margin'] = {a: float(np.mean([mean_m(a, k) for k in range(2 * n)])) for a in ARMS}
out['Q3_n_teams_positive'] = {a: int(sum(net[a][t] > 0 for t in ids)) for a in ARMS}

# ---- 探索性（不進判定）：各隊五個對手分差的標準差；對 T0（控衛主導）與 T4（中鋒主導）的分差 ----
def opp_means(a):
    acc = {t: np.zeros(5) for t in ids}; cnt = {t: 0 for t in ids}
    for g in G:
        for k, t in ((2 * g['i'], g['home']), (2 * g['i'] + 1, g['away'])):
            acc[t] += np.array([m / c for c, m in ARMS[a][k]]); cnt[t] += 1
    return {t: acc[t] / cnt[t] for t in ids}
om = {a: opp_means(a) for a in ('A5', 'B5')}
out['explore'] = dict(
    teams=sorted([dict(abbr=abbr[t], rank_old=rk['OLD'][t], rank_b5=rk['B5'][t], rank_a5=rk['A5'][t], net_old=net['OLD'][t], net_b5=net['B5'][t], net_a5=net['A5'][t],
                       opp_b5=[float(v) for v in om['B5'][t]], sd_opp_b5=float(om['B5'][t].std()), opp_a5=[float(v) for v in om['A5'][t]],
                       vs_pg_minus_vs_c_b5=float(om['B5'][t][0] - om['B5'][t][4])) for t in ids], key=lambda r: r['rank_b5']),
    note='opp_*＝對 T0…T4 的平均分差（T0 最強球員為 PG、T4 為 C）；探索性，不進判定')
json.dump(out, open(os.path.join(W, f'eval-e224-{key}.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != 'explore'}, indent=1, ensure_ascii=False))
