"""評分 M5 擬合與驗收（E-148，spec：reports/rating-m5/spec.md，凍結 sha256 cb41c4b5…ab53）。

用法（順序固定，L-026）：
  python -I scripts/fit_rating_m5.py fit    只用 2025-26 A 半（int(GAME_ID)%2==0）：七個 β_q 候選各定 μ、K、R、a、c，算 J（EPM＋DARKO）、q 佔比；
                                            選 β_q；上線版用整季重算 → params.json（寫完先單獨 commit＋push，之後才准跑 eval／a5）
  python -I scripts/fit_rating_m5.py eval   2025-26 B 半驗收 V0 B1 B2 T2 A7 T3 T4 A4（判定）、T1（只報告）；M4 同口徑重算 → eval.json
  python -I scripts/fit_rating_m5.py a5     A5 範例 → a5.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_rating_m3 as f3  # noqa: E402
import fit_rating_m4 as f4  # noqa: E402
import rating_m4 as m4  # noqa: E402
from rating_m3 import player_means, wquant  # noqa: E402
from rating_m5 import OUT, ROOT, Table5, score_arrays, xval  # noqa: E402

GRID_Q = [0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]
GRID_K = list(range(0, 121, 2))
Q_SHARE_MAX = 0.30
M4_DIR = ROOT / 'reports' / 'rating-m4'


def derive(cur, mask, bq):
    """順序：μ、K、R、a、c（同 M4 規則，q 換成 M5 的 q）。"""
    x = xval(cur, bq)
    mu = float((x * cur.mn)[mask].sum() / cur.mn[mask].sum())
    pm = player_means(cur, x, mask)
    big = [(xb, M) for _, (M, xb) in pm.items() if M >= 300]
    R = wquant([b[0] for b in big], [b[1] for b in big], 0.2)
    P = dict(bq=bq, mu=mu, R=R, K=120, a=0.0, c=1.0, k_reached=False)
    for K in GRID_K:
        P['K'] = K
        _, _, G, _ = score_arrays(cur, P)
        top_share, all_share = f4.a4_ok(cur, mask, G)
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


def j_terms(cur, A, S, epm, dk):
    avg = f3.avg_by_player(cur, S, A, 250)
    r1, n1 = f3.corr_ext(avg, epm)
    r2, n2 = f3.corr_ext(avg, dk)
    return dict(rho_epm=r1, rho_darko=r2, n_epm=n1, n_darko=n2)


def fit():
    cur = Table5('2025-26')
    A = cur.half == 0
    epm, dk = f3.load_ext(f3.EPM, 'net'), f3.load_ext(f3.DARKO, 'dpm')
    sel = A & (cur.mn >= 10)
    grid = []
    for bq in GRID_Q:
        P = derive(cur, A, bq)
        _, _, G, S = score_arrays(cur, P)
        Gq = bq * cur.q * cur.mn / (cur.mn + P['K']) * cur.mn / 36
        share = float(np.var(Gq[sel]) / np.var(G[sel]))
        m = j_terms(cur, A, S, epm, dk)
        grid.append(dict(P=P, q_share=share, feasible=share <= Q_SHARE_MAX, J=m['rho_epm'] + m['rho_darko'], **m))
    ok = [g for g in grid if g['feasible']]
    best = max(ok, key=lambda g: (round(g['J'], 9), -g['P']['bq']))
    allm = np.ones(len(cur), bool)
    Pp = derive(cur, allm, best['P']['bq'])
    _, _, _, Sp = score_arrays(cur, Pp)
    cut1, cut5 = f4.cuts(cur, Sp)
    v0 = dict(cur.v0)
    fbg = v0.pop('fb_games')
    out = dict(
        spec_sha256=f3.sha(OUT / 'spec.md'), fit_data='2025-26 A half (int(GAME_ID)%2==0) only; prod = whole 2025-26 with chosen bq',
        v0=dict(season='2025-26', **v0, fallback_game_ids_n=len(fbg),
                note='一致＝>=10 分鐘球員單場 |stints PM - box PM| <= 2；退回＝整場任一人差 >2、或該場不在 stints（含 OT 場）'),
        inputs={'player-games 2025-26': f3.sha(m4.season_dir('2025-26') / 'player-games.json'),
                'team-games 2025-26': f3.sha(m4.season_dir('2025-26') / 'team-games.json'),
                'stints 2025-26': f3.sha(ROOT / 'reports/defense-b1/stints.jsonl'),
                'epm_self 2025-26': f3.sha(f3.EPM), 'darko 2025-26': f3.sha(f3.DARKO),
                'm2 weights': f3.sha(f3.rating_m2.M2 / 'weights.json'),
                'matchup-source 2025-26': f3.sha_dir(ROOT / 'data/matchup-source/2025-26')},
        q_share_def='Var(β_q·q·MIN/(MIN+K)·MIN/36) / Var(G)，A 半 >=10 分鐘單場（q＝M5 相對非垃圾時間）',
        J_def='ρ(A 半平均評分, EPM net) + ρ(A 半平均評分, DARKO dpm)，A 半 >=250 分鐘球員',
        chosen=best, grid=grid, prod=dict(P=Pp, cut1=cut1, cut5=cut5))
    (OUT / 'params.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('V0', json.dumps(out['v0'], ensure_ascii=False))
    for g in grid:
        P = g['P']
        print(f'bq={P["bq"]:.2f} K={P["K"]}{"" if P["k_reached"] else "(未達成)"} mu={P["mu"]:.3f} R={P["R"]:.3f} a={P["a"]:.3f} c={P["c"]:.4f} '
              f'J={g["J"]:.4f} ({g["rho_epm"]:.3f},{g["rho_darko"]:.3f}) qshare={g["q_share"]:.3f}{"" if g["feasible"] else " X"}')
    print('chosen bq', best['P']['bq'], 'prod P', json.dumps(Pp), cut1, cut5)


# ---------------------------------------------------------------- eval
def b1(cur, B, S):
    """B1：大勝爛場（B 半，球隊淨勝 >=15、>=25 分鐘、FG% <=35%、FGA >=12）中，評分低於本人 B 半中位數的比例。"""
    fgm = np.array([r[cur.h['FGM']] or 0 for r in cur.rows], float)
    med = {pid: float(np.median(S[B & (cur.pid == pid)])) for pid in np.unique(cur.pid[B])}
    sel = np.where(B & (cur.tpm >= 15) & (cur.mn >= 25) & (cur.fga >= 12) & (fgm <= 0.35 * cur.fga))[0]
    below = [S[i] < med[cur.pid[i]] for i in sel]
    return float(np.mean(below)), len(sel)


def b2(cur, B, S):
    """B2：B 半 >=10 分鐘單場中評分前 10%，「>=1/3 上場時間在垃圾時間」的比例。"""
    idx = np.where(B & (cur.mn >= 10))[0]
    k = int(round(0.10 * len(idx)))
    top = idx[np.argsort(-S[idx], kind='stable')[:k]]
    return float((cur.gfrac[top] >= 1 / 3).mean()), k


def pack(cur, B, S, label):
    r = f3.full_metrics(cur, B, S, label)
    r['T4 低於本人中位比例'], r['T4 n'] = f4.t4(cur, B, S)
    r['B1 低於本人中位比例'], r['B1 n'] = b1(cur, B, S)
    r['B2 前10%中垃圾時間>=1/3佔比'], r['B2 n_top'] = b2(cur, B, S)
    return r


def evaluate():
    P0 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))
    P4 = json.loads((M4_DIR / 'params.json').read_text(encoding='utf-8'))['chosen']['P']
    cur = Table5('2025-26')
    B = cur.half == 1
    res = {}
    S4 = m4.score_arrays(cur, P4)[3]
    res['M4'] = pack(cur, B, S4, 'M4')
    P5 = P0['chosen']['P']
    S5 = score_arrays(cur, P5)[3]
    res['M5'] = pack(cur, B, S5, 'M5')
    names = {int(p): n for p, n in zip(cur.pid, cur.name)}
    top30 = list(res['M5']['_rank'].keys())
    res['T3_top10'] = [dict(pid=p, name=names[p], m4_rank=res['M4']['_rank'][p], m5_rank=res['M5']['_rank'][p]) for p in top30[:10]]
    for k in ('M4', 'M5'):
        res[k].pop('_rank', None)
    old = json.loads((M4_DIR / 'eval.json').read_text(encoding='utf-8'))['M4']
    res['m4_recheck'] = {k: dict(old=old[k], new=res['M4'][k], same=abs(old[k] - res['M4'][k]) < 1e-9)
                         for k in old if k in res['M4'] and isinstance(old[k], (int, float))}
    m4_, m5_ = res['M4'], res['M5']
    v0 = P0['v0']
    kb = 'B2 前10%中垃圾時間>=1/3佔比'
    judge = {
        'V0': v0['pl_ok_ratio'] >= 0.85,
        'B1': m5_['B1 低於本人中位比例'] >= 0.70 and m5_['B1 低於本人中位比例'] > m4_['B1 低於本人中位比例'],
        'B2': m5_[kb] < m4_[kb],
        'T2': m5_['T2 ρ(平均評分,自製EPM net)'] >= m4_['T2 ρ(平均評分,自製EPM net)'] - 0.01
        and m5_['T2 ρ(平均評分,EPM net×分鐘佔比)'] >= m4_['T2 ρ(平均評分,EPM net×分鐘佔比)'] - 0.01,
        'A7': m5_['A7 ρ(平均評分,DARKO)'] >= m4_['A7 ρ(平均評分,DARKO)'] and m5_['A7 前後半 r'] >= m4_['A7 前後半 r'] - 0.03,
        'T3': m5_['T3 前30用掉回合者名次中位數'] <= m4_['T3 前30用掉回合者名次中位數'] + 3,
        'T4': m5_['T4 低於本人中位比例'] >= 0.8,
        'A4': m5_['A4 前6%中<15分鐘佔比'] <= m5_['A4 全部場次<15分鐘佔比'],
    }
    judge['all_pass'] = all(judge.values())
    res['judge'] = judge
    res['T1_report_only'] = dict(m4=m4_['T1 r(單場≥10分,淨勝分)'], m5=m5_['T1 r(單場≥10分,淨勝分)'])
    (OUT / 'eval.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{"":40s} {"M4":>9s} {"M5":>9s}')
    for k in [k for k in m4_ if not k.startswith('_')]:
        print(f'{k:40s} {m4_[k]:9.4f} {m5_[k]:9.4f}')
    print('M4 recheck all same:', all(v['same'] for v in res['m4_recheck'].values()), [(k, v['old'], v['new']) for k, v in res['m4_recheck'].items() if not v['same']])
    print(judge)
    for r in res['T3_top10']:
        print(r)


# ---------------------------------------------------------------- a5
def a5():
    P0 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))
    M4P = json.loads((M4_DIR / 'params.json').read_text(encoding='utf-8'))
    P4p, P4c = M4P['prod']['P'], M4P['chosen']['P']
    P5p, P5c = P0['prod']['P'], P0['chosen']['P']
    cur = Table5('2025-26')
    B = cur.half == 1
    nxt = Table5('2026-27')
    out = {}

    def rowd(t, i, S4, S5):
        return dict(name=str(t.name[i]), date=str(t.date[i]), gid=str(t.gid[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fga=int(t.fga[i]),
                    pm=float(t.pm[i]), team_net=float(t.tpm[i]), q_m4=float(t.q_m4[i]), q_m5=float(t.q[i]), fb=bool(t.fbq[i]),
                    garbage_frac=float(t.gfrac[i]), m4=float(S4[i]), m5=float(S5[i]))

    for tag, t, base, (p4, p5) in (('2025-26B', cur, B, (P4c, P5c)), ('2026-27', nxt, np.ones(len(nxt), bool), (P4p, P5p))):
        S4, S5 = m4.score_arrays(t, p4)[3], score_arrays(t, p5)[3]
        d = {}
        ex = {}
        for key, nm in (('Caruso', 'Caruso'), ('SGA', 'Gilgeous'), ('Wembanyama', 'Wembanyama')):
            idx = [i for i in range(len(t)) if nm in str(t.name[i]) and base[i]]
            ex[key] = dict(n=len(idx), avg_m4=float(np.mean(S4[idx])) if idx else None, avg_m5=float(np.mean(S5[idx])) if idx else None,
                           games=[rowd(t, i, S4, S5) for i in sorted(idx, key=lambda i: str(t.date[i]))])
        d['examples'] = ex
        fgm = np.array([r[t.h['FGM']] or 0 for r in t.rows], float)
        sel = np.where(base & (t.tpm >= 15) & (t.mn >= 25) & (t.fga >= 12) & (fgm <= 0.35 * t.fga))[0]
        d['b1_class'] = [rowd(t, i, S4, S5) for i in sorted(sel, key=lambda i: (-t.tpm[i], str(t.gid[i])))[:5]]
        idx = np.where(base & (t.mn >= 10))[0]
        k = int(round(0.10 * len(idx)))
        top = idx[np.argsort(-S4[idx], kind='stable')[:k]]
        cand = [i for i in top if t.gfrac[i] >= 0.5]
        d['garbage_pad'] = [rowd(t, i, S4, S5) for i in sorted(cand, key=lambda i: -(S4[i] - S5[i]))[:3]]
        d['n_top10pct_m4'] = k
        d['n_garbage_third_m4'] = int((t.gfrac[top] >= 1 / 3).sum())
        out[tag] = d
    S4p, S5p = m4.score_arrays(cur, P4p)[3], score_arrays(cur, P5p)[3]
    fgm = np.array([r[cur.h['FGM']] or 0 for r in cur.rows], float)
    mit = [i for i in range(len(cur)) if 'Mitchell' in str(cur.name[i]) and 'Donovan' in str(cur.name[i]) and cur.fga[i] == 18 and fgm[i] == 5]
    out['Mitchell_18_5'] = [rowd(cur, i, S4p, S5p) for i in mit]
    (OUT / 'a5.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['Mitchell_18_5'], ensure_ascii=False, indent=1))
    for tag in ('2025-26B', '2026-27'):
        d = out[tag]
        print('==', tag)
        for k, v in d['examples'].items():
            print(k, v['n'], v['avg_m4'], v['avg_m5'])
        print('B1class', *d['b1_class'], sep='\n  ')
        print('garbagepad', *d['garbage_pad'], sep='\n  ')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'fit': fit, 'eval': evaluate, 'a5': a5}[sys.argv[1]]()
