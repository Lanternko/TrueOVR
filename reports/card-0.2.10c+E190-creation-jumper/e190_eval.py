"""E-190 評估（errata-1 判定）。重用 reports/card-0.2.10+E187-t6r-pass-pooled/e187_eval.py 的 C／下季 RAPM ρ 程式（c_setup、c_metrics、c_boot，
跨季共用球員重抽 2000 次，seed 20261101），只把 rpath 換成本目錄的臂；S(drive, 殘差) 照 F-109（reports/E173-pressure-vs-rapm/e173_eval.py）：
e_net＝pct(下季 RAPM net×W(mpg)) − pct(ovr)，MIN≥500、下季 poss≥1000，Spearman，三季人數加權，季內球員重抽。
  phase0：只讀 KAU（KA 歷史原點）→ phase0.json（h_R、KAU 的 S）
  final ：a1／a2／b 與只報告項 → results-final.json
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10c+E190-creation-jumper/e190_eval.py phase0|final"""
import csv, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W = HERE / 'work'


def _load(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


E = _load('e187e', ROOT / 'reports/card-0.2.10+E187-t6r-pass-pooled/e187_eval.py')
E173 = _load('e173e', ROOT / 'reports/E173-pressure-vs-rapm/e173_eval.py')
P = E.P
HIST = E.HIST
SEASONS = E.SEASONS
NEXT = E.NEXT
SEED, B = 20261101, 2000
TAIL_COLS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'creation', 'pressure']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rpath(arm, t):
    if arm == 'KAU':
        return W / ('KAU-2025-26' if t == '2025-26' else f'KA-{t}') / 'out/ranking.csv'
    return W / (f'{arm}U-2025-26' if t == '2025-26' else f'{arm}-{t}') / 'out/ranking.csv'


E.rpath = rpath


def s_data(t, arms):
    pop, _ = P.pop_of(t)
    _, mp_next = P.pop_of(NEXT[t])
    n2 = defaultdict(list)
    for p, i in pop.items():
        n2[P.norm(i['name'])].append(p)
    m = {}
    for a in arms:
        m[a] = {}
        for r in csv.DictReader(open(rpath(a, t), encoding='utf-8-sig')):
            if float(r['MIN']) < 500:
                continue
            ids = n2.get(P.norm(r['name'])) or []
            if len(ids) == 1:
                m[a][ids[0]] = r
    d = json.loads((E.E126 / f'rapm-{NEXT[t]}.json').read_text(encoding='utf-8'))
    assert d['season'] == NEXT[t]
    rv = {int(p): v for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mp_next}
    ids = sorted(p for p in m[arms[0]] if p in rv and all(p in m[a] for a in arms))
    out = {'ids': ids, 'net': np.array([rv[p]['net'] * P.wfun(mp_next[p]) for p in ids])}
    for a in arms:
        rows = [m[a][p] for p in ids]
        out[a] = {k: np.array([float(r[k]) for r in rows]) for k in ('ovr', 'drive', 'creation')}
    return out


def s_stat(d, a, idx):
    e = E173.pct(d['net'][idx]) - E173.pct(d[a]['ovr'][idx])
    return {'S_drive': E173.sp(d[a]['drive'][idx], e), 'S_creation': E173.sp(d[a]['creation'][idx], e)}


def s_all(arms):
    data = {t: s_data(t, arms) for t in HIST}
    ns = {t: len(data[t]['ids']) for t in HIST}
    tot = sum(ns.values())

    def pooled(idxs):
        per = {a: {t: s_stat(data[t], a, idxs[t]) for t in HIST} for a in arms}
        return {a: {k: sum(ns[t] / tot * per[a][t][k] for t in HIST) for k in per[a][HIST[0]]} for a in arms}, per
    pt, per = pooled({t: np.arange(ns[t]) for t in HIST})
    rng = np.random.default_rng(SEED)
    dr = defaultdict(list)
    for _ in range(B):
        pp, _ = pooled({t: rng.integers(0, ns[t], ns[t]) for t in HIST})
        for a in arms:
            for k, v in pp[a].items():
                dr[(a, k)].append(v)
    return data, ns, pt, per, dr


def half(v):
    return float((np.percentile(v, 95) - np.percentile(v, 5)) / 2)


def ci(v):
    return [float(np.percentile(v, 5)), float(np.percentile(v, 95))]


def phase0():
    D = E.c_setup(('KAU',))
    cC, cR = E.c_boot(D, ('KAU',))
    ps = {t: E.c_metrics(D, t, 'KAU') for t in HIST}
    nr = {t: ps[t]['n_rapm'] for t in HIST}
    ns = {t: ps[t]['n'] for t in HIST}
    rpt = sum(nr[t] * ps[t]['rapm'] for t in HIST) / sum(nr.values())
    cpt = sum(ns[t] * ps[t]['C'] for t in HIST) / sum(ns.values())
    _, nS, pt, per, dr = s_all(('KAU',))
    out = {'arm': 'KAU（2025-26＝work/KAU-2025-26、歷史＝work/KA-<季>）', 'seed': SEED, 'draws': B,
           'rapm_rho_KAU_pooled': rpt, 'rapm_rho_KAU_per_season': {t: ps[t]['rapm'] for t in HIST}, 'n_rapm': nr,
           'h_R': half(cR['KAU']), 'floor_R_minus_2hR': -2 * half(cR['KAU']), 'ci90_rapm_rho': ci(cR['KAU']),
           'C_KAU_pooled_info': cpt, 'h_C_info_recomputed': half(cC['KAU']), 'h_C_prereg': 0.045, 'floor_C_prereg': -0.089, 'n_eval_C': ns,
           'S_drive_KAU_pooled': pt['KAU']['S_drive'], 'S_drive_KAU_ci90': ci(dr[('KAU', 'S_drive')]),
           'S_drive_KAU_per_season': {t: per['KAU'][t]['S_drive'] for t in HIST},
           'S_creation_KAU_pooled_info': pt['KAU']['S_creation'], 'n_eval_S': nS,
           'ranking_sha256': {t: sha(rpath('KAU', t)) for t in SEASONS}}
    (HERE / 'work/phase0.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


# ---------------- final ----------------
KEY = ['Jordan Miller', 'Trendon Watford', 'Aaron Holiday', 'Michael Porter Jr.', 'Lauri Markkanen', 'Kristaps Porziņģis', 'Stephen Curry',
       'Shai Gilgeous-Alexander', 'Giannis Antetokounmpo', 'Ja Morant', 'Zion Williamson', 'Jalen Williams', 'LeBron James', 'Nikola Jokić',
       'Anthony Edwards', 'Rudy Gobert', 'Joel Embiid', 'Alperen Sengun', 'Mitchell Robinson']
ARMS = ('KAU', 'KP', 'KJ')


def rank500(arm):
    from scipy.stats import rankdata
    rows = [r for r in csv.DictReader(open(rpath(arm, '2025-26'), encoding='utf-8-sig')) if float(r['MIN']) >= 500]
    rk = rankdata(-np.array([float(r['ovr']) for r in rows]))
    return rows, {r['name']: float(k) for r, k in zip(rows, rk)}


def _vif(X, cols, c):
    ix = cols.index(c)
    y = X[:, ix]
    Z = np.c_[np.ones(len(X)), np.delete(X, ix, axis=1)]
    res = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    r2 = 1 - res.var() / y.var()
    return float(1 / (1 - r2)), float(r2)


def collinearity(arm):
    """2025-26 MIN≥500（該臂 ranking.csv，379 人）。主口徑＝預註冊字面：13 項 tail 屬性（含 physique）＋help、heightInches；
    另報『擬合實際用的 14 欄』（拿掉 physique，--dropAttr physique／stamina）作參考。"""
    rows, _ = rank500(arm)
    out = {'n': len(rows)}
    for tag, cols in (('prereg_13tail_help_height', TAIL_COLS + ['help', 'heightInches']),
                      ('fit_cols_info', [c for c in TAIL_COLS if c != 'physique'] + ['help', 'heightInches'])):
        X = np.array([[float(r[c]) for c in cols] for r in rows])
        vd, r2 = _vif(X, cols, 'drive')
        vc, _ = _vif(X, cols, 'creation')
        out[tag] = {'VIF_drive': vd, 'R2_drive': r2, 'VIF_creation': vc}
    out['r_drive_creation'] = float(np.corrcoef([float(r['drive']) for r in rows], [float(r['creation']) for r in rows])[0, 1])
    out['VIF_drive'] = out['prereg_13tail_help_height']['VIF_drive']
    return out


def coefs(arm):
    """OVR 層 primary 部件（calibrate_wing_t summary.json）valuePer10AttributePoints：每 10 點、每 36 分，SE＝校準內建 bootstrap。"""
    o = {}
    for t in SEASONS:
        nm = (f'{arm}U' if arm != 'KAU' else 'KAU') if t == '2025-26' else ('KA' if arm == 'KAU' else arm)
        d = W / f'base-{nm}-{t}' / ('c0' if t == '2025-26' else t) / 'cards/K0/primary/summary.json'
        v = json.loads(d.read_text(encoding='utf-8'))['valuePer10AttributePoints']
        o[t] = {k: v[k] for k in ('drive', 'creation', 'pass', 'short')}
    return o


def final():
    prereg_ok = sha(HERE / 'errata-1.md') == (HERE / 'errata-1.sha256').read_text().split()[0]
    p0 = json.loads((W / 'phase0.json').read_text(encoding='utf-8'))
    # a1
    a1 = {a: collinearity(a) for a in ARMS}
    a1['pass'] = bool(a1['KJ']['r_drive_creation'] <= 0.70 and a1['KJ']['VIF_drive'] <= 3.0)
    # a2
    _, nS, pt, per, dr = s_all(ARMS)
    dJP = np.array(dr[('KJ', 'S_drive')]) - np.array(dr[('KP', 'S_drive')])
    dPA = np.array(dr[('KP', 'S_drive')]) - np.array(dr[('KAU', 'S_drive')])
    a2 = {'S_drive': {a: pt[a]['S_drive'] for a in ARMS}, 'S_drive_per_season': {a: {t: per[a][t]['S_drive'] for t in HIST} for a in ARMS},
          'S_creation_info': {a: pt[a]['S_creation'] for a in ARMS}, 'n_eval': nS,
          'diff_KJ_minus_KP': pt['KJ']['S_drive'] - pt['KP']['S_drive'], 'ci90_KJ_minus_KP_info': ci(dJP), 'threshold': 0.05,
          'diff_KP_minus_KAU_info': pt['KP']['S_drive'] - pt['KAU']['S_drive'], 'ci90_KP_minus_KAU_info': ci(dPA),
          'diff_KJ_minus_KAU_info': pt['KJ']['S_drive'] - pt['KAU']['S_drive']}
    a2['pass'] = bool(a2['diff_KJ_minus_KP'] >= 0.05)
    # b
    D = E.c_setup(ARMS)
    ps = {t: {a: E.c_metrics(D, t, a) for a in ARMS} for t in SEASONS}

    def pooled_diff(key, arm, base='KAU'):
        num = den = 0.0
        for t in HIST:
            nn = ps[t][arm]['n'] if key == 'C' else ps[t][arm]['n_' + key]
            num += nn * (ps[t][arm][key] - ps[t][base][key])
            den += nn
        return num / den
    od = {a: {k: pooled_diff(k, a) for k in ('C', 'sal', 'twok', 'rapm')} for a in ('KP', 'KJ')}
    cC, cR = E.c_boot(D, ARMS)
    b = {'C_diff_KJ_minus_KAU': od['KJ']['C'], 'floor_C': -0.089, 'C_pass': bool(od['KJ']['C'] >= -0.089), 'C_ci90_info': ci(cC['KJ'] - cC['KAU']),
         'R_diff_KJ_minus_KAU': od['KJ']['rapm'], 'h_R': p0['h_R'], 'floor_R': -2 * p0['h_R'], 'R_pass': bool(od['KJ']['rapm'] >= -2 * p0['h_R']),
         'R_ci90_info': ci(cR['KJ'] - cR['KAU']), 'npm_test': 'logs/npm_test.log', 'c0': 'KAU 逐位元、舊 drive U 0.0／V 2.8e-14'}
    # 只報告
    rk = {a: rank500(a) for a in ARMS}
    key = {}
    for n in KEY:
        row = {}
        for a in ARMS:
            rows, r = rk[a]
            m = [x for x in rows if P.norm(x['name']) == P.norm(n)]
            row[a] = {'rank': r[m[0]['name']], 'ovr': float(m[0]['ovr']), 'drive': float(m[0]['drive']), 'creation': float(m[0]['creation'])} if m else None
        key[n] = row
    moved = {a: sum(1 for n, k in rk['KAU'][1].items() if k <= 100 and n in rk[a][1] and abs(rk[a][1][n] - k) >= 10) for a in ('KP', 'KJ')}
    top20 = {a: sorted([n for n, k in rk[a][1].items() if k <= 20], key=lambda n: rk[a][1][n]) for a in ARMS}
    # F-118 傳球偏差（S_all_pass 等，E-187 stat 口徑）、JW（F-125 護欄：MIN≥900 名次、前 25 名對 T6 分段殘差）
    sd = {t: E.season_data(t, ARMS) for t in HIST}
    spt, sper = E.pooled_stats(sd, {t: np.arange(len(sd[t]['ids'])) for t in HIST}, ARMS)
    sdr = E.boot_stats(sd, ARMS)
    f118 = {k: {a: spt[a][k] for a in ARMS} | {f'ci90_{a}_minus_KAU': ci(sdr['diff_' + a][k]) for a in ARMS[1:]} for k in spt['KAU']}
    jw = {}
    for a in ARMS:
        rows9, rk9 = E.rank900(a)
        jw[a] = {'rank_MIN900': rk9[E.JW], 'n900': len(rows9),
                 'top25_vs_T6': E.top25_resid(rows9, rk9, E.E142 / 'phase1-work/cands/T6-2025-26.pkl')}
    co = {a: coefs(a) for a in ARMS}
    res = {'F118_S_stats': f118, 'JW': jw, 'coef_per10': co, 'errata1_sha256_ok': prereg_ok, 'seed': SEED, 'draws': B, 'a1': a1, 'a2': a2, 'b': b,
           'C_per_season': ps, 'pooled_diff_vs_KAU': od, 'key_players_2025_26_MIN500': key, 'moved10_top100_vs_KAU': moved, 'top20': top20,
           'ranking_sha256': {a: {t: sha(rpath(a, t)) for t in SEASONS} for a in ARMS}}
    (W / 'results-final.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('a1', 'a2', 'b', 'pooled_diff_vs_KAU', 'moved10_top100_vs_KAU', 'coef_per10')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    {'phase0': phase0, 'final': final}[sys.argv[1]]()
