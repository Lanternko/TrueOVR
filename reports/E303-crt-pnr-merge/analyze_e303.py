"""E-303 本機判定：cross_test MSE（主）、M2（沒弄壞）、M1／test（只報告）、代表球員合成分數。
用法：python -I -B -X utf8 reports/E303-crt-pnr-merge/analyze_e303.py（out-*.json 先從 5090 拉回本目錄）"""
import hashlib, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/E255-pnr-handler-lineup-tf'))
import analyze_e255 as A  # noqa: E402  （P_JSON＝E-255 json；E-179 欄位與 G50 相同）

SRC = {'BOTH': ROOT / 'reports/E258-pnr-lowvol-gate/G50/out-W05.json', 'NOPNR': ROOT / 'reports/E255-pnr-handler-lineup-tf/out-T0.json'}
NEW = ['NOCRT', 'MRG3', 'MRG5', 'MRG7']
CANDS = ['NOPNR', 'NOCRT', 'MRG3', 'MRG5', 'MRG7']
ARMS = ['BOTH'] + CANDS


def main():
    pre_ok = hashlib.sha256((HERE / 'preregistration.md').read_bytes()).hexdigest() == (HERE / 'preregistration.sha256').read_text().strip()
    outs = {a: json.loads(SRC[a].read_text(encoding='utf-8')) for a in SRC}
    outs.update({a: json.loads((HERE / f'out-{a}.json').read_text(encoding='utf-8')) for a in NEW})
    y = {s: np.array(A.P_JSON['e179'][s]['O']) for s in A.E179_SEAS}
    m2 = {a: round(A.r2_pooled(y, A.ridge_cv_preds(A.make_m2(outs[a]['e179']), y))[0], 5) for a in ARMS}
    m1 = {a: round(A.r2_pooled(y, A.ridge_cv_preds(A.make_m1(outs[a]['e179']), y))[0], 5) for a in ARMS}
    G = outs['BOTH']['cross_test']['games']
    rng = np.random.default_rng(20261303)
    draws = np.stack([np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(2000)]).astype(float)
    sig = float(np.std(outs['BOTH']['cross_test']['seed_pts100_mse'], ddof=1))
    cross = {a: outs[a]['cross_test']['pts100_mse'] for a in ARMS}
    gate = {}
    for a in CANDS:
        d = A.paired_game_bs(outs[a], outs['BOTH'], 'cross_test', 'pts', draws)
        gate[a] = {'cross_diff': d, 'c1': d['point'] <= 2 * sig, 'm2_diff': round(m2[a] - m2['BOTH'], 5), 'c2': m2[a] - m2['BOTH'] >= -0.005}
    ok = [a for a in CANDS if gate[a]['c1'] and gate[a]['c2']]
    pick = None
    if ok:
        best = min(ok, key=lambda a: cross[a])
        mrg = [a for a in ok if a.startswith('MRG')]
        pick = best
        if not best.startswith('MRG') and mrg:
            bm = min(mrg, key=lambda a: cross[a])
            if cross[bm] - cross[best] <= sig:
                pick = bm
    res = {'prereg_sha256_ok': pre_ok, 'sigma_seed_BOTH': round(sig, 4), 'cross_test': cross,
           'test_pts': {a: outs[a]['test']['pts100_mse'] for a in ARMS}, 'test_net': {a: outs[a]['test']['net_mse'] for a in ARMS},
           'cross_net': {a: outs[a]['cross_test']['net_mse'] for a in ARMS},
           'seed_std_cross': {a: round(float(np.std(outs[a]['cross_test']['seed_pts100_mse'], ddof=1)), 4) for a in ARMS},
           'M2': m2, 'M1': m1, 'gate': gate, 'pass': ok, 'pick': pick}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in res.items() if k != 'gate'}, ensure_ascii=False, indent=1))
    for a in CANDS:
        print(a, gate[a])


if __name__ == '__main__':
    main()
