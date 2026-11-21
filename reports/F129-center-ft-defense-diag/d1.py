"""F-129 D1: additive ridge decomposition of the defensive 'fta' coefficient into blocks, real (pbp-attributed) vs sim (record-only patch ledgers).
Same ridge as d0 (lambda 3000, weight = defensive possessions, per 100). Linear in the response, so coefficient(total) = sum of block coefficients.
Blocks: own = FTs from shooting fouls committed by the player himself (fouler on court); mate = shooting-foul FTs by his 4 on-court teammates;
offl = shooting-foul FTs whose fouler is not in the stint lineup (real only, substitution timing); nsh = non-shooting-foul FTs + other.
Second lens on the shooting FTs: comp = sum_z opportunities_z * league mean FT-per-opportunity_z (shot mix/volume), rate = remainder (foul rate per shot).
Shares: cross-half covariance (half0 block vs half1 total, both ways, averaged) / cross-half covariance of total; scaled to the noise-corrected tsd^2.
usage: python d1.py   cwd = repo root. numpy/scipy only, no subprocess."""
import sys, json, time; sys.path.insert(0, 'reports/F129-center-ft-defense-diag')
from f129lib import *
LD = 'reports/F129-center-ft-defense-diag/ledgers/'; LAM = 3000; ZONES = ('short', 'mid', 'long')
x = players(); RD = json.load(open('reports/F129-center-ft-defense-diag/real_d1_rows.json', encoding='utf-8')); RR = {0: RD['0'], 1: RD['1']}
seeds = list(range(20261103, 20261119)); SIM = {c: {s: sim_load(LD + f'v-{c}-{s}.json') for s in seeds} for c in 'ab'}
ids = sorted({i for h in RR for r in RR[h] for i in r['o'] + r['d']} | {i for c in SIM for s in SIM[c] for r in SIM[c][s] for i in r['o'] + r['d']}); ix = {v: k for k, v in enumerate(ids)}; n = len(ids)
def zsum(r, key): return sum(v for k, v in r[key].items())
class Half:
    def __init__(s, rows, rbar):
        m = len(rows); s.P = np.array([r['poss'] for r in rows], float); rr, cc = [], []; yr, yc, yv = [], [], []
        T = np.zeros((m, 9))  # tot sh nsh comp rate offl onl nsf oth
        for k, r in enumerate(rows):
            for i in r['o']: rr.append(k); cc.append(ix[i])
            dset = set(r['d'])
            for i in r['d']: rr.append(k); cc.append(n + ix[i])
            sh = off = 0; own = {}
            for key, v in r['sf'].items():
                j = int(key.split('|')[0]); sh += v
                if j in dset: own[j] = own.get(j, 0) + v
                else: off += v
            for j, v in own.items(): yr.append(k); yc.append(ix[j]); yv.append(v)
            nsh = sum(r['nsf'].values()) + r['oth']; comp = sum((r[z + 'A'] + r['sfa'].get(z, 0)) * rbar[z] for z in ZONES)
            T[k] = (sh + nsh, sh, nsh, comp, sh - comp, off, sh - off, sum(r['nsf'].values()), r['oth'])
        s.X = sp.csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(m, 2 * n)); s.XT = s.X.T.tocsr(); s.T = T
        s.Y = sp.csr_matrix((yv, (yr, yc)), shape=(m, n)); s.A = (s.XT @ sp.diags(s.P) @ s.X).tocsc(); s.v = s.XT @ s.P; s.Wn = s.P.sum()
        s.U = np.hstack([s.XT @ T, (s.XT @ s.Y).toarray()]); s.S = np.concatenate([T.sum(0), np.asarray(s.Y.sum(0)).ravel()])
def solve(parts, cols=None):
    A = sum(p.A for p in parts); v = sum(p.v for p in parts); Wn = sum(p.Wn for p in parts); U = sum(p.U for p in parts); S = sum(p.S for p in parts)
    if cols is not None: U = U[:, cols]; S = S[cols]
    sol = sl.splu((A + LAM * sp.eye(2 * n, format='csc')).tocsc()).solve(U - np.outer(v, S / Wn)) * 100
    return -sol[n:, :]   # (n, ncols) defence coefficients
def blocks(C):
    """C: (n, 7+n) solved coefficients -> dict of block vectors"""
    own = np.array([C[i, 9 + i] for i in range(n)]); onl = C[:, 6]
    return {'tot': C[:, 0], 'sh': C[:, 1], 'nsh': C[:, 2], 'comp': C[:, 3], 'rate': C[:, 4], 'offl': C[:, 5], 'own': own, 'mate': onl - own, 'nsf': C[:, 7], 'oth': C[:, 8]}
def rbar_of(rowsets):
    num = {z: 0 for z in ZONES}; den = {z: 0 for z in ZONES}
    for rows in rowsets:
        for r in rows:
            for key, v in r['sf'].items(): num[key.split('|')[1]] += v
            for z in ZONES: den[z] += r[z + 'A'] + r['sfa'].get(z, 0)
    return {z: num[z] / den[z] for z in ZONES}
def analyse(h0, h1, sel, pidx):
    """h0,h1: Half objects; returns per group: tsd_total, shares of blocks (signal var scaled to tsd^2), block var."""
    c0 = blocks(solve([h0])); c1 = blocks(solve([h1])); cf = solve([h0, h1], cols=[0])[:, 0]
    res = {}
    for g, j in pidx.items():
        r = np.corrcoef(c0['tot'][j], c1['tot'][j])[0, 1]; t = cf[j].std() * np.sqrt(max(2 * r / (1 + r), 0)); sig = np.cov(c0['tot'][j], c1['tot'][j])[0, 1]
        sh = {}
        for b in c0:
            cv = 0.5 * (np.cov(c0[b][j], c1['tot'][j])[0, 1] + np.cov(c1[b][j], c0['tot'][j])[0, 1]); sh[b] = cv / sig
        res[g] = {'tsd': float(t), 'r': float(r), 'share': {b: float(v) for b, v in sh.items()}, 'var': {b: float(v * t * t) for b, v in sh.items()}}
    return res
def run():
    pres = [set(i for rr_ in RR[h] for i in rr_['o'] + rr_['d']) for h in (0, 1)] + [set(i for r in SIM[c][s] for i in r['o'] + r['d']) for c in 'ab' for s in (20261103, 20261104)]
    P = [i for i in x if x[i]['min'] >= 1000 and all(i in p for p in pres)]; pidx = {g: np.array([ix[i] for i in P if x[i]['pos'] in pos]) for g, pos in GRP}
    out = {'n_players': len(P), 'n_group': {g: len(v) for g, v in pidx.items()}}
    rb = rbar_of([RR[0], RR[1]]); t = time.time(); H = [Half(RR[0], rb), Half(RR[1], rb)]; out['real'] = analyse(H[0], H[1], None, pidx); out['rbar_real'] = rb
    print('real', f'{time.time()-t:.0f}s', {g: round(v['tsd'], 3) for g, v in out['real'].items()}); sys.stdout.flush()
    for c in 'ab':
        for tag, prs in (('point', [(20261103, 20261104)]), ('disjoint8', [(seeds[2 * k], seeds[2 * k + 1]) for k in range(8)])):
            lst = []
            for sa, sb in prs:
                rbs = rbar_of([SIM[c][sa], SIM[c][sb]]); hs = [Half(SIM[c][sa], rbs), Half(SIM[c][sb], rbs)]; lst.append(analyse(hs[0], hs[1], None, pidx))
                if tag == 'point': out['rbar_sim_' + c] = rbs
            out[f'sim_{c}_{tag}'] = lst; print(c, tag, [{g: round(v['tsd'], 3) for g, v in L.items()} for L in lst][:3]); sys.stdout.flush()
    json.dump(out, open('reports/F129-center-ft-defense-diag/d1_blocks.json', 'w', encoding='utf-8'), indent=1)
if __name__ == '__main__': run()
