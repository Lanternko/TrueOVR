"""E-202 phase0：只用 K0，寫 phase0.json／phase0.md（跑 KT 前）。"""
import json, sys
import numpy as np
from scipy.stats import rankdata
from e202_common import *

def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])

def main():
    c = load_arm('K0')
    bh = twok_bh()
    ids2k = [p for p, r in c.items() if float(r['MIN']) >= 500 and norm(r['name']) in bh]
    tov = np.array([float(c[p]['tovSkill']) for p in ids2k]); y = np.array([bh[norm(c[p]['name'])] for p in ids2k])
    rng = np.random.default_rng(SEED); n = len(ids2k)
    bs = []
    for _ in range(B):
        i = rng.integers(0, n, n); bs.append(rho(tov[i], y[i]))
    rho_bh = rho(tov, y); mde = hw(bs)
    rapm = {k: json.load(open(f, encoding='utf-8'))['players'] for k, f in RAPM_FILES.items()}
    full = rapm['full']
    ids = sorted(p for p, r in c.items() if float(r['MIN']) >= 500 and str(p) in full and full[str(p)]['poss'] >= 1000)
    ovr = np.array([float(c[p]['ovr']) for p in ids]); rv = np.array([full[str(p)]['net'] for p in ids])
    rho_r = rho(ovr, rv); rng = np.random.default_rng(SEED); m = len(ids)
    bs2 = []
    for _ in range(B):
        i = rng.integers(0, m, m); bs2.append(rho(ovr[i], rv[i]))
    h = hw(bs2)
    f = f143(c)
    res = {'n_2k_pool': n, 'K0_tov_vs_2K_BallHandle_rho': rho_bh, 'MDE': mde, 'ci90': ci(bs),
           'n_rapm_pop': m, 'K0_ovr_vs_rapm_rho': rho_r, 'h': h, 'notBroken_threshold': -2 * h,
           'F143': f, 'seed': SEED, 'draws': B, 'K0_ranking_sha256': sha(rank_path('K0')),
           'pop_def': '2K 池＝卡片 MIN≥500 且 2K27 有 Ball Handle（姓名正規化比對）；RAPM 人群＝MIN≥500 且本季 RAPM poss≥1000（同 E-198）；F-143＝MIN≥500，持球/36＝handle.csv TIME_OF_POSS÷卡片 MIN×36，中位數取同人群'}
    (HERE / 'phase0.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    md = f"""# E-202 phase0（跑 KT 前；只用 K0）

- K0 ranking.csv sha256 `{res['K0_ranking_sha256']}`（＝card-0.2.10j）。bootstrap 球員層 {B} 次，seed {SEED}。
- tovSkill 對 2K27 Ball Handle Spearman（n={n}）= {rho_bh:.4f}，90% 半寬 **MDE = {mde:.4f}** → A：KT − K0 ≥ {mde:.4f}。
- 全體 OVR 對 2025-26 RAPM Spearman（n={m}）= {rho_r:.4f}，90% 半寬 **h = {h:.4f}** → 沒弄壞：KT − K0 ≥ **{-2*h:.4f}**。
- F-143 現值：TO 前 30 中持球/36 低於池中位數（{f['median']:.3f}）的有 **{f['n_below']}**/30（無資料 {f['n_nodata']}；前 30 平均持球 {f['top30_mean_poss36']:.2f}）；榜首 {'、'.join(f['top5'])}。
- 人群定義：{res['pop_def']}
"""
    (HERE / 'phase0.md').write_text(md, encoding='utf-8'); print(md)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main()
