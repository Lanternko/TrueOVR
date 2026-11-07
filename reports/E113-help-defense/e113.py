"""E-113：評分的防守對位補上補防與對手強度（預註冊 preregistration.md，凍結 sha256 c1ef9562…afc7）。

M2＝E-110 選中組（box 11＋hustle 5＋PTS_SAVED＋TOV_FORCED）；
M3＝box 11＋hustle 5＋PROD_SAVED_LO（取代 PTS_SAVED）＋TOV_FORCED＋HELP_BLK。
M3a／b／c 只報告：M2＋HELP_BLK／PTS_SAVED 排除自己／PTS_SAVED 含助攻。
擬合、人群、A／B 切法全部沿用 E-110（e110.py）。沒有可調參數。

用法：python -I reports/E113-help-defense/e113.py
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
sys.path.insert(0, str(ROOT / 'reports/E110-defensive-rating'))
import fit_game_contribution as gc  # noqa: E402
import e110  # noqa: E402

OUT = Path(__file__).resolve().parent
CARD26 = ROOT / 'reports/card-0.2.6/ranking.csv'
CARD27 = ROOT / 'reports/card-0.2.7/ranking.csv'
RAPMD = ROOT / 'reports/card-0.2.6+E107-defense-UL/ranking.csv'
E110_RES = ROOT / 'reports/E110-defensive-rating/results.json'
BOX, HUS = e110.BOX, list(e110.HUSTLE)
MODELS = {
    'M2': BOX + HUS + ['PTS_SAVED', 'TOV_FORCED'],
    'M3': BOX + HUS + ['PROD_SAVED_LO', 'TOV_FORCED', 'HELP_BLK'],
    'M3a': BOX + HUS + ['PTS_SAVED', 'TOV_FORCED', 'HELP_BLK'],
    'M3b': BOX + HUS + ['PTS_SAVED_LO', 'TOV_FORCED'],
    'M3c': BOX + HUS + ['PROD_SAVED', 'TOV_FORCED'],
}
MIN_POSS = e110.EXP_MIN_POSS
SEED, NBOOT = 20261113, 2000
RIM = ['Rudy Gobert', 'Brook Lopez', 'Jaren Jackson Jr.', 'Myles Turner', 'Joel Embiid']
STOPPER = ['Herbert Jones', 'Dillon Brooks']
GAMBLER = ['Bilal Coulibaly', 'Russell Westbrook', 'Keldon Johnson', 'Dru Smith']
PROTECTED = ['reports/game-contribution', 'reports/impact-rapm', 'reports/E110-defensive-rating',
             'data/matchup-source'] + \
            sorted(str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'reports').glob('card-*'))


def sha_tree():
    out = {}
    for d in PROTECTED:
        for p in sorted((ROOT / d).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                out[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def in_half(gid, half):
    return half is None or e110.half_of(gid) == half


class Exp:
    """一個半季（half=None 為整季）的對位基準：含自己／排除自己 × 只算得分／得分＋助攻。"""

    def __init__(self, games, half):
        pts, fgm = 0.0, 0.0
        for gid, g in games.items():
            if in_half(gid, half):
                for m in g['matchups']:
                    pts += m['playerPoints']; fgm += m['matchupFieldGoalsMade']
        self.V = pts / fgm
        self.o = {k: defaultdict(float) for k in ('pts', 'prod', 'poss')}
        self.od = {k: defaultdict(float) for k in ('pts', 'prod', 'poss')}
        for gid, g in games.items():
            if not in_half(gid, half):
                continue
            for m in g['matchups']:
                v = {'pts': m['playerPoints'], 'prod': m['playerPoints'] + self.V * m['matchupAssists'],
                     'poss': m['partialPossessions']}
                for k in v:
                    self.o[k][m['off']] += v[k]; self.od[k][(m['off'], m['def'])] += v[k]
        tp = sum(self.o['poss'].values())
        self.lg = {k: sum(self.o[k].values()) / tp for k in ('pts', 'prod')}
        self.fallback = {'all': 0.0, 'lo': 0.0, 'poss': tp}
        for (o, d), p in self.od['poss'].items():
            if self.o['poss'][o] < MIN_POSS:
                self.fallback['all'] += p
            if self.o['poss'][o] - p < MIN_POSS:
                self.fallback['lo'] += p

    def get(self, key, o, d, lo):
        po = self.o['poss'][o] - (self.od['poss'][(o, d)] if lo else 0)
        if po < MIN_POSS:
            return self.lg[key]
        return (self.o[key][o] - (self.od[key][(o, d)] if lo else 0)) / po


def game_extra(g, ex):
    e = defaultdict(lambda: defaultdict(float))
    for r in g['hustle']:
        for k, src in e110.HUSTLE.items():
            e[r['personId']][k] += r.get(src) or 0
    for m in g['matchups']:
        o, d, p = m['off'], m['def'], m['partialPossessions']
        pts, prod = m['playerPoints'], m['playerPoints'] + ex.V * m['matchupAssists']
        x = e[d]
        x['PTS_SAVED'] += ex.get('pts', o, d, False) * p - pts
        x['PTS_SAVED_LO'] += ex.get('pts', o, d, True) * p - pts
        x['PROD_SAVED'] += ex.get('prod', o, d, False) * p - prod
        x['PROD_SAVED_LO'] += ex.get('prod', o, d, True) * p - prod
        x['TOV_FORCED'] += m['matchupTurnovers']
        x['HELP_BLK'] += m.get('helpBlocks') or 0
    return e


def totals(rows, h, games, half, ex):
    t = gc.totals(rows, h, half)
    for gid, g in games.items():
        if in_half(gid, half):
            for pid, e in game_extra(g, ex).items():
                if pid in t:
                    for k, v in e.items():
                        t[pid][k] += v
    return t


def boot_dr(pa, pb, y, w):
    rng = np.random.default_rng(SEED)
    n, out = len(y), []
    for _ in range(NBOOT):
        i = rng.integers(0, n, n)
        out.append(gc.wcorr(pa[i], y[i], w[i]) - gc.wcorr(pb[i], y[i], w[i]))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def wdict(b, feats):
    return {'intercept': float(b[0]), **{k: float(v) for k, v in zip(feats, b[1:])}}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    before = sha_tree()
    rows, h = gc.load_games()
    games = e110.load_matchups()
    res = {'prereg_sha256': (OUT / 'preregistration.sha256').read_text(encoding='utf-8').split()[0],
           'n_games': len(games)}

    rapm = {'A': gc.load_rapm('A'), 'B': gc.load_rapm('B')}
    T, EX = {}, {}
    for half, hk in ((0, 'A'), (1, 'B')):
        EX[hk] = Exp(games, half)
        T[hk] = totals(rows, h, games, half, EX[hk])
    betas, r = {}, {}
    for fh, eh in (('A', 'B'), ('B', 'A')):
        ps, y, w = e110.evalset(T[eh], rapm[eh])
        P = {}
        for mk, feats in MODELS.items():
            b = e110.fit(T[fh], rapm[fh], feats)
            betas[(mk, fh)] = b
            P[mk] = e110.pred(T[eh], ps, b, feats)
            r[(mk, fh)] = gc.wcorr(P[mk], y, w)
        if fh == 'A':
            boot = boot_dr(P['M3'], P['M2'], y, w)
            n_eval_B = len(ps)

    # ---- 硬條件 ----
    ref = json.loads(E110_RES.read_text(encoding='utf-8'))
    c0 = {}
    for fh, key, rk_ in (('A', 'weights_AB', 'M2 A→B'), ('B', 'weights_BA', 'M2 B→A')):
        rw = ref[key]['M2']
        refb = np.r_[rw['intercept'], [rw[k] for k in MODELS['M2']]]
        c0[fh] = {'max_weight_diff': float(np.abs(betas[('M2', fh)] - refb).max()),
                  'r_diff': abs(r[('M2', fh)] - ref['r'][rk_])}
    c0['pass'] = all(c0[k]['max_weight_diff'] < 1e-6 and c0[k]['r_diff'] < 1e-6 for k in ('A', 'B'))

    exS = Exp(games, None)
    tS = totals(rows, h, games, None, exS)
    pl = [p for p, d in tS.items() if d['MIN'] > 0]
    hb = {p: tS[p]['HELP_BLK'] for p in pl}
    bk = {p: tS[p]['BLK'] for p in pl}
    d3_share = sum(hb[p] <= bk[p] + 1e-9 for p in pl) / len(pl)
    d3_ratio = sum(hb.values()) / sum(bk.values())
    fb = {hk: EX[hk].fallback['lo'] / EX[hk].fallback['poss'] for hk in EX}
    gates = {
        'c0': c0,
        'd3': {'share_help_le_blk': d3_share, 'league_help_over_blk': d3_ratio, 'n_players': len(pl),
               'pass': d3_share >= 0.99 and 0 < d3_ratio <= 1},
        'd4': {'V': {hk: EX[hk].V for hk in EX}, 'V_season': exS.V, 'fallback_lo_share': fb,
               'fallback_all_share': {hk: EX[hk].fallback['all'] / EX[hk].fallback['poss'] for hk in EX},
               'pass': all(1.8 <= EX[hk].V <= 2.6 for hk in EX) and all(v <= 0.10 for v in fb.values())},
    }
    res['gates'] = gates

    dAB, dBA = r[('M3', 'A')] - r[('M2', 'A')], r[('M3', 'B')] - r[('M2', 'B')]
    res['s1'] = {'dr_AB': dAB, 'ci_AB': boot, 'dr_BA': dBA, 'pass': boot[0] > 0 and dBA > 0}
    res['r'] = {f'{mk} {fh}→{"B" if fh == "A" else "A"}': r[(mk, fh)] for mk, fh in r}
    res['n_eval_B'] = n_eval_B
    res['weights_AB'] = {mk: wdict(betas[(mk, 'A')], f) for mk, f in MODELS.items()}
    res['weights_BA'] = {mk: wdict(betas[(mk, 'B')], f) for mk, f in MODELS.items()}

    # ---- 整季評分（A→B 權重；人群同 E-110：≥1000 分鐘且在 card 0.2.6） ----
    name = {r_[h['PLAYER_ID']]: r_[h['PLAYER_NAME']] for r_ in rows}
    ovr26 = {c['name']: float(c['ovr']) for c in csv.DictReader(CARD26.open(encoding='utf-8'))}
    ovr27 = {c['name']: float(c['ovr']) for c in csv.DictReader(CARD27.open(encoding='utf-8'))}
    rd = {c['name']: float(c['rapmDRank']) for c in csv.DictReader(RAPMD.open(encoding='utf-8')) if c['rapmDRank']}
    pool = [p for p, d in tS.items() if d['MIN'] >= 1000 and name[p] in ovr26]
    season = {mk: e110.pred(tS, pool, betas[(mk, 'A')], f) for mk, f in MODELS.items()}
    rank = lambda v: {p: int(k) + 1 for p, k in zip(pool, np.argsort(np.argsort(-v)))}
    rk = {mk: rank(v) for mk, v in season.items()}
    o26 = np.array([ovr26[name[p]] for p in pool])
    rk['OVR026'] = rank(o26)
    o27 = np.array([ovr27.get(name[p], np.nan) for p in pool])
    res['n_season_pool'] = len(pool)
    res['spearman_vs_ovr026'] = {mk: gc.spearman(v, o26) for mk, v in season.items()}
    ok27 = ~np.isnan(o27)
    res['spearman_vs_ovr027'] = {mk: gc.spearman(v[ok27], o27[ok27]) for mk, v in season.items()}
    dpool = [i for i, p in enumerate(pool) if name[p] in rd]
    dr_ = np.array([-rd[name[pool[i]]] for i in dpool])
    res['spearman_vs_rapmD'] = {mk: gc.spearman(v[dpool], dr_) for mk, v in season.items()}
    byname = {name[p]: p for p in pool}
    watch = RIM + STOPPER + GAMBLER
    res['watch'] = {n: {k: rk[k][byname[n]] for k in rk} for n in watch if n in byname}
    res['watch_missing'] = [n for n in watch if n not in byname]
    up = lambda lst: sum(rk['M3'][byname[n]] < rk['M2'][byname[n]] for n in lst if n in byname)
    res['s2'] = {'rim_up': up(RIM), 'rim_of': sum(n in byname for n in RIM), 'stopper_up': up(STOPPER),
                 'pass': up(RIM) >= 4 and up(STOPPER) == len(STOPPER)}
    res['help_blk_top15'] = sorted(((name[p], hb[p], bk[p]) for p in pl), key=lambda x: -x[1])[:15]
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(['name', 'MIN', 'OVR026', 'rank_OVR026', 'HELP_BLK', 'BLK'] +
                    [x for mk in MODELS for x in (mk, f'rank_{mk}')])
        for p in sorted(pool, key=lambda p: rk['OVR026'][p]):
            i = pool.index(p)
            wr.writerow([name[p], round(tS[p]['MIN']), ovr26[name[p]], rk['OVR026'][p], hb[p], bk[p]] +
                        [x for mk in MODELS for x in (round(float(season[mk][i]), 3), rk[mk][p])])

    # ---- 單場 >10／=0 比例（只報告；基準用整季值） ----
    gx = {gid: game_extra(g, exS) for gid, g in games.items()}
    sc = lambda v: max(0.0, 0.75 * (v + 7.5))
    allv = defaultdict(list)
    for r_ in rows:
        mn = r_[h['MIN']] or 0
        if mn < 10:
            continue
        d = defaultdict(float, {k: r_[h[k]] or 0 for k in BOX})
        d['MIN'] = mn
        d.update(gx.get(r_[h['GAME_ID']], {}).get(r_[h['PLAYER_ID']], {}))
        for mk, f in MODELS.items():
            b = betas[(mk, 'A')]
            allv[mk].append(sc(b[0] + gc.per36(d, f) @ b[1:]))
    res['rating_share'] = {mk: {'gt10': float((np.array(v) > 10).mean()), 'eq0': float((np.array(v) == 0).mean())}
                           for mk, v in allv.items()}

    after = sha_tree()
    res['protected_unchanged'] = before == after
    res['protected_files'] = len(before)
    (OUT / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('gates', 's1', 'r', 's2', 'spearman_vs_ovr026', 'spearman_vs_rapmD',
                                          'rating_share', 'watch', 'watch_missing', 'protected_unchanged')},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
