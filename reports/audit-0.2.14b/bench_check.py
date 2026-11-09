"""role-audit 0.2.14b：前瞻台獨立重算（四折，λ=0.5，W1 對 A 的 Spearman 差）。
只借 E-290 台子載入各折人群（ids、names、pos、ovr、sd、P_ref）與下季 EPM 目標 Y；
MIX 加分（BBRef 比例、身高帶、z_H、tanh、縮放）自己從原始檔重寫，指標用 scipy spearmanr 自己算，不用 e295_eval／Q.metrics。
用法（repo root）：python -I -B -X utf8 reports/audit-0.2.14b/bench_check.py
"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


E290 = mod('e290', 'reports/E290-reb-bonus-0213a/e290_eval.py')
E = E290.E; Q = E.Q
FOLDS, NEXT, FULL = E.FOLDS, E.NEXT, E.FULL
BB = ROOT / 'reports/card-0.2.9a+E177-bbref-position-shares'
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
P5 = ['PG', 'SG', 'SF', 'PF', 'C']; WP = np.array([0, 0, 0, .68 / 2.8, 1])
SH = {}
for s in SEAS:
    SH[s] = {}
    for r in csv.DictReader(open(BB / f'pos-shares-{s}.csv', encoding='utf-8')):
        if r['playerId']:
            v = np.array([float(r['p_' + p]) for p in P5])
            if v.sum() > 0: SH[s][r['playerId']] = (v / v.sum(), float(r['MP']))
soft = lambda x: 1.5 * np.tanh(np.clip(x, 0, None) / 1.5)


def shares(ids, hgt, season):
    cur = SH[season]
    m = np.array([p in cur and cur[p][1] >= 200 for p in ids])
    H = hgt[m]; PIp = np.array([cur[p][0] for p, k in zip(ids, m) if k])

    def pr(h):
        for k in (1, 2, 3, 4, 5, 8):
            mm = np.abs(H - h) <= k
            if mm.sum() >= 15: return PIp[mm].mean(0)
        return PIp.mean(0)
    out = np.zeros((len(ids), 5))
    earlier = SEAS[:SEAS.index(season)][::-1]
    for i, p in enumerate(ids):
        row = cur.get(p)
        if row is None:
            row = next((SH[s][p] for s in earlier if p in SH[s]), None)
        ph = pr(hgt[i])
        if row is None: out[i] = ph; continue
        v, mp = row
        out[i] = v if mp >= 200 else (mp * v + (200 - mp) * ph) / 200
    return out


def P_of(feat, PIm, w, ref):
    zh = {}
    for k, (v, ok) in feat.items():
        mu, sd = v[ok].mean(), v[ok].std()
        z = np.where(ok, (v - mu) / sd, 0.0)
        mp = (PIm[ok] * z[ok, None]).sum(0) / PIm[ok].sum(0)
        mi = PIm @ mp
        zh[k] = np.where(ok, z - 0.5 * mi, 0.5 * mi)
    a, b = soft((zh['reb'] + zh['ob'] + zh['db']) / 3), soft(zh['con'])
    rms = lambda x: np.sqrt(np.mean(x ** 2))
    sa, sb = ref / rms(a), ref / rms(b)
    m0 = .5 * a * sa + .5 * b * sb
    return m0 * ref / rms(m0) * w


res = {}
D = {c: E.build(c) for c in FOLDS}
Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}; Y['2025-26'] = E.V.live_targets(D['2025-26']['ids'])['epm']
for c in FOLDS:
    d = D[c]; n = len(d['ids']); ids = [str(p) for p in d['ids']]
    stage = {r['name']: r for r in csv.DictReader(open(E290.STAGE / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
    cardS = {r['name']: r for r in csv.DictReader(open(E.CARD / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
    reb = np.array([float(stage[x]['rebound']) for x in d['names']]); hgt = np.array([float(cardS[x]['heightInches']) for x in d['names']])
    tab = {}
    for r in csv.DictReader(open(ROOT / f'reports/E227-lineup-transformer-r2/data/stats-{c}.csv', encoding='utf-8')):
        tab[r['pid']] = r
    ob = np.array([float(tab[p]['orebPct']) if p in tab and tab[p]['orebPct'] not in ('', None) else np.nan for p in ids])
    db = np.array([float(tab[p]['drebPct']) if p in tab and tab[p]['drebPct'] not in ('', None) else np.nan for p in ids])
    js = json.loads(E.hustle_path(c).read_text(encoding='utf-8')); Hs = {}
    for r in js['rowSet']:
        r = dict(zip(js['headers'], r)); a = Hs.setdefault(int(r['PLAYER_ID']), [0.0, 0.0]); a[0] += r['MIN'] or 0; a[1] += r['CONTESTED_SHOTS_2PT'] or 0
    con = np.array([Hs[int(p)][1] / Hs[int(p)][0] * 36 if int(p) in Hs and Hs[int(p)][0] >= 200 else np.nan for p in ids])
    feat = {'reb': (reb, np.ones(n, bool)), 'ob': (np.nan_to_num(ob), np.isfinite(ob)), 'db': (np.nan_to_num(db), np.isfinite(db)),
            'con': (np.nan_to_num(con), np.isfinite(con))}
    PIb = shares(ids, hgt, c)
    PIl = np.array([[1.0 if q == p else 0.0 for q in P5] for p in d['pos']])
    PA = P_of(feat, PIl, PIl @ WP, d['P_ref']); PW = P_of(feat, PIb, PIb @ WP, d['P_ref'])
    y = Y[c]; k = np.isfinite(y)
    o0, oA, oW = d['ovr'], d['ovr'] + .5 * d['sd'] * PA, d['ovr'] + .5 * d['sd'] * PW
    sp = lambda o: float(spearmanr(o[k], y[k])[0])
    res[c] = {'n': int(k.sum()), 'rho_base': sp(o0), 'rho_A': sp(oA), 'rho_W1': sp(oW), 'W1_minus_A': sp(oW) - sp(oA), 'A_minus_base': sp(oA) - sp(o0)}
nn = {c: res[c]['n'] for c in FOLDS}; tot = sum(nn.values())
res['weighted_W1_minus_A'] = sum(nn[c] / tot * res[c]['W1_minus_A'] for c in FOLDS)
res['weighted_W1_minus_base'] = sum(nn[c] / tot * (res[c]['rho_W1'] - res[c]['rho_base']) for c in FOLDS)
rj = json.load(open(ROOT / 'reports/E295-mix-pos-continuous/results.json', encoding='utf-8'))['bench']['arms']
res['producer_per_fold_W1_vs_A'] = rj['W1']['per_fold_vs_A05']; res['producer_weighted'] = rj['W1']['same05_vs_A05']
res['producer_W1_vs_base'] = rj['W1']['same05_vs_base']
Path(__file__).with_name('bench_check.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, indent=1))
