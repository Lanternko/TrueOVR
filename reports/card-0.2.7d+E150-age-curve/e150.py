"""E-150 年齡旗標改連續：y→max(0,25−年齡)、v→max(0,年齡−29)，A2 另加 yc·g·L（g＝clip((s−0.60)/0.10)）。
唯讀匯入 E-147 e147.py（連續 d、run_arm、metrics），替換 scope_feats 的 y／v 與 design()。
用法（repo 根目錄）：python -I -X utf8 "reports/card-0.2.7d+E150-age-curve/e150.py"
"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C027D_SHA = '696a8ac7b235acf51cdb5634fa9896a6905fec81adb96166b6995b9015c20649'
_spec = importlib.util.spec_from_file_location('e147', ROOT / 'reports/card-0.2.7c+E147-continuous-d/e147.py')
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
M = E.M
E.HERE = M.HERE = HERE
M.W, M.CARDS = HERE / 'work', HERE / 'cards'
SF0, DESIGN0 = E.ORIG_SF, M.design
NAMED = ['Brandin Podziemski', 'Anthony Edwards', 'Cooper Flagg', 'LeBron James', 'Stephen Curry', 'Chris Paul', 'Victor Wembanyama', 'Ace Bailey', 'VJ Edgecombe', 'Ryan Rollins']


def make_sf(tb, cont_v, with_g):
    def sf(*a):
        r = SF0(*a)
        age = r['age']
        r['y'] = np.array([max(0.0, 25.0 - x) if x is not None else 0.0 for x in age])
        if cont_v:
            r['v'] = np.array([max(0.0, x - 29.0) if x is not None else 0.0 for x in age])
        if with_g:
            r['g'] = np.array([min(1.0, max(0.0, (tb[t]['s'] - 0.60) / 0.10)) if t is not None else 0.0 for t in r['main']])
        return r
    return sf


def design_g(sf, sel, k, p=None):
    X = DESIGN0(sf, sel, k, p)
    return np.column_stack([X, sf['y'][sel] * sf['g'][sel] * sf['L'][sel]])


def mdarko(path):
    dk = {int(r['playerId']): float(r['dpm']) for r in csv.DictReader(open(ROOT / 'data/external-impact/darko/darko_2025-26.csv', encoding='utf-8')) if r['dpm']}
    xs, ys = [], []
    for r in csv.DictReader(open(path, encoding='utf-8')):
        if float(r['MIN']) < 500:
            continue
        q = M.D['nm2pid'].get(r['name'])
        if q is not None and int(q) in dk:
            xs.append(float(r['ovr'])); ys.append(dk[int(q)])
    return {'n': len(xs), 'rho': float(spearmanr(xs, ys)[0])}


def run(arm, pools, pdnew, tb, sf=None, design=None):
    E.ORIG_SF = sf or SF0
    M.design = design or DESIGN0
    try:
        return E.run_arm(arm, pools, pdnew, dcont=tb)
    finally:
        E.ORIG_SF, M.design = SF0, DESIGN0


def agegrp(x):
    return '1 ≤21' if x <= 21 else '2 22–23' if x <= 23 else '3 24' if x == 24 else '4 25–29' if x <= 29 else '5 30–32' if x <= 32 else '6 ≥33'


def main():
    want = (HERE / 'preregistration.sha256').read_text().split()[0]
    assert E.sha(HERE / 'preregistration.md') == want, '預註冊 sha256 與凍結值不同'
    M.load_data()
    M.set_card_dir(E.RB / 'cards/c0')
    pools = M.build_pools()
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(E.E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    tb = E.team_badness()
    out = {'K0': run('K0', pools, pdnew, tb)}
    k0 = out['K0'][0]
    c0 = E.sha(HERE / 'K0/ranking.csv')
    res = {'prereg_sha': want, 'c0': {'sha256': c0, 'want': C027D_SHA, 'pass': c0 == C027D_SHA}}
    if not res['c0']['pass']:
        print('c0 FAIL', c0); (HERE / 'results.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); return 1
    out['A1'] = run('A1', pools, pdnew, tb, sf=make_sf(tb, True, False))
    out['A2'] = run('A2', pools, pdnew, tb, sf=make_sf(tb, True, True), design=design_g)
    out['A1y'] = run('A1y', pools, pdnew, tb, sf=make_sf(tb, False, False))
    arms = ['K0', 'A1', 'A2', 'A1y']
    cn = lambda a: M.COEF_NAMES + (['b9_ygL'] if a == 'A2' else [])
    res['coef'] = {a: dict(zip(cn(a), map(float, out[a][1][2]))) for a in arms}
    res['coef_halves'] = {a: {dn: dict(zip(cn(a), map(float, cc))) for dn, cc in zip(('AB', 'BA'), out[a][1][:2])} for a in arms[1:]}
    res['metrics'] = {}
    for a in arms:
        m = E.metrics(HERE / a / 'ranking.csv')
        m['Mdarko'] = mdarko(HERE / a / 'ranking.csv')
        res['metrics'][a] = m
    res['eval'] = {}
    for a in arms[1:]:
        ev = M.e089_eval(out[a][0]['_aux']['dirs'], k0['_aux']['dirs'])
        res['eval'][a] = {m: {'pass': v['pass'], 'point': v['value']['point'], 'ci90': v['value']['ci90']} for m, v in ev['checks'].items()}
    rk = {a: {r['name']: r for r in csv.DictReader(open(HERE / a / 'ranking.csv', encoding='utf-8'))} for a in arms}
    R = lambda r: int(r['rank'])
    base = rk['K0']
    res['by_arm'] = {}
    for a in arms[1:]:
        b = rk[a]
        grp = {}
        for n in base:
            age = M.D['age'].get(M.D['nm2pid'].get(n))
            if age is None or float(base[n]['MIN']) < 500:
                continue
            grp.setdefault(agegrp(age), []).append(float(b[n]['ovr']) - float(base[n]['ovr']))
        res['by_arm'][a] = {
            'age_group_mean_dOVR': {g: {'n': len(v), 'mean': round(float(np.mean(v)), 2)} for g, v in sorted(grp.items())},
            'R064': {'top20_out': sorted(n for n in base if R(base[n]) <= 20 and R(b[n]) > 20),
                     'top20_in': sorted(n for n in b if R(b[n]) <= 20 and R(base[n]) > 20),
                     'top300_movers_ge10': sum(1 for n in base if R(base[n]) <= 300 and abs(R(base[n]) - R(b[n])) >= 10)},
            'named': {n: [float(base[n]['ovr']), R(base[n]), float(b[n]['ovr']), R(b[n])] for n in NAMED if n in b},
            'big_movers': sorted(([n, float(base[n]['ovr']), float(b[n]['ovr']), R(base[n]), R(b[n])] for n in base
                                  if float(base[n]['MIN']) >= 500 and abs(float(b[n]['ovr']) - float(base[n]['ovr'])) >= 3), key=lambda x: x[2] - x[1])}
    m0 = res['metrics']['K0']
    judge = {}
    for a in ('A1', 'A2'):
        bm = {k: {'K0': m0[k]['rho'], a: res['metrics'][a][k]['rho'], 'pass': res['metrics'][a][k]['rho'] - m0[k]['rho'] >= -0.01} for k in m0}
        cm = {m: v['pass'] for m, v in res['eval'][a].items()}
        judge[a] = {'b': bm, 'c': cm, 'pass': bool(res['c0']['pass'] and all(v['pass'] for v in bm.values()) and all(cm.values())),
                    'm_mean': float(np.mean([v['point'] for v in res['eval'][a].values()]))}
    passing = [a for a in ('A1', 'A2') if judge[a]['pass']]
    if not passing:
        rec = 'K0'
    elif len(passing) == 1:
        rec = passing[0]
    else:
        rec = 'A2' if judge['A2']['m_mean'] - judge['A1']['m_mean'] >= 0.001 else 'A1'
    res['judge'], res['recommend'] = judge, rec
    res['sha'] = {a: E.sha(HERE / a / 'ranking.csv') for a in arms}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('c0', 'judge', 'recommend')}, ensure_ascii=False, default=float))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
