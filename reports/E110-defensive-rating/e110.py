"""E-110：單場評分加入 hustle 與防守對位（預註冊 preregistration.md，凍結 sha256 b034e377…4e00）。

M0＝E-105 box 11 項；M1＝＋hustle 5 項；M2＝＋PTS_SAVED、TOV_FORCED。
每人半季合計換算每 36 分鐘（分母＝player-games MIN），對同一半 rapm1 net 加權最小平方（權重＝poss），
人群＝該半上場 ≥ 300 分鐘；A→B 與 B→A 兩個方向。沒有可調參數。

用法：python -I reports/E110-defensive-rating/e110.py
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import fit_game_contribution as gc  # noqa: E402

OUT = Path(__file__).resolve().parent
MDIR = ROOT / 'data/matchup-source/2025-26'
TEAM = ROOT / 'data/season-source/team-games.json'
CARD = ROOT / 'reports/card-0.2.6/ranking.csv'
BOX = gc.FEATS
HUSTLE = {'DEFL': 'deflections', 'CONTEST': 'contestedShots', 'CHARGE': 'chargesDrawn',
          'LOOSE': 'looseBallsRecoveredTotal', 'SCREEN_AST': 'screenAssists'}
MATCH = ['PTS_SAVED', 'TOV_FORCED']
MODELS = {'M0': BOX, 'M1': BOX + list(HUSTLE), 'M2': BOX + list(HUSTLE) + MATCH}
EXP_MIN_POSS = 50
SEED, NBOOT = 20261110, 2000
DEFENDERS = ['Herbert Jones', 'Toumani Camara', 'Dillon Brooks', 'Draymond Green', 'Ivica Zubac']
WATCH = DEFENDERS + ['Dru Smith', 'Reed Sheppard', 'Bones Hyland', 'Keyonte George', 'Simone Fontecchio', 'Kyle Filipowski']
PROTECTED = ['reports/game-contribution', 'reports/impact-rapm'] + \
            sorted(str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'reports').glob('card-*'))


def sha_tree():
    out = {}
    for d in PROTECTED:
        for p in sorted((ROOT / d).rglob('*')):
            if p.is_file():
                out[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def half_of(gid):
    return int(gid) % 2


def load_matchups():
    games = {}
    for p in sorted(MDIR.glob('00*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        if d.get('matchups') and d.get('hustle'):
            games[d['gameId']] = d
    return games


def mmss(s):
    if not s:
        return 0.0
    m, _, sec = str(s).partition(':')
    return int(m) + (int(sec) if sec else 0) / 60


def exp_table(games, half):
    """o → 得分÷部分回合（該半）；回合 < 50 用聯盟平均。half=None 取整季。"""
    pts, poss = defaultdict(float), defaultdict(float)
    for gid, g in games.items():
        if half is not None and half_of(gid) != half:
            continue
        for m in g['matchups']:
            pts[m['off']] += m['playerPoints']
            poss[m['off']] += m['partialPossessions']
    lg = sum(pts.values()) / sum(poss.values())
    return defaultdict(lambda: lg, {o: pts[o] / poss[o] for o in poss if poss[o] >= EXP_MIN_POSS}), lg


def game_extra(g, exp):
    """{pid: {DEFL..., PTS_SAVED, TOV_FORCED}} for one game."""
    e = defaultdict(lambda: defaultdict(float))
    for r in g['hustle']:
        for k, src in HUSTLE.items():
            e[r['personId']][k] += r.get(src) or 0
    for m in g['matchups']:
        d = e[m['def']]
        d['PTS_SAVED'] += exp[m['off']] * m['partialPossessions'] - m['playerPoints']
        d['TOV_FORCED'] += m['matchupTurnovers']
    return e


def totals(rows, h, games, half, exp):
    t = gc.totals(rows, h, half)
    for gid, g in games.items():
        if half is not None and half_of(gid) != half:
            continue
        for pid, e in game_extra(g, exp).items():
            if pid in t:
                for k, v in e.items():
                    t[pid][k] += v
    return t


def fit(t, rapm, feats):
    ps = [p for p, d in t.items() if d['MIN'] >= gc.MIN_MIN and p in rapm]
    X = np.array([np.r_[1.0, gc.per36(t[p], feats)] for p in ps])
    y = np.array([rapm[p][0] for p in ps])
    w = np.sqrt([rapm[p][1] for p in ps])
    return np.linalg.lstsq(X * w[:, None], y * w, rcond=None)[0]


def evalset(t, rapm):
    ps = [p for p, d in t.items() if d['MIN'] >= gc.MIN_MIN and p in rapm]
    return ps, np.array([rapm[p][0] for p in ps]), np.array([rapm[p][1] for p in ps])


def pred(t, ps, beta, feats):
    return np.array([beta[0] + gc.per36(t[p], feats) @ beta[1:] for p in ps])


def boot_dr(pa, pb, y, w):
    rng = np.random.default_rng(SEED)
    n, out = len(y), []
    for _ in range(NBOOT):
        i = rng.integers(0, n, n)
        out.append(gc.wcorr(pa[i], y[i], w[i]) - gc.wcorr(pb[i], y[i], w[i]))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    before = sha_tree()
    rows, h = gc.load_games()
    games = load_matchups()
    res = {'prereg_sha256': (OUT / 'preregistration.sha256').read_text(encoding='utf-8').split()[0]}

    # ---- d0 / d1 / d2 ----
    roster = defaultdict(set)
    for r in rows:
        roster[r[h['GAME_ID']]].add(r[h['PLAYER_ID']])
    all_gids = sorted(roster)
    n_ok = n_all = 0
    for gid, g in games.items():
        ro = roster[gid]
        for m in g['matchups']:
            n_all += 1; n_ok += m['off'] in ro and m['def'] in ro
        for r in g['hustle']:
            n_all += 1; n_ok += r['personId'] in ro
    trs = json.loads(TEAM.read_text(encoding='utf-8'))['data']['resultSets'][0]
    th = {k: i for i, k in enumerate(trs['headers'])}
    tposs = {(r[th['GAME_ID']], r[th['TEAM_ID']]): r[th['FGA']] + 0.44 * r[th['FTA']] - r[th['OREB']] + r[th['TOV']]
             for r in trs['rowSet']}
    mp = defaultdict(float)
    for gid, g in games.items():
        for m in g['matchups']:
            mp[(gid, m['teamId'])] += m['partialPossessions']
    ratios = [v / tposs[k] for k, v in mp.items() if k in tposs and tposs[k] > 0]
    res['gates'] = {
        'd0': {'games': len(games), 'of': len(all_gids), 'pass': len(games) >= 1210},
        'd1': {'share': n_ok / n_all, 'rows': n_all, 'pass': n_ok / n_all >= 0.99},
        'd2': {'median': float(np.median(ratios)), 'p10': float(np.percentile(ratios, 10)),
               'p90': float(np.percentile(ratios, 90)), 'n': len(ratios),
               'pass': 0.85 <= float(np.median(ratios)) <= 1.15},
    }

    # ---- fits ----
    rapm = {'A': gc.load_rapm('A'), 'B': gc.load_rapm('B')}
    T = {}
    for half, hk in ((0, 'A'), (1, 'B')):
        exp, lg = exp_table(games, half)
        T[hk] = totals(rows, h, games, half, exp)
        res[f'league_ppp_{hk}'] = lg
    betas, r = {}, {}
    for fh, eh in (('A', 'B'), ('B', 'A')):
        ps, y, w = evalset(T[eh], rapm[eh])
        P = {}
        for mk, feats in MODELS.items():
            b = fit(T[fh], rapm[fh], feats)
            betas[(mk, fh)] = b
            P[mk] = pred(T[eh], ps, b, feats)
            r[(mk, fh)] = gc.wcorr(P[mk], y, w)
        if fh == 'A':
            boot = {mk: boot_dr(P[mk], P['M0'], y, w) for mk in ('M1', 'M2')}
            boot['M2_vs_M1'] = boot_dr(P['M2'], P['M1'], y, w)
            n_eval_B = len(ps)
    ref = json.loads((ROOT / 'reports/game-contribution/weights.json').read_text(encoding='utf-8'))
    refb = np.r_[ref['intercept'], [ref['per36'][k] for k in BOX]]
    c0 = {'max_weight_diff': float(np.abs(betas[('M0', 'A')] - refb).max()),
          'r_diff': abs(r[('M0', 'A')] - ref['eval']['box_B_vs_rapmB']['wPearson'])}
    c0['pass'] = c0['max_weight_diff'] < 1e-6 and c0['r_diff'] < 1e-6
    res['gates']['c0'] = c0

    s = {}
    for mk in ('M1', 'M2'):
        dAB, dBA = r[(mk, 'A')] - r[('M0', 'A')], r[(mk, 'B')] - r[('M0', 'B')]
        s[mk] = {'dr_AB': dAB, 'ci_AB': boot[mk], 'dr_BA': dBA, 'pass': boot[mk][0] > 0 and dBA > 0}
    if s['M2']['pass'] and not (s['M1']['pass'] and r[('M2', 'A')] - r[('M1', 'A')] < 0.01):
        chosen = 'M2'
    elif s['M1']['pass']:
        chosen = 'M1'
    elif s['M2']['pass']:
        chosen = 'M2'
    else:
        chosen = 'M0'
    res['s1'] = s['M2']; res["s1'"] = s['M1']; res['M2_vs_M1_ci_AB'] = boot['M2_vs_M1']
    res['chosen'] = chosen
    res['r'] = {f'{mk} {fh}→{"B" if fh == "A" else "A"}': r[(mk, fh)] for mk, fh in r}
    res['n_eval_B'] = n_eval_B
    res['weights_AB'] = {mk: {'intercept': float(betas[(mk, 'A')][0]),
                              **{k: float(v) for k, v in zip(feats, betas[(mk, 'A')][1:])}} for mk, feats in MODELS.items()}
    res['weights_BA'] = {mk: {'intercept': float(betas[(mk, 'B')][0]),
                              **{k: float(v) for k, v in zip(feats, betas[(mk, 'B')][1:])}} for mk, feats in MODELS.items()}

    # ---- 整季評分（A→B 權重） ----
    expS, _ = exp_table(games, None)
    tS = totals(rows, h, games, None, expS)
    name = {r_[h['PLAYER_ID']]: r_[h['PLAYER_NAME']] for r_ in rows}
    ovr = {c['name']: float(c['ovr']) for c in csv.DictReader(CARD.open(encoding='utf-8'))}
    pool = [p for p, d in tS.items() if d['MIN'] >= 1000 and name[p] in ovr]
    season = {mk: pred(tS, pool, betas[(mk, 'A')], feats) for mk, feats in MODELS.items()}
    o = np.array([ovr[name[p]] for p in pool])
    rank = lambda v: {p: int(k) + 1 for p, k in zip(pool, np.argsort(np.argsort(-v)))}
    rk = {mk: rank(v) for mk, v in season.items()}
    rk['OVR'] = rank(o)
    res['n_season_pool'] = len(pool)
    res['spearman_vs_ovr'] = {mk: gc.spearman(v, o) for mk, v in season.items()}
    byname = {name[p]: p for p in pool}
    res['watch'] = {n: {k: rk[k][byname[n]] for k in rk} for n in WATCH if n in byname}
    res['watch_missing'] = [n for n in WATCH if n not in byname]
    top10 = sorted(pool, key=lambda p: rk['OVR'][p])[:10]
    res['ovr_top10'] = {name[p]: {k: rk[k][p] for k in rk} for p in top10}
    up = {mk: sum(rk[mk][byname[n]] < rk['M0'][byname[n]] for n in DEFENDERS if n in byname) for mk in ('M1', 'M2')}
    res['s2'] = {'model': chosen, 'up': up.get(chosen), 'up_by_model': up,
                 'pass': up.get(chosen, 0) >= 4 if chosen != 'M0' else None}
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['name', 'MIN', 'OVR', 'rank_OVR'] + [x for mk in MODELS for x in (f'{mk}', f'rank_{mk}')])
        for p in sorted(pool, key=lambda p: rk['OVR'][p]):
            wr.writerow([name[p], round(tS[p]['MIN']), ovr[name[p]], rk['OVR'][p]] +
                        [x for mk in MODELS for x in (round(float(season[mk][pool.index(p)]), 3), rk[mk][p])])

    # ---- 單場穩定度、>10／=0 比例（只報告；exp 用整季值） ----
    gx = {gid: game_extra(g, expS) for gid, g in games.items()}
    per_player = defaultdict(list)
    for r_ in rows:
        mn = r_[h['MIN']] or 0
        if mn < 10:
            continue
        d = defaultdict(float, {k: r_[h[k]] or 0 for k in BOX})
        d['MIN'] = mn
        d.update(gx.get(r_[h['GAME_ID']], {}).get(r_[h['PLAYER_ID']], {}))
        per_player[r_[h['PLAYER_ID']]].append((r_[h['GAME_DATE']], d))
    stab, share = {}, {}
    sc = lambda v: max(0.0, 0.75 * (v + 7.5))
    for mk, feats in MODELS.items():
        b = betas[(mk, 'A')]
        one, rest1, five, rest5, allv = [], [], [], [], []
        for pid, gl in per_player.items():
            v = np.array([b[0] + gc.per36(d, feats) @ b[1:] for _, d in gl])
            allv += [sc(x) for x in v]
            if len(gl) < 40 or sum(d['MIN'] for _, d in gl) / len(gl) < 20:
                continue
            order = np.argsort([dt for dt, _ in gl])
            v = v[order]; m = np.array([gl[i][1]['MIN'] for i in order])
            for j in range(len(v)):
                mask = np.ones(len(v), bool); mask[j] = False
                one.append(v[j]); rest1.append((v[mask] * m[mask]).sum() / m[mask].sum())
            for j in range(0, len(v) - 4, 5):
                mask = np.ones(len(v), bool); mask[j:j + 5] = False
                five.append((v[j:j + 5] * m[j:j + 5]).sum() / m[j:j + 5].sum())
                rest5.append((v[mask] * m[mask]).sum() / m[mask].sum())
        stab[mk] = {'one': float(np.corrcoef(one, rest1)[0, 1]), 'five': float(np.corrcoef(five, rest5)[0, 1])}
        allv = np.array(allv)
        share[mk] = {'gt10': float((allv > 10).mean()), 'eq0': float((allv == 0).mean())}
    res['stability'] = stab
    res['rating_share'] = share

    after = sha_tree()
    res['protected_unchanged'] = before == after
    res['protected_files'] = len(before)
    (OUT / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('gates', 's1', "s1'", 'M2_vs_M1_ci_AB', 'chosen', 'r', 's2', 'spearman_vs_ovr',
                                          'stability', 'rating_share', 'watch', 'watch_missing', 'protected_unchanged')},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
