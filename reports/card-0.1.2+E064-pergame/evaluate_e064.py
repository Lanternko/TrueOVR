"""E-064 卡片端驗收（預註冊 §3.2、§3.3）。python -I reports/card-0.1.2+E064-pergame/evaluate_e064.py  → verdict.json

預測（OVR 是這些值的單調函數，ρ 只看名次，所以直接用 pred／g／g_r）：
  OVR_36   = fitX 卡的 pred（每 36）
  OVR_game = fitX 卡的 g = pred*MPG_X/36     MPG_X = 擬合那一半的 2025-26 場次平均分鐘
  OVR_repl = fitX 卡的 g_r = (pred-PR10)*MPG_X/36
  MPG      = MPG_X 本身
答案：另一半的 RAPM pooledNet * MPG_Y（Y 為評估半）。
人群：v58-holdout 共同球員 ∩ 評估半 pooledPoss >= 2500 ∩ 2025-26 在 A、B 兩半各 >= 5 場。
bootstrap：以球員配對重抽 2000 次、seed 1；兩個方向用同一組抽樣（在兩方向人群的聯集上抽，各方向只取落在自己人群內的抽樣）。
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
V58 = ROOT / 'reports/ovr-v58-holdout-2025-26'
E060 = ROOT / 'reports/card-0.1.1+E060-onball-targeting'
THR, MIN_G = 2500, 5
FROZEN = ['reports/ovr-calibrated-2025-26/ranking.csv', 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv',
          'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv', 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv',
          'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv']


def read(p, enc='utf-8-sig'):
    return list(csv.DictReader(open(p, encoding=enc)))


def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_card(d):
    pr = {r['name']: r for r in read(HERE / d / 'pred.csv')}
    return pr, json.loads((HERE / d / 'pergame-summary.json').read_text(encoding='utf-8'))


def main():
    out = {}
    # ---- (c0)
    base = E060 / 'primary/ranking.csv'
    c0 = {}
    for d in ('c0-switch-off', 'primary'):
        a = read(HERE / d / 'ranking.csv'); b = read(base)
        mx = max(abs(float(x['ovr']) - float(y['ovr'])) for x, y in zip(a, b)) if len(a) == len(b) else None
        c0[d] = {'sha256': sha(HERE / d / 'ranking.csv'), 'byteIdentical': sha(HERE / d / 'ranking.csv') == sha(base), 'rows': len(a), 'maxAbsOvrDiff': mx}
    c0['baseline'] = {'file': str(base.relative_to(ROOT)), 'sha256': sha(base)}
    c0['pass'] = bool(c0['c0-switch-off']['byteIdentical'] or (c0['c0-switch-off']['maxAbsOvrDiff'] is not None and c0['c0-switch-off']['maxAbsOvrDiff'] < 1e-9))
    c0['note'] = 'summary.json 只有 defenseBonusPosMeanD 的鍵順序不同（set 迭代順序隨 hash seed 變），數值相同；ranking.csv 逐位元相同。'
    out['c0'] = c0
    # ---- (c1)
    lines = (HERE / 'npm-test.log').read_text(encoding='utf-8', errors='replace').splitlines()
    out['c1'] = {'npmExit': int((HERE / 'npm-test.exit').read_text().strip()), 'log': 'npm-test.log',
                 'summaryLine': [l for l in lines if 'passed' in l and 'failed' in l][-1].strip()}
    out['c1']['pass'] = out['c1']['npmExit'] == 0 and ' 0 failed' in out['c1']['summaryLine']

    # ---- populations
    rapm = {h: {r['name']: r for r in read(V58 / f'rapm-{h}.csv') if r['name']} for h in 'AB'}
    k2 = {r['name']: float(r['overall2k']) for r in read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    sets = [set(r['name'] for r in read(ROOT / p)) for p in FROZEN]
    for sc in ('0.5', '1.0'):
        for fit in 'AB':
            for k in ('E2', 'F2', 'G3', 'H1-m0'):
                sets.append(set(r['name'] for r in read(V58 / f'fit{fit}-scale{sc}' / k / 'ranking.csv')))
    common_v58 = set.intersection(*sets) & set(k2)
    fitcards = {h: load_card(f'fit{h}') for h in 'AB'}
    prim, prim_sum = load_card('primary')
    common = common_v58 & set(fitcards['A'][0]) & set(fitcards['B'][0]) & set(prim)
    mpg = {h: {int(r['playerId']): (int(r['gp']), float(r['mpg'])) for r in read(HERE / f'mpg-{h}.csv')} for h in 'AB'}
    pid = {n: int(r['playerId']) for n, r in prim.items()}

    def games_ok(n):
        return all(pid[n] in mpg[h] and mpg[h][pid[n]][0] >= MIN_G for h in 'AB')
    pools = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        pools[fit + ev] = sorted(n for n in common if n in rapm[ev] and float(rapm[ev][n]['pooledPoss']) >= THR and games_ok(n))
    out['population'] = {'v58CommonPlayers': len(common_v58), 'commonWithE064Cards': len(common), 'A_to_B_n': len(pools['AB']), 'B_to_A_n': len(pools['BA']),
                         'unionN': len(set(pools['AB']) | set(pools['BA'])), 'threshold': THR, 'minGamesEachHalf': MIN_G}

    def variants(fit):
        pr, sm = fitcards[fit]
        names = sorted(pr)
        pred = {n: float(pr[n]['pred']) for n in names}
        m = {n: (float(pr[n]['mpg']) if pr[n]['mpg'] != '' else 0.0) for n in names}
        rr = sm['rRepl_PR10_of_pred']
        return {'ovr36': dict(pred), 'game': {n: pred[n] * m[n] / 36 for n in names},
                'repl': {n: (pred[n] - rr) * m[n] / 36 for n in names}, 'mpg': m}
    V = {fit: variants(fit) for fit in 'AB'}
    master = sorted(set(pools['AB']) | set(pools['BA']))
    keys = ['ovr36', 'game', 'repl', 'mpg']
    dirs = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        names = pools[fit + ev]
        dirs[fit + ev] = {'names': names,
                          'ansPG': np.array([float(rapm[ev][n]['pooledNet']) * mpg[ev][pid[n]][1] for n in names]),
                          'ansOld': np.array([float(rapm[ev][n]['pooledNet']) for n in names]),
                          **{k: np.array([V[fit][k][n] for n in names]) for k in keys}}
    res = {}
    for dname, d in dirs.items():
        res[dname] = {'n': len(d['names']), 'newTarget_perGame': {k: rho(d[k], d['ansPG']) for k in keys},
                      'oldTarget_per100': {k: rho(d[k], d['ansOld']) for k in keys}}
    summ = {tgt: {k: float(np.mean([res[x][tgt][k] for x in res])) for k in keys} for tgt in ('newTarget_perGame', 'oldTarget_per100')}
    out['rho'] = {'byDirection': res, 'avg': summ}

    # ---- bootstrap（同一組抽樣、兩方向共用）
    rng = np.random.default_rng(1)
    N = len(master)
    mp = {dn: np.array([{n: i for i, n in enumerate(d['names'])}.get(n, -1) for n in master]) for dn, d in dirs.items()}
    pairs = {'c2': ('game', 'ovr36'), 'c3': ('game', 'mpg'), 'c2_repl': ('repl', 'ovr36'), 'c3_repl': ('repl', 'mpg'), 'game_vs_repl': ('game', 'repl')}
    boot = {p: [] for p in pairs}
    for _ in range(2000):
        idx = rng.integers(0, N, N)
        dl = {p: [] for p in pairs}
        for dname, d in dirs.items():
            sel = mp[dname][idx]; sel = sel[sel >= 0]
            a = d['ansPG'][sel]
            r = {k: rho(d[k][sel], a) for k in keys}
            for p, (x, y) in pairs.items():
                dl[p].append(r[x] - r[y])
        for p in pairs:
            boot[p].append(float(np.mean(dl[p])))
    boots = {}
    for p, (x, y) in pairs.items():
        b = np.array(boot[p])
        pt = float(np.mean([res[dn]['newTarget_perGame'][x] - res[dn]['newTarget_perGame'][y] for dn in dirs]))
        boots[p] = {'a': x, 'b': y, 'delta': pt, 'ci90': [float(np.percentile(b, 5)), float(np.percentile(b, 95))],
                    'byDirectionDelta': {dn: res[dn]['newTarget_perGame'][x] - res[dn]['newTarget_perGame'][y] for dn in dirs},
                    'bootMean': float(b.mean())}
    out['bootstrap'] = {'resamples': 2000, 'seed': 1, 'unit': 'player (union of both directions)', 'results': boots}
    out['c2'] = {'delta': boots['c2']['delta'], 'ci90': boots['c2']['ci90'], 'pass': bool(boots['c2']['ci90'][0] > 0)}
    out['c3'] = {'delta': boots['c3']['delta'], 'ci90': boots['c3']['ci90'], 'pass': bool(boots['c3']['ci90'][0] > 0)}
    if not out['c0']['pass']:
        out['cardSide'] = '(c0) 不過，整輪停止'
    elif all([out['c1']['pass'], out['c2']['pass'], out['c3']['pass']]):
        out['cardSide'] = '通過'
    elif out['c2']['pass'] and out['c1']['pass'] and not out['c3']['pass']:
        out['cardSide'] = '每場 OVR 幾乎等於上場時間（c3 不過），不自動採用，交使用者決定'
    else:
        out['cardSide'] = '未通過'

    # ---- 2K27 ρ
    names2k = sorted(common)
    t2k = [k2[n] for n in names2k]
    full = {n: (float(prim[n]['pred']), float(prim[n]['mpg'])) for n in names2k}
    rr = prim_sum['rRepl_PR10_of_pred']
    out['rho2k'] = {'n': len(names2k),
                    'full': {'ovr36': rho([full[n][0] for n in names2k], t2k), 'game': rho([full[n][0] * full[n][1] / 36 for n in names2k], t2k),
                             'repl': rho([(full[n][0] - rr) * full[n][1] / 36 for n in names2k], t2k), 'mpg': rho([full[n][1] for n in names2k], t2k)},
                    'halfFitMean': {k: float(np.mean([rho([V[f][k][n] for n in names2k], t2k) for f in 'AB'])) for k in keys}}
    # ---- 抽查材料（全量卡 primary；0.1.2 = E060 primary/ranking.csv）
    base_rows = read(E060 / 'primary/ranking.csv')
    base_rank = {r['name']: (int(r['rank']), float(r['ovr'])) for r in base_rows}
    main_rows = read(HERE / 'primary/pergame-main.csv'); repl_rows = read(HERE / 'primary/pergame-repl.csv')
    main_rank = {r['name']: (int(r['rank']), round(float(r['ovr']), 1)) for r in main_rows}
    repl_rank = {r['name']: (int(r['rank']), round(float(r['ovr']), 1)) for r in repl_rows}
    posof = {r['name']: r['pos'] for r in base_rows}
    mpgof = {n: float(prim[n]['mpg']) for n in prim}
    BIGS = {'C', 'PF'}

    def top(rows, k):
        return [r['name'] for r in rows[:k]]
    out['spot'] = {
        'top20_main': [{'name': r['name'], 'pos': r['pos'], 'mpg': round(mpgof[r['name']], 1), 'main': main_rank[r['name']], 'repl': repl_rank[r['name']],
                        'v012': base_rank[r['name']]} for r in main_rows[:20]],
        'top20_repl': [{'name': r['name'], 'pos': r['pos'], 'mpg': round(mpgof[r['name']], 1), 'repl': repl_rank[r['name']], 'main': main_rank[r['name']],
                        'v012': base_rank[r['name']]} for r in repl_rows[:20]],
        'top20_v012': [{'name': r['name'], 'pos': r['pos'], 'v012': base_rank[r['name']], 'main': main_rank.get(r['name']), 'repl': repl_rank.get(r['name'])} for r in base_rows[:20]],
        'bigsInTop10': {k: [n for n in top(rows, 10) if posof[n] in BIGS] for k, rows in (('main', main_rows), ('repl', repl_rows), ('v012', base_rows))},
        'players': {n: {'pos': posof.get(n), 'mpg': round(mpgof[n], 1) if n in mpgof else None, 'v012': base_rank.get(n), 'main': main_rank.get(n), 'repl': repl_rank.get(n)}
                    for n in ('Ty Jerome', 'Tyrese Maxey', 'Walker Kessler', 'Nikola Jokić')}}

    def inversion(rows):
        low = [float(r['ovr']) for r in rows if float(r['mpg']) < 12]
        hi = [r for r in rows if float(r['mpg']) >= 20]
        med = float(np.median(low)) if low else None
        return {'poolN': len(rows), 'n_mpg_lt12': len(low), 'medianOvr_mpg_lt12': med, 'n_mpg_ge20': len(hi),
                'n_ge20_below_median': sum(float(r['ovr']) < med for r in hi) if med is not None else None,
                'names': [r['name'] for r in hi if float(r['ovr']) < med] if med is not None else []}
    out['inversion'] = {'main': inversion([r for r in main_rows if float(r['MIN']) >= 500]), 'repl': inversion([r for r in repl_rows if float(r['MIN']) >= 500])}
    cr = [(r['name'], float(r['creation']), float(r['MIN'])) for r in base_rows]
    out['creation99'] = {'allPlayers': sum(c >= 98.95 for _, c, _ in cr), 'minGe500': sum(c >= 98.95 and m >= 500 for _, c, m in cr),
                         'total': len(cr), 'poolMinGe500': sum(m >= 500 for _, _, m in cr)}
    pgfull = {int(r['playerId']): float(r['mpg']) for r in read(HERE / 'mpg-full.csv')}
    out['mpgCheck'] = {'maxAbsDiff_leagueObserved_vs_playerGames': float(max(abs(mpgof[n] - pgfull[pid[n]]) for n in prim if pid[n] in pgfull))}
    out['anchors'] = {'primary': prim_sum['anchors'], 'rRepl': prim_sum['rRepl_PR10_of_pred'], 'fitA': fitcards['A'][1]['anchors'], 'fitB': fitcards['B'][1]['anchors']}
    out['inputs'] = {'preregistrationSha256': sha(HERE / 'preregistration.md'), 'playerGamesSha256': sha(ROOT / 'data/season-source/player-games.json'),
                     'rapmA': sha(V58 / 'rapm-A.csv'), 'rapmB': sha(V58 / 'rapm-B.csv')}
    (HERE / 'verdict.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    f = lambda v: f'{v:.4f}'
    print('c0', c0['pass'], 'c1', out['c1']['pass'])
    print('c2', f(out['c2']['delta']), [f(x) for x in out['c2']['ci90']], out['c2']['pass'])
    print('c3', f(out['c3']['delta']), [f(x) for x in out['c3']['ci90']], out['c3']['pass'])
    print('card side:', out['cardSide'])
    print(json.dumps(out['population']), json.dumps(summ))


if __name__ == '__main__':
    main()
