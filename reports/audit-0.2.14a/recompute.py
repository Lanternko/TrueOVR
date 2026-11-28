"""role-audit 0.2.14a（E-294 H-same）：獨立重算 MIX 加分、鑑別度、代表名次、一致度。
不 import e294_eval／build_cand；只讀原始特徵（mix-pool-card0214.json）與卡片 0.2.13a。
用法（repo root）：python -I -B -X utf8 reports/audit-0.2.14a/recompute.py
"""
import csv, json, re, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
R = lambda p: ROOT / p
card = list(csv.DictReader(open(R('reports/card-0.2.13a/ranking.csv'), encoding='utf-8')))
fz = json.load(open(R('reports/ovr-inseason-2026-27/live/mix-pool-card0214.json'), encoding='utf-8'))
cfg = fz['config']
byname = {v['name']: v for v in fz['players'].values()}
pid = {v['name']: k for k, v in fz['players'].items()}


def nm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', ' ', s)
    return ' '.join(w for w in s.split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv'))


cnt = {}
for r in csv.DictReader(open(R('reports/E227-lineup-transformer-r2/data/stats-2025-26.csv'), encoding='utf-8')):
    cnt[nm(r['name'])] = cnt.get(nm(r['name']), 0) + 1

N = len(card)
name = [r['name'] for r in card]
pos = np.array([r['pos'] for r in card])
MIN = np.array([float(r['MIN']) for r in card])
ovr0 = np.array([float(r['ovr']) for r in card])
rk0 = np.array([int(r['rank']) for r in card])
pool = (MIN >= 500) & np.array([cnt.get(nm(n), 0) == 1 for n in name])
EP = MIN >= 500


def col(k):
    v = np.array([np.nan if byname[n][k] is None else byname[n][k] for n in name], float)
    return v


F = {'rebound': np.array([byname[n]['cardRebound'] for n in name], float),
     'orebPct': col('orebPct'), 'drebPct': col('drebPct'), 'con2_36': col('con2_36')}

# 0. 人群核對：我算的全聯盟 μ/σ 要等於凍結檔
for k, v in F.items():
    ok = pool & np.isfinite(v)
    mu, sd = v[ok].mean(), v[ok].std()
    assert abs(mu - cfg['z'][k]['mu']) < 1e-9 and abs(sd - cfg['z'][k]['sd']) < 1e-9, (k, mu, sd, cfg['z'][k])
assert pool.sum() == fz['epN']

PW = {'C': 1.0, 'PF': 0.68 / 2.80}


def bonus_arm(alpha, soft, weighted):
    """alpha=None：全聯盟 z（現行）；alpha=a：每個特徵 z_L 減去 (1-a)·該位置在 pool 的 z_L 平均（缺值記 a·m_pos）。"""
    Z = {}
    for k, v in F.items():
        ok = np.isfinite(v)
        mu, sd = cfg['z'][k]['mu'], cfg['z'][k]['sd']
        z = np.where(ok, (np.nan_to_num(v) - mu) / sd, 0.0)
        if alpha is not None:
            for p in set(pos):
                g = pos == p
                m = z[g & ok & pool].mean()
                z = np.where(g & ok, z - (1 - alpha) * m, z)
                z = np.where(g & ~ok, alpha * m, z)
        Z[k] = z
    zr = (Z['rebound'] + Z['orebPct'] + Z['drebPct']) / 3
    zc = Z['con2_36']
    f = (lambda x: 1.5 * np.tanh(np.clip(x, 0, None) / 1.5)) if soft else (lambda x: np.clip(x, 0, 1.5))
    a, b = f(zr), f(zc)
    ref = cfg['ref']
    rms = lambda x: np.sqrt(np.mean(x[pool] ** 2))
    sa, sb = ref / rms(a), ref / rms(b)
    m0 = .5 * a * sa + .5 * b * sb
    sm = ref / rms(m0)
    w = np.array([PW.get(p, 0.0) for p in pos]) if weighted else np.ones(N)
    full = cfg['lambda'] * cfg['sd'] * m0 * sm * w
    cap = cfg['lambda'] * cfg['sd'] * (.75 * sa + .75 * sb) * sm * w
    ramp = np.minimum(1, MIN / 500)
    return full * ramp, cap, dict(zr=zr, zc=zc, sa=sa, sb=sb, sm=sm, full=full)


A, capA, partsA = bonus_arm(None, False, False)
H, capH, partsH = bonus_arm(0.5, True, True)

out = {}
# 1. 加分比對
c14 = {r['name']: float(r['mixBonus']) for r in csv.DictReader(open(R('reports/card-0.2.14/ranking.csv'), encoding='utf-8'))}
out['A_vs_card0214_maxabs'] = float(max(abs(A[i] - c14[n]) for i, n in enumerate(name)))
npz = np.load(R('reports/E294-mix-pos-z-soft/bonus_pick.npz'))
assert list(npz['names']) == name
out['H_vs_npz_maxabs'] = float(np.abs(H - npz['bonus']).max())
cand = {r['name']: r for r in csv.DictReader(open(R('reports/card-0.2.15-cand/ranking.csv'), encoding='utf-8'))}
out['H_vs_cand_csv_maxabs'] = float(max(abs(H[i] - float(cand[n]['mixBonus'])) for i, n in enumerate(name)))
out['scales_H'] = {k: float(partsH[k]) for k in ('sa', 'sb', 'sm')}
# 各位置 m_pos（每個特徵，pool 內）
mp = {}
for k, v in F.items():
    ok = np.isfinite(v)
    z = (np.nan_to_num(v) - cfg['z'][k]['mu']) / cfg['z'][k]['sd']
    mp[k] = {p: round(float(z[(pos == p) & ok & pool].mean()), 3) for p in ('PG', 'SG', 'SF', 'PF', 'C')}
    mp[k]['nC'] = int(((pos == 'C') & ok & pool).sum())
out['m_pos'] = mp


# 2. 名次與鑑別度
def rank_of(b):
    o = np.round(ovr0 + b, 1)
    order = sorted(range(N), key=lambda i: (-o[i], rk0[i]))
    r = np.empty(N, int); r[order] = np.arange(1, N + 1)
    return o, r


def disc(b, cap, o, r):
    near = EP & (cap > 0) & (b >= cap - 0.2)
    top30 = np.sort(b[EP])[::-1][:30]
    _, c30 = np.unique(np.round(top30, 1), return_counts=True)
    _, c50 = np.unique(o[r <= 50], return_counts=True)
    cb = b[EP & (pos == 'C')]
    return {'near_cap': int(near.sum()), 'near90pct_cap': int((EP & (cap > 0) & (b >= 0.9 * cap)).sum()),
            'top30_max_tie': int(c30.max()), 'top50_tie_groups': int((c50 >= 2).sum()),
            'C_mean': round(float(cb.mean()), 3), 'C_sd': round(float(cb.std()), 3),
            'C_iqr': round(float(np.percentile(cb, 75) - np.percentile(cb, 25)), 3), 'nC': int(cb.size),
            'max': round(float(b.max()), 2), 'cap_C': round(float(cap[pos == 'C'].max()), 2), 'min': round(float(b.min()), 4)}


oA, rA = rank_of(A); oH, rH = rank_of(H); o0, r0 = rank_of(np.zeros(N))
out['disc_A'] = disc(A, capA, oA, rA); out['disc_H'] = disc(H, capH, oH, rH)
# 卡片 csv 名次對得上
out['cand_rank_mismatch'] = [n for i, n in enumerate(name) if int(cand[n]['rank']) != rH[i]]

SHOW = ['Joel Embiid', 'Anthony Davis', 'Karl-Anthony Towns', 'Rudy Gobert', 'Jarrett Allen', 'Domantas Sabonis', 'Ivica Zubac',
        'Zach Edey', 'Chet Holmgren', 'Evan Mobley', 'Alperen Sengun', 'Bam Adebayo', 'Isaiah Hartenstein', 'Victor Wembanyama',
        'Nikola Jokić', 'Donovan Clingan']
ix = {n: i for i, n in enumerate(name)}
out['show'] = {n: {'pos': pos[ix[n]], 'MIN': MIN[ix[n]], 'rank0213a': int(r0[ix[n]]), 'rankA': int(rA[ix[n]]), 'rankH': int(rH[ix[n]]),
                   'bonusA': round(float(A[ix[n]]), 2), 'bonusH': round(float(H[ix[n]]), 2),
                   'zr': round(float(partsA['zr'][ix[n]]), 2), 'zc': round(float(partsA['zc'][ix[n]]), 2)} for n in SHOW}
top = lambda r: [name[i] for i in np.argsort(r)[:10]]
out['top10'] = {'0213a': top(r0), 'A': top(rA), 'H': top(rH)}
out['rank11_15_H'] = [(name[i], pos[i]) for i in np.argsort(rH)[10:15]]
out['top30_0213a_drop_gt10_H'] = [(name[i], int(r0[i]), int(rH[i])) for i in range(N) if r0[i] <= 30 and rH[i] - r0[i] > 10]
out['top30_0213a_drop_gt5_H'] = [(name[i], int(r0[i]), int(rH[i])) for i in range(N) if r0[i] <= 30 and rH[i] - r0[i] > 5]
out['top_bonus_H'] = [(name[i], pos[i], MIN[i], round(float(H[i]), 2), round(float(partsA['zr'][i]), 2), round(float(partsA['zc'][i]), 2))
                      for i in np.argsort(-H)[:12]]

# 3. 一致度（獨立）：T 淨值、EPM（poss≥200）、2K27
ts = json.load(open(R('reports/ovr-inseason-2026-27/live/2026-11-08/t-swap.json'), encoding='utf-8'))
T = {str(p): ts['ownPts100'][p] - ts['oppPts100'][p] for p in ts['pool']}
E = {r['playerId']: float(r['net']) for r in csv.DictReader(open(R('reports/impact-epm-2026-27/epm-live.csv'), encoding='utf-8'))
     if float(r['poss2627'] or 0) >= 200}
K = {}
for r in csv.DictReader(open(R('reports/ovr-v55-2k27-compare/2k27_ratings.csv'), encoding='utf-8-sig')):
    if r['overall2k']:
        K.setdefault(nm(r['name']), float(r['overall2k']))
ref = {'T': [T.get(pid[n]) for n in name], 'EPM': [E.get(pid[n]) for n in name], '2K': [K.get(nm(n)) for n in name]}
out['rho'] = {}
for s, y in ref.items():
    k = [i for i in range(N) if y[i] is not None]
    yy = np.array([y[i] for i in k])
    out['rho'][s] = {'n': len(k), '0213a': round(spearmanr(o0[k], yy)[0], 4), 'A': round(spearmanr(oA[k], yy)[0], 4),
                     'H': round(spearmanr(oH[k], yy)[0], 4)}
    out['rho'][s]['H-A'] = round(out['rho'][s]['H'] - out['rho'][s]['A'], 4)

# 4. 邊界：單調性（固定位置與縮放下，加分對 zr、zc 非遞減）、負加分、少分鐘
out['n_negative_H'] = int((H < -1e-12).sum())
zz = np.linspace(-3, 6, 2001); g = 1.5 * np.tanh(np.clip(zz, 0, None) / 1.5)
out['soft_monotone'] = bool(np.all(np.diff(g) >= -1e-15))
lo = (MIN < 500) & (H > 3)
out['low_min_bonus_gt3'] = [(name[i], pos[i], MIN[i], round(float(H[i]), 2)) for i in np.where(lo)[0]]
# 缺 con 的中鋒（H 會給 a·m_pos 而非 0）
nocon = (pos == 'C') & ~np.isfinite(F['con2_36'])
out['C_missing_con'] = [(name[i], MIN[i], round(float(A[i]), 2), round(float(H[i]), 2)) for i in np.where(nocon)[0]]
noreb = ~np.isfinite(F['orebPct']) & (pos == 'C')
out['C_missing_obdb'] = [(name[i], MIN[i], round(float(H[i]), 2)) for i in np.where(noreb)[0]]
# PF/C 兩棲：假如位置標籤換成另一個，加分差多少（全分鐘）
amp = []
for i in np.where(EP & np.isin(pos, ['PF', 'C']))[0]:
    alt = 'C' if pos[i] == 'PF' else 'PF'
    pos_save = pos[i]; pos[i] = alt
    Halt, _, _ = bonus_arm(0.5, True, True)
    pos[i] = pos_save
    amp.append((name[i], pos_save, round(float(H[i]), 2), round(float(Halt[i]), 2)))
amp.sort(key=lambda x: -abs(x[3] - x[2]))
out['pos_flip_top'] = amp[:12]
out['pos_flip_median_abs'] = float(np.median([abs(a[3] - a[2]) for a in amp]))

Path(__file__).with_name('recompute.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
