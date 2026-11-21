"""E-186 評估：預註冊 preregistration.md ＋ errata-1.md（sha 見兩個 .sha256）。判定 a1／a2／b 一字照預註冊。
  python -I -B -X utf8 e186_eval.py phase0   只用 K6 算檢定力：S_F(creation,e_net) 的 bootstrap 90% 半寬 h，與 C 的半寬 h_C -> work/phase0.json
  python -I -B -X utf8 e186_eval.py final    a1／a2／b 與只報告項 -> results.json
卡片：K6＝歷史原點 work/K6-<季>（E-164 S 臂重建，c0 逐位元相同）、2025-26＝reports/card-0.2.10/ranking.csv；
      KR＝work/KR-<季>、2025-26＝work/KRU-2025-26（0.2.10 屬性＋依 T6R 重擬合）；對照 K6U＝2025-26 以 T6 重擬合（只報告）。
統計量沿用 E-179 e179_eval.py 的 off_scores／pct／sp／人群規則（季內以球員重抽 2000 次，seed 20261101）；C 沿用 E-153 e153_eval.py。"""
import csv, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W = HERE / 'work'
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
ARMS = ('K6', 'KR')
STAT_ATTR = ('creation', 'pass')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rpath(arm, t):
    if arm == 'K6':
        return ROOT / 'reports/card-0.2.10/ranking.csv' if t == '2025-26' else W / f'K6-{t}/out/ranking.csv'
    if arm == 'K6U':
        return W / 'K6U-2025-26/out/ranking.csv'
    return W / ('KRU-2025-26' if t == '2025-26' else f'KR-{t}') / 'out/ranking.csv'


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
    """Spearman(屬性, e_net)：F、G、C、全部；e_net＝pct(下季 net×W) − pct(ovr)（E-179 定義）。"""
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
    """季內以球員重抽（各臂共用同一組 idx＝配對）；回 {arm: {key: draws}}，arms 含兩臂時另有 'diff'（KR−K6）。"""
    rng = np.random.default_rng(SEED)
    draws = {a: defaultdict(list) for a in arms}
    if len(arms) == 2:
        draws['diff'] = defaultdict(list)
    for _ in range(B):
        idxs = {t: rng.integers(0, len(data[t]['ids']), len(data[t]['ids'])) for t in HIST}
        pp, _ = pooled_stats(data, idxs, arms)
        for a in arms:
            for k, v in pp[a].items():
                draws[a][k].append(v)
        if len(arms) == 2:
            for k, v in pp[arms[1]].items():
                draws['diff'][k].append(v - pp[arms[0]][k])
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
    """跨季共用球員重抽（同 e153_eval）；回每臂 pooled C 的 draws。"""
    rng = np.random.default_rng(SEED)
    allids = sorted(set().union(*[D[t]['ids'] for t in HIST]))
    pos = {t: {p: i for i, p in enumerate(D[t]['ids'])} for t in HIST}
    res = {a: np.empty(B) for a in arms}
    for b in range(B):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        num = {a: 0.0 for a in arms}
        den = 0.0
        for t in HIST:
            sel = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat(np.array([pos[t][allids[j]] for j in sel]), np.array([mult[j] for j in sel]))
            for a in arms:
                num[a] += len(idx) * P.spearman(D[t]['ovr'][a][idx], D[t]['ref'][idx])
            den += len(idx)
        for a in arms:
            res[a][b] = num[a] / den
    return res


def half(v):
    return float((np.percentile(v, 95) - np.percentile(v, 5)) / 2)


def ci(v):
    return [float(np.percentile(v, 5)), float(np.percentile(v, 95))]


def phase0():
    """只讀 K6 的卡（K6 欄位）；KR 檔不開。"""
    data = {t: season_data(t, ('K6',)) for t in HIST}
    draws = boot_stats(data, ('K6',))['K6']
    full = {t: np.arange(len(data[t]['ids'])) for t in HIST}
    pt, per = pooled_stats(data, full, ('K6',))
    D = c_setup(('K6',))
    cb = c_boot(D, ('K6',))['K6']
    ns = {t: len(D[t]['ids']) for t in HIST}
    cpt = sum(ns[t] * c_metrics(D, t, 'K6')['C'] for t in HIST) / sum(ns.values())
    out = {'n_eval_S': {t: len(data[t]['ids']) for t in HIST},
           'nF': {t: int(np.isin(data[t]['K6']['pos'], list(GROUPS['F'])).sum()) for t in HIST},
           'S_F_creation_K6_pooled': pt['K6']['S_F_creation'], 'S_F_creation_K6_per_season': {t: per['K6'][t]['S_F_creation'] for t in HIST},
           'h_S_F_creation': half(draws['S_F_creation']), 'ci90_S_F_creation': ci(draws['S_F_creation']),
           'n_eval_C': ns, 'C_K6_pooled': cpt, 'h_C': half(cb), 'ci90_C': ci(cb), 'seed': SEED, 'draws': B}
    (W / 'phase0.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


KEY = ['Jalen Williams', 'Jalen Johnson', 'Paolo Banchero', 'Anthony Edwards', 'Franz Wagner', 'Kevin Durant', 'Herbert Jones', 'Dillon Brooks',
       'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Victor Wembanyama', 'Cooper Flagg', 'Kon Knueppel']
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
    prereg_ok = sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().split()[0] and \
        sha(HERE / 'errata-1.md') == (HERE / 'errata-1.sha256').read_text().split()[0]
    c0 = json.loads((HERE / 'phase0.json').read_text(encoding='utf-8'))
    c0_pass = all(v['same'] for v in c0['c0_hist'].values()) and json.loads((W / 'c0-2526.json').read_text())['same']
    # ---- a2 / S ----
    data = {t: season_data(t) for t in HIST}
    full = {t: np.arange(len(data[t]['ids'])) for t in HIST}
    pt, per = pooled_stats(data, full, ARMS)
    dr = boot_stats(data, ARMS)
    S = {k: {'K6': pt['K6'][k], 'KR': pt['KR'][k], 'diff': pt['KR'][k] - pt['K6'][k], 'ci90_K6': ci(dr['K6'][k]), 'ci90_KR': ci(dr['KR'][k]),
             'ci90_diff': ci(dr['diff'][k]), 'per_season_K6': {t: per['K6'][t][k] for t in HIST}, 'per_season_KR': {t: per['KR'][t][k] for t in HIST}}
         for k in pt['K6']}
    a2 = {'diff': S['S_F_creation']['diff'], 'ci90': S['S_F_creation']['ci90_diff'], 'pass': bool(S['S_F_creation']['ci90_diff'][0] > 0)}
    # ---- a1 ----
    rows_by, rk_by = {}, {}
    for a in ('K6', 'KR', 'K6U'):
        rows_by[a], rk_by[a] = rank900(a)
    a1 = {'JW_rank': {a: rk_by[a][JW] for a in rk_by}, 'n900': {a: len(rows_by[a]) for a in rk_by}, 'threshold': 16,
          'pass': bool(rk_by['KR'][JW] >= 16), 'ovr': {a: float(next(r['ovr'] for r in rows_by[a] if r['name'] == JW)) for a in rows_by}}
    # ---- C / b ----
    D = c_setup()
    ns = {t: len(D[t]['ids']) for t in HIST}
    ps = {t: {a: c_metrics(D, t, a) for a in ARMS} for t in SEASONS}

    def pooled_diff(key):
        num = den = 0.0
        for t in HIST:
            nn = ps[t]['KR']['n'] if key == 'C' else ps[t]['KR']['n_' + key]
            num += nn * (ps[t]['KR'][key] - ps[t]['K6'][key])
            den += nn
        return num / den
    od = {k: pooled_diff(k) for k in ('C', 'sal', 'twok', 'rapm')}
    cb = c_boot(D, ARMS)
    h_C = p0['h_C']
    b = {'c0_pass': bool(c0_pass), 'npm_test': '見 report.md／npm_test.log', 'C_diff_pooled': od['C'], 'h_C': h_C, 'floor_minus_2hC': -2 * h_C,
         'C_diff_ci90_info': ci(cb['KR'] - cb['K6']), 'C_pass': bool(od['C'] >= -2 * h_C)}
    # ---- 只報告 ----
    key = {}
    for n in KEY:
        row = {}
        for a in ('K6', 'KR', 'K6U'):
            m = [r for r in rows_by[a] if P.norm(r['name']) == P.norm(n)]
            row[a] = {'rank': rk_by[a][m[0]['name']], 'ovr': float(m[0]['ovr'])} if m else None
        key[n] = row
    top20 = {a: sorted([n for n, k in rk_by[a].items() if k <= 20], key=lambda n: rk_by[a][n]) for a in rk_by}
    top25 = {}
    for a in ('K6', 'KR', 'K6U'):
        for tgt in ('T6', 'T6R'):
            pk = ROOT / 'reports/E142-card-target/phase1-work/cands/T6-2025-26.pkl' if tgt == 'T6' else W / 'cands/T6R-2025-26.pkl'
            top25[f'{a}_vs_{tgt}'] = top25_resid(rows_by[a], rk_by[a], pk)
    moved = {a: sum(1 for n, k in rk_by['K6'].items() if k <= 100 and abs(rk_by[a][n] - k) >= 10) for a in ('KR', 'K6U')}
    res = {'prereg_sha256_ok': bool(prereg_ok), 'seed': SEED, 'draws': B, 'n_eval_S': {t: len(data[t]['ids']) for t in HIST}, 'n_eval_C': ns,
           'a1': a1, 'a2': a2, 'b': b, 'S_stats': S, 'C_per_season': ps, 'C_pooled_diff_KR_minus_K6': od,
           'key_players_2025_26': key, 'top20_2025_26': top20, 'top25_resid_JW': top25, 'moved10_top100_vs_K6': moved,
           'verdict': ('adopt_candidate' if (a1['pass'] and a2['pass'] and b['c0_pass'] and b['C_pass']) else
                       ('a1_pass_a2_fail' if a1['pass'] and not a2['pass'] else 'not_fixed' if not a1['pass'] else 'a1_a2_pass_but_b_fail')),
           'arms': {'K6': 'reports/card-0.2.10/ranking.csv（2025-26）、E-164 S 臂重建（歷史）', 'KR': 'T6R；2025-26＝0.2.10 屬性＋重擬合', 'K6U': '對照：2025-26 T6 重擬合（只報告）'}}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('a1', 'a2', 'b', 'verdict')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    {'phase0': phase0, 'final': final}[sys.argv[1]]()
