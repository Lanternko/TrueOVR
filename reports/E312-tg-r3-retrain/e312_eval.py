"""E-312 評估（本機；prereg.md 凍結判準）。讀 results/pred-mock.json（5090）與 work/pred-f.json（本機）→ results/eval.json。
  python -X utf8 reports/E312-tg-r3-retrain/e312_eval.py"""
import csv, hashlib, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tg_live as TL
MAIN = TL.MAIN; WT = TL.WT
sys.path.insert(0, os.path.join(MAIN, 'scripts')); sys.path.insert(0, os.path.join(MAIN, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np

H, SIG, NB = 2.5, 12.0, 2000
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))
J = lambda p: json.load(open(p, encoding='utf-8'))


def brier(m, d):
    return (np.clip(Phi((np.asarray(m) + H) / SIG), 1e-6, 1 - 1e-6) - (np.asarray(d) > 0)) ** 2


def mae(m, d):
    return np.abs(np.asarray(d) - np.asarray(m) - H)


def ci(x, seed):
    x = np.asarray(x, float); r = np.random.default_rng(seed); b = x[r.integers(0, len(x), (NB, len(x)))].mean(1)
    return [float(np.percentile(b, 5)), float(np.percentile(b, 95))]


def block(MB, MT, d, seed):
    """MB、MT：[seed, 場]。回傳 ensemble 指標、兩半、逐 seed。"""
    eb, et = MB.mean(0), MT.mean(0)
    db = brier(et, d) - brier(eb, d); da = mae(et, d) - mae(eb, d)
    out = dict(n=len(d), brierB=float(brier(eb, d).mean()), brierTG=float(brier(et, d).mean()), dBrier=float(db.mean()), dBrierCI90=ci(db, seed),
               dMAE=float(da.mean()), dMAECI90=ci(da, seed + 1), corr=float(np.corrcoef(eb, et)[0, 1]))
    if len(MB) == 10:
        out['halves'] = {h: float((brier(MT[s].mean(0), d) - brier(MB[s].mean(0), d)).mean()) for h, s in (('s0-4', slice(0, 5)), ('s5-9', slice(5, 10)))}
    out['perSeed'] = [dict(seed=s, B=float(brier(MB[s], d).mean()), TG=float(brier(MT[s], d).mean())) for s in range(len(MB))]
    out['seedPairsTGwin'] = sum(1 for x in out['perSeed'] if x['TG'] < x['B'])
    return out


def main():
    if hashlib.sha256(open(os.path.join(HERE, 'prereg.md'), 'rb').read()).hexdigest() != open(os.path.join(HERE, 'prereg.sha256')).read().strip():
        print('prereg sha mismatch'); return 1
    res = {}
    # ---------- 測試 M ----------
    P = J(os.path.join(HERE, 'results', 'pred-mock.json'))
    byi = {g['i']: g for g in J(os.path.join(WT, 'reports', 'E208-team-rating', 'inputs.json'))['games']}
    idx = [j for j, f in enumerate(P['first']) if not f]
    d = np.array([byi[P['games'][j]]['hs'] - byi[P['games'][j]]['as'] for j in idx], float)
    S = {k: np.array(v)[:, idx] for k, v in P['margin_seed'].items()}
    res['M'] = block(S['B'], S['TG'], d, 20261312)
    if 'E306mock' in S:
        res['M']['reproE306'] = dict(brierE306mock5=float(brier(S['E306mock'].mean(0), d).mean()), brierB5=float(brier(S['B'][:5].mean(0), d).mean()),
                                     corr=float(np.corrcoef(S['E306mock'].mean(0), S['B'][:5].mean(0))[0, 1]))
    # ---------- 測試 F ----------
    import actual_blend as ab
    G = ab.played_games(); Fd = J(os.path.join(HERE, 'work', 'pred-f.json'))
    gids = sorted(Fd, key=lambda g: (Fd[g]['date'], g))
    d = np.array([G[g]['pts_home'] - G[g]['pts_away'] for g in gids], float)
    S = {k: np.array([Fd[g]['seeds'][k] for g in gids]).T for k in ('B', 'TG', 'E306cut')}
    res['F'] = block(S['B'], S['TG'], d, 20261322)
    sub = np.array([Fd[g]['date'] <= '2026-11-20' for g in gids])
    res['F']['sub1120'] = block(S['B'][:, sub], S['TG'][:, sub], d[sub], 20261332); res['F']['sub1120'].pop('perSeed')
    res['F']['reproE306'] = dict(brierE306cut5=float(brier(S['E306cut'].mean(0), d).mean()), brierB5=float(brier(S['B'][:5].mean(0), d).mean()),
                                 corr=float(np.corrcoef(S['E306cut'].mean(0), S['B'][:5].mean(0))[0, 1]))
    res['F']['dateRange'] = [Fd[gids[0]]['date'], Fd[gids[-1]]['date']]
    # ---------- 判準 ----------
    c1 = res['M']['dBrier'] <= 0; c2 = all(v <= 0 for v in res['M']['halves'].values()); c3 = res['F']['dBrier'] <= 0.002
    res['verdict'] = dict(c1_M=c1, c2_halves=c2, c3_F=c3, adopt=bool(c1 and c2 and c3))
    # ---------- 只報告：本季 AG 前十（11-22 資料） ----------
    import e229_live
    dates = {k: v['date'] for k, v in G.items()}
    box = e229_live.season_box('2026-11-23')
    agm, ainf = TL.ag_mixed(box, TL.pbp_by_game(cache=os.path.join(HERE, 'work', 'pbp-per-game.json')), dates, '2026-11-23')
    ldir = sorted(f for f in os.listdir(e229_live.LIVE_ROOT) if f.startswith('2026-'))[-1]
    nm = {r['playerId']: r.get('name') or r.get('playerName') for r in csv.DictReader(open(os.path.join(e229_live.LIVE_ROOT, ldir, 'ranking.csv'), encoding='utf-8'))}
    top = sorted((p for p in ainf['curAG'] if box[p]['MIN'] >= 200), key=lambda p: -ainf['curAG'][p])[:10]
    res['agTop10'] = [dict(pid=p, name=nm.get(p), min=round(box[p]['MIN']), blk36=round(box[p]['BLK'] * 36 / box[p]['MIN'], 2),
                           agCur=round(ainf['curAG'][p], 3), agMixed=round(agm[p], 3)) for p in top]
    os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
    json.dump(res, open(os.path.join(HERE, 'results', 'eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k in ('M', 'F'):
        r = res[k]; print(k, {x: r[x] for x in ('n', 'brierB', 'brierTG', 'dBrier', 'dBrierCI90', 'dMAE', 'corr', 'halves', 'seedPairsTGwin') if x in r})
        print('  perSeed', [(x['seed'], round(x['B'], 4), round(x['TG'], 4)) for x in r['perSeed']]); print('  repro', r.get('reproE306'))
    print('F sub1120', {x: res['F']['sub1120'][x] for x in ('n', 'dBrier', 'dBrierCI90')}); print('verdict', res['verdict'])
    print('agTop10', res['agTop10'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
