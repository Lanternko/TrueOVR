"""E-189 step 1: non-shooting-foul propensity attribute gamma (prereg section 2). cwd = repo root. Local, light; no subprocess.
Definition = reports/F129-center-ft-defense-diag/d2_propensity.py (personal foul, descriptor None / loose ball / take; flagrant excluded).
Build half h uses games with int(gameId)%2==h; the other half is the judging answer. Writes attr-odd.json (built on odd games, judged on even),
attr-even.json (built on even games, judged on odd), real-halves.json (per-player counts/possessions per half) and p150.json (frozen population)."""
import json, collections, hashlib, numpy as np, sys
sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from f129lib import players, real_rows, sim_load
D = 'reports/sim-0.1.3+E189-nsfoul-attr/'
poss = collections.defaultdict(lambda: [0, 0]); ns = collections.defaultdict(lambda: [0, 0]); games = set()
for l in open('reports/defense-b1/stints.jsonl', encoding='utf-8'):
    s = json.loads(l); h = int(s['id']) % 2; games.add(s['id'])
    for t in s['teams']:
        for p in t['players']: poss[p][h] += t['defensivePossessions']
for g in games:
    h = int(g) % 2
    for x in json.load(open(f'data/defense-a-source/pbp/{g}.json', encoding='utf-8'))['data']['game']['actions']:
        if x.get('actionType') != 'foul' or x.get('subType') != 'personal': continue
        d = x.get('descriptor')
        if d and d.startswith('flagrant'): continue
        if d in (None, 'loose ball', 'take'): ns[x.get('personId')][h] += 1
ids = [p for p in poss if min(poss[p]) >= 1000]
rate = lambda p, h: 100 * ns[p][h] / poss[p][h]
rel = float(np.corrcoef([rate(p, 0) for p in ids], [rate(p, 1) for p in ids])[0, 1])
nmed = float(np.median([poss[p][h] for p in ids for h in (0, 1)]))
k = nmed * (1 - rel) / rel
meta = {'players_for_k': len(ids), 'split_half_reliability': rel, 'median_half_defposs': nmed, 'k': k, 'definition': 'k = n_med*(1-rel)/rel, computed once on all >=1000-per-half players, same k for both builds'}
def build(h):
    P = [p for p in poss if poss[p][h] > 0]
    tot_n = sum(poss[p][h] for p in P); tot_c = sum(ns[p][h] for p in P); rbar = 100 * tot_c / tot_n
    out = {}
    for p in P:
        n = poss[p][h]; r = 100 * ns[p][h] / n; rt = (n * r + k * rbar) / (n + k); out[p] = [n, ns[p][h], r, rt, float(np.log(rt / rbar))]
    m = sum(v[0] * v[4] for v in out.values()) / sum(v[0] for v in out.values())
    return {'rbar': rbar, 'center_shift': m, 'gamma': {str(p): v[4] - m for p, v in out.items()}, 'n': {str(p): v[0] for p, v in out.items()}}
x = players(); R = real_rows()
LD = 'reports/F129-center-ft-defense-diag/ledgers/'
pres = [set(i for r in R[h] for i in r['o'] + r['d']) for h in (0, 1)]
sims = [set(i for r in sim_load(LD + f'v-a-{s}.json') for i in r['o'] + r['d']) for s in (20261103, 20261104)]
P150 = sorted(i for i in x if x[i]['min'] >= 1000 and all(i in p for p in pres + sims))
for name, h in (('odd', 1), ('even', 0)):
    b = build(h); b.update(meta); b['build_half'] = f'games with int(gameId)%2=={h} ({name})'
    json.dump(b, open(D + f'attr-{name}.json', 'w', encoding='utf-8'), indent=1)
json.dump({str(p): {'name': x[p]['name'], 'pos': x[p]['pos'], 'defposs': poss[p], 'ns': ns[p]} for p in P150}, open(D + 'real-halves.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(P150, open(D + 'p150.json', 'w'))
print(json.dumps(meta)); print('p150', len(P150))
for f in ('attr-odd.json', 'attr-even.json', 'p150.json', 'real-halves.json'):
    print(f, hashlib.sha256(open(D + f, 'rb').read()).hexdigest())
for name in ('odd', 'even'):
    b = json.load(open(D + f'attr-{name}.json')); g = np.array([b['gamma'][str(p)] for p in P150 if str(p) in b['gamma']])
    print(name, 'rbar', b['rbar'], 'gamma sd (p150)', g.std(), g.min(), g.max())
