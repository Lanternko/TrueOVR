"""sim 0.1.4: non-shooting-foul propensity attribute gamma, 2025-26 full season (R-131, E-189). cwd = repo root. Local, light; no subprocess.
Same definition as reports/sim-0.1.3+E189-nsfoul-attr/build_attr.py (personal foul, descriptor None / loose ball / take; flagrant excluded;
rate per 100 defensive possessions; reliability shrinkage toward league rate; log vs league; possession-weighted mean removed),
but built on BOTH halves merged (all games). k is frozen to the E-189 value (build_attr.log), not recomputed.
Output: reports/sim-0.1.4/ns-foul-gamma-2025-26.json"""
import json, collections, hashlib, numpy as np
K = 696.6998437251774  # build_attr.log k (split-half reliability 0.7128, median half defposs 1729.5)
D = 'reports/sim-0.1.4/'
STINTS = 'reports/defense-b1/stints.jsonl'
sha = lambda b: hashlib.sha256(b).hexdigest()
poss = collections.Counter(); ns = collections.Counter(); games = set()
for l in open(STINTS, encoding='utf-8'):
    s = json.loads(l); games.add(s['id'])
    for t in s['teams']:
        for p in t['players']: poss[p] += t['defensivePossessions']
pbp_h = hashlib.sha256()
for g in sorted(games, key=str):
    raw = open(f'data/defense-a-source/pbp/{g}.json', 'rb').read(); pbp_h.update(str(g).encode() + b':' + sha(raw).encode() + b'\n')
    for x in json.loads(raw.decode('utf-8'))['data']['game']['actions']:
        if x.get('actionType') != 'foul' or x.get('subType') != 'personal': continue
        d = x.get('descriptor')
        if d and d.startswith('flagrant'): continue
        if d in (None, 'loose ball', 'take'): ns[x.get('personId')] += 1
P = [p for p in poss if poss[p] > 0]
tot_n = sum(poss[p] for p in P); tot_c = sum(ns[p] for p in P); rbar = 100 * tot_c / tot_n
g = {}
for p in P:
    n = poss[p]; r = 100 * ns[p] / n; rt = (n * r + K * rbar) / (n + K); g[p] = float(np.log(rt / rbar))
m = sum(poss[p] * g[p] for p in P) / tot_n
out = {'rbar': rbar, 'center_shift': m, 'k': K, 'games': len(games),
       'gamma': {str(p): g[p] - m for p in P}, 'n': {str(p): poss[p] for p in P},
       'sha': {'stints.jsonl': sha(open(STINTS, 'rb').read()), 'pbp_files_combined(sorted gameId, id:sha256 lines)': pbp_h.hexdigest()},
       'definition': 'reports/sim-0.1.3+E189-nsfoul-attr/build_attr.py build(h) on all games; k frozen'}
json.dump(out, open(D + 'ns-foul-gamma-2025-26.json', 'w', encoding='utf-8'), indent=1)
v = np.array(list(out['gamma'].values()))
print('games', len(games), 'players', len(P), 'rbar', rbar, 'center_shift', m, 'gamma sd', v.std(), v.min(), v.max())
print('sha256 out', sha(open(D + 'ns-foul-gamma-2025-26.json', 'rb').read()))
print(json.dumps(out['sha']))
