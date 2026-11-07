"""E-157 評估口徑 v2（可重用）。匯入 E-142 phase1_eval 的函式，不複製改寫口徑；只新增「下季自製 EPM」項。
ref_i ＝ Σ w·p ÷ Σ w（缺項按比例重分配）：薪水 0.4×合約年次權重、2K 0.3、下季 RAPM×W 0.15、下季 EPM×W 0.15（模擬不列入）。
EPM 項：epm_self/epm_<t+1>.csv 的 net（stintPoss>=1000）× W(t+1 mpg)，處理照 phase1_eval.build_ref 的下季 RAPM 項。2025-26 無此項。
用法（import）：
    import eval_v2 as V
    D = V.load({'K0': {'2022-23': path, ...}, 'K6': {...}})      # 各臂各季 ranking.csv
    V.metrics(D, t, arm, ref='v2'|'old', idx=None)               # n, C, sal, twok, rapm, epm
    V.pooled(D, 'K6', 'K0', seasons, key, ref='v2', mask=None)   # 人數加權差
    V.boot(D, 'K6', 'K0', seasons, seed, ref='v2', mask=None)    # 球員層 bootstrap（2000 次）
    V.checks(...)  # 見 judge()
ref='old' 即關掉 EPM 項（舊三項權重；c0 用）。
"""
import csv, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E142 = ROOT / 'reports/E142-card-target'
sys.path.insert(0, str(E142))
_s = importlib.util.spec_from_file_location('pe', E142 / 'phase1_eval.py')
P = importlib.util.module_from_spec(_s)
_s.loader.exec_module(P)
TWOK = ROOT / 'data/external-impact/2k/2k-merged-e142.csv'
EPMDIR = ROOT / 'data/external-impact/epm_self'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
JUDGE = SEASONS[:3]
B = 2000
W_EPM = 0.15
KEYS = ('sal', 'twok', 'rapm', 'epm')
TOL = {'sal': 0.02, 'twok': 0.02, 'rapm': 0.05, 'epm': 0.05}

_CACHE = {}


def ages(t):
    f = ROOT / ('data/benchmark-source/bio.json' if t == '2025-26' else f'data/defense-seventh/{t}/bio.json')
    d = json.loads(f.read_text(encoding='utf-8'))['data']['resultSets'][0]
    i, a = d['headers'].index('PLAYER_ID'), d['headers'].index('AGE')
    return {r[i]: r[a] for r in d['rowSet'] if r[a] is not None}


def _base():
    """每季：pop、sal、old ref、raw、epm 項、v2 ref（與臂無關，只算一次）。"""
    if 'base' in _CACHE:
        return _CACHE['base']
    twok = P.load_twok(str(TWOK))
    pages = {s: P.C0L.contracts(s) for s in P.C0L.ORDER}
    drafts, ev = P.C0L.draft_years(), P.C0L.tx_events()
    pops, mpgs = {}, {}
    for t in SEASONS:
        pops[t], mpgs[t] = P.pop_of(t)
    base = {}
    for t in SEASONS:
        pop = pops[t]
        sal, sstat = P.salary_terms(t, pop, pages, drafts, ev)
        ref_old, raw, excl = P.build_ref(t, pop, mpgs, sal, twok, {})
        epm = {}
        if t in P.NEXT:
            n = P.NEXT[t]
            mp = mpgs[n]
            for r in csv.DictReader(open(EPMDIR / f'epm_{n}.csv', encoding='utf-8-sig')):
                p = int(r['playerId'])
                if p in pop and float(r['stintPoss']) >= 1000 and p in mp:
                    epm[p] = float(r['net']) * P.wfun(mp[p])
        raw = dict(raw)
        raw['epm'] = epm
        # v2 ref：用 raw 的各項重算百分位（與 build_ref 同法）；舊三項分量必須和 ref_old 完全一致
        ps = P.pct({p: v[0] for p, v in raw['sal'].items()})
        terms = [{p: (ps[p], P.W_BASE['sal'] * P.YEARW.get(raw['sal'][p][1], 0.3)) for p in raw['sal']}]
        pk = P.pct(raw['twok']); terms.append({p: (pk[p], P.W_BASE['twok']) for p in raw['twok']})
        pr = P.pct(raw['rapm']); terms.append({p: (pr[p], P.W_BASE['rapm']) for p in raw['rapm']})
        pe = P.pct(raw['epm']); terms_v2 = terms + [{p: (pe[p], W_EPM) for p in raw['epm']}]

        def comb(tl):
            out = {}
            for p in pop:
                num = den = 0.0
                for tt in tl:
                    if p in tt:
                        v, w = tt[p]; num += w * v; den += w
                if den > 0:
                    out[p] = num / den
            return out
        r_old2, ref_v2 = comb(terms), comb(terms_v2)
        assert set(r_old2) == set(ref_old) and all(abs(r_old2[p] - ref_old[p]) < 1e-12 for p in ref_old), 'old ref 重算與 phase1_eval 不一致'
        base[t] = {'pop': pop, 'mpg': mpgs[t], 'raw': raw, 'ref_old': ref_old, 'ref_v2': ref_v2, 'sstat': sstat, 'age': ages(t)}
    _CACHE['base'] = base
    return base


def load(arms, seasons=SEASONS):
    """arms: {臂名: {季: ranking.csv 路徑}}。人群＝MIN>=500、所有臂都有、ref_v2 有項目者（ref_old 的人群是其子集）。"""
    base = _base()
    D = {'arms': list(arms), 'seasons': {}, 'sha': {}}
    for t in seasons:
        b = base[t]
        pop = b['pop']
        n2 = defaultdict(list)
        for p, i in pop.items():
            n2[P.norm(i['name'])].append(p)
        ranks, names = {}, {}
        for a, paths in arms.items():
            D['sha'][f'{a}-{t}'] = P.sha(paths[t])
            m = {}
            for r in csv.DictReader(open(paths[t], encoding='utf-8-sig')):
                if float(r['MIN']) < 500:
                    continue
                ids = n2.get(P.norm(r['name'])) or []
                if len(ids) == 1:
                    m[ids[0]] = float(r['ovr']); names[ids[0]] = r['name']
            ranks[a] = m
        common = set.intersection(*[set(ranks[a]) for a in arms])
        ids = sorted(p for p in common if p in b['ref_v2'])
        D['seasons'][t] = {
            'ids': ids, 'names': [names[p] for p in ids], 'ovr': {a: np.array([ranks[a][p] for p in ids]) for a in arms},
            'ref_v2': np.array([b['ref_v2'][p] for p in ids]),
            'ref_old': np.array([b['ref_old'].get(p, np.nan) for p in ids]),
            'raw': b['raw'], 'young': np.array([b['age'].get(p, 99) <= 23 for p in ids]), 'pop': len(pop)}
    return D


def metrics(D, t, arm, ref='v2', idx=None):
    d = D['seasons'][t]
    rf_all = d['ref_v2'] if ref == 'v2' else d['ref_old']
    idx = np.arange(len(d['ids'])) if idx is None else np.asarray(idx)
    if ref == 'old':
        idx = np.array([i for i in idx if not np.isnan(rf_all[i])], dtype=int)
    o, rf = d['ovr'][arm][idx], rf_all[idx]
    out = {'n': int(len(idx)), 'C': P.spearman(o, rf)}
    for k in KEYS:
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


def per_season(D, ref='v2', subset=None, seasons=SEASONS):
    """subset: None 或 'young'。回 {t: {arm: metrics}}。"""
    res = {}
    for t in seasons:
        d = D['seasons'][t]
        idx = None if subset is None else np.where(d['young'])[0]
        res[t] = {a: metrics(D, t, a, ref, idx) for a in D['arms']}
    return res


def pooled(ps, a, b, seasons, key):
    """a−b，依 a 的 n 加權（C 用 n，其他用 n_key），與 E-153 e153_eval.pooled 相同。"""
    num = den = 0.0
    for t in seasons:
        x, y = ps[t][a], ps[t][b]
        if x[key] is None or y[key] is None:
            continue
        nn = x['n'] if key == 'C' else x['n_' + key]
        num += nn * (x[key] - y[key]); den += nn
    return num / den if den else None


def pooled_level(ps, a, seasons, key):
    num = den = 0.0
    for t in seasons:
        x = ps[t][a]
        if x[key] is None:
            continue
        nn = x['n'] if key == 'C' else x['n_' + key]
        num += nn * x[key]; den += nn
    return num / den if den else None


def boot(D, a, b, seasons, seed, ref='v2', subset=None, draws=B):
    """C(a)−C(b) 的球員層 bootstrap：seasons 球員聯集重抽，各季人數加權。subset='young' 時只含該季 AGE<=23 者（聯集也只含年輕人）。"""
    rng = np.random.default_rng(seed)
    sel = {}
    for t in seasons:
        d = D['seasons'][t]
        rf = d['ref_v2'] if ref == 'v2' else d['ref_old']
        ok = ~np.isnan(rf)
        if subset == 'young':
            ok &= d['young']
        sel[t] = np.where(ok)[0]
    allids = sorted(set().union(*[{D['seasons'][t]['ids'][i] for i in sel[t]} for t in seasons]))
    pos = {t: {D['seasons'][t]['ids'][i]: i for i in sel[t]} for t in seasons}
    diffs = np.empty(draws)
    for k in range(draws):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        num = den = 0.0
        for t in seasons:
            s = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat(np.array([pos[t][allids[j]] for j in s]), np.array([mult[j] for j in s]))
            d = D['seasons'][t]
            rf = d['ref_v2'] if ref == 'v2' else d['ref_old']
            cs = P.spearman(d['ovr'][a][idx], rf[idx]) - P.spearman(d['ovr'][b][idx], rf[idx])
            num += len(idx) * cs; den += len(idx)
        diffs[k] = num / den
    return {'lower90': float(np.percentile(diffs, 5)), 'upper90': float(np.percentile(diffs, 95)), 'draws': draws, 'seed': seed}


def judge(ps, bt, a, b, seasons=JUDGE):
    od = {k: pooled(ps, a, b, seasons, k) for k in ('C',) + KEYS}
    j = {'1': bt['lower90'] > 0, '2_sal': od['sal'] >= -TOL['sal'], '2-2_2k': od['twok'] >= -TOL['twok'],
         '3_rapm': od['rapm'] >= -TOL['rapm'], '4_epm': od['epm'] >= -TOL['epm']}
    return od, {k: bool(v) for k, v in j.items()}
