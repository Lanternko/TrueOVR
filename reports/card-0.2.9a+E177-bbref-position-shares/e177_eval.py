"""E-177 評估（預註冊 §2 c0／c0h、§3 s0、§4 ①②③ 與只報告項）。口徑：eval_v2 的 ref='old'（薪水 0.4、2K 0.3、下季 RAPM×W 0.15，缺項重分配）。
bootstrap：球員層，三個判定季聯集重抽，2000 次，seed 20261101；①②用同一組重抽。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.9a+E177-bbref-position-shares/e177_eval.py
"""
import csv, hashlib, json, sys, unicodedata, re, html
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import rankdata, spearmanr
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))
sys.path.insert(0, str(ROOT / 'scripts'))
import eval_v2 as V
import season_nav as SN
P = V.P
SEED = 20261101
DRAWS = 2000
SEAS = V.SEASONS
JUDGE = V.JUDGE
POS = ['PG', 'SG', 'SF', 'PF', 'C']
KEY = ['Jalen Williams', 'Jalen Johnson', 'Paolo Banchero', 'Scottie Barnes', 'Franz Wagner', 'Mikal Bridges', 'Josh Hart', 'Draymond Green']
E164 = ROOT / 'reports/card-0.2.9+E164-no-stamina'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref_path(t):
    return ROOT / 'reports/card-0.2.9a/ranking.csv' if t == '2025-26' else E164 / f'ranking-S-{t}.csv'


def out_path(arm, t):
    return HERE / 'work' / f'{arm}-{t}' / 'out' / 'ranking.csv'


def norm(n):
    n = unicodedata.normalize('NFKD', html.unescape(n)).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[.']", '', n)
    n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n)
    return re.sub(r'[^a-z]', '', n)


def boot2(D, a, b, seasons, seed, draws):
    """①C(a)−C(b) 與 ②rapm(a)−rapm(b) 的球員層 bootstrap；①的抽法與 V.boot 相同（同 seed 時結果相同，下面會核對）。"""
    rng = np.random.default_rng(seed)
    sel = {}
    for t in seasons:
        d = D['seasons'][t]
        sel[t] = np.where(~np.isnan(d['ref_old']))[0]
    allids = sorted(set().union(*[{D['seasons'][t]['ids'][i] for i in sel[t]} for t in seasons]))
    pos = {t: {D['seasons'][t]['ids'][i]: i for i in sel[t]} for t in seasons}
    d1 = np.empty(draws); d2 = np.empty(draws)
    for k in range(draws):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        n1 = m1 = n2 = m2 = 0.0
        for t in seasons:
            s = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat(np.array([pos[t][allids[j]] for j in s]), np.array([mult[j] for j in s]))
            d = D['seasons'][t]
            rf = d['ref_old']
            n1 += len(idx) * (P.spearman(d['ovr'][a][idx], rf[idx]) - P.spearman(d['ovr'][b][idx], rf[idx])); m1 += len(idx)
            rp = d['raw']['rapm']
            hv = np.array([i for i in idx if d['ids'][i] in rp], dtype=int)
            if len(hv) >= 10:
                y = [rp[d['ids'][i]] for i in hv]
                n2 += len(hv) * (P.spearman(d['ovr'][a][hv], y) - P.spearman(d['ovr'][b][hv], y)); m2 += len(hv)
        d1[k] = n1 / m1; d2[k] = n2 / m2
    f = lambda x: {'lower90': float(np.percentile(x, 5)), 'upper90': float(np.percentile(x, 95)), 'mean': float(x.mean())}
    return {'C': f(d1), 'rapm': f(d2), 'draws': draws, 'seed': seed}


def team_median(path, name2pid):
    """2025-26 隊內 MIN–OVR Spearman 30 隊中位數（E-082 team_rho：MIN>=100、主隊＝出賽分鐘最多的隊、人數>=6、標準 Spearman）。"""
    pg = json.loads((ROOT / 'data/season-source/player-games.json').read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = pg['headers']
    ip, it, ia, im = (h.index(k) for k in ('PLAYER_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'MIN'))
    tmin = defaultdict(lambda: defaultdict(float)); abbr = {}
    for r in pg['rowSet']:
        abbr[r[it]] = r[ia]
        if r[im]:
            tmin[r[ip]][r[it]] += r[im]
    main = {p: max(sorted(v.items()), key=lambda kv: kv[1])[0] for p, v in tmin.items()}
    by = defaultdict(list)
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        mn = float(r['MIN'])
        pid = name2pid.get(norm(r['name']))
        if mn < 100 or pid is None or pid not in main:
            continue
        by[main[pid]].append((mn, float(r['ovr'])))
    std = {abbr[t]: float(np.corrcoef(rankdata([x[0] for x in v]), rankdata([x[1] for x in v]))[0, 1]) for t, v in by.items() if len(v) >= 6}
    return {'median': float(np.median(sorted(std.values()))), 'n_teams': len(std), 'by_team': std}


def share_coefs(rows, pi):
    """P 下的 OFF／DEF 拆解（E-176 口徑）：pred0 對 [1, x, pi_p(PG..PF), pi_p·x_j(j∈交互項)] 做最小平方，
    球員係數 b_j + Σ_p pi_p·g_pj（和 calibrate 的設計式同構）。回 {playerId: (OFF, DEF)}、最大殘差。"""
    INT = ['long', 'short', 'pass', 'rebound', 'help']
    A = SN.OD_ALL
    X = np.array([[float(r[a]) for a in A] for r in rows])
    PI = np.array([pi[r['playerId']] for r in rows])
    cols = [np.ones(len(rows)), *X.T, *[PI[:, k] for k in range(4)]]
    for k in range(4):
        for a in INT:
            cols.append(PI[:, k] * X[:, A.index(a)])
    M = np.column_stack(cols)
    y = np.array([float(r['pred0']) for r in rows])
    beta = np.linalg.lstsq(M, y, rcond=None)[0]
    resid = float(np.abs(M @ beta - y).max())
    base = {a: beta[1 + j] for j, a in enumerate(A)}
    g = {}
    c = 1 + len(A) + 4
    for k in range(4):
        for a in INT:
            g[(k, a)] = beta[c]; c += 1
    q = [i for i, r in enumerate(rows) if float(r['MIN']) >= 500]
    mu = X[q].mean(0)
    dbm = float(np.mean([float(rows[i]['defenseBonus']) for i in q]))
    out = {}
    for i, r in enumerate(rows):
        co = np.array([base[a] + (sum(PI[i, k] * g[(k, a)] for k in range(4)) if a in INT else 0.0) for a in A])
        cc = co * (X[i] - mu)
        out[r['playerId']] = (round(float(cc[:len(SN.OD_OFF)].sum()), 2),
                              round(float(cc[len(SN.OD_OFF):len(SN.OD_OFF) + len(SN.OD_DEF)].sum()) + float(r['defenseBonus']) - dbm, 2))
    return out, resid


def main():
    res = {'seed': SEED, 'draws': DRAWS}
    # ---- c0 / c0h：S0（比例程式碼餵現行標籤）逐位元重現參考
    c0 = {}
    for t in SEAS:
        a, b = sha(out_path('S0', t)), sha(ref_path(t))
        c0[t] = {'S0_sha': a, 'ref_sha': b, 'ref': ref_path(t).relative_to(ROOT).as_posix(), 'same': a == b}
    res['c0'] = {'2025-26': c0['2025-26']}
    res['c0h'] = {t: c0[t] for t in SEAS[:3]}
    res['c0_pass'] = bool(c0['2025-26']['same']); res['c0h_pass'] = all(c0[t]['same'] for t in SEAS[:3])
    assert res['c0_pass'] and res['c0h_pass'], 'c0／c0h 不符，停（L-026）'
    s0 = json.loads((HERE / 's0_s1.json').read_text(encoding='utf-8'))
    res['s0'] = {'2025-26': {k: s0['2025-26'][k] for k in ('card_MIN500', 'found', 'found_pct', 'usable', 'usable_pct')}, 'pass': bool(s0['s0_pass'])}
    res['s1'] = {t: {k: s0[t][k] for k in ('card_MIN500', 'usable', 'argmax_differs_from_label', 'argmax_differs_pct_of_usable')} for t in SEAS}
    res['selfcheck_JW_2025-26'] = s0['selfcheck_JW_2025-26']
    # ---- 判定
    arms = {'K0': {t: out_path('S0', t) for t in SEAS}, 'P': {t: out_path('P', t) for t in SEAS}}
    D = V.load(arms)
    ps = V.per_season(D, 'old')
    res['n_eval'] = {t: ps[t]['K0']['n'] for t in SEAS}
    res['per_season'] = ps
    bt = boot2(D, 'P', 'K0', JUDGE, SEED, DRAWS)
    bv = V.boot(D, 'P', 'K0', JUDGE, SEED, ref='old')
    res['boot'] = bt
    res['boot_check_vs_V.boot'] = {'lower90_same': abs(bv['lower90'] - bt['C']['lower90']) < 1e-12, 'upper90_same': abs(bv['upper90'] - bt['C']['upper90']) < 1e-12}
    pc, pr = V.pooled(ps, 'P', 'K0', JUDGE, 'C'), V.pooled(ps, 'P', 'K0', JUDGE, 'rapm')
    res['pooled_diff'] = {'C': pc, 'rapm': pr, 'sal': V.pooled(ps, 'P', 'K0', JUDGE, 'sal'), 'twok': V.pooled(ps, 'P', 'K0', JUDGE, 'twok')}
    res['pooled_level'] = {a: {k: V.pooled_level(ps, a, JUDGE, k) for k in ('C', 'sal', 'twok', 'rapm')} for a in ('K0', 'P')}
    # ③
    pop = {}
    d = HERE / 'work/base-P-2025-26/c0/cards/K0/primary/pred.csv'
    for r in csv.DictReader(open(d, encoding='utf-8')):
        pop[norm(r['name'])] = int(r['playerId'])
    t0, tp = team_median(out_path('S0', '2025-26'), pop), team_median(out_path('P', '2025-26'), pop)
    res['t3'] = {'K0': t0['median'], 'P': tp['median'], 'n_teams': tp['n_teams'], 'diff': tp['median'] - t0['median']}
    j1 = bt['C']['lower90'] > -0.01
    j2 = bt['rapm']['lower90'] > -0.02
    j3 = (tp['median'] - t0['median']) >= -0.02
    res['judge'] = {'1_C_lower90_gt_-0.01': bool(j1), '2_rapm_lower90_gt_-0.02': bool(j2), '3_teamMedian_not_below_0.02': bool(j3)}
    res['verdict'] = ('採用候選' if (j1 and j2 and j3) else ('不採用' if not (j1 and j2) else '只有③不過：回報使用者裁定'))
    res['s0_pass_all'] = bool(res['s0']['pass'])
    # ---- 只報告：2025-26
    R = {a: list(csv.DictReader(open(out_path(s, '2025-26'), encoding='utf-8-sig'))) for a, s in (('K0', 'S0'), ('P', 'P'))}
    pidmap = {r['name']: pop.get(norm(r['name'])) for r in R['K0']}
    used = {}
    for r in csv.DictReader(open(HERE / 'work/base-P-2025-26/c0/cards/K0/primary/pos-shares-used.csv', encoding='utf-8')):
        used[r['name']] = r
    big = {a: [r for r in R[a] if float(r['MIN']) >= 500] for a in R}
    rk = {a: {r['name']: i + 1 for i, r in enumerate(sorted(big[a], key=lambda r: -float(r['ovr'])))} for a in R}
    ov = {a: {r['name']: float(r['ovr']) for r in big[a]} for a in R}
    names = [n for n in rk['K0'] if n in rk['P']]
    lab = {r['name']: r['pos'] for r in big['K0']}
    def pil(n):
        u = used.get(n)
        return 1.0 if (u is None or u['used'] == '0') else float(u['pi_' + lab[n]])
    bord = [n for n in names if pil(n) < 0.6]
    def row(n):
        u = used.get(n)
        return {'name': n, 'label': lab[n], 'label_share': round(pil(n), 3), 'pi': None if u is None else [round(float(u['pi_' + p]), 3) for p in POS],
                'K0': [ov['K0'][n], rk['K0'][n]], 'P': [ov['P'][n], rk['P'][n]], 'dOVR': round(ov['P'][n] - ov['K0'][n], 1), 'dRank': rk['K0'][n] - rk['P'][n]}
    res['boundary'] = {'n': len(bord), 'n_pop': len(names), 'top20_by_abs_rank_move': [row(n) for n in sorted(bord, key=lambda n: -abs(rk['K0'][n] - rk['P'][n]))[:20]],
                       'top20_by_abs_ovr_move': [row(n) for n in sorted(bord, key=lambda n: -abs(ov['P'][n] - ov['K0'][n]))[:20]]}
    mv = [abs(ov['P'][n] - ov['K0'][n]) for n in names]
    res['moves_all'] = {'median_abs_dOVR': float(np.median(mv)), 'max_abs_dOVR': float(max(mv)), 'moved10_top300': sum(1 for n in names if rk['K0'][n] <= 300 and abs(rk['P'][n] - rk['K0'][n]) >= 10),
                        'moved10_top100': sum(1 for n in names if rk['K0'][n] <= 100 and abs(rk['P'][n] - rk['K0'][n]) >= 10)}
    top = {a: sorted(rk[a], key=rk[a].get)[:20] for a in R}
    res['top20'] = {'K0': top['K0'], 'P': top['P'], 'in': [n for n in top['P'] if n not in top['K0']], 'out': [n for n in top['K0'] if n not in top['P']]}
    # OFF/DEF 拆解
    pi_by_pid = {}
    for r in R['P']:
        u = used.get(r['name'])
        pid = str(pidmap[r['name']])
        pi_by_pid[pid] = [float(u['pi_' + p]) for p in POS] if u else [1.0 if r['pos'] == p else 0.0 for p in POS]
        r['playerId'] = pid
    for r in R['K0']:
        r['playerId'] = str(pidmap[r['name']])
    od0, bad0 = SN.off_def(R['K0'], 'playerId')
    odp, resid = share_coefs(R['P'], pi_by_pid)
    res['offdef_fit'] = {'K0_unmatched_players': bad0, 'P_max_abs_resid_pred0': resid}
    ex = {}
    for k in KEY:
        n = next((x for x in names if norm(x) == norm(k)), None)
        if n is None:
            ex[k] = None; continue
        pid = str(pidmap[n])
        ex[n] = {**row(n), 'OFF_DEF_K0': list(od0.get(pid, (None, None))), 'OFF_DEF_P': list(odp[pid])}
    res['examples'] = ex
    # E-176：SF／PF 的 pass 與「卡 OFF 名次−外部進攻名次」殘差 Spearman（2025-26 同季，樣本內，只看方向）
    def loadx(f, col):
        return {r['playerId']: float(r[col]) for r in csv.DictReader(open(ROOT / 'data/external-impact' / f, encoding='utf-8-sig')) if r[col] not in ('', None)}
    ext = {'DARKO': loadx('darko/darko_2025-26.csv', 'o_dpm'), 'EPM': loadx('epm_self/epm_2025-26.csv', 'O'), 'OBPM': loadx('bpm/bpm_2025-26.csv', 'obpm')}
    def resid_rho(arm, odd):
        card = [r for r in R[arm] if float(r['MIN']) >= 900]
        ids = [r['playerId'] for r in card if odd.get(r['playerId'], (None, None))[0] is not None and all(r['playerId'] in e for e in ext.values())]
        RR = {r['playerId']: r for r in card}
        off = np.array([odd[i][0] for i in ids])
        z = lambda x: (rankdata(x) - 0.5) / len(x)
        ez = np.mean([z(np.array([ext[k][i] for i in ids])) for k in ext], axis=0)
        rs = ez - z(off)
        if arm == 'P':   # P 下以最大比例位置分組（有比例者）
            grp = np.array([POS[int(np.argmax(pi_by_pid[i]))] for i in ids])
        else:
            grp = np.array([RR[i]['pos'] for i in ids])
        x = np.array([float(RR[i]['pass']) for i in ids])
        return {'n': len(ids), 'rho_OFF_ext': float(spearmanr(off, ez)[0]),
                'pass_vs_resid': {p: {'rho': float(spearmanr(x[grp == p], rs[grp == p])[0]), 'n': int((grp == p).sum())} for p in ('SF', 'PF')},
                'pass_vs_resid_all': float(spearmanr(x, rs)[0])}
    od0_all = od0
    res['e176_resid'] = {'K0': resid_rho('K0', od0_all), 'P': resid_rho('P', odp)}
    res['c1'] = {'npm_test_exit': int((HERE / 'logs/npm-test.exit').read_text().strip()), 'log': 'logs/npm-test.log'}
    res['c1']['pass'] = res['c1']['npm_test_exit'] == 0
    res['prereg_sha256'] = sha(HERE / 'preregistration.md')
    res['prereg_sha256_ok'] = res['prereg_sha256'] == '243341d1283b958f815e5c53b5d076ab1c5fcec26f82c9b80c640b4906c3284b'
    res['thresholds'] = {'1_C_lower90': '> -0.01', '2_rapm_lower90': '> -0.02', '3_team_median_diff': '>= -0.02'}
    res['all_preconditions_pass'] = bool(res['s0']['pass'] and res['c0_pass'] and res['c0h_pass'] and res['c1']['pass'])
    res['sha256'] = {f'{a}-{t}': sha(out_path(s, t)) for a, s in (('K0', 'S0'), ('P', 'P')) for t in SEAS}
    res['pos_shares_sha256'] = {t: sha(HERE / f'pos-shares-{t}.csv') for t in SEAS}
    for t in SEAS:
        for a, s in (('K0', 'S0'), ('P', 'P')):
            (HERE / f'ranking-{a}-{t}.csv').write_bytes(out_path(s, t).read_bytes())
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('c0_pass', 'c0h_pass', 's0', 'boot', 'boot_check_vs_V.boot', 'pooled_diff', 't3', 'judge', 'verdict', 'moves_all', 'offdef_fit')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
