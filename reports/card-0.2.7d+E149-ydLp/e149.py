"""E-149 usage 層加 y·d·L·p。唯讀匯入 E-147 e147.py（連續 d、run_arm、metrics），只替換 e094 的 design()。
臂：K0（c0 逐位元＝card 0.2.7d）、Q1（多一欄 y·d·L·p 後重擬合）。
用法（repo 根目錄）：python -I -X utf8 "reports/card-0.2.7d+E149-ydLp/e149.py"
"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C027D_SHA = '696a8ac7b235acf51cdb5634fa9896a6905fec81adb96166b6995b9015c20649'
_spec = importlib.util.spec_from_file_location('e147', ROOT / 'reports/card-0.2.7c+E147-continuous-d/e147.py')
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
M = E.M
E.HERE = M.HERE = HERE
M.W, M.CARDS = HERE / 'work', HERE / 'cards'
ORIG_DESIGN = M.design


def design_q(sf, sel, k, p=None):
    X = ORIG_DESIGN(sf, sel, k, p)
    pp = sf['p'][sel] if p is None else p
    return np.column_stack([X, sf['y'][sel] * sf['d'][sel] * sf['L'][sel] * pp])


def main():
    want = (HERE / 'preregistration.sha256').read_text().split()[0]
    assert E.sha(HERE / 'preregistration.md') == want, '預註冊 sha256 與凍結值不同'
    M.load_data()
    M.set_card_dir(E.RB / 'cards/c0')
    pools = M.build_pools()
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(E.E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    tb = E.team_badness()
    k0, k0_calls = E.run_arm('K0', pools, pdnew, dcont=tb)
    c0 = E.sha(HERE / 'K0/ranking.csv')
    res = {'prereg_sha': want, 'c0': {'sha256': c0, 'want': C027D_SHA, 'pass': c0 == C027D_SHA}}
    if not res['c0']['pass']:
        print('c0 FAIL', c0); (HERE / 'results.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); return 1
    M.design = design_q
    try:
        q1, q1_calls = E.run_arm('Q1', pools, pdnew, dcont=tb)
    finally:
        M.design = ORIG_DESIGN
    names = M.COEF_NAMES + ['b9_ydLp']
    res['coef'] = {'K0': dict(zip(names, map(float, k0_calls[2]))), 'Q1': dict(zip(names, map(float, q1_calls[2])))}
    res['coef_halves_Q1'] = {dn: dict(zip(names, map(float, c))) for dn, c in zip(('AB', 'BA'), q1_calls[:2])}
    res['metrics'] = {arm: E.metrics(HERE / arm / 'ranking.csv') for arm in ('K0', 'Q1')}
    ev = M.e089_eval(q1['_aux']['dirs'], k0['_aux']['dirs'])
    res['eval_Q1_vs_K0'] = {m: {'pass': v['pass'], 'point': v['value']['point'], 'ci90': v['value']['ci90']} for m, v in ev['checks'].items()}
    rk = {arm: {r['name']: r for r in csv.DictReader(open(HERE / arm / 'ranking.csv', encoding='utf-8'))} for arm in ('K0', 'Q1')}
    a, b = rk['K0'], rk['Q1']
    R = lambda r: int(r['rank'])
    res['R064'] = {'top20_out': sorted(n for n in a if R(a[n]) <= 20 and R(b[n]) > 20), 'top20_in': sorted(n for n in b if R(b[n]) <= 20 and R(a[n]) > 20),
                   'top300_movers_ge10': sum(1 for n in a if R(a[n]) <= 300 and abs(R(a[n]) - R(b[n])) >= 10)}
    # y=1 且 d>0：用全季 scope_feats
    sf = M.scope_feats('full', M.D['prim'], M.classify(M.BASE_OPTS), M.BASE_OPTS)
    d_by_main = {t: tb[t]['d'] for t in tb}
    yd = []
    for i, q in enumerate(sf['pids']):
        t = sf['main'][i]
        if sf['y'][i] == 1 and t is not None and d_by_main.get(t, 0) > 0:
            n = M.D['prim'][q]['name']
            if n in a:
                yd.append({'name': n, 'team': M.D['abbr'].get(t, t), 'd': round(d_by_main[t], 3), 'p': round(float(sf['p'][i]), 3), 'MIN': float(a[n]['MIN']),
                           'ovr_K0': float(a[n]['ovr']), 'ovr_Q1': float(b[n]['ovr']), 'rank_K0': R(a[n]), 'rank_Q1': R(b[n])})
    res['young_bad'] = sorted(yd, key=lambda x: x['ovr_Q1'] - x['ovr_K0'])
    m0, m1 = res['metrics']['K0'], res['metrics']['Q1']
    res['judge'] = {'a_c0': res['c0']['pass'],
                    'b_metrics': {k: {'K0': m0[k]['rho'], 'Q1': m1[k]['rho'], 'pass': m1[k]['rho'] - m0[k]['rho'] >= -0.01} for k in m0},
                    'c_m': {m: v['pass'] for m, v in res['eval_Q1_vs_K0'].items()}}
    res['judge']['adopt_candidate'] = bool(res['judge']['a_c0'] and all(v['pass'] for v in res['judge']['b_metrics'].values()) and all(res['judge']['c_m'].values()))
    res['sha'] = {arm: E.sha(HERE / arm / 'ranking.csv') for arm in ('K0', 'Q1')}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('c0', 'coef', 'judge', 'R064')}, ensure_ascii=False, default=float))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
