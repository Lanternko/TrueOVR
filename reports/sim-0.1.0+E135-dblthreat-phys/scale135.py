"""E-135 scale135：legacy（E-102 merged-legacy，不重跑）對 ch1（checkpoint-ch1-60.jsonl），X 計分 60 樣本。
S、Pop、聯合 bootstrap 直接 import E-099 scale.py（不改它），格子數 30x60（同 E-102 scale240）。"""
import csv, hashlib, importlib.util, json, platform, sys, time
from pathlib import Path
import numpy as np, scipy
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
PREREG_SHA = '454e4cc4f208b8d4222772cdd68fdb99e91ef061163b0bff7c614833ac15a169'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
spec = importlib.util.spec_from_file_location('scale099', ROOT / 'reports/bias-check-E099-scale/scale.py')
SC = importlib.util.module_from_spec(spec); spec.loader.exec_module(SC)
NOPP, NSMP = 30, 60
SC.NCELL = NOPP * NSMP; SC.NSMP = NSMP
BE, BC = SC.BE, SC.BC
VERS = ['legacy', 'ch1']; ANSN = ['AB', 'BA', 'OOS']
FILES = {'legacy': ROOT / 'reports/sim-0.1.0+E102-winimp-240/merged-legacy.jsonl', 'ch1': HERE / 'checkpoint-ch1-60.jsonl'}
SIX = ['Rudy Gobert', 'Jalen Duren', 'Neemias Queta', 'Donovan Clingan', 'Mitchell Robinson', 'Scottie Barnes', 'Herbert Jones', 'Luguentz Dort']


def load(k):
    names, X = [], []
    for l in open(FILES[k], encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l); d = np.array(r['avg']['draws'], dtype=float)
        d = d[np.argsort(d[:, 0] * NSMP + d[:, 1], kind='stable')]
        assert d.shape == (NOPP * NSMP, 8) and (d[:, 1] == np.tile(np.arange(NSMP), NOPP)).all()
        names.append(r['avg']['name']); X.append(d[:, 4] - d[:, 5])
    return names, np.array(X)


def main():
    sys.stdout.reconfigure(encoding='utf-8'); T0 = time.time()
    assert sha(HERE / 'preregistration.md') == PREREG_SHA, 'preregistration changed'
    NAMES, A = load('legacy'); n2, B2 = load('ch1')
    assert sorted(NAMES) == sorted(n2) and len(NAMES) == 379, (len(NAMES), len(n2))
    idx = {n: i for i, n in enumerate(n2)}; ARR = {'legacy': A, 'ch1': B2[[idx[n] for n in NAMES]]}
    POSN = {r['name']: r['pos'] for r in csv.DictReader(open(SC.CSV['legacy'], encoding='utf-8-sig'))}
    SC.POSP = POSN
    ans = {'AB': BC.answers('B'), 'BA': BC.answers('A')}; ans['OOS'] = BE.oos_answers()[0]
    POPS = {an: SC.Pop(an, ans[an], NAMES, POSN) for an in ANSN}
    r240 = json.loads((ROOT / 'reports/sim-0.1.0+E102-winimp-240/rescore240.json').read_text(encoding='utf-8'))
    res = {'B': SC.B, 'cells': {}, 'dS': {}, 'gates': {}, 'r1': {}}
    worst = 0.0
    for an in ANSN:
        pop = POPS[an]; draws = SC.make_draws(pop); bj, pt = {}, {}
        for k in VERS:
            arr = ARR[k]; d, _ = pop.detail(arr[pop.rows].mean(1))
            bj[k] = SC.boot_S(pop, arr, draws, True); d['CI90_joint'] = SC.pct(bj[k])
            res['cells'][f'X|{an}|{k}'] = d; pt[k] = d
        worst = max(worst, abs(pt['legacy']['S'] - r240['cells'][f'X|{an}|legacy']['S']))
        dj = bj['legacy'] - bj['ch1']; ci = SC.pct(dj)
        res['dS'][f'X|{an}'] = {'diff': pt['legacy']['S'] - pt['ch1']['S'], 'CI90_joint': ci, 'excludes0': bool(ci[0] > 0 or ci[1] < 0)}
        print('rescore', an, f'{time.time() - T0:.0f}s', flush=True)
    res['selfcheckLegacySvsE102'] = worst
    o = res['dS']['X|OOS']; rl, rc = res['cells']['X|OOS|legacy']['rho'], res['cells']['X|OOS|ch1']['rho']
    res['gates'] = {'b1': {'CI90_joint': o['CI90_joint'], 'pass': bool(o['CI90_joint'][0] > 0)},
                    'b3': {'rhoLegacy': rl, 'rhoCh1': rc, 'pass': bool(rc >= rl - 0.02)}}
    res['gates']['adopt_to_G5'] = res['gates']['b1']['pass'] and res['gates']['b3']['pass']
    # r1：全體 379 人名次（X 平均，大者第 1）與 OOS 人群名次
    for k in VERS:
        s = ARR[k].mean(1); rk = rankdata(-s, method='min')
        po = POPS['OOS']; so = s[po.rows]; ro = rankdata(-so, method='min')
        res['r1'][k] = {n: {'all379': int(rk[NAMES.index(n)]), 'oos287': int(ro[po.names.index(n)]) if n in po.names else None} for n in SIX}
        res['r1'][k]['top20C_all379'] = int(sum(POSN[NAMES[i]] == 'C' for i in np.argsort(-s)[:20]))
    res['r1']['oosAnswerRank'] = {n: int(po.ra[po.names.index(n)]) for n in SIX if n in po.names}
    res['spearmanLegacyVsCh1'] = float(scipy.stats.spearmanr(ARR['legacy'].mean(1), ARR['ch1'].mean(1))[0])
    (HERE / 'rescore135.json').write_text(json.dumps(SC.jd(res), ensure_ascii=False, indent=1), encoding='utf-8')
    meta = {'preregSha256': PREREG_SHA, 'inputs': {k: sha(p) for k, p in FILES.items()},
            'scale099Sha256': sha(ROOT / 'reports/bias-check-E099-scale/scale.py'),
            'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__, 'seconds': time.time() - T0}
    old = json.loads((HERE / 'run-meta.json').read_text(encoding='utf-8')) if (HERE / 'run-meta.json').exists() else {}
    old['analysis'] = meta; (HERE / 'run-meta.json').write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(res['gates'], ensure_ascii=False), 'selfcheck', worst)
    print(json.dumps(res['dS'], ensure_ascii=False))


if __name__ == '__main__':
    main()
