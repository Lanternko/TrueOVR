"""E-284 評估（prereg.md 凍結）。用法（repo root）：python -I -B -X utf8 reports/E284-onoff-fouls/e284_eval.py"""
import importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_s = importlib.util.spec_from_file_location('dx_eval', ROOT / 'reports/E280-blk-weight/dx_eval.py')
DX = importlib.util.module_from_spec(_s); sys.modules['dx_eval'] = DX; _s.loader.exec_module(DX)
E280 = ROOT / 'reports/E280-blk-weight'
EXTRA = {'F1': (['f_on', 'f_off'], False), 'F2': (['f_on', 'f_off', 'f_gen'], False), 'F3': (['f_ball', 'f_off'], False)}


def _p(a):
    return lambda c: HERE / f'ranking-{a}-{c}.csv'


ARMS = {'F0': {'path': lambda c: E280 / f'ranking-K3-{c}.csv', 'extras': ['blk36'], 'window': True}}
for _a, (_ks, _np) in EXTRA.items():
    ARMS[_a] = {'path': _p(_a), 'extras': ['blk36'] + _ks, 'window': True, 'nopress': _np, 'work': HERE / 'work' / _a}


def main():
    if DX.Z.sha(HERE / 'prereg.md') != (HERE / 'prereg.sha256').read_text().split()[0]:
        print('prereg sha mismatch'); return 1
    res, F = DX.compute(ARMS, 'F0', 20261284)
    for a, (ks, _) in EXTRA.items():
        ar = res['arms'][a]
        fc = ar['fitted_coef']
        ar['sign_stable'] = {k: len({fc[t][k]['perSD'] > 0 for t in DX.ORIG}) == 1 for k in ks}
        ar['perSD'] = {k: [round(fc[t][k]['perSD'], 3) for t in DX.ORIG] for k in ks}
        ar['candidate'] = bool(ar['S2'] and ar['S3'])
    c = [a for a in EXTRA if res['arms'][a]['candidate']]
    dd = {a: res['arms'][a]['delta']['rhoDEF_epmD'] for a in c}
    best = max(dd, key=dd.get) if c else None
    res['adopt_candidate'] = 'F1' if best and 'F1' in dd and dd[best] - dd['F1'] <= 0.003 else best
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    DX.show(res, ARMS, 'F0')
    for a in EXTRA:
        print(a, 'cand', res['arms'][a]['candidate'], 'stable', res['arms'][a]['sign_stable'], res['arms'][a]['perSD'])
    print('adopt', res['adopt_candidate'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
