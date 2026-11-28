"""role-audit 0.2.14b（E-295 W1）：獨立重算 MIX 加分（BBRef 連續位置比例）、比例資料對名、斷崖／連續／單調、
errata-1 G2 各種定義、鑑別度、前十、掉名、一致度。
不 import e295_eval／errata_g2／build_cand；只讀原始檔：card 0.2.13a、mix-pool-card0214.json（原始特徵＋z 尺）、
BBRef pos-shares-*.csv、card-0.2.14a、T／EPM／2K 參考檔。
用法（repo root）：python -I -B -X utf8 reports/audit-0.2.14b/recompute.py
"""
import csv, json, re, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
R = lambda p: ROOT / p
OUT = {}

# ---------------------------------------------------------------- 原始資料
card = list(csv.DictReader(open(R('reports/card-0.2.13a/ranking.csv'), encoding='utf-8')))
fz = json.load(open(R('reports/ovr-inseason-2026-27/live/mix-pool-card0214.json'), encoding='utf-8'))
cfg = fz['config']
pid_by_name = {v['name']: k for k, v in fz['players'].items()}
name = [r['name'] for r in card]; N = len(name)
pid = [pid_by_name[n] for n in name]
pos = np.array([r['pos'] for r in card])
MIN = np.array([float(r['MIN']) for r in card]); HGT = np.array([float(r['heightInches']) for r in card])
ovr0 = np.array([float(r['ovr']) for r in card]); rk0 = np.array([int(r['rank']) for r in card])
P5 = ['PG', 'SG', 'SF', 'PF', 'C']
WP = np.array([0, 0, 0, 0.68 / 2.80, 1.0])


def nm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', ' ', s)
    return ' '.join(w for w in s.split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv'))


cnt = {}
for r in csv.DictReader(open(R('reports/E227-lineup-transformer-r2/data/stats-2025-26.csv'), encoding='utf-8')):
    cnt[nm(r['name'])] = cnt.get(nm(r['name']), 0) + 1
EP = MIN >= 500
pool = EP & np.array([cnt.get(nm(n), 0) == 1 for n in name])
assert pool.sum() == fz['epN']
F = {'reb': np.array([fz['players'][p]['cardRebound'] for p in pid], float)}
for k, src in (('ob', 'orebPct'), ('db', 'drebPct'), ('con', 'con2_36')):
    F[k] = np.array([np.nan if fz['players'][p][src] is None else fz['players'][p][src] for p in pid], float)
ZK = {'reb': 'rebound', 'ob': 'orebPct', 'db': 'drebPct', 'con': 'con2_36'}

# ---------------------------------------------------------------- BBRef 比例（自己讀）
BB = R('reports/card-0.2.9a+E177-bbref-position-shares')
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
SH, RAW = {}, {}
for s in SEAS:
    SH[s], RAW[s] = {}, {}
    for r in csv.DictReader(open(BB / f'pos-shares-{s}.csv', encoding='utf-8')):
        RAW[s].setdefault(r['playerId'], []).append(r)
        if not r['playerId']:
            continue
        v = np.array([float(r['p_' + p]) for p in P5])
        if v.sum() > 0:
            SH[s][r['playerId']] = (v / v.sum(), float(r['MP']))

# 對名稽核：卡片名 vs BBRef 名、重複 playerId、交易球員
cur = SH['2025-26']
mm = []
dup_pid = {k: len(v) for k, v in RAW['2025-26'].items() if k and len(v) > 1}
bbname = {r['playerId']: r for rs in RAW['2025-26'].values() for r in rs if r['playerId']}
for i, n in enumerate(name):
    r = bbname.get(pid[i])
    if r and nm(r['name']).replace(' ', '') != nm(n).replace(' ', ''):
        mm.append((n, r['name'], r['bbref_id']))
OUT['bbref_name_mismatch_2025_26'] = mm
OUT['bbref_dup_playerId_2025_26'] = dup_pid
OUT['bbref_unmatched_rows'] = {s: [(r['name'], r['match'], r['MP']) for r in RAW[s].get('', [])] for s in SEAS}
OUT['card_not_in_bbref_2025_26'] = [(n, pos[i], MIN[i], HGT[i]) for i, n in enumerate(name) if pid[i] not in cur]
traded = [(n, bbname[pid[i]]['team'], bbname[pid[i]]['MP']) for i, n in enumerate(name)
          if pid[i] in bbname and re.fullmatch(r'\d+TM', bbname[pid[i]]['team'] or '')]
OUT['traded_2TM_rows_n'] = len(traded)
# 卡片 MIN 與 BBRef MP 是否同一人（同季分鐘應相近）
gap = [(n, MIN[i], cur[pid[i]][1]) for i, n in enumerate(name) if pid[i] in cur and abs(MIN[i] - cur[pid[i]][1]) > 150]
OUT['card_MIN_vs_bbref_MP_gt150'] = gap
OUT['traded_MP_check'] = [t for t in traded if t[0] in [g[0] for g in gap]]

# 身高帶（自己重寫）：卡片有 2025-26 BBRef 且 MP≥200 的人；±1 吋，不足 15 人放寬
hp_mask = np.array([pid[i] in cur and cur[pid[i]][1] >= 200 for i in range(N)])
HP_H = HGT[hp_mask]; HP_PI = np.array([cur[pid[i]][0] for i in np.where(hp_mask)[0]])


def prior(h):
    for k in (1, 2, 3, 4, 5, 8):
        m = np.abs(HP_H - h) <= k
        if m.sum() >= 15:
            return HP_PI[m].mean(0)
    return HP_PI.mean(0)


PI = np.zeros((N, 5)); SRC = []
for i in range(N):
    ph = prior(HGT[i]); row = cur.get(pid[i]); tag = '2025-26'
    if row is None:
        for s in ('2024-25', '2023-24', '2022-23'):
            if pid[i] in SH[s]:
                row = SH[s][pid[i]]; tag = s; break
    if row is None:
        PI[i] = ph; SRC.append('height'); continue
    v, mp = row
    PI[i] = v if mp >= 200 else (mp * v + (200 - mp) * ph) / 200
    SRC.append(tag if mp >= 200 else tag + '+shrink')
OUT['src_counts'] = {s: SRC.count(s) for s in sorted(set(SRC))}
OUT['height_only'] = [(name[i], pos[i], MIN[i], HGT[i]) for i in range(N) if SRC[i] == 'height']
OUT['earlier_season_src'] = [(name[i], SRC[i]) for i in range(N) if not SRC[i].startswith('2025-26') and SRC[i] != 'height']
OUT['height_prior_n_pool'] = int(hp_mask.sum())
OUT['height_prior_c'] = {h: round(float(prior(h) @ WP), 3) for h in range(74, 90)}


# ---------------------------------------------------------------- 公式（自己重寫）
def soft(x):
    return 1.5 * np.tanh(np.clip(x, 0, None) / 1.5)


def zL(k):
    v = F[k]; ok = np.isfinite(v)
    mu, sd = cfg['z'][ZK[k]]['mu'], cfg['z'][ZK[k]]['sd']
    assert abs(v[ok & pool].mean() - mu) < 1e-9 and abs(v[ok & pool].std() - sd) < 1e-9
    return np.where(ok, (np.nan_to_num(v) - mu) / sd, 0.0), ok


ZL = {k: zL(k) for k in F}


def fit(PIm):
    mp = {}
    for k, (z, ok) in ZL.items():
        g = pool & ok
        mp[k] = (PIm[g] * z[g, None]).sum(0) / PIm[g].sum(0)
    return mp


def bonus(PIm, w, mp=None, scales=None, idx=None):
    """回傳 (bonus, cap, mp, scales, zr, zc)；mp／scales 給定就固定（反事實）。"""
    if mp is None:
        mp = fit(PIm)
    zh = {}
    for k, (z, ok) in ZL.items():
        mi = PIm @ mp[k]
        zh[k] = np.where(ok, z - 0.5 * mi, 0.5 * mi)
    zr = (zh['reb'] + zh['ob'] + zh['db']) / 3; zc = zh['con']
    a, b = soft(zr), soft(zc)
    if scales is None:
        rms = lambda x: np.sqrt(np.mean(x[pool] ** 2))
        sa, sb = cfg['ref'] / rms(a), cfg['ref'] / rms(b)
        sm = cfg['ref'] / rms(.5 * a * sa + .5 * b * sb)
        scales = (sa, sb, sm)
    sa, sb, sm = scales
    full = cfg['lambda'] * cfg['sd'] * (.5 * a * sa + .5 * b * sb) * sm * w
    cap = cfg['lambda'] * cfg['sd'] * (.75 * sa + .75 * sb) * sm * w
    return full * np.minimum(1, MIN / 500), cap, mp, scales, zr, zc


onehot = lambda lab: np.array([[1.0 if l == p else 0.0 for p in P5] for l in lab])
PIL = onehot(pos)
A, capA, mpA, scA, _, _ = bonus(PIL, PIL @ WP)
c = PI @ WP
W, capW, mpW, scW, zrW, zcW = bonus(PI, c)

# 1. 比對
c14a = {r['name']: r for r in csv.DictReader(open(R('reports/card-0.2.14a/ranking.csv'), encoding='utf-8'))}
OUT['A_vs_card0214a_maxabs'] = float(max(abs(A[i] - float(c14a[n]['mixBonus'])) for i, n in enumerate(name)))
npz = np.load(R('reports/E295-mix-pos-continuous/bonus_pick.npz'))
assert list(npz['names']) == name
OUT['npz_pick'] = str(npz['pick'])
OUT['W1_vs_npz_maxabs'] = float(np.abs(W - npz['bonus']).max())
OUT['pi_vs_npz_maxabs'] = float(np.abs(PI - npz['pi']).max())
OUT['src_vs_npz_mismatch'] = [name[i] for i in range(N) if SRC[i] != str(npz['src'][i])]
cand = {r['name']: r for r in csv.DictReader(open(R('reports/card-0.2.14b-cand/ranking.csv'), encoding='utf-8'))}
OUT['W1_vs_cand_csv_maxabs'] = float(max(abs(W[i] - float(cand[n]['mixBonus'])) for i, n in enumerate(name)))
OUT['c_vs_cand_csv_maxabs'] = float(max(abs(c[i] - float(cand[n]['cShare'])) for i, n in enumerate(name)))
mpc = json.load(open(R('reports/card-0.2.14b-cand/mix-pool-cand.json'), encoding='utf-8'))
OUT['frozen_mpos_vs_mine_maxabs'] = float(max(np.abs(np.array(mpc['mpos'][k]) - mpW[k]).max() for k in mpW))
OUT['frozen_scales_vs_mine'] = [mpc['scales']['reb'] - scW[0], mpc['scales']['con'] - scW[1], mpc['scales']['mix'] - scW[2]]
OUT['frozen_pi_vs_mine_maxabs'] = float(max(np.abs(np.array(mpc['players'][pid[i]]['pi']) - PI[i]).max() for i in range(N)))
OUT['frozen_prior_vs_mine_maxabs'] = float(max(np.abs(np.array(v) - prior(int(h))).max() for h, v in mpc['heightPrior'].items()))
OUT['frozen_keys'] = list(mpc.keys())
# 用凍結檔單獨重建（模擬賽中接線：z 尺取 0214a 基底 config、其餘取 cand 檔）
PIf = np.array([mpc['players'][pid[i]]['pi'] for i in range(N)])
mpf = {k: np.array(mpc['mpos'][k]) for k in mpc['mpos']}
Wf = bonus(PIf, PIf @ WP, mpf, (mpc['scales']['reb'], mpc['scales']['con'], mpc['scales']['mix']))[0]
OUT['rebuild_from_frozen_vs_W1_maxabs'] = float(np.abs(Wf - W).max())


# ---------------------------------------------------------------- 名次
def rank_of(b):
    o = np.round(ovr0 + b, 1)
    order = sorted(range(N), key=lambda i: (-o[i], rk0[i])); r = np.empty(N, int); r[order] = np.arange(1, N + 1)
    return o, r


oA, rA = rank_of(A); oW, rW = rank_of(W)
OUT['cand_rank_mismatch'] = [n for i, n in enumerate(name) if int(cand[n]['rank']) != rW[i]]
OUT['top10_A'] = [name[i] for i in np.argsort(rA)[:10]]
OUT['top10_W1'] = [(name[i], round(float(oW[i]), 1), round(float(W[i]), 2)) for i in np.argsort(rW)[:12]]
OUT['top30A_drop_gt10'] = [(name[i], int(rA[i]), int(rW[i])) for i in range(N) if rA[i] <= 30 and rW[i] - rA[i] > 10]
OUT['top30A_drop_gt5'] = [(name[i], int(rA[i]), int(rW[i])) for i in range(N) if rA[i] <= 30 and rW[i] - rA[i] > 5]
OUT['top30_0213a_drop_gt10_W1'] = [(name[i], int(rk0[i]), int(rW[i])) for i in range(N) if rk0[i] <= 30 and rW[i] - rk0[i] > 10]
d = W - A
OUT['biggest_change'] = [(name[i], pos[i], round(float(c[i]), 2), round(float(A[i]), 2), round(float(W[i]), 2), int(rA[i]), int(rW[i]))
                         for i in np.argsort(-np.abs(d))[:15]]
OUT['n_changed_gt_0.5'] = int((np.abs(d) > 0.5).sum())

# 兩棲長人 10 位：比例、c、加分
BIGS = ['Chet Holmgren', 'Evan Mobley', 'Jaren Jackson Jr.', 'Bam Adebayo', 'Giannis Antetokounmpo', 'Anthony Davis',
        'Scottie Barnes', 'Domantas Sabonis', 'Alperen Sengun', 'Kristaps Porziņģis', 'Jabari Smith Jr.', 'Paolo Banchero',
        'Victor Wembanyama', 'Myles Turner', 'Naz Reid', 'Draymond Green', 'Julius Randle', 'Lauri Markkanen']
ix = {n: i for i, n in enumerate(name)}
OUT['bigs'] = {n: {'label': pos[ix[n]], 'src': SRC[ix[n]], 'MP': cur.get(pid[ix[n]], (None, None))[1],
                   'team': bbname.get(pid[ix[n]], {}).get('team'), 'pi%': [round(100 * float(x)) for x in PI[ix[n]]],
                   'c': round(float(c[ix[n]]), 3), 'bonusA': round(float(A[ix[n]]), 2), 'bonusW1': round(float(W[ix[n]]), 2),
                   'rankA': int(rA[ix[n]]), 'rankW1': int(rW[ix[n]])} for n in BIGS if n in ix}

# ---------------------------------------------------------------- 斷崖／連續／單調
# (a) 標籤不進 W1：任意打亂標籤，加分逐位元相同
rng = np.random.default_rng(7)
pos_save = pos.copy(); pos[:] = rng.permutation(pos)
Wperm = bonus(PI, PI @ WP)[0]
pos[:] = pos_save
OUT['label_permute_maxabs'] = float(np.abs(Wperm - W).max())
# (b) 同一人標 PF／C：W1 公式完全不含標籤 → 0；另做「把該人的 π 改成全 PF vs 全 C」看 one-hot 斷崖還剩多少（對照）


def one(i, pi_i, w_i):
    """單人反事實：尺、m_p、縮放固定在 W1 正式值。"""
    zh = {}
    for k, (z, ok) in ZL.items():
        mi = float(pi_i @ mpW[k])
        zh[k] = (z[i] - 0.5 * mi) if ok[i] else 0.5 * mi
    zr = (zh['reb'] + zh['ob'] + zh['db']) / 3
    sa, sb, sm = scW
    return float(cfg['lambda'] * cfg['sd'] * (.5 * soft(zr) * sa + .5 * soft(zh['con']) * sb) * sm * w_i * min(1, MIN[i] / 500))


chk = [abs(one(i, PI[i], c[i]) - W[i]) for i in range(N)]
OUT['one_vs_vector_maxabs'] = float(max(chk))
# (c) 全部 MIN≥500 且 PF+C>0：固定 PF+C 總量，C 佔比 0→1 每 0.5% 一步；最大相鄰跳動、是否單調、斜率
sweep = []
for i in np.where(EP & (PI[:, 3] + PI[:, 4] > 0.05))[0]:
    tot = PI[i, 3] + PI[i, 4]; vals = []
    for k in range(201):
        p = PI[i].copy(); p[4] = tot * k / 200; p[3] = tot - p[4]
        vals.append(one(i, p, float(p @ WP)))
    v = np.array(vals); dv = np.diff(v)
    sweep.append({'name': name[i], 'tot': round(float(tot), 2), 'max_step_per_1pct': float(np.abs(dv).max() * 2),
                  'monotone_up': bool((dv >= -1e-9).all()), 'min_dv': float(dv.min()), 'at0': round(float(v[0]), 2), 'at1': round(float(v[-1]), 2),
                  'peak_at': round(float(np.argmax(v) / 200), 3)})
OUT['sweep_n'] = len(sweep)
OUT['sweep_max_step_per_1pct'] = max(s['max_step_per_1pct'] for s in sweep)
nonmono = [s for s in sweep if not s['monotone_up']]
OUT['sweep_nonmonotone_n'] = len(nonmono)
OUT['sweep_nonmonotone_worst'] = sorted(nonmono, key=lambda s: s['at1'] - max(s['at0'], s['at1']) + (s['at1'] - s['at0']))[:10]
OUT['sweep_nonmonotone_biggest_drop'] = sorted([{**s, 'drop_from_peak': None} for s in nonmono], key=lambda s: s['min_dv'])[:10]
# 量化：從峰值掉到 C=100% 的幅度
for s in sweep:
    pass
# (d) c 本身（w 與 m 同時隨 c 動）：沿「PF→C」直線 c 單調，bonus 對 c 是否單調，已由 (c) 覆蓋；另報 bonus 為 0 → 正的轉折點連續性
OUT['sweep_examples'] = {s['name']: s for s in sweep if s['name'] in ('Chet Holmgren', 'Evan Mobley', 'Jaren Jackson Jr.', 'Bam Adebayo',
                                                                       'Giannis Antetokounmpo', 'Anthony Davis', 'Scottie Barnes', 'Kristaps Porziņģis')}

# ---------------------------------------------------------------- errata-1：G2 各種定義
def g2(b, cap, label):
    res = {}
    m0 = EP & (cap > 0)
    res['literal(cap>0, b>=cap-0.2)'] = int((m0 & (b >= cap - 0.2)).sum())
    res['literal_with_zero_bonus'] = int((m0 & (b >= cap - 0.2) & (b <= 0.05)).sum())
    for th in (0.5, 1.0, 2.0):
        m = EP & (cap >= th)
        res[f'cap>={th}, b>=cap-0.2'] = int((m & (b >= cap - 0.2)).sum())
    res['cap>0, b>0.05, b>=cap-0.2'] = int((m0 & (b > 0.05) & (b >= cap - 0.2)).sum())
    res['cap>0, b>=0.95cap, b>0.05'] = int((m0 & (b >= 0.95 * cap) & (b > 0.05)).sum())
    res['cap>0, b>=0.90cap, b>0.05'] = int((m0 & (b >= 0.90 * cap) & (b > 0.05)).sum())
    res['c>=0.5, b>=cap-0.2'] = int((m0 & (label >= 0.5) & (b >= cap - 0.2)).sum())
    # 前 30 加分同分群（到 0.1）
    t30 = np.sort(b[EP])[::-1][:30]; _, cc = np.unique(np.round(t30, 1), return_counts=True)
    res['top30_max_tie'] = int(cc.max())
    # 飽和：未打折 P 的 tanh 輸入 >2（tanh 斜率 <0.2）的人
    res['max_ratio_b_over_cap(cap>=1)'] = float((b[EP & (cap >= 1)] / cap[EP & (cap >= 1)]).max())
    lit = m0 & (b >= cap - 0.2) & (b > 0.05)
    res['literal_nonzero_names'] = [(name[i], round(float(c[i]), 3), round(float(b[i]), 3), round(float(cap[i]), 3)) for i in np.where(lit)[0]]
    return res


OUT['G2_defs'] = {'A': g2(A, capA, PIL @ WP), 'W1': g2(W, capW, c)}
# 碰頂本來要防的：上限附近擠在一起。看 c≥0.5 的人 b/cap 分布
for a, b_, cp, cc_ in (('A', A, capA, PIL @ WP), ('W1', W, capW, c)):
    m = EP & (cc_ >= 0.5)
    q = b_[m] / cp[m]
    OUT.setdefault('ratio_b_cap_bigs', {})[a] = {'n': int(m.sum()), 'p50': round(float(np.median(q)), 3), 'p90': round(float(np.percentile(q, 90)), 3),
                                                 'max': round(float(q.max()), 3)}


# ---------------------------------------------------------------- 鑑別度、同分
def ties50(o, r):
    _, cc = np.unique(o[r <= 50], return_counts=True); return int((cc >= 2).sum()), int(cc[cc >= 2].sum())


bigC = EP & (pos == 'C')
OUT['disc'] = {a: {'C_sd': round(float(b[bigC].std()), 3), 'C_mean': round(float(b[bigC].mean()), 3), 'ties50': ties50(o, r), 'max': round(float(b.max()), 2)}
               for a, b, o, r in (('A', A, oA, rA), ('W1', W, oW, rW))}

# ---------------------------------------------------------------- 一致度
ts = json.load(open(R('reports/ovr-inseason-2026-27/live/2026-11-08/t-swap.json'), encoding='utf-8'))
T = {str(p): ts['ownPts100'][p] - ts['oppPts100'][p] for p in ts['pool']}
E = {r['playerId']: float(r['net']) for r in csv.DictReader(open(R('reports/impact-epm-2026-27/epm-live.csv'), encoding='utf-8'))
     if float(r['poss2627'] or 0) >= 200}
K = {}
for r in csv.DictReader(open(R('reports/ovr-v55-2k27-compare/2k27_ratings.csv'), encoding='utf-8-sig')):
    if r['overall2k']:
        K.setdefault(nm(r['name']), float(r['overall2k']))
ref = {'T': [T.get(pid[i]) for i in range(N)], 'EPM': [E.get(pid[i]) for i in range(N)], '2K': [K.get(nm(n)) for n in name]}
rng = np.random.default_rng(14214)
OUT['rho'] = {}
for s, y in ref.items():
    k = np.array([i for i in range(N) if y[i] is not None]); yy = np.array([y[i] for i in k])
    ra, rw = spearmanr(oA[k], yy)[0], spearmanr(oW[k], yy)[0]
    bs = []
    for _ in range(2000):
        b = rng.integers(0, len(k), len(k))
        bs.append(spearmanr(oW[k][b], yy[b])[0] - spearmanr(oA[k][b], yy[b])[0])
    OUT['rho'][s] = {'n': len(k), 'A': round(ra, 4), 'W1': round(rw, 4), 'd': round(rw - ra, 4),
                     'ci90': [round(float(np.percentile(bs, 5)), 4), round(float(np.percentile(bs, 95)), 4)]}
# 新進前十 c≥0.5 的人的 T／EPM／2K 名次
rk = lambda dct: {kk: j + 1 for j, kk in enumerate(sorted(dct, key=lambda x: -dct[x]))}
rT, rE, rK = rk(T), rk(E), rk(K)
OUT['new_top10_refs'] = {name[i]: {'c': round(float(c[i]), 2), 'T': rT.get(pid[i]), 'EPM': rE.get(pid[i]), '2K': rK.get(nm(name[i]))}
                         for i in np.argsort(rW)[:10] if name[i] not in OUT['top10_A']}
OUT['bigs_refs'] = {n: {'T': rT.get(pid[ix[n]]), 'EPM': rE.get(pid[ix[n]]), '2K': rK.get(nm(n))} for n in BIGS if n in ix}

# ---------------------------------------------------------------- 賽中新秀（身高帶）
live = list(csv.DictReader(open(R('reports/ovr-inseason-2026-27/live/2026-11-08/ranking.csv'), encoding='utf-8')))
hz = {}
for r in live:
    if r['playerId'] not in mpc['players']:
        h = float(r['heightInches'])
        hz.setdefault('heights', []).append(h)
        if str(int(h)) not in mpc['heightPrior']:
            hz.setdefault('height_outside_table', []).append((r['name'], h))
OUT['live_not_in_frozen'] = len(hz.get('heights', []))
OUT['live_not_in_frozen_height_outside_table'] = hz.get('height_outside_table', [])
OUT['live_not_in_frozen_names_h>=80'] = sorted([(r['name'], r['pos'], float(r['heightInches']), round(float(np.array(mpc['heightPrior'].get(str(int(float(r['heightInches']))), [0] * 5)) @ WP), 3))
                                                for r in live if r['playerId'] not in mpc['players'] and float(r['heightInches']) >= 80], key=lambda x: -x[2])
# 卡片身高非整數？
OUT['card_nonint_height'] = int((HGT != np.round(HGT)).sum())
OUT['live_nonint_height'] = int(sum(float(r['heightInches']) != round(float(r['heightInches'])) for r in live))

Path(__file__).with_name('recompute.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x)), encoding='utf-8')
skip = ('bigs', 'bigs_refs', 'sweep_examples')
print(json.dumps({k: v for k, v in OUT.items() if k not in skip}, ensure_ascii=False, indent=0, default=lambda x: x.item() if hasattr(x, 'item') else str(x)))


# ---------------------------------------------------------------- 補：對名漏掉的 3 人（BBRef 名字不同）手動對上後的影響
FIXMAP = {'Ronald Holland II': 'hollaro01', 'Trevon Scott': 'scotttr01', 'Adama Bal': 'balad01'}
rows26 = {r['bbref_id']: r for rs in RAW['2025-26'].values() for r in rs}
PIx = PI.copy()
fx = {}
for n, b in FIXMAP.items():
    i = ix[n]; r = rows26[b]
    v = np.array([float(r['p_' + p]) for p in P5]); v = v / v.sum(); mp_ = float(r['MP'])
    PIx[i] = v if mp_ >= 200 else (mp_ * v + (200 - mp_) * prior(HGT[i])) / 200
Wx = bonus(PIx, PIx @ WP)[0]
oX, rX = rank_of(Wx)
for n in FIXMAP:
    i = ix[n]
    fx[n] = {'bbref_name': rows26[FIXMAP[n]]['name'], 'MP': rows26[FIXMAP[n]]['MP'], 'c_height': round(float(c[i]), 3), 'c_bbref': round(float(PIx[i] @ WP), 3),
             'bonus_cand': round(float(W[i]), 3), 'bonus_fixed': round(float(Wx[i]), 3), 'rank_cand': int(rW[i]), 'rank_fixed': int(rX[i])}
OUT['namefix_3'] = fx
OUT['namefix_others_maxabs'] = float(np.abs(np.delete(Wx - W, [ix[n] for n in FIXMAP])).max())

# 賽中不在凍結檔的 48 人：有沒有較早季 BBRef 列（老將）卻被當新秀走身高帶
bb_by_name = {}
for s in SEAS:
    for rs in RAW[s].values():
        for r in rs:
            bb_by_name.setdefault(nm(r['name']).replace(' ', ''), []).append((s, r['team'], r['MP'], [r['p_' + p] for p in P5]))
OUT['live_not_frozen_with_bbref_history'] = {r['name']: bb_by_name[nm(r['name']).replace(' ', '')] for r in live
                                             if r['playerId'] not in mpc['players'] and nm(r['name']).replace(' ', '') in bb_by_name}
Path(__file__).with_name('recompute.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x)), encoding='utf-8')
print(json.dumps({k: OUT[k] for k in ('namefix_3', 'namefix_others_maxabs', 'live_not_frozen_with_bbref_history')}, ensure_ascii=False, indent=0))
