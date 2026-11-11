"""E-288 評估：預註冊 preregistration.md（凍結 sha 見 preregistration.sha256）。
中鋒被低估？不靠出手的長人貢獻（掩護助攻、兩分干擾、卡位）加分，四季輪流挑 λ。
用法（repo root）：python -I -B -X utf8 reports/E288-center-underrated/e288_eval.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


V = mod('e267', 'reports/E267-usage-penalty/e267_eval.py')
X, Q, M = V.X, V.Q, V.M
pct, sp = M.pct, M.sp
FOLDS = ['2022-23', '2023-24', '2024-25', '2025-26']
NEXT = {'2022-23': '2023-24', '2023-24': '2024-25', '2024-25': '2025-26'}
FULL = FOLDS[:3]
GRID = [0, .05, .1, .2, .3, .5, .75, 1.0]
SEED, B, N_SHUF = 20261288, 2000, 300
CAND = ['ROLE', 'ROLE_BIG', 'SCR', 'CON', 'BOX']
ARMS = CAND + ['CPOS', 'HGT']
TOP_BIGS_OK = {'Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren'}
SHOW = ['Steven Adams', 'Myles Turner', 'Ivica Zubac', 'Jakob Poeltl', 'Isaiah Hartenstein', 'Rudy Gobert', 'Jarrett Allen',
        'Nikola Jokić', 'Victor Wembanyama', 'Domantas Sabonis', 'Alperen Sengun', 'Bam Adebayo']
CARD = ROOT / 'reports/card-0.2.9+E164-no-stamina'
LIVEF = ROOT / 'reports/impact-epm-2026-27/epm-live.csv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hustle_path(t):
    return ROOT / ('data/tracking-cells/2025-26/hustle-2025-26.json' if t == '2025-26' else f'reports/E239-tracking-full/data/hustle-{t}.json')


def zc(v):
    return (v - v.mean()) / v.std()


def build(t):
    d = X.load(t)
    n = len(d['ids'])
    js = json.loads(hustle_path(t).read_text(encoding='utf-8'))
    H = {}
    for r in js['rowSet']:
        r = dict(zip(js['headers'], r))
        a = H.setdefault(int(r['PLAYER_ID']), {'MIN': 0, 'SCR': 0, 'CON2': 0, 'BOX': 0})
        a['MIN'] += r['MIN'] or 0; a['SCR'] += r['SCREEN_ASSISTS'] or 0
        a['CON2'] += r['CONTESTED_SHOTS_2PT'] or 0; a['BOX'] += r['BOX_OUTS'] or 0
    feats, have = {}, np.zeros(n, bool)
    for k in ('SCR', 'CON2', 'BOX'):
        v = np.zeros(n)
        for i, p in enumerate(d['ids']):
            h = H.get(int(p))
            if h and h['MIN'] >= 200:
                v[i] = h[k] / h['MIN'] * 36; have[i] = True
        z = np.zeros(n); z[have] = zc(v[have])
        feats[k] = z   # 缺資料＝0（不加分）
    card = {r['name']: r for r in csv.DictReader(open(CARD / f'ranking-S-{t}.csv', encoding='utf-8-sig'))}
    hgt = np.array([float(card[nm]['heightInches']) for nm in d['names']])
    pos = d['pos']
    role = np.clip((feats['SCR'] + feats['CON2'] + feats['BOX']) / 3, 0, 1.5)
    raw = {'ROLE': role, 'ROLE_BIG': role * np.isin(pos, ['PF', 'C']),
           'SCR': np.clip(feats['SCR'], 0, 1.5), 'CON': np.clip(feats['CON2'], 0, 1.5), 'BOX': np.clip(feats['BOX'], 0, 1.5),
           'HGT': np.clip(zc(hgt), 0, 1.5)}
    cpos = (pos == 'C').astype(float)
    ref = np.sqrt((cpos ** 2).mean())
    P = {k: (v * ref / np.sqrt((v ** 2).mean()) if (v ** 2).mean() > 0 else v) for k, v in raw.items()}
    P['CPOS'] = cpos
    d['P'], d['P_ref'], d['role_raw'] = P, ref, role
    d['sd'] = float(d['ovr'].std())
    d['hustle_cover'] = float(have.mean())
    return d


def adj(d, P, lam):
    return d['ovr'] + lam * d['sd'] * P


def gap(d, y, o, posv):
    k = np.isfinite(y)
    e = pct(y[k]) - pct(o[k])
    m = d['pos'][k] == posv
    return e[m]


def main():
    if sha(HERE / 'preregistration.md') != (HERE / 'preregistration.sha256').read_text().strip():
        print('prereg sha mismatch'); return
    D = {c: build(c) for c in FOLDS}
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}
    Y['2025-26'] = V.live_targets(D['2025-26']['ids'])['epm']
    YR = {c: Q.target(D[c]['ids'], NEXT[c], 'rapm') for c in FULL}
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}
    w = {t: n[t] / sum(n.values()) for t in FOLDS}
    w3 = {t: n[t] / sum(n[c] for c in FULL) for t in FULL}
    rng = np.random.default_rng(SEED)
    res = {'prereg_sha256': sha(HERE / 'preregistration.md'), 'live_epm_sha256': sha(LIVEF), 'n': n,
           'hustle_cover': {c: D[c]['hustle_cover'] for c in FOLDS}, 'arms': {}}

    # 基準中鋒／PF 缺口（四折合併）
    base_gap = {}
    for pv in ('PG', 'SG', 'SF', 'PF', 'C'):
        g = np.concatenate([gap(D[c], Y[c], D[c]['ovr'], pv) for c in FOLDS])
        base_gap[pv] = float(g.mean())
    base_gap_fold = {c: float(gap(D[c], Y[c], D[c]['ovr'], 'C').mean()) for c in FOLDS}
    res['base_gap'] = base_gap; res['base_gap_C_fold'] = base_gap_fold
    print('base gap (pct(y)-pct(ovr), + = OVR 低估):', {k: round(v, 3) for k, v in base_gap.items()}, base_gap_fold)

    boot_idx = [{t: rng.choice(np.where(np.isfinite(Y[t]))[0], n[t]) for t in FOLDS} for _ in range(B)]

    def run_arm(Pmap, keep_bs=True):
        rho = {c: {l: float(Q.metrics(D[c], Y[c], adj(D[c], Pmap[c], l))['all']) for l in GRID} for c in FOLDS}
        f4 = {}
        for t in FOLDS:
            lam = max(GRID, key=lambda l: np.mean([rho[c][l] for c in FOLDS if c != t]))
            m0, m1 = Q.metrics(D[t], Y[t], D[t]['ovr']), Q.metrics(D[t], Y[t], adj(D[t], Pmap[t], lam))
            f4[t] = {'lambda': lam, 'all': float(m1['all'] - m0['all']), 'G': float(m1['G'] - m0['G']), 'F': float(m1['F'] - m0['F'])}
        mall = float(sum(w[t] * f4[t]['all'] for t in FOLDS))
        out = {'folds': f4, 'mean_all': mall, 'rho_grid': {t: {str(l): v for l, v in rho[t].items()} for t in FOLDS}}
        if not keep_bs:
            return out
        bs = []
        for bm in boot_idx:
            v = 0.0
            for t in FOLDS:
                r = bm[t]
                v += w[t] * (Q.metrics(D[t], Y[t], adj(D[t], Pmap[t], f4[t]['lambda']), r)['all'] - Q.metrics(D[t], Y[t], D[t]['ovr'], r)['all'])
            bs.append(v)
        out['_bs'] = np.array(bs)
        out['ci90'] = [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]
        out['n_pos'] = int(sum(f4[t]['all'] > 0 for t in FOLDS))
        out['mean_G'] = float(sum(w[t] * f4[t]['G'] for t in FOLDS))
        out['mean_F'] = float(sum(w[t] * f4[t]['F'] for t in FOLDS))
        g1 = {pv: float(np.concatenate([gap(D[t], Y[t], adj(D[t], Pmap[t], f4[t]['lambda']), pv) for t in FOLDS]).mean())
              for pv in ('PG', 'SG', 'SF', 'PF', 'C')}
        out['gap_after'] = g1
        out['rapm'] = {t: float(Q.metrics(D[t], YR[t], adj(D[t], Pmap[t], f4[t]['lambda']))['all'] - Q.metrics(D[t], YR[t], D[t]['ovr'])['all']) for t in FULL}
        out['mean_rapm'] = float(sum(w3[t] * out['rapm'][t] for t in FULL))
        out['lambda_star'] = max(GRID, key=lambda l: np.mean([rho[c][l] for c in FOLDS]))
        return out

    def ranks_2526(Pv, lam):
        d = D['2025-26']
        o0, o1 = d['ovr'], adj(d, Pv, lam)
        r0 = (-o0).argsort().argsort() + 1; r1 = (-o1).argsort().argsort() + 1
        nm = d['names']
        top10 = [nm[i] for i in np.argsort(-o1)[:10]]
        top10_0 = [nm[i] for i in np.argsort(-o0)[:10]]
        new_bigs = [x for i, x in enumerate(nm) if x in top10 and x not in top10_0 and d['pos'][i] in ('PF', 'C') and x not in TOP_BIGS_OK]
        drops = [nm[i] for i in range(len(nm)) if r0[i] <= 30 and r1[i] - r0[i] > 10]
        show = {x: [int(r0[nm.index(x)]), int(r1[nm.index(x)])] for x in SHOW if x in nm}
        return {'top10': top10, 'r001_new_bigs': new_bigs, 'top30_drops': drops, 'show': show,
                'gate4': bool(not new_bigs and len(drops) <= 1)}

    for arm in ARMS:
        Pmap = {c: D[c]['P'][arm] for c in FOLDS}
        r = run_arm(Pmap)
        lam_s = r['lambda_star']
        r['rank_2025_26'] = ranks_2526(D['2025-26']['P'][arm], lam_s)
        r['rank_2025_26_lam02'] = ranks_2526(D['2025-26']['P'][arm], .2)
        res['arms'][arm] = r

    bsC = res['arms']['CPOS']['_bs']
    for arm in ARMS:
        r = res['arms'][arm]
        diff = r['_bs'] - bsC
        r['diff_vs_CPOS'] = {'mean': float(r['mean_all'] - res['arms']['CPOS']['mean_all']),
                             'ci90': [float(np.percentile(diff, 5)), float(np.percentile(diff, 95))]}
        if arm in CAND:
            c1 = r['mean_all'] >= .005 and r['ci90'][0] > -.005
            c2 = r['n_pos'] >= 3
            if base_gap['C'] > 0:
                c3 = r['gap_after']['C'] <= base_gap['C'] / 2 and r['mean_G'] >= -.01
            else:
                c3 = None
            c4 = r['rank_2025_26']['gate4']
            if base_gap['C'] <= 0:
                verdict = 'adopt_candidate' if (c1 and c2 and c4) else 'reject'
            elif c1 and c2 and c3 and c4:
                verdict = 'adopt_candidate'
            elif c3 and c4 and r['mean_all'] >= -.003 and r['ci90'][0] > -.01:
                verdict = 'structural_partial'
            else:
                verdict = 'reject'
            r['checks'] = [bool(c1), bool(c2), c3 if c3 is None else bool(c3), bool(c4)]
            r['verdict'] = verdict
        else:
            r['verdict'] = 'control'
        del r['_bs']
        print(f"== {arm:8s} {r['verdict']:18s} Δall={r['mean_all']:+.4f} [{r['ci90'][0]:+.4f},{r['ci90'][1]:+.4f}] pos={r['n_pos']}/4 "
              f"ΔG={r['mean_G']:+.4f} ΔRAPM={r['mean_rapm']:+.4f} λ={[r['folds'][t]['lambda'] for t in FOLDS]} λ*={r['lambda_star']} "
              f"gapC {base_gap['C']:+.3f}->{r['gap_after']['C']:+.3f} gapPF {base_gap['PF']:+.3f}->{r['gap_after']['PF']:+.3f} vsCPOS {r['diff_vs_CPOS']['mean']:+.4f}")
        print('   ', r['rank_2025_26']['show'], 'newBigsTop10=', r['rank_2025_26']['r001_new_bigs'], 'drops=', r['rank_2025_26']['top30_drops'])

    shuf = []
    for _ in range(N_SHUF):
        Pm = {}
        for c in FOLDS:
            v = rng.permutation(D[c]['role_raw'])
            Pm[c] = v * D[c]['P_ref'] / np.sqrt((v ** 2).mean())
        shuf.append(run_arm(Pm, keep_bs=False)['mean_all'])
    res['shuf_control'] = {'mean': float(np.mean(shuf)), 'p95': float(np.percentile(shuf, 95)), 'max': float(np.max(shuf)),
                           'role_rank_pct': float(np.mean(np.array(shuf) < res['arms']['ROLE']['mean_all']))}
    print('SHUF:', res['shuf_control'])
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
