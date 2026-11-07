"""評分 M6 參數與驗收（E-150，spec：reports/rating-m6/spec.md）。

用法（順序固定）：
  python -I scripts/fit_rating_m6.py fit    只用 2025-26 A 半（int(GAME_ID)%2==0）定 TS_lg、TSA36_lg、TS_repl、PACE_lg、a'、c'；
                                            另用整季重算上線版 → params.json（寫完先單獨 commit，之後才准跑 eval／a5）
  python -I scripts/fit_rating_m6.py eval   2025-26 B 半驗收 C1 C2 T3 T4 A4 A7＋A8、λ 自然實驗重跑（M4 同口徑基準）→ eval.json
  python -I scripts/fit_rating_m6.py a5     A5 範例（2026-27）→ a5.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_rating_m3 as f3  # noqa: E402
import fit_rating_m4 as f4  # noqa: E402
import rating_m6 as m6  # noqa: E402
from rating_m3 import Table, _rs, season_dir, wquant  # noqa: E402
from rating_m6 import OUT, ROOT, bonus, score_arrays  # noqa: E402

M4P = ROOT / 'reports' / 'rating-m4' / 'params.json'


def tsa_ts(t):
    tsa = t.fga + 0.44 * t.fta
    return tsa, np.where(tsa > 0, t.pts / (2 * np.where(tsa > 0, tsa, 1)), 0.0)


def constants(t, mask):
    """spec §3：TS_lg、TSA36_lg、TS_repl、PACE_lg。"""
    tsa, _ = tsa_ts(t)
    C = dict(TS_lg=float(t.pts[mask].sum() / (2 * tsa[mask].sum())),
             TSA36_lg=float(tsa[mask].sum() / t.mn[mask].sum() * 36))
    acc = defaultdict(lambda: [0.0, 0.0, 0.0])
    for i in np.where(mask)[0]:
        a = acc[t.pid[i]]
        a[0] += t.pts[i]; a[1] += tsa[i]; a[2] += t.mn[i]
    big = [(a[0] / (2 * a[1]), a[2]) for a in acc.values() if a[2] >= 500 and a[1] > 0]
    C['TS_repl'] = float(wquant([b[0] for b in big], [b[1] for b in big], 0.2))
    halves = set(int(g) % 2 for g in t.gid[mask])
    h, rows = _rs(season_dir('2025-26') / 'team-games.json')
    poss = mins = 0.0
    for r in rows:
        if int(r[h['GAME_ID']]) % 2 not in halves:
            continue
        poss += r[h['FGA']] + 0.44 * r[h['FTA']] - r[h['OREB']] + r[h['TOV']]
        m = r[h['MIN']]
        mins += m / 5 if m > 100 else m
    C['PACE_lg'] = float(poss / mins * 48)
    return C


def scale(t, mask, P4, C):
    C = dict(C, a=0.0, c=1.0)
    Gp, _ = score_arrays(t, P4, C)
    sel = mask & (t.mn >= 10)
    med, p94 = float(np.median(Gp[sel])), float(np.percentile(Gp[sel], 94))
    C['c'] = (10 - 5.8) / (p94 - med)
    C['a'] = 5.8 - C['c'] * med
    return C


def fit():
    cur = Table('2025-26')
    A = cur.half == 0
    p4 = json.loads(M4P.read_text(encoding='utf-8'))
    P4a, P4p = p4['chosen']['P'], p4['prod']['P']
    Ca = scale(cur, A, P4a, constants(cur, A))
    allm = np.ones(len(cur), bool)
    Cp = scale(cur, allm, P4p, constants(cur, allm))
    _, Sp = score_arrays(cur, P4p, Cp)
    cut1, cut5 = f4.cuts(cur, Sp)
    out = dict(
        spec_sha256=f3.sha(OUT / 'spec.md'), fit_data='2025-26 A half (int(GAME_ID)%2==0) only; prod = whole 2025-26 same rules',
        fixed=dict(lam=m6.LAM, g=m6.G_MULT, delta=m6.DELTA),
        inputs={'player-games 2025-26': f3.sha(season_dir('2025-26') / 'player-games.json'),
                'team-games 2025-26': f3.sha(season_dir('2025-26') / 'team-games.json'),
                'm4 params': f3.sha(M4P), 'm2 weights': f3.sha(f3.rating_m2.M2 / 'weights.json')},
        chosen=dict(P4=P4a, C=Ca), prod=dict(P4=P4p, C=Cp, cut1=cut1, cut5=cut5))
    (OUT / 'params.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('A half C', json.dumps(Ca))
    print('prod C', json.dumps(Cp), cut1, cut5)


def above_median(t, B, S, sel):
    med = {pid: float(np.median(S[B & (t.pid == pid)])) for pid in np.unique(t.pid[sel])}
    idx = np.where(sel)[0]
    return float(np.mean([S[i] > med[t.pid[i]] for i in idx])) if len(idx) else float('nan'), int(len(idx))


def lam_experiment(rows, h):
    """spec §2 λ 依據重跑：A 半，各隊出手前 2 名（≥15 場）缺陣時，其他球員每 36 出手與 TS 的變化（Wald）。"""
    rows = [r for r in rows if int(r[h['GAME_ID']]) % 2 == 0 and (r[h['MIN']] or 0) > 0]
    tsa = lambda r: r[h['FGA']] + 0.44 * r[h['FTA']]
    pt = defaultdict(lambda: [0, 0, 0])
    games, team_games = defaultdict(set), defaultdict(set)
    for r in rows:
        a = pt[(r[h['TEAM_ID']], r[h['PLAYER_ID']])]
        a[0] += tsa(r); a[1] += r[h['MIN']]; a[2] += 1
        games[(r[h['TEAM_ID']], r[h['GAME_ID']])].add(r[h['PLAYER_ID']]); team_games[r[h['TEAM_ID']]].add(r[h['GAME_ID']])
    stars = {}
    for tm in team_games:
        c = [(a[0] / a[2], p) for (tt, p), a in pt.items() if tt == tm and a[2] >= 15]
        stars[tm] = {p for _, p in sorted(c, reverse=True)[:2]}
    acc = defaultdict(lambda: {0: [0, 0, 0], 1: [0, 0, 0]})
    for r in rows:
        tm, p, g = r[h['TEAM_ID']], r[h['PLAYER_ID']], r[h['GAME_ID']]
        if p in stars[tm]:
            continue
        a = acc[p][int(len(stars[tm] - games[(tm, g)]) > 0)]
        a[0] += r[h['PTS']]; a[1] += tsa(r); a[2] += r[h['MIN']]
    d = []
    for s in acc.values():
        a, b = s[0], s[1]
        if a[2] < 300 or b[2] < 100 or a[1] < 30 or b[1] < 20:
            continue
        d.append((b[1] / b[2] * 36 - a[1] / a[2] * 36, b[0] / (2 * b[1]) - a[0] / (2 * a[1]), 1 / (1 / a[1] + 1 / b[1])))
    W = sum(w for *_, w in d)
    mU, mT = sum(u * w for u, _, w in d) / W, sum(x * w for _, x, w in d) / W
    return dict(n=len(d), dU36=mU, dTS_pp=mT * 100, wald_pp_per_shot=mT / mU * 100)


def evaluate():
    P0 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))
    P4, C = P0['chosen']['P4'], P0['chosen']['C']
    cur = Table('2025-26')
    B = cur.half == 1
    _, _, _, S4 = f4.score_arrays(cur, P4)
    Gp, S6 = score_arrays(cur, P4, C)
    Bp, BG, f, E = bonus(cur, C)
    tsa, ts = tsa_ts(cur)
    res = {}
    for k, S in (('M4', S4), ('M6', S6)):
        res[k] = f3.full_metrics(cur, B, S, k)
        res[k]['T4 低於本人中位比例'], res[k]['T4 n'] = f4.t4(cur, B, S)
        res[k]['A4 前6%中<15分鐘佔比'], res[k]['A4 全部場次<15分鐘佔比'] = f4.a4_ok(cur, B, S)
        sel = B & (cur.mn >= 25) & (tsa >= 25) & (ts >= C['TS_lg'])
        res[k]['C1 高量有效率高於本人中位比例'], res[k]['C1 n'] = above_median(cur, B, S, sel)
    rank4, rank6 = res['M4'].pop('_rank'), res['M6'].pop('_rank')
    band = (ts >= C['TS_lg'] - 0.08) & (ts < C['TS_lg'])
    hi, lo = B & (tsa >= 25) & band, B & (tsa <= 12) & band
    c2 = dict(hi_n=int(hi.sum()), hi_mean_diff=float((S6 - S4)[hi].mean()),
              lo_n=int(lo.sum()), lo_max_abs_diff=float(np.abs(S6 - S4)[lo].max()), lo_bonus_max=float(Bp[lo].max()))
    sel10 = B & (cur.mn >= 10)
    a8 = dict(var_share=float(np.var(BG[sel10]) / np.var(Gp[sel10])), B_mean=float(Bp[sel10].mean()),
              B_p99=float(np.percentile(Bp[sel10], 99)), share_E_pos=float((E[sel10] > 0).mean()),
              share_f_partial_of_Epos=float(((f > 0) & (f < 1) & (E > 0))[sel10].sum() / max(1, (E[sel10] > 0).sum())))
    h, rows = _rs(season_dir('2025-26') / 'player-games.json')
    m4_ref = json.loads((ROOT / 'reports/rating-m4/eval.json').read_text(encoding='utf-8'))['M4']
    m4_check = {k: [res['M4'][k], m4_ref.get(k)] for k in res['M4'] if k in m4_ref}
    m4, m6_ = res['M4'], res['M6']
    judge = {
        'C1': m6_['C1 高量有效率高於本人中位比例'] >= 0.8 and m6_['C1 高量有效率高於本人中位比例'] > m4['C1 高量有效率高於本人中位比例'],
        'C2': c2['hi_mean_diff'] > 0 and c2['lo_max_abs_diff'] < 1e-9,
        'T3': m6_['T3 前30用掉回合者名次中位數'] < m4['T3 前30用掉回合者名次中位數'],
        'T4': m6_['T4 低於本人中位比例'] >= 0.8,
        'A4': m6_['A4 前6%中<15分鐘佔比'] <= m6_['A4 全部場次<15分鐘佔比'],
        'A7': all(m6_[k] >= m4[k] - 0.03 for k in ('T2 ρ(平均評分,自製EPM net)', 'A7 ρ(平均評分,DARKO)', 'A7 前後半 r')),
    }
    judge['all_pass'] = all(judge.values())
    names = {int(p): n for p, n in zip(cur.pid, cur.name)}
    res.update(C2=c2, A8=a8, lam_rerun=lam_experiment(rows, h), m4_vs_E146=m4_check, judge=judge,
               T3_list=[dict(name=names[p], m4=rank4[p], m6=rank6[p]) for p in rank4])
    (OUT / 'eval.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{"":40s} {"M4":>9s} {"M6":>9s}')
    for k in res['M4']:
        print(f'{k:40s} {res["M4"][k]:9.4f} {res["M6"][k]:9.4f}')
    for k in ('C2', 'A8', 'lam_rerun', 'judge'):
        print(k, json.dumps(res[k], ensure_ascii=False))
    print('M4 vs E-146', json.dumps(m4_check, ensure_ascii=False))


def a5():
    P0 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))['prod']
    t = Table('2026-27')
    _, _, _, S4 = f4.score_arrays(t, P0['P4'])
    _, S6 = score_arrays(t, P0['P4'], P0['C'])
    Bp, _, f, E = bonus(t, P0['C'])
    tsa, ts = tsa_ts(t)
    fgm = np.array([r[t.h['FGM']] or 0 for r in t.rows], float)
    row = lambda i: dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fg=f'{int(fgm[i])}/{int(t.fga[i])}',
                         fta=int(t.fta[i]), ts=round(float(ts[i]), 3), E=round(float(E[i]), 1), f=round(float(f[i]), 2),
                         m4=round(float(S4[i]), 2), m6=round(float(S6[i]), 2))
    pick = lambda nm, d: [row(i) for i in range(len(t)) if nm in str(t.name[i]) and str(t.date[i]).endswith(d)]
    out = dict(
        named=pick('Scottie Barnes', '10-30') + pick('Jalen Brunson', '10-25') + pick('Anthony Edwards', '10-23'),
        players={nm: dict(n=int(m.sum()), m4=float(S4[m].mean()), m6=float(S6[m].mean()))
                 for nm, m in ((nm, np.array([nm in str(x) for x in t.name])) for nm in ('Gilgeous', 'Wembanyama', 'Caruso'))},
        top10_m6=[row(i) for i in np.argsort(-S6, kind='stable')[:10]],
        role_low_volume=[row(i) for i in sorted(np.where((t.mn >= 28) & (E == 0) & (ts > 0.6))[0], key=lambda i: -S4[i])[:3]])
    (OUT / 'a5.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'fit': fit, 'eval': evaluate, 'a5': a5}[sys.argv[1]]()
