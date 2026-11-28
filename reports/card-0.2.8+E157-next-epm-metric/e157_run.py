"""E-157 執行：c0 → 0.2.7d(K0) vs 0.2.8(K6) 的 v2 口徑 → 診斷。seed 20261101（沿用 E-153，預註冊未另訂）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.8+E157-next-epm-metric/e157_run.py"""
import json, pickle, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eval_v2 as V
P, ROOT = V.P, V.ROOT
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
SEED = 20261101


def rpath(arm, t):
    W = E153 / 'work'
    if t == '2025-26':
        return W / ('K0' if arm == 'K0' else 'K6-2025-26') / 'c0/ranking.csv'
    return W / (f'K0h-{t}' if arm == 'K0' else f'K6-{t}') / t / 'out/K0/ranking.csv'


def main():
    arms = {a: {t: rpath(a, t) for t in V.SEASONS} for a in ('K0', 'K6')}
    D = V.load(arms)
    # c0：關掉 EPM 項（ref_old），C 對 E-153 results.json 到 1e-9
    ref = json.loads((E153 / 'results.json').read_text(encoding='utf-8'))['per_season']
    ps_old = V.per_season(D, 'old')
    c0, ok = {}, True
    for t in V.SEASONS:
        for a in ('K0', 'K6'):
            d = abs(ps_old[t][a]['C'] - ref[t][a]['C'])
            nn = ps_old[t][a]['n'] == ref[t][a]['n']
            c0[f'{a}-{t}'] = {'C_v2off': ps_old[t][a]['C'], 'C_e153': ref[t][a]['C'], 'absdiff': d, 'n_same': nn}
            ok &= (d < 1e-9) and nn
    print('c0', 'PASS' if ok else 'FAIL', json.dumps(c0))
    if not ok:
        (HERE / 'results.json').write_text(json.dumps({'c0': c0, 'c0_pass': False}, indent=1), encoding='utf-8')
        sys.exit(2)
    ps = V.per_season(D, 'v2')
    bt = V.boot(D, 'K6', 'K0', V.JUDGE, SEED, 'v2')
    od, j = V.judge(ps, bt, 'K6', 'K0')
    lvl = {a: {k: V.pooled_level(ps, a, V.JUDGE, k) for k in ('C',) + V.KEYS} for a in ('K0', 'K6')}
    # 診斷（W 加權後的 raw 值，與指標同口徑；人群＝該季 MIN>=500 pop 中兩者皆有者）
    base = V._base()
    diag = {}
    for t in V.SEASONS[:3]:
        raw = base[t]['raw']
        t6 = pickle.load(open(ROOT / f'reports/E142-card-target/phase1-work/cands/T6-{t}.pkl', 'rb'))
        def sp(x, y):
            ids = [p for p in x if p in y]
            return {'n': len(ids), 'rho': P.spearman([x[p] for p in ids], [y[p] for p in ids])}
        t6n = {p: v[0] for p, v in t6.items()}
        diag[t] = {'epm_vs_rapm': sp(raw['epm'], raw['rapm']), 'epm_vs_T6': sp(raw['epm'], t6n), 'rapm_vs_T6': sp(raw['rapm'], t6n)}
    nn = {t: sum(ps[t]['K0']['n'] for _ in [0]) for t in V.SEASONS}
    pooled_diff = {k: V.pooled(ps, 'K6', 'K0', V.JUDGE, k) for k in ('C',) + V.KEYS}
    res = {'seed': SEED, 'draws': V.B, 'c0': c0, 'c0_pass': True, 'weights_v2': {'sal': 0.4, 'twok': 0.3, 'rapm': 0.15, 'epm': 0.15},
           'per_season_v2': ps, 'per_season_old': ps_old, 'pooled_level_v2': lvl, 'pooled_diff_K6_minus_K0': pooled_diff,
           'bootstrap': bt, 'judgement': j, 'diagnostics': diag, 'sha256': D['sha'],
           'epm_files': {t: P.sha(str(V.EPMDIR / f'epm_{P.NEXT[t]}.csv')) for t in V.SEASONS[:3]}, 'twok_sha256': P.sha(str(V.TWOK))}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({'level': lvl, 'diff': pooled_diff, 'boot': bt, 'judge': j, 'diag': diag}, ensure_ascii=False, indent=1))
    for t in V.SEASONS:
        print(t, json.dumps({a: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ps[t][a].items()} for a in ps[t]}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
