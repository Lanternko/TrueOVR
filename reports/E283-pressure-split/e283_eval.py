"""E-283 評估（prereg.md 凍結）。用法（repo root）：python -I -B -X utf8 reports/E283-pressure-split/e283_eval.py"""
import importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_s = importlib.util.spec_from_file_location('dx_eval', ROOT / 'reports/E280-blk-weight/dx_eval.py')
DX = importlib.util.module_from_spec(_s); sys.modules['dx_eval'] = DX; _s.loader.exec_module(DX)
E280 = ROOT / 'reports/E280-blk-weight'
P4 = ['p_stl', 'p_defl', 'p_mtov', 'p_chg']
EXTRA = {'Q1': (P4, True), 'Q2': (P4 + ['p_pf'], True), 'Q3': (P4, False)}


def _p(a):
    return lambda c: HERE / f'ranking-{a}-{c}.csv'


ARMS = {'Q0': {'path': lambda c: E280 / f'ranking-K3-{c}.csv', 'extras': ['blk36'], 'window': True}}
for _a, (_ks, _np) in EXTRA.items():
    ARMS[_a] = {'path': _p(_a), 'extras': ['blk36'] + _ks, 'window': True, 'nopress': _np, 'work': HERE / 'work' / _a}


def main():
    if DX.Z.sha(HERE / 'prereg.md') != (HERE / 'prereg.sha256').read_text().split()[0]:
        print('prereg sha mismatch'); return 1
    res, F = DX.compute(ARMS, 'Q0', 20261283)
    for a, (ks, _) in EXTRA.items():
        ar = res['arms'][a]
        fc = ar['fitted_coef']
        ar['sign_stable'] = {k: len({fc[t][k]['perSD'] > 0 for t in DX.ORIG}) == 1 for k in ks}
        ar['perSD'] = {k: [round(fc[t][k]['perSD'], 3) for t in DX.ORIG] for k in ks}
        ar['candidate'] = bool(ar['S2'] and ar['S3']) if a != 'Q3' else None
    c = [a for a in ('Q1', 'Q2') if res['arms'][a]['candidate']]
    if len(c) == 2:
        d1, d2 = (res['arms'][a]['delta']['rhoDEF_epmD'] for a in c)
        res['adopt_candidate'] = 'Q2' if d2 > d1 + 0.003 else 'Q1'
    else:
        res['adopt_candidate'] = c[0] if c else None
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    DX.show(res, ARMS, 'Q0')
    for a in EXTRA:
        print(a, 'cand', res['arms'][a]['candidate'], 'stable', res['arms'][a]['sign_stable'], res['arms'][a]['perSD'])
    print('adopt', res['adopt_candidate'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
