"""E-196 評估（只報告，R-131；spec.md 凍結）。
A 線（機制，樣本外）：沿用 E-181（reports/E181-offball-attr/e181_eval.py 的 origin_data／stats 同式）：各原點卡 → 下一季 RAPM（E-126 rapm-<下季>.json，net×wfun(下季 MPG)），
  人群＝原點卡 MIN>=500 且名字唯一對上、下季 poss>=1000 且下季有出賽；無球組 Q＝offBall 百分位>=60 且 creation 百分位<=50（E-181 errata A1 定義；
  offBall 取 E-181 offball-raw-o2.csv 靜態值，creation 取 G 臂該原點卡欄位；三臂同一份分組）。
  e_net＝pct(net×W)−pct(OVR)。符號（L-096）：OVR 名次比答案低（卡片低估）→ e_net 為正；Q 組平均 e_net 越接近 0 越好，「補回低估」＝X−G 為負。
  ρ＝Spearman(OVR, net×W)。bootstrap 2000 次、seed 20261181、90% 區間；臂間差在同一組重抽上算。
  沒弄壞：ρ 的 X−G 低於 −2×SD（同一組重抽的 X−G 標準差）算弄壞（spec「退步超過雜訊 2 倍」）。三原點各自判，另報三原點合併（逐原點重抽後平均）。
B 線（2025-26 卡，樣本內）：MIN>=500 且在 T6（card-0.2.10d/rapm-T6.csv）的人群；名次殘差＝卡片名次−T6 名次（正＝卡片排得比 T6 低＝低估）；
  另報值殘差（T6 對 OVR 線性迴歸的殘差，正＝低估；L-112）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10g+E196-production/e196_eval.py"""
import csv, hashlib, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))
import eval_v2 as V  # noqa: E402
P = V.P
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
E181 = ROOT / 'reports/E181-offball-attr'
SEED, B = 20261181, 2000
ORIG = ['2022-23', '2023-24', '2024-25']
NEXT = {'2022-23': '2023-24', '2023-24': '2024-25', '2024-25': '2025-26'}
ARMS = ('G', 'S', 'SP')
XARMS = ('S', 'SP')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct(x):
    return rankdata(x) / len(x)


def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def ci(x):
    return [float(np.nanpercentile(x, 5)), float(np.nanpercentile(x, 95))]


def load(p):
    return list(csv.DictReader(open(p, encoding='utf-8-sig')))


def hist_rank(arm, t):
    return HERE / 'work' / f'{arm}-{t}' / 'out' / 'ranking.csv'


# ---------------------------------------------------------------- A 線
def origin_data(t, offb):
    cards = {a: load(hist_rank(a, t)) for a in ARMS}
    byname = {a: {r['name']: r for r in cards[a]} for a in ARMS}
    pop, _ = P.pop_of(t)
    _, mp_next = P.pop_of(NEXT[t])
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    m = {}
    for r in cards['G']:
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
    Wt = np.array([P.wfun(mp_next[p]) for p in ids])
    out = {'ids': ids, 'names': names, 'pos': np.array([r['pos'] for r in rows]), 'net': np.array([rv[p]['net'] for p in ids]) * Wt, 'ovr': {}}
    for a in ARMS:
        out['ovr'][a] = np.array([float(byname[a][n]['ovr']) for n in names])
    cre = np.array([float(r['creation']) for r in rows])
    ob = np.array([offb[p] for p in ids])
    out['Q'] = (100 * pct(ob) >= 60) & (100 * pct(cre) <= 50)
    out['n'] = len(ids)
    return out


def stats(d, idx, arm):
    e = pct(d['net'][idx]) - pct(d['ovr'][arm][idx])
    q = d['Q'][idx]
    return {'rho': sp(d['ovr'][arm][idx], d['net'][idx]), 'Q_e_net': float(e[q].mean()) if q.any() else np.nan}


def line_a():
    offb = {int(r['playerId']): float(r['offBall']) for r in load(E181 / 'offball-raw-o2.csv')}
    data = {t: origin_data(t, offb) for t in ORIG}
    rng = np.random.default_rng(SEED)
    dr = {t: {a: {'rho': np.empty(B), 'Q_e_net': np.empty(B)} for a in ARMS} for t in ORIG}
    for b in range(B):
        for t in ORIG:
            d = data[t]
            idx = rng.integers(0, d['n'], d['n'])
            for a in ARMS:
                s = stats(d, idx, a)
                for k in s:
                    dr[t][a][k][b] = s[k]
    res = {'seed': SEED, 'draws': B, 'sign': 'e_net＝pct(net×W)−pct(OVR)；正＝卡片低估。Q 組補回低估＝X−G 為負', 'origins': {}}
    pooled_pt = {a: {k: [] for k in ('rho', 'Q_e_net')} for a in ARMS}
    for t in ORIG:
        d = data[t]
        pt = {a: stats(d, np.arange(d['n']), a) for a in ARMS}
        o = {'n': d['n'], 'nQ': int(d['Q'].sum())}
        for a in ARMS:
            o[a] = {k: {'point': pt[a][k], 'ci90': ci(dr[t][a][k])} for k in pt[a]}
            for k in pt[a]:
                pooled_pt[a][k].append(pt[a][k])
        for a in XARMS:
            dd = {k: dr[t][a][k] - dr[t]['G'][k] for k in ('rho', 'Q_e_net')}
            o[f'{a}-G'] = {k: {'point': pt[a][k] - pt['G'][k], 'ci90': ci(dd[k]), 'sd': float(np.std(dd[k]))} for k in dd}
            o[f'{a}-G']['rho']['broken'] = bool(o[f'{a}-G']['rho']['point'] < -2 * o[f'{a}-G']['rho']['sd'])
        o['Q_members'] = [{'name': d['names'][i], 'pos': str(d['pos'][i]), **{f'e_{a}': float((pct(d['net']) - pct(d['ovr'][a]))[i]) for a in ARMS}}
                          for i in range(d['n']) if d['Q'][i]]
        res['origins'][t] = o
    pl = {'note': '三原點平均（各原點同一輪重抽後平均）'}
    for a in ARMS:
        pl[a] = {k: {'point': float(np.mean(pooled_pt[a][k])), 'ci90': ci(np.mean([dr[t][a][k] for t in ORIG], 0))} for k in ('rho', 'Q_e_net')}
    for a in XARMS:
        pl[f'{a}-G'] = {}
        for k in ('rho', 'Q_e_net'):
            dd = np.mean([dr[t][a][k] - dr[t]['G'][k] for t in ORIG], 0)
            pl[f'{a}-G'][k] = {'point': pl[a][k]['point'] - pl['G'][k]['point'], 'ci90': ci(dd), 'sd': float(np.std(dd))}
        pl[f'{a}-G']['rho']['broken'] = bool(pl[f'{a}-G']['rho']['point'] < -2 * pl[f'{a}-G']['rho']['sd'])
    res['pooled'] = pl
    return res


# ---------------------------------------------------------------- B 線
SHOOTERS = ['Klay Thompson', 'Sam Hauser', 'Duncan Robinson', 'Luke Kennard', 'Cameron Johnson', 'Rui Hachimura']
VOLUME = ['Jordan Clarkson', 'Malik Monk', 'Collin Sexton', 'Coby White', 'Jordan Poole']


def season_box():
    rs = V.P.jrs(ROOT / 'data/season-source/player-games.json') if hasattr(V.P, 'jrs') else None
    if rs is None:
        d = json.loads((ROOT / 'data/season-source/player-games.json').read_text(encoding='utf-8'))['data']['resultSets']
        d = d[0] if isinstance(d, list) else d
        rs = [dict(zip(d['headers'], r)) for r in d['rowSet']]
    tot = defaultdict(lambda: defaultdict(float))
    for r in rs:
        if not r['MIN']:
            continue
        t = tot[int(r['PLAYER_ID'])]
        for k in ('PTS', 'FGA', 'FTA', 'MIN'):
            t[k] += float(r[k] or 0)
    lg = [sum(t[k] for t in tot.values()) for k in ('PTS', 'FGA', 'FTA')]
    lgts = lg[0] / (2 * (lg[1] + 0.44 * lg[2]))
    return tot, lgts


def line_b():
    cards = {a: {r['name']: r for r in load(HERE / f'ranking-{a}.csv')} for a in ARMS}
    t6 = {r['name']: float(r['pooledNet']) for r in load(ROOT / 'reports/card-0.2.10d/rapm-T6.csv')}
    pid = {r['name']: int(r['playerId']) for r in load(ROOT / 'reports/card-0.2.10d/rapm-T6.csv')}
    names = [n for n, r in cards['G'].items() if float(r['MIN']) >= 500 and n in t6]
    N = len(names)
    ovr = {a: np.array([float(cards[a][n]['ovr']) for n in names]) for a in ARMS}
    rk = {a: N + 1 - rankdata(ovr[a], method='min') for a in ARMS}   # 1＝最高
    t6v = np.array([t6[n] for n in names])
    rk_t6 = N + 1 - rankdata(t6v, method='min')
    vres = {}
    for a in ARMS:
        bcoef = np.polyfit(ovr[a], t6v, 1)
        vres[a] = t6v - np.polyval(bcoef, ovr[a])
    ix = {n: i for i, n in enumerate(names)}
    tot, lgts = season_box()
    pts36 = np.array([tot[pid[n]]['PTS'] / max(tot[pid[n]]['MIN'], 1) * 36 for n in names])
    tsv = np.array([tot[pid[n]]['PTS'] / max(2 * (tot[pid[n]]['FGA'] + 0.44 * tot[pid[n]]['FTA']), 1e-9) for n in names])

    def prow(n):
        i = ix[n]
        return {'name': n, 'pos': cards['G'][n]['pos'], 'T6rank': int(rk_t6[i]), 'long_G': float(cards['G'][n]['long']), 'creation_G': float(cards['G'][n]['creation']),
                'production_SP': float(cards['SP'][n]['creation']), 'pts36': round(float(pts36[i]), 1), 'TS': round(float(tsv[i]), 3),
                **{f'rank_{a}': int(rk[a][i]) for a in ARMS}, **{f'ovr_{a}': float(ovr[a][i]) for a in ARMS}}

    def grp(sel, label):
        sel = np.asarray(sel, bool)
        o = {'label': label, 'n': int(sel.sum())}
        for a in ARMS:
            o[a] = {'mean_rank_resid': float((rk[a] - rk_t6)[sel].mean()), 'mean_value_resid': float(vres[a][sel].mean()), 'mean_rank': float(rk[a][sel].mean())}
        o['members'] = [prow(names[i]) for i in np.where(sel)[0]]
        return o
    cs = np.array([float(cards['G'][n]['long']) >= 75 and float(cards['G'][n]['creation']) <= 60 for n in names])
    top50 = np.zeros(N, bool); top50[np.argsort(-pts36)[:50]] = True
    vol = top50 & (tsv < lgts)
    res = {'N': N, 'lgTS_2025-26': lgts, 'resid_sign': '名次殘差＝卡片名次−T6 名次、值殘差＝T6−迴歸預測；兩者正＝卡片低估',
           'catch_shoot': grp(cs, 'long>=75 且 creation<=60（G 臂卡片值）'), 'volume_ineff': grp(vol, 'PTS/36 前 50 且 TS<聯盟'),
           'named_shooters': [prow(n) for n in SHOOTERS if n in ix], 'named_volume': [prow(n) for n in VOLUME if n in ix],
           'missing_named': [n for n in SHOOTERS + VOLUME if n not in ix]}
    # 配對（規則在看 B 線結果前定）：A＝creation<=60 且 PTS/36 前 30%（無球得分高）；B＝creation>=75 且 PTS/36 低於中位數（自主多、得分少）；
    # 依 A 的 PTS/36 降冪，各配一個 G 臂 OVR 最接近、|ΔOVR|<=2、未用過的 B；最多 10 組。看各臂 A 排在 B 前面的組數。
    p70, p50 = np.percentile(pts36, 70), np.percentile(pts36, 50)
    A = [i for i in np.argsort(-pts36) if float(cards['G'][names[i]]['creation']) <= 60 and pts36[i] >= p70]
    Bs = [i for i in range(N) if float(cards['G'][names[i]]['creation']) >= 75 and pts36[i] < p50]
    used, pairs = set(), []
    for i in A:
        c = [j for j in Bs if j not in used and abs(ovr['G'][j] - ovr['G'][i]) <= 2]
        if not c:
            continue
        j = min(c, key=lambda j: (abs(ovr['G'][j] - ovr['G'][i]), names[j]))
        used.add(j)
        pairs.append({'A': prow(names[i]), 'B': prow(names[j]), **{f'A_ahead_{a}': bool(rk[a][i] < rk[a][j]) for a in ARMS}})
        if len(pairs) >= 10:
            break
    res['pairs'] = {'rule': 'A：creation<=60 且 PTS/36>=第70百分位；B：creation>=75 且 PTS/36<中位數；G 臂 OVR 差<=2 最近配對，最多 10 組',
                    'list': pairs, **{f'A_ahead_{a}': sum(p[f'A_ahead_{a}'] for p in pairs) for a in ARMS}}
    # R-109
    allc = {a: load(HERE / f'ranking-{a}.csv') for a in ARMS}
    big = {a: [r for r in allc[a] if float(r['MIN']) >= 500] for a in ARMS}
    rr = {a: {r['name']: i + 1 for i, r in enumerate(sorted(big[a], key=lambda r: -float(r['ovr'])))} for a in ARMS}
    full = {a: {r['name']: int(r['rank']) for r in allc[a]} for a in ARMS}
    r109 = {}
    for a in XARMS:
        top_g = [n for n in full['G'] if full['G'][n] <= 20]; top_x = [n for n in full[a] if full[a][n] <= 20]
        r109[a] = {'pool': 'ranking.csv 全名單（582）名次', 'top20_in': [n for n in top_x if n not in top_g], 'top20_out': [n for n in top_g if n not in top_x],
                   'top100_moved10': sorted([(n, full['G'][n], full[a][n]) for n in full['G'] if full['G'][n] <= 100 and abs(full[a][n] - full['G'][n]) >= 10], key=lambda x: x[1]),
                   'min500_top20_in': [n for n in rr[a] if rr[a][n] <= 20 and rr['G'].get(n, 999) > 20],
                   'min500_top100_moved10_n': sum(1 for n in rr['G'] if rr['G'][n] <= 100 and abs(rr[a][n] - rr['G'][n]) >= 10)}
        r109[a]['top100_moved10_n'] = len(r109[a]['top100_moved10'])
        d = {n: rr[a][n] - rr['G'][n] for n in rr['G']}
        r109[a]['biggest_up'] = sorted([(n, rr['G'][n], rr[a][n]) for n in d], key=lambda x: x[2] - x[1])[:12]
        r109[a]['biggest_down'] = sorted([(n, rr['G'][n], rr[a][n]) for n in d], key=lambda x: x[1] - x[2])[:12]
    res['r109'] = r109
    res['top20_min500'] = {a: sorted(rr[a], key=rr[a].get)[:20] for a in ARMS}
    return res


def coefs():
    out = {}
    for part in ('primary', 'fitA', 'fitB'):
        out[part] = {}
        for a in ARMS:
            s = json.loads((HERE / f'work/base-{a}-2025-26/c0/cards/K0/{part}/summary.json').read_text(encoding='utf-8'))
            v = s['valuePer10AttributePoints']
            out[part][a] = {'creation_or_production_per10': v['creation']['per36'], 'se': v['creation']['bootstrapSE'], 'long_per10_main': v['long']['per36'],
                            'cvR2': list(s['cvR2'].values())[0]['mean'], 'floor': s.get('e196Floor')}
    hist = {}
    for t in ORIG:
        hist[t] = {}
        for part in ('primary', 'fitA', 'fitB'):
            s = json.loads((HERE / f'work/base-SP-{t}/{t}/cards/K0/{part}/summary.json').read_text(encoding='utf-8'))
            hist[t][part] = s.get('e196Floor')
    return {'2025-26': out, 'history_SP_floor': hist}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    res = {'spec_sha256': sha(HERE / 'spec.md'),
           'ranking_sha256': {f'ranking-{a}.csv': sha(HERE / f'ranking-{a}.csv') for a in ARMS},
           'G_equals_card_0.2.10g': (HERE / 'ranking-G.csv').read_bytes() == (ROOT / 'reports/card-0.2.10g/ranking.csv').read_bytes(),
           'hist_ranking_sha256': {f'{a}-{t}': sha(hist_rank(a, t)) for a in ARMS for t in ORIG},
           'hist_G_vs_E181_K0h': {t: sha(hist_rank('G', t)) == sha(E181 / f'ranking-K0h-{t}.csv') for t in ORIG},
           'inputs_sha256': {'offball-raw-o2.csv': sha(E181 / 'offball-raw-o2.csv'), 'rapm-T6.csv(0.2.10d)': sha(ROOT / 'reports/card-0.2.10d/rapm-T6.csv'),
                             **{f'rapm-{NEXT[t]}.json': sha(E126 / f'rapm-{NEXT[t]}.json') for t in ORIG},
                             **{f'T6-{t}.pkl': sha(ROOT / f'reports/E142-card-target/phase1-work/cands/T6-{t}.pkl') for t in ORIG + ['2025-26']}}}
    res['prod'] = json.loads((HERE / 'work/prod.json').read_text(encoding='utf-8'))
    res['coef'] = coefs()
    res['A'] = line_a()
    res['B'] = line_b()
    ex = HERE / 'logs/npm-test.exit'
    res['npm_test_exit'] = int(ex.read_text().strip()) if ex.exists() else None
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    a = res['A']
    for t in ORIG + ['pooled']:
        o = a['origins'][t] if t != 'pooled' else a['pooled']
        print(t, {k: {m: round(o[k][m]['point'], 4) for m in ('rho', 'Q_e_net')} for k in ARMS + ('S-G', 'SP-G')},
              {k: o[k]['rho']['broken'] for k in ('S-G', 'SP-G')})
    print(json.dumps({k: res['B'][k] for k in ('N',)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
