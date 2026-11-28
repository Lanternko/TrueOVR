"""E-162 評估（預註冊 §3、§4）。用 E-157 eval_v2。seed 20261103、2000 次。用法（repo root）：python -I -B -X utf8 <本檔>"""
import csv, json, pickle, shutil, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))
import eval_v2 as V
P = V.P
SEED = 20261103
ARMS = ['K', 'P15', 'P30']
KEY = ['Cooper Flagg', 'Paolo Banchero', 'Kon Knueppel', 'Anthony Edwards', 'Jalen Green', 'Zach LaVine', 'DeMar DeRozan', 'Jordan Poole',
       'Trae Young', 'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Victor Wembanyama']


def rp(a, t):
    return HERE / 'work' / f'{a}-{t}' / 'out' / 'ranking.csv'


def submask(D, t):
    """子群：USG% >= 第75百分位 且 TS% 在 [第25, 第75] 百分位（含端點）；分位在該季評估人群（D ids）內算（np.percentile 線性內插）。"""
    adv = pickle.load(open(HERE / f'work/adv-{t}.pkl', 'rb'))
    ids = D['seasons'][t]['ids']
    u = np.array([adv.get(p, {}).get('usg_pct', np.nan) for p in ids], float)
    s = np.array([adv.get(p, {}).get('ts_pct', np.nan) for p in ids], float)
    ok = ~np.isnan(u) & ~np.isnan(s)
    u75 = np.percentile(u[ok], 75)
    s25, s75 = np.percentile(s[ok], [25, 75])
    m = ok & (u >= u75) & (s >= s25) & (s <= s75)
    return m, {'n_pop': len(ids), 'n_adv': int(ok.sum()), 'usg_p75': float(u75), 'ts_p25': float(s25), 'ts_p75': float(s75), 'n_sub': int(m.sum())}


def per_sub(D, masks, seasons):
    return {t: {a: V.metrics(D, t, a, 'v2', np.where(masks[t])[0]) for a in D['arms']} for t in seasons}


def boot_sub(D, a, b, seasons, masks, seed, draws=V.B):
    rng = np.random.default_rng(seed)
    sel = {t: np.where(masks[t])[0] for t in seasons}
    allids = sorted(set().union(*[{D['seasons'][t]['ids'][i] for i in sel[t]} for t in seasons]))
    pos = {t: {D['seasons'][t]['ids'][i]: i for i in sel[t]} for t in seasons}
    diffs = np.empty(draws)
    for k in range(draws):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        num = den = 0.0
        for t in seasons:
            s = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat(np.array([pos[t][allids[j]] for j in s]), np.array([mult[j] for j in s]))
            d = D['seasons'][t]
            rf = d['ref_v2']
            num += len(idx) * (P.spearman(d['ovr'][a][idx], rf[idx]) - P.spearman(d['ovr'][b][idx], rf[idx]))
            den += len(idx)
        diffs[k] = num / den
    return {'lower90': float(np.percentile(diffs, 5)), 'upper90': float(np.percentile(diffs, 95)), 'draws': draws, 'seed': seed, 'n_union': len(allids)}


def main():
    c0 = {}
    for t in V.SEASONS:
        ref = ROOT / 'reports/card-0.2.9/ranking.csv' if t == '2025-26' else ROOT / f'reports/card-0.2.8+E158-young-under-T6/ranking-Y0-{t}.csv'
        c0[t] = {'K_sha': P.sha(rp('K', t)), 'ref_sha': P.sha(ref), 'same': P.sha(rp('K', t)) == P.sha(ref)}
    ok = all(v['same'] for v in c0.values())
    print('c0', 'PASS' if ok else 'FAIL')
    if not ok:
        (HERE / 'results.json').write_text(json.dumps({'c0': c0, 'c0_pass': False}, indent=1), encoding='utf-8')
        sys.exit(2)
    D = V.load({a: {t: rp(a, t) for t in V.SEASONS} for a in ARMS})
    masks, minfo = {}, {}
    for t in V.SEASONS:
        masks[t], minfo[t] = submask(D, t)
    psA = V.per_season(D, 'v2')
    psS = per_sub(D, masks, V.SEASONS)
    res = {'c0': c0, 'c0_pass': True, 'seed': SEED, 'draws': V.B, 'n_eval': {t: len(D['seasons'][t]['ids']) for t in V.SEASONS},
           'subgroup': minfo, 'per_season_all': psA, 'per_season_sub': psS, 'cand': {}}
    for c in ('P15', 'P30'):
        bt = boot_sub(D, c, 'K', V.JUDGE, masks, SEED)
        dy = {k: V.pooled(psS, c, 'K', V.JUDGE, k) for k in ('C',) + V.KEYS}
        da = {k: V.pooled(psA, c, 'K', V.JUDGE, k) for k in ('C',) + V.KEYS}
        a_ = dy['C'] >= 0.01 and bt['lower90'] > -0.02
        b_ = da['C'] >= -0.005
        c_ = {'sal': da['sal'] >= -0.02, 'twok': da['twok'] >= -0.02, 'rapm': da['rapm'] >= -0.05, 'epm': da['epm'] >= -0.05}
        res['cand'][c] = {'sub_diff': dy, 'all_diff': da, 'sub_boot': bt, 'a': bool(a_), 'a_diff_ge_0.01': bool(dy['C'] >= 0.01),
                          'a_lower_gt_-0.02': bool(bt['lower90'] > -0.02), 'b': bool(b_), 'c': {k: bool(v) for k, v in c_.items()},
                          'pass': bool(a_ and b_ and all(c_.values()))}
    p = [c for c in ('P15', 'P30') if res['cand'][c]['pass']]
    if not p:
        pick = 'K (維持 0.2.9)'
    elif len(p) == 1:
        pick = p[0]
    else:
        d1, d3 = res['cand']['P15']['sub_diff']['C'], res['cand']['P30']['sub_diff']['C']
        pick = 'P15' if (abs(d1 - d3) < 0.005 or d1 > d3) else 'P30'
    res['verdict'] = pick
    res['y2526'] = {a: {'all': psA['2025-26'][a], 'sub': psS['2025-26'][a]} for a in ARMS}
    rk, ov, pos = {}, {}, {}
    for a in ARMS:
        rows = [(r['name'], float(r['ovr']), r['pos']) for r in csv.DictReader(open(rp(a, '2025-26'), encoding='utf-8-sig')) if float(r['MIN']) >= 500]
        rows.sort(key=lambda x: -x[1])
        rk[a] = {n: i + 1 for i, (n, _, _) in enumerate(rows)}
        ov[a] = {n: o for n, o, _ in rows}
        pos = {n: q for n, _, q in rows}
    names = list(rk['K'])

    def find(k):
        m = [n for n in names if P.norm(n) == P.norm(k)] or [n for n in names if P.norm(k) in P.norm(n)]
        return m[0] if m else None
    d = D['seasons']['2025-26']
    subnames = [d['names'][i] for i in np.where(masks['2025-26'])[0]]
    mv = sorted(((rk['K'][n] - rk['P30'][n], n) for n in subnames), reverse=True)  # 正＝升
    up5, dn5 = [n for _, n in mv[:5]], [n for _, n in mv[-5:]][::-1]
    keyrows = {}
    for k in KEY + up5 + dn5:
        n = find(k) if k in KEY else k
        if n:
            keyrows[n] = {a: {'rank': rk[a][n], 'ovr': ov[a][n]} for a in ARMS}
        else:
            keyrows[k] = None
    res['key_players'] = keyrows
    res['sub_up5_K_to_P30'] = up5
    res['sub_down5_K_to_P30'] = dn5
    top = {a: sorted(rk[a], key=rk[a].get) for a in ARMS}
    bigs = [n for n in top['K'] if pos[n] in ('C', 'PF')][:10]
    res['K_top10_bigs'] = {n: {'pos': pos[n], **{a: rk[a][n] for a in ARMS}} for n in bigs}
    res['top20'] = {a: top[a][:20] for a in ARMS}
    res['top20_changes'] = {c: {'in': [n for n in top[c][:20] if n not in top['K'][:20]], 'out': [n for n in top['K'][:20] if n not in top[c][:20]]} for c in ('P15', 'P30')}
    res['moved10_top300'] = {c: sum(1 for n in top['K'][:300] if abs(rk[c].get(n, 999) - rk['K'][n]) >= 10) for c in ('P15', 'P30')}
    res['sha256'] = {f'{a}-{t}': P.sha(rp(a, t)) for a in ARMS for t in V.SEASONS}
    for a in ARMS:
        for t in V.SEASONS:
            shutil.copy(rp(a, t), HERE / f'ranking-{a}-{t}.csv')
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('verdict', 'cand', 'subgroup', 'n_eval')}, ensure_ascii=False, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ('y2526', 'key_players', 'K_top10_bigs', 'top20_changes', 'moved10_top300', 'sub_up5_K_to_P30', 'sub_down5_K_to_P30')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
