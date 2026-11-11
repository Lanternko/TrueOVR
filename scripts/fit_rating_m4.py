"""評分 M4 擬合與驗收（E-146，spec：reports/rating-m4/spec.md）。

用法（順序固定）：
  python -I scripts/fit_rating_m4.py fit    只用 2025-26 A 半（int(GAME_ID)%2==0）：七個 β_q 候選各定 μ、K、R、a、c，算 J、q 佔比；選 β_q；
                                            另用整季重算上線版 → params.json（寫完先單獨 commit＋push，之後才准跑 eval／a5）
  python -I scripts/fit_rating_m4.py eval   2025-26 B 半驗收 T1 T2 T3 T4 A4 A7（M2 同口徑基準）→ eval.json
  python -I scripts/fit_rating_m4.py a5     A5 範例（2026-27／B 半）→ a5.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_rating_m3 as f3  # noqa: E402
import rating_m4 as m4  # noqa: E402
from rating_m3 import Table, player_means, wquant  # noqa: E402
from rating_m4 import OUT, ROOT, score_arrays, xval  # noqa: E402

GRID_Q = [0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]
GRID_K = list(range(0, 121, 2))
Q_SHARE_MAX = 0.30


def a4_ok(t, mask, G):
    idx = np.where(mask)[0]
    k = int(round(0.06 * len(idx)))
    top = idx[np.argsort(-G[idx], kind='stable')[:k]]
    return float((t.mn[top] < 15).mean()), float((t.mn[idx] < 15).mean())


def derive(cur, mask, bq):
    """順序：μ、K、R、a、c（spec §2）。"""
    x = xval(cur, bq)
    mu = float((x * cur.mn)[mask].sum() / cur.mn[mask].sum())
    pm = player_means(cur, x, mask)
    big = [(xb, M) for _, (M, xb) in pm.items() if M >= 300]
    R = wquant([b[0] for b in big], [b[1] for b in big], 0.2)
    P = dict(bq=bq, mu=mu, R=R, K=120, a=0.0, c=1.0, k_reached=False)
    for K in GRID_K:
        P['K'] = K
        _, _, G, _ = score_arrays(cur, P)
        top_share, all_share = a4_ok(cur, mask, G)
        if top_share <= all_share:
            P['k_reached'] = True
            break
    P['a4_top_share'], P['a4_all_share'] = top_share, all_share
    _, _, G, _ = score_arrays(cur, P)
    sel = mask & (cur.mn >= 10)
    med, p94 = float(np.median(G[sel])), float(np.percentile(G[sel], 94))
    P['c'] = (10 - 5.8) / (p94 - med)
    P['a'] = 5.8 - P['c'] * med
    return P


def cuts(cur, S):
    d1, d5 = [], []
    for pid in np.unique(cur.pid):
        idx = np.where(cur.pid == pid)[0]
        idx = idx[np.argsort(cur.date[idx].astype(str), kind='stable')]
        s = S[idx]
        b = s.mean()
        d1 += list(np.abs(s[cur.mn[idx] >= 10] - b))
        d5 += [abs(s[j:j + 5].mean() - b) for j in range(len(s) - 4)]
    return ([round(float(x), 1) for x in np.percentile(d1, [20, 60])],
            [round(float(x), 1) for x in np.percentile(d5, [20, 60])])


def fit():
    cur = Table('2025-26')
    A = cur.half == 0
    epm = f3.load_ext(f3.EPM, 'net')
    hg = f3.half_games_of(cur, A)
    sel = A & (cur.mn >= 10)
    grid = []
    for bq in GRID_Q:
        P = derive(cur, A, bq)
        x, xs, G, S = score_arrays(cur, P)
        Gq = bq * (cur.pm * 36 / cur.mn) * cur.mn / (cur.mn + P['K']) * cur.mn / 36
        share = float(np.var(Gq[sel]) / np.var(G[sel]))
        m = f3.metrics_core(cur, A, S, epm, 250, hg)
        J = m['rho_epm'] + m['rho_epm_share'] + m['r_pm']
        grid.append(dict(P=P, q_share=share, feasible=share <= Q_SHARE_MAX, J=J, **m))
    ok = [g for g in grid if g['feasible']]
    best = max(ok, key=lambda g: (round(g['J'], 9), -g['P']['bq']))
    # 上線版：bq 用 A 半選定值，其餘整季重算
    allm = np.ones(len(cur), bool)
    Pp = derive(cur, allm, best['P']['bq'])
    _, _, _, Sp = score_arrays(cur, Pp)
    cut1, cut5 = cuts(cur, Sp)
    out = dict(
        spec_sha256=f3.sha(OUT / 'spec.md'), fit_data='2025-26 A half (int(GAME_ID)%2==0) only; prod = whole 2025-26 with chosen bq',
        inputs={'player-games 2025-26': f3.sha(m4.season_dir('2025-26') / 'player-games.json'),
                'team-games 2025-26': f3.sha(m4.season_dir('2025-26') / 'team-games.json'),
                'epm_self 2025-26': f3.sha(f3.EPM), 'm2 weights': f3.sha(f3.rating_m2.M2 / 'weights.json'),
                'matchup-source 2025-26': f3.sha_dir(ROOT / 'data/matchup-source/2025-26')},
        q_share_def='Var(β_q·q·MIN/(MIN+K)·MIN/36) / Var(G)，A 半 ≥10 分鐘單場',
        J_def='ρ(A 半平均評分, EPM net)(≥250 A 半分鐘) + ρ(…, EPM net × A 半分鐘佔比) + r(單場≥10 分鐘評分, 球隊淨勝分)',
        chosen=best, grid=grid, prod=dict(P=Pp, cut1=cut1, cut5=cut5))
    (OUT / 'params.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for g in grid:
        P = g['P']
        print(f'bq={P["bq"]:.2f} K={P["K"]}{"" if P["k_reached"] else "(未達成)"} mu={P["mu"]:.3f} R={P["R"]:.3f} a={P["a"]:.3f} c={P["c"]:.4f} '
              f'J={g["J"]:.4f} ({g["rho_epm"]:.3f},{g["rho_epm_share"]:.3f},{g["r_pm"]:.3f}) qshare={g["q_share"]:.3f}{"" if g["feasible"] else " X"}')
    print('chosen bq', best['P']['bq'], 'prod P', json.dumps(Pp), cut1, cut5)


def t4(cur, B, S):
    fgm = np.array([r[cur.h['FGM']] or 0 for r in cur.rows], float)
    med = {}
    for pid in np.unique(cur.pid[B]):
        med[pid] = float(np.median(S[B & (cur.pid == pid)]))
    sel = np.where(B & (cur.mn >= 30) & (cur.fga >= 15) & (fgm <= 0.3 * cur.fga))[0]
    below = [S[i] < med[cur.pid[i]] for i in sel]
    return float(np.mean(below)), len(sel)


def evaluate():
    P0 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))
    cur = Table('2025-26')
    A, B = cur.half == 0, cur.half == 1
    res = {}
    S2 = np.maximum(0, 0.75 * (cur.v + 7.5))
    res['M2'] = f3.full_metrics(cur, B, S2, 'M2')
    res['M2']['T4 低於本人中位比例'], res['M2']['T4 n'] = t4(cur, B, S2)
    P = P0['chosen']['P']
    _, _, _, S = score_arrays(cur, P)
    res['M4'] = f3.full_metrics(cur, B, S, 'M4')
    res['M4']['T4 低於本人中位比例'], res['M4']['T4 n'] = t4(cur, B, S)
    P0b = derive(cur, A, 0)
    _, _, _, S0 = score_arrays(cur, P0b)
    res['M4_noq'] = f3.full_metrics(cur, B, S0, 'noq')
    res['M4_noq']['T4 低於本人中位比例'], res['M4_noq']['T4 n'] = t4(cur, B, S0)
    res['M4_noq_params'] = P0b
    names = {int(p): n for p, n in zip(cur.pid, cur.name)}
    top30 = list(res['M4']['_rank'].keys())
    res['T3_top10'] = [dict(pid=p, name=names[p], m2_rank=res['M2']['_rank'][p], m4_rank=res['M4']['_rank'][p]) for p in top30[:10]]
    for k in ('M2', 'M4', 'M4_noq'):
        res[k].pop('_rank', None)
    m2, m4_ = res['M2'], res['M4']
    judge = {
        'T1': m4_['T1 r(單場≥10分,淨勝分)'] > m2['T1 r(單場≥10分,淨勝分)'],
        'T2': m4_['T2 ρ(平均評分,自製EPM net)'] >= m2['T2 ρ(平均評分,自製EPM net)'] and m4_['T2 ρ(平均評分,EPM net×分鐘佔比)'] > m2['T2 ρ(平均評分,EPM net×分鐘佔比)'],
        'T3': m4_['T3 前30用掉回合者名次中位數'] < m2['T3 前30用掉回合者名次中位數'],
        'T4': m4_['T4 低於本人中位比例'] >= 0.8,
        'A4': m4_['A4 前6%中<15分鐘佔比'] <= m4_['A4 全部場次<15分鐘佔比'],
        'A7': m4_['A7 ρ(平均評分,DARKO)'] >= m2['A7 ρ(平均評分,DARKO)'] - 0.03 and m4_['A7 前後半 r'] >= m2['A7 前後半 r'] - 0.03,
    }
    judge['all_pass'] = all(judge.values())
    res['judge'] = judge
    (OUT / 'eval.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{"":40s} {"M2":>9s} {"M4":>9s} {"M4無q":>9s}')
    for k in [k for k in res['M2'] if not k.startswith('_')]:
        print(f'{k:40s} {res["M2"][k]:9.4f} {res["M4"][k]:9.4f} {res["M4_noq"][k]:9.4f}')
    print(judge)
    for r in res['T3_top10']:
        print(r)


def a5():
    cur = Table('2025-26')
    sc = m4.Scorer('2026-27')
    out = {}
    for tag, t, S4 in (('2025-26B', cur, score_arrays(cur, sc.P)[3]), ('2026-27', sc.tab, sc.S)):
        S2 = np.maximum(0, 0.75 * (t.v + 7.5))
        base = (t.half == 1) if tag == '2025-26B' else np.ones(len(t), bool)
        ex = {}
        for key, nm in (('Caruso', 'Caruso'), ('SGA', 'Gilgeous'), ('Wembanyama', 'Wembanyama')):
            idx = [i for i in range(len(t)) if nm in str(t.name[i]) and base[i]]
            ex[key] = [dict(date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fga=int(t.fga[i]), pm=float(t.pm[i]), m2=float(S2[i]), m4=float(S4[i]))
                       for i in sorted(idx, key=lambda i: str(t.date[i]))]
        top = lambda arr: [dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), pm=float(t.pm[i]), score=float(arr[i]))
                           for i in np.argsort(-arr, kind='stable')[:10]]
        rec = {}
        seen = set()
        for tid, gid, w in zip(t.tid, t.gid, t.twin):
            if (tid, gid) in seen:
                continue
            seen.add((tid, gid))
            a = rec.setdefault(tid, [0, 0])
            a[0] += w
            a[1] += 1
        weak = {tid for tid, (w, n) in rec.items() if n >= 10 and w / n < 0.4}
        thr = np.percentile(S4[base & (t.mn >= 10)], 90)
        cand = [i for i in np.where(base & (t.mn >= 30) & (S4 >= thr))[0] if t.tid[i] in weak]
        cand = sorted(cand, key=lambda i: -S4[i])[:8]
        weak_ex = [dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fga=int(t.fga[i]), pm=float(t.pm[i]),
                        team_rec=f'{int(rec[t.tid[i]][0])}-{int(rec[t.tid[i]][1] - rec[t.tid[i]][0])}', m2=float(S2[i]), m4=float(S4[i])) for i in cand]
        fgm = np.array([r[t.h['FGM']] or 0 for r in t.rows], float)
        bad = list(np.where(base & (t.mn >= 30) & (t.fga >= 15) & (fgm <= 0.3 * t.fga))[0])
        bad = sorted(bad, key=lambda i: -t.pts[i])[:8]
        bad_ex = [dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fgm=int(fgm[i]), fga=int(t.fga[i]), pm=float(t.pm[i]),
                       m2=float(S2[i]), m4=float(S4[i])) for i in bad]
        out[tag] = dict(examples=ex, top10_m2=top(S2), top10_m4=top(S4), weak_burst=weak_ex, bad_games=bad_ex, p90=float(thr))
    (OUT / 'a5.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for tag, d in out.items():
        print('==', tag)
        for k, v in d['examples'].items():
            print(k, 'n', len(v), 'avg M2 %.2f M4 %.2f' % (np.mean([g['m2'] for g in v]), np.mean([g['m4'] for g in v])) if v else '')
        print('TOP10 M4', *d['top10_m4'], sep='\n  ')
        print('WEAK', *d['weak_burst'], sep='\n  ')
        print('BAD', *d['bad_games'], sep='\n  ')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'fit': fit, 'eval': evaluate, 'a5': a5}[sys.argv[1]]()
