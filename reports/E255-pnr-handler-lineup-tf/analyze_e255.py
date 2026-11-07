"""E-255 本機分析與預註冊判定（擋拆持球 pnr 新增欄；由 analyze_e245 改寫）：
1. E-179（867 人次，留一季預測下季進攻 RAPM O）：
   M1 = 位置＋long＋九項進攻屬性（含 mid、creation）＋LineupNet 個人擋拆邊際進攻影響力 offpnr_val（ridge λ=10）。
   基準 T0（不放擋拆，offpnr_val≡0，等於只有基底）。
2. 對戰 stints：cross_test（前一季球員表預測當季 split=test，無洩漏）為閘門；split=test 只報告（Synergy 季總量含 test 場次）。
3. 每點換算（只報告）：基底＋擋拆分數 S（0–99，季內 z_pnr(w*) 的百分位×99），三季合併 ridge，係數 = O 每百回合／點；
   換勝場：Δ勝 ≈ 係數 × 點數 × (MPG/48) × 2.7（球隊淨效率 +1／百回合 ≈ +2.7 勝）。
4. 只報告：不經 Transformer 的直接 ridge（基底＋z_pnr(w)）各 w 的 R²。
用法：python -I -B -X utf8 reports/E255-pnr-handler-lineup-tf/analyze_e255.py
"""
import hashlib, json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
P_JSON = json.loads((HERE / 'e255_players.json').read_text(encoding='utf-8'))
E179_SEAS = ['2022-23', '2023-24', '2024-25']
WARMS = ['W00', 'W02', 'W04', 'W05', 'W06', 'W08', 'W10']
WV = {'W00': 0.0, 'W02': 0.2, 'W04': 0.4, 'W05': 0.5, 'W06': 0.6, 'W08': 0.8, 'W10': 1.0}
ALL_ARMS = ['T0'] + WARMS + ['WL']
SEED_P, SEED_G, B = 20261255, 20261107, 2000


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ridge_fit(X, y, lam=10.0):
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Z = np.c_[(X - mu) / sd, np.ones(len(X))]
    b = np.linalg.solve(Z.T @ Z + lam * np.diag([1] * X.shape[1] + [0]), Z.T @ y)
    return b, mu, sd


def ridge_cv_preds(feat_by_s, y_by_s, lam=10.0):
    preds = {}
    for te in E179_SEAS:
        tr = [s for s in E179_SEAS if s != te]
        b, mu, sd = ridge_fit(np.vstack([feat_by_s[s] for s in tr]), np.concatenate([y_by_s[s] for s in tr]), lam)
        preds[te] = np.c_[(feat_by_s[te] - mu) / sd, np.ones(len(feat_by_s[te]))] @ b
    return preds


def r2_pooled(y_by_s, p_by_s, idx=None):
    sse = sst = 0.0
    per = {}
    for t in E179_SEAS:
        yy, pp = y_by_s[t], p_by_s[t]
        i = np.arange(len(yy)) if idx is None else idx[t]
        e = float(((yy[i] - pp[i]) ** 2).sum()); v = float(((yy[i] - yy[i].mean()) ** 2).sum())
        sse += e; sst += v
        per[t] = round(1.0 - e / v, 5)
    return float(1.0 - sse / sst), per


def base_cols(s):
    d = P_JSON['e179'][s]
    pos_cols = [np.array([1.0 if p == q else 0.0 for p in d['pos']]) for q in P_JSON['e179_pos']]
    return pos_cols + [np.array(d['long'])] + [np.array(d['base'][a]) for a in P_JSON['e179_base_attr']]


def make_m1(arm_e179, seed=None):
    out = {}
    for s in E179_SEAS:
        arr = np.array(arm_e179[s]['offpnr_val'])
        v = arr.mean(0) if seed is None else arr[seed]
        out[s] = np.column_stack(base_cols(s) + [v])
    return out


def make_m2(arm_e179, seed=None):
    out = {}
    for s in E179_SEAS:
        d = P_JSON['e179'][s]
        pos_cols = [np.array([1.0 if p == q else 0.0 for p in d['pos']]) for q in P_JSON['e179_pos']]
        arr = np.array(arm_e179[s]['off_val'])
        out[s] = np.column_stack(pos_cols + [arr.mean(0) if seed is None else arr[seed]])
    return out


def zpnr(s, w):
    """E-179 季 t 每位球員 z_pnr(w)（full 模式），沒分鐘者 0。"""
    tb = P_JSON['player_tables'][s]; md = tb['modes']['full']
    ix = {p: i for i, p in enumerate(tb['pids'])}
    rho = md['rho']; den = math.sqrt(w * w + (1 - w) ** 2 + 2 * w * (1 - w) * rho + 1e-12)
    out = []
    for pid in P_JSON['e179'][s]['ids']:
        i = ix[str(pid)]
        out.append((w * md['zv'][i] + (1 - w) * md['za'][i]) / den if md['mask3'][i] > 0 else 0.0)
    return np.array(out)


def score99(s, w):
    """擋拆分數 0–99：季內（全部有分鐘球員）z_pnr(w) 的百分位×99，再取 E-179 球員。"""
    from scipy.stats import rankdata
    tb = P_JSON['player_tables'][s]; md = tb['modes']['full']
    rho = md['rho']; den = math.sqrt(w * w + (1 - w) ** 2 + 2 * w * (1 - w) * rho + 1e-12)
    ok = np.array(md['mask3']) > 0
    z = (w * np.array(md['zv']) + (1 - w) * np.array(md['za'])) / den
    sc = np.zeros(len(z)); sc[ok] = rankdata(z[ok], method='average') / ok.sum() * 99.0
    ix = {p: i for i, p in enumerate(tb['pids'])}
    return np.array([sc[ix[str(pid)]] for pid in P_JSON['e179'][s]['ids']])


def paired_game_bs(raw_a, raw_b, split_key, metric_key, draws):
    na, da = np.array(raw_a[split_key][f'game_num_{metric_key}']), np.array(raw_a[split_key][f'game_den_{metric_key}'])
    nb, db = np.array(raw_b[split_key][f'game_num_{metric_key}']), np.array(raw_b[split_key][f'game_den_{metric_key}'])
    pt = float(na.sum() / da.sum() - nb.sum() / db.sum())
    diff = (draws @ na) / (draws @ da) - (draws @ nb) / (draws @ db)
    lo, hi = np.percentile(diff, [5, 95])
    return {'point': round(pt, 4), 'ci90': [round(float(lo), 4), round(float(hi), 4)]}


def main():
    pre_ok = sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip()
    outs = {a: json.loads((HERE / f'out-{a}.json').read_text(encoding='utf-8')) for a in ALL_ARMS}
    y_O = {s: np.array(P_JSON['e179'][s]['O']) for s in E179_SEAS}
    pos_e = {s: np.array(P_JSON['e179'][s]['pos']) for s in E179_SEAS}

    preds = {a: ridge_cv_preds(make_m1(outs[a]['e179']), y_O) for a in ALL_ARMS}
    m1, m1f, m2, sstd = {}, {}, {}, {}
    for a in ALL_ARMS:
        r, pf = r2_pooled(y_O, preds[a]); m1[a] = round(r, 5); m1f[a] = pf
        m2[a] = round(r2_pooled(y_O, ridge_cv_preds(make_m2(outs[a]['e179']), y_O))[0], 5)
        ss = [r2_pooled(y_O, ridge_cv_preds(make_m1(outs[a]['e179'], sd), y_O))[0] for sd in range(5)]
        sstd[a] = round(float(np.std(ss, ddof=1)), 5)
    # T0 的 offpnr_val 恆 0，種子間 M1 無差異；門檻雜訊用 w* 臂自身種子 std
    wstar = max(WARMS, key=lambda a: m1[a])
    gain = m1[wstar] - m1['T0']
    fold = {s: round(m1f[wstar][s] - m1f['T0'][s], 5) for s in E179_SEAS}
    rng = np.random.default_rng(SEED_P)
    idxs = [{t: rng.integers(0, len(y_O[t]), len(y_O[t])) for t in E179_SEAS} for _ in range(B)]
    bs = np.array([r2_pooled(y_O, preds[wstar], ix)[0] - r2_pooled(y_O, preds['T0'], ix)[0] for ix in idxs])
    ci = [round(float(np.percentile(bs, 5)), 5), round(float(np.percentile(bs, 95)), 5)]
    j = WARMS.index(wstar)
    nb = {WARMS[x]: round(m1[WARMS[x]] - m1['T0'], 5) for x in (j - 1, j + 1) if 0 <= x < len(WARMS)}
    need = max(0.005, 2.0 * sstd[wstar])

    # 對戰：cross_test 閘門
    G = outs['T0']['cross_test']['games']
    rg = np.random.default_rng(SEED_G)
    draws = np.stack([np.bincount(rg.integers(0, G, G), minlength=G) for _ in range(B)]).astype(float)
    cross = paired_game_bs(outs[wstar], outs['T0'], 'cross_test', 'pts', draws)
    cross_seed_std = float(np.std(outs['T0']['cross_test']['seed_pts100_mse'], ddof=1))
    Gt = outs['T0']['test']['games']
    rt = np.random.default_rng(SEED_G + 1)
    draws_t = np.stack([np.bincount(rt.integers(0, Gt, Gt), minlength=Gt) for _ in range(B)]).astype(float)
    test_rep = paired_game_bs(outs[wstar], outs['T0'], 'test', 'pts', draws_t)
    stint = {sp: {a: outs[a][sp]['pts100_mse'] for a in ALL_ARMS} for sp in ('fold0', 'test', 'cross_test')}

    gate = {'wstar': wstar, 'c1_gain_vs_T0': round(gain, 5), 'c1_need': round(need, 5), 'c1_pass': bool(gain >= need),
            'c2_fold': fold, 'c2_pass': bool(sum(v > 0 for v in fold.values()) >= 2),
            'c3_ci90': ci, 'c3_pass': bool(ci[0] > 0),
            'c4_neighbors': nb, 'c4_pass': bool(all(v > 0 for v in nb.values())),
            'c5_cross_test_pts100_diff': cross, 'c5_seed_std_T0': round(cross_seed_std, 4),
            'c5_pass': bool(cross['point'] <= 2.0 * cross_seed_std)}
    gate['all_pass'] = all(gate[k] for k in ('c1_pass', 'c2_pass', 'c3_pass', 'c4_pass', 'c5_pass'))

    # 只報告：直接 ridge（不經 TF）
    base_only = {s: np.column_stack(base_cols(s)) for s in E179_SEAS}
    r_base = r2_pooled(y_O, ridge_cv_preds(base_only, y_O))[0]
    direct = {}
    for a in WARMS:
        f = {s: np.column_stack(base_cols(s) + [zpnr(s, WV[a])]) for s in E179_SEAS}
        direct[a] = round(r2_pooled(y_O, ridge_cv_preds(f, y_O))[0] - r_base, 5)

    # 每點換算（w*；另報 w=0.5）
    per_point = {}
    for wk in sorted({wstar, 'W05'}):
        X = np.vstack([np.column_stack(base_cols(s) + [score99(s, WV[wk])]) for s in E179_SEAS])
        y = np.concatenate([y_O[s] for s in E179_SEAS])
        b, mu, sd = ridge_fit(X, y)
        coef = float(b[-2] / sd[-1])
        rb = np.random.default_rng(SEED_P + 1); cs = []
        for _ in range(B):
            ii = rb.integers(0, len(y), len(y)); bb, _, sdb = ridge_fit(X[ii], y[ii]); cs.append(bb[-2] / sdb[-1])
        lo, hi = np.percentile(cs, [5, 95])
        per_point[wk] = {'O_per_point': round(coef, 5), 'ci90': [round(float(lo), 5), round(float(hi), 5)],
                         'wins_per_10pts_at_30mpg': round(coef * 10 * 30 / 48 * 2.7, 3),
                         'wins_ci90_per_10pts_at_30mpg': [round(float(lo) * 10 * 30 / 48 * 2.7, 3), round(float(hi) * 10 * 30 / 48 * 2.7, 3)]}

    # 位置組、WL、例子
    grp = {'G': ['PG', 'SG'], 'F': ['SF', 'PF'], 'C': ['C']}
    by_group = {}
    for g, ps in grp.items():
        ix = {t: np.where(np.isin(pos_e[t], ps))[0] for t in E179_SEAS}
        by_group[g] = {a: round(r2_pooled(y_O, preds[a], ix)[0], 4) for a in ('T0', wstar)}
        by_group[g]['n'] = int(sum(len(v) for v in ix.values()))
    wl = [s['w_best'] for s in outs['WL']['seeds']]
    t = '2024-25'; d = P_JSON['e179'][t]
    rk = lambda v: np.argsort(np.argsort(-v)) + 1
    r0, rw, ra = rk(preds['T0'][t]), rk(preds[wstar][t]), rk(y_O[t])
    off = np.array(outs[wstar]['e179'][t]['offpnr_val']).mean(0)
    sc = score99(t, WV[wstar])
    raw = P_JSON['player_tables'][t]['pnr_raw']

    def row(i):
        rr = raw.get(str(d['ids'][i]), [0, 0, 0])
        return {'name': d['names'][i], 'pos': d['pos'][i], 'pnr_score': round(float(sc[i]), 1),
                'pnr_vol36': rr[0], 'pnr_rate': rr[1], 'pnr_poss': rr[2], 'offpnr': round(float(off[i]), 3),
                'rank_T0': int(r0[i]), 'rank_wstar': int(rw[i]), 'actual_rank': int(ra[i]), 'n': len(r0)}
    sh = np.argsort(r0 - rw)
    names = ('Trae Young', 'Luka', 'Jalen Brunson', 'Shai Gilgeous', 'Tyrese Haliburton', 'Cade Cunningham',
             'Damian Lillard', 'Ja Morant', 'Stephen Curry', 'Nikola Joki', 'Giannis')
    ex = {'up': [row(i) for i in sh[::-1][:8]], 'down': [row(i) for i in sh[:8]],
          'named': [row(i) for i, nm in enumerate(d['names']) if any(k in nm for k in names)]}

    res = {'prereg_sha256_ok': pre_ok, 'M1': m1, 'M1_per_fold': m1f, 'M2': m2, 'M1_seed_std': sstd,
           'stint_pts100_mse': stint, 'test_report_wstar_minus_T0': test_rep, 'gate': gate,
           'direct_ridge_gain_vs_base': direct, 'base_only_R2': round(r_base, 5), 'per_point': per_point,
           'wl': {'w': [round(float(x), 4) for x in wl], 'mean': round(float(np.mean(wl)), 4), 'std': round(float(np.std(wl, ddof=1)), 4)},
           'by_group': by_group, 'examples_2024_25': ex,
           'verdict': 'candidate' if gate['all_pass'] else 'not_adopted_or_hold'}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('prereg_sha256_ok', 'M1', 'M2', 'gate', 'direct_ridge_gain_vs_base', 'per_point', 'wl', 'by_group')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
