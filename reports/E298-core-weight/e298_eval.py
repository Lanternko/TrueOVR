"""E-298：MIX 加分按 MPG 打折（主力權重）＋上限。預註冊 preregistration.md（sha 見 preregistration.sha256，commit 835a2a8）。
重用 E-295 的公式與評估（reports/E295-mix-pos-continuous/e295_eval.py，W1＝BBRef 連續位置）。
用法（repo root）：python -I -B -X utf8 reports/E298-core-weight/e298_eval.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'

sys.argv.append('--explore')   # 只為了略過 e295 自己的預註冊 sha 斷言；不呼叫它的 main
s = importlib.util.spec_from_file_location('e295', ROOT / 'reports/E295-mix-pos-continuous/e295_eval.py')
M = importlib.util.module_from_spec(s); sys.modules['e295'] = M; s.loader.exec_module(M)

SEED, B = 20261298, 2000
rng = np.random.default_rng(SEED)
M.BOOT = {k: [rng.integers(0, len(M.idx[k]), len(M.idx[k])) for _ in range(B)] for k in M.idx}
N, names = M.N, M.names
card = list(csv.DictReader(open(M.CARD, encoding='utf-8')))
MPG = np.array([float(r['mpg'] or 0) for r in card])
CW1 = M.SPEC['W1'][1]


def U(b, mpg, ref): return b * np.minimum(1.0, mpg / ref)
def K(b, cap=5.0): return cap * np.tanh(np.maximum(b, 0) / cap)


TRANS = {'W1': lambda b, m: b, 'U30': lambda b, m: U(b, m, 30.0), 'U24': lambda b, m: U(b, m, 24.0),
         'K5': lambda b, m: K(b), 'UK': lambda b, m: K(U(b, m, 30.0))}
CAND = ('U30', 'U24', 'K5', 'UK')
BON = {'A': M.BON['A'], **{a: f(M.BON['W1'], MPG) for a, f in TRANS.items()}}
WATCH = ['Deni Avdija', 'Donovan Clingan', 'Robert Williams III', 'Jrue Holiday', 'Rudy Gobert', 'Nikola Jokić', 'Victor Wembanyama',
         'Anthony Davis', 'Karl-Anthony Towns', 'Joel Embiid', 'Kristaps Porziņģis', 'Chet Holmgren', 'Evan Mobley', 'Ivica Zubac',
         'Jarrett Allen', 'Clint Capela', 'Mitchell Robinson', 'Isaiah Hartenstein', 'Domantas Sabonis', 'Alperen Sengun', 'Bam Adebayo',
         'Scottie Barnes', 'Jalen Johnson', 'Franz Wagner', 'Josh Giddey', 'Toumani Camara']


def ranks(o):
    order = sorted(range(N), key=lambda i: (-o[i], M.rank0[i])); r = np.empty(N, int); r[order] = np.arange(1, N + 1); return r


def bench():
    """E-295 bench 同台，只算 W1 與其轉換（各折 MPG 用該折卡片 mpg）。"""
    E290 = M.mod('e290', 'reports/E290-reb-bonus-0213a/e290_eval.py')
    E = E290.E; Q = E.Q; FOLDS, NEXT, FULL = E.FOLDS, E.NEXT, E.FULL
    D = {c: E.build(c) for c in FOLDS}
    PP = {}
    for c in FOLDS:
        d = D[c]; E290.add_arms(c, d)
        stage = {r['name']: r for r in csv.DictReader(open(E290.STAGE / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
        cardS = {r['name']: r for r in csv.DictReader(open(E.CARD / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
        n = len(d['ids'])
        reb = np.array([float(stage[nm]['rebound']) for nm in d['names']])
        hgt = np.array([float(cardS[nm]['heightInches']) for nm in d['names']])
        mpg = np.array([float(cardS[nm]['mpg'] or 0) for nm in d['names']])
        tab = E290.stats_tab(c); ob = np.full(n, np.nan); db = np.full(n, np.nan)
        for i, p in enumerate(d['ids']):
            x = tab.get(str(p))
            if x:
                if x['orebPct'] is not None: ob[i] = x['orebPct']
                if x['drebPct'] is not None: db[i] = x['drebPct']
        js = json.loads(E.hustle_path(c).read_text(encoding='utf-8')); H = {}
        for r in js['rowSet']:
            r = dict(zip(js['headers'], r)); a_ = H.setdefault(int(r['PLAYER_ID']), [0.0, 0.0])
            a_[0] += r['MIN'] or 0; a_[1] += r['CONTESTED_SHOTS_2PT'] or 0
        v = np.zeros(n); have = np.zeros(n, bool)
        for i, p in enumerate(d['ids']):
            x = H.get(int(p))
            if x and x[0] >= 200: v[i] = x[1] / x[0] * 36; have[i] = True
        feat = {'reb': (reb, np.ones(n, bool)), 'ob': (np.nan_to_num(ob), np.isfinite(ob)), 'db': (np.nan_to_num(db), np.isfinite(db)),
                'con': (v, have)}
        ids = [str(p) for p in d['ids']]
        PIb, _, _ = M.shares_for(ids, hgt, c, M.SH)
        keep = M.REFC; M.REFC = d['P_ref']
        p1 = M.build(feat, np.ones(n, bool), PIb, PIb @ M.POSW)[0]
        M.REFC = keep
        # P 是「每 sd·λ 單位」的加分；轉換在 OVR 分數尺度上做（×λ·sd 後轉換再除回），和卡片一致
        sc = 0.5 * d['sd']
        PP[c] = {a: f(p1 * sc, mpg) / sc for a, f in TRANS.items()}
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}; Y['2025-26'] = E.V.live_targets(D['2025-26']['ids'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}; w = {t: n[t] / sum(n.values()) for t in FOLDS}
    m = lambda t, o: float(Q.metrics(D[t], Y[t], o)['all'])
    base = {t: m(t, D[t]['ovr']) for t in FOLDS}
    ref = {t: m(t, E.adj(D[t], PP[t]['W1'], .5)) for t in FOLDS}
    out = {'n': n}
    for a in TRANS:
        v = {t: m(t, E.adj(D[t], PP[t][a], .5)) for t in FOLDS}
        out[a] = {'vs_base': float(sum(w[t] * (v[t] - base[t]) for t in FOLDS)), 'vs_W1': float(sum(w[t] * (v[t] - ref[t]) for t in FOLDS)),
                  'per_fold_vs_W1': {t: v[t] - ref[t] for t in FOLDS}, 'n_pos_vs_W1': int(sum(v[t] > ref[t] for t in FOLDS)),
                  'gap_C': float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], PP[t][a], .5), 'C') for t in FOLDS]).mean())}
        print(f"bench {a:4s} Δbase {out[a]['vs_base']:+.4f} ΔW1 {out[a]['vs_W1']:+.4f} ({out[a]['n_pos_vs_W1']}/4) gapC {out[a]['gap_C']:+.3f}")
    return out


def live(a):
    rows = list(csv.DictReader(open(M.LIVE_RANK, encoding='utf-8')))
    o0 = np.array([float(r['ovr']) - float(r['mixBonus'] or 0) for r in rows])
    b = np.array([float(r['mixBonus'] or 0) for r in rows]); mp = np.array([float(r['MPGhat'] or r['MPG0'] or 0) for r in rows])
    f = {'A': lambda b, m: b, 'W1': lambda b, m: b, **TRANS}[a]
    o = np.round(o0 + f(b, mp), 1)
    order = np.argsort(-o, kind='stable'); rk = np.empty(len(rows), int); rk[order] = np.arange(1, len(rows) + 1)
    nm = [r['name'] for r in rows]
    return {n: (int(rk[nm.index(n)]), float(o[nm.index(n)])) for n in ('Deni Avdija', 'Donovan Clingan', 'Robert Williams III', 'Jrue Holiday') if n in nm}


def main():
    W1o = np.round(M.ovr0 + BON['W1'], 1)
    evW, _ = M.card_eval(BON['W1'], M.CAPB['W1'])
    rA = ranks(np.round(M.ovr0 + BON['A'], 1))
    res = {'prereg_sha256': sha(HERE / 'preregistration.md'), 'arms': {}}
    for a in BON:
        ev, o = M.card_eval(BON[a], M.CAPB['W1'], W1o)
        r = ev.pop('_rank')
        ia, ic, iw = names.index('Deni Avdija'), names.index('Donovan Clingan'), names.index('Robert Williams III')
        S1 = bool(r[ia] < r[ic])
        drops = [(names[i], int(rA[i]), int(r[i])) for i in range(N) if rA[i] <= 30 and r[i] - rA[i] > 10]
        big_drops = [x for x in drops if CW1[names.index(x[0])] >= 0.5]
        S2 = len(drops) <= 2 and not big_drops
        S3 = not any(v['mean'] < -0.005 and v['ci90'][1] < 0 for v in ev['drho_vs_A'].values())
        res['arms'][a] = {'S1': S1, 'S1b_avdija_over_rw3': bool(r[ia] < r[iw]), 'S2': S2, 'S3': S3, 'drops_vs_0214a': drops,
                          'rho': ev['rho'], 'drho_vs_W1': ev['drho_vs_A'],
                          'watch': {n: {'rank': int(r[names.index(n)]), 'ovr': float(o[names.index(n)]), 'bonus': round(float(BON[a][names.index(n)]), 2),
                                        'mpg': float(MPG[names.index(n)])} for n in WATCH if n in names},
                          'top20': [names[i] for i in np.argsort(r)[:20]], 'live': live(a),
                          'max_bonus': float(BON[a].max()), 'top_bonus': [(names[i], round(float(BON[a][i]), 2), float(MPG[i])) for i in np.argsort(-BON[a])[:10]]}
        x = res['arms'][a]
        print(f"{a:4s} S1 {S1} S1b {x['S1b_avdija_over_rw3']} S2 {S2} S3 {S3} drops {drops}")
        print('     ρ', {k: round(v, 4) for k, v in ev['rho'].items()}, {k: (round(v['mean'], 4), [round(c, 4) for c in v['ci90']]) for k, v in ev['drho_vs_A'].items()})
        print('     POR', {k: (v['rank'], v['ovr'], v['bonus']) for k, v in x['watch'].items() if k in ('Deni Avdija', 'Donovan Clingan', 'Robert Williams III')}, 'live', x['live'])
    res['bench'] = bench()
    for a in CAND:
        x = res['arms'][a]; x['S4'] = res['bench'][a]['vs_W1'] >= -0.002
        x['verdict'] = 'adopt_candidate' if all(x[g] for g in ('S1', 'S2', 'S3', 'S4')) else 'reject'
    ok = [a for a in CAND if res['arms'][a]['verdict'] == 'adopt_candidate']
    pick = None
    if ok:
        best = max(res['bench'][a]['vs_W1'] for a in ok)
        pick = next(a for a in CAND if a in ok and res['bench'][a]['vs_W1'] >= best - 0.001)
    res['pick'] = pick
    print('verdicts', {a: res['arms'][a]['verdict'] for a in CAND}, 'pick', pick)
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=lambda v: v.item() if hasattr(v, 'item') else str(v)), encoding='utf-8')


if __name__ == '__main__':
    main()
