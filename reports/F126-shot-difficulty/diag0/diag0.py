"""F-126 第 0 步診斷：出手能力 SM ＝ (FGM − Σ逐球xFG)/(FGA+k) 能不能解釋卡片 OVR 對半季 RAPM 的殘差。
跑一次，不看結果挑參數。判讀規則在 verdict()，寫死、不隨結果改。
用法（repo 根目錄）：python reports/F126-shot-difficulty/diag0/diag0.py   → result.json、inputs.sha256"""
import csv, hashlib, json, os, sys
import numpy as np
from scipy.stats import spearmanr
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.abspath(os.path.join(here, '../../..'))
P = lambda p: os.path.join(root, p)
L = lambda p: list(csv.DictReader(open(p, encoding='utf-8')))
SEED, NBOOT, MINFGA = 20261101, 2000, 100
CARD = P('reports/card-0.2.10/ranking.csv')
RA, RB = P('reports/card-0.2.3+E081-age-residual/rapm1-A.csv'), P('reports/card-0.2.3+E081-age-residual/rapm1-B.csv')
PG, POOL, GRAV = os.path.join(here, 'player_game.csv'), os.path.join(here, 'pool.csv'), os.path.join(here, 'gravity.json')

# ---- 讀入 ----
card = {x['name']: x for x in L(CARD) if float(x['MIN']) >= 900}
pid = {x['name']: x['playerId'] for x in L(POOL)}
rap = {h: {x['playerId']: float(x['net']) for x in L(f)} for h, f in (('A', RA), ('B', RB))}
agg = {}                                     # (pid, half) → [FGA, FGM, sumXFG]
for x in L(PG):
    a = agg.setdefault((x['playerId'], x['half']), [0, 0, 0.0])
    a[0] += int(x['FGA']); a[1] += int(x['FGM']); a[2] += float(x['sumXFG'])
grav = {str(g['playerId']): g['avgGravity'] for g in json.load(open(GRAV, encoding='utf-8'))}

names = [n for n in card if pid.get(n) and all((pid[n], h) in agg for h in 'AB')]
cov = len(names) / len(card)                 # 驗收：player_game.csv 涵蓋池內球員比例
names = [n for n in names if all(pid[n] in rap[h] for h in 'AB')]
ids = [pid[n] for n in names]
ovr = np.array([float(card[n]['ovr']) for n in names])
G = {h: np.array([agg[(i, h)] for i in ids], float) for h in 'AB'}     # 欄：FGA, FGM, sumXFG
net = {h: np.array([rap[h][i] for i in ids]) for h in 'AB'}
N = len(names)

# ---- 1. 信度與收縮常數 ----
def wcorr(x, y, w):
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return np.average((x - mx) * (y - my), weights=w) / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))
raw = lambda g: (g[:, 1] - g[:, 2]) / np.maximum(g[:, 0], 1)
ok = (G['A'][:, 0] >= MINFGA) & (G['B'][:, 0] >= MINFGA)
w = 2 * G['A'][ok, 0] * G['B'][ok, 0] / (G['A'][ok, 0] + G['B'][ok, 0])   # 權重＝兩半 FGA 的調和平均
r = float(wcorr(raw(G['A'])[ok], raw(G['B'])[ok], w))
fga_half = float(np.mean(np.r_[G['A'][ok, 0], G['B'][ok, 0]]))
no_signal = r <= 0
k = None if no_signal else fga_half * (1 - r) / r
def sm_shrunk(g):
    return np.zeros(len(g)) if no_signal else (g[:, 1] - g[:, 2]) / (g[:, 0] + k)
SM = {h: sm_shrunk(G[h]) for h in 'AB'}

# ---- 2/3. 殘差與主統計量 ----
def resid(y, x):
    X = np.c_[np.ones_like(x), x]; return y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
def dir_slope(sm, res, extra=None):
    """每 1 SD SM 對應的殘差（RAPM/100 回合）；extra＝共變數（同樣標準化）"""
    z = (sm - sm.mean()) / sm.std()
    X = np.c_[np.ones_like(z), z] if extra is None else np.c_[np.ones_like(z), z, (extra - extra.mean()) / extra.std()]
    return float(np.linalg.lstsq(X, res, rcond=None)[0][1])
def main_stat(idx, extra=None):
    """方向 AB：SM 用 A 半 × 殘差用 B 半；BA 反之。各方向殘差回歸在 idx 內重做。回傳 (AB, BA, 平均)"""
    out = []
    for s, t in (('A', 'B'), ('B', 'A')):
        res = resid(net[t][idx], ovr[idx])
        out.append(dir_slope(SM[s][idx], res, None if extra is None else extra[idx]))
    return out[0], out[1], (out[0] + out[1]) / 2
allx = np.arange(N)
res_out = {'N_pool_card': len(card), 'N_with_data': N, 'coverage_pool': cov, 'reliability_r': r, 'FGA_half_mean': fga_half,
           'n_reliability': int(ok.sum()), 'k': k, 'no_signal': bool(no_signal)}
if no_signal:
    res_out['verdict'] = 'SM 沒有可量的訊號（r≤0）'
else:
    ab, ba, mean = main_stat(allx)
    rng = np.random.default_rng(SEED); boots = []
    for _ in range(NBOOT):
        boots.append(main_stat(rng.integers(0, N, N)))      # 兩方向同一組抽樣
    boots = np.array(boots); se = boots[:, 2].std(ddof=1)
    lo, hi = np.percentile(boots[:, 2], [5, 95])
    mde = 2.49 * se
    # SM 第 90 百分位的人（相對全體平均，用兩半合併的全季 SM；k 對全季同值，見報告）
    full = np.c_[G['A'][:, 0] + G['B'][:, 0], G['A'][:, 1] + G['B'][:, 1], G['A'][:, 2] + G['B'][:, 2]]
    SMf = sm_shrunk(full); z90 = float((np.percentile(SMf, 90) - SMf.mean()) / SMf.std())
    res_out.update({'slope_AB': ab, 'slope_BA': ba, 'slope_mean': mean, 'boot_se': float(se), 'lo90': float(lo), 'hi90': float(hi),
                    'MDE': float(mde), 'z_p90': z90, 'p90_card_underpays_per100': mean * z90,
                    'sd_SM_full': float(SMf.std()), 'boot_n': NBOOT})

    def verdict(lo, hi, mde):          # 預先定好，照抄進報告
        if lo > 0: return '低估成立'
        if hi < 0: return '卡片高估難球命中者'
        return f'未偵測到（MDE＝{mde:.3f} RAPM/100 回合／SD）'
    res_out['verdict'] = verdict(lo, hi, mde)

    # ---- 6. 只報告 ----
    sf = SMf
    rk = lambda v: (-v).argsort().argsort() + 1
    card_rank = rk(ovr)
    rep = {'spearman_SM_vs_ovr': float(spearmanr(sf, ovr)[0])}
    for c in ('long', 'mid', 'short'):
        rep[f'spearman_SM_vs_{c}'] = float(spearmanr(sf, [float(card[n][c]) for n in names])[0])
    sm_rank = rk(sf)
    rep['top15'] = [{'name': names[i], 'SM_shrunk': float(sf[i]), 'FGA': int(full[i, 0]),
                     'raw_pp': float(100 * (full[i, 1] - full[i, 2]) / full[i, 0]),
                     'card_rank': int(card[names[i]]['rank'])} for i in np.argsort(-sf)[:15]]
    if 'Shai Gilgeous-Alexander' in names:
        s = names.index('Shai Gilgeous-Alexander')
        rep['SGA'] = {'SM_shrunk': float(sf[s]), 'SM_rank': int(sm_rank[s]), 'of': N, 'FGA': int(full[s, 0]),
                      'raw_pp': float(100 * (full[s, 1] - full[s, 2]) / full[s, 0]), 'card_rank': int(card[names[s]]['rank'])}
    # Gravity 共變數：限有 Gravity 的人（GP≥55），同一子樣本比較加／不加共變數
    gi = np.array([i for i in allx if ids[i] in grav]); gv = np.array([grav[ids[i]] for i in gi])
    gx = np.full(N, np.nan); gx[gi] = gv
    wo, wi = main_stat(gi), main_stat(gi, gx)
    rep['gravity'] = {'n': int(len(gi)), 'slope_without': wo[2], 'slope_with': wi[2], 'by_dir_without': wo[:2], 'by_dir_with': wi[:2],
                      'spearman_SM_vs_gravity': float(spearmanr(sf[gi], gv)[0])}
    res_out['report_only'] = rep

res_out['seed'] = SEED
json.dump(res_out, open(os.path.join(here, 'result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k_: v for k_, v in res_out.items() if k_ != 'report_only'}, ensure_ascii=False, indent=1))

# ---- inputs.sha256 ----
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
with open(os.path.join(here, 'inputs.sha256'), 'w', encoding='utf-8') as fh:
    for p in (CARD, RA, RB, PG, POOL, GRAV, P('data/season-source/player-games.json'),
              P('reports/ovr-inseason-2026-27/live/2026-10-31/ranking.csv')):
        fh.write(f'{sha(p)}  {os.path.relpath(p, root).replace(os.sep, "/")}\n')
