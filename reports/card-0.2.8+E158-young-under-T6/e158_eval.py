"""E-158 評估（預註冊 §3、§4）。用 E-157 eval_v2。seed 20261102、2000 次。用法（repo root）：python -I -B -X utf8 <本檔>"""
import csv, json, shutil, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))
import eval_v2 as V
P = V.P
SEED = 20261102
ARMS = ['K', 'Y1', 'Y0']
E153W = ROOT / 'reports/card-0.2.7d+E153-t6-target/work'
KEY = ['Cooper Flagg', 'Kon Knueppel', 'Paolo Banchero', 'Dylan Harper', 'Stephon Castle', 'Ron Holland', 'Jaylen Wells', 'Anthony Edwards',
       'Brandin Podziemski', 'Victor Wembanyama', 'Shai Gilgeous-Alexander', 'Nikola Jokić']


def rp(a, t):
    return HERE / 'work' / f'{a}-{t}' / 'out' / 'ranking.csv'


def main():
    c0 = {}
    for t in V.SEASONS:
        ref = (E153W / 'K6-2025-26/c0/ranking.csv') if t == '2025-26' else (E153W / f'K6-{t}/{t}/out/K0/ranking.csv')
        c0[t] = {'K_sha': P.sha(rp('K', t)), 'K6_sha': P.sha(ref), 'same': P.sha(rp('K', t)) == P.sha(ref)}
    c0['2025-26']['card028_sha'] = P.sha(ROOT / 'reports/card-0.2.8/ranking.csv')
    c0['2025-26']['same_card028'] = c0['2025-26']['K_sha'] == c0['2025-26']['card028_sha']
    ok = all(v['same'] for v in c0.values()) and c0['2025-26']['same_card028']
    print('c0', 'PASS' if ok else 'FAIL')
    if not ok:
        (HERE / 'results.json').write_text(json.dumps({'c0': c0, 'c0_pass': False}, indent=1), encoding='utf-8')
        sys.exit(2)
    D = V.load({a: {t: rp(a, t) for t in V.SEASONS} for a in ARMS})
    psA, psY = V.per_season(D, 'v2'), V.per_season(D, 'v2', 'young')
    res = {'c0': c0, 'c0_pass': True, 'seed': SEED, 'draws': V.B, 'n_eval': {t: len(D['seasons'][t]['ids']) for t in V.SEASONS},
           'n_young': {t: int(D['seasons'][t]['young'].sum()) for t in V.SEASONS}, 'per_season_all': psA, 'per_season_young': psY, 'cand': {}}
    for c in ('Y1', 'Y0'):
        bt = V.boot(D, c, 'K', V.JUDGE, SEED, 'v2', 'young')
        dy = {k: V.pooled(psY, c, 'K', V.JUDGE, k) for k in ('C',) + V.KEYS}
        da = {k: V.pooled(psA, c, 'K', V.JUDGE, k) for k in ('C',) + V.KEYS}
        a_ = dy['C'] >= 0.01 and bt['lower90'] > -0.02
        b_ = da['C'] >= -0.005
        c_ = {'sal': da['sal'] >= -0.02, 'twok': da['twok'] >= -0.02, 'rapm': da['rapm'] >= -0.05, 'epm': da['epm'] >= -0.05}
        res['cand'][c] = {'young_diff': dy, 'all_diff': da, 'young_boot': bt, 'a': bool(a_), 'a_diff_ge_0.01': bool(dy['C'] >= 0.01),
                          'a_lower_gt_-0.02': bool(bt['lower90'] > -0.02), 'b': bool(b_), 'c': {k: bool(v) for k, v in c_.items()},
                          'pass': bool(a_ and b_ and all(c_.values()))}
    p = [c for c in ('Y1', 'Y0') if res['cand'][c]['pass']]
    if not p:
        pick = 'K (維持 0.2.8)'
    elif len(p) == 1:
        pick = p[0]
    else:
        d1, d0 = res['cand']['Y1']['young_diff']['C'], res['cand']['Y0']['young_diff']['C']
        pick = 'Y1' if (abs(d1 - d0) < 0.005 or d1 > d0) else 'Y0'
    res['verdict'] = pick
    res['y2526'] = {a: {'all': psA['2025-26'][a], 'young': psY['2025-26'][a]} for a in ARMS}
    rk, ov = {}, {}
    for a in ARMS:
        rows = [(r['name'], float(r['ovr'])) for r in csv.DictReader(open(rp(a, '2025-26'), encoding='utf-8-sig')) if float(r['MIN']) >= 500]
        rows.sort(key=lambda x: -x[1])
        rk[a] = {n: i + 1 for i, (n, _) in enumerate(rows)}
        ov[a] = {n: o for n, o in rows}
    names = list(rk['K'])

    def find(k):
        m = [n for n in names if P.norm(n) == P.norm(k)] or [n for n in names if P.norm(k) in P.norm(n)]
        return m[0] if m else None
    dump = json.loads((HERE / 'work/K-2025-26/out/usage-dump.json').read_text(encoding='utf-8'))
    coef = dump['wls'][-1]
    f = dump['full']
    disc = {q: coef[8] * f['y'][i] * f['d'][i] * f['L'][i] for i, q in enumerate(f['pid']) if f['y'][i] == 1.0}
    d = D['seasons']['2025-26']
    pn = dict(zip(d['ids'], d['names']))
    dl = sorted([(v, pn[q]) for q, v in disc.items() if q in pn and pn[q] in rk['K']])[:5]
    keyrows = {}
    for k in KEY + [n for _, n in dl]:
        n = find(k) if k in KEY else k
        if n:
            keyrows[n] = {a: {'rank': rk[a][n], 'ovr': ov[a][n]} for a in ARMS}
    res['coef_ydL_K'] = coef[8]
    res['top5_ydL_discount'] = [{'name': n, 'raw_discount': v} for v, n in dl]
    res['key_players'] = keyrows
    res['usage_coef_last'] = {a: json.loads((HERE / f'work/{a}-2025-26/out/usage-dump.json').read_text(encoding='utf-8'))['wls'][-1] for a in ARMS}
    top = {a: sorted(rk[a], key=rk[a].get) for a in ARMS}
    res['top20'] = {a: top[a][:20] for a in ARMS}
    res['top20_changes'] = {c: {'in': [n for n in top[c][:20] if n not in top['K'][:20]], 'out': [n for n in top['K'][:20] if n not in top[c][:20]]} for c in ('Y1', 'Y0')}
    res['moved10_top300'] = {c: sum(1 for n in top['K'][:300] if abs(rk[c].get(n, 999) - rk['K'][n]) >= 10) for c in ('Y1', 'Y0')}
    yng = set(d['names'][i] for i in range(len(d['ids'])) if d['young'][i])
    ytop = {a: [n for n in top[a] if n in yng][:30] for a in ARMS}
    res['young_top30'] = ytop
    res['young_top30_changes'] = {c: {'in': [n for n in ytop[c] if n not in ytop['K']], 'out': [n for n in ytop['K'] if n not in ytop[c]]} for c in ('Y1', 'Y0')}
    res['young_top30_rank_move'] = {c: {n: (rk['K'][n], rk[c][n]) for n in ytop['K']} for c in ('Y1', 'Y0')}
    res['sha256'] = {f'{a}-{t}': P.sha(rp(a, t)) for a in ARMS for t in V.SEASONS}
    for a in ARMS:
        for t in V.SEASONS:
            shutil.copy(rp(a, t), HERE / f'ranking-{a}-{t}.csv')
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({'verdict': pick, 'cand': res['cand']}, ensure_ascii=False, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ('y2526', 'key_players', 'top5_ydL_discount', 'top20_changes', 'moved10_top300', 'young_top30_changes',
                                          'coef_ydL_K', 'usage_coef_last', 'n_eval', 'n_young')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
