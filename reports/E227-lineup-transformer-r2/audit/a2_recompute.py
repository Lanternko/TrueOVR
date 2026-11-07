"""稽核 A2：獨立重算判定 1／2。特徵張量、指標、bootstrap 都是稽核者自己寫的；
只重用凍結的權重檔與網路結構類別 LineupNet（無法不用）。不 import e227_eval／e227_model.tensors。
python -I -X utf8 a2_recompute.py"""
import sys, os, hashlib, json
import csv, gzip
import numpy as np, torch
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(R))
sys.path.insert(0, R)
from e227_model import LineupNet            # 只取結構
from e227_common import ATTRS, STATS
torch.set_num_threads(6)
SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
ARMS = {'R2-abil': (0, 0), 'R2-stats': (1, 0), 'R2-stats-rapm': (1, 1)}   # (用統計, 用RAPM)


def rd(path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([r[k] for r in rows]) for k in rows[0]} if rows else {}


def num(a):
    return np.array([float(x) if x != '' else np.nan for x in a])


def h(tag, gid, m):
    return int(hashlib.sha256(f'E225|{tag}|{gid}'.encode()).hexdigest()[:8], 16) % m


# ---- 1) 測試列：E-225 完整 stints，依雜湊重切 ----
NUMC = ['possa', 'possb', 'ptsa', 'ptsb', 'tova', 'tovb', 'orba', 'orbb', 'rebOppa', 'rebOppb']
PC = [f'{x}{j}' for x in 'ab' for j in range(5)]
parts = []
for s in SEASONS:
    d = rd(os.path.join(ROOT, 'reports/E225-lineup-transformer/data', f'stints-{s}.csv.gz'))
    keep = np.array([h('test', g, 100) < 20 for g in d['gid']])
    e = {k: v[keep] for k, v in d.items()}; e['season'] = np.array([s] * keep.sum()); parts.append(e)
T = {k: np.concatenate([p[k] for p in parts]) for k in parts[0] if all(k in p for p in parts)}
for k in NUMC: T[k] = num(T[k])
NT = len(T['gid'])
print('test stints', NT, 'games', len(set(T['gid'])), 'by season', {s: len(set(T['gid'][T['season'] == s])) for s in SEASONS})

# ---- 2) 季均：E227 data 的 train 列、fold!=0 ----
means = {}
for s in SEASONS:
    d = rd(os.path.join(R, 'data', f'stints-train-{s}.csv.gz')); assert (d['split'] == 'train').all()
    fo = np.array([h('fold', g, 5) for g in d['gid']]); assert (fo == d['fold'].astype(int)).all(), 'fold 欄位與雜湊不一致'
    assert not (set(d['gid']) & set(T['gid'][T['season'] == s])), 'train/test 場次交集'
    m = fo != 0
    means[s] = (num(d['ptsa'])[m].sum() + num(d['ptsb'])[m].sum()) / (num(d['possa'])[m].sum() + num(d['possb'])[m].sum())
print('season means', {k: round(v, 5) for k, v in means.items()})
print('train/test game overlap: none (asserted)')


# ---- 3) 球員特徵 ----
def table(s):
    p = rd(os.path.join(R, 'data', f'players-{s}.csv')); st = rd(os.path.join(R, 'data', f'stats-{s}.csv'))
    t = {}
    for i, pid in enumerate(p['pid']): t.setdefault(pid, {}).update({c: num(p[c][i:i + 1])[0] for c in ATTRS})
    for i, pid in enumerate(st['pid']): t.setdefault(pid, {}).update({c: num(st[c][i:i + 1])[0] for c in STATS})
    return t


def zt(s, cols):
    """pid -> float32[len(cols)] z（缺值 NaN）；樣本<10 或常數的欄整欄缺。"""
    t = table(s); M = {pid: np.full(len(cols), np.nan) for pid in t}
    for j, c in enumerate(cols):
        ids = [p for p in t if not np.isnan(t[p].get(c, np.nan))]; v = np.array([t[p][c] for p in ids])
        if len(v) < 10 or v.std() < 1e-9:
            continue
        for p, x in zip(ids, v): M[p][j] = (x - v.mean()) / v.std()
    return M


def rapm(s, key):
    r = rd(os.path.join(R, 'data', f'rapm-{s}-excl{key}.csv')); o, dd, ex = num(r['off']), num(r['def']), num(r['exposed'])
    return {p: (o[i], dd[i]) for i, p in enumerate(r['pid']) if ex[i] > 0}


def build(use_stats, use_rapm):
    cols = ATTRS + (STATS if use_stats else []); F0 = len(cols); F = F0 + 2 * use_rapm
    X = np.zeros((NT, 10, 2 * F), np.float32)
    for s in SEASONS:
        idx = np.where(T['season'] == s)[0]
        Z = zt(s, cols); Rp = rapm(s, 'none') if use_rapm else None
        for t, pc in enumerate(PC):
            for i in idx:
                pid = T[pc][i]; z = Z.get(pid)
                if z is not None:
                    X[i, t, :F0] = np.nan_to_num(z); X[i, t, F:F + F0] = ~np.isnan(z)
                if use_rapm and pid in Rp:
                    X[i, t, F0], X[i, t, F0 + 1] = Rp[pid]; X[i, t, F + F0] = X[i, t, F + F0 + 1] = 1
    return torch.from_numpy(X), F


pos = torch.from_numpy(np.stack([T['p' + c].astype(np.int64) for c in PC], 1))
side = torch.from_numpy(np.tile(np.r_[np.zeros(5), np.ones(5)].astype(np.int64), (NT, 1)))
sig = lambda x: 1 / (1 + np.exp(-x))
PRED = {}
for arm, (us, ur) in ARMS.items():
    X, F = build(us, ur); outs = []
    for sd in range(5):
        net = LineupNet(F); net.load_state_dict(torch.load(os.path.join(R, 'results/weights', f'{arm}-{sd}.pt'), map_location='cpu')); net.eval()
        with torch.no_grad():
            outs.append(torch.cat([net(X[b:b + 4096], pos[b:b + 4096], side[b:b + 4096]) for b in range(0, len(X), 4096)]).numpy())
    O = np.stack(outs)   # [5,N,2,3]
    PRED[arm] = (O[..., 0].mean(0), sig(O[..., 1]).mean(0), sig(O[..., 2]).mean(0))
    print(arm, 'features', F, 'done', flush=True)

# ---- 4) 指標 ----
possA, possB = T['possa'], T['possb']; Pw = (possA + possB) / 2
mean = np.array([means[s] for s in T['season']])
actual = np.where(Pw > 0, 100 * (T['ptsa'] - T['ptsb']) / np.maximum(Pw, 1e-9), 0.0)
games = np.unique(T['gid'], return_inverse=True)[1]
_, first = np.unique(T['gid'], return_index=True)
# 與凍結腳本相同的場次順序（依第一次出現）
order = np.argsort(first); rank = np.empty_like(order); rank[order] = np.arange(len(order)); games = rank[games]; G = games.max() + 1
poss2 = np.stack([possA, possB], 1); pts2 = np.stack([T['ptsa'], T['ptsb']], 1); tov2 = np.stack([T['tova'], T['tovb']], 1)
orb2 = np.stack([T['orba'], T['orbb']], 1); opp2 = np.stack([T['rebOppa'], T['rebOppb']], 1)
rate = np.where(poss2 > 0, pts2 / np.maximum(poss2, 1e-9), mean[:, None]) - mean[:, None]


def ll(p, k, n):
    p = np.clip(p, 1e-5, 1 - 1e-5); k = np.minimum(k, n); return np.where(n > 0, -(k * np.log(p) + (n - k) * np.log(1 - p)), 0.0)


def bc(w):
    return np.bincount(games, w, G)


def stats_for(pr):
    pts, ptov, porb = pr
    pred = 100 * ((pts[:, 0] + mean) * possA - (pts[:, 1] + mean) * possB) / np.maximum(Pw, 1e-9)
    return {'net': (bc(Pw * (actual - pred) ** 2), bc(Pw)),
            'ptsSide': (bc((poss2 * (rate - pts) ** 2).sum(1)), bc(poss2.sum(1))),
            'tovLL': (bc(ll(ptov, tov2, poss2).sum(1)), bc(poss2.sum(1))),
            'orbLL': (bc(ll(porb, orb2, opp2).sum(1)), bc(opp2.sum(1)))}


S = {a: stats_for(p) for a, p in PRED.items()}
S['B0'] = {'net': stats_for((np.zeros((NT, 2)), np.full((NT, 2), .1), np.full((NT, 2), .1)))['net']}


def val(a, m):
    return S[a][m][0].sum() / S[a][m][1].sum()


print('MSE', {a: round(val(a, 'net'), 2) for a in S})


def boot(seed, B=2000):
    rng = np.random.default_rng(seed)
    return np.stack([np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(B)]).astype(float)


def paired(a, b, m, D):
    na, da = S[a][m]; nb, db = S[b][m]
    d = (D @ na) / (D @ da) - (D @ nb) / (D @ db); lo, hi = np.percentile(d, [5, 95])
    return dict(point=val(a, m) - val(b, m), lo=float(lo), hi=float(hi), hw=float((hi - lo) / 2))


out = {}
for seed in (20261103, 777):
    D = boot(seed); out[seed] = {}
    for a, mde, thr in (('R2-stats', 15.36, (0.00050, 0.00024, 0.00066)), ('R2-stats-rapm', 14.208, (0.00048, 0.00024, 0.00064))):
        j1 = paired(a, 'R2-abil', 'net', D); g = {m: paired(a, 'R2-abil', m, D) for m in ('ptsSide', 'tovLL', 'orbLL')}
        out[seed][a] = dict(j1=j1, guard=g, j1pass=bool(j1['point'] <= -mde and j1['hi'] < 0),
                            j2={m: bool(g[m]['point'] <= -t) for m, t in zip(('ptsSide', 'tovLL', 'orbLL'), thr)})
        print(seed, a, json.dumps(out[seed][a], ensure_ascii=False, default=float))
json.dump({'mse': {a: val(a, 'net') for a in S}, 'res': {str(k): v for k, v in out.items()}}, open(os.path.join(HERE, 'a2_result.json'), 'w'), indent=1, default=float)
np.savez(os.path.join(HERE, 'a2_pred.npz'), **{a: np.stack(p) for a, p in PRED.items()})
