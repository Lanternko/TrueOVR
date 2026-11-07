"""E-191：threeValue 窗口版離散度縮小（預註冊見 prereg.md）。用法：python -I -X utf8 reports/E191-threevalue-dispersion/run.py
輸出 results.json；若採用規則判定要改，另寫 three-value-candidate.csv。不改任何 live／card 檔。"""
import csv, hashlib, json, sys, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import window10 as W10  # noqa: E402

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
K0 = W10.THREE_K
KS = {'K0.5': K0 * 0.5, 'K1': K0, 'K2': K0 * 2}
E123W = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/work'
SV = json.loads((E123W / 'season-values.json').read_text(encoding='utf-8'))['vals']['T']
H1 = json.loads((E123W.parent / 'h1-results.json').read_text(encoding='utf-8'))['h1']['threeValue']
TOP, BOT = bool(H1['top']['pass']), bool(H1['bot']['pass'])
PAST = ('2022-23', '2023-24', '2024-25')
TV10C = ROOT / 'reports/card-0.2.10c/three-value.csv'
TV10D = ROOT / 'reports/card-0.2.10d/three-value.csv'
NAMES = {'Jović': 'jovic', 'Lonzo Ball': 'lonzo ball', "De'Andre Hunter": "de'andre hunter", 'Curry': 'stephen curry', 'Sabonis': 'domantas sabonis'}
norm = lambda s: ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def main():
    W = W10.Win10()
    ix = {int(p): i for i, p in enumerate(W.D.pids)}
    cache = {}

    def raw(s):
        if s not in cache:
            cur, G = W.season_cur(s)
            n, a, mn = W.tv_raw(G, cur, s, G, 4)
            m_, a_ = W10.lg_total(W.T10[s])
            cache[s] = (n, a, mn, m_ / a_)
        return cache[s]

    def value(s, K):
        n, a, mn, mu = raw(s)
        acc = (n + K * mu) / (a + K)
        vol = np.where(mn > 0, a / np.where(mn > 0, mn, 1) * 36, np.nan)
        return vol * (acc - (mu - W10.THREE_REP_GAP))

    # ---- 與 window10.tv_value 對帳
    n, a, mn, mu = raw('2025-26')
    chk = np.nanmax(np.abs(value('2025-26', K0) - W.tv_value(n, a, mn, mu)[2]))
    assert chk < 1e-12, chk

    # ---- 排名判準
    def rank_corr(end, target, K):
        x = value(end, K)
        xs, ys = [], []
        for pid, v in SV[target].items():
            q = int(pid)
            if (v['MIN'] or 0) >= 500 and q in ix and not np.isnan(x[ix[q]]):
                xs.append(x[ix[q]]); ys.append(float(v['value']))
        return float(spearmanr(xs, ys)[0]), len(xs)
    sel = {k: rank_corr('2023-24', '2024-25', K) for k, K in KS.items()}
    conf = {k: rank_corr('2024-25', '2025-26', K) for k, K in KS.items()}
    best = max(sel, key=lambda k: (sel[k][0], k == 'K1'))      # 平手留原 K
    k_change = bool(best != 'K1' and conf[best][0] - conf['K1'][0] >= 0.01)
    k_final = best if k_change else 'K1'

    # ---- 尺度判準
    c_rows = {int(r['playerId']): r for r in csv.DictReader(open(TV10C, encoding='utf-8'))}
    d_rows = list(csv.DictReader(open(TV10D, encoding='utf-8')))
    tv26 = SV['2025-26']
    nl = json.loads((ROOT / 'reports/ovr-v62-3pt-difficulty-2025-26/new-long.json').read_text(encoding='utf-8'))
    has = [int(r['playerId']) for r in d_rows if r['playerId'] in nl and r['playerId'] in tv26]

    def cur_vals(K):
        v = value('2025-26', K)
        return {q: float(v[ix[q]]) for q in has if q in ix and not np.isnan(v[ix[q]])}

    def pool_past_single():
        return [float(v['value']) for s in PAST for v in SV[s].values() if (v['MIN'] or 0) >= 500]

    def pool_past_window(K):
        out = []
        for s in PAST:
            x = value(s, K)
            out += [float(x[ix[int(p)]]) for p, v in SV[s].items() if (v['MIN'] or 0) >= 500 and int(p) in ix and not np.isnan(x[ix[int(p)]])]
        return out

    def mapped(K, pool_kind):
        cv = cur_vals(K)
        pool = (pool_past_single() if pool_kind == 'U0' else pool_past_window(K)) + [cv[q] for q in cv if (tv26[str(q)]['MIN'] or 0) >= 500]
        mp = W10.L.PctMapper(pool, TOP, BOT)
        qs_ = list(cv)
        return dict(zip(qs_, map(float, mp(np.array([cv[q] for q in qs_]))))), len(pool)

    base, _ = mapped(K0, 'U0')
    ref_d = {int(r['playerId']): float(r['tv_main']) for r in d_rows}
    selfcheck = max(abs(ref_d[q] - base[q]) for q in base)
    assert selfcheck < 1e-6, selfcheck
    qs = [q for q in base if q in c_rows]
    sd = lambda m: float(np.std([m[q] for q in qs]))
    sd_c = float(np.std([float(c_rows[q]['tv_main']) for q in qs]))
    arms = {}
    for name, (K, kind) in {'U0': (K0, 'U0'), 'P1': (K0, 'P1'), 'K0.5': (KS['K0.5'], 'P1'), 'K2': (KS['K2'], 'P1')}.items():
        m, npool = mapped(K, kind)
        top50 = sorted((m[q] for q in qs), reverse=True)[:50]
        arms[name] = {'map': m, 'n_pool': npool, 'sd': sd(m), 'ratio': sd(m) / sd_c, 'n': len(qs),
                      'top50': {'min': top50[-1], 'q25': float(np.percentile(top50, 25)), 'median': float(np.median(top50)), 'q75': float(np.percentile(top50, 75)),
                                'max': top50[0], 'n_ge99': int(sum(v >= 99 for v in top50))}}
    c_top = sorted((float(c_rows[q]['tv_main']) for q in qs), reverse=True)[:50]
    r_u0, r_p1 = arms['U0']['ratio'], arms['P1']['ratio']
    adopt_p1 = bool(0.95 <= r_p1 <= 1.05 and abs(r_p1 - 1) < abs(r_u0 - 1))
    pool_final = 'P1' if adopt_p1 else 'U0'
    changed = adopt_p1 or k_change

    # ---- 診斷（不進判準）
    cvs = cur_vals(K0)
    diag = {'sd_raw_window_2025-26': float(np.std([cvs[q] for q in cvs if (tv26[str(q)]['MIN'] or 0) >= 500])),
            'sd_raw_single_2025-26': float(np.std([float(v['value']) for v in tv26.values() if (v['MIN'] or 0) >= 500])),
            'sd_tv_0210c': sd_c, 'n_players': len(qs), 'U0_selfcheck_maxdiff_vs_0.2.10d': selfcheck}

    # ---- 候選
    final_map = None
    if changed:
        final_map, _ = mapped(KS[k_final], pool_final)
    cand_arm = 'U0' if not changed else f'{pool_final}+{k_final}'
    rank_of = lambda m: {q: i + 1 for i, q in enumerate(sorted(m, key=lambda q: -m[q]))}
    r0, rc = rank_of(base), (rank_of(final_map) if final_map else None)
    if changed:
        Kf = KS[k_final]
        n_, a_, mn_, mu_ = raw('2025-26')
        acc = (n_ + Kf * mu_) / (a_ + Kf)
        vv = value('2025-26', Kf)
        with open(H / 'three-value-candidate.csv', 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['playerId', 'name', 'team', 'MIN', 'long', 'vol', 'acc', 'value_main', 'tv_main', 'tv_0210d', 'rank_0210d', 'rank_cand'])
            for r in d_rows:
                q = int(r['playerId'])
                if q in final_map:
                    i = ix[q]
                    w.writerow([q, r['name'], r['team'], r['MIN'], r['long'], r['vol'], repr(float(acc[i])), repr(float(vv[i])), repr(final_map[q]), r['tv_main'], r0[q], rc[q]])
                else:
                    w.writerow([q, r['name'], r['team'], r['MIN'], r['long'], r['vol'], r['acc'], r['value_main'], r['tv_main'], r['tv_main'], '', ''])
    # ---- 直觀證據
    pid_name = {int(r['playerId']): r['name'] for r in d_rows}
    ev = {}
    for lab, key in NAMES.items():
        hit = [q for q in qs if norm(pid_name[q]) == key or (lab == 'Jović' and 'jovic' in norm(pid_name[q]))]
        for q in hit:
            ev[pid_name[q]] = {'tv_0210c': float(c_rows[q]['tv_main']), 'U0': arms['U0']['map'][q], 'P1': arms['P1']['map'][q],
                               'K0.5': arms['K0.5']['map'][q], 'K2': arms['K2']['map'][q], 'rank_U0': r0[q], 'rank_cand': rc[q] if rc else None}
    out = {'K0': K0, 'topbot': [TOP, BOT], 'selection_2023-24_to_2024-25': {k: {'spearman': v[0], 'n': v[1]} for k, v in sel.items()},
           'confirm_2024-25_to_2025-26': {k: {'spearman': v[0], 'n': v[1]} for k, v in conf.items()},
           'best_K_in_selection': best, 'k_change': k_change, 'K_final': k_final,
           'scale': {k: {kk: vv_ for kk, vv_ in v.items() if kk != 'map'} for k, v in arms.items()},
           'top50_0210c': {'min': c_top[-1], 'median': float(np.median(c_top)), 'max': c_top[0], 'n_ge99': int(sum(v >= 99 for v in c_top))},
           'adopt_P1': adopt_p1, 'changed': changed, 'candidate_arm': cand_arm, 'diag': diag, 'evidence': ev,
           'candidate_sha256': sha(H / 'three-value-candidate.csv') if changed else None}
    (H / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
