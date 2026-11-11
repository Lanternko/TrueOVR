import json, csv, math, sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from scipy.stats import rankdata
ROOT = Path(r'D:/Projects/CODING/basketball-autochess')
sys.path.insert(0, str(ROOT/'reports/E175-sliding-window-card'))
import e175_lib as L
F = json.loads((ROOT/'reports/ovr-inseason-2026-27/live/pnr-pool-card0213.json').read_text(encoding='utf-8'))
ww = F['weights_c0']; print('weights', ww)
rows = list(csv.DictReader(open(ROOT/'reports/card-0.2.13/pnr-attr.csv', encoding='utf-8')))
# (A) 從原始 Synergy + player-games 獨立重算 POSS_eff/vol/rate
def rs(d):
    d = d.get('data', d); t = d['resultSets'] if 'resultSets' in d else d
    t = t[0] if isinstance(t, list) else t
    return t['headers'], t['rowSet']
def mins(path):
    H, R = rs(json.loads(Path(path).read_text(encoding='utf-8')))
    i, j = H.index('PLAYER_ID'), H.index('MIN'); c = Counter()
    for r in R:
        v = r[j]
        if v in (None, ''): continue
        m = int(v.split(':')[0]) + int(v.split(':')[1])/60 if isinstance(v, str) and ':' in v else float(v)
        if m > 0: c[int(r[i])] += m
    return c
SEAS = ['2022-23','2023-24','2024-25','2025-26']
PG = {s: ROOT/f'data/defense-seventh/{s}/player-games.json' for s in SEAS[:3]}; PG['2025-26'] = ROOT/'data/season-source/player-games.json'
acc = defaultdict(lambda: [0,0,0,0,0])
S = {}
for s in SEAS:
    if s not in ww: continue
    H, R = rs(json.loads((ROOT/f'reports/E239-tracking-full/data/syn-PRBallHandler-{s}.json').read_text(encoding='utf-8')))
    ip, iP, it = H.index('PLAYER_ID'), H.index('POSS'), H.index('PTS')
    poss, pts = Counter(), Counter()
    for r in R: poss[int(r[ip])] += float(r[iP]); pts[int(r[ip])] += float(r[it])
    S[s] = (poss, pts)
    for p, m in mins(PG[s]).items():
        a = acc[p]; w = ww[s]; a[0] += w*poss.get(p,0); a[1] += w*pts.get(p,0); a[2] += w*m; a[3] += w; a[4] = max(a[4], w)
eff = {p: (a[0]/max(a[3],a[4]), a[1]/max(a[3],a[4]), a[2]/max(a[3],a[4])) for p, a in acc.items()}
# k, mu from 2025-26
poss25, pts25 = S['2025-26']
H, R = rs(json.loads((ROOT/'reports/E239-tracking-full/data/syn-PRBallHandler-2025-26.json').read_text(encoding='utf-8')))
sp = H.index('SCORE_POSS_PCT'); score = Counter()
for r in R: score[int(r[H.index('PLAYER_ID')])] += float(r[sp])*float(r[H.index('POSS')])
P = sum(poss25.values()); mu = sum(pts25.values())/P; sc = sum(score.values())/P
s2 = mu*(mu/sc) - mu*mu
ps = [(pts25[p]/poss25[p], poss25[p]) for p in poss25 if poss25[p] >= 50]
x = np.array([a for a,_ in ps]); n = np.array([b for _,b in ps]); m = np.average(x, weights=n)
vt = max(np.average((x-m)**2, weights=n) - np.average(s2/n, weights=n), 1e-6)
k = float(min(max(s2/vt, 20), 800)); print('k', k, 'mu', mu, 'frozen', F['k'], F['mu'])
pids = [int(r['playerId']) for r in rows]
vol = np.array([eff[p][0]/eff[p][2]*36 for p in pids]); rate = np.array([(eff[p][1]+k*mu)/(eff[p][0]+k) for p in pids])
poss_e = np.array([eff[p][0] for p in pids]); ok = poss_e >= 50
pv = rankdata(vol, 'average')/len(vol); pa = rankdata(rate[ok], 'average')/ok.sum()
zv = (pv-pv.mean())/pv.std(); za = np.zeros(len(pids)); za[ok] = (pa-pa.mean())/pa.std()
rho = float(np.corrcoef(zv, za)[0,1]); print('rho', rho, F['rho'])
raw = (0.5*zv+0.5*za)/math.sqrt(0.5+0.5*rho)   # w^2+(1-w)^2 = .5 ; 2w(1-w)=.5
# 池
H, R = rs(json.loads((ROOT/'data/benchmark-source/base.json').read_text(encoding='utf-8')))
b = {int(r[H.index('PLAYER_ID')]): (float(r[H.index('GP')]), float(r[H.index('MIN')])) for r in R}
pool = [raw[i] for i, p in enumerate(pids) if b[p][0] >= 30 and b[p][1]/max(b[p][0],1) >= 20]
class M(L.PctMapper):
    def __init__(self, v):
        self.pool = L.Pool(v); s = self.pool.s; pc = self.pool.pct(s)
        r90, r99 = float(s[pc>=90].min()), float(s[pc>=99].min()); sd = float(np.std(s)); gap = (r99-r90)/L.Z9990
        self.an = {'r90': r90, 'r99': r99, 'r1': float(s.min()), 'SD_pool': sd, 'gapScale': gap, 'S': max(gap, sd), 'poolN': self.pool.n}; self.top, self.bot = True, False
attr = M(pool)(raw)
csvv = np.array([float(r['pnr']) for r in rows])
d = np.abs(attr-csvv); print('N', len(pids), 'pool', len(pool), 'max|d| pnr', d.max(), 'mean', d.mean(), 'argmax', rows[int(d.argmax())]['name'])
print('max|d| poss', np.abs(poss_e-np.array([float(r['poss']) for r in rows])).max(), ' vol', np.abs(vol-np.array([float(r['vol']) for r in rows])).max(), ' rate', np.abs(rate-np.array([float(r['rate']) for r in rows])).max())
# (B) 只用 csv 的 poss/vol/rate 算
vol2 = np.array([float(r['vol']) for r in rows]); rate2 = np.array([float(r['rate']) for r in rows]); ok2 = np.array([float(r['poss']) for r in rows]) >= 50
pv2 = rankdata(vol2,'average')/len(vol2); pa2 = rankdata(rate2[ok2],'average')/ok2.sum()
zv2=(pv2-pv2.mean())/pv2.std(); za2=np.zeros(len(rows)); za2[ok2]=(pa2-pa2.mean())/pa2.std(); rho2=float(np.corrcoef(zv2,za2)[0,1])
raw2=(0.5*zv2+0.5*za2)/math.sqrt(0.5+0.5*rho2)
pool2=[raw2[i] for i,p in enumerate(pids) if b[p][0]>=30 and b[p][1]/max(b[p][0],1)>=20]
attr2=M(pool2)(raw2); d2=np.abs(attr2-csvv); print('csv-only max|d|', d2.max(), 'n>1e-6', int((d2>1e-6).sum()))
for i in np.linspace(0, len(rows)-1, 20).astype(int): print(f"  {rows[i]['name'][:22]:22s} csv {csvv[i]:8.3f} re {attr2[i]:8.3f} raw-src {attr[i]:8.3f} poss {poss_e[i]:.0f}")
print('n poss<50', int((~ok).sum()), 'pnr dist', np.percentile(csvv,[0,10,50,90,100]).round(1))
i=int(d2.argmax()); print('csv-only worst', rows[i]['name'], rows[i]['poss'], csvv[i], attr2[i])
# 用精確 poss (來源重算) 當門檻重做 csv-only
ok3 = poss_e >= 50
print('gate mismatches csv-rounded vs exact', int((ok3!=ok2).sum()), [rows[j]['name']+' '+rows[j]['poss'] for j in np.where(ok3!=ok2)[0]])
print('TyTy exact', poss_e[i], vol[i], rows[i]['vol'])
tiny = np.where((poss_e>0)&(poss_e<0.01))[0]; zero = np.where(poss_e==0)[0]
print('tiny-poss (<0.01, >0):', len(tiny), 'exact-zero:', len(zero))
print('tiny pnr:', sorted(round(float(csvv[j]),1) for j in tiny)[:40]); print('zero pnr unique', set(round(float(csvv[j]),2) for j in zero))
print('tiny names', [(rows[j]['name'], round(float(csvv[j]),1)) for j in tiny])
