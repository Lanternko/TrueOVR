"""E-282 評估（prereg.md 凍結）。用法（repo root）：python -I -B -X utf8 reports/E282-stl-weight/e282_eval.py"""
import importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_s = importlib.util.spec_from_file_location('dx_eval', ROOT / 'reports/E280-blk-weight/dx_eval.py')
DX = importlib.util.module_from_spec(_s); sys.modules['dx_eval'] = DX; _s.loader.exec_module(DX)
E280 = ROOT / 'reports/E280-blk-weight'
GRID = {'L1': 0.1, 'L2': 0.2, 'L3': 0.3, 'L4': 0.4, 'L5': 0.5, 'L6': 0.6}


def _p(a):
    return lambda c: HERE / f'ranking-{a}-{c}.csv'


ARMS = {'L0': {'path': lambda c: E280 / f'ranking-K3-{c}.csv', 'extras': ['blk36'], 'window': True}}
for _a in list(GRID) + ['LW']:
    ARMS[_a] = {'path': _p(_a), 'extras': ['blk36', 'stl36'], 'window': True, 'work': HERE / 'work' / _a}


def pick(res, folds, F):
    """S2 過的 L1–L6 裡取 Δρ（EPM 防守，按 folds 人數加權）最高；與最高差 ≤0.003 取較小權重。"""
    w = {c: res['n_primary'][c] for c in folds}
    tot = sum(w.values())
    sc = {}
    for a in GRID:
        d = {c: F[a][c]['R2'] - F['L0'][c]['R2'] for c in folds}
        if sum(w[c] * d[c] for c in folds) / tot < -0.005 or min(d.values()) < -0.010:
            continue
        sc[a] = sum(w[c] * (F[a][c]['rhoDEF_epmD'] - F['L0'][c]['rhoDEF_epmD']) for c in folds) / tot
    if not sc:
        return None, sc
    best = max(sc.values())
    return min((a for a in sc if sc[a] >= best - 0.003), key=lambda a: GRID[a]), sc


def main():
    if DX.Z.sha(HERE / 'prereg.md') != (HERE / 'prereg.sha256').read_text().split()[0]:
        print('prereg sha mismatch'); return 1
    res, F = DX.compute(ARMS, 'L0', 20261282)
    choice, scores = pick(res, DX.FULL, F)
    lofo = {}
    for out in DX.FULL:
        ch, _ = pick(res, [c for c in DX.FULL if c != out], F)
        lofo[out] = {'picked': ch, 'w': GRID.get(ch),
                     'heldout_dRhoEPMD': None if ch is None else F[ch][out]['rhoDEF_epmD'] - F['L0'][out]['rhoDEF_epmD'],
                     'heldout_dR2': None if ch is None else F[ch][out]['R2'] - F['L0'][out]['R2']}
    kw = res['arms']['LW']['fitted_coef']
    res.update(choice=choice, choice_w=GRID.get(choice), choice_scores=scores, lofo=lofo,
               lofo_holds=all(v['heldout_dRhoEPMD'] is not None and v['heldout_dRhoEPMD'] > 0 for v in lofo.values()),
               LW_stable=all(bool(kw[t]) and kw[t]['stl36']['perSD'] > 1e-6 for t in DX.ORIG))
    if choice:
        res['choice_dRhoT'] = res['arms'][choice]['delta']['rhoDEF_T']
        res['choice_T_sidefx'] = res['choice_dRhoT'] < -0.010
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    DX.show(res, ARMS, 'L0')
    print('choice', choice, GRID.get(choice), {k: round(v, 4) for k, v in scores.items()})
    print('lofo', lofo, 'holds', res['lofo_holds'], 'LW_stable', res['LW_stable'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
