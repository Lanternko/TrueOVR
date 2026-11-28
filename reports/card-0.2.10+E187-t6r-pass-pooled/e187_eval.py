"""E-187 評估（自 E-186 e186_eval.py 複本）：判定 a1／b 一字照 preregistration.md（sha 見 .sha256）。
  python -I -B -X utf8 e187_eval.py phase0   只讀 K6 的卡：h_C（綜合分 C 三季合併 bootstrap 90% 半寬）、h_R（下季 RAPM 名次 ρ 三季合併 bootstrap 90% 半寬）-> phase0.json
  python -I -B -X utf8 e187_eval.py final    a1／b 與只報告項 -> results.json
卡片：K6＝歷史原點 E-186 work/K6-<季>（E-164 S 臂重建，E-186 c0 逐位元相同）、2025-26＝reports/card-0.2.10/ranking.csv；
      KJ＝work/KJ-<季>、2025-26＝work/KJU-2025-26（0.2.10 屬性＋依 T6R 重擬合＋pass 共用斜率）；KA（只報告）＝同上但目標 T6（KA／KAU）。
統計量沿用 E-186／E-179：S 用 off_scores／pct／sp，季內以球員重抽 2000 次，seed 20261101；C 沿用 E-153。"""
import csv, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W = HERE / 'work'
S186 = ROOT / 'reports/card-0.2.10+E186-t6-rapm-target'
E142 = ROOT / 'reports/E142-card-target'
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
sys.path.insert(0, str(E142))
sys.path.insert(0, str(ROOT / 'scripts'))


def _load(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


P = _load('pe', E142 / 'phase1_eval.py')
E179 = _load('e179', ROOT / 'reports/E179-forward-pass-vs-rapm/e179_eval.py')
TWOK = ROOT / 'data/external-impact/2k/2k-merged-e142.csv'
HIST = ['2022-23', '2023-24', '2024-25']
SEASONS = HIST + ['2025-26']
NEXT = E179.NEXT
SEED, B = 20261101, 2000
GROUPS = E179.GROUPS
ARMS = ('K6', 'KJ')
ALL = ('K6', 'KJ', 'KA')
STAT_ATTR = ('creation', 'pass')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rpath(arm, t):
    if arm == 'K6':
        return ROOT / 'reports/card-0.2.10/ranking.csv' if t == '2025-26' else S186 / f'work/K6-{t}/out/ranking.csv'
    return W / (f'{arm}U-2025-26' if t == '2025-26' else f'{arm}-{t}') / 'out/ranking.csv'


def season_data(t, arms=ARMS):
    """E-179 season_data 的複本：卡片檔改成各臂的 ranking，各臂人群取交集。"""
    cards = {a: list(csv.DictReader(open(rpath(a, t), encoding='utf-8-sig'))) for a in arms}
    off = {a: E179.off_scores(cards[a]) for a in arms}
    pop, _ = P.pop_of(t)
    _, mp_next = P.pop_of(NEXT[t])
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    m = {}
    for a in arms:
        m[a] = {}
        for r in cards[a]:
            if float(r['MIN']) < 500:
                continue
            ids = n2.get(P.norm(r['name'])) or []
            if len(ids) == 1:
                m[a][ids[0]] = r
    d = json.loads((E126 / f'rapm-{NEXT[t]}.json').read_text(encoding='utf-8'))
    assert d['season'] == NEXT[t]
    rv = {int(p): v for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mp_next}
    ids = sorted(p for p in m[arms[0]] if p in rv and all(p in m[a] for a in arms))
    W_ = np.array([P.wfun(mp_next[p]) for p in ids])
    out = {'ids': ids, 'net': np.array([rv[p]['net'] for p in ids]) * W_, 'O': np.array([rv[p]['O'] for p in ids]) * W_}
    for a in arms:
        rows = [m[a][p] for p in ids]
        out[a] = {'names': [r['name'] for r in rows], 'pos': np.array([r['pos'] for r in rows]), 'ovr': np.array([float(r['ovr']) for r in rows]),
                  'pass': np.array([float(r['pass']) for r in rows]), 'creation': np.array([float(r['creation']) for r in rows])}
    return out


def stat(d, a, idx):
    """Spearman(屬性, e_net)：F、G、全部；e_net＝pct(下季 net×W) − pct(ovr)（E-179 定義）。"""
    e = E179.pct(d['net'][idx]) - E179.pct(d[a]['ovr'][idx])
    pos = d[a]['pos'][idx]
    o = {}
    for at in STAT_ATTR:
        x = d[a][at][idx]
        for g, ps in GROUPS.items():
            k = np.isin(pos, list(ps))
            o[f'S_{g}_{at}'] = E179.sp(x[k], e[k])
        o[f'S_all_{at}'] = E179.sp(x, e)
    return o


def pooled_stats(data, idxs, arms):
    """三季以人數加權合併（E-179 §3）。"""
    ns = {t: len(idxs[t]) for t in HIST}
    tot = sum(ns.values())
    per = {a: {t: stat(data[t], a, idxs[t]) for t in HIST} for a in arms}
    return {a: {k: float(sum(ns[t] / tot * per[a][t][k] for t in HIST)) for k in per[a][HIST[0]]} for a in arms}, per


def boot_stats(data, arms):
    """季內以球員重抽（各臂共用同一組 idx＝配對）；回 {arm: {key: draws}}，另有 'diff_<臂>'（臂−arms[0]）。"""
    rng = np.random.default_rng(SEED)
    draws = {a: defaultdict(list) for a in arms}
    for a in arms[1:]:
        draws['diff_' + a] = defaultdict(list)
    for _ in range(B):
        idxs = {t: rng.integers(0, len(data[t]['ids']), len(data[t]['ids'])) for t in HIST}
        pp, _ = pooled_stats(data, idxs, arms)
        for a in arms:
            for k, v in pp[a].items():
                draws[a][k].append(v)
        for a in arms[1:]:
            for k, v in pp[a].items():
                draws['diff_' + a][k].append(v - pp[arms[0]][k])
    return draws


# ---------- C（E-153 口徑） ----------
def c_setup(arms=ARMS):
    twok = P.load_twok(str(TWOK))
    pages = {s_: P.C0L.contracts(s_) for s_ in P.C0L.ORDER}
    drafts, ev = P.C0L.draft_years(), P.C0L.tx_events()
    out = {}
    for t in SEASONS:
        pop, _ = P.pop_of(t)
        mpgs = {s: P.pop_of(s)[1] for s in SEASONS}
        sal, _ = P.salary_terms(t, pop, pages, drafts, ev)
        ref, raw, _ = P.build_ref(t, pop, mpgs, sal, twok, {})
        n2 = defaultdict(list)
        for p, i in pop.items():
            n2[P.norm(i['name'])].append(p)
        ovr = {}
        for a in arms:
            m = {}
            for r in csv.DictReader(open(rpath(a, t), encoding='utf-8-sig')):
                if float(r['MIN']) < 500:
                    continue
                ids = n2.get(P.norm(r['name'])) or []
                if len(ids) == 1:
                    m[ids[0]] = float(r['ovr'])
            ovr[a] = m
        ids = sorted(p for p in set.intersection(*[set(ovr[a]) for a in arms]) if p in ref)
        out[t] = {'ids': ids, 'ovr': {a: np.array([ovr[a][p] for p in ids]) for a in arms}, 'ref': np.array([ref[p] for p in ids]), 'raw': raw}
    return out


def c_metrics(D, t, arm, idx=None):
    d = D[t]
    idx = np.arange(len(d['ids'])) if idx is None else idx
    o, rf = d['ovr'][arm][idx], d['ref'][idx]
    out = {'n': int(len(idx)), 'C': P.spearman(o, rf)}
    for k in ('sal', 'twok', 'rapm'):
        have = [i for i in idx if d['ids'][i] in d['raw'][k]]
        out['n_' + k] = len(have)
        if len(have) < 10:
            out[k] = None
            continue
        oo = d['ovr'][arm][have]
        if k == 'sal':
            y = [d['raw'][k][d['ids'][i]][0] for i in have]
            w = [P.YEARW.get(d['raw'][k][d['ids'][i]][1], 0.3) for i in have]
            out[k] = P.wspearman(oo, y, w)
        else:
            out[k] = P.spearman(oo, [d['raw'][k][d['ids'][i]] for i in have])
    return out


def c_boot(D, arms):
    """跨季共用球員重抽（同 e153_eval）；回每臂 pooled C 與 pooled 下季 RAPM ρ 的 draws（ρ 以各季 n_rapm 加權，同點估計）。"""
    rng = np.random.default_rng(SEED)
    allids = sorted(set().union(*[D[t]['ids'] for t in HIST]))
    pos = {t: {p: i for i, p in enumerate(D[t]['ids'])} for t in HIST}
    resC = {a: np.empty(B) for a in arms}
    resR = {a: np.empty(B) for a in arms}
    for b in range(B):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        numC = {a: 0.0 for a in arms}
        numR = {a: 0.0 for a in arms}
        den = denR = 0.0
        for t in HIST:
            sel = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat(np.array([pos[t][allids[j]] for j in sel]), np.array([mult[j] for j in sel]))
            for a in arms:
                numC[a] += len(idx) * P.spearman(D[t]['ovr'][a][idx], D[t]['ref'][idx])
            den += len(idx)
            have = [i for i in idx if D[t]['ids'][i] in D[t]['raw']['rapm']]
            y = [D[t]['raw']['rapm'][D[t]['ids'][i]] for i in have]
            for a in arms:
                numR[a] += len(have) * P.spearman(D[t]['ovr'][a][have], y)
            denR += len(have)
        for a in arms:
            resC[a][b] = numC[a] / den
            resR[a][b] = numR[a] / denR
    return resC, resR


def half(v):
    return float((np.percentile(v, 95) - np.percentile(v, 5)) / 2)


def ci(v):
    return [float(np.percentile(v, 5)), float(np.percentile(v, 95))]


def phase0():
    """只讀 K6 的卡；KJ／KA 檔不開。h_C 照 E-186 phase0 口徑重算（應與 0.04468 同），h_R 為新增。"""
    D = c_setup(('K6',))
    cC, cR = c_boot(D, ('K6',))
    ns = {t: len(D[t]['ids']) for t in HIST}
    ps = {t: c_metrics(D, t, 'K6') for t in HIST}
    cpt = sum(ns[t] * ps[t]['C'] for t in HIST) / sum(ns.values())
    nr = {t: ps[t]['n_rapm'] for t in HIST}
    rpt = sum(nr[t] * ps[t]['rapm'] for t in HIST) / sum(nr.values())
    out = {'n_eval_C': ns, 'n_rapm': nr, 'C_K6_pooled': cpt, 'h_C': half(cC['K6']), 'ci90_C': ci(cC['K6']),
           'rapm_rho_K6_pooled': rpt, 'rapm_rho_K6_per_season': {t: ps[t]['rapm'] for t in HIST},
           'h_R': half(cR['K6']), 'ci90_rapm_rho_K6': ci(cR['K6']), 'seed': SEED, 'draws': B,
           'e186_h_C': json.loads((S186 / 'phase0.json').read_text(encoding='utf-8')).get('h_C') if (S186 / 'phase0.json').exists() else None}
    (W / 'phase0.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    (HERE / 'phase0.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


KEY = ['Jalen Williams', 'Jalen Johnson', 'Paolo Banchero', 'Anthony Edwards', 'Franz Wagner', 'Kevin Durant', 'Herbert Jones', 'Dillon Brooks',
       'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Victor Wembanyama', 'Cooper Flagg', 'Kon Knueppel', 'Scottie Barnes', 'LeBron James']
JW = 'Jalen Williams'


def rank900(arm):
    """2025-26 卡內 MIN>=900 的 OVR 名次（平手取平均名次，同 F-125 ranks.py）。"""
    from scipy.stats import rankdata
    rows = [r for r in csv.DictReader(open(rpath(arm, '2025-26'), encoding='utf-8-sig')) if float(r['MIN']) >= 900]
    rk = rankdata(-np.array([float(r['ovr']) for r in rows]))
    return rows, {r['name']: float(k) for r, k in zip(rows, rk)}


def top25_resid(rows, rk, target):
    """卡片前 25 名內：JW 對目標的殘差（全人群線性擬合 目標~OVR）減去前 25 名殘差平均；另報 JW 在前 25 名殘差的排序（1＝最低）。"""
    import pickle
    t0 = {}
    for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8-sig')):
        t0[r['name']] = int(r['playerId'])
    cand = pickle.load(open(target, 'rb'))
    ok = [r for r in rows if r['name'] in t0 and t0[r['name']] in cand]
    o = np.array([float(r['ovr']) for r in ok])
    y = np.array([cand[t0[r['name']]][0] for r in ok])
    X = np.c_[np.ones_like(o), o]
    res = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    names = [r['name'] for r in ok]
    top = [i for i, n in enumerate(names) if rk[n] <= 25]
    j = names.index(JW)
    return {'n_fit': len(ok), 'n_top25_with_target': len(top), 'JW_resid': float(res[j]), 'top25_mean_resid': float(res[top].mean()),
            'JW_minus_top25_mean': float(res[j] - res[top].mean()), 'JW_in_top25': j in top,
            'JW_resid_rank_in_top25_lowest_first': int((res[top] < res[j]).sum()) + 1, 'resid_sd_all': float(res.std())}


def final():
    p0 = json.loads((W / 'phase0.json').read_text(encoding='utf-8'))
    prereg_ok = sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().split()[0] and         sha(HERE / 'errata-1.md') == (HERE / 'errata-1.sha256').read_text().split()[0]
    # ---- S（report-only）----
    data = {t: season_data(t, ALL) for t in HIST}
    full = {t: np.arange(len(data[t]['ids'])) for t in HIST}
    pt, per = pooled_stats(data, full, ALL)
    dr = boot_stats(data, ALL)
    S = {k: {a: pt[a][k] for a in ALL} | {'diff_KJ': pt['KJ'][k] - pt['K6'][k], 'diff_KA': pt['KA'][k] - pt['K6'][k],
                                           'ci90_diff_KJ': ci(dr['diff_KJ'][k]), 'ci90_diff_KA': ci(dr['diff_KA'][k]),
                                           'per_season': {a: {t: per[a][t][k] for t in HIST} for a in ALL}} for k in pt['K6']}
    # ---- a1 ----
    rows_by, rk_by = {}, {}
    for a in ALL:
        rows_by[a], rk_by[a] = rank900(a)
    a1 = {'JW_rank': {a: rk_by[a][JW] for a in ALL}, 'n900': {a: len(rows_by[a]) for a in ALL}, 'threshold': 16,
          'pass_prereg_ge16_report_only': bool(rk_by['KJ'][JW] >= 16), 'ovr': {a: float(next(r['ovr'] for r in rows_by[a] if r['name'] == JW)) for a in ALL}}
    # ---- C、下季 RAPM ρ / b ----
    D = c_setup(ALL)
    ns = {t: len(D[t]['ids']) for t in HIST}
    ps = {t: {a: c_metrics(D, t, a) for a in ALL} for t in SEASONS}

    def pooled_diff(key, arm):
        num = den = 0.0
        for t in HIST:
            nn = ps[t][arm]['n'] if key == 'C' else ps[t][arm]['n_' + key]
            num += nn * (ps[t][arm][key] - ps[t]['K6'][key])
            den += nn
        return num / den
    od = {a: {k: pooled_diff(k, a) for k in ('C', 'sal', 'twok', 'rapm')} for a in ('KJ', 'KA')}
    cC, cR = c_boot(D, ALL)
    h_C, h_R = p0['h_C'], p0['h_R']
    b = {'npm_test': '見 report.md／logs/npm_test.log', 'C_diff_pooled': od['KJ']['C'], 'h_C': h_C, 'floor_C_minus_2hC': -2 * h_C,
         'C_diff_ci90_info': ci(cC['KJ'] - cC['K6']), 'C_pass': bool(od['KJ']['C'] >= -2 * h_C),
         'rapm_rho_diff_pooled': od['KJ']['rapm'], 'h_R': h_R, 'floor_R_minus_2hR': -2 * h_R, 'rapm_diff_ci90_info': ci(cR['KJ'] - cR['K6']),
         'R_pass': bool(od['KJ']['rapm'] >= -2 * h_R)}
    # ---- 只報告 ----
    key = {}
    for n in KEY:
        row = {}
        for a in ALL:
            m = [r for r in rows_by[a] if P.norm(r['name']) == P.norm(n)]
            row[a] = {'rank': rk_by[a][m[0]['name']], 'ovr': float(m[0]['ovr'])} if m else None
        key[n] = row
    top20 = {a: sorted([n for n, k in rk_by[a].items() if k <= 20], key=lambda n: rk_by[a][n]) for a in rk_by}
    top25 = {}
    for a in ALL:
        for tgt in ('T6', 'T6R', 'T6new'):   # T6＝E-186 當時的 T6（pre-L102 備份，errata 的 −1.04 基準）；T6new＝17:20 被 L-102 重產後的 T6（補 Jokić／Wembanyama），只報告
            pk = {'T6': E142 / 'phase1-work/cands/pre-L102/T6-2025-26.pkl', 'T6new': E142 / 'phase1-work/cands/T6-2025-26.pkl',
                  'T6R': S186 / 'work/cands/T6R-2025-26.pkl'}[tgt]
            top25[f'{a}_vs_{tgt}'] = top25_resid(rows_by[a], rk_by[a], pk)
    moved = {a: sum(1 for n, k in rk_by['K6'].items() if k <= 100 and abs(rk_by[a][n] - k) >= 10) for a in ('KJ', 'KA')}
    # errata-1（R-119）：a1＝JW 名次比 K6 低（數字變大）且前 25 名內對 T6 的分段殘差（JW−前25平均）往 0 縮小；不設名次門檻
    r6, rj = top25['K6_vs_T6']['JW_minus_top25_mean'], top25['KJ_vs_T6']['JW_minus_top25_mean']
    a1['errata1'] = {'rank_K6': rk_by['K6'][JW], 'rank_KJ': rk_by['KJ'][JW], 'rank_dropped': bool(rk_by['KJ'][JW] > rk_by['K6'][JW]),
                     'seg_resid_vs_T6_K6': r6, 'seg_resid_vs_T6_KJ': rj, 'seg_resid_shrunk_toward_0': bool(abs(rj) < abs(r6) and rj * r6 > 0)}
    a1['pass'] = bool(a1['errata1']['rank_dropped'] and a1['errata1']['seg_resid_shrunk_toward_0'])
    ok_b_pre_npm = b['C_pass'] and b['R_pass']
    res = {'prereg_sha256_ok': bool(prereg_ok), 'seed': SEED, 'draws': B, 'n_eval_S': {t: len(data[t]['ids']) for t in HIST}, 'n_eval_C': ns,
           'a1': a1, 'b': b, 'S_stats': S, 'C_per_season': ps, 'C_pooled_diff_vs_K6': od,
           'key_players_2025_26': key, 'top20_2025_26': top20, 'top25_resid_JW': top25, 'moved10_top100_vs_K6': moved,
           'verdict_before_npm_test': ('fixed_adoption_candidate' if (a1['pass'] and ok_b_pre_npm) else 'not_fixed' if not a1['pass'] else 'a1_pass_but_b_fail'),
           'arms': {'K6': 'reports/card-0.2.10/ranking.csv（2025-26）、E-186 重建（歷史）', 'KJ': 'T6R＋pass 共用斜率；2025-26＝0.2.10 屬性＋重擬合',
                    'KA': '只報告：T6＋pass 共用斜率＋重擬合'}}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('a1', 'b', 'verdict_before_npm_test', 'moved10_top100_vs_K6')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    {'phase0': phase0, 'final': final}[sys.argv[1]]()
