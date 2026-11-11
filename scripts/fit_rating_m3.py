"""評分 M3 擬合與驗收（E-145，spec：reports/rating-m3/spec.md，凍結 sha256 見 spec.sha256）。

用法（順序固定，不可顛倒）：
  python -I scripts/fit_rating_m3.py fit    只用 2025-26 A 半（int(GAME_ID)%2==0）與 2024-25：算 R_ppp、K、μ、R、a、c，25 組格點選 β → params.json
                                            （寫完先單獨 commit，之後才准跑 eval／prod，A2）
  python -I scripts/fit_rating_m3.py eval   2025-26 B 半驗收 T1 T2 T3 A4 A7（M2 同口徑基準一起算）→ eval.json
  python -I scripts/fit_rating_m3.py prod   上線參數：β 照 params.json，其餘用 2025-26 整季重算；五色切點；A5 範例 → params_prod.json、a5.json
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rating_m2  # noqa: E402
import rating_m3 as m3  # noqa: E402
from rating_m3 import OUT, ROOT, Table, player_means, prior_table, score_arrays, wquant, xval  # noqa: E402

GRID_U = [0, 0.1, 0.2, 0.3, 0.5]
GRID_Q = [0, 0.05, 0.1, 0.15, 0.2]
EPM = ROOT / 'data/external-impact/epm_self/epm_2025-26.csv'
DARKO = ROOT / 'data/external-impact/darko/darko_2025-26.csv'
BPM = ROOT / 'data/external-impact/bpm/bpm_2025-26.csv'
Q_SHARE_MAX = 0.30


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_dir(path):
    h = hashlib.sha256()
    for p in sorted(Path(path).glob('00*.json')):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def load_ext(path, col):
    import csv
    return {int(r['playerId']): float(r[col]) for r in csv.DictReader(open(path, encoding='utf-8')) if r[col] not in ('', None)}


def derive(cur, mask, prev, Rppp, bu, bq):
    """給定 (R_ppp, β_u, β_q)，用 mask 範圍的資料算 K、μ、R、a、c。"""
    x = xval(cur, Rppp, bu, bq)
    pm = player_means(cur, x, mask)
    xbars, Ms, num, den = [], [], 0.0, 0
    for pid, (M, _) in pm.items():
        if M < 500:
            continue
        m = mask & (cur.pid == pid)
        w = cur.mn[m] / 36
        xb = float((x[m] * w).sum() / w.sum())
        num += float((w * (x[m] - xb) ** 2).sum())
        den += int(m.sum()) - 1
        xbars.append(xb)
        Ms.append(M)
    sigma2 = num / den
    tau2 = float(np.var(xbars, ddof=1)) - float(np.mean([sigma2 * 36 / M for M in Ms]))
    assert tau2 > 0, 'tau2 <= 0'
    K = 36 * sigma2 / tau2
    mu = float((x * cur.mn)[mask].sum() / cur.mn[mask].sum())
    big = [(xb_, M) for _, (M, xb_) in pm.items() if M >= 300]
    R = wquant([b[0] for b in big], [b[1] for b in big], 0.2)
    P = dict(Rppp=Rppp, bu=bu, bq=bq, K=K, mu=mu, R=R, a=0.0, c=1.0, sigma2=sigma2, tau2=tau2)
    prior = prior_table(prev, Rppp, bu, bq, mu, K)
    _, _, G, _ = score_arrays(cur, P, prior)
    sel = mask & (cur.mn >= 10)
    med, p94 = float(np.median(G[sel])), float(np.percentile(G[sel], 94))
    P['c'] = (10 - 5.8) / (p94 - med)
    P['a'] = 5.8 - P['c'] * med
    return P, prior


def rppp(cur, mask):
    pids = np.unique(cur.pid[mask])
    vals, ws = [], []
    for pid in pids:
        m = mask & (cur.pid == pid)
        mins = cur.mn[m].sum()
        if mins >= 500:
            vals.append(cur.pts[m].sum() / cur.uses[m].sum())
            ws.append(mins)
    return wquant(vals, ws, 0.2)


def avg_by_player(t, S, mask, min_total):
    """pid → (分鐘合計, 單場評分簡單平均)，只留分鐘合計 ≥ min_total。"""
    idx = np.where(mask)[0]
    u, inv = np.unique(t.pid[idx], return_inverse=True)
    mins = np.bincount(inv, t.mn[idx])
    avg = np.bincount(inv, S[idx]) / np.bincount(inv)
    return {int(p): (float(a), float(b)) for p, a, b in zip(u, mins, avg) if a >= min_total}


def corr_ext(avg, ext, share=None):
    ps = [p for p in avg if p in ext]
    y = [ext[p] * (share[p] if share else 1) for p in ps]
    return float(spearmanr([avg[p][1] for p in ps], y)[0]), len(ps)


def metrics_core(t, mask, S, epm, thr, half_games):
    """J 的三項（A 半用）：ρ(平均評分, EPM)、ρ(平均評分, EPM×分鐘佔比)、r(單場≥10 分鐘, 球隊淨勝分)。"""
    avg = avg_by_player(t, S, mask, thr)
    share = {p: avg[p][0] / (half_games * 48) for p in avg}
    r1, n1 = corr_ext(avg, epm)
    r2, _ = corr_ext(avg, epm, share)
    sel = mask & (t.mn >= 10) & ~np.isnan(t.tpm)
    r3 = float(pearsonr(S[sel], t.tpm[sel])[0])
    return dict(rho_epm=r1, rho_epm_share=r2, r_pm=r3, n=n1)


def half_games_of(t, mask):
    return len(set(t.gid[mask])) * 2 / 30


def fit():
    cur, prev = Table('2025-26'), Table('2024-25')
    A = cur.half == 0
    epm = load_ext(EPM, 'net')
    Rppp = rppp(cur, A)
    hg = half_games_of(cur, A)
    sel = A & (cur.mn >= 10)
    grid = []
    for bu in GRID_U:
        for bq in GRID_Q:
            P, prior = derive(cur, A, prev, Rppp, bu, bq)
            x, xs, G, S = score_arrays(cur, P, prior)
            Gq = bq * (cur.pm * 36 / cur.mn) * cur.mn / (cur.mn + P['K']) * cur.mn / 36
            share = float(np.var(Gq[sel]) / np.var(G[sel]))
            m = metrics_core(cur, A, S, epm, 250, hg)
            J = m['rho_epm'] + m['rho_epm_share'] + m['r_pm']
            grid.append(dict(P=P, q_share=share, feasible=share <= Q_SHARE_MAX, J=J, **m))
    ok = [g for g in grid if g['feasible']]
    best = max(ok, key=lambda g: (round(g['J'], 9), -g['P']['bu'], -g['P']['bq']))
    noq = next(g for g in grid if g['P']['bu'] == best['P']['bu'] and g['P']['bq'] == 0)
    out = dict(
        spec_sha256=sha(OUT / 'spec.md'), fit_data='2025-26 A half (int(GAME_ID)%2==0) + 2024-25 prior only',
        inputs={'player-games 2025-26': sha(m3.season_dir('2025-26') / 'player-games.json'),
                'team-games 2025-26': sha(m3.season_dir('2025-26') / 'team-games.json'),
                'player-games 2024-25': sha(m3.season_dir('2024-25') / 'player-games.json'),
                'epm_self 2025-26': sha(EPM), 'm2 weights': sha(rating_m2.M2 / 'weights.json'),
                'matchup-source 2025-26': sha_dir(ROOT / 'data/matchup-source/2025-26'),
                'matchup-source 2024-25': sha_dir(ROOT / 'data/matchup-source/2024-25')},
        q_share_def='Var(β_q·q·MIN/(MIN+K)·MIN/36) / Var(G)，A 半 ≥10 分鐘單場',
        J_def='ρ(A 半平均評分, EPM net)(≥250 A 半分鐘) + ρ(…, EPM net × A 半分鐘佔比 [分鐘 ÷ (A 半每隊場數×48)]) + r(單場≥10 分鐘評分, 球隊淨勝分)',
        Rppp=Rppp, chosen=best, noq=noq, grid=grid)
    (OUT / 'params.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'R_ppp={Rppp:.4f}  chosen bu={best["P"]["bu"]} bq={best["P"]["bq"]} J={best["J"]:.4f} q_share={best["q_share"]:.3f}')
    for g in grid:
        print(f'bu={g["P"]["bu"]:.1f} bq={g["P"]["bq"]:.2f} K={g["P"]["K"]:.1f} J={g["J"]:.4f} '
              f'({g["rho_epm"]:.3f},{g["rho_epm_share"]:.3f},{g["r_pm"]:.3f}) qshare={g["q_share"]:.3f}{"" if g["feasible"] else " X"}')
    print('chosen P:', json.dumps(best['P']))


# ---------------------------------------------------------------- eval（B 半）
def halves_r(t, S, mask, thr):
    xs, ys = [], []
    for pid in np.unique(t.pid[mask]):
        idx = np.where(mask & (t.pid == pid))[0]
        idx = idx[np.argsort(t.date[idx].astype(str), kind='stable')]
        n = len(idx) // 2
        a, b = idx[:n], idx[n:]
        if t.mn[a].sum() >= thr and t.mn[b].sum() >= thr:
            xs.append(S[a].mean())
            ys.append(S[b].mean())
    return float(pearsonr(xs, ys)[0]), len(xs)


def full_metrics(t, B, S, label):
    """B 半驗收用的全部數字。"""
    out = {}
    sel = B & (t.mn >= 10) & ~np.isnan(t.tpm)
    out['T1 r(單場≥10分,淨勝分)'] = float(pearsonr(S[sel], t.tpm[sel])[0])
    out['T1 r(單場≥10分,勝負)'] = float(pearsonr(S[sel], t.twin[sel])[0])
    avg = avg_by_player(t, S, B, 250)
    hg = half_games_of(t, B)
    share = {p: avg[p][0] / (hg * 48) for p in avg}
    epm, dk, bp = load_ext(EPM, 'net'), load_ext(DARKO, 'dpm'), load_ext(BPM, 'bpm')
    out['T2 ρ(平均評分,自製EPM net)'], out['T2 n'] = corr_ext(avg, epm)
    out['T2 ρ(平均評分,EPM net×分鐘佔比)'], _ = corr_ext(avg, epm, share)
    out['A7 ρ(平均評分,DARKO)'], out['A7 n_darko'] = corr_ext(avg, dk)
    out['附 ρ(平均評分,BPM)'], _ = corr_ext(avg, bp)
    out['A7 前後半 r'], out['A7 前後半 n'] = halves_r(t, S, B, 150)
    # T3：全季用掉回合最多 30 人（全季 ≥1500 分鐘），B 半平均評分在 B 半 ≥250 分鐘球員中的名次
    allm = np.ones(len(t), bool)
    tot = {}
    for pid in np.unique(t.pid):
        m = t.pid == pid
        if t.mn[m].sum() >= 1500:
            tot[int(pid)] = float(t.uses[m].sum())
    top30 = sorted(tot, key=lambda p: -tot[p])[:30]
    order = sorted(avg, key=lambda p: -avg[p][1])
    rank = {p: i + 1 for i, p in enumerate(order)}
    rk = [rank[p] for p in top30 if p in rank]
    out['T3 前30用掉回合者名次中位數'] = float(np.median(rk))
    out['T3 n'] = len(rk)
    out['T3 league n'] = len(order)
    out['_rank'] = {p: rank.get(p) for p in top30}
    # A4：評分前 6% 場次中 <15 分鐘佔比 vs 全部場次中 <15 分鐘佔比（B 半、全部 MIN>0 場次）
    idx = np.where(B)[0]
    k = int(round(0.06 * len(idx)))
    top = idx[np.argsort(-S[idx], kind='stable')[:k]]
    out['A4 前6%中<15分鐘佔比'] = float((t.mn[top] < 15).mean())
    out['A4 全部場次<15分鐘佔比'] = float((t.mn[idx] < 15).mean())
    return out


def evaluate():
    P0 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))
    cur, prev = Table('2025-26'), Table('2024-25')
    B = cur.half == 1
    res = {}
    S2 = np.maximum(0, 0.75 * (cur.v + 7.5))
    res['M2'] = full_metrics(cur, B, S2, 'M2')
    for key in ('chosen', 'noq'):
        P = P0[key]['P']
        prior = prior_table(prev, P['Rppp'], P['bu'], P['bq'], P['mu'], P['K'])
        _, _, G, S = score_arrays(cur, P, prior)
        res['M3' if key == 'chosen' else 'M3_noq'] = full_metrics(cur, B, S, key)
        if key == 'chosen':
            Sm3 = S
    # T3 名單：全季用掉回合前 10 人 M2 與 M3 名次
    names = {int(p): n for p, n in zip(cur.pid, cur.name)}
    top30 = list(res['M3']['_rank'].keys())
    res['T3_top10'] = [dict(pid=p, name=names[p], m2_rank=res['M2']['_rank'][p], m3_rank=res['M3']['_rank'][p]) for p in top30[:10]]
    for k in res:
        if isinstance(res[k], dict):
            res[k].pop('_rank', None)
    (OUT / 'eval.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    keys = [k for k in res['M2'] if not k.startswith('_')]
    print(f'{"":40s} {"M2":>9s} {"M3":>9s} {"M3無q":>9s}')
    for k in keys:
        print(f'{k:40s} {res["M2"][k]:9.4f} {res["M3"][k]:9.4f} {res["M3_noq"][k]:9.4f}')
    for r in res['T3_top10']:
        print(r)


# ---------------------------------------------------------------- prod
def prod():
    P0 = json.loads((OUT / 'params.json').read_text(encoding='utf-8'))
    bu, bq = P0['chosen']['P']['bu'], P0['chosen']['P']['bq']
    cur, prev = Table('2025-26'), Table('2024-25')
    allm = np.ones(len(cur), bool)
    Rppp = rppp(cur, allm)
    P, prior = derive(cur, allm, prev, Rppp, bu, bq)
    _, _, G, S = score_arrays(cur, P, prior)
    # 五色切點：|單場(≥10 分鐘)評分 − 自己整季平均|、|連續 5 場平均 − 自己整季平均| 的 20／60 百分位，取到 0.1
    d1, d5 = [], []
    for pid in np.unique(cur.pid):
        idx = np.where(cur.pid == pid)[0]
        idx = idx[np.argsort(cur.date[idx].astype(str), kind='stable')]
        s = S[idx]
        b = s.mean()
        d1 += list(np.abs(s[cur.mn[idx] >= 10] - b))
        d5 += [abs(s[j:j + 5].mean() - b) for j in range(len(s) - 4)]
    cut1 = [round(float(x), 1) for x in np.percentile(d1, [20, 60])]
    cut5 = [round(float(x), 1) for x in np.percentile(d5, [20, 60])]
    sel = cur.mn >= 10
    share = dict(gt10=float((S[sel] > 10).mean()), eq0=float((S[sel] == 0).mean()), mean=float(S[sel].mean()),
                 median=float(np.median(S[sel])), p94=float(np.percentile(S[sel], 94)))
    out = dict(P=P, cut1=cut1, cut5=cut5, share=share, note='上線參數：β 照 params.json，R_ppp、K、μ、R、a、c 用 2025-26 整季重算（spec §2）',
               inputs={'player-games 2025-26': sha(m3.season_dir('2025-26') / 'player-games.json')})
    (OUT / 'params_prod.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('P', 'cut1', 'cut5', 'share')}, ensure_ascii=False))
    # A5：2026-27 範例
    sc = m3.Scorer('2026-27')
    t = sc.tab
    S2 = np.maximum(0, 0.75 * (t.v + 7.5))
    ex = {}
    for key, nm in (('Caruso', 'Caruso'), ('SGA', 'Gilgeous'), ('Wembanyama', 'Wembanyama')):
        idx = [i for i in range(len(t)) if nm in str(t.name[i])]
        ex[key] = [dict(date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fga=int(t.fga[i]), m2=float(S2[i]), m3=float(sc.S[i]))
                   for i in sorted(idx, key=lambda i: str(t.date[i]))]
    top = lambda arr: [dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), score=float(arr[i]))
                       for i in np.argsort(-arr, kind='stable')[:10]]
    res = dict(examples=ex, top10_m2=top(S2), top10_m3=top(sc.S))
    (OUT / 'a5.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    for k, v in ex.items():
        print(k, 'n', len(v), 'avg M2 %.2f M3 %.2f' % (np.mean([g['m2'] for g in v]), np.mean([g['m3'] for g in v])) if v else '')
    print('TOP10 M2', *res['top10_m2'], sep='\n  ')
    print('TOP10 M3', *res['top10_m3'], sep='\n  ')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'fit': fit, 'eval': evaluate, 'prod': prod}[sys.argv[1]]()
