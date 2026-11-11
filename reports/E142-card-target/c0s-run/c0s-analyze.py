"""E-142 c0s: two different-seed 60-sample WinImp groups (sim 0.1.1, X scoring) -> player-rank Spearman and S 90% joint-bootstrap interval width.
Reuses E-099 scale.py / E-102 scale240.py machinery unchanged. Only the two groups' mutual consistency and the S interval width are used;
no comparison to cards, candidate targets, salary or 2K. (S needs the E-099 RAPM answer halves, as in E-102; only the interval WIDTH is judged.)
usage: python c0s-analyze.py grpA.jsonl grpB.jsonl out.json seedA seedB"""
import importlib.util, json, sys, csv, hashlib, platform
from pathlib import Path
import numpy as np, scipy
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('scale099', ROOT / 'reports/bias-check-E099-scale/scale.py')
SC = importlib.util.module_from_spec(spec); spec.loader.exec_module(SC)
NOPP, NSMP = 30, 60
SC.NCELL = NOPP * NSMP; SC.NSMP = NSMP
BE, BC = SC.BE, SC.BC
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def load(p):
    d = {}
    for l in open(p, encoding='utf-8'):
        r = json.loads(l)['avg']; a = np.array(r['draws'], dtype=float); assert a.shape == (NOPP * NSMP, 8)
        d[r['name']] = a[:, 4] - a[:, 5]          # X = luck-corrected margin, candidate - control
    return d
pa, pb, out, sa, sb = sys.argv[1:6]
A, B = load(pa), load(pb); assert set(A) == set(B) and len(A) == 379, (len(A), len(B))
NAMES = sorted(A); AA = np.array([A[n] for n in NAMES]); BB = np.array([B[n] for n in NAMES])
POSN = {r['name']: r['pos'] for r in csv.DictReader(open(SC.CSV['legacy'], encoding='utf-8-sig'))}; SC.POSP = POSN
ans = {'AB': BC.answers('B'), 'BA': BC.answers('A')}; ans['OOS'] = BE.oos_answers()[0]
res = {'n_players': len(NAMES), 'samples_per_group': NSMP, 'opponents': NOPP, 'seeds': {'A': int(sa), 'B': int(sb)}, 'scoring': 'X'}
mA, mB = AA.mean(1), BB.mean(1)
res['spearman_all379'] = float(spearmanr(mA, mB)[0])
res['spearman_half_noise_ref'] = None
res['S'] = {}
for an in ['AB', 'BA', 'OOS']:
    pop = SC.Pop(an, ans[an], NAMES, POSN); draws = SC.make_draws(pop); cell = {'n_pop': pop.n, 'n_centers': len(pop.c), 'n_guards': len(pop.g)}
    res['spearman_popcut_' + an] = float(spearmanr(mA[pop.rows], mB[pop.rows])[0])
    for g, arr in (('A', AA), ('B', BB)):
        d, _ = pop.detail(arr[pop.rows].mean(1)); bj = SC.boot_S(pop, arr, draws, True); ci = SC.pct(bj)
        cell[g] = {'S': d['S'], 'CI90_joint': [float(ci[0]), float(ci[1])], 'width': float(ci[1] - ci[0])}
    res['S'][an] = cell
w = [res['S'][an][g]['width'] for an in res['S'] for g in 'AB']
res['S_width_max'] = max(w)
res['pass'] = {'spearman_ge_0.90': res['spearman_all379'] >= 0.90, 'S_width_le_30_all': max(w) <= 30.0}
res['pass']['c0s'] = bool(all(res['pass'].values()))
res['meta'] = {'scale099Sha256': sha(ROOT / 'reports/bias-check-E099-scale/scale.py'), 'grpA_sha256': sha(pa), 'grpB_sha256': sha(pb),
               'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__}
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float); print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
