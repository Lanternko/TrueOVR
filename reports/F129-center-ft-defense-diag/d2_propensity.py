"""F-129 D2: are shooting-foul and non-shooting-foul rates the same individual propensity? (real 2025-26, measure only)
Per player: personal fouls committed per 100 defensive possessions, split shooting vs non-shooting (personal None / loose ball / take;
flagrant, offensive, technical excluded). Split-half by game-id parity; cross-half correlation disattenuated by half reliabilities."""
import json, collections, numpy as np
R = 'reports/F129-center-ft-defense-diag/'
poss = collections.defaultdict(lambda: [0, 0]); sh = collections.defaultdict(lambda: [0, 0]); ns = collections.defaultdict(lambda: [0, 0]); nsft = collections.defaultdict(lambda: [0, 0])
games = set()
for l in open('reports/defense-b1/stints.jsonl', encoding='utf-8'):
    s = json.loads(l); h = int(s['id']) % 2; games.add(s['id'])
    for t in s['teams']:
        for p in t['players']: poss[p][h] += t['defensivePossessions']
for g in games:
    h = int(g) % 2
    for x in json.load(open(f'data/defense-a-source/pbp/{g}.json', encoding='utf-8'))['data']['game']['actions']:
        if x.get('actionType') != 'foul' or x.get('subType') != 'personal': continue
        d = x.get('descriptor'); p = x.get('personId')
        if d and d.startswith('flagrant'): continue
        if d == 'shooting': sh[p][h] += 1
        elif d in (None, 'loose ball', 'take'):
            ns[p][h] += 1
            if any(q.endswith('freethrow') for q in x.get('qualifiers', [])): nsft[p][h] += 1
meta = {p['id']: p for p in json.load(open('reports/sim-0.1.1-oreb-diag/rr-20261101.json', encoding='utf-8'))['real']}
ids = [p for p in poss if min(poss[p]) >= 1000]
def rate(c, p, h): return 100 * c[p][h] / poss[p][h]
def full(c, p): return 100 * sum(c[p]) / sum(poss[p])
def block(sel, label):
    out = {'label': label, 'n': len(sel)}
    S = {k: np.array([[rate(c, p, 0), rate(c, p, 1)] for p in sel]) for k, c in (('sh', sh), ('ns', ns), ('nsft', nsft))}
    for k, v in S.items(): out[f'rel_half_{k}'] = float(np.corrcoef(v[:, 0], v[:, 1])[0, 1])
    for k in ('ns', 'nsft'):
        cross = (np.corrcoef(S['sh'][:, 0], S[k][:, 1])[0, 1] + np.corrcoef(S['sh'][:, 1], S[k][:, 0])[0, 1]) / 2
        out[f'cross_sh_{k}'] = float(cross)
        out[f'true_r_sh_{k}'] = float(cross / np.sqrt(max(out['rel_half_sh'], 1e-9) * max(out[f'rel_half_{k}'], 1e-9)))
        F = np.array([[full(sh, p), full(c, p)] for p, c in ((p, {'ns': ns, 'nsft': nsft}[k]) for p in sel)])
        out[f'raw_full_r_sh_{k}'] = float(np.corrcoef(F[:, 0], F[:, 1])[0, 1])
    out['mean_sh'] = float(np.mean([full(sh, p) for p in sel])); out['mean_ns'] = float(np.mean([full(ns, p) for p in sel]))
    return out
res = [block(ids, 'all >=2000 def poss')]
known = [p for p in ids if p in meta]
res.append(block([p for p in known if meta[p]['pos'] == 'C'], 'C'))
res.append(block([p for p in known if meta[p]['pos'] != 'C'], 'non-C'))
top = sorted(ids, key=lambda p: -full(sh, p))[:12]
res.append({'examples_top_shooting_fouls': [{'id': p, 'name': meta.get(p, {}).get('name'), 'pos': meta.get(p, {}).get('pos'), 'sh100': round(full(sh, p), 2), 'ns100': round(full(ns, p), 2), 'pct_rank_ns': round(float(np.mean([full(ns, q) <= full(ns, p) for q in ids])), 2)} for p in top]})
json.dump(res, open(R + 'd2_propensity.json', 'w'), ensure_ascii=False, indent=1)
for r in res: print(json.dumps(r, ensure_ascii=False))
