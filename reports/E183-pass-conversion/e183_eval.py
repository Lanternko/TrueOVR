"""E-183 評估：預註冊 preregistration.md（凍結 sha 見 preregistration.sha256）。
§2a：c0／c0h、s0、s1、s2、npm test。§2b：2024-25 原點 K0h／Qh 對 2025-26 RAPM；①②③。§3 只報告項。
輔助函式（pct、sp、ci、off_def_card、team_median、load_card）唯讀匯入 E-180 e180_eval.py；統計量寫法同其 §2b，
差別：兩臂 pass 欄不同，所以 S(pass) 另算「自己的 pass 軸」與「固定 K0 pass 軸」兩種。
用法（repo root）：python -I -B -X utf8 reports/E183-pass-conversion/e183_eval.py
"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E180D = ROOT / 'reports/E180-pass-pool-creation-interact'
sys.path.insert(0, str(E180D))
spec = importlib.util.spec_from_file_location('e180_eval', E180D / 'e180_eval.py')
E0 = importlib.util.module_from_spec(spec); spec.loader.exec_module(E0)
V, P, SN = E0.V, E0.P, E0.SN
pct, sp, ci, load_card, off_def_card = E0.pct, E0.sp, E0.ci, E0.load_card, E0.off_def_card
PREREG_SHA = 'fa7d5de97a737e4d5d18c83feb92da075baef3c833f2ee4f2a779f500c0716ff'
SEED, B = 20261101, 2000
SEAS, ORIG, NEXT, JUDGE_T, GROUPS = E0.SEAS, E0.ORIG, E0.NEXT, E0.JUDGE_T, E0.GROUPS
ARMS = ('K0', 'Q')
EXAMPLES = ['Jalen Williams', 'Jalen Johnson', 'Paolo Banchero', 'Scottie Barnes', 'Franz Wagner', 'LeBron James', 'Nikola Jokić',
            'Tyrese Haliburton', 'Giannis Antetokounmpo']
sha = E0.sha
rk = lambda t, arm: HERE / f'ranking-{arm}-{t}.csv'


# ---------------------------------------------------------------- 2a
def s0():
    """2025-26 卡片人群（MIN>=500）對到追蹤資料的比例。"""
    d = json.load(open(ROOT / 'reports/handle-E069/raw/2025-26/Passing-FULL.json', encoding='utf-8'))['data']['resultSets'][0]
    ids = {int(r[d['headers'].index('PLAYER_ID')]) for r in d['rowSet']}
    pop = {}
    for r in csv.DictReader(open(HERE / 'work/base-K0-2025-26/c0/cards/K0/primary/pred.csv', encoding='utf-8')):
        pop[P.norm(r['name'])] = int(r['playerId'])
    rows = [r for r in load_card(rk('2025-26', 'K0')) if float(r['MIN']) >= 500]
    miss = [r['name'] for r in rows if pop.get(P.norm(r['name'])) not in ids]
    return {'n': len(rows), 'matched': len(rows) - len(miss), 'frac': 1 - len(miss) / len(rows), 'unmatched': miss, 'pass': bool(1 - len(miss) / len(rows) >= 0.95)}, pop


def s1():
    D = V.load({a: {'2025-26': rk('2025-26', a)} for a in ARMS}, seasons=['2025-26'])
    d = D['seasons']['2025-26']
    ok = np.where(~np.isnan(d['ref_old']))[0]
    full = {a: V.metrics(D, '2025-26', a, 'old', ok) for a in ARMS}
    rng = np.random.default_rng(SEED)
    ds, dk = np.empty(B), np.empty(B)
    for k in range(B):
        idx = ok[rng.integers(0, len(ok), len(ok))]
        m = {a: V.metrics(D, '2025-26', a, 'old', idx) for a in ARMS}
        ds[k] = m['Q']['sal'] - m['K0']['sal']
        dk[k] = m['Q']['twok'] - m['K0']['twok']
    out = {'n_eval': int(len(ok)), **{a: {k: full[a][k] for k in ('n_sal', 'sal', 'n_twok', 'twok', 'C')} for a in ARMS},
           'diff_sal': full['Q']['sal'] - full['K0']['sal'], 'diff_twok': full['Q']['twok'] - full['K0']['twok'],
           'ci90_sal': ci(ds), 'ci90_twok': ci(dk), 'seed': SEED, 'draws': B}
    out['pass_sal'] = bool(out['ci90_sal'][0] > -0.01)
    out['pass_twok'] = bool(out['ci90_twok'][0] > -0.01)
    out['pass'] = out['pass_sal'] and out['pass_twok']
    return out


def s2(pop):
    t0, tq = E0.team_median(rk('2025-26', 'K0'), pop), E0.team_median(rk('2025-26', 'Q'), pop)
    return {'K0': t0['median'], 'Q': tq['median'], 'n_teams': tq['n_teams'], 'diff': tq['median'] - t0['median'],
            'pass': bool(tq['median'] - t0['median'] >= -0.02)}


# ---------------------------------------------------------------- 2b
def origin_data(t):
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
    d = json.loads((E0.E126 / f'rapm-{NEXT[t]}.json').read_text(encoding='utf-8'))
    assert d['season'] == NEXT[t]
    rv = {int(p): v for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mp_next}
    ids = sorted(p for p in m if p in rv)
    rows = [m[p] for p in ids]
    names = [r['name'] for r in rows]
    W = np.array([P.wfun(mp_next[p]) for p in ids])
    out = {'ids': ids, 'names': names, 'pos': np.array([r['pos'] for r in rows]),
           'net': np.array([rv[p]['net'] for p in ids]) * W, 'O': np.array([rv[p]['O'] for p in ids]) * W, 'ovr': {}, 'off': {}, 'pass': {}}
    for a in ARMS:
        rr = [byname[a][n] for n in names]
        assert [r['pos'] for r in rr] == [r['pos'] for r in rows], '兩臂 pos 標籤不同'
        out['ovr'][a] = np.array([float(r['ovr']) for r in rr])
        out['off'][a] = np.array([off[a][0][n][0] for n in names])
        out['pass'][a] = np.array([float(r['pass']) for r in rr])
    for k in ('creation', 'foulDraw'):   # 其他能力值兩臂應完全相同
        v0 = np.array([float(byname['K0'][n][k]) for n in names]); v1 = np.array([float(byname['Q'][n][k]) for n in names])
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
    axes = {'pass': d['pass'][arm], 'passK0': d['pass']['K0'], 'creation': d['creation'], 'foulDraw': d['foulDraw']}
    for a, ax in axes.items():
        x = ax[idx]
        for tag, e in (('net', e_net), ('O', e_O)):
            o[f'S_all_{a}_{tag}'] = sp(x, e)
            for g, ps in GROUPS.items():
                k = np.isin(pos, list(ps))
                o[f'S_{g}_{a}_{tag}'] = sp(x[k], e[k])
            o[f'D_{a}_{tag}'] = o[f'S_F_{a}_{tag}'] - o[f'S_G_{a}_{tag}']
    return o


def run_boot(data):
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
        for a in ARMS + ('Q-K0',):
            out[t][a] = {}
            for k in keys:
                if t == 'pooled':
                    f = lambda arm: sum(wts[u] * point[u][arm][k] for u in ORIG)
                    g = lambda arm: sum(wts[u] * draws[u][arm][k] for u in ORIG)
                else:
                    f = lambda arm: point[t][arm][k]
                    g = lambda arm: draws[t][arm][k]
                pt, dr = (f('Q') - f('K0'), g('Q') - g('K0')) if a == 'Q-K0' else (f(a), g(a))
                out[t][a][k] = {'point': float(pt), 'ci90': ci(dr)}
    return out, ns


# ---------------------------------------------------------------- 主程式
def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    res = {'seed': SEED, 'draws': B}
    res['prereg_sha256'] = sha(HERE / 'preregistration.md')
    res['prereg_sha256_ok'] = res['prereg_sha256'] == PREREG_SHA == (HERE / 'preregistration.sha256').read_text().split()[0]
    assert res['prereg_sha256_ok'], '預註冊 sha 不符'
    out_path = lambda a, t: HERE / 'work' / f'{a}-{t}' / 'out' / 'ranking.csv'
    for t in SEAS:
        for a in ARMS:
            rk(t, a).write_bytes(out_path(a, t).read_bytes())
    res['sha256'] = {f'{a}-{t}': sha(rk(t, a)) for a in ARMS for t in SEAS}
    ref = ROOT / 'reports/card-0.2.9a/ranking.csv'
    res['c0'] = {'K0_2025-26': res['sha256']['K0-2025-26'], 'ref': 'reports/card-0.2.9a/ranking.csv', 'ref_sha': sha(ref)}
    res['c0']['same'] = res['c0']['K0_2025-26'] == res['c0']['ref_sha']
    res['c0h'] = {t: {'K0': res['sha256'][f'K0-{t}'], 'ref': f'reports/E180-pass-pool-creation-interact/ranking-K0-{t}.csv',
                      'ref_sha': sha(E180D / f'ranking-K0-{t}.csv')} for t in ORIG}
    for t in ORIG:
        res['c0h'][t]['same'] = res['c0h'][t]['K0'] == res['c0h'][t]['ref_sha']
    res['c0_pass'] = bool(res['c0']['same']); res['c0h_pass'] = all(res['c0h'][t]['same'] for t in ORIG)
    assert res['c0_pass'] and res['c0h_pass'], 'c0／c0h 不符，停'
    res['npm_test'] = {'exit': int((HERE / 'logs/npm-test.exit').read_text().strip())}
    res['npm_test']['pass'] = res['npm_test']['exit'] == 0
    res['s0'], pop = s0()
    res['s1'] = s1()
    res['s2'] = s2(pop)
    data = {t: origin_data(t) for t in ORIG}
    res['n'] = {t: {'n': data[t]['n'], 'nF': data[t]['nF'], 'nG': data[t]['nG'], 'off_bad_frac': data[t]['off_bad']} for t in ORIG}
    bt, ns = run_boot(data)
    res['boot'] = bt
    j = bt[JUDGE_T]
    p1 = j['Q-K0']['S_all_pass_net']['ci90']
    p2 = j['Q-K0']['rho_ovr_net']['ci90']
    a2 = {'c0': res['c0_pass'], 'c0h': res['c0h_pass'], 'npm_test': res['npm_test']['pass'], 's0': res['s0']['pass'], 's1_sal': res['s1']['pass_sal'],
          's1_2k': res['s1']['pass_twok'], 's2': res['s2']['pass']}
    res['judge'] = {
        'K0h_S_all_pass_net(參考)': {'point': j['K0']['S_all_pass_net']['point'], 'ci90': j['K0']['S_all_pass_net']['ci90']},
        'c1_S_all_pass_net_Q-K0': {'point': j['Q-K0']['S_all_pass_net']['point'], 'ci90': p1, 'rule': '下界 > 0', 'pass': bool(p1[0] > 0)},
        'c2_rho_ovr_net_Q-K0': {'point': j['Q-K0']['rho_ovr_net']['point'], 'ci90': p2, 'rule': '下界 > -0.01', 'pass': bool(p2[0] > -0.01)},
        'c3_2a_all': {**a2, 'pass': bool(all(a2.values()))}}
    jj = res['judge']
    res['verdict'] = 'Q 採用候選' if jj['c1_S_all_pass_net_Q-K0']['pass'] and jj['c2_rho_ovr_net_Q-K0']['pass'] and jj['c3_2a_all']['pass'] else '不採用（Q 不是候選）'
    # ---- 只報告：2025-26 卡
    cards = {a: load_card(rk('2025-26', a)) for a in ARMS}
    big = {a: [r for r in cards[a] if float(r['MIN']) >= 500] for a in ARMS}
    ovr = {a: {r['name']: float(r['ovr']) for r in big[a]} for a in ARMS}
    rank = {a: {r['name']: i + 1 for i, r in enumerate(sorted(big[a], key=lambda r: -float(r['ovr'])))} for a in ARMS}
    names = [n for n in rank['K0'] if n in rank['Q']]
    lab = {r['name']: r['pos'] for r in big['K0']}
    odc = {a: off_def_card(cards[a]) for a in ARMS}
    passv = {a: {r['name']: float(r['pass']) for r in cards[a]} for a in ARMS}
    top = {a: sorted(rank[a], key=rank[a].get)[:20] for a in ARMS}
    res['top20'] = {'K0': top['K0'], 'Q': top['Q'], 'in': [n for n in top['Q'] if n not in top['K0']], 'out': [n for n in top['K0'] if n not in top['Q']]}

    def row(n):
        o0, oq = odc['K0'][0][n], odc['Q'][0][n]
        return {'name': n, 'pos': lab[n], 'pass_K0': round(passv['K0'][n], 1), 'pass_Q': round(passv['Q'][n], 1),
                'K0': [ovr['K0'][n], rank['K0'][n]], 'Q': [ovr['Q'][n], rank['Q'][n]],
                'dOVR': round(ovr['Q'][n] - ovr['K0'][n], 2), 'dRank': rank['K0'][n] - rank['Q'][n],
                'OFF_K0': round(o0[0], 2), 'OFF_Q': round(oq[0], 2), 'DEF_K0': round(o0[1], 2), 'DEF_Q': round(oq[1], 2)}
    res['top20_ovr_movers'] = [row(n) for n in sorted(names, key=lambda n: -abs(ovr['Q'][n] - ovr['K0'][n]))[:20]]
    res['top20_rank_movers'] = [row(n) for n in sorted(names, key=lambda n: -abs(rank['K0'][n] - rank['Q'][n]))[:20]]
    dv = [ovr['Q'][n] - ovr['K0'][n] for n in names]
    pl = ['PG', 'SG', 'SF', 'PF', 'C']
    res['moves_all'] = {'n_pop': len(names), 'median_abs_dOVR': float(np.median(np.abs(dv))), 'max_abs_dOVR': float(np.max(np.abs(dv))), 'mean_dOVR': float(np.mean(dv)),
                        'moved10_top100': sum(1 for n in names if rank['K0'][n] <= 100 and abs(rank['Q'][n] - rank['K0'][n]) >= 10),
                        'moved10_top300': sum(1 for n in names if rank['K0'][n] <= 300 and abs(rank['Q'][n] - rank['K0'][n]) >= 10),
                        'by_pos_mean_dOVR': {p: float(np.mean([ovr['Q'][n] - ovr['K0'][n] for n in names if lab[n] == p])) for p in pl},
                        'by_pos_n': {p: sum(1 for n in names if lab[n] == p) for p in pl}}
    res['examples'] = {}
    for k in EXAMPLES:
        n = next((x for x in names if P.norm(x) == P.norm(k)), None)
        res['examples'][k] = None if n is None else row(n)
    # 2024-25 原點上前鋒 pass 前 10（K0 軸）的 e_net 變化
    d = data[JUDGE_T]
    e = {a: pct(d['net']) - pct(d['ovr'][a]) for a in ARMS}
    fw = [i for i in range(d['n']) if d['pos'][i] in GROUPS['F']]
    res['top10_forward_pass_2024-25'] = [{'name': d['names'][i], 'pos': str(d['pos'][i]), 'pass_K0': float(d['pass']['K0'][i]), 'pass_Q': float(d['pass']['Q'][i]),
                                          'e_net_K0': float(e['K0'][i]), 'e_net_Q': float(e['Q'][i]),
                                          'ovr_K0': float(d['ovr']['K0'][i]), 'ovr_Q': float(d['ovr']['Q'][i])}
                                         for i in sorted(fw, key=lambda i: -d['pass']['K0'][i])[:10]]
    # ---- conv 描述（2025-26）：前後 20、與 AST/astCh、AST/36 的 Spearman
    arr = np.load(HERE / 'work/conv-2025-26.npy')
    pid2i = {int(p): i for i, p in enumerate(arr[0])}
    trk = json.load(open(ROOT / 'reports/handle-E069/raw/2025-26/Passing-FULL.json', encoding='utf-8'))['data']['resultSets'][0]
    h = trk['headers']
    tr = {}
    for r in trk['rowSet']:
        t_ = tr.setdefault(int(r[h.index('PLAYER_ID')]), {k: 0.0 for k in ('MIN', 'PASSES_MADE', 'AST', 'POTENTIAL_AST')})
        for k in t_:
            t_[k] += float(r[h.index(k)] or 0)
    rate0 = json.load(open(HERE / 'work/a0-pass-P0.json', encoding='utf-8'))['r']   # K0 的率那一半（收縮 AST/astCh）
    cv = []
    for nm in names:
        p = pop.get(P.norm(nm))
        if p is None or p not in pid2i or p not in tr:
            continue
        cv.append((nm, p, float(arr[1][pid2i[p]]), float(rate0[str(p)]), tr[p]['AST'] / tr[p]['MIN'] * 36 if tr[p]['MIN'] else np.nan,
                   tr[p]['PASSES_MADE'], tr[p]['AST'] / tr[p]['PASSES_MADE'] if tr[p]['PASSES_MADE'] else np.nan))
    ok = [c for c in cv if not np.isnan(c[4])]
    res['conv_desc'] = {'n': len(ok), 'rho_conv_s_vs_AST_per_astCh_shrunk': sp([c[2] for c in ok], [c[3] for c in ok]),
                        'rho_conv_s_vs_AST_per36_raw': sp([c[2] for c in ok], [c[4] for c in ok]),
                        'rho_AST_per_astCh_vs_AST_per36': sp([c[3] for c in ok], [c[4] for c in ok]),
                        'top20': [{'name': c[0], 'conv_s': round(c[2], 4), 'conv_raw': round(c[6], 4), 'passes': c[5]} for c in sorted(ok, key=lambda c: -c[2])[:20]],
                        'bottom20': [{'name': c[0], 'conv_s': round(c[2], 4), 'conv_raw': round(c[6], 4), 'passes': c[5]} for c in sorted(ok, key=lambda c: c[2])[:20]],
                        'note': 'MIN>=500 卡片人群；AST/36 為追蹤資料原始值（未收縮）'}
    # ---- POTENTIAL_AST/PASSES_MADE、AST/POTENTIAL_AST 與 e_net 的 Spearman（2024-25 原點、2024-25 追蹤資料、K0h 的 e_net；不建卡）
    t24 = json.load(open(ROOT / 'reports/handle-E069/raw/2024-25/Passing-FULL.json', encoding='utf-8'))['data']['resultSets'][0]
    h2 = t24['headers']
    tr2 = {}
    for r in t24['rowSet']:
        t_ = tr2.setdefault(int(r[h2.index('PLAYER_ID')]), {k: 0.0 for k in ('PASSES_MADE', 'AST', 'POTENTIAL_AST')})
        for k in t_:
            t_[k] += float(r[h2.index(k)] or 0)
    ids24 = data[JUDGE_T]['ids']
    sel = [i for i, p in enumerate(ids24) if p in tr2 and tr2[p]['PASSES_MADE'] >= 200 and tr2[p]['POTENTIAL_AST'] > 0]
    pa_pm = np.array([tr2[ids24[i]]['POTENTIAL_AST'] / tr2[ids24[i]]['PASSES_MADE'] for i in sel])
    a_pa = np.array([tr2[ids24[i]]['AST'] / tr2[ids24[i]]['POTENTIAL_AST'] for i in sel])
    a_pm = np.array([tr2[ids24[i]]['AST'] / tr2[ids24[i]]['PASSES_MADE'] for i in sel])
    e_all = {a: e[a][sel] for a in ARMS}
    res['direction_only_2024-25'] = {'n': len(sel), 'note': 'PASSES_MADE>=200、未收縮、2024-25 追蹤資料；e_net 為 K0h／Qh 各自的',
                                     **{f'rho_{nm}_e_net_{a}': sp(x, e_all[a]) for nm, x in (('POTENTIAL_AST_per_PASSES_MADE', pa_pm), ('AST_per_POTENTIAL_AST', a_pa), ('AST_per_PASSES_MADE', a_pm))
                                        for a in ARMS}}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print('verdict', res['verdict'])
    print(json.dumps({'c0': res['c0_pass'], 'c0h': res['c0h_pass'], 'npm': res['npm_test'], 's0': {k: res['s0'][k] for k in ('n', 'matched', 'frac', 'pass')},
                      's1': {k: res['s1'][k] for k in ('diff_sal', 'ci90_sal', 'diff_twok', 'ci90_twok', 'pass')}, 's2': res['s2'], 'judge': res['judge']},
                     ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    main()
