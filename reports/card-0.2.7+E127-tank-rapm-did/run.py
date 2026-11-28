"""E-127 正式執行（預註冊 dbafa0fe… + errata-1 a7159d57…）。
用法: python -I -B -X utf8 run.py phase0 | main | compare
沒有 subprocess。phase0 沒過就停，不進 main。"""
import csv, hashlib, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
PAIRS = list(zip(SEASONS[:-1], SEASONS[1:]))
PAIRN = [f'{a}->{b}' for a, b in PAIRS]
PRE_SHA = 'dbafa0fe5aa764a7e706b58814630b4f69ab9ad3c71e889a35263203ed75e3e2'
ERR_SHA = 'a7159d5702e52194f939bffe292dbafd04a5b642ff2997442d679f689e79c255'
B8 = 0.4678; POSS_MIN = 1500; B = 2000; SEED = 1


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jl(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def check_frozen():
    a, b = sha(HERE / 'preregistration.md'), sha(HERE / 'errata-1.md')
    if a != PRE_SHA or b != ERR_SHA:
        print('SHA MISMATCH', a, b); sys.exit(2)
    return a, b


def load():
    FE = {s: {int(k): v for k, v in jl(HERE / f'feats-{s}.json').items()} for s in SEASONS}
    RP = {s: {int(k): v for k, v in jl(E126 / f'rapm-{s}.json')['players'].items()} for s in SEASONS}
    meta = jl(HERE / 'phase0.json')['seasons']
    return FE, RP, meta


def phase0(FE, RP):
    """只取 poss 判斷合格；不輸出任何 RAPM 值。"""
    res = {'doc': 'E-127 phase 0 (errata-1 c0f)', 'prereg_sha256': PRE_SHA, 'errata1_sha256': ERR_SHA}
    ref = jl(ROOT / 'reports/ovr-inseason-2026-27/live/usage-2025-26-card027.json')['players']
    fe = FE['2025-26']; poss = {q: v['poss'] for q, v in RP['2025-26'].items()}
    my = md = miss = 0; mxL_all = 0.0; mxL = 0.0; nL = 0; nbig_low = 0
    for k, f in ref.items():
        q = int(k)
        if q not in fe: miss += 1; continue
        my += fe[q]['y'] != f['y']; md += fe[q]['d'] != f['d']
        dl = abs(fe[q]['L'] - f['L']); mxL_all = max(mxL_all, dl)
        if poss.get(q, 0) >= POSS_MIN: mxL = max(mxL, dl); nL += 1
        elif dl >= 0.01: nbig_low += 1
    res['c0f'] = {'nRef': len(ref), 'missingInMine': miss, 'yMismatch': int(my), 'dMismatch': int(md), 'maxAbsDiffL_all': mxL_all,
                  'nCompareL_poss>=1500': nL, 'maxAbsDiffL_poss>=1500': mxL, 'nLdiffGE0.01_lowPoss': nbig_low,
                  'pass': bool(miss == 0 and my == 0 and md == 0 and mxL < 0.01)}
    teams = {s: sorted({v['mainAbbr'] for v in FE[s].values() if v['d'] == 1}) for s in SEASONS}
    res['c0s'] = {s: {'nTeams': len(teams[s]), 'teams': teams[s]} for s in SEASONS}
    res['c0s']['pass'] = all(3 <= res['c0s'][s]['nTeams'] <= 8 for s in SEASONS[:3])
    n_pair = {}
    for S, S1 in PAIRS:
        ok = lambda q: FE[S][q]['age'] is not None and RP[S].get(q, {}).get('poss', 0) >= POSS_MIN
        elig = [q for q in FE[S] if ok(q) and RP[S1].get(q, {}).get('poss', 0) >= POSS_MIN]
        lost = [q for q in FE[S] if ok(q) and RP[S1].get(q, {}).get('poss', 0) < POSS_MIN]
        c = lambda y, d: sum(FE[S][q]['y'] == y and FE[S][q]['d'] == d for q in elig)
        n_pair[f'{S}->{S1}'] = {'eligible': len(elig), 'y1d1': c(1, 1), 'y1d0': c(1, 0), 'y0d1': c(0, 1), 'y0d0': c(0, 0), 'lost': len(lost)}
    tot = sum(v['y1d1'] for v in n_pair.values())
    res['c0n'] = {'perPair': n_pair, 'totalY1D1': tot, 'threshold': 30, 'pass': tot >= 30}
    res['allPass'] = bool(res['c0f']['pass'] and res['c0s']['pass'] and res['c0n']['pass'])
    (HERE / 'phase0-errata1.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    return res


def dnp_game_ids(season):
    if season == '2025-26':
        return {int(g) for g in jl(ROOT / 'data/season-source/dnp-2025-26.json')['games']}
    return {int(f.name.split('_')[1].split('.')[0]) for f in (ROOT / f'data/season-source/dnp-{season}-raw').glob('boxscore_*.json.gz')}


def min_alt(season, gids):
    p = (ROOT / 'data/season-source/player-games.json') if season == '2025-26' else (ROOT / f'data/defense-seventh/{season}/player-games.json')
    rs = jl(p)['data']['resultSets'][0]; h = rs['headers']
    ip, ig, im, inm = h.index('PLAYER_ID'), h.index('GAME_ID'), h.index('MIN'), h.index('PLAYER_NAME')
    mn = defaultdict(float); names = {}
    for r in rs['rowSet']:
        names[r[ip]] = r[inm]
        if r[im] and int(r[ig]) in gids: mn[r[ip]] += r[im]
    return mn, names


def wls(X, y, w):
    sw = np.sqrt(w)
    return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def build_rows(FE, RP, meta, names):
    rows = []
    for S, S1 in PAIRS:
        wr = meta[S1]['winrate']
        for q in FE[S]:
            f = FE[S][q]
            if f['age'] is None: continue
            a, b = RP[S].get(q), RP[S1].get(q)
            if not a or not b or a['poss'] < POSS_MIN or b['poss'] < POSS_MIN or q not in FE[S1]: continue
            g1 = FE[S1][q]
            rows.append(dict(pair=f'{S}->{S1}', pid=q, name=names.get(q, ''), y=f['y'], d=f['d'], age=f['age'], L=f['L'], L_alt=f['L_alt'],
                             R0=a['net'], R1=b['net'], p0=a['poss'], p1=b['poss'], team0=f['mainAbbr'], team1=g1['mainAbbr'],
                             wr1=wr[g1['mainAbbr']], moved=int(g1['main'] != f['main'])))
    return rows


def design(rows):
    X = np.zeros((len(rows), 6))
    for i, r in enumerate(rows):
        X[i, PAIRN.index(r['pair'])] = 1; X[i, 3] = r['R0']; X[i, 4] = r['age'] - 22; X[i, 5] = r['d']
    return X


def W(rows): return np.array([1 / (1 / r['p0'] + 1 / r['p1']) for r in rows])


def boot_idx(rows, rng, n):
    pids = sorted({r['pid'] for r in rows}); by = defaultdict(list)
    for i, r in enumerate(rows): by[r['pid']].append(i)
    for _ in range(n):
        pick = rng.integers(0, len(pids), len(pids))
        yield np.array([i for k in pick for i in by[pids[k]]])


def ci(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]
    return [float(np.percentile(a, 5)), float(np.percentile(a, 95))] if len(a) else [None, None]


def est(pt, draws):
    d = np.asarray(draws, float)
    return {'est': None if pt is None else float(pt), 'ci90': ci(d), 'nValidDraws': int(np.sum(~np.isnan(d)))}


def main():
    pre, err = check_frozen()
    FE, RP, meta = load()
    p0 = phase0(FE, RP)
    if not p0['allPass']:
        print('PHASE0 FAIL', json.dumps({k: p0[k] for k in ('c0f', 'c0s', 'c0n')}, ensure_ascii=False)); sys.exit(3)
    print('phase0 pass; c0f maxL', p0['c0f']['maxAbsDiffL_poss>=1500'], 'c0n', p0['c0n']['totalY1D1'])
    names = {}; chk = {}
    for s in SEASONS:
        gids = dnp_game_ids(s); mn, nm = min_alt(s, gids); names.update(nm)
        for q, f in FE[s].items():
            m = mn.get(q, 0.0); f['MIN_alt'] = m
            f['L_alt'] = float(np.log1p(m / f['ap'])) if f['ap'] > 0 else 0.0
        chk[s] = {'nDnpGames': len(gids), 'maxAbs_MINalt_minus_MIN': max(abs(f['MIN_alt'] - f['MIN']) for f in FE[s].values())}
    rows = build_rows(FE, RP, meta, names)
    Y1 = [r for r in rows if r['y'] == 1]; Y0 = [r for r in rows if r['y'] == 0]
    grp = {'y1d1': [r for r in Y1 if r['d'] == 1], 'y1d0': [r for r in Y1 if r['d'] == 0], 'y0d1': [r for r in Y0 if r['d'] == 1], 'y0d0': [r for r in Y0 if r['d'] == 0]}
    res = {'doc': 'E-127 results', 'prereg_sha256': pre, 'errata1_sha256': err, 'phase0': 'phase0-errata1.json',
           'bootstrap': {'B': B, 'seed': SEED, 'unit': 'player', 'rng': 'numpy default_rng(seed), 每個模型各自從 seed 重開', 'level': 0.90},
           'beta8': -B8, 'eAltCheck': chk, 'nRows': len(rows)}
    res['n'] = {k: len(v) for k, v in grp.items()}
    res['nPerPair'] = {p: {k: sum(r['pair'] == p for r in v) for k, v in grp.items()} for p in PAIRN}
    res['nPlayersY1D1'] = len({r['pid'] for r in grp['y1d1']})
    att = {}
    for S, S1 in PAIRS:
        t = {'y1d1': [0, 0], 'y1d0': [0, 0], 'y0d1': [0, 0], 'y0d0': [0, 0]}
        for q, f in FE[S].items():
            a = RP[S].get(q)
            if f['age'] is None or not a or a['poss'] < POSS_MIN: continue
            k = f'y{int(f["y"])}d{int(f["d"])}'; t[k][0] += 1
            b = RP[S1].get(q)
            if not b or b['poss'] < POSS_MIN: t[k][1] += 1
        att[f'{S}->{S1}'] = {k: {'nS': v[0], 'lost': v[1], 'lostRate': (v[1] / v[0] if v[0] else None)} for k, v in t.items()}
    tot = {k: [sum(att[p][k]['nS'] for p in PAIRN), sum(att[p][k]['lost'] for p in PAIRN)] for k in ('y1d1', 'y1d0', 'y0d1', 'y0d0')}
    att['total'] = {k: {'nS': v[0], 'lost': v[1], 'lostRate': v[1] / v[0] if v[0] else None} for k, v in tot.items()}
    res['attrition'] = att
    # 主模型
    ys = np.array([r['R1'] for r in Y1]); X = design(Y1); w = W(Y1)
    coef = wls(X, ys, w)
    def Eof(rs, key='L'): return float(np.mean([B8 * r[key] for r in rs])) if rs else float('nan')
    E, Ea = Eof(grp['y1d1']), Eof(grp['y1d1'], 'L_alt')
    rng = np.random.default_rng(SEED)
    bd = []; bE = []; bEa = []; bdd = []
    for idx in boot_idx(Y1, rng, B):
        sub = [Y1[i] for i in idx]
        bd.append(wls(X[idx], ys[idx], w[idx]))
        d11 = [r for r in sub if r['d'] == 1]; d10 = [r for r in sub if r['d'] == 0]
        bE.append(Eof(d11)); bEa.append(Eof(d11, 'L_alt'))
        bdd.append(np.mean([r['R1'] - r['R0'] for r in d11]) - np.mean([r['R1'] - r['R0'] for r in d10]) if d11 and d10 else np.nan)
    bd = np.array(bd); bE = np.array(bE); bEa = np.array(bEa); g = bd[:, 5]
    res['main'] = {'gamma': est(coef[5], g), 'E': est(E, bE), 'gamma_over_E': est(coef[5] / E, g / bE), 'E_alt': est(Ea, bEa),
                   'gamma_over_E_alt': est(coef[5] / Ea, g / bEa), 'beta': est(coef[3], bd[:, 3]), 'delta_per_year': est(coef[4], bd[:, 4]),
                   'alphaS': {p: est(coef[i], bd[:, i]) for i, p in enumerate(PAIRN)},
                   'note': 'age 以 22 歲置中，只影響 α_S 的讀法，不影響 γ、β、δ'}
    gl = res['main']['gamma']['ci90'][0]; r_pt = res['main']['gamma_over_E']['est']; ru = res['main']['gamma_over_E']['ci90'][1]
    verdict = '環境說成立' if (gl > 0 and r_pt >= 0.5) else ('折扣是真的' if ru < 0.5 else '無定論')
    ra_pt, ra_u = res['main']['gamma_over_E_alt']['est'], res['main']['gamma_over_E_alt']['ci90'][1]
    verdict_alt = '環境說成立' if (gl > 0 and ra_pt >= 0.5) else ('折扣是真的' if ra_u < 0.5 else '無定論')
    res['verdict'] = verdict
    res['verdict_rule'] = {'gamma_ci90_lower': gl, 'gamma_over_E_pt': r_pt, 'gamma_over_E_ci90_upper': ru}
    res['verdict_if_E_alt_reference_only'] = verdict_alt
    dr = lambda rs: float(np.mean([r['R1'] - r['R0'] for r in rs]))
    res['raw_did'] = est(dr(grp['y1d1']) - dr(grp['y1d0']), bdd)
    res['raw_did'].update({'mean_dR_y1d1': dr(grp['y1d1']), 'mean_dR_y1d0': dr(grp['y1d0'])})
    # H2
    h2 = {}
    y0 = np.array([r['R1'] for r in Y0]); X0 = design(Y0); w0 = W(Y0); c0 = wls(X0, y0, w0)
    rng = np.random.default_rng(SEED); b0 = np.array([wls(X0[i], y0[i], w0[i]) for i in boot_idx(Y0, rng, B)])
    h2['gamma_old'] = est(c0[5], b0[:, 5]); h2['n_old'] = {'all': len(Y0), 'd1': len(grp['y0d1'])}
    Xm = np.hstack([design(rows), np.array([[r['y'] for r in rows]]).T, np.array([[r['y'] * r['d'] for r in rows]]).T])
    ym = np.array([r['R1'] for r in rows]); wm = W(rows); cm = wls(Xm, ym, wm)
    rng = np.random.default_rng(SEED); bm = np.array([wls(Xm[i], ym[i], wm[i]) for i in boot_idx(rows, rng, B)])
    h2['merged_dxy'] = {'columns': 'alphaS x3, R_S, age-22, d, y, d*y', 'gamma_d_at_y0': est(cm[5], bm[:, 5]), 'y_main': est(cm[6], bm[:, 6]),
                        'interaction_dxy': est(cm[7], bm[:, 7]), 'n': len(rows)}
    subs = {'S1_winrate>=0.45': lambda r: float(r['wr1'] >= 0.45), 'moved_team': lambda r: float(r['moved']), 'age<=20': lambda r: float(r['age'] <= 20)}
    h2['subgroups'] = {}
    for nm, fn in subs.items():
        gg = np.array([fn(r) for r in Y1]); dd = np.array([r['d'] for r in Y1])
        n11 = int(np.sum((gg == 1) & (dd == 1))); n10 = int(np.sum((gg == 0) & (dd == 1)))
        info = {'n_d1_g1': n11, 'n_d1_g0': n10, 'n_all_g1': int(gg.sum()), 'n_all_g0': int((1 - gg).sum())}
        if n11 < 8 or n10 < 8:
            info['status'] = 'n<8 只列名單（任一側 d=1 人次不足 8 就不估）'
            info['roster_d1_g1'] = [f"{r['name']}({r['pair']})" for r, v in zip(Y1, gg) if v == 1 and r['d'] == 1]
            info['roster_d1_g0'] = [f"{r['name']}({r['pair']})" for r, v in zip(Y1, gg) if v == 0 and r['d'] == 1]
        else:
            Xs = np.hstack([X, gg[:, None], (gg * dd)[:, None]]); cs = wls(Xs, ys, w)
            rng = np.random.default_rng(SEED); bs = np.array([wls(Xs[i], ys[i], w[i]) for i in boot_idx(Y1, rng, B)])
            info['status'] = 'estimated'; info['gamma_g0'] = est(cs[5], bs[:, 5]); info['gamma_g1'] = est(cs[5] + cs[7], bs[:, 5] + bs[:, 7])
            info['interaction_d_x_g'] = est(cs[7], bs[:, 7])
        h2['subgroups'][nm] = info
    res['H2'] = h2
    pred = X @ coef
    with open(HERE / 'players.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        wr = csv.writer(fh); wr.writerow(['pair', 'pid', 'name', 'team_S', 'team_S1', 'age', 'L', 'L_alt', 'R_S', 'R_S1', 'pred', 'resid', 'poss_S', 'poss_S1', 'wr_S1', 'moved'])
        for i, r in enumerate(Y1):
            if r['d'] == 1:
                wr.writerow([r['pair'], r['pid'], r['name'], r['team0'], r['team1'], r['age'], round(r['L'], 5), round(r['L_alt'], 5), round(r['R0'], 5), round(r['R1'], 5),
                             round(pred[i], 5), round(r['R1'] - pred[i], 5), round(r['p0'], 1), round(r['p1'], 1), r['wr1'], r['moved']])
    res['sampleCounts'] = {'rows_total': len(rows), 'players_unique': len({r['pid'] for r in rows})}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('n', 'verdict', 'main', 'raw_did')}, ensure_ascii=False, indent=1))


def compare():
    a, b = jl(HERE / 'ro-before-run.json'), jl(HERE / 'ro-after-run.json'); out = {}
    for d in a['dirs']:
        fa, fb = a['dirs'][d]['files'], b['dirs'][d]['files']
        out[d] = {'sameTree': a['dirs'][d]['treeSha256'] == b['dirs'][d]['treeSha256'], 'nBefore': len(fa), 'nAfter': len(fb),
                  'changed': sorted(k for k in fa if k in fb and fa[k] != fb[k]), 'added': sorted(set(fb) - set(fa)), 'removed': sorted(set(fa) - set(fb))}
    (HERE / 'ro-compare-run.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({d: (v['sameTree'], v['nBefore'], v['nAfter'], v['changed'][:5], v['added'][:5], v['removed'][:5]) for d, v in out.items()}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    {'main': main, 'compare': compare}[sys.argv[1]]()
