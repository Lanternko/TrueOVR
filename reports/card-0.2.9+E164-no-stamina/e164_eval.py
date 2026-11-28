"""E-164 評估（預註冊 §2 c0/u1、§3、§4）。eval_v2，seed 20261104、2000 次。用法（repo root）：python -I -B -X utf8 <本檔>"""
import csv, json, shutil, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))
import eval_v2 as V
P = V.P
SEED = 20261104
ARMS = ['K', 'S']
KEY = ['Jalen Williams', 'Chet Holmgren', 'Nikola Jokić', 'Shai Gilgeous-Alexander', 'Victor Wembanyama', 'Cooper Flagg', 'Anthony Edwards']
ABIL = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina',
        'heightInches', 'creation', 'pressure', 'mpg', 'foulDisc', 'MIN', 'pos']


def rp(a, t):
    return HERE / 'work' / f'{a}-{t}' / 'out' / 'ranking.csv'


def rows(a, t):
    return {r['name']: r for r in csv.DictReader(open(rp(a, t), encoding='utf-8-sig'))}


def main():
    c0 = {}
    for t in V.SEASONS:
        ref = ROOT / 'reports/card-0.2.9/ranking.csv' if t == '2025-26' else ROOT / f'reports/card-0.2.8+E158-young-under-T6/ranking-Y0-{t}.csv'
        c0[t] = {'K_sha': P.sha(rp('K', t)), 'ref_sha': P.sha(ref), 'same': P.sha(rp('K', t)) == P.sha(ref)}
    assert all(v['same'] for v in c0.values()), 'c0 FAIL'
    u1 = {}
    for t in V.SEASONS:
        k, s = rows('K', t), rows('S', t)
        bad = []
        if set(k) != set(s):
            bad.append('name set differs')
        for n in k:
            if n in s:
                for c in ABIL:
                    if c in k[n] and k[n][c] != s[n][c]:
                        bad.append((n, c, k[n][c], s[n][c]))
        u1[t] = {'n': len(k), 'mismatch': len(bad), 'examples': bad[:5], 'same': not bad}
    D = V.load({a: {t: rp(a, t) for t in V.SEASONS} for a in ARMS})
    ps = V.per_season(D, 'v2')
    bt = V.boot(D, 'S', 'K', V.JUDGE, SEED)
    da = {k: V.pooled(ps, 'S', 'K', V.JUDGE, k) for k in ('C',) + V.KEYS}
    a_ = da['C'] >= -0.005
    b_ = {'sal': da['sal'] >= -0.02, 'twok': da['twok'] >= -0.02, 'rapm': da['rapm'] >= -0.05, 'epm': da['epm'] >= -0.05}
    res = {'c0': c0, 'c0_pass': True, 'u1': u1, 'seed': SEED, 'draws': V.B, 'n_eval': {t: len(D['seasons'][t]['ids']) for t in V.SEASONS},
           'per_season': ps, 'diff_pooled_S_minus_K': da, 'boot': bt, 'a': bool(a_), 'b': {k: bool(v) for k, v in b_.items()},
           'pass': bool(a_ and all(b_.values()))}
    res['pooled_level'] = {a: {k: V.pooled_level(ps, a, V.JUDGE, k) for k in ('C',) + V.KEYS} for a in ARMS}
    # 2025-26 名次
    rk, ov, pos, mpg = {}, {}, {}, {}
    for a in ARMS:
        rr = [(r['name'], float(r['ovr']), r['pos'], float(r['mpg'])) for r in csv.DictReader(open(rp(a, '2025-26'), encoding='utf-8-sig')) if float(r['MIN']) >= 500]
        rr.sort(key=lambda x: -x[1])
        rk[a] = {n: i + 1 for i, (n, _, _, _) in enumerate(rr)}
        ov[a] = {n: o for n, o, _, _ in rr}
        if a == 'K':
            pos = {n: q for n, _, q, _ in rr}
            mpg = {n: m for n, _, _, m in rr}
    names = list(rk['K'])

    def find(k):
        m = [n for n in names if P.norm(n) == P.norm(k)] or [n for n in names if P.norm(k) in P.norm(n)]
        return m[0] if m else None
    mv = sorted(((rk['K'][n] - rk['S'][n], n) for n in names if n in rk['S']), reverse=True)  # 正＝升
    up5, dn5 = [n for _, n in mv[:5]], [n for _, n in mv[-5:]][::-1]
    kr = {}
    for k in KEY + up5 + dn5:
        n = find(k) if k in KEY else k
        kr[n or k] = {a: {'rank': rk[a][n], 'ovr': ov[a][n]} for a in ARMS} if n else None
    res['key_players'] = kr; res['up5'] = up5; res['dn5'] = dn5
    # 三分位（整季場均分鐘，K 的 mpg 欄）
    def tert(t, pop_names):
        pass
    tr = {}
    for t in V.SEASONS:
        k, s = rows('K', t), rows('S', t)
        ns = [n for n in k if float(k[n]['MIN']) >= 500 and n in s]
        m = np.array([float(k[n]['mpg']) for n in ns])
        q1, q2 = np.percentile(m, [100 / 3, 200 / 3])
        # 名次：在 MIN>=500 人群內
        def ranks(r):
            o = sorted(ns, key=lambda n: -float(r[n]['ovr']))
            return {n: i + 1 for i, n in enumerate(o)}
        rK, rS = ranks(k), ranks(s)
        g = {'低': [], '中': [], '高': []}
        for n, mm in zip(ns, m):
            g['低' if mm <= q1 else ('中' if mm <= q2 else '高')].append(n)
        tr[t] = {'cuts': [float(q1), float(q2)], **{lab: {'n': len(v), 'dOVR': float(np.mean([float(s[n]['ovr']) - float(k[n]['ovr']) for n in v])),
                 'dRank_up': float(np.mean([rK[n] - rS[n] for n in v])), 'mpg_mean': float(np.mean([float(k[n]['mpg']) for n in v]))} for lab, v in g.items()}}
    res['tertiles'] = tr
    top = {a: sorted(rk[a], key=rk[a].get) for a in ARMS}
    bigs = [n for n in top['K'] if pos[n] in ('C', 'PF')][:10]
    res['K_top10_bigs'] = {n: {'pos': pos[n], 'K': rk['K'][n], 'S': rk['S'].get(n)} for n in bigs}
    res['top20'] = {a: top[a][:20] for a in ARMS}
    res['top20_changes'] = {'in': [n for n in top['S'][:20] if n not in top['K'][:20]], 'out': [n for n in top['K'][:20] if n not in top['S'][:20]]}
    res['moved10_top300'] = sum(1 for n in top['K'][:300] if abs(rk['S'].get(n, 999) - rk['K'][n]) >= 10)
    res['n_pop_2526'] = len(names)
    # 係數
    co = {}
    for part in ('primary', 'fitA', 'fitB'):
        out = {}
        for a, d in (('K', 'base-Kc-2025-26'), ('S', 'base-S-2025-26')):
            sm = json.load(open(HERE / 'work' / d / 'c0/cards/K0' / part / 'summary.json', encoding='utf-8'))
            out[a] = {'chosen': sm['chosen'], 'per10': {k: v['per36'] for k, v in sm['valuePer10AttributePoints'].items()}}
        kk, ss = out['K']['per10'], out['S']['per10']
        chg = sorted(((abs(ss[k] - kk[k]), k) for k in ss if k in kk and k != 'stamina'), reverse=True)[:3]
        out['K_stamina'] = kk.get('stamina')
        out['top3_change'] = {k: {'K': kk[k], 'S': ss[k], 'd': ss[k] - kk[k]} for _, k in chg}
        co[part] = out
    res['coef'] = co
    res['sha256'] = {f'{a}-{t}': P.sha(rp(a, t)) for a in ARMS for t in V.SEASONS}
    for a in ARMS:
        for t in V.SEASONS:
            shutil.copy(rp(a, t), HERE / f'ranking-{a}-{t}.csv')
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
