"""E-153 評估：預註冊 §4 ＋ errata-1。匯入 E-142 phase1_eval 的函式（口徑 errata-1～3），人群 K0／K6，三季 2022-23～2024-25，seed 20261101。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.7d+E153-t6-target/e153_eval.py"""
import csv, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E142 = ROOT / 'reports/E142-card-target'
sys.path.insert(0, str(E142))
s = importlib.util.spec_from_file_location('pe', E142 / 'phase1_eval.py'); P = importlib.util.module_from_spec(s); s.loader.exec_module(P)
TWOK = ROOT / 'data/external-impact/2k/2k-merged-e142.csv'
W = HERE / 'work'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
JUDGE = SEASONS[:3]
SEED, B = 20261101, 2000
KEY = ['Cooper Flagg', 'Kon Knueppel', 'Paolo Banchero', 'Jalen Suggs', 'Dylan Harper', 'Anthony Edwards', 'Jonathan Kuminga', 'Victor Wembanyama',
       'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Jalen Brunson', 'Herbert Jones', 'Dillon Brooks', 'Stephon Castle', 'Jaylen Wells', 'Ron Holland', 'Podziemski']


def rpath(arm, t):
    if t == '2025-26':
        return W / ('K0' if arm == 'K0' else 'K6-2025-26') / 'c0/ranking.csv'
    return W / (f'K0h-{t}' if arm == 'K0' else f'K6-{t}') / t / 'out/K0/ranking.csv'


def ages(t):
    f = ROOT / ('data/benchmark-source/bio.json' if t == '2025-26' else f'data/defense-seventh/{t}/bio.json')
    d = json.loads(f.read_text(encoding='utf-8'))['data']['resultSets'][0]
    i, a = d['headers'].index('PLAYER_ID'), d['headers'].index('AGE')
    return {r[i]: r[a] for r in d['rowSet'] if r[a] is not None}


def main():
    twok = P.load_twok(str(TWOK))
    pages = {s_: P.C0L.contracts(s_) for s_ in P.C0L.ORDER}
    drafts, ev = P.C0L.draft_years(), P.C0L.tx_events()
    pops, mpgs = {}, {}
    for t in SEASONS:
        pops[t], mpgs[t] = P.pop_of(t)
    data, chk, rankinfo = {}, {'twok_sha256': P.sha(TWOK), 'seed': SEED, 'draws': B, 'rank_sha256': {}, 'seasons': {}}, {}
    for t in SEASONS:
        pop = pops[t]
        sal, sstat = P.salary_terms(t, pop, pages, drafts, ev)
        ref, raw, excl = P.build_ref(t, pop, mpgs, sal, twok, {})
        n2 = defaultdict(list)
        for p, i in pop.items():
            n2[P.norm(i['name'])].append(p)
        ranks, ovrs = {}, {}
        for arm in ('K0', 'K6'):
            f = rpath(arm, t)
            chk['rank_sha256'][f'{arm}-{t}'] = P.sha(f)
            m, full = {}, []
            for r in csv.DictReader(open(f, encoding='utf-8-sig')):
                if float(r['MIN']) < 500:
                    continue
                ids = n2.get(P.norm(r['name'])) or []
                full.append((r['name'], float(r['ovr'])))
                if len(ids) == 1:
                    m[ids[0]] = float(r['ovr'])
            ranks[arm] = m
            ovrs[arm] = full
        common = set(ranks['K0']) & set(ranks['K6'])
        ids = sorted(p for p in common if p in ref)
        ag = ages(t)
        data[t] = {'ids': ids, 'ovr': {a: np.array([ranks[a][p] for p in ids]) for a in ranks}, 'ref': np.array([ref[p] for p in ids]), 'raw': raw,
                   'young': np.array([ag.get(p, 99) <= 23 for p in ids])}
        chk['seasons'][t] = {'pop': len(pop), 'evalPop': len(ids), 'cardRows500': {a: len(ovrs[a]) for a in ovrs}, 'salaryStats': sstat,
                             'avail': {k: sum(1 for p in ids if p in raw[k]) for k in raw}}
        rankinfo[t] = ovrs

    def metrics(t, arm, idx=None):
        d = data[t]
        idx = np.arange(len(d['ids'])) if idx is None else idx
        o, rf = d['ovr'][arm][idx], d['ref'][idx]
        out = {'n': int(len(idx)), 'C': P.spearman(o, rf)}
        for k in ('sal', 'twok', 'rapm'):
            have = [i for i in idx if d['ids'][i] in d['raw'][k]]
            out['n_' + k] = len(have)
            if len(have) < 10:
                out[k] = None
                continue
            oo = d['ovr'][arm][have]
            if k == 'sal':
                y = [d['raw'][k][d['ids'][i]][0] for i in have]
                w = [P.YEARW.get(d['raw'][k][d['ids'][i]][1], 0.3) for i in have]
                out[k] = P.wspearman(oo, y, w)
            else:
                out[k] = P.spearman(oo, [d['raw'][k][d['ids'][i]] for i in have])
        return out
    ps = {t: {a: metrics(t, a) for a in ('K0', 'K6')} for t in SEASONS}
    young = {t: {a: metrics(t, a, np.where(data[t]['young'])[0]) for a in ('K0', 'K6')} for t in SEASONS}

    def pooled(key):
        num = den = 0.0
        for t in JUDGE:
            a, b0 = ps[t]['K6'], ps[t]['K0']
            nn = a['n'] if key == 'C' else a['n_' + key]
            num += nn * (a[key] - b0[key]); den += nn
        return num / den
    od = {k: pooled(k) for k in ('C', 'sal', 'twok', 'rapm')}
    rng = np.random.default_rng(SEED)
    allids = sorted(set().union(*[data[t]['ids'] for t in JUDGE]))
    pos = {t: {p: i for i, p in enumerate(data[t]['ids'])} for t in JUDGE}
    diffs = np.empty(B)
    for b in range(B):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        num = den = 0.0
        for t in JUDGE:
            sel = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat(np.array([pos[t][allids[j]] for j in sel]), np.array([mult[j] for j in sel]))
            d = data[t]
            cs = P.spearman(d['ovr']['K6'][idx], d['ref'][idx]) - P.spearman(d['ovr']['K0'][idx], d['ref'][idx])
            num += len(idx) * cs; den += len(idx)
        diffs[b] = num / den
    lo, hi = float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95))
    j1, j2, j22, j3 = lo > 0, od['sal'] >= -P.TOL['sal'], od['twok'] >= -P.TOL['twok'], od['rapm'] >= -P.TOL['rapm']
    verdict = 'adopt_candidate' if (j1 and j2 and j22 and j3) else ('side_effect' if j1 else 'no_improvement')
    # 關鍵球員與前 20
    def rk(t, arm):
        lst = sorted(rankinfo[t][arm], key=lambda x: -x[1])
        return {n: (i + 1, o) for i, (n, o) in enumerate(lst)}, lst
    key = {}
    for t in ('2025-26', '2024-25'):
        r0, l0 = rk(t, 'K0'); r6, l6 = rk(t, 'K6')
        rows = {}
        for k in KEY:
            for n in r0:
                if k.lower() in n.lower() or P.norm(k) == P.norm(n):
                    rows[n] = {'K0_rank': r0[n][0], 'K0_ovr': r0[n][1], 'K6_rank': r6.get(n, (None, None))[0], 'K6_ovr': r6.get(n, (None, None))[1]}
        key[t] = {'n500': len(l0), 'players': rows,
                  'top20_K0': [n for n, _ in l0[:20]], 'top20_K6': [n for n, _ in l6[:20]]}
    res = {'per_season': ps, 'young_le23': young, 'oof_diff': od, 'bootstrap': {'lower90': lo, 'upper90': hi, 'draws': B, 'seed': SEED},
           'judgement': {'1': bool(j1), '2_sal': bool(j2), '2-2_2k': bool(j22), '3_rapm': bool(j3), 'verdict': verdict}, 'key_players': key, 'checks': chk}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({'od': od, 'lo': lo, 'hi': hi, 'verdict': verdict}, ensure_ascii=False))
    for t in SEASONS:
        print(t, json.dumps(ps[t]), ' | young', json.dumps(young[t]))
    for t in key:
        print(t, json.dumps(key[t], ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
