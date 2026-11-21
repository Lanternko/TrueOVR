"""E-295：MIX 加分位置權重改連續（BBRef 上場位置比例），修 0.2.14a PF／C 標籤斷崖。預註冊 preregistration.md（sha 見 preregistration.sha256）。
臂（全部＝E-294 H-same 的 z_H＝z_L−0.5·m、1.5·tanh 軟上限、λ=0.5、sd、500 分鐘打折；只換「位置」怎麼進公式）：
  A  ＝0.2.14a 現行：m＝標籤位置平均、w＝標籤權重（C=1、PF=0.243、其他 0）
  W1 ＝m 與 w 都用 BBRef 比例 π：w＝c＝π_C＋0.243·π_PF；m_i＝Σ_p π_ip·m_p（m_p＝算尺人群以 π 加權的 z_L 平均）
  W2 ＝只有 w 用 c，m 仍照標籤
  W3 ＝替代連續量：π 全部改用身高帶推估 π̂(身高)（不看 BBRef）
π 的來源（W1／W2）：2025-26 BBRef（E-177 pos-shares）；MP<200 往身高帶 π̂ 收縮 π＝(MP·π_b＋(200−MP)·π̂)/200；
  沒有 2025-26 列 → 最近一個較早季的列（同收縮）；完全沒有 → π̂（身高帶）。
身高帶 π̂(h)：卡片 2025-26 有 BBRef 且 MP≥200 的人，|身高−h|≤1 吋的 π 平均（不足 15 人放寬到 ±2、±3）。
用法（repo root）：python -I -B -X utf8 reports/E295-mix-pos-continuous/e295_eval.py [--explore|--dry]
  --dry：凍結前檢查，只印輸入與基準 A（不算候選臂）。"""
import csv, hashlib, importlib.util, json, re, sys, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr, rankdata

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
EXPLORE = '--explore' in sys.argv or '--dry' in sys.argv
if not EXPLORE:
    assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


CARD = ROOT / 'reports/card-0.2.13a/ranking.csv'; C14A = ROOT / 'reports/card-0.2.14a/ranking.csv'
FROZEN = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214.json'
FROZEN_H = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214a.json'
STATS25 = ROOT / 'reports/E227-lineup-transformer-r2/data/stats-2025-26.csv'
BB = ROOT / 'reports/card-0.2.9a+E177-bbref-position-shares'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
INP = HERE / 'inputs'
TSW = INP / 'live-2026-11-08-t-swap.json'; EPM = INP / 'epm-live.csv'
LIVE_RANK = INP / 'live-2026-11-08-ranking.csv'; LIVE_MIX = INP / 'live-2026-11-08-mix.json'
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
WPF = 0.68 / 2.80
POSL = ('PG', 'SG', 'SF', 'PF', 'C')
POSW = np.array([0.0, 0.0, 0.0, WPF, 1.0])
HI, ALPHA, MPK = 1.5, 0.5, 200.0
ARMS = ('A', 'W1', 'W2', 'W3')
CAND = ('W1', 'W2', 'W3')
SEED, B = 20261295, 2000
GRID = [0, .05, .1, .2, .3, .5, .75, 1.0, 1.5, 2.0]
SHOW = ['Chet Holmgren', 'Evan Mobley', 'Donovan Clingan', 'Bam Adebayo', 'Anthony Davis', 'Karl-Anthony Towns', 'Pascal Siakam',
        'Jaren Jackson Jr.', 'Giannis Antetokounmpo', 'Zion Williamson', 'Paolo Banchero', 'Jayson Tatum', 'Joel Embiid',
        'Victor Wembanyama', 'Nikola Jokić', 'Rudy Gobert', 'Jarrett Allen', 'Domantas Sabonis', 'Alperen Sengun', 'Ivica Zubac',
        'Isaiah Hartenstein', 'Zach Edey', 'Kristaps Porziņģis', 'Jalen Johnson', 'Scottie Barnes']
SWEEP = ['Chet Holmgren', 'Evan Mobley', 'Jaren Jackson Jr.', 'Bam Adebayo', 'Giannis Antetokounmpo', 'Donovan Clingan']


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s); s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return ' '.join(s.split())


def soft(x):
    return HI * np.tanh(np.maximum(x, 0.0) / HI)


# ================================================================ 位置比例
def load_shares():
    out = {}
    for s in SEASONS:
        out[s] = {}
        for r in csv.DictReader(open(BB / f'pos-shares-{s}.csv', encoding='utf-8')):
            if not r['playerId']: continue
            v = np.array([float(r[f'p_{p}']) for p in POSL])
            if v.sum() <= 0: continue
            out[s][str(r['playerId'])] = (v / v.sum(), float(r['MP'] or 0))
    return out


def height_prior(hgt_pool, pi_pool):
    """回傳函式 h→π̂：|身高−h|≤k 吋（k=1，不足 15 人放寬到 2、3…）的 π 平均。"""
    hp, pp = np.asarray(hgt_pool, float), np.asarray(pi_pool, float)

    def f(h):
        for k in (1, 2, 3, 4, 5, 8):
            m = np.abs(hp - h) <= k
            if m.sum() >= 15: return pp[m].mean(0)
        return pp.mean(0)
    return f


def shares_for(pids, hgt, season, SH, prior_pool_mask=None):
    """π（N×5）與來源標記。season＝卡片季；先用該季，沒有就往前找最近一季；MP<200 往身高帶收縮。"""
    N = len(pids)
    cur = SH[season]
    have = [pids[i] in cur and cur[pids[i]][1] >= MPK for i in range(N)]
    pm = np.array(have) if prior_pool_mask is None else (np.array(have) & prior_pool_mask)
    pri = height_prior(hgt[pm], np.array([cur[pids[i]][0] for i in np.where(pm)[0]]))
    PI = np.zeros((N, 5)); src = []
    earlier = SEASONS[:SEASONS.index(season)][::-1]
    for i, p in enumerate(pids):
        ph = pri(hgt[i])
        row = cur.get(p); tag = season
        if row is None:
            for s in earlier:
                if p in SH[s]: row = SH[s][p]; tag = s; break
        if row is None:
            PI[i] = ph; src.append('height'); continue
        v, mp = row
        PI[i] = v if mp >= MPK else (mp * v + (MPK - mp) * ph) / MPK
        src.append(tag if mp >= MPK else tag + '+shrink')
    return PI, src, pri


def onehot(pos):
    return np.array([[1.0 if p == q else 0.0 for q in POSL] for p in pos])


# ================================================================ 公式
def zL(v, have, pool):
    k = pool & have; mu, s = v[k].mean(), v[k].std()
    z = np.zeros(len(v)); z[have] = (v[have] - mu) / s
    return z


def build(feat, pool, PI_m, wvec, mpos=None):
    """PI_m（N×5）決定 m_i＝PI_m·m_p；wvec 位置權重；回傳 (P, capP, info)。mpos 給定就用（反事實時固定），否則在 pool 上以 PI_m 加權算。"""
    keys = ('reb', 'ob', 'db', 'con')
    ZL = {k: zL(feat[k][0], feat[k][1], pool) for k in keys}
    if mpos is None:
        mpos = {}
        for k in keys:
            g = pool & feat[k][1]
            wsum = PI_m[g].sum(0)
            mpos[k] = (PI_m[g] * ZL[k][g][:, None]).sum(0) / np.where(wsum > 0, wsum, 1)
    ZH = {}
    for k in keys:
        mi = PI_m @ mpos[k]
        ZH[k] = np.where(feat[k][1], ZL[k] - (1 - ALPHA) * mi, ALPHA * mi)
    zr = (ZH['reb'] + ZH['ob'] + ZH['db']) / 3; zc = ZH['con']
    r, c = soft(zr), soft(zc)
    rms = lambda x: float(np.sqrt((x[pool] ** 2).mean()))
    s_r, s_c = REFC / rms(r), REFC / rms(c)
    mix0 = .5 * r * s_r + .5 * c * s_c
    s_m = REFC / rms(mix0)
    capP = (.5 * HI * s_r + .5 * HI * s_c) * s_m * wvec
    return mix0 * s_m * wvec, capP, {'mpos': mpos, 'scales': (s_r, s_c, s_m), 'zr': zr, 'zc': zc}


def p_one(feat_i, PI_i, w_i, mpos, scales, zstats):
    """單人反事實（尺、m_p、縮放固定）。feat_i: {k: value or None}"""
    s_r, s_c, s_m = scales
    zh = {}
    for k in ('reb', 'ob', 'db', 'con'):
        mi = float(PI_i @ mpos[k])
        x = feat_i[k]
        zh[k] = ALPHA * mi if x is None else (x - zstats[k][0]) / zstats[k][1] - (1 - ALPHA) * mi
    zr = (zh['reb'] + zh['ob'] + zh['db']) / 3
    return float((.5 * soft(zr) * s_r + .5 * soft(zh['con']) * s_c) * s_m * w_i)


# ================================================================ 卡片
card = list(csv.DictReader(open(CARD, encoding='utf-8'))); N = len(card)
names = [r['name'] for r in card]; pos = np.array([r['pos'] for r in card])
MIN = np.array([float(r['MIN']) for r in card]); ovr0 = np.array([float(r['ovr']) for r in card])
rank0 = np.array([int(r['rank']) for r in card]); HGT = np.array([float(r['heightInches']) for r in card])
fz = json.load(open(FROZEN, encoding='utf-8')); cfg = fz['config']
pid_of = {v['name']: k for k, v in fz['players'].items()}
pids = [pid_of[n] for n in names]
cnt = {}
for r in csv.DictReader(open(STATS25, encoding='utf-8')):
    cnt[norm(r['name'])] = cnt.get(norm(r['name']), 0) + 1
uniq = np.array([cnt.get(norm(n), 0) == 1 for n in names])
EPZ = (MIN >= 500) & uniq
EP = MIN >= 500
assert EPZ.sum() == fz['epN']


def arr(key):
    v = np.array([np.nan if fz['players'][p][key] is None else fz['players'][p][key] for p in pids], float)
    return (np.nan_to_num(v), np.isfinite(v))


FEAT = {'reb': (np.array([fz['players'][p]['cardRebound'] for p in pids], float), np.ones(N, bool)),
        'ob': arr('orebPct'), 'db': arr('drebPct'), 'con': arr('con2_36')}
ZSTAT = {k: (FEAT[k][0][EPZ & FEAT[k][1]].mean(), FEAT[k][0][EPZ & FEAT[k][1]].std()) for k in FEAT}
ramp = np.minimum(1.0, MIN / 500.0)
LAM, SD, REFC = cfg['lambda'], cfg['sd'], cfg['ref']
SH = load_shares()
PI_B, SRC, PRIOR = shares_for(pids, HGT, '2025-26', SH)
PI_H = np.array([PRIOR(h) for h in HGT])
PI_L = onehot(pos)
cW = lambda PI: PI @ POSW
SPEC = {'A': (PI_L, cW(PI_L)), 'W1': (PI_B, cW(PI_B)), 'W2': (PI_L, cW(PI_B)), 'W3': (PI_H, cW(PI_H))}
PC, CAPC, INFO = {}, {}, {}
for a in ARMS:
    PC[a], CAPC[a], INFO[a] = build(FEAT, EPZ, *SPEC[a])
BON = {a: LAM * SD * PC[a] * ramp for a in ARMS}
CAPB = {a: LAM * SD * CAPC[a] for a in ARMS}
c14a = {r['name']: r for r in csv.DictReader(open(C14A, encoding='utf-8'))}
repro = float(max(abs(BON['A'][i] - float(c14a[n]['mixBonus'])) for i, n in enumerate(names)))
assert repro <= 0.001, repro
rankA_card = np.array([int(c14a[n]['rank']) for n in names])

# 參考名次
ts = json.load(open(TSW, encoding='utf-8'))
tnet = {p: ts['ownPts100'][p] - ts['oppPts100'][p] for p in ts['pool']}
ep = {r['playerId']: float(r['net']) for r in csv.DictReader(open(EPM, encoding='utf-8')) if float(r['poss2627'] or 0) >= 200}
tk = {}
for r in csv.DictReader(open(TWOK, encoding='utf-8-sig')):
    if r['overall2k']: tk.setdefault(norm(r['name']), float(r['overall2k']))
rnk = lambda dct: {k: i + 1 for i, k in enumerate(sorted(dct, key=lambda x: -dct[x]))}
rT, rE, rK = rnk(tnet), rnk(ep), rnk(tk)
idx = {'T': np.array([i for i in range(N) if pids[i] in tnet]), 'EPM': np.array([i for i in range(N) if pids[i] in ep]),
       '2K': np.array([i for i in range(N) if norm(names[i]) in tk])}
yv = {'T': np.array([tnet[pids[i]] for i in idx['T']]), 'EPM': np.array([ep[pids[i]] for i in idx['EPM']]),
      '2K': np.array([tk[norm(names[i])] for i in idx['2K']])}
rng = np.random.default_rng(SEED)
BOOT = {s: [rng.integers(0, len(idx[s]), len(idx[s])) for _ in range(B)] for s in idx}


def ranks(o):
    order = sorted(range(N), key=lambda i: (-o[i], rank0[i])); r = np.empty(N, int); r[order] = np.arange(1, N + 1); return r


def rho(o, src, b=None):
    k = idx[src]; y = yv[src]
    if b is not None: k, y = k[b], y[b]
    return float(spearmanr(o[k], y)[0])


def ties50(o, r):
    v, c = np.unique(np.round(o[r <= 50], 1), return_counts=True)
    return int((c >= 2).sum()), int(c[c >= 2].sum())


def disc(bonus, cap):
    m = EP & (cap > 0)
    near = m & (bonus >= cap - 0.2)
    cb = bonus[EP & (pos == 'C')]
    top30 = np.sort(bonus[EP])[::-1][:30]
    _, cnts = np.unique(np.round(top30, 1), return_counts=True)
    q = lambda x, p: float(np.percentile(x, p))
    return {'n_near_cap': int(near.sum()), 'near_cap_names': [names[i] for i in np.where(near)[0]], 'max_bonus': float(bonus.max()),
            'C_sd': float(cb.std()), 'C_iqr': q(cb, 75) - q(cb, 25), 'C_mean': float(cb.mean()),
            'n_pos_bonus_min500': int((EP & (bonus > 0.05)).sum()), 'max_same_bonus_group': int(cnts.max()),
            'top10_bonus': [(names[i], pos[i], round(float(bonus[i]), 2)) for i in np.argsort(-bonus)[:10]],
            'pos_mean_min500': {p: float(bonus[EP & (pos == p)].mean()) for p in POSL}}


def card_eval(bonus, cap, oA=None):
    o = np.round(ovr0 + bonus, 1); r = ranks(o)
    out = {'top10': [(names[i], pos[i]) for i in np.argsort(r)[:10]],
           'rank11_20': [(names[i], pos[i], int(r[i])) for i in np.argsort(r)[10:20]],
           'top30_drops_vs_0214a': [(names[i], int(rankA_card[i]), int(r[i])) for i in range(N) if rankA_card[i] <= 30 and r[i] - rankA_card[i] > 10],
           'top30_drops_vs_0213a': [(names[i], int(rank0[i]), int(r[i])) for i in range(N) if rank0[i] <= 30 and r[i] - rank0[i] > 10],
           'ties50': ties50(o, r), 'rho': {s: rho(o, s) for s in idx},
           'show': {n: {'rank': int(r[names.index(n)]), 'bonus': round(float(bonus[names.index(n)]), 2)} for n in SHOW if n in names},
           'disc': disc(bonus, cap), '_rank': r}
    if oA is not None:
        out['drho_vs_A'] = {}
        for s in idx:
            d = np.array([rho(o, s, b) - rho(oA, s, b) for b in BOOT[s]])
            out['drho_vs_A'][s] = {'mean': out['rho'][s] - rho(oA, s), 'ci90': [float(np.percentile(d, 5)), float(np.percentile(d, 95))]}
    return out, o


def ok_big(i):
    t, e, k = rT.get(pids[i]), rE.get(pids[i]), rK.get(norm(names[i]))
    return (t is not None and t <= 50) or (e is not None and e <= 50) or (k is not None and k <= 30)


def fi(i):
    return {k: (float(FEAT[k][0][i]) if FEAT[k][1][i] else None) for k in FEAT}


def cliff(a):
    """斷崖指標：(1) 標籤反事實——把每個 MIN≥500 球員的標籤改 C 與改 PF，加分差（尺、m_p、縮放固定）；
    (2) 比例掃描——SWEEP 球員的 PF＋C 總比例固定，C 佔比 0→1 每 1% 一步，最大相鄰跳動。A 的標籤在掃描中取 argmax(π)。"""
    PI_m, wv = SPEC[a]; inf = INFO[a]
    lab = {}
    for i in np.where(EP)[0]:
        b = {}
        for L in ('C', 'PF'):
            oh = onehot([L])[0]
            Pm = oh if a in ('A', 'W2') else PI_m[i]
            wi = float(oh @ POSW) if a == 'A' else float(wv[i])
            b[L] = LAM * SD * p_one(fi(i), Pm, wi, inf['mpos'], inf['scales'], ZSTAT) * ramp[i]
        lab[names[i]] = b['C'] - b['PF']
    absd = np.array([abs(v) for v in lab.values()])
    sw = {}
    for n in SWEEP:
        i = names.index(n); base = PI_B[i].copy(); tot = base[3] + base[4]
        if tot <= 0: continue
        vals = []
        for k in range(101):
            pi = base.copy(); pi[4] = tot * k / 100; pi[3] = tot - pi[4]
            if a == 'A':
                oh = onehot([POSL[int(np.argmax(pi))]])[0]; Pm, wi = oh, float(oh @ POSW)
            elif a == 'W2':
                Pm, wi = PI_L[i], float(pi @ POSW)
            elif a == 'W3':
                Pm, wi = PI_H[i], float(PI_H[i] @ POSW)
            else:
                Pm, wi = pi, float(pi @ POSW)
            vals.append(LAM * SD * p_one(fi(i), Pm, wi, inf['mpos'], inf['scales'], ZSTAT) * ramp[i])
        vals = np.array(vals)
        sw[n] = {'pfc_share': float(tot), 'C_share_actual': float(base[4]), 'max_step': float(np.abs(np.diff(vals)).max()),
                 'at_C0': float(vals[0]), 'at_C50': float(vals[50]), 'at_C100': float(vals[100])}
    return {'label_flip_max_abs': float(absd.max()), 'label_flip_n_gt_0.5': int((absd > 0.5).sum()),
            'label_flip_named': {n: round(lab[n], 2) for n in SHOW if n in lab}, 'sweep': sw,
            'sweep_max_step': float(max(v['max_step'] for v in sw.values()))}


# ================================================================ 賽中新秀（只報告＋G5 結構檢查）
def live_rookies(a):
    rows = list(csv.DictReader(open(LIVE_RANK, encoding='utf-8')))
    mx = json.load(open(LIVE_MIX, encoding='utf-8'))['players']
    fzh = json.load(open(FROZEN_H, encoding='utf-8'))
    PI_m, wv = SPEC[a]; inf = INFO[a]
    out = []
    for r in rows:
        pid = r['playerId']
        if pid in fzh['players']: continue
        d = mx.get(pid) or {}
        h = float(r['heightInches']); pi_hat = PRIOR(h)
        lab = r['pos'] if r['pos'] in POSL else None
        oh = onehot([lab])[0] if lab else np.zeros(5)
        if a == 'A': Pm, wi = oh, float(oh @ POSW)
        elif a == 'W2': Pm, wi = oh, float(pi_hat @ POSW)
        else: Pm, wi = pi_hat, float(pi_hat @ POSW)
        f = {'reb': float(r['rebound']), 'ob': d.get('orebPct'), 'db': d.get('drebPct'), 'con': d.get('con2_36')}
        mins = float(d.get('MIN') or r['MIN26'] or 0)
        b = LAM * SD * p_one(f, Pm, wi, inf['mpos'], inf['scales'], ZSTAT) * min(1.0, mins / 500)
        out.append({'name': r['name'], 'pos': r['pos'], 'height': h, 'MIN26': float(r['MIN26'] or 0), 'c': round(float(pi_hat @ POSW), 3), 'w': round(wi, 3),
                    'bonus': round(b, 3), 'live_bonus_0214a': float(r['mixBonus'] or 0)})
    return sorted(out, key=lambda x: -x['height'])


# ================================================================ 前瞻台（E-290 台子＋E-294 MIX 重算，只報告）
def bench():
    E290 = mod('e290', 'reports/E290-reb-bonus-0213a/e290_eval.py')
    E = E290.E; Q = E.Q; FOLDS, NEXT, FULL = E.FOLDS, E.NEXT, E.FULL
    D = {c: E.build(c) for c in FOLDS}
    PP, cover = {}, {}
    for c in FOLDS:
        d = D[c]; E290.add_arms(c, d)
        stage = {r['name']: r for r in csv.DictReader(open(E290.STAGE / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
        cardS = {r['name']: r for r in csv.DictReader(open(E.CARD / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
        n = len(d['ids'])
        reb = np.array([float(stage[nm]['rebound']) for nm in d['names']])
        hgt = np.array([float(cardS[nm]['heightInches']) for nm in d['names']])
        tab = E290.stats_tab(c); ob = np.full(n, np.nan); db = np.full(n, np.nan)
        for i, p in enumerate(d['ids']):
            x = tab.get(str(p))
            if x:
                if x['orebPct'] is not None: ob[i] = x['orebPct']
                if x['drebPct'] is not None: db[i] = x['drebPct']
        js = json.loads(E.hustle_path(c).read_text(encoding='utf-8')); H = {}
        for r in js['rowSet']:
            r = dict(zip(js['headers'], r)); a_ = H.setdefault(int(r['PLAYER_ID']), [0.0, 0.0])
            a_[0] += r['MIN'] or 0; a_[1] += r['CONTESTED_SHOTS_2PT'] or 0
        v = np.zeros(n); have = np.zeros(n, bool)
        for i, p in enumerate(d['ids']):
            x = H.get(int(p))
            if x and x[0] >= 200: v[i] = x[1] / x[0] * 36; have[i] = True
        feat = {'reb': (reb, np.ones(n, bool)), 'ob': (np.nan_to_num(ob), np.isfinite(ob)), 'db': (np.nan_to_num(db), np.isfinite(db)),
                'con': (v, have)}
        allp = np.ones(n, bool)
        ids = [str(p) for p in d['ids']]
        PIb, src, pri = shares_for(ids, hgt, c, SH)
        PIh = np.array([pri(h) for h in hgt]); PIl = onehot(d['pos'])
        spec = {'A': (PIl, PIl @ POSW), 'W1': (PIb, PIb @ POSW), 'W2': (PIl, PIb @ POSW), 'W3': (PIh, PIh @ POSW)}
        global REFC
        keep = REFC; REFC = d['P_ref']
        PP[c] = {a: build(feat, allp, *spec[a])[0] for a in ARMS}
        REFC = keep
        cover[c] = {s: int(sum(x == s for x in src)) for s in set(src)}
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}; Y['2025-26'] = E.V.live_targets(D['2025-26']['ids'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}; w = {t: n[t] / sum(n.values()) for t in FOLDS}
    m = lambda t, o: float(Q.metrics(D[t], Y[t], o)['all'])
    base = {t: m(t, D[t]['ovr']) for t in FOLDS}
    a05 = {t: m(t, E.adj(D[t], PP[t]['A'], .5)) for t in FOLDS}
    out = {'n': n, 'cover': cover, 'arms': {}}
    for a in ARMS:
        rg = {t: {l: m(t, E.adj(D[t], PP[t][a], l)) for l in GRID} for t in FOLDS}
        lofo = {t: max(GRID, key=lambda l: np.mean([rg[c][l] for c in FOLDS if c != t])) for t in FOLDS}
        r = {'lofo_lambda': lofo,
             'same05_vs_base': float(sum(w[t] * (rg[t][.5] - base[t]) for t in FOLDS)),
             'same05_vs_A05': float(sum(w[t] * (rg[t][.5] - a05[t]) for t in FOLDS)),
             'per_fold_vs_A05': {t: rg[t][.5] - a05[t] for t in FOLDS},
             'n_pos_same05_vs_A05': int(sum(rg[t][.5] > a05[t] for t in FOLDS)),
             'gap_C_same05': float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], PP[t][a], .5), 'C') for t in FOLDS]).mean()),
             'gap_PF_same05': float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], PP[t][a], .5), 'PF') for t in FOLDS]).mean())}
        out['arms'][a] = r
        print(f"bench {a:3s} Δbase={r['same05_vs_base']:+.4f} ΔA={r['same05_vs_A05']:+.4f} ({r['n_pos_same05_vs_A05']}/4) gapC {r['gap_C_same05']:+.3f} PF {r['gap_PF_same05']:+.3f}")
    print('bench cover', cover)
    return out


def checks(a, ev, evA, cl, rook):
    dsc = ev['disc']
    G1 = cl['label_flip_max_abs'] <= 0.05 and cl['sweep_max_step'] <= 0.2
    G2 = dsc['n_near_cap'] == 0 and dsc['max_same_bonus_group'] <= evA['disc']['max_same_bonus_group'] + 2
    G3 = not any(v['mean'] < -0.005 and v['ci90'][1] < 0 for v in ev['drho_vs_A'].values())
    topA = [n for n, _ in evA['top10']]
    new_bigs = [n for n, p in ev['top10'] if n not in topA and float(SPEC[a][1][names.index(n)]) >= 0.5]
    G4 = all(ok_big(names.index(n)) for n in new_bigs) and len(ev['top30_drops_vs_0214a']) <= 2
    src_ok = all(s != 'none' for s in SRC)
    rk_ok = all(x['w'] > 0 for x in rook if x['height'] >= 80)
    G5 = src_ok and rk_ok
    return {'G1': G1, 'G2': G2, 'G3': G3, 'G4': G4, 'G5': G5, 'new_bigs_top10': new_bigs}


def main():
    res = {'sources_sha256': {'card_0213a': sha(CARD), 'card_0214a': sha(C14A), 'mix_pool': sha(FROZEN), 'mix_pool_h': sha(FROZEN_H),
                              't_swap': sha(TSW), 'epm': sha(EPM), '2k27': sha(TWOK), 'live_rank': sha(LIVE_RANK), 'live_mix': sha(LIVE_MIX),
                              **{f'pos_shares_{s}': sha(BB / f'pos-shares-{s}.csv') for s in SEASONS}},
           'repro_A_vs_card0214a_maxabs': repro, 'n_match': {s: int(len(idx[s])) for s in idx},
           'share_source_counts': {s: SRC.count(s) for s in sorted(set(SRC))},
           'share_source_counts_min500': {s: int(sum(1 for i in np.where(EP)[0] if SRC[i] == s)) for s in sorted(set(SRC))},
           'mpos': {a: {k: [round(float(x), 4) for x in v] for k, v in INFO[a]['mpos'].items()} for a in ARMS},
           'scales': {a: INFO[a]['scales'] for a in ARMS},
           'share_table': {n: {'pi': [round(float(x), 3) for x in PI_B[names.index(n)]], 'c': round(float(cW(PI_B)[names.index(n)]), 3),
                               'c_height': round(float(cW(PI_H)[names.index(n)]), 3), 'label': pos[names.index(n)], 'src': SRC[names.index(n)],
                               'height': HGT[names.index(n)]} for n in SHOW if n in names}}
    if not EXPLORE:
        res['prereg_sha256'] = sha(HERE / 'preregistration.md')
    evA, oA = card_eval(BON['A'], CAPB['A'])
    if '--dry' in sys.argv:   # 凍結前：只看輸入（比例、來源）與基準 A，不算任何候選臂
        print(json.dumps({k: res[k] for k in ('repro_A_vs_card0214a_maxabs', 'share_source_counts', 'share_source_counts_min500', 'share_table')}, ensure_ascii=False, indent=0, default=str))
        print('A top10', evA['top10']); print('A 11-20', evA['rank11_20']); print('A disc', {k: evA['disc'][k] for k in ('n_near_cap', 'max_same_bonus_group', 'C_sd')}, 'ties50', evA['ties50'])
        print('A drops vs 0213a', evA['top30_drops_vs_0213a'])
        print('rookies≥81 A', [(x['name'], x['pos'], x['height'], x['c'], x['w'], x['bonus']) for x in live_rookies('A') if x['height'] >= 81])
        return
    res['card'] = {}
    for a in ARMS:
        ev, o = card_eval(BON[a], CAPB[a], oA)
        cl = cliff(a); rook = live_rookies(a)
        ev['cliff'] = cl; ev['rookies_live'] = rook
        ev['checks'] = checks(a, ev, evA, cl, rook)
        ev['verdict'] = 'baseline' if a == 'A' else ('adopt_candidate' if all(ev['checks'][g] for g in ('G1', 'G2', 'G3', 'G4', 'G5')) else 'reject')
        r = ev.pop('_rank')
        res['card'][a] = ev
        d = ev['disc']
        print(f"\n{a} {ev['verdict']} {ev['checks']}")
        print(f"  near_cap {d['n_near_cap']} maxsame {d['max_same_bonus_group']} C sd {d['C_sd']:.2f} Cmean {d['C_mean']:.2f} ties50 {ev['ties50']} drops14a {ev['top30_drops_vs_0214a']}")
        print('  ρ', {s: round(ev['rho'][s], 4) for s in idx}, {s: (round(v['mean'], 4), [round(x, 4) for x in v['ci90']]) for s, v in ev['drho_vs_A'].items()})
        print('  cliff', cl['label_flip_max_abs'], cl['label_flip_n_gt_0.5'], 'sweep', round(cl['sweep_max_step'], 3))
        print('  top10', [x[0] for x in ev['top10']]); print('  11-20', ev['rank11_20'])
        print('  show', {k: (v['rank'], v['bonus']) for k, v in ev['show'].items()})
        print('  topbonus', d['top10_bonus'])
        print('  rookies≥82', [(x['name'], x['pos'], x['height'], x['c'], x['bonus'], x['live_bonus_0214a']) for x in rook if x['height'] >= 81])
    if not EXPLORE:
        res['bench'] = bench()
    pick = next((a for a in CAND if res['card'][a]['verdict'] == 'adopt_candidate'), None)
    res['pick'] = pick
    res['ref_ranks'] = {n: {'T': rT.get(pids[names.index(n)]), 'EPM': rE.get(pids[names.index(n)]), '2K': rK.get(norm(n)),
                            'rank_0213a': int(rank0[names.index(n)]), 'rank_0214a': int(rankA_card[names.index(n)])} for n in SHOW if n in names}
    print('pick', pick)
    out = HERE / ('explore.json' if EXPLORE else 'results.json')
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else (list(x) if isinstance(x, tuple) else str(x))), encoding='utf-8')
    if pick and not EXPLORE:
        np.savez(HERE / 'bonus_pick.npz', names=np.array(names), bonus=BON[pick], pick=np.array(pick),
                 pi=SPEC[pick][0], w=SPEC[pick][1], src=np.array(SRC))


if __name__ == '__main__':
    main()
