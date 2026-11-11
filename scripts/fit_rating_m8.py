"""評分 M8 參數與驗收（E-167，預註冊：reports/rating-m8-smooth/preregistration.md）。

用法（順序固定）：
  python -I scripts/fit_rating_m8.py fit    各臂在 2025-26 A 半重定 a、c；另用整季算上線版 → params.json
                                            （寫完先單獨 commit，之後才准跑 eval／a5）
  python -I scripts/fit_rating_m8.py eval   2025-26 B 半驗收 M4／M6／S1／S3／S13 → eval.json
  python -I scripts/fit_rating_m8.py a5     A5 範例（2026-27，上線版常數）→ a5.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_rating_m3 as f3  # noqa: E402
import fit_rating_m4 as f4  # noqa: E402
import fit_rating_m6 as f6  # noqa: E402
import rating_m2  # noqa: E402
import rating_m6 as m6  # noqa: E402
from rating_m3 import Table, season_dir  # noqa: E402
from rating_m8 import ARMS, OUT, ROOT, bonus, score_arrays  # noqa: E402

M6P = ROOT / 'reports' / 'rating-m6' / 'params.json'
PRE = OUT / 'preregistration.md'
C1K, T3K = 'C1 高量有效率高於本人中位比例', 'T3 前30用掉回合者名次中位數'
A7K = ('T2 ρ(平均評分,自製EPM net)', 'A7 ρ(平均評分,DARKO)', 'A7 前後半 r')


def scale(t, mask, P4, C, arm):
    C = dict(C, a=0.0, c=1.0)
    Gp, _ = score_arrays(t, P4, C, arm)
    sel = mask & (t.mn >= 10)
    med, p94 = float(np.median(Gp[sel])), float(np.percentile(Gp[sel], 94))
    C['c'] = (10 - 5.8) / (p94 - med)
    C['a'] = 5.8 - C['c'] * med
    return C


def fit():
    cur = Table('2025-26')
    p6 = json.loads(M6P.read_text(encoding='utf-8'))
    for k in ('chosen', 'prod'):  # M6 臂逐位元重現 rating_m6
        assert np.array_equal(bonus(cur, p6[k]['C'], 0.10, False)[1], m6.bonus(cur, p6[k]['C'])[1])
    A, allm = cur.half == 0, np.ones(len(cur), bool)
    out = dict(prereg_sha256=f3.sha(PRE), fit_data='M6 constants reused; a/c per arm: 2025-26 A half >=10 min (chosen), whole 2025-26 (prod)',
               arms={k: dict(delta=d, linear_X=l) for k, (d, l) in ARMS.items()},
               inputs={'player-games 2025-26': f3.sha(season_dir('2025-26') / 'player-games.json'), 'm6 params': f3.sha(M6P)},
               chosen=dict(P4=p6['chosen']['P4'], **{k: scale(cur, A, p6['chosen']['P4'], p6['chosen']['C'], k) for k in ARMS}),
               prod=dict(P4=p6['prod']['P4'], **{k: scale(cur, allm, p6['prod']['P4'], p6['prod']['C'], k) for k in ARMS}))
    (OUT / 'params.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['chosen'], indent=1))


def perturbed(t, rater, sel):
    """sel 內每場把一顆沒進的兩分改成進：PTS+2、FGM+1，M2 貢獻值重算。"""
    t2 = Table.__new__(Table)
    t2.__dict__.update({k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in t.__dict__.items()})
    h = t.h
    for i in np.where(sel)[0]:
        r = list(t.rows[i])
        r[h['PTS']] += 2
        r[h['FGM']] += 1
        if 'FG_PCT' in h:
            r[h['FG_PCT']] = r[h['FGM']] / r[h['FGA']]
        t2.v[i] = rater.value(r, h)
        t2.pts[i] += 2
    return t2


def all_scores(t, P4, C6, P8):
    _, _, _, S4 = f4.score_arrays(t, P4)
    sc = {'M4': S4, 'M6': m6.score_arrays(t, P4, C6)[1]}
    for k in ARMS:
        sc[k] = score_arrays(t, P4, dict(C6, a=P8[k]['a'], c=P8[k]['c']), k)[1]
    return sc


def fake_grid(rater, P4, C6, P8):
    """§3 假場次：36 分鐘、全兩分、罰球 4 中 3，5 板 4 助 1 抄 2 失誤 2 犯規，正負值 0。"""
    from rating_m3 import _rs
    h, rows = _rs(season_dir('2025-26') / 'player-games.json')
    tpl = next(r for r in rows if r[h['MIN']] and 35 <= float(r[h['MIN']]) <= 37 and not rater.fallback(r, h) and r[h['FGA']] == 15)
    specs = [(25, m) for m in (16, 14, 13, 12, 11, 10, 9, 7)] + [(n, n // 2) for n in (8, 12, 16, 20, 24, 28, 32, 36)] \
        + [(n, round(n * .44)) for n in (9, 16, 23, 27, 32, 36)]
    rs = []
    for fga, fgm in specs:
        r = list(tpl)
        for k, v in dict(MIN=36, FGA=fga, FGM=fgm, FG3A=0, FG3M=0, FTA=4, FTM=3, PTS=2 * fgm + 3, OREB=1, DREB=4, REB=5,
                         AST=4, STL=1, BLK=0, TOV=2, PF=2, PLUS_MINUS=0, FG_PCT=fgm / fga).items():
            if k in h:
                r[h[k]] = v
        rs.append(r)
    t = Table.__new__(Table)
    t.rows, t.h = rs, h
    t.mn = np.full(len(rs), 36.0)
    t.v = np.array([rater.value(r, h) for r in rs])
    for a, k in (('pts', 'PTS'), ('fga', 'FGA'), ('fta', 'FTA'), ('tov', 'TOV'), ('pm', 'PLUS_MINUS')):
        setattr(t, a, np.array([r[h[k]] for r in rs], float))
    sc = all_scores(t, P4, C6, P8)
    return [dict(fg=f'{m}/{n}', pts=2 * m + 3, **{k: round(float(S[i]), 2) for k, S in sc.items()}) for i, (n, m) in enumerate(specs)]


def evaluate():
    P8 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['chosen']
    P6 = json.loads(M6P.read_text(encoding='utf-8'))['chosen']
    P4, C6 = P6['P4'], P6['C']
    rater = rating_m2.Rater('2025-26')
    cur = Table('2025-26', rater)
    B = cur.half == 1
    tsa, ts = f6.tsa_ts(cur)
    scores = all_scores(cur, P4, C6, P8)
    res = {}
    for k, S in scores.items():
        res[k] = f3.full_metrics(cur, B, S, k)
        res[k].pop('_rank')
        res[k]['T4 低於本人中位比例'], res[k]['T4 n'] = f4.t4(cur, B, S)
        res[k]['A4 前6%中<15分鐘佔比'], res[k]['A4 全部場次<15分鐘佔比'] = f4.a4_ok(cur, B, S)
        sel = B & (cur.mn >= 25) & (tsa >= 25) & (ts >= C6['TS_lg'])
        res[k][C1K], res[k]['C1 n'] = f6.above_median(cur, B, S, sel)
    ref = json.loads((m6.OUT / 'eval.json').read_text(encoding='utf-8'))
    c0 = {k: {m: [res[k][m], ref[k].get(m)] for m in res[k] if m in ref[k]} for k in ('M4', 'M6')}
    res['c0'] = dict(ok=bool(all(abs(a - b) < 1e-9 for k in c0 for a, b in c0[k].values() if b is not None)), detail=c0)
    # P1：一顆沒進的兩分改成進
    fgm = np.array([r[cur.h['FGM']] or 0 for r in cur.rows], float)
    psel = B & (tsa >= 20) & (fgm < cur.fga)
    sc2 = all_scores(perturbed(cur, rater, psel), P4, C6, P8)
    res['P1'] = {k: dict(n=int(psel.sum()), median=float(np.median((sc2[k] - S)[psel])), p90=float(np.percentile((sc2[k] - S)[psel], 90)))
                 for k, S in scores.items()}
    m4, m6r = res['M4'], res['M6']
    S4 = scores['M4']
    hi = B & (tsa >= 25) & (ts >= C6['TS_lg'] - 0.08) & (ts < C6['TS_lg'])
    judge = {}
    for k in ARMS:
        r = res[k]
        j = {'P1': bool(res['P1'][k]['p90'] <= 0.8 * res['P1']['M6']['p90']),
             'C1': bool(r[C1K] >= m6r[C1K] - 0.05),
             'A7': bool(all(r[x] >= m6r[x] - 0.03 for x in A7K)),
             'T3': bool(r[T3K] <= m6r[T3K] + 5),
             'C2前半': bool((scores[k] - S4)[hi].mean() > 0),
             'T4': bool(r['T4 低於本人中位比例'] >= 0.8),
             'A4': bool(r['A4 前6%中<15分鐘佔比'] <= r['A4 全部場次<15分鐘佔比'])}
        j['all_pass'] = all(j.values())
        judge[k] = j
    passing = [k for k in ARMS if judge[k]['all_pass']]
    if passing:
        best = min(res['P1'][k]['p90'] for k in passing)
        pick = next(k for k in ARMS if k in passing and res['P1'][k]['p90'] - best < 0.05)
    else:
        pick = 'M6（維持）'
    judge['pick'] = pick
    res['judge'] = judge
    grp = {'量大效率低於聯盟(TSA>=30, TS<TS_lg)': B & (tsa >= 30) & (ts < C6['TS_lg']),
           '低效率大量(TSA>=25, TS<TS_lg-0.08)': B & (tsa >= 25) & (ts < C6['TS_lg'] - 0.08),
           '30投6中類(FGA>=25, FG%<=30%)': B & (cur.fga >= 25) & (fgm <= 0.3 * cur.fga),
           '低量角色場(TSA<=12)': B & (tsa <= 12)}
    res['report_only'] = {g: dict(n=int(m.sum()), **{k: float(S[m].mean()) for k, S in scores.items()}) for g, m in grp.items()}
    res['fake'] = fake_grid(rater, P4, C6, P8)
    (OUT / 'eval.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print('c0', res['c0']['ok'])
    print(f'{"":40s}' + ''.join(f'{k:>9s}' for k in scores))
    for m in res['M4']:
        print(f'{m:40s}' + ''.join(f'{res[k][m]:9.4f}' for k in scores))
    for k in ('P1', 'judge', 'report_only', 'fake'):
        print(k, json.dumps(res[k], ensure_ascii=False, indent=1))


def a5():
    P = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
    P6 = json.loads(M6P.read_text(encoding='utf-8'))['prod']
    t = Table('2026-27')
    sc = all_scores(t, P6['P4'], P6['C'], P)
    tsa, ts = f6.tsa_ts(t)
    fgm = np.array([r[t.h['FGM']] or 0 for r in t.rows], float)
    row = lambda i: dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fg=f'{int(fgm[i])}/{int(t.fga[i])}',
                         fta=int(t.fta[i]), ts=round(float(ts[i]), 3), **{k: round(float(S[i]), 2) for k, S in sc.items()})
    pick = lambda nm, d: [row(i) for i in range(len(t)) if nm in str(t.name[i]) and str(t.date[i]).endswith(d)]
    out = dict(named=pick('Scottie Barnes', '10-30') + pick('Jalen Brunson', '10-25') + pick('Anthony Edwards', '10-23'),
               players={nm: dict(n=int(m.sum()), **{k: float(S[m].mean()) for k, S in sc.items()})
                        for nm, m in ((nm, np.array([nm in str(x) for x in t.name])) for nm in ('Gilgeous', 'Wembanyama', 'Caruso'))},
               **{f'top10_{k}': [row(i) for i in np.argsort(-S, kind='stable')[:10]] for k, S in sc.items()})
    (OUT / 'a5.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'fit': fit, 'eval': evaluate, 'a5': a5}[sys.argv[1]]()
