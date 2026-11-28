"""評分 M7 參數與驗收（E-165，預註冊：reports/rating-m7-gmsc/preregistration.md）。

用法（順序固定）：
  python -I scripts/fit_rating_m7.py fit    2025-26 A 半定 z 的平均／標準差與 a″、c″（G15、G30）；另用整季算上線版 → params.json
                                            （寫完先單獨 commit，之後才准跑 eval／a5）
  python -I scripts/fit_rating_m7.py eval   2025-26 B 半驗收 M4／M6／G15／G30 → eval.json
  python -I scripts/fit_rating_m7.py a5     A5 範例（2026-27，上線版常數）→ a5.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_rating_m3 as f3  # noqa: E402
import fit_rating_m4 as f4  # noqa: E402
import fit_rating_m6 as f6  # noqa: E402
import rating_m4  # noqa: E402
import rating_m6 as m6  # noqa: E402
from rating_m3 import Table, season_dir  # noqa: E402
from rating_m7 import ARMS, OUT, ROOT, gmsc, score_arrays  # noqa: E402

M4P = ROOT / 'reports' / 'rating-m4' / 'params.json'
M6P = ROOT / 'reports' / 'rating-m6' / 'params.json'
PRE = OUT / 'preregistration.md'


def constants(t, mask, P4, w):
    _, _, G, _ = rating_m4.score_arrays(t, P4)
    S = gmsc(t)
    sel = mask & (t.mn >= 10)
    C = dict(muG=float(G[sel].mean()), sdG=float(G[sel].std()), muS=float(S[sel].mean()), sdS=float(S[sel].std()))
    C = dict(C, a=0.0, c=1.0)
    Gpp = score_arrays(t, P4, C, w)[0]
    med, p94 = float(np.median(Gpp[sel])), float(np.percentile(Gpp[sel], 94))
    C['c'] = (10 - 5.8) / (p94 - med)
    C['a'] = 5.8 - C['c'] * med
    return C


def fit():
    cur = Table('2025-26')
    A = cur.half == 0
    allm = np.ones(len(cur), bool)
    p4 = json.loads(M4P.read_text(encoding='utf-8'))
    P4a, P4p = p4['chosen']['P'], p4['prod']['P']
    out = dict(prereg_sha256=f3.sha(PRE), fit_data='2025-26 A half (int(GAME_ID)%2==0) >=10 min for z / a / c; prod = whole 2025-26 same rules',
               w=ARMS, inputs={'player-games 2025-26': f3.sha(season_dir('2025-26') / 'player-games.json'), 'm4 params': f3.sha(M4P)},
               chosen=dict(P4=P4a, **{k: constants(cur, A, P4a, w) for k, w in ARMS.items()}),
               prod=dict(P4=P4p, **{k: constants(cur, allm, P4p, w) for k, w in ARMS.items()}))
    (OUT / 'params.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['chosen'], indent=1))
    print(json.dumps(out['prod'], indent=1))


def evaluate():
    P7 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['chosen']
    P6 = json.loads(M6P.read_text(encoding='utf-8'))
    P4, C6 = P6['chosen']['P4'], P6['chosen']['C']
    assert P4 == P7['P4']
    cur = Table('2025-26')
    B = cur.half == 1
    tsa, ts = f6.tsa_ts(cur)
    _, _, _, S4 = f4.score_arrays(cur, P4)
    _, S6 = m6.score_arrays(cur, P4, C6)
    scores = {'M4': S4, 'M6': S6}
    Gpp, zs = {}, {}
    for k, w in ARMS.items():
        Gpp[k], scores[k], zG, zS = score_arrays(cur, P4, P7[k], w)
        zs[k] = (zG, zS)
    res = {}
    for k, S in scores.items():
        res[k] = f3.full_metrics(cur, B, S, k)
        res[k].pop('_rank')
        res[k]['T4 低於本人中位比例'], res[k]['T4 n'] = f4.t4(cur, B, S)
        res[k]['A4 前6%中<15分鐘佔比'], res[k]['A4 全部場次<15分鐘佔比'] = f4.a4_ok(cur, B, S)
        sel = B & (cur.mn >= 25) & (tsa >= 25) & (ts >= C6['TS_lg'])
        res[k]['C1 高量有效率高於本人中位比例'], res[k]['C1 n'] = f6.above_median(cur, B, S, sel)
    # c0：M4、M6 對 E-150 eval.json
    ref = json.loads((m6.OUT / 'eval.json').read_text(encoding='utf-8'))
    c0 = {k: {m: [res[k][m], ref[k].get(m)] for m in res[k] if m in ref[k]} for k in ('M4', 'M6')}
    c0_ok = all(abs(a - b) < 1e-9 for k in c0 for a, b in c0[k].values() if b is not None)
    res['c0'] = dict(ok=bool(c0_ok), detail=c0, missing_keys=[(k, m) for k in ('M4', 'M6') for m in res[k] if m not in ref[k]])
    band = (ts >= C6['TS_lg'] - 0.08) & (ts < C6['TS_lg'])
    hi = B & (tsa >= 25) & band
    A7K = ('T2 ρ(平均評分,自製EPM net)', 'A7 ρ(平均評分,DARKO)', 'A7 前後半 r')
    C1K, T3K = 'C1 高量有效率高於本人中位比例', 'T3 前30用掉回合者名次中位數'
    m4, m6r = res['M4'], res['M6']
    judge = {}
    for k in ARMS:
        r = res[k]
        j = {'C1': bool(r[C1K] >= 0.8 and r[C1K] > m4[C1K]),
             'C2前半': bool((scores[k] - S4)[hi].mean() > 0),
             'T3': bool(r[T3K] < m4[T3K]), 'T4': bool(r['T4 低於本人中位比例'] >= 0.8),
             'A4': bool(r['A4 前6%中<15分鐘佔比'] <= r['A4 全部場次<15分鐘佔比']),
             'A7': bool(all(r[x] >= m4[x] - 0.03 for x in A7K)),
             'D1': bool(all(r[x] >= m6r[x] - 0.03 for x in A7K) and r[C1K] >= m6r[C1K] - 0.05)}
        j['all_pass'] = all(j.values())
        j['C2前半 hi_mean_diff'] = float((scores[k] - S4)[hi].mean())
        judge[k] = j
    passing = [k for k in ARMS if judge[k]['all_pass']]
    if not passing:
        pick = 'M6（維持）'
    elif len(passing) == 1:
        pick = passing[0]
    else:
        d = res['G30'][C1K] - res['G15'][C1K]
        pick = 'G30' if d >= 0.02 else 'G15'
    judge['pick'] = pick
    res['judge'] = judge
    # 預註冊 §3 只報告
    fgm = np.array([r[cur.h['FGM']] or 0 for r in cur.rows], float)
    grp = {'低效率大量(TSA>=25, TS<TS_lg-0.08)': B & (tsa >= 25) & (ts < C6['TS_lg'] - 0.08),
           '30投6中類(FGA>=25, FG%<=30%)': B & (cur.fga >= 25) & (fgm <= 0.3 * cur.fga),
           '低量角色場(TSA<=12)': B & (tsa <= 12)}
    res['report_only'] = {g: dict(n=int(m.sum()), **{k: float(S[m].mean()) for k, S in scores.items()},
                                  **{f'{k}-M4': float((S - S4)[m].mean()) for k, S in scores.items() if k != 'M4'}) for g, m in grp.items()}
    sel10 = B & (cur.mn >= 10)
    res['A8'] = {k: dict(GmSc項變異佔比=float(np.var(ARMS[k] * zs[k][1][sel10]) / np.var(Gpp[k][sel10])),
                         zG與zS相關=float(np.corrcoef(zs[k][0][sel10], zs[k][1][sel10])[0, 1])) for k in ARMS}
    (OUT / 'eval.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print('c0', res['c0']['ok'], res['c0']['missing_keys'])
    print(f'{"":40s}' + ''.join(f'{k:>9s}' for k in scores))
    for m in res['M4']:
        print(f'{m:40s}' + ''.join(f'{res[k][m]:9.4f}' for k in scores))
    for k in ('judge', 'report_only', 'A8'):
        print(k, json.dumps(res[k], ensure_ascii=False, indent=1))


def a5():
    P = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
    P6 = json.loads(M6P.read_text(encoding='utf-8'))['prod']
    t = Table('2026-27')
    _, _, _, S4 = f4.score_arrays(t, P['P4'])
    _, S6 = m6.score_arrays(t, P6['P4'], P6['C'])
    sc = {'M4': S4, 'M6': S6}
    for k, w in ARMS.items():
        sc[k] = score_arrays(t, P['P4'], P[k], w)[1]
    tsa, ts = f6.tsa_ts(t)
    gm = gmsc(t)
    fgm = np.array([r[t.h['FGM']] or 0 for r in t.rows], float)
    row = lambda i: dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fg=f'{int(fgm[i])}/{int(t.fga[i])}',
                         fta=int(t.fta[i]), ts=round(float(ts[i]), 3), gmsc=round(float(gm[i]), 1), **{k: round(float(S[i]), 2) for k, S in sc.items()})
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
