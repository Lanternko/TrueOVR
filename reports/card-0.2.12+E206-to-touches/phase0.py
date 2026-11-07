"""E-206 phase0：只用 K12（c0 重現的 0.2.12），寫 phase0.json／phase0.md（跑 KC 前）。"""
import csv, json, sys
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from e202_common import *

def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])

def main():
    c = load_arm('K12')
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
    m5 = [p for p in sorted(c) if float(c[p]['MIN']) >= 500]
    sj = json.loads((HERE / 'work/K12/A/base-KG-2025-26/c0/cards/K0/primary/summary.json').read_text(encoding='utf-8'))['valuePer10AttributePoints']
    attrs = [k for k in sj if k != 'gravity' and k in next(iter(c.values()))]
    gr = {int(r['playerId']): float(r['gravity']) for r in csv.DictReader(open(HERE / 'gravity-attr.csv', encoding='utf-8'))}
    names = attrs + ['gravity']
    X = np.array([[float(c[p][k]) for k in attrs] + [gr[p]] for p in m5]); j = names.index('tovSkill'); yv = X[:, j]
    Xc = np.column_stack([np.ones(len(m5)), np.delete(X, j, 1)]); bb, *_ = np.linalg.lstsq(Xc, yv, rcond=None)
    r2 = 1 - ((yv - Xc @ bb) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
    vif = {'vif': float(1 / (1 - r2)), 'attrs_used': attrs, 'corr': {k: float(np.corrcoef(yv, X[:, names.index(k)])[0, 1]) for k in ('creation', 'pass', 'gravity')}}
    # A：持球者子群 tovSkill vs AVG_SEC_PER_TOUCH（handle 原始檔 2025-26）
    d = json.loads((ROOT / 'reports/handle-E069/raw/2025-26/Possessions-FULL.json').read_text(encoding='utf-8'))['data']['resultSets']
    rs = d[0] if isinstance(d, list) else d
    ip, ia = rs['headers'].index('PLAYER_ID'), rs['headers'].index('AVG_SEC_PER_TOUCH')
    ast = {r[ip]: r[ia] for r in rs['rowSet']}
    p36 = poss36(c)
    subA = sorted(p for p, r in c.items() if float(r['MIN']) >= 1000 and p in p36 and p36[p] >= 5 and p in ast)
    ta = np.array([float(c[p]['tovSkill']) for p in subA]); sa = np.array([ast[p] for p in subA])
    rho_A = rho(ta, sa); rng = np.random.default_rng(SEED); na = len(subA); bsA = []
    for _ in range(B):
        i = rng.integers(0, na, na); bsA.append(rho(ta[i], sa[i]))
    mdeA = hw(bsA)
    info = json.loads((HERE / 'tov-raw-info-K12.json').read_text(encoding='utf-8'))
    res = {'n_2k_pool': n, 'K12_tov_vs_2K_BallHandle_rho': rho_bh, 'MDE': mde, 'ci90': ci(bs),
           'n_rapm_pop': m, 'K12_ovr_vs_rapm_rho': rho_r, 'h': h, 'notBroken_threshold': -2 * h,
           'F143': f, 'seed': SEED, 'draws': B, 'A_subgroup': {'n': na, 'K12_rho_tov_vs_avgsec': rho_A, 'MDE_A': mdeA, 'ci90': ci(bsA), 'threshold_K12_minus_KC_ge': mdeA}, 'conversion_rho_touch_per_possmin': {'card_pool_582': info['rho_touch_per_possmin'], 'z_pool_252': info['rho_touch_per_possmin_pool252'], 'k_t': 64 * info['rho_touch_per_possmin'], 'kh_t': 256 * info['rho_touch_per_possmin']}, 'KC_thresholds': {'A_rho_drop_ge': mdeA, 'keepE202_BH_rho_ge': 0.0798 + 0.0879, 'notBroken_rho_diff_ge': -2 * h, 'B_le': 10}, 'K12_ranking_sha256': sha(rank_path('K12')), 'K12_vif': vif, 'E202_K0_BH_rho_0211': 0.0798,
           'pop_def': '2K 池＝卡片 MIN≥500 且 2K27 有 Ball Handle（姓名正規化比對）；RAPM 人群＝MIN≥500 且本季 RAPM poss≥1000（同 E-198）；F-143＝MIN≥500，持球/36＝handle.csv TIME_OF_POSS÷卡片 MIN×36，中位數取同人群'}
    (HERE / 'phase0.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    md = f"""# E-206 phase0（跑 KC 前；只用 K12）

- K12 ranking.csv sha256 `{res['K12_ranking_sha256']}`（c0 重現＝card 0.2.12）。bootstrap 球員層 {B} 次，seed {SEED}。
- tovSkill 對 2K27 Ball Handle Spearman（n={n}）= {rho_bh:.4f}（0.2.11 為 0.0798，E-202 MDE 0.0879）→ 保住 E-202 門檻：KC ≥ {0.0798+0.0879:.4f}。（K12 自身 90% 半寬 {mde:.4f}）
- 全體 OVR 對 2025-26 RAPM Spearman（n={m}）= {rho_r:.4f}，90% 半寬 **h = {h:.4f}** → 沒弄壞：KC − K12 ≥ **{-2*h:.4f}**。
- tovSkill 對其他能力值 VIF = **{vif['vif']:.2f}**（只報告）；與 creation 相關 {vif['corr']['creation']:+.2f}、pass {vif['corr']['pass']:+.2f}、gravity {vif['corr']['gravity']:+.2f}。
- F-143 現值：TO 前 30 中持球/36 低於池中位數（{f['median']:.3f}）的有 **{f['n_below']}**/30（無資料 {f['n_nodata']}；前 30 平均持球 {f['top30_mean_poss36']:.2f}）；榜首 {'、'.join(f['top5'])}。
- **A 基準**：持球者子群（MIN≥1000 且持球/36≥5，n={na}）tovSkill 對 AVG_SEC_PER_TOUCH Spearman（K12）= **{rho_A:.4f}**，bootstrap 90% 半寬 **MDE_A = {mdeA:.4f}** → A 過門檻：K12 − KC ≥ {mdeA:.4f}（即 KC ≤ {rho_A-mdeA:.4f}）。
- 換算係數 ρ（觸球／持球分鐘）：卡片池 2025-26 = {info['rho_touch_per_possmin']:.4f}（z 池 252 人 {info['rho_touch_per_possmin_pool252']:.4f}）；k_t = {64*info['rho_touch_per_possmin']:.2f}、kh_t = {256*info['rho_touch_per_possmin']:.2f}。
- 人群定義：{res['pop_def']}
"""
    (HERE / 'phase0.md').write_text(md, encoding='utf-8'); print(md)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main()
