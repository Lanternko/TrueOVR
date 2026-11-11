"""E-191b：用 MIN>=500 人群、沒看過的季（2023-24、2024-25）重判 threeValue 的池（預註冊見 prereg-b.md）。
用法：python -I -X utf8 reports/E191-threevalue-dispersion/run_b.py
輸出 results-b.json；採用時另寫 three-value-candidate.csv。不改任何 live／card 檔。"""
import csv, json, sys
from pathlib import Path
import numpy as np

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import run as R  # noqa: E402

W10, SV, ROOT, K0 = R.W10, R.SV, R.ROOT, R.K0
JUDGE = ('2023-24', '2024-25')
SEAS = sorted(SV)
yr = lambda s: int(s[:4])


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

    def value(s):
        n, a, mn, mu = raw(s)
        acc = (n + K0 * mu) / (a + K0)
        vol = np.where(mn > 0, a / np.where(mn > 0, mn, 1) * 36, np.nan)
        return vol * (acc - (mu - W10.THREE_REP_GAP))

    c_rows = {int(r['playerId']): r for r in csv.DictReader(open(R.TV10C, encoding='utf-8'))}
    d_rows = list(csv.DictReader(open(R.TV10D, encoding='utf-8')))
    tv26 = SV['2025-26']
    nl = json.loads((ROOT / 'reports/ovr-v62-3pt-difficulty-2025-26/new-long.json').read_text(encoding='utf-8'))
    has = {int(r['playerId']) for r in d_rows if r['playerId'] in nl and r['playerId'] in tv26}

    def prior(s):
        return [t for t in SEAS if yr(s) - 3 <= yr(t) <= yr(s) - 1]

    def cohort(t, min_rule, s_is_card=False):
        """{pid: 窗口值}；min_rule＝'season'（SV 該季 MIN>=500）或 'window'（窗口加權 MIN>=500）。s_is_card＝2025-26 項限 has。"""
        x, mn = value(t), raw(t)[2]
        out = {}
        for p, v in SV[t].items():
            q = int(p)
            if q not in ix or np.isnan(x[ix[q]]):
                continue
            if s_is_card and q not in has:
                continue
            ok = (v['MIN'] or 0) >= 500 if min_rule == 'season' else mn[ix[q]] >= 500
            if ok:
                out[q] = float(x[ix[q]])
        return out

    def single_pool(s):
        return [float(v['value']) for t in prior(s) for v in SV[t].values() if (v['MIN'] or 0) >= 500] + [float(v['value']) for v in SV[s].values() if (v['MIN'] or 0) >= 500]

    def arm_pool(s, arm):
        card = s == '2025-26'
        if arm == 'U0':
            return [float(v['value']) for t in prior(s) for v in SV[t].values() if (v['MIN'] or 0) >= 500] + list(cohort(s, 'season', card).values())
        rule = 'season' if arm == 'P1' else 'window'
        return [x for t in prior(s) for x in cohort(t, rule).values()] + list(cohort(s, rule, card).values())

    def mapper(pool):
        return W10.L.PctMapper(pool, R.TOP, R.BOT)

    def pop_of(s):
        x = value(s)
        out = [int(p) for p, v in SV[s].items() if (v['MIN'] or 0) >= 500 and int(p) in ix and not np.isnan(x[ix[int(p)]])]
        if s == '2025-26':
            out = [q for q in out if q in has and q in c_rows]
        return out

    def num_map(s, arm, qs):
        x = value(s)
        return dict(zip(qs, map(float, mapper(arm_pool(s, arm))(np.array([x[ix[q]] for q in qs])))))

    out = {'note': 'prereg-b.md'}
    # ---- c0
    q26 = pop_of('2025-26')
    sd_c = float(np.std([float(c_rows[q]['tv_main']) for q in q26]))
    u0 = num_map('2025-26', 'U0', q26)
    c0_ratio = float(np.std([u0[q] for q in q26]) / sd_c)
    ref = json.loads((H / 'posthoc_min500.json').read_text(encoding='utf-8'))['U0']['ratio']
    assert len(q26) == 378 or len(q26) == 379, len(q26)
    assert abs(c0_ratio - ref) < 1e-6, (c0_ratio, ref)
    sx = {int(p): float(v['value']) for p, v in tv26.items()}
    qa = [q for q in c_rows if str(q) in tv26 and q in has]
    sm = dict(zip(qa, mapper(single_pool('2025-26'))(np.array([sx[q] for q in qa]))))
    c0_single = max(abs(float(c_rows[q]['tv_main']) - sm[q]) for q in qa)
    assert c0_single < 1e-6, c0_single
    out['c0'] = {'n': len(q26), 'U0_ratio_2025-26_min500': c0_ratio, 'ref': ref, 'single_recipe_maxdiff_vs_0.2.10c': c0_single, 'n_single_check': len(qa)}
    info = {}
    for arm in ('P1', 'P1m'):
        m = num_map('2025-26', arm, q26)
        info[arm] = float(np.std([m[q] for q in q26]) / sd_c)
    out['info_2025-26_ratio'] = info

    # ---- 判準季
    res = {}
    for s in JUDGE:
        qs = pop_of(s)
        den = dict(zip(qs, map(float, mapper(single_pool(s))(np.array([float(SV[s][str(q)]['value']) for q in qs])))))
        sd_den = float(np.std([den[q] for q in qs]))
        r = {'n_pop': len(qs), 'prior_seasons': prior(s), 'sd_single': sd_den}
        for arm in ('U0', 'P1', 'P1m'):
            m = num_map(s, arm, qs)
            sd = float(np.std([m[q] for q in qs]))
            r[arm] = {'sd': sd, 'ratio': sd / sd_den, 'n_pool': len(arm_pool(s, arm))}
        res[s] = r
    out['judge'] = res

    def passes(arm):
        ok = all(0.95 <= res[s][arm]['ratio'] <= 1.05 and abs(res[s][arm]['ratio'] - 1) < abs(res[s]['U0']['ratio'] - 1) for s in JUDGE)
        mean = float(np.mean([res[s][arm]['ratio'] for s in JUDGE]))
        return ok, mean
    pa = {arm: passes(arm) for arm in ('P1', 'P1m')}
    ok = [a for a in ('P1', 'P1m') if pa[a][0]]
    if len(ok) == 2:
        adopt = 'P1' if abs(pa['P1'][1] - 1) <= abs(pa['P1m'][1] - 1) else 'P1m'
    else:
        adopt = ok[0] if ok else None
    out['pass'] = {a: {'passes': pa[a][0], 'mean_ratio': pa[a][1]} for a in pa}
    out['U0_mean_ratio'] = float(np.mean([res[s]['U0']['ratio'] for s in JUDGE]))
    out['adopt'] = adopt

    # ---- 證據（2025-26 卡片端）與草案
    allp = [int(r['playerId']) for r in d_rows if int(r['playerId']) in has]
    x26 = value('2025-26')
    qall = [q for q in allp if q in ix and not np.isnan(x26[ix[q]])]
    maps = {}
    for arm in ('U0', 'P1', 'P1m'):
        maps[arm] = num_map('2025-26', arm, qall)
    rank_of = lambda m: {q: i + 1 for i, q in enumerate(sorted(m, key=lambda q: -m[q]))}
    r0 = rank_of(maps['U0'])
    pid_name = {int(r['playerId']): r['name'] for r in d_rows}
    ev = {}
    for key in ('jovic', 'lonzo ball', "de'andre hunter", 'stephen curry', 'domantas sabonis', 'sengun'):
        for q in qall:
            nm = R.norm(pid_name[q])
            if key in nm:
                ev[pid_name[q]] = {'tv_0210c': float(c_rows[q]['tv_main']) if q in c_rows else None, 'U0': maps['U0'][q], 'P1': maps['P1'][q], 'P1m': maps['P1m'][q],
                                   'rank_U0': r0[q], 'rank_P1': rank_of(maps['P1'])[q], 'rank_P1m': rank_of(maps['P1m'])[q]}
    out['evidence'] = ev
    if adopt:
        fm = maps[adopt]
        rc = rank_of(fm)
        n_, a_, mn_, mu_ = raw('2025-26')
        acc = (n_ + K0 * mu_) / (a_ + K0)
        with open(H / 'three-value-candidate.csv', 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['playerId', 'name', 'team', 'MIN', 'long', 'vol', 'acc', 'value_main', 'tv_main', 'tv_0210d', 'rank_0210d', 'rank_cand'])
            for r in d_rows:
                q = int(r['playerId'])
                if q in fm:
                    w.writerow([q, r['name'], r['team'], r['MIN'], r['long'], r['vol'], repr(float(acc[ix[q]])), repr(float(x26[ix[q]])), repr(fm[q]), r['tv_main'], r0[q], rc[q]])
                else:
                    w.writerow([q, r['name'], r['team'], r['MIN'], r['long'], r['vol'], r['acc'], r['value_main'], r['tv_main'], r['tv_main'], '', ''])
        out['candidate_sha256'] = R.sha(H / 'three-value-candidate.csv')
        out['candidate_rank_corr_vs_0210d'] = float(R.spearmanr([fm[q] for q in fm], [maps['U0'][q] for q in fm])[0])
    (H / 'results-b.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
