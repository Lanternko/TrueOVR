"""E-089 稽核：獨立重算 m1–m3（與 Q_lin）、W 單元值、抽驗卡片 OVR。

用法（repo 根目錄或任意處）：
  PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 python reports/card-0.2.4+E089-minutes-saturation/audit/audit_recalc.py
輸出：audit/audit_recalc.json（並印出摘要）。只寫 audit/。

獨立的部分（自己實作，不呼叫 e089.py／e084.py 的計算函式）：
  W、g_c、卡片 g／替補水準／錨點／two_segment、四個答案、Spearman ρ、bootstrap（2000 次、seed 1、master 聯集、AB/BA 平均）。
共用的輸入（只當資料來源，只呼叫資料載入與特徵準備，不呼叫評估或 g 的計算）：
  e089.load_data() / build_pools()（E-075 pools）/ classify() / scope_feats()（讀 CSV、組特徵）、
  e089.pipeline() 只取其中「用人回歸預測 pn、pred_new」（回歸係數不隨分鐘權重改變，c0 已證明 linear 重現 card 0.2.4）。
  pn、pred_new 在分鐘模式 linear 下取得；g 一律由本檔用 pn、替補水準 r、分鐘自己重算。
"""
import csv
import hashlib
import importlib.util
import json
import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.dont_write_bytecode = True
import numpy as np

AUD = Path(__file__).resolve().parent
E89 = AUD.parent
ROOT = E89.parents[1]
NBOOT = 2000
POOL_MIN = 500   # 預註冊沿用 E-084/card 0.2.4 的 POOL_MIN（寫死）；本檔另用 ranking.csv 的 MIN 欄交叉驗證


# ---------------------------------------------------------------- 自己實作的部分
def W(m):
    m = np.asarray(m, dtype=float)
    return (1.0 - np.exp(-m / 15.0)) / (1.0 - math.exp(-36.0 / 15.0))


def avg_rank(x):
    """平均名次（同分取平均），自己寫，不用 scipy。"""
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind='mergesort')
    xs = x[order]
    r = np.empty(len(x))
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and xs[j + 1] == xs[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = avg_rank(a), avg_rank(b)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / math.sqrt((ra * ra).sum() * (rb * rb).sum()))


def pctl(vals, mask, prc):
    """第 prc 百分位：池內排序後取 round(prc/100*(n-1)) 位（預註冊沿用的 qf 定義）。"""
    ref = np.sort(np.asarray(vals)[np.asarray(mask)])
    return float(ref[int(round(prc / 100.0 * (len(ref) - 1)))])


def two_seg(x, p1, p50, p99):
    return np.where(x <= p50, 40 + 30 * (x - p1) / (p50 - p1), 70 + 29 * (x - p50) / (p99 - p50))


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------- 取資料（只當輸入）
def load_inputs():
    spec = importlib.util.spec_from_file_location('e089_data_only', E89 / 'e089.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.load_data()
    pools = m.build_pools()
    D = m.D
    C = m.classify(m.BASE_OPTS)
    # 用人回歸預測 pn、pred_new：在 linear 模式取（回歸與分鐘權重無關）
    m.MINUTES = 'linear'
    res = m.pipeline(m.BASE_OPTS, pools, 'season')
    aux = res['_aux']
    inp = {'AB': {}, 'BA': {}}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        dn = fit + ev
        names = pools[dn]
        sf = m.scope_feats(fit, D['fitpred'][fit], C, m.BASE_OPTS)
        nm2pid = D['nm2pid']
        pid = [nm2pid[n] for n in names]
        sel = np.array([sf['idx'][q] for q in pid])
        # 答案所需欄位自己從 D 取（不用 pipeline dirs 的現成答案）
        r1e = D['rapm1'][ev]
        netN = np.array([r1e[q]['net'] if q in r1e else np.nan for q in pid])
        net = np.array([float(D['rapm'][ev][n]['pooledNet']) for n in names])
        mpg_ev = np.array([D['mpgh'][ev][q][1] for q in pid])
        d = aux['dirs'][dn]
        inp[dn] = {'names': names, 'mp': sf['mp'][sel], 'pn': d['pn'], 'rr': d['rr'], 'netN': netN, 'net': net, 'mpg_ev': mpg_ev,
                   '_prod_cand_linear': d['cand'], '_prod_netN': d['netN'], '_prod_net': d['net'], '_prod_mpg_ev': d['mpg_ev']}
    sff = m.scope_feats('full', D['prim'], C, m.BASE_OPTS)
    card = {'names': aux['names'], 'MIN': sff['MIN'], 'mp': sff['mp'], 'pred_new': aux['pred_new']}
    return inp, card


# ---------------------------------------------------------------- m1–m3 重算
def recalc(inp):
    out = {'checks_inputs': {}}
    E = {}
    for dn in ('AB', 'BA'):
        d = inp[dn]
        g_lin = (d['pn'] - d['rr']) * d['mp'] / 36.0
        g_W = (d['pn'] - d['rr']) * W(d['mp'])
        out['checks_inputs'][dn] = {
            'n_pool': len(d['names']), 'n_with_rapm1': int((~np.isnan(d['netN'])).sum()),
            'g_lin_vs_producer_linear_cand_maxabs': float(np.abs(g_lin - d['_prod_cand_linear']).max()),
            'netN_equal_producer': bool(np.array_equal(np.nan_to_num(d['netN'], nan=9e9), np.nan_to_num(d['_prod_netN'], nan=9e9))),
            'net_equal_producer': bool(np.array_equal(d['net'], d['_prod_net'])),
            'mpg_ev_equal_producer': bool(np.array_equal(d['mpg_ev'], d['_prod_mpg_ev']))}
        hasN = ~np.isnan(d['netN'])
        wev = W(d['mpg_ev'])
        E[dn] = {'names': d['names'], 'hasN': hasN, 'g': {'W': g_W, 'lin': g_lin},
                 'ans': {'N_W': d['netN'] * wev, 'Q_W': d['net'] * wev, 'N_lin': d['netN'] * d['mpg_ev'], 'Q_lin': d['net'] * d['mpg_ev']}}
    KEYS = ('N_W', 'Q_W', 'N_lin', 'Q_lin')

    def stat(sel):
        r = {}
        for k in KEYS:
            for tag in ('W', 'lin'):
                vs = []
                for dn in ('AB', 'BA'):
                    e, s = E[dn], sel[dn]
                    if k.startswith('N'):
                        s = s[e['hasN'][s]]
                    vs.append(spearman(e['g'][tag][s], e['ans'][k][s]))
                r[(k, tag)] = float(np.mean(vs))
        return r

    full = stat({dn: np.arange(len(E[dn]['names'])) for dn in E})
    master = sorted(set(E['AB']['names']) | set(E['BA']['names']))
    NN = len(master)
    pos = {dn: {n: i for i, n in enumerate(E[dn]['names'])} for dn in E}
    mp_ = {dn: np.array([pos[dn].get(n, -1) for n in master]) for dn in E}
    rng = np.random.default_rng(1)
    boots = {key: [] for key in full}
    for _ in range(NBOOT):
        ix = rng.integers(0, NN, NN)
        sel = {}
        for dn in E:
            s = mp_[dn][ix]
            sel[dn] = s[s >= 0]
        st = stat(sel)
        for key, v in st.items():
            boots[key].append(v)
    res = {}
    for k in KEYS:
        d = np.array(boots[(k, 'W')]) - np.array(boots[(k, 'lin')])
        res[k] = {'delta': full[(k, 'W')] - full[(k, 'lin')], 'ci90': [float(np.percentile(d, 5)), float(np.percentile(d, 95))],
                  'rho_cand': full[(k, 'W')], 'rho_base': full[(k, 'lin')]}
    out['master_size'] = NN
    out['pool_sizes'] = {dn: len(E[dn]['names']) for dn in E}
    out['delta_rho'] = res
    out['gates'] = {'m1': res['N_W']['ci90'][0] > -0.02, 'm2': res['N_lin']['ci90'][0] > -0.05, 'm3': res['Q_W']['ci90'][0] > -0.05}
    return out


# ---------------------------------------------------------------- 單元值
def unit():
    want = {0: 0.0, 36: 1.0, 5: 0.31175, 20: 0.80987}
    tol = {0: 1e-12, 36: 1e-12, 5: 1e-5, 20: 1e-5}
    return {str(m): {'W': float(W(m)), 'want': v, 'pass': bool(abs(float(W(m)) - v) <= tol[m])} for m, v in want.items()}


# ---------------------------------------------------------------- 卡片抽驗
def card_check(card):
    names = card['names']
    MIN, mp, pr = card['MIN'], card['mp'], card['pred_new']
    pool = MIN >= POOL_MIN
    r = pctl(pr, pool, 10)
    g = (pr - r) * W(mp)
    p1, p50, p99 = pctl(g, pool, 1), pctl(g, pool, 50), pctl(g, pool, 99)
    ovr = two_seg(g, p1, p50, p99)
    ovr1 = np.array([float(f'{x:.1f}') for x in ovr])
    # 線性（card 0.2.4）對照
    gl = (pr - r) * mp / 36.0
    q1, q50, q99 = pctl(gl, pool, 1), pctl(gl, pool, 50), pctl(gl, pool, 99)
    ovrl = np.array([float(f'{x:.1f}') for x in two_seg(gl, q1, q50, q99)])
    rows = list(csv.DictReader(open(E89 / 'ranking.csv', encoding='utf-8')))
    rows024 = {x['name']: x for x in csv.DictReader(open(ROOT / 'reports/card-0.2.4/ranking.csv', encoding='utf-8'))}
    byname = {x['name']: x for x in rows}
    idx = {n: i for i, n in enumerate(names)}
    # 全員比對
    diffs_ovr = [abs(ovr1[idx[n]] - float(x['ovr'])) for n, x in byname.items()]
    diffs_g = [abs(g[idx[n]] - float(x['gRepl'])) for n, x in byname.items()]
    diffs_ovr_lin = [abs(ovrl[idx[n]] - float(x['ovr'])) for n, x in rows024.items()]
    # 排名：依 ovr 由大到小（同分保持 ranking.csv 順序比對時只看名次欄位是否落在同分區間）
    order = sorted(range(len(names)), key=lambda i: -ovr[i])   # 以未四捨五入的 OVR 排序（ranking.csv 也是）
    my_rank = {names[i]: k + 1 for k, i in enumerate(order)}
    rk_mismatch = [n for n, x in byname.items() if my_rank[n] != int(x['rank'])]
    # 同 OVR 的人名次可能不同；用「ranking 的名次所對應的 OVR 與我的 OVR 一致」再判
    rk_bad = [n for n in rk_mismatch if abs(ovr1[idx[n]] - float(byname[n]['ovr'])) > 1e-9]
    random.seed(7)
    all_names = [x['name'] for x in rows]
    pick = random.Random(7).sample(all_names, 5)
    sample = []
    for n in ['Alex Caruso', 'Dyson Daniels'] + pick:
        i = idx[n]
        x = byname[n]
        sample.append({'name': n, 'mpg_csv': float(x['mpg']), 'mp_exact': float(mp[i]), 'g_mine': float(g[i]), 'g_csv': float(x['gRepl']),
                       'ovr_mine': float(ovr1[i]), 'ovr_csv': float(x['ovr']), 'rank_mine': my_rank[n], 'rank_csv': int(x['rank']),
                       'ovr_card024': float(rows024[n]['ovr']), 'rank_card024': int(rows024[n]['rank']),
                       'g_card024': float(rows024[n]['gRepl'])})
    # 只用 ranking.csv 的已發佈欄位（rounded mpg 與線性 gRepl）反推，不碰管線
    pub = {}
    for n in ['Alex Caruso', 'Dyson Daniels']:
        x = rows024[n]
        gl_pub, m_pub = float(x['gRepl']), float(x['mpg'])
        pub[n] = {'pred_minus_r_from_card024': gl_pub * 36.0 / m_pub, 'g_W_from_csv_only': gl_pub * 36.0 / m_pub * float(W(m_pub))}
    return {'r_repl': r, 'anchors': {'PR1': p1, 'PR50': p50, 'PR99': p99}, 'anchors_linear': {'PR1': q1, 'PR50': q50, 'PR99': q99},
            'n_players': len(names), 'n_pool_MIN_ge_500': int(pool.sum()),
            'all_players': {'max_abs_ovr_diff': float(max(diffs_ovr)), 'n_ovr_diff_gt_0.05': int(sum(d > 0.05 for d in diffs_ovr)),
                            'max_abs_gRepl_diff': float(max(diffs_g)), 'n_rank_mismatch_ignoring_ties': len(rk_bad),
                            'n_rank_mismatch_raw': len(rk_mismatch)},
            'linear_replay_vs_card024': {'max_abs_ovr_diff': float(max(diffs_ovr_lin))},
            'sample': sample, 'csv_only_check': pub}


def main():
    inp, card = load_inputs()
    out = {'unit_W': unit()}
    out.update(recalc(inp))
    out['card_check'] = card_check(card)
    out['sha256'] = {'ranking.csv': sha256(E89 / 'ranking.csv'), 'results.json': sha256(E89 / 'results.json'),
                     'preregistration.md': sha256(E89 / 'preregistration.md')}
    (AUD / 'audit_recalc.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    dr = out['delta_rho']
    for k in ('N_W', 'N_lin', 'Q_W', 'Q_lin'):
        v = dr[k]
        print(f"Δρ_{k}: {v['delta']:+.4f} [{v['ci90'][0]:+.4f}, {v['ci90'][1]:+.4f}]  (cand {v['rho_cand']:.4f}, base {v['rho_base']:.4f})")
    print('gates', out['gates'])
    print('unit', {k: v['pass'] for k, v in out['unit_W'].items()})
    cc = out['card_check']
    print('card all-players', cc['all_players'], 'linear replay', cc['linear_replay_vs_card024'])
    for s in cc['sample']:
        print(s['name'], 'g', round(s['g_mine'], 4), s['g_csv'], 'ovr', s['ovr_mine'], s['ovr_csv'], 'rank', s['rank_mine'], s['rank_csv'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
