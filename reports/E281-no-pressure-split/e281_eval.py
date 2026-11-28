"""E-281 評估（prereg.md 凍結）。用法（repo root）：python -I -B -X utf8 reports/E281-no-pressure-split/e281_eval.py"""
import importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_s = importlib.util.spec_from_file_location('dx_eval', ROOT / 'reports/E280-blk-weight/dx_eval.py')
DX = importlib.util.module_from_spec(_s); sys.modules['dx_eval'] = DX; _s.loader.exec_module(DX)
E277 = ROOT / 'reports/E277-help-monotone'
EXTRA = {'C1': ['stl36', 'blk36', 'deflections36'], 'C2': ['stl36', 'blk36', 'deflections36'], 'C3': [], 'C4': ['stl36', 'deflections36']}


def _p(a):
    return lambda c: HERE / f'ranking-{a}-{c}.csv'


ARMS = {'C0': {'path': lambda c: E277 / f'ranking-M1-{c}.csv'}}
for _a, _ks in EXTRA.items():
    ARMS[_a] = {'path': _p(_a), 'extras': _ks, 'window': True, 'nopress': True, 'work': HERE / 'work' / _a}


def main():
    if DX.Z.sha(HERE / 'prereg.md') != (HERE / 'prereg.sha256').read_text().split()[0]:
        print('prereg sha mismatch'); return 1
    res, F = DX.compute(ARMS, 'C0', 20261281)
    for a, ks in EXTRA.items():
        ar = res['arms'][a]
        fc = ar.get('fitted_coef') or {}
        s1 = None if not ks else all(bool(fc.get(t)) and all(fc[t][k]['perSD'] > 1e-6 for k in ks) for t in DX.ORIG)
        ar['S1'] = s1
        ar['candidate'] = bool(s1 and ar['S2'] and ar['S3'])
    c = [a for a in ('C1', 'C2', 'C4') if res['arms'][a]['candidate']]
    res['adopt_candidate'] = 'C1' if 'C1' in c else (max(c, key=lambda a: res['arms'][a]['delta']['rhoDEF_epmD']) if c else None)
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    DX.show(res, ARMS, 'C0')
    print('S1', {a: res['arms'][a]['S1'] for a in EXTRA}, 'adopt', res['adopt_candidate'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
