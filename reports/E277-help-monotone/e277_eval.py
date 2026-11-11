"""E-277 評估（prereg.md，sha 見 prereg.sha256）。A0／A1 用 E-269 的 ranking，M1–M3 用本目錄 e277_build.py 產的 ranking。
用法（repo root）：python -I -B -X utf8 reports/E277-help-monotone/e277_eval.py"""
import csv, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E269 = ROOT / 'reports/E269-def-coef-pooling'


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


X = mod('e269e', E269 / 'e269_eval.py')
Q, V, P, sp = X.Q, X.V, X.P, X.sp
ARMS = ['A0', 'A1', 'M1', 'M2', 'M3']
ORIG, FULL, NEXT = X.ORIG, X.FULL, X.NEXT
SEED, B = 20261277, 2000
POS = ['PG', 'SG', 'SF', 'PF', 'C']
NAMED = ['Kevin Durant', 'Fred VanVleet', 'Victor Wembanyama', 'Rudy Gobert', 'Anthony Davis', 'Bam Adebayo', 'Jarrett Allen',
         'Alex Caruso', 'Stephen Curry', 'Amen Thompson', 'Trae Young']
EPMDIR = Q.EPMDIR


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def epm_d(ids, s):
    _, mp = P.pop_of(s)
    v = {}
    for r in csv.DictReader(open(EPMDIR / f'epm_{s}.csv', encoding='utf-8-sig')):
        p = int(r['playerId'])
        if float(r['stintPoss']) >= 1000 and p in mp:
            v[p] = float(r['D']) * P.wfun(mp[p])
    return np.array([v.get(p, np.nan) for p in ids])


def t_def(ids, t):
    w = json.loads((ROOT / f'reports/E274-def-display-transformer/d2-{t}.json').read_text(encoding='utf-8'))['oppPts100']
    return np.array([-w[str(p)] if str(p) in w else np.nan for p in ids])


def r2(x, y):
    k = np.isfinite(x) & np.isfinite(y)
    return float(np.corrcoef(x[k], y[k])[0, 1] ** 2)


def rho(x, y):
    k = np.isfinite(x) & np.isfinite(y)
    return float(sp(x[k], y[k])), int(k.sum())


def main():
    if sha(HERE / 'prereg.md') != (HERE / 'prereg.sha256').read_text().split()[0]:
        print('prereg sha mismatch'); return 1
    for a in ('A0', 'A1'):
        for t in ORIG:
            shutil.copy(E269 / f'ranking-{a}-{t}.csv', HERE / f'ranking-{a}-{t}.csv')
    X.HERE = HERE
    chk = {}
    for s in ['2023-24', '2024-25', '2025-26']:
        j = json.loads((X.E.E126 / f'rapm-{s}.json').read_text(encoding='utf-8'))['players']
        v = [x for x in j.values() if x['poss'] >= 1000]
        net, o, dd = (np.array([x[k] for x in v]) for k in ('net', 'O', 'D'))
        chk[s] = float(np.corrcoef(net, o + dd)[0, 1]) > float(np.corrcoef(net, o - dd)[0, 1])
    sign = 1.0 if all(chk.values()) else -1.0
    D = {a: {c: X.load(a, c) for c in ORIG} for a in ARMS}
    for c in ORIG:
        for a in ARMS[1:]:
            assert D[a][c]['ids'] == D['A0'][c]['ids'], 'population differs'
    ids = {c: D['A0'][c]['ids'] for c in ORIG}
    Y = {c: Q.target(ids[c], NEXT[c], 'epm') for c in FULL}
    YR = {c: Q.target(ids[c], NEXT[c], 'rapm') for c in FULL}
    YE = {c: epm_d(ids[c], NEXT[c]) for c in FULL}
    YD = {c: sign * X.drapm(ids[c], NEXT[c]) for c in FULL}
    YT = {c: t_def(ids[c], c) for c in FULL}
    Y['2025-26'] = V.live_targets(ids['2025-26'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in ORIG}
    nf = sum(n[c] for c in FULL)
    w = {c: n[c] / nf for c in FULL}

    def fold(a, c):
        d = D[a][c]
        out = {'R2': r2(d['ovr'], Y[c])}
        if c in FULL:
            out['rhoDEF_epmD'], out['n_epmD'] = rho(d['def'], YE[c])
            out['rhoDEF_T'], out['n_T'] = rho(d['def'], YT[c])
            out['rhoDEF_rapmD'], out['n_rapmD'] = rho(d['def'], YD[c])
            out['R2_rapm'] = r2(d['ovr'], YR[c])
        return out

    F = {a: {c: fold(a, c) for c in ORIG} for a in ARMS}
    rng = np.random.default_rng(SEED)
    idx = {c: np.where(np.isfinite(Y[c]))[0] for c in FULL}
    draws = [{c: rng.choice(idx[c], len(idx[c])) for c in FULL} for _ in range(B)]
    base_bs = [sum(w[c] * r2(D['A0'][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) for dr in draws]
    res = {'sign': sign, 'n_primary': n, 'arms': {}}
    keys = ('R2', 'rhoDEF_epmD', 'rhoDEF_T', 'rhoDEF_rapmD', 'R2_rapm')
    for a in ARMS:
        hs = {c: {ps: D[a][c]['coef'][ps]['help'] * 10 for ps in POS} for c in ORIG}
        s1 = all(all(hs[c][POS[i]] <= hs[c][POS[i + 1]] + 1e-6 for i in range(4)) and hs[c]['C'] > hs[c]['PG'] + 1e-6 for c in ORIG)
        comb = {k: float(sum(w[c] * F[a][c][k] for c in FULL)) for k in keys}
        res['arms'][a] = {'folds': F[a], 'combined': comb, 'help_per10': hs, 'S1': bool(s1)}
    A0 = res['arms']['A0']
    for a in ARMS[1:]:
        ar = res['arms'][a]
        dd = {k: ar['combined'][k] - A0['combined'][k] for k in keys}
        per = {c: {k: F[a][c][k] - F['A0'][c][k] for k in F[a][c] if not k.startswith('n_')} for c in ORIG}
        bs = [sum(w[c] * r2(D[a][c]['ovr'][dr[c]], Y[c][dr[c]]) for c in FULL) - b0 for dr, b0 in zip(draws, base_bs)]
        s2 = dd['R2'] >= -0.005 and all(per[c]['R2'] >= -0.010 for c in FULL)
        s3 = dd['rhoDEF_epmD'] >= -0.010
        ar.update(delta=dd, delta_fold=per, ci90_dR2=[float(np.percentile(bs, 5)), float(np.percentile(bs, 95))],
                  gates={'S1': ar['S1'], 'S2': bool(s2), 'S3': bool(s3)}, candidate=bool(ar['S1'] and s2 and s3),
                  vs_A0={c: {'n_ovr_diff>=3': int((np.abs(D[a][c]['ovr'] - D['A0'][c]['ovr']) >= 3).sum()),
                             'max_abs_ovr_diff': float(np.abs(D[a][c]['ovr'] - D['A0'][c]['ovr']).max())} for c in ORIG})
    cands = [a for a in ('M1', 'M2', 'M3') if res['arms'][a]['candidate']]
    res['adopt_candidate'] = 'M1' if 'M1' in cands else (max(cands, key=lambda a: res['arms'][a]['delta']['rhoDEF_epmD']) if cands else None)
    res['examples'] = {}
    for c in ['2024-25', '2025-26']:
        d0 = D['A0'][c]
        bigs = [nm for nm, p, o in sorted(zip(d0['all_names'], d0['all_pos'], d0['all_ovr']), key=lambda t: -t[2]) if p == 'C'][:10]
        show = NAMED + [b for b in bigs if b not in NAMED]
        ex = {}
        for a in ARMS:
            d = D[a][c]
            v = d['all_def']; o = d['all_ovr']; nm = d['all_names']
            ex[a] = {s: ({'def': round(float(v[nm.index(s)]), 3), 'def_rank': int((v > v[nm.index(s)]).sum() + 1),
                          'ovr': round(float(o[nm.index(s)]), 2), 'ovr_rank': int((o > o[nm.index(s)]).sum() + 1)} if s in nm else None) for s in show}
        res['examples'][c] = {'n_pop': len(d0['all_names']), 'bigs': bigs, 'by_arm': ex}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print('A0 combined', {k: round(v, 4) for k, v in A0['combined'].items()}, 'S1', A0['S1'])
    for a in ARMS[1:]:
        ar = res['arms'][a]
        print(f"== {a} cand={ar['candidate']} gates={ar['gates']} ci90={[round(x, 4) for x in ar['ci90_dR2']]}")
        print('   d', {k: round(v, 4) for k, v in ar['delta'].items()})
        for c in ORIG:
            print('   ', c, {k: round(v, 4) for k, v in ar['delta_fold'][c].items()}, ar['vs_A0'][c])
    for a in ARMS:
        print('help/10', a, {c: [round(res['arms'][a]['help_per10'][c][p], 3) for p in POS] for c in ORIG})
    for c in res['examples']:
        print('--', c, 'n', res['examples'][c]['n_pop'])
        for s in NAMED + res['examples'][c]['bigs'][:6]:
            print('  ', s, {a: (x['def_rank'], x['ovr_rank']) if (x := res['examples'][c]['by_arm'][a][s]) else None for a in ARMS})
    print('adopt_candidate', res['adopt_candidate'])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
