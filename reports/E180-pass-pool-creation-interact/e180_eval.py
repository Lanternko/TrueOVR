"""E-180 評估：預註冊 preregistration.md（凍結 sha 見 preregistration.sha256）。
§2a：c0／c0h、s1（2025-26，薪水 errata-1 權重 Spearman、2K Spearman，A−K0 球員層 bootstrap）、s2（隊內 MIN–OVR）、npm test。
§2b：2024-25 原點卡（K0h／Ah）對 2025-26 RAPM（net×W、O×W），E-179 的人群／pct／e_net／bootstrap 寫法；p0、①、②。
§3 與只報告項：全部列在 results.json。
用法（repo root）：python -I -B -X utf8 reports/E180-pass-pool-creation-interact/e180_eval.py
"""
import csv, hashlib, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))
sys.path.insert(0, str(ROOT / 'scripts'))
import eval_v2 as V
import season_nav as SN
P = V.P
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
E177 = ROOT / 'reports/card-0.2.9a+E177-bbref-position-shares'
PREREG_SHA = '50b34a14204267a6d854e345e60222170bea35e024e5342024bda4c2db423533'
SEED, B = 20261101, 2000
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
ORIG = SEAS[:3]
NEXT = {'2022-23': '2023-24', '2023-24': '2024-25', '2024-25': '2025-26'}
JUDGE_T = '2024-25'
ATTRS = ['pass', 'creation', 'foulDraw']
GROUPS = {'F': {'SF', 'PF'}, 'G': {'PG', 'SG'}, 'C': {'C'}}
EXAMPLES = ['Jalen Williams', 'Jalen Johnson', 'Paolo Banchero', 'Scottie Barnes', 'Franz Wagner', 'LeBron James']
ARMS = ('K0', 'A')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rk(t, arm):
    return HERE / f'ranking-{arm}-{t}.csv'


def pct(x):
    return rankdata(x) / len(x)


def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1]) if len(x) > 2 else np.nan


def ci(x):
    return [float(np.nanpercentile(x, 5)), float(np.nanpercentile(x, 95))]


def load_card(path):
    return list(csv.DictReader(open(path, encoding='utf-8-sig')))


def off_def_card(card):
    """season_nav.off_def 的做法套在該季卡片內：依位置把 pred0 回歸到 OD_ALL；回 {name: (OFF, DEF)}、{pos: coef}、pred0 誤差 > 0.02 的比例、最大誤差。"""
    coef = {}
    for ps in {r['pos'] for r in card}:
        g = [r for r in card if r['pos'] == ps]
        X = np.c_[np.ones(len(g)), [[float(r[a]) for a in SN.OD_ALL] for r in g]]
        coef[ps] = np.linalg.lstsq(X, np.array([float(r['pred0']) for r in g]), rcond=None)[0]
    q = [r for r in card if float(r['MIN']) >= 500]
    mu = np.array([np.mean([float(r[a]) for r in q]) for a in SN.OD_ALL])
    dbm = float(np.mean([float(r['defenseBonus']) for r in q]))
    no, nd = len(SN.OD_OFF), len(SN.OD_DEF)
    out, bad, mx = {}, 0, 0.0
    for r in q:
        b = coef[r['pos']]
        x = np.array([float(r[a]) for a in SN.OD_ALL])
        e = abs(b[0] + b[1:] @ x - float(r['pred0']))
        bad += e > 0.02; mx = max(mx, e)
        c = b[1:] * (x - mu)
        out[r['name']] = (float(c[:no].sum()), float(c[no:no + nd].sum()) + float(r['defenseBonus']) - dbm)
    return out, coef, bad / len(q), mx


def team_median(path, name2pid):
    """2025-26 隊內 MIN–OVR Spearman 30 隊中位數（E-082 team_rho：MIN>=100、主隊＝出賽分鐘最多的隊、人數>=6）。"""
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
    for r in load_card(path):
        mn = float(r['MIN'])
        pid = name2pid.get(P.norm(r['name']))
        if mn < 100 or pid is None or pid not in main:
            continue
        by[main[pid]].append((mn, float(r['ovr'])))
    std = {abbr[t]: float(np.corrcoef(rankdata([x[0] for x in v]), rankdata([x[1] for x in v]))[0, 1]) for t, v in by.items() if len(v) >= 6}
    return {'median': float(np.median(sorted(std.values()))), 'n_teams': len(std), 'by_team': std}


# ---------------------------------------------------------------- 2a
def s1(res):
    paths = {a: {'2025-26': rk('2025-26', a)} for a in ARMS}
    D = V.load(paths, seasons=['2025-26'])
    d = D['seasons']['2025-26']
    ok = np.where(~np.isnan(d['ref_old']))[0]     # E-177 口徑 ref='old'
    full = {a: V.metrics(D, '2025-26', a, 'old', ok) for a in ARMS}
    rng = np.random.default_rng(SEED)
    ds, dk = np.empty(B), np.empty(B)
    for k in range(B):
        idx = ok[rng.integers(0, len(ok), len(ok))]
        m = {a: V.metrics(D, '2025-26', a, 'old', idx) for a in ARMS}
        ds[k] = m['A']['sal'] - m['K0']['sal']
        dk[k] = m['A']['twok'] - m['K0']['twok']
    out = {'n_eval': int(len(ok)), 'K0': {k: full['K0'][k] for k in ('n_sal', 'sal', 'n_twok', 'twok', 'C')},
           'A': {k: full['A'][k] for k in ('n_sal', 'sal', 'n_twok', 'twok', 'C')},
           'diff_sal': full['A']['sal'] - full['K0']['sal'], 'diff_twok': full['A']['twok'] - full['K0']['twok'],
           'ci90_sal': ci(ds), 'ci90_twok': ci(dk), 'seed': SEED, 'draws': B}
    out['pass_sal'] = bool(out['ci90_sal'][0] > -0.01)
    out['pass_twok'] = bool(out['ci90_twok'][0] > -0.01)
    out['pass'] = out['pass_sal'] and out['pass_twok']
    return out


def s2():
    pop = {}
    for r in csv.DictReader(open(HERE / 'work/base-K0-2025-26/c0/cards/K0/primary/pred.csv', encoding='utf-8')):
        pop[P.norm(r['name'])] = int(r['playerId'])
    t0, ta = team_median(rk('2025-26', 'K0'), pop), team_median(rk('2025-26', 'A'), pop)
    return {'K0': t0['median'], 'A': ta['median'], 'n_teams': ta['n_teams'], 'diff': ta['median'] - t0['median'],
            'pass': bool(ta['median'] - t0['median'] >= -0.02)}, pop


# ---------------------------------------------------------------- 2b
def origin_data(t):
    """K0h／Ah 的原點卡 vs 下季 RAPM（E-179 season_data 的寫法，卡換成本實驗兩臂；人群與分組用 K0h 的 MIN、pos）。"""
    cards = {a: load_card(rk(t, a)) for a in ARMS}
    byname = {a: {r['name']: r for r in cards[a]} for a in ARMS}
    off = {a: off_def_card(cards[a]) for a in ARMS}
    pop, _ = P.pop_of(t)
    _, mp_next = P.pop_of(NEXT[t])
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    m = {}
    for r in cards['K0']:
        if float(r['MIN']) < 500:
            continue
        ids = n2.get(P.norm(r['name'])) or []
        if len(ids) == 1:
            m[ids[0]] = r
    d = json.loads((E126 / f'rapm-{NEXT[t]}.json').read_text(encoding='utf-8'))
    assert d['season'] == NEXT[t]
    rv = {int(p): v for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mp_next}
    ids = sorted(p for p in m if p in rv)
    rows = [m[p] for p in ids]
    names = [r['name'] for r in rows]
    W = np.array([P.wfun(mp_next[p]) for p in ids])
    out = {'ids': ids, 'names': names, 'pos': np.array([r['pos'] for r in rows]),
           'net': np.array([rv[p]['net'] for p in ids]) * W, 'O': np.array([rv[p]['O'] for p in ids]) * W, 'ovr': {}, 'off': {}}
    for a in ARMS:
        rr = [byname[a][n] for n in names]
        assert [r['pos'] for r in rr] == [r['pos'] for r in rows], '兩臂 pos 標籤不同'
        out['ovr'][a] = np.array([float(r['ovr']) for r in rr])
        out['off'][a] = np.array([off[a][0][n][0] for n in names])
    for k in ATTRS:   # 能力值兩臂應完全相同
        v0 = np.array([float(byname['K0'][n][k]) for n in names]); v1 = np.array([float(byname['A'][n][k]) for n in names])
        assert np.array_equal(v0, v1), f'{k} 兩臂能力值不同'
        out[k] = v0
    out['n'] = len(ids)
    out['nF'] = int(np.isin(out['pos'], list(GROUPS['F'])).sum()); out['nG'] = int(np.isin(out['pos'], list(GROUPS['G'])).sum())
    out['off_bad'] = {a: off[a][2] for a in ARMS}
    return out


def stats(d, idx, arm):
    e_net = pct(d['net'][idx]) - pct(d['ovr'][arm][idx])
    e_O = pct(d['O'][idx]) - pct(d['off'][arm][idx])
    pos = d['pos'][idx]
    o = {'rho_ovr_net': sp(d['ovr'][arm][idx], d['net'][idx]), 'rho_off_O': sp(d['off'][arm][idx], d['O'][idx])}
    for a in ATTRS:
        x = d[a][idx]
        for tag, e in (('net', e_net), ('O', e_O)):
            o[f'S_all_{a}_{tag}'] = sp(x, e)
            for g, ps in GROUPS.items():
                k = np.isin(pos, list(ps))
                o[f'S_{g}_{a}_{tag}'] = sp(x[k], e[k])
            o[f'D_{a}_{tag}'] = o[f'S_F_{a}_{tag}'] - o[f'S_G_{a}_{tag}']
    return o


def run_boot(data):
    """每季各自 rng(SEED) 重抽球員 2000 次；兩臂用同一組重抽，臂間差在同一組上算；另算三原點以人數加權合併。"""
    ns = {t: data[t]['n'] for t in ORIG}
    wts = {t: ns[t] / sum(ns.values()) for t in ORIG}
    point = {t: {a: stats(data[t], np.arange(ns[t]), a) for a in ARMS} for t in ORIG}
    keys = list(point[ORIG[0]]['K0'])
    draws = {t: {a: {k: np.empty(B) for k in keys} for a in ARMS} for t in ORIG}
    rngs = {t: np.random.default_rng(SEED) for t in ORIG}
    for b in range(B):
        for t in ORIG:
            idx = rngs[t].integers(0, ns[t], ns[t])
            for a in ARMS:
                s = stats(data[t], idx, a)
                for k in keys:
                    draws[t][a][k][b] = s[k]
    out = {}
    for t in list(ORIG) + ['pooled']:
        out[t] = {}
        for a in ARMS + ('A-K0',):
            out[t][a] = {}
            for k in keys:
                if t == 'pooled':
                    f = lambda arm: sum(wts[u] * point[u][arm][k] for u in ORIG)
                    g = lambda arm: sum(wts[u] * draws[u][arm][k] for u in ORIG)
                else:
                    f = lambda arm: point[t][arm][k]
                    g = lambda arm: draws[t][arm][k]
                if a == 'A-K0':
                    pt, dr = f('A') - f('K0'), g('A') - g('K0')
                else:
                    pt, dr = f(a), g(a)
                out[t][a][k] = {'point': float(pt), 'ci90': ci(dr)}
    return out, ns


# ---------------------------------------------------------------- 主程式
def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    res = {'seed': SEED, 'draws': B}
    res['prereg_sha256'] = sha(HERE / 'preregistration.md')
    res['prereg_sha256_ok'] = res['prereg_sha256'] == PREREG_SHA == (HERE / 'preregistration.sha256').read_text().split()[0]
    assert res['prereg_sha256_ok'], '預註冊 sha 不符'
    # ---- 建卡輸出 → ranking-{arm}-{t}.csv；c0／c0h
    out_path = lambda a, t: HERE / 'work' / f'{a}-{t}' / 'out' / 'ranking.csv'
    for t in SEAS:
        for a in ARMS:
            rk(t, a).write_bytes(out_path(a, t).read_bytes())
    res['sha256'] = {f'{a}-{t}': sha(rk(t, a)) for a in ARMS for t in SEAS}
    res['c0'] = {'K0_2025-26': res['sha256']['K0-2025-26'], 'ref': 'reports/card-0.2.9a/ranking.csv', 'ref_sha': sha(ROOT / 'reports/card-0.2.9a/ranking.csv')}
    res['c0']['same'] = res['c0']['K0_2025-26'] == res['c0']['ref_sha']
    res['c0h'] = {t: {'K0': res['sha256'][f'K0-{t}'], 'ref': f'reports/card-0.2.9a+E177-bbref-position-shares/ranking-K0-{t}.csv',
                      'ref_sha': sha(E177 / f'ranking-K0-{t}.csv')} for t in ORIG}
    for t in ORIG:
        res['c0h'][t]['same'] = res['c0h'][t]['K0'] == res['c0h'][t]['ref_sha']
    res['c0_pass'] = bool(res['c0']['same']); res['c0h_pass'] = all(res['c0h'][t]['same'] for t in ORIG)
    assert res['c0_pass'] and res['c0h_pass'], 'c0／c0h 不符，停'
    res['npm_test'] = {'exit': int((HERE / 'logs/npm-test.exit').read_text().strip())}
    res['npm_test']['pass'] = res['npm_test']['exit'] == 0
    # ---- 2a
    res['s1'] = s1(res)
    res['s2'], pop = s2()
    # ---- 2b
    data = {t: origin_data(t) for t in ORIG}
    res['n'] = {t: {'n': data[t]['n'], 'nF': data[t]['nF'], 'nG': data[t]['nG'], 'off_bad_frac': data[t]['off_bad']} for t in ORIG}
    bt, ns = run_boot(data)
    res['boot'] = bt
    j = bt[JUDGE_T]
    p0_ci = j['K0']['S_all_pass_net']['ci90']
    p1 = j['A-K0']['S_all_pass_net']['ci90']
    p2 = j['A-K0']['rho_ovr_net']['ci90']
    res['judge'] = {
        'p0_K0h_S_all_pass_net': {'point': j['K0']['S_all_pass_net']['point'], 'ci90': p0_ci, 'rule': '上界 < 0', 'pass': bool(p0_ci[1] < 0)},
        'c1_S_all_pass_net_A-K0': {'point': j['A-K0']['S_all_pass_net']['point'], 'ci90': p1, 'rule': '下界 > 0', 'pass': bool(p1[0] > 0)},
        'c2_rho_ovr_net_A-K0': {'point': j['A-K0']['rho_ovr_net']['point'], 'ci90': p2, 'rule': '下界 > -0.01', 'pass': bool(p2[0] > -0.01)},
        'c3_c0_s1_s2': {'c0': res['c0_pass'], 's1': res['s1']['pass'], 's2': res['s2']['pass'], 'pass': bool(res['c0_pass'] and res['s1']['pass'] and res['s2']['pass'])}}
    jj = res['judge']
    if not jj['p0_K0h_S_all_pass_net']['pass']:
        res['verdict'] = '偏差沒出現，不改卡（p0 不成立）'
    elif jj['c1_S_all_pass_net_A-K0']['pass'] and jj['c2_rho_ovr_net_A-K0']['pass'] and jj['c3_c0_s1_s2']['pass']:
        res['verdict'] = 'A 採用候選'
    else:
        res['verdict'] = '不採用（A 不是候選）'
    # ---- 只報告：2025-26 卡
    cards = {a: load_card(rk('2025-26', a)) for a in ARMS}
    big = {a: [r for r in cards[a] if float(r['MIN']) >= 500] for a in ARMS}
    ovr = {a: {r['name']: float(r['ovr']) for r in big[a]} for a in ARMS}
    rank = {a: {r['name']: i + 1 for i, r in enumerate(sorted(big[a], key=lambda r: -float(r['ovr'])))} for a in ARMS}
    names = [n for n in rank['K0'] if n in rank['A']]
    lab = {r['name']: r['pos'] for r in big['K0']}
    odc = {a: off_def_card(cards[a]) for a in ARMS}
    # 係數表
    pos_list = ['PG', 'SG', 'SF', 'PF', 'C']
    coef = {}
    for a in ARMS:
        coef[a] = {}
        for att in ATTRS:
            j_ = SN.OD_ALL.index(att)
            coef[a][att] = {p: float(odc[a][1][p][1 + j_] * 10) for p in pos_list if p in odc[a][1]}
    res['coef_per10'] = coef
    res['coef_note'] = '每 10 能力值點的 pred0（每 36 分鐘淨分）；各位置對 pred0 做最小平方（pred0 對能力值線性，等於主效應＋該位置交互項）'
    res['offdef_fit_2025-26'] = {a: {'bad_frac_gt_0.02': odc[a][2], 'max_abs_resid': odc[a][3]} for a in ARMS}
    # 前鋒內相關
    def fwd_corr(card, minmin=500):
        f = [r for r in card if float(r['MIN']) >= minmin and r['pos'] in GROUPS['F']]
        return {'n': len(f), 'rho_pass_creation': sp([float(r['pass']) for r in f], [float(r['creation']) for r in f])}
    res['forward_pass_creation_spearman'] = {'2025-26_card': fwd_corr(cards['K0']),
                                             **{f'{t}_card': fwd_corr(load_card(rk(t, 'K0'))) for t in ORIG}}
    # 前 20 與變動
    top = {a: sorted(rank[a], key=rank[a].get)[:20] for a in ARMS}
    res['top20'] = {'K0': top['K0'], 'A': top['A'], 'in': [n for n in top['A'] if n not in top['K0']], 'out': [n for n in top['K0'] if n not in top['A']]}
    def row(n):
        o0, oa = odc['K0'][0][n], odc['A'][0][n]
        return {'name': n, 'pos': lab[n], 'K0': [ovr['K0'][n], rank['K0'][n]], 'A': [ovr['A'][n], rank['A'][n]],
                'dOVR': round(ovr['A'][n] - ovr['K0'][n], 2), 'dRank': rank['K0'][n] - rank['A'][n],
                'OFF_K0': round(o0[0], 2), 'OFF_A': round(oa[0], 2), 'DEF_K0': round(o0[1], 2), 'DEF_A': round(oa[1], 2)}
    res['top20_ovr_movers'] = [row(n) for n in sorted(names, key=lambda n: -abs(ovr['A'][n] - ovr['K0'][n]))[:20]]
    res['top20_rank_movers'] = [row(n) for n in sorted(names, key=lambda n: -abs(rank['K0'][n] - rank['A'][n]))[:20]]
    dv = [ovr['A'][n] - ovr['K0'][n] for n in names]
    res['moves_all'] = {'n_pop': len(names), 'median_abs_dOVR': float(np.median(np.abs(dv))), 'max_abs_dOVR': float(np.max(np.abs(dv))),
                        'mean_dOVR': float(np.mean(dv)),
                        'moved10_top100': sum(1 for n in names if rank['K0'][n] <= 100 and abs(rank['A'][n] - rank['K0'][n]) >= 10),
                        'moved10_top300': sum(1 for n in names if rank['K0'][n] <= 300 and abs(rank['A'][n] - rank['K0'][n]) >= 10),
                        'by_pos_mean_dOVR': {p: float(np.mean([ovr['A'][n] - ovr['K0'][n] for n in names if lab[n] == p])) for p in pos_list},
                        'by_pos_n': {p: sum(1 for n in names if lab[n] == p) for p in pos_list}}
    ex = {}
    for k in EXAMPLES:
        n = next((x for x in names if P.norm(x) == P.norm(k)), None)
        ex[k] = None if n is None else row(n)
    res['examples'] = ex
    # 2024-25 原點上 pass 前鋒前 10 的 e_net 變化（只報告）
    d = data[JUDGE_T]
    e = {a: pct(d['net']) - pct(d['ovr'][a]) for a in ARMS}
    fw = [i for i in range(d['n']) if d['pos'][i] in GROUPS['F']]
    res['top10_forward_pass_2024-25'] = [{'name': d['names'][i], 'pos': str(d['pos'][i]), 'pass': float(d['pass'][i]),
                                          'e_net_K0': float(e['K0'][i]), 'e_net_A': float(e['A'][i]),
                                          'ovr_K0': float(d['ovr']['K0'][i]), 'ovr_A': float(d['ovr']['A'][i])}
                                         for i in sorted(fw, key=lambda i: -d['pass'][i])[:10]]
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print('verdict', res['verdict'])
    print(json.dumps({'c0': res['c0_pass'], 'c0h': res['c0h_pass'], 'npm': res['npm_test'], 's1': {k: res['s1'][k] for k in ('diff_sal', 'ci90_sal', 'diff_twok', 'ci90_twok', 'pass')},
                      's2': res['s2'], 'judge': res['judge']}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    main()
