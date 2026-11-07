"""E-194（F-133 診斷）：切入型球員被高估從哪來。定義見 diag_plan.md（跑前凍結）。
用法（repo root）：python -I -B -X utf8 reports/F133-drive-scoring/diag.py   → results.json
只讀 E-190 的 work/；不改卡、不提採用。"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E190 = ROOT / 'reports/card-0.2.10c+E190-creation-jumper'
SEED, B, NFOLD, LAM = 20261101, 2000, 10, 1.0
A14 = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'onBall', 'help', 'heightInches', 'creation', 'pressure']
POS4 = ['PG', 'SG', 'SF', 'PF']
INT4 = ['long', 'short', 'rebound', 'help']
ID = A14.index('drive')
KEY15 = ['Jordan Miller', 'Trendon Watford', 'Aaron Holiday', 'Michael Porter Jr.', 'Lauri Markkanen', 'Kristaps Porziņģis', 'Stephen Curry',
         'Shai Gilgeous-Alexander', 'Giannis Antetokounmpo', 'Ja Morant', 'Zion Williamson', 'Jalen Williams', 'LeBron James', 'Nikola Jokić',
         'Anthony Edwards']


def _load(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


M = _load('e190e', E190 / 'e190_eval.py')
E173, P, HIST = M.E173, M.P, M.HIST
W = E190 / 'work'


def pct(x):
    return rankdata(np.asarray(x, float)) / len(x)


def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def rcov(x, y):
    return float(np.cov(rankdata(x), y, ddof=0)[0, 1])


def ci(v):
    v = np.asarray(v, float)
    return [float(np.nanpercentile(v, 5)), float(np.nanpercentile(v, 95))]


# ---------------- 資料 ----------------
def load_season(t):
    d = M.s_data(t, ('KJ',))
    ids = d['ids']
    pop, _ = P.pop_of(t)
    base = W / f'base-KJ-{t}' / t
    t6 = {int(r['playerId']): float(r['pooledNet']) for r in csv.DictReader(open(base / 'rapm-R.csv', encoding='utf-8-sig'))}
    summ = json.loads((base / 'cards/K0/primary/summary.json').read_text(encoding='utf-8'))
    f = summ['formula']
    # ranking.csv 與 s_data 同一批（以名字對 id，同 s_data 的規則）
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    rows = {}
    for r in csv.DictReader(open(M.rpath('KJ', t), encoding='utf-8-sig')):
        if float(r['MIN']) < 500:
            continue
        c = n2.get(P.norm(r['name'])) or []
        if len(c) == 1:
            rows[c[0]] = r
    rr = [rows[p] for p in ids]
    n = len(ids)
    X = np.array([[float(r[a]) for a in A14] for r in rr])
    mean = np.array([f['attributeMean'][a] for a in A14])
    sd = np.array([f['attributeSD'][a] for a in A14])
    z = (X - mean) / sd
    b = np.array(f['coefficientsOnStandardized'])
    assert len(b) == 14 + 16
    pos = np.array([r['pos'] for r in rr])
    # 逐人逐欄係數（含位置交互）→ per36 貢獻
    beta = np.tile(b[:14], (n, 1))
    des = [z]
    for k, p in enumerate(POS4):
        isp = (pos == p).astype(float)[:, None]
        zi = z[:, [A14.index(a) for a in INT4]]
        des.append(isp * zi)
        for m_, a in enumerate(INT4):
            beta[:, A14.index(a)] += (pos == p) * b[14 + 4 * k + m_]
    c36 = beta * z
    pred0_re = f['intercept'] + c36.sum(1)
    pred0_err = float(np.max(np.abs(pred0_re - np.array([float(r['pred0']) for r in rr]))))
    anc = summ['scaleAnchorsPer36']
    slope = 29.0 / (anc['PR99'] - anc['PR50'])
    return {'t': t, 'ids': ids, 'n': n, 'names': [r['name'] for r in rr], 'pos': pos, 'net': d['net'], 'ovr': d['KJ']['ovr'],
            'drive': d['KJ']['drive'], 'creation': d['KJ']['creation'], 'drive_row': np.array([float(r['drive']) for r in rr]),
            't6': np.array([t6.get(p, np.nan) for p in ids]), 'c36': c36, 'cov': c36 * slope, 'slope': slope,
            'design': np.hstack(des), 'sd_drive': float(sd[ID]), 'pred0_err': pred0_err,
            'card_drive_per10_per36': summ['valuePer10AttributePoints']['drive']['per36']}


# ---------------- 迴歸 ----------------
def ridge(X, y):
    A = np.c_[np.ones(len(X)), X]
    pen = LAM * np.eye(A.shape[1])
    pen[0, 0] = 0
    return np.linalg.solve(A.T @ A + pen, A.T @ y)


def predict(b, X):
    return np.c_[np.ones(len(X)), X] @ b


def cv_pred(X, y, folds, keep):
    out = np.empty(len(y))
    for k in range(NFOLD):
        te = folds == k
        if not te.any():
            continue
        b = ridge(X[~te][:, keep], y[~te])
        out[te] = predict(b, X[te][:, keep])
    return out


# ---------------- 統計 ----------------
def stats(d, idx, folds, detail=False):
    """回傳 (full, sub)：full＝整個 a2 人群上的量，sub＝有 t6net 的子群上的量。idx＝球員重抽（原順序＝arange）。"""
    net, ovr, drive, t6 = d['net'][idx], d['ovr'][idx], d['drive'][idx], d['t6'][idx]
    X, cov, fo = d['design'][idx], d['cov'][idx], folds[idx]
    pn, po = pct(net), pct(ovr)
    e_net = pn - po
    full, sub = {}, {}
    full['S_drive_enet'] = sp(drive, e_net)
    # D3：下季 RAPM／卡 ovr 迴歸（整個人群）
    allc = np.arange(X.shape[1])
    keep_nd = np.array([c for c in allc if c != ID])
    full_y = {'net': pn, 'ovr': po}
    for nm, y in full_y.items():
        b = ridge(X, y)
        full[f'drive10_{nm}'] = float(b[1 + ID] / d['sd_drive'] * 10 * 100)
    pr_all = predict(ridge(X, pn), X)
    pr_nd = predict(ridge(X[:, keep_nd], pn), X[:, keep_nd])
    cv_all = cv_pred(X, pn, fo, allc)
    cv_nd = cv_pred(X, pn, fo, keep_nd)
    full['rho_in_with'], full['rho_in_without'] = sp(pr_all, net), sp(pr_nd, net)
    full['rho_cv_with'], full['rho_cv_without'] = sp(cv_all, net), sp(cv_nd, net)
    full['d_rho_in'] = full['rho_in_without'] - full['rho_in_with']
    full['d_rho_cv'] = full['rho_cv_without'] - full['rho_cv_with']
    full['rho_card_ovr'] = sp(ovr, net)
    # D2（整個人群）：c_j 與 drive
    top = drive >= np.percentile(drive, 75)
    for j, a in enumerate(A14):
        full[f'sp_c_{a}'] = sp(drive, cov[:, j])
        full[f'top_minus_rest_c_{a}'] = float(cov[top, j].mean() - cov[~top, j].mean())
    full['top_minus_rest_sum_c'] = float(cov.sum(1)[top].mean() - cov.sum(1)[~top].mean())
    full['top_minus_rest_ovr'] = float(ovr[top].mean() - ovr[~top].mean())
    full['top_minus_rest_enet'] = float(e_net[top].mean() - e_net[~top].mean())
    # 子群（有 t6net）
    ok = ~np.isnan(t6)
    if ok.sum() > 10:
        ds, ts = drive[ok], t6[ok]
        pt6 = pct(ts)
        en, ef, et = e_net[ok], pt6 - po[ok], pn[ok] - pt6
        sub['S_drive_enet'] = sp(ds, en)
        sub['S_drive_etarget'] = sp(ds, et)
        sub['S_drive_efit'] = sp(ds, ef)
        cn, ct, cf = rcov(ds, en), rcov(ds, et), rcov(ds, ef)
        sub['cov_enet'], sub['cov_etarget'], sub['cov_efit'] = cn, ct, cf
        sub['top_minus_rest_efit'] = float(ef[top[ok]].mean() - ef[~top[ok]].mean())
        sub['top_minus_rest_etarget'] = float(et[top[ok]].mean() - et[~top[ok]].mean())
        b = ridge(X[ok], pt6)
        sub['drive10_t6'] = float(b[1 + ID] / d['sd_drive'] * 10 * 100)
        if detail:
            sub['_identity_maxdiff'] = float(np.max(np.abs(et + ef - en)))
            sub['_e_target'], sub['_e_fit'] = et, ef
            sub['_ok'] = ok
    return full, sub


def pooled(per, ns, kind):
    out = {}
    tot = sum(ns[t] for t in HIST)
    for k in per[HIST[0]][kind]:
        if k.startswith('_'):
            continue
        out[k] = sum(ns[t] / tot * per[t][kind][k] for t in HIST)
    return out


def run():
    data = {t: load_season(t) for t in HIST}
    ns = {t: data[t]['n'] for t in HIST}
    # 閘門
    e190 = json.loads((W / 'results-final.json').read_text(encoding='utf-8'))
    assert ns == e190['a2']['n_eval'], (ns, e190['a2']['n_eval'])
    for t in HIST:
        assert data[t]['pred0_err'] < 0.02, (t, data[t]['pred0_err'])
    rng0 = np.random.default_rng(SEED)
    folds = {t: rng0.permutation(np.arange(ns[t]) % NFOLD) for t in HIST}
    per = {}
    for t in HIST:
        f, s = stats(data[t], np.arange(ns[t]), folds[t], detail=True)
        per[t] = {'full': f, 'sub': s}
    ns_sub = {t: int((~np.isnan(data[t]['t6'])).sum()) for t in HIST}
    gate_S = sum(ns[t] / sum(ns.values()) * per[t]['full']['S_drive_enet'] for t in HIST)
    assert abs(gate_S - e190['a2']['S_drive']['KJ']) < 1e-9, (gate_S, e190['a2']['S_drive']['KJ'])
    ident = max(per[t]['sub']['_identity_maxdiff'] for t in HIST)
    assert ident < 1e-9, ident
    PF, PS = pooled(per, ns, 'full'), pooled(per, ns_sub, 'sub')
    PS['share_target'] = PS['cov_etarget'] / PS['cov_enet']
    PS['share_fit'] = PS['cov_efit'] / PS['cov_enet']
    # bootstrap
    rng = np.random.default_rng(SEED)
    drF, drS = {}, {}
    for _ in range(B):
        pb = {}
        for t in HIST:
            idx = rng.integers(0, ns[t], ns[t])
            f, s = stats(data[t], idx, folds[t])
            pb[t] = {'full': f, 'sub': s}
        bf = pooled(pb, ns, 'full')
        bs = pooled(pb, ns_sub, 'sub')
        bs['share_target'] = bs['cov_etarget'] / bs['cov_enet']
        bs['share_fit'] = bs['cov_efit'] / bs['cov_enet']
        bf['drive10_net_minus_t6'] = bf['drive10_net'] - bs['drive10_t6']
        for k, v in bf.items():
            drF.setdefault(k, []).append(v)
        for k, v in bs.items():
            drS.setdefault(k, []).append(v)
        for t in HIST:
            for k, v in pb[t]['sub'].items():
                drS.setdefault(f'{t}|{k}', []).append(v)
            for k, v in pb[t]['full'].items():
                drF.setdefault(f'{t}|{k}', []).append(v)
    pf_extra = {'drive10_net_minus_t6': PF['drive10_net'] - PS['drive10_t6']}

    def summ(point, dr, keys=None):
        o = {}
        for k in (keys or point):
            o[k] = {'point': point[k], 'ci90': ci(dr[k]), 'se': float(np.std(dr[k]))}
        return o
    D1 = {'n_full': ns, 'n_t6_subset': ns_sub, 'identity_maxdiff': ident,
          'pooled': summ(PS, drS, ['S_drive_enet', 'S_drive_etarget', 'S_drive_efit', 'share_target', 'share_fit']),
          'per_season': {t: {k: per[t]['sub'][k] for k in ('S_drive_enet', 'S_drive_etarget', 'S_drive_efit', 'cov_enet', 'cov_etarget', 'cov_efit')} |
                         {'share_target': per[t]['sub']['cov_etarget'] / per[t]['sub']['cov_enet']} for t in HIST},
          'per_season_ci90': {t: {k: ci(drS[f'{t}|{k}']) for k in ('S_drive_etarget', 'S_drive_efit', 'S_drive_enet')} for t in HIST},
          'S_drive_enet_full_pop': summ(PF, drF, ['S_drive_enet']),
          'S_drive_enet_full_per_season': {t: per[t]['full']['S_drive_enet'] for t in HIST},
          'gate_matches_E190_a2_KJ': e190['a2']['S_drive']['KJ']}
    D2 = {'slope_ovr_per_per36': {t: data[t]['slope'] for t in HIST}, 'pred0_recon_maxabs_err': {t: data[t]['pred0_err'] for t in HIST},
          'by_attr': {a: {'sp_drive_c': summ(PF, drF, [f'sp_c_{a}'])[f'sp_c_{a}'],
                          'top25_minus_rest_c_ovr': summ(PF, drF, [f'top_minus_rest_c_{a}'])[f'top_minus_rest_c_{a}']} for a in A14},
          'top25_minus_rest': summ(PF, drF, ['top_minus_rest_sum_c', 'top_minus_rest_ovr', 'top_minus_rest_enet']) |
          summ(PS, drS, ['top_minus_rest_efit', 'top_minus_rest_etarget'])}
    D2['top3_attrs'] = sorted(A14, key=lambda a: -PF[f'top_minus_rest_c_{a}'])[:3]
    D2['unexplained_ovr_diff_minus_sum_c'] = PF['top_minus_rest_ovr'] - PF['top_minus_rest_sum_c']
    D2['per_season_top25_minus_rest_c'] = {t: {a: per[t]['full'][f'top_minus_rest_c_{a}'] for a in A14} for t in HIST}
    card10 = sum(ns[t] / sum(ns.values()) * data[t]['card_drive_per10_per36'] for t in HIST)
    D3 = {'unit': '百分位分（pct×100）／drive 每 10 點', 'method': 'ridge λ=1、位置交互、單位權重、14 欄、z 用 KJ formula mean/SD',
          'pooled': {'drive10_net': summ(PF, drF, ['drive10_net'])['drive10_net'], 'drive10_t6': summ(PS, drS, ['drive10_t6'])['drive10_t6'],
                     'drive10_ovr': summ(PF, drF, ['drive10_ovr'])['drive10_ovr'],
                     'drive10_net_minus_t6': {'point': pf_extra['drive10_net_minus_t6'], 'ci90': ci(drF['drive10_net_minus_t6']), 'se': float(np.std(drF['drive10_net_minus_t6']))}},
          'per_season': {t: {'net': per[t]['full']['drive10_net'], 't6': per[t]['sub']['drive10_t6'], 'ovr': per[t]['full']['drive10_ovr'],
                             'net_se': float(np.std(drF[f'{t}|drive10_net'])), 't6_se': float(np.std(drS[f'{t}|drive10_t6']))} for t in HIST},
          'card_KJ_drive_per10_per36_pooled': card10, 'card_KJ_drive_per10_ovr_pts_approx': card10 * float(np.mean([data[t]['slope'] for t in HIST])),
          'card_KJ_drive_per10_per_season_per36': {t: data[t]['card_drive_per10_per36'] for t in HIST},
          'independent_info': {k: summ(PF, drF, [k])[k] for k in ('rho_cv_with', 'rho_cv_without', 'd_rho_cv', 'rho_in_with', 'rho_in_without', 'd_rho_in', 'rho_card_ovr')},
          'd_rho_per_season': {t: {'cv': per[t]['full']['d_rho_cv'], 'in': per[t]['full']['d_rho_in']} for t in HIST}}
    # 球員表
    tops = sorted(((float(data[t]['drive'][i]), t, i) for t in HIST for i in range(ns[t])), key=lambda x: -x[0])[:10]
    top3 = D2['top3_attrs']
    rows = []

    def prow(t, i, tag):
        d = data[t]
        s = per[t]['sub']
        ok = s['_ok']
        # 子群內位置 → 取 e_target／e_fit
        e_t = e_f = None
        if ok[i]:
            k = int(ok[:i].sum())
            e_t, e_f = float(s['_e_target'][k]), float(s['_e_fit'][k])
        e_net = float(pct(d['net'])[i] - pct(d['ovr'])[i])
        r = {'tag': tag, 'season': t, 'name': d['names'][i], 'pos': str(d['pos'][i]), 'drive': float(d['drive'][i]), 'creation': float(d['creation'][i]), 'ovr': float(d['ovr'][i]),
             'e_net': e_net, 'e_target': e_t, 'e_fit': e_f}
        for a in top3:
            r[f'c_{a}'] = float(d['cov'][i, A14.index(a)])
        rows.append(r)
    absent = []
    for nm in KEY15:
        hit = False
        for t in HIST:
            for i, n_ in enumerate(data[t]['names']):
                if P.norm(n_) == P.norm(nm):
                    prow(t, i, 'E190-15')
                    hit = True
        if not hit:
            absent.append(nm)
    for v, t, i in tops:
        prow(t, i, 'drive-top10')
    res = {'definition': 'diag_plan.md', 'seed': SEED, 'draws': B, 'attrs': A14, 'D1': D1, 'D2': D2, 'D3': D3,
           'players': rows, 'key15_absent_from_population': absent,
           'checks': {'n_equals_E190_a2': True, 'identity_maxdiff_lt_1e-9': ident, 'pred0_recon_ok': True, 'gate_S_drive_KJ_pooled': gate_S},
           'input_sha256': {t: hashlib.sha256(Path(M.rpath('KJ', t)).read_bytes()).hexdigest() for t in HIST} |
           {'results-final.json': hashlib.sha256((W / 'results-final.json').read_bytes()).hexdigest()}}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True, default=float), encoding='utf-8')
    print('D1', json.dumps(D1['pooled'], ensure_ascii=False, default=float))
    print('top3', top3, 'n', ns, ns_sub, 'ident', ident)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    run()
