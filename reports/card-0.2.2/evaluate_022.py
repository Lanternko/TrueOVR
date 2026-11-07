"""card 0.2.2 關卡判定（c0a、c0b、c1、c2、c3）與只報告項。python -I reports/card-0.2.2/evaluate_022.py → gates.json
c2 方法複本自 reports/card-0.2.0+E071-pressure/evaluate_e071.py（G4 RAPM 分半、同人群、同 seed 1、bootstrap 2000 次；g_r=(pred−r_repl)·MPG/36）。
比較：merged(P1，card 0.2.2) − card 0.2.0（門檻 CI 下界 > −0.02）；merged − E-070 primary（只報告）；另附 merged − E-071 P1、E070 − card 0.2.0（只報告）。
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E064 = ROOT / 'reports/card-0.1.2+E064-pergame'
V58 = ROOT / 'reports/ovr-v58-holdout-2025-26'
E070 = ROOT / 'reports/card-0.2.0+E070-foul-volume'
E071 = ROOT / 'reports/card-0.2.0+E071-pressure'
THR, MIN_G = 2500, 5
FROZEN = ['reports/ovr-calibrated-2025-26/ranking.csv', 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv',
          'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv', 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv',
          'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv']
# 變體 → 資料夾（含 primary／fitA／fitB 的 pred.csv、pergame-summary.json）
DIRS = {'c020': E071 / 'cards/base', 'E070': E070 / 'cards-w075', 'M': HERE / 'cards/P1', 'E071P1': E071 / 'cards/P1', 'Mbase': HERE / 'cards/base'}
VARS = list(DIRS)
DERIVED = ['rank', 'ovr', 'predictedPer36', 'simulatedPer36', 'defenseBonus', 'align', 'pred0', 'pr', 'mpg', 'gRepl', 'ovr36']
SPOT = ['Moussa Diabaté', 'Kyle Lowry', 'Luguentz Dort', 'Shai Gilgeous-Alexander', 'Dru Smith', 'Ausar Thompson']


def read(p, enc='utf-8-sig'):
    return list(csv.DictReader(open(p, encoding=enc)))


def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def same_bytes(a, b):
    return Path(a).read_bytes() == Path(b).read_bytes()


def main():
    out = {}
    # ---------- c0a
    w = E070 / 'cards-w075'
    mb = HERE / 'cards/base'
    c0a_files = {f'{p}/{f}': same_bytes(mb / p / f, w / p / f) for p in ('primary', 'fitA', 'fitB') for f in ('ranking.csv', 'pergame-repl.csv', 'pred.csv', 'pergame-main.csv')}
    card_base = read(mb / 'card/ranking.csv', 'utf-8')
    e070_rank = read(E070 / 'primary/ranking.csv', 'utf-8')
    mx = max(abs(float(x['ovr']) - float(y['ovr'])) for x, y in zip(card_base, e070_rank)) if len(card_base) == len(e070_rank) else None
    card_byte = same_bytes(mb / 'card/ranking.csv', E070 / 'primary/ranking.csv')
    c0a_ok = c0a_files['primary/ranking.csv'] and c0a_files['primary/pergame-repl.csv'] and (card_byte or (mx is not None and mx < 1e-9))
    out['c0a'] = {'pass': bool(c0a_ok), 'primaryRankingIdentical': c0a_files['primary/ranking.csv'], 'primaryPergameReplIdentical': c0a_files['primary/pergame-repl.csv'],
                  'cardBaseVsE070PrimaryByteIdentical': card_byte, 'cardBaseVsE070PrimaryMaxAbsOvrDiff': mx, 'rows': len(card_base),
                  'allFilesIdenticalVsE070cardsW075': c0a_files, 'sha256CardBase': sha(mb / 'card/ranking.csv'), 'sha256E070Primary': sha(E070 / 'primary/ranking.csv')}

    # ---------- c0b
    pm = {r['name']: r for r in read(HERE / 'cards/P1/card/ranking.csv', 'utf-8')}
    bm = {r['name']: r for r in card_base}
    cols = list(next(iter(pm.values())).keys())
    differ = {}
    for c in cols:
        n = sum(pm[k][c] != bm[k][c] for k in pm)
        if n:
            differ[c] = n
    unexpected = [c for c in differ if c not in ['pressure'] + DERIVED]
    prim_cols = [c for c in cols if c not in DERIVED and c != 'pressure']
    attr_same = all(pm[k][c] == bm[k][c] for k in pm for c in prim_cols) and set(pm) == set(bm)
    e71 = {r['name']: r for r in read(E071 / 'cards/P1/card/ranking.csv', 'utf-8')}
    c20card = {r['name']: r for r in read(E071 / 'cards/base/card/ranking.csv', 'utf-8')}
    fd_diff = sum(pm[k]['foulDraw'] != e71[k]['foulDraw'] for k in pm)
    out['c0b'] = {'pass': bool(attr_same and not unexpected and fd_diff > 0), 'columnsDifferingP1VsBase': differ, 'unexpectedColumns': unexpected,
                  'nonDerivedNonPressureColumnsIdentical': bool(attr_same), 'foulDrawDiffersVsE071P1_players': fd_diff,
                  'foulDrawDiffersVsE071P1_expected': '> 0',
                  'foulDrawDiffersVsCard020_players': sum(pm[k]['foulDraw'] != c20card[k]['foulDraw'] for k in pm)}

    # ---------- c1
    ne = (HERE / 'npm-test.exit').read_text().strip()
    out['c1'] = {'pass': ne == '0', 'npmExit': int(ne)}

    # ---------- c3
    ev = json.loads((HERE / 'evaluation.json').read_text(encoding='utf-8'))
    gates = {c['label']: c['gates']['pass'] for c in ev['candidates']}
    out['c3'] = {'pass': gates['card0.2.2'] >= gates['card0.2.0'], 'gatesPassed': gates, 'of': ev['candidates'][0]['gates']['of'],
                 'rho2kRapmDef': {c['label']: [c['rho2k'], c['rhoRapm'], c['rhoDef']] for c in ev['candidates']}}

    # ---------- c2
    rapm = {h: {r['name']: r for r in read(V58 / f'rapm-{h}.csv') if r['name']} for h in 'AB'}
    k2 = {r['name']: float(r['overall2k']) for r in read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    sets = [set(r['name'] for r in read(ROOT / p)) for p in FROZEN]
    for sc in ('0.5', '1.0'):
        for fit in 'AB':
            for k in ('E2', 'F2', 'G3', 'H1-m0'):
                sets.append(set(r['name'] for r in read(V58 / f'fit{fit}-scale{sc}' / k / 'ranking.csv')))
    common_v58 = set.intersection(*sets) & set(k2)
    preds = {(v, p): {r['name']: r for r in read(DIRS[v] / p / 'pred.csv')} for v in VARS for p in ('primary', 'fitA', 'fitB')}
    summ = {(v, p): json.loads((DIRS[v] / p / 'pergame-summary.json').read_text(encoding='utf-8')) for v in VARS for p in ('primary', 'fitA', 'fitB')}
    common = set(common_v58)
    for pr in preds.values():
        common &= set(pr)
    mpg = {h: {int(r['playerId']): (int(r['gp']), float(r['mpg'])) for r in read(E064 / f'mpg-{h}.csv')} for h in 'AB'}
    pid = {n: int(r['playerId']) for n, r in preds[('c020', 'primary')].items()}
    pools = {}
    for fit, ev_ in (('A', 'B'), ('B', 'A')):
        pools[fit + ev_] = sorted(n for n in common if n in rapm[ev_] and float(rapm[ev_][n]['pooledPoss']) >= THR
                                  and all(pid[n] in mpg[h] and mpg[h][pid[n]][0] >= MIN_G for h in 'AB'))
    out['population'] = {'v58CommonPlayers': len(common_v58), 'commonWithCards': len(common), 'A_to_B_n': len(pools['AB']), 'B_to_A_n': len(pools['BA']),
                         'unionN': len(set(pools['AB']) | set(pools['BA'])), 'threshold': THR, 'minGamesEachHalf': MIN_G}

    def repl_of(v, fit):
        pr = preds[(v, 'fit' + fit)]
        rr = summ[(v, 'fit' + fit)]['rRepl_PR10_of_pred']
        return {n: (float(r['pred']) - rr) * (float(r['mpg']) if r['mpg'] != '' else 0.0) / 36 for n, r in pr.items()}
    V = {(v, f): repl_of(v, f) for v in VARS for f in 'AB'}
    master = sorted(set(pools['AB']) | set(pools['BA']))
    dirs = {}
    for fit, ev_ in (('A', 'B'), ('B', 'A')):
        names = pools[fit + ev_]
        dirs[fit + ev_] = {'names': names, 'ans': np.array([float(rapm[ev_][n]['pooledNet']) * mpg[ev_][pid[n]][1] for n in names])}
        for v in VARS:
            dirs[fit + ev_][v] = np.array([V[(v, fit)][n] for n in names])
    res = {dn: {'n': len(d['names']), **{v: rho(d[v], d['ans']) for v in VARS}} for dn, d in dirs.items()}
    out['rho'] = {'byDirection': res, 'avg': {v: float(np.mean([res[dn][v] for dn in dirs])) for v in VARS}}
    rng = np.random.default_rng(1)
    N = len(master)
    mp = {dn: np.array([{n: i for i, n in enumerate(d['names'])}.get(n, -1) for n in master]) for dn, d in dirs.items()}
    pairs = {'M-c020': ('M', 'c020'), 'M-E070': ('M', 'E070'), 'M-E071P1': ('M', 'E071P1'), 'E070-c020': ('E070', 'c020'), 'E071P1-c020': ('E071P1', 'c020'),
             'Mbase-E070': ('Mbase', 'E070')}
    boot = {p: [] for p in pairs}
    for _ in range(2000):
        idx = rng.integers(0, N, N)
        dl = {p: [] for p in pairs}
        for dn, d in dirs.items():
            sel = mp[dn][idx]
            sel = sel[sel >= 0]
            a = d['ans'][sel]
            r = {v: rho(d[v][sel], a) for v in VARS}
            for p, (x, y) in pairs.items():
                dl[p].append(r[x] - r[y])
        for p in pairs:
            boot[p].append(float(np.mean(dl[p])))
    boots = {}
    for p, (x, y) in pairs.items():
        b = np.array(boot[p])
        boots[p] = {'delta': float(np.mean([res[dn][x] - res[dn][y] for dn in dirs])), 'ci90': [float(np.percentile(b, 5)), float(np.percentile(b, 95))],
                    'byDirectionDelta': {dn: res[dn][x] - res[dn][y] for dn in dirs}}
    out['bootstrap'] = {'resamples': 2000, 'seed': 1, 'unit': 'player (union of both directions)', 'results': boots}
    out['c2'] = {'pass': bool(boots['M-c020']['ci90'][0] > -0.02), 'threshold': 'CI90 lower > -0.02', 'delta': boots['M-c020']['delta'], 'ci90': boots['M-c020']['ci90'],
                 'vsCard020': boots['M-c020'], 'vsE070primary_reportOnly': boots['M-E070'], 'rhoAvg': out['rho']['avg']}

    # ---------- 2K27 ρ（只報告）
    names2k = sorted(common)
    t2k = [k2[n] for n in names2k]
    rho2k = {}
    for v in ('c020', 'E070', 'E071P1', 'M'):
        pr = preds[(v, 'primary')]
        rr = summ[(v, 'primary')]['rRepl_PR10_of_pred']
        rho2k[v] = {'perGame_repl': rho([(float(pr[n]['pred']) - rr) * float(pr[n]['mpg']) / 36 for n in names2k], t2k),
                    'per36': rho([float(pr[n]['pred']) for n in names2k], t2k),
                    'halfFitMean_perGame': float(np.mean([rho([V[(v, f)][n] for n in names2k], t2k) for f in 'AB']))}
    out['rho2k'] = {'n': len(names2k), **rho2k}

    # ---------- 前 20 名異動
    pub021 = read(ROOT / 'reports/card-0.2.1/ranking.csv', 'utf-8')
    c020 = read(ROOT / 'reports/card-0.2.0/ranking.csv', 'utf-8')
    new = read(HERE / 'ranking.csv', 'utf-8')
    b21 = {r['name']: r for r in pub021}
    b20 = {r['name']: r for r in c020}
    b70 = {r['name']: r for r in e070_rank}
    top = lambda rows: [r['name'] for r in rows[:20]]
    ch = {}
    for lab, ref in (('vs_card0.2.1_published', pub021), ('vs_card0.2.0', c020)):
        rt, nt = top(ref), top(new)
        ent, ex = [n for n in nt if n not in rt], [n for n in rt if n not in nt]
        ch[lab] = {'entered': ent, 'exited': ex, 'nEntered': len(ent), 'nExited': len(ex), 'needG4': len(ent) > 3 or len(ex) > 3,
                   'note': 'c2 本身就是 G4'}
    ch['top20'] = [{'rank': int(r['rank']), 'name': r['name'], 'pos': r['pos'], 'ovr': float(r['ovr']),
                    'rank021': int(b21[r['name']]['rank']), 'rank020': int(b20[r['name']]['rank'])} for r in new[:20]]
    out['top20Changes'] = ch
    out['maxAbsOvrDelta'] = {'vs021': max(abs(float(r['ovr']) - float(b21[r['name']]['ovr'])) for r in new),
                             'vs020': max(abs(float(r['ovr']) - float(b20[r['name']]['ovr'])) for r in new)}

    # ---------- 抽查
    spot = []
    for n in SPOT:
        r = next((x for x in new if x['name'] == n), None)
        if r is None:
            spot.append({'name': n, 'missing': True})
            continue
        g = lambda d, k: (float(d[n][k]) if d[n].get(k, '') != '' else None)
        spot.append({'name': n, 'pos': r['pos'], 'MIN': int(r['MIN']),
                     'v022': {'ovr': float(r['ovr']), 'rank': int(r['rank']), 'PRES': float(r['pressure']), 'presDisplay': float(r['presDisplay']), 'foulDisc': float(r['foulDisc']), 'foulDraw': float(r['foulDraw'])},
                     'v021': {'ovr': g(b21, 'ovr'), 'rank': int(b21[n]['rank']), 'PRES': g(b21, 'pressure'), 'presDisplay': g(b21, 'presDisplay'), 'foulDisc': g(b21, 'foulDisc'), 'foulDraw': g(b21, 'foulDraw')},
                     'v020': {'ovr': g(b20, 'ovr'), 'rank': int(b20[n]['rank']), 'PRES': g(b20, 'pressure'), 'foulDraw': g(b20, 'foulDraw')},
                     'E070': {'ovr': g(b70, 'ovr'), 'rank': int(b70[n]['rank']), 'foulDraw': g(b70, 'foulDraw')}})
    out['spotCheck'] = spot
    out['allPass'] = all(out[k]['pass'] for k in ('c0a', 'c0b', 'c1', 'c2', 'c3'))
    out['inputs'] = {'rapmA': sha(V58 / 'rapm-A.csv'), 'rapmB': sha(V58 / 'rapm-B.csv'), 'ranking_csv_sha256': sha(HERE / 'ranking.csv'),
                     'evaluation_json': sha(HERE / 'evaluation.json')}
    (HERE / 'gates.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    f = lambda v: f'{v:.4f}'
    print({k: out[k]['pass'] for k in ('c0a', 'c0b', 'c1', 'c2', 'c3')})
    print('c0a', {k: out['c0a'][k] for k in ('cardBaseVsE070PrimaryByteIdentical', 'cardBaseVsE070PrimaryMaxAbsOvrDiff')}, 'allfiles', all(c0a_files.values()))
    print('c0b', out['c0b'])
    print('population', out['population'])
    print('rho avg', {k: round(v, 4) for k, v in out['rho']['avg'].items()})
    for p, b in boots.items():
        print(p, f(b['delta']), [f(x) for x in b['ci90']])
    print('2K27', json.dumps(out['rho2k']))
    print('c3', out['c3']['gatesPassed'], 'top20', json.dumps({k: (v['nEntered'], v['nExited']) for k, v in ch.items() if k != 'top20'}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
