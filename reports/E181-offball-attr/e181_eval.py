"""E-181 評估：preregistration.md（sha 1e3c8e86…）＋ errata-A1.md（sha fe0475c1…，取代 §3 第 2 階段）。第 1、2 階段一次跑完。
O2 的 offBallAcc 映射規格未定義（見 e181_offballacc.py 說明），O2 標為補充臂、不計入判定。
用法（repo root）：python -I -B -X utf8 reports/E181-offball-attr/e181_eval.py"""
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
SEED, B = 20261181, 2000
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
ORIG = SEAS[:3]
NEXT = {'2022-23': '2023-24', '2023-24': '2024-25', '2024-25': '2025-26'}
JUDGE_T = '2024-25'
ARMS = ('K0', 'O1', 'O2')
XARMS = ('O1', 'O2')
GROUPS = {'F': {'SF', 'PF'}, 'G': {'PG', 'SG'}, 'C': {'C'}}
POS = ['PG', 'SG', 'SF', 'PF', 'C']
EXAMPLES = ['Anfernee Simons', 'Klay Thompson', 'Michael Porter Jr.', 'Sam Hauser', 'Duncan Robinson', 'Derrick White', 'Jalen Williams']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pct(x):
    return rankdata(x) / len(x)
def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1]) if len(x) > 2 else np.nan
def ci(x):
    return [float(np.nanpercentile(x, 5)), float(np.nanpercentile(x, 95))]
def load_card(path):
    return list(csv.DictReader(open(path, encoding='utf-8-sig')))
def rk(t, a):
    return HERE / (f'ranking-{a}-{t}.csv' if t == '2025-26' else f'ranking-{a}h-{t}.csv')


def off_def_card(card):
    coef = {}
    for ps in {r['pos'] for r in card}:
        g = [r for r in card if r['pos'] == ps]
        X = np.c_[np.ones(len(g)), [[float(r[a]) for a in SN.OD_ALL] for r in g]]
        coef[ps] = np.linalg.lstsq(X, np.array([float(r['pred0']) for r in g]), rcond=None)[0]
    q = [r for r in card if float(r['MIN']) >= 500]
    mu = np.array([np.mean([float(r[a]) for r in q]) for a in SN.OD_ALL])
    out = {}
    for r in q:
        b = coef[r['pos']]
        x = np.array([float(r[a]) for a in SN.OD_ALL])
        out[r['name']] = float((b[1:] * (x - mu))[:len(SN.OD_OFF)].sum())
    return out


def team_median(path, name2pid):
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
        mn = float(r['MIN']); pid = name2pid.get(P.norm(r['name']))
        if mn < 100 or pid is None or pid not in main:
            continue
        by[main[pid]].append((mn, float(r['ovr'])))
    std = {abbr[t]: float(np.corrcoef(rankdata([x[0] for x in v]), rankdata([x[1] for x in v]))[0, 1]) for t, v in by.items() if len(v) >= 6}
    return {'median': float(np.median(sorted(std.values()))), 'n_teams': len(std)}


def stage1():
    paths = {a: {'2025-26': rk('2025-26', a)} for a in ARMS}
    D = V.load(paths, seasons=['2025-26'])
    d = D['seasons']['2025-26']
    ok = np.where(~np.isnan(d['ref_old']))[0]
    full = {a: V.metrics(D, '2025-26', a, 'old', ok) for a in ARMS}
    rng = np.random.default_rng(SEED)
    ds = {a: np.empty(B) for a in XARMS}; dk = {a: np.empty(B) for a in XARMS}
    for k in range(B):
        idx = ok[rng.integers(0, len(ok), len(ok))]
        m = {a: V.metrics(D, '2025-26', a, 'old', idx) for a in ARMS}
        for a in XARMS:
            ds[a][k] = m[a]['sal'] - m['K0']['sal']; dk[a][k] = m[a]['twok'] - m['K0']['twok']
    s1 = {'n_eval': int(len(ok)), 'seed': SEED, 'draws': B, 'arms': {a: {k: full[a][k] for k in ('n_sal', 'sal', 'n_twok', 'twok')} for a in ARMS}}
    for a in XARMS:
        o = {'diff_sal': full[a]['sal'] - full['K0']['sal'], 'ci90_sal': ci(ds[a]), 'diff_twok': full[a]['twok'] - full['K0']['twok'], 'ci90_twok': ci(dk[a])}
        o['pass'] = bool(o['ci90_sal'][0] > -0.01 and o['ci90_twok'][0] > -0.01)
        s1['arms'][a].update(o)
    pop = {}
    for r in csv.DictReader(open(HERE / 'work/base-K0-2025-26/c0/cards/K0/primary/pred.csv', encoding='utf-8')):
        pop[P.norm(r['name'])] = int(r['playerId'])
    tm = {a: team_median(rk('2025-26', a), pop) for a in ARMS}
    s2 = {'K0': tm['K0']['median'], 'n_teams': tm['K0']['n_teams']}
    for a in XARMS:
        s2[a] = {'median': tm[a]['median'], 'diff': tm[a]['median'] - tm['K0']['median'], 'pass': bool(tm[a]['median'] - tm['K0']['median'] >= -0.02)}
    s3 = {}
    for a in XARMS:
        s3[a] = {}
        for part in ('primary', 'fitA', 'fitB'):
            sm = json.loads((HERE / f'work/base-{a}-2025-26/c0/cards/K0/{part}/summary.json').read_text(encoding='utf-8'))['valuePer10AttributePoints']
            s3[a][part] = {k: sm[k] for k in ('offBall', 'offBallAcc') if k in sm}
        s3[a]['pass'] = bool(s3[a]['primary']['offBall']['per36'] > 0)
    for a in XARMS:
        s1['arms'][a]['stage1_pass'] = bool(s1['arms'][a]['pass'] and s2[a]['pass'] and s3[a]['pass'])
    return s1, s2, s3


def origin_data(t, offb):
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
    rows = [m[p] for p in ids]; names = [r['name'] for r in rows]
    W = np.array([P.wfun(mp_next[p]) for p in ids])
    out = {'ids': ids, 'names': names, 'pos': np.array([r['pos'] for r in rows]),
           'net': np.array([rv[p]['net'] for p in ids]) * W, 'O': np.array([rv[p]['O'] for p in ids]) * W, 'ovr': {}, 'off': {}}
    for a in ARMS:
        rr = [byname[a][n] for n in names]
        assert [r['pos'] for r in rr] == [r['pos'] for r in rows]
        out['ovr'][a] = np.array([float(r['ovr']) for r in rr]); out['off'][a] = np.array([off[a][n] for n in names])
    cre = np.array([float(r['creation']) for r in rows])
    ob = np.array([offb[p] for p in ids])
    out['offPct'] = 100 * pct(ob); out['crePct'] = 100 * pct(cre)
    out['Q'] = (out['offPct'] >= 60) & (out['crePct'] <= 50)
    out['n'] = len(ids)
    out['nF'] = int(np.isin(out['pos'], list(GROUPS['F'])).sum()); out['nG'] = int(np.isin(out['pos'], list(GROUPS['G'])).sum())
    return out


def stats(d, idx, arm):
    e_net = pct(d['net'][idx]) - pct(d['ovr'][arm][idx])
    e_O = pct(d['O'][idx]) - pct(d['off'][arm][idx])
    q = d['Q'][idx]; pos = d['pos'][idx]
    o = {'rho_ovr_net': sp(d['ovr'][arm][idx], d['net'][idx]), 'Q_e_net': float(e_net[q].mean()) if q.any() else np.nan,
         'Q_e_O': float(e_O[q].mean()) if q.any() else np.nan, 'nQ': int(q.sum())}
    for g, ps in GROUPS.items():
        k = q & np.isin(pos, list(ps))
        o[f'Q_{g}_e_net'] = float(e_net[k].mean()) if k.any() else np.nan
    return o


def run_boot(data):
    out = {}
    for t in ORIG:
        d = data[t]; n = d['n']
        pt = {a: stats(d, np.arange(n), a) for a in ARMS}
        keys = [k for k in pt['K0'] if k != 'nQ']
        dr = {a: {k: np.empty(B) for k in keys} for a in ARMS}
        rng = np.random.default_rng(SEED)
        for b in range(B):
            idx = rng.integers(0, n, n)
            for a in ARMS:
                s = stats(d, idx, a)
                for k in keys:
                    dr[a][k][b] = s[k]
        out[t] = {'n': n, 'nQ': pt['K0']['nQ'], 'nF': d['nF'], 'nG': d['nG']}
        for a in ARMS:
            out[t][a] = {k: {'point': pt[a][k], 'ci90': ci(dr[a][k])} for k in keys}
        for a in XARMS:
            out[t][a + '-K0'] = {k: {'point': pt[a][k] - pt['K0'][k], 'ci90': ci(dr[a][k] - dr['K0'][k])} for k in keys}
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    res = {'seed': SEED, 'draws': B}
    PRE, ERR = 'preregistration.md', 'errata-A1.md'
    res['inputs_sha256'] = {PRE: sha(HERE / PRE), ERR: sha(HERE / ERR), 'offball-raw.csv': sha(HERE / 'offball-raw.csv'), 'offball-raw-o2.csv': sha(HERE / 'offball-raw-o2.csv'),
                            'rapm-2025-26.json': sha(E126 / 'rapm-2025-26.json'), '2k-merged-e142.csv': sha(ROOT / 'data/external-impact/2k/2k-merged-e142.csv'),
                            **{f'data/catchshoot-{s}.json': sha(HERE / f'data/catchshoot-{s}.json') for s in SEAS}}
    assert res['inputs_sha256'][PRE].startswith('1e3c8e86') and res['inputs_sha256'][ERR].startswith('fe0475c1'), '凍結檔 sha 不符'
    for t in SEAS:
        for a in ARMS:
            rk(t, a).write_bytes((HERE / 'work' / f'{a}-{t}' / 'out' / 'ranking.csv').read_bytes())
    res['sha256'] = {rk(t, a).name: sha(rk(t, a)) for t in SEAS for a in ARMS}
    c0 = sha(rk('2025-26', 'K0')) == sha(ROOT / 'reports/card-0.2.9a/ranking.csv')
    c0h = {t: sha(rk(t, 'K0')) == sha(E177 / f'ranking-K0-{t}.csv') for t in ORIG}
    res['c0'] = {'pass': c0, 'K0': sha(rk('2025-26', 'K0')), 'ref': 'reports/card-0.2.9a/ranking.csv'}
    res['c0h'] = {'pass': c0h[JUDGE_T], 'all_origins': c0h, 'ref': 'reports/card-0.2.9a+E177-bbref-position-shares/ranking-K0-<t>.csv'}
    print('c0', c0, 'c0h', c0h, flush=True)
    assert c0 and c0h[JUDGE_T], 'c0／c0h 不符，停'
    ex = HERE / 'logs/npm-test.exit'
    res['npm_test'] = {'exit': int(ex.read_text().strip()) if ex.exists() else None}
    res['npm_test']['pass'] = res['npm_test']['exit'] == 0
    res['s1'], res['s2'], res['s3'] = stage1()
    offrows = list(csv.DictReader(open(HERE / 'offball-raw-o2.csv', encoding='utf-8')))
    offb = {int(r['playerId']): float(r['offBall']) for r in offrows}
    data = {t: origin_data(t, offb) for t in ORIG}
    res['n'] = {t: {'n': data[t]['n'], 'nF': data[t]['nF'], 'nG': data[t]['nG'], 'nQ': int(data[t]['Q'].sum()),
                    'nQ_by_pos': {p: int((data[t]['Q'] & (data[t]['pos'] == p)).sum()) for p in POS}} for t in ORIG}
    res['boot'] = bt = run_boot(data)
    j = bt[JUDGE_T]
    p0 = j['K0']['Q_e_net']
    res['p0'] = {'Q_e_net_K0h': p0, 'rule': '上界 < 0', 'pass': bool(p0['ci90'][1] < 0)}
    res['arms_judge'] = {}
    for a in XARMS:
        c1 = j[a + '-K0']['Q_e_net']; c2 = j[a + '-K0']['rho_ovr_net']; s1p = res['s1']['arms'][a]['stage1_pass']
        g = {'c1_Q_e_net_X-K0': {**c1, 'rule': '下界 > 0', 'pass': bool(c1['ci90'][0] > 0)},
             'c2_rho_ovr_net_X-K0': {**c2, 'rule': '下界 > -0.01', 'pass': bool(c2['ci90'][0] > -0.01)},
             'c3_stage1': s1p}
        g['candidate'] = bool(g['c1_Q_e_net_X-K0']['pass'] and g['c2_rho_ovr_net_X-K0']['pass'] and s1p)
        res['arms_judge'][a] = g
    # 只報告（非凍結定義）：errata-A1 的 e_net＝pct(net)−pct(OVR) 與「低估」假設符號相反（OVR 偏低 → e_net 為正，但 p0 要求上界<0、①要求 X−K0 下界>0）。
    # 這裡把 e_net 反號（＝pct(OVR)−pct(net)）的結果列出，供使用者裁定是否另開 errata A2；判定仍照字面。
    def neg(c):
        return {'point': -c['point'], 'ci90': [-c['ci90'][1], -c['ci90'][0]]}
    sc = {'note': 'e_net 反號（pct(OVR)−pct(net)）的讀法，非凍結定義，不計入判定', 'p0_Q_e_net_K0h': neg(p0)}
    sc['p0_pass_if_flipped'] = bool(sc['p0_Q_e_net_K0h']['ci90'][1] < 0)
    for a in XARMS:
        c1n = neg(j[a + '-K0']['Q_e_net'])
        sc[a] = {'c1_Q_e_net_X-K0': {**c1n, 'pass': bool(c1n['ci90'][0] > 0)}}
        sc[a]['candidate_if_flipped'] = bool(sc['p0_pass_if_flipped'] and sc[a]['c1_Q_e_net_X-K0']['pass'] and res['arms_judge'][a]['c2_rho_ovr_net_X-K0']['pass'] and res['arms_judge'][a]['c3_stage1'])
    res['sign_check'] = sc
    res['O2_note'] = 'offBallAcc 的映射規格未定義（CURVE_3PT 以 3P% 標定，套不到 eFG%）；O2 用與 offBall 相同的 E-101 合併池百分位尺，是規格外補定義，不計入判定。'
    if not res['p0']['pass']:
        res['verdict'] = '低估沒出現，不加屬性（p0 不成立）'
    elif res['arms_judge']['O1']['candidate']:
        res['verdict'] = 'O1 採用候選'
    else:
        res['verdict'] = '不採用（O1 不是候選）'
    res['verdict_if_O2_counted'] = ('低估沒出現，不加屬性（p0 不成立）' if not res['p0']['pass'] else
                                    ('O1 採用候選' if res['arms_judge']['O1']['candidate'] else 'O2 採用候選' if res['arms_judge']['O2']['candidate'] else '不採用'))
    # ---------- 只報告：2025-26 卡
    cards = {a: load_card(rk('2025-26', a)) for a in ARMS}
    big = {a: [r for r in cards[a] if float(r['MIN']) >= 500] for a in ARMS}
    ovr = {a: {r['name']: float(r['ovr']) for r in big[a]} for a in ARMS}
    rank = {a: {r['name']: i + 1 for i, r in enumerate(sorted(big[a], key=lambda r: -float(r['ovr'])))} for a in ARMS}
    names = [n for n in rank['K0'] if all(n in rank[a] for a in ARMS)]
    lab = {r['name']: r['pos'] for r in big['K0']}
    def row(n):
        return {'name': n, 'pos': lab[n], **{a: [ovr[a][n], rank[a][n]] for a in ARMS}}
    res['examples'] = {}
    for k in EXAMPLES:
        n = next((x for x in names if P.norm(x) == P.norm(k)), None)
        res['examples'][k] = None if n is None else row(n)
    top = {a: sorted(rank[a], key=rank[a].get)[:20] for a in ARMS}
    res['top20'] = {a: top[a] for a in ARMS}
    for a in XARMS:
        res['top20'][f'{a}_in'] = [n for n in top[a] if n not in top['K0']]
        res['top20'][f'{a}_out'] = [n for n in top['K0'] if n not in top[a]]
        res[f'movers_{a}'] = [{**row(n), 'dOVR': round(ovr[a][n] - ovr['K0'][n], 2), 'dRank': rank['K0'][n] - rank[a][n]}
                              for n in sorted(names, key=lambda n: -abs(ovr[a][n] - ovr['K0'][n]))[:20]]
        dv = [ovr[a][n] - ovr['K0'][n] for n in names]
        res[f'moves_{a}'] = {'n': len(names), 'median_abs_dOVR': float(np.median(np.abs(dv))), 'max_abs_dOVR': float(np.max(np.abs(dv))), 'mean_dOVR': float(np.mean(dv)),
                             'moved10_top100': sum(1 for n in names if rank['K0'][n] <= 100 and abs(rank[a][n] - rank['K0'][n]) >= 10),
                             'by_pos_mean_dOVR': {p: float(np.mean([ovr[a][n] - ovr['K0'][n] for n in names if lab[n] == p])) for p in POS if any(lab[n] == p for n in names)}}
    k0 = {r['name']: r for r in big['K0']}
    inpop = [r for r in offrows if r['name'] in k0]
    raws = np.array([float(r['offBallRaw']) for r in inpop])
    res['offball_top30'] = [{'name': r['name'], 'raw': float(r['offBallRaw']), 'pct': float(r['offBallPct']), 'offBall': float(r['offBall']), 'creation': float(k0[r['name']]['creation']),
                              'ovr_K0': ovr['K0'].get(r['name']), 'ovr_O1': ovr['O1'].get(r['name'])} for r in sorted(inpop, key=lambda r: -float(r['offBallRaw']))[:30]]
    res['offball_dist'] = {'n': len(raws), 'quantiles': {str(p): float(np.percentile(raws, p)) for p in (1, 10, 25, 50, 75, 90, 99)}, 'mean': float(raws.mean()), 'sd': float(raws.std())}
    ob = np.array([float(r['offBall']) for r in inpop])
    res['offball_spearman'] = {a: sp(ob, [float(k0[r['name']][a]) for r in inpop]) for a in ('creation', 'long', 'pass')}
    res['offballacc_spearman_offball'] = sp([float(r['offBallAcc']) for r in inpop], ob)
    res['coef_per10_per36_primary'] = {a: {k: v['per36'] for k, v in json.loads((HERE / f'work/base-{a}-2025-26/c0/cards/K0/primary/summary.json').read_text(encoding='utf-8'))['valuePer10AttributePoints'].items()} for a in ARMS}
    d = data[JUDGE_T]
    e = {a: pct(d['net']) - pct(d['ovr'][a]) for a in ARMS}
    qi = [i for i in range(d['n']) if d['Q'][i]]
    res['Q_members_2024-25'] = [{'name': d['names'][i], 'pos': str(d['pos'][i]), 'offPct': float(d['offPct'][i]), 'crePct': float(d['crePct'][i]),
                                 **{f'ovr_{a}': float(d['ovr'][a][i]) for a in ARMS}, **{f'e_net_{a}': float(e[a][i]) for a in ARMS}} for i in sorted(qi, key=lambda i: -d['offPct'][i])]
    pg = json.loads((ROOT / 'data/season-source/player-games.json').read_text(encoding='utf-8'))['data']['resultSets'][0]
    gi = pg['headers'].index('GAME_DATE')
    res['data_cutoff'] = {'player-games_last_game_date': max(r[gi] for r in pg['rowSet']), 'rapm': 'rapm-2025-26.json（E-126）', 'catchshoot': '2025-26 整季（2026-11-01 取得）'}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print('verdict', res['verdict'], '| if O2 counted:', res['verdict_if_O2_counted'])
    print(json.dumps({'s1': {a: {k: v for k, v in res['s1']['arms'][a].items() if k not in ('n_sal', 'n_twok')} for a in XARMS},
                      's2': res['s2'], 's3': {a: res['s3'][a]['primary'] | {'pass': res['s3'][a]['pass']} for a in XARMS}, 'p0': res['p0'], 'judge': res['arms_judge'], 'n': res['n']}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    main()
