"""F-129 D1 bootstrap: uncertainty of the block variance gap (real minus sim) of the defensive fta coefficient, groups C and nonC.
Per draw: players resampled with replacement within group (paired real/sim); real games resampled within each parity half; sim = two distinct seeds from the 16-seed pool.
Reuses d1.py (same ridge, same blocks). usage: python d1_boot.py [N=400]   cwd = repo root. numpy/scipy only."""
import sys, time, json; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from types import SimpleNamespace as NS
import d1
from d1 import *
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400; rng = np.random.default_rng(1291)
rb = rbar_of([RR[0], RR[1]]); RH = [Half(RR[0], rb), Half(RR[1], rb)]
ug = [np.unique([r['gid'] for r in RR[h]], return_inverse=True) for h in (0, 1)]
def withmult(h, m):
    W = h.P * m; return NS(A=(h.XT @ sp.diags(W) @ h.X).tocsc(), v=h.XT @ W, Wn=W.sum(), U=np.hstack([h.XT @ (h.T * m[:, None]), (h.XT @ h.Y.multiply(m[:, None]).tocsr()).toarray()]), S=np.concatenate([(h.T * m[:, None]).sum(0), np.asarray(h.Y.multiply(m[:, None]).sum(0)).ravel()]))
pres = [set(i for rr_ in RR[h] for i in rr_['o'] + rr_['d']) for h in (0, 1)] + [set(i for r in SIM[c][s] for i in r['o'] + r['d']) for c in 'ab' for s in (20261103, 20261104)]
P = [i for i in x if x[i]['min'] >= 1000 and all(i in p for p in pres)]; pidx = {g: np.array([ix[i] for i in P if x[i]['pos'] in pos]) for g, pos in GRP if g in ('C', 'nonC')}
SH = {}; SB = {}
for c in 'ab':
    rbs = rbar_of([SIM[c][s] for s in seeds]); SH[c] = [Half(SIM[c][s], rbs) for s in seeds]; SB[c] = [blocks(solve([h])) for h in SH[c]]
FC = {}
def sim_pair(c):
    a, b = sorted(rng.choice(16, 2, replace=False))
    if (c, a, b) not in FC: FC[(c, a, b)] = solve([SH[c][a], SH[c][b]], cols=[0])[:, 0]
    return SB[c][a], SB[c][b], FC[(c, a, b)]
def stat(c0, c1, cf, j):
    r = np.corrcoef(c0['tot'][j], c1['tot'][j])[0, 1]; t = cf[j].std() * np.sqrt(max(2 * r / (1 + r), 0)); sig = np.cov(c0['tot'][j], c1['tot'][j])[0, 1]
    v = {b: 0.5 * (np.cov(c0[b][j], c1['tot'][j])[0, 1] + np.cov(c1[b][j], c0['tot'][j])[0, 1]) / sig * t * t for b in c0}; v['tsd'] = t; return v
acc = {g: [] for g in pidx}; t0 = time.time()
for it in range(N):
    m = []
    for h in (0, 1):
        u, inv = ug[h]; cnt = np.bincount(rng.integers(0, len(u), len(u)), minlength=len(u)); m.append(cnt[inv].astype(float))
    hs = [withmult(RH[h], m[h]) for h in (0, 1)]; r0, r1, rf = blocks(solve([hs[0]])), blocks(solve([hs[1]])), solve(hs, cols=[0])[:, 0]
    sims = {c: sim_pair(c) for c in 'ab'}
    for g, J in pidx.items():
        j = rng.choice(J, len(J), replace=True)
        acc[g].append({'real': stat(r0, r1, rf, j), **{'sim_' + c: stat(*sims[c], j) for c in 'ab'}})
    if it % 50 == 0: print(it, f'{time.time()-t0:.0f}s'); sys.stdout.flush()
B = ['own', 'mate', 'nsf', 'oth', 'sh', 'comp', 'rate', 'tsd']
out = {'N': N}
for g in pidx:
    out[g] = {}
    for c in 'ab':
        q = {}
        for b in B:
            gap = np.array([a['real'][b] - a['sim_' + c][b] for a in acc[g]]); q[b + '_gap'] = [float(np.percentile(gap, p)) for p in (5, 50, 95)]
        tot = np.array([a['real']['tot'] - a['sim_' + c]['tot'] for a in acc[g]]); 
        for b in ('nsf', 'sh', 'mate', 'own', 'rate', 'comp'):
            gap = np.array([a['real'][b] - a['sim_' + c][b] for a in acc[g]]); sh = gap / tot; q[b + '_share_of_gap'] = [float(np.percentile(sh, p)) for p in (5, 50, 95)]
        q['tot_gap'] = [float(np.percentile(tot, p)) for p in (5, 50, 95)]
        rat = np.array([a['sim_' + c]['tsd'] / a['real']['tsd'] for a in acc[g]]); q['ratio_foultime_basis'] = [float(np.percentile(rat, p)) for p in (5, 50, 95)]; q['ratio_frac_ge_1'] = float((rat >= 1).mean())
        q['real_nsf_var_gt_sim_frac'] = float(np.mean([a['real']['nsf'] > a['sim_' + c]['nsf'] for a in acc[g]]))
        out[g][c] = q
json.dump(out, open('reports/F129-center-ft-defense-diag/d1_boot.json', 'w', encoding='utf-8'), indent=1)
for g in out:
    if g == 'N': continue
    for c in 'ab': print(g, c, {k: ([round(z, 3) for z in v] if isinstance(v, list) else round(v, 3)) for k, v in out[g][c].items() if k.endswith(('_gap', 'ratio_foultime_basis', 'ratio_frac_ge_1', 'real_nsf_var_gt_sim_frac')) or 'share' in k})
