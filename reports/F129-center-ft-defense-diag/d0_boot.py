"""F-129 D0 step 2: bootstrap of the sim/real noise-corrected spread ratio of the defensive 'fta' coefficient, by position group.
Resampling: players (with replacement within group, paired real/sim), real games (with replacement within each parity half), sim seeds (two distinct
seeds drawn from the 16-seed pool per config). Modes isolate each source. Same ridge as ridge_k.py (checked in d0_repro.py).
usage: python d0_boot.py [N_all=2000] [N_each=1000]   cwd = repo root. Local, light (numpy/scipy only)."""
import sys, glob, os, json, time; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from f129lib import *
NA = int(sys.argv[1]) if len(sys.argv) > 1 else 2000; NE = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
LD = 'reports/F129-center-ft-defense-diag/ledgers/'
x = players(); R = real_rows(); LAM = 3000
seeds = list(range(20261103, 20261119)); cfg = {c: {s: sim_load(LD + f'v-{c}-{s}.json') for s in seeds} for c in 'ab'}
ids = sorted({i for h in R for r in R[h] for i in r['o'] + r['d']} | {i for c in cfg for s in cfg[c] for r in cfg[c][s] for i in r['o'] + r['d']}); ix = {v: k for k, v in enumerate(ids)}; n = len(ids)
def mat(rows):
    rr, cc = [], []
    for k, r in enumerate(rows):
        for i in r['o']: rr.append(k); cc.append(ix[i])
        for i in r['d']: rr.append(k); cc.append(n + ix[i])
    X = sp.csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(rows), 2 * n)); return X, X.T.tocsr()
class Half:
    def __init__(s, rows):
        s.rows = rows; s.X, s.XT = mat(rows); s.P = np.array([r['poss'] for r in rows], float); s.N = np.array([r['fta'] for r in rows], float)
        s.gid = np.array([hash(r.get('gid', 0)) for r in rows]) if 'gid' in rows[0] else None
        s.ug, s.inv = (np.unique([r['gid'] for r in rows], return_inverse=True) if s.gid is not None else (None, None))
    def stats(s, mult=None):
        m = np.ones(len(s.P)) if mult is None else mult; W = s.P * m; Nn = s.N * m
        return (s.XT @ sp.diags(W) @ s.X).tocsc(), s.XT @ Nn, s.XT @ W, Nn.sum(), W.sum()
def solve(A, u, v, S, Wn, others=()):
    return None
def coefs(sa, sb):
    """sa,sb = stats of two halves -> (half0, half1, full) defence coef vectors (len n) via normal equations"""
    out = []
    for (A, u, v, S, Wn) in (sa, sb, tuple(a + b for a, b in zip(sa, sb))):
        b = sl.splu((A + LAM * sp.eye(2 * n, format='csc')).tocsc()).solve(u - (S / Wn) * v) * 100; out.append(-b[n:])
    return out
rh = {h: Half(R[h]) for h in (0, 1)}
sh = {c: {s: Half(cfg[c][s]) for s in seeds} for c in cfg}
sstat = {c: {s: sh[c][s].stats() for s in seeds} for c in cfg}
rstat0 = [rh[h].stats() for h in (0, 1)]
FR0 = coefs(*rstat0)
pres = [set(i for r in rr_ for i in r['o'] + r['d']) for rr_ in [R[0], R[1], cfg['a'][20261103], cfg['a'][20261104], cfg['b'][20261103], cfg['b'][20261104]]]
P = [i for i in x if x[i]['min'] >= 1000 and all(i in p for p in pres)]; print('players', len(P))
pidx = {g: np.array([ix[i] for i in P if x[i]['pos'] in pos]) for g, pos in GRP}
def ratio(FR, FS, sel):
    out = {}
    for g in pidx:
        j = sel[g]; fr = tsd(FR[2][j], FR[0][j], FR[1][j])[0]; fs = tsd(FS[2][j], FS[0][j], FS[1][j])[0]
        out[g] = fs / fr if fr > 0 else np.nan
    return out
fixed_sel = {g: pidx[g] for g in pidx}
rng = np.random.default_rng(129)
def real_resample():
    st = []
    for h in (0, 1):
        H = rh[h]; cnt = np.bincount(rng.integers(0, len(H.ug), len(H.ug)), minlength=len(H.ug)); st.append(H.stats(cnt[H.inv].astype(float)))
    return coefs(*st)
PC = {}
def sim_pair(c):
    a, b = sorted(rng.choice(len(seeds), 2, replace=False))
    if (c, a, b) not in PC: PC[(c, a, b)] = coefs(sstat[c][seeds[a]], sstat[c][seeds[b]])
    return PC[(c, a, b)]
RD = []
def real_draw(i):
    while len(RD) <= i: RD.append(real_resample())
    return RD[i]
res = {}
for c in 'ab':
    FS0 = coefs(sstat[c][20261103], sstat[c][20261104]); base = ratio(FR0, FS0, fixed_sel)
    # all 120 seed pairs, real fixed
    pairs = [(a, b) for a in range(16) for b in range(a + 1, 16)]
    allp = [ratio(FR0, coefs(sstat[c][seeds[a]], sstat[c][seeds[b]]), fixed_sel) for a, b in pairs]
    res[c] = {'point_seeds_03_04': base, 'pairs120': {g: {'mean': float(np.mean([p[g] for p in allp])), 'min': float(np.min([p[g] for p in allp])), 'max': float(np.max([p[g] for p in allp]))} for g in pidx}}
    print(c, 'point', {g: round(v, 3) for g, v in base.items()}, 'pairs120 mean', {g: round(res[c]['pairs120'][g]['mean'], 3) for g in pidx}); sys.stdout.flush()
    for mode, N in (('players', NE), ('real_games', NE), ('sim_seeds', NE), ('all', NA)):
        t = time.time(); FS_fixed = coefs(sstat[c][20261103], sstat[c][20261104]); acc = {g: [] for g in pidx}; nn = 0
        for _ in range(N):
            sel = {g: rng.choice(pidx[g], len(pidx[g]), replace=True) for g in pidx} if mode in ('players', 'all') else fixed_sel
            FR = real_draw(_) if mode in ('real_games', 'all') else FR0
            FS = sim_pair(c) if mode in ('sim_seeds', 'all') else FS_fixed
            r = ratio(FR, FS, sel)
            for g in pidx: acc[g].append(r[g])
        res[c][mode] = {'N': N, **{g: {'p05': float(np.nanpercentile(a, 5)), 'p50': float(np.nanpercentile(a, 50)), 'p95': float(np.nanpercentile(a, 95)), 'mean': float(np.nanmean(a)),
                       'nan': int(np.isnan(a).sum()), 'frac_ge_1': float(np.nanmean(np.array(a) >= 1)), 'frac_ge_0.8': float(np.nanmean(np.array(a) >= 0.8))} for g, a in acc.items()}}
        print(c, mode, N, f'{time.time()-t:.0f}s', {g: (round(res[c][mode][g]['p05'], 2), round(res[c][mode][g]['p50'], 2), round(res[c][mode][g]['p95'], 2)) for g in pidx}); sys.stdout.flush()
json.dump(res, open('reports/F129-center-ft-defense-diag/d0_boot.json', 'w', encoding='utf-8'), indent=1)
