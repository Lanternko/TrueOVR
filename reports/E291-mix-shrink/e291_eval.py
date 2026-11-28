"""E-291 評估：MIX 加分上場時間收縮（預註冊 preregistration.md，sha 見 preregistration.sha256）。
臂 A＝card-0.2.14-cand 現行加分；B＝收縮平滑版；C＝不收縮 582 人全套。
用法（repo root）：python -I -B -X utf8 reports/E291-mix-shrink/e291_eval.py"""
import csv, hashlib, json, re, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAM, K = 0.5, 500.0
OK_BIGS = {'Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren', 'Evan Mobley'}
POS = ('PG', 'SG', 'SF', 'PF', 'C')
CARD = ROOT / 'reports/card-0.2.13a/ranking.csv'
CAND = ROOT / 'reports/card-0.2.14-cand/ranking.csv'
STATS = ROOT / 'reports/E227-lineup-transformer-r2/data/stats-2025-26.csv'
HUST = ROOT / 'data/tracking-cells/2025-26/hustle-2025-26.json'
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
EPM = ROOT / 'reports/impact-epm-2026-27/epm-live.csv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s)
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return ' '.join(s.split())


def fl(x):
    return float(x) if x not in ('', None) else np.nan


card = list(csv.DictReader(open(CARD, encoding='utf-8')))
N = len(card)
names = [r['name'] for r in card]
pos = np.array([r['pos'] for r in card])
MIN = np.array([float(r['MIN']) for r in card])
ovr0 = np.array([float(r['ovr']) for r in card])
rank0 = np.array([int(r['rank']) for r in card])
reb = np.array([float(r['rebound']) for r in card])

st = {}
for r in csv.DictReader(open(STATS, encoding='utf-8')):
    st.setdefault(norm(r['name']), []).append(r)
js = json.loads(HUST.read_text(encoding='utf-8'))
H = {}
for row in js['rowSet']:
    r = dict(zip(js['headers'], row)); a = H.setdefault(norm(r['PLAYER_NAME']), {})
    pid = r['PLAYER_ID']; b = a.setdefault(pid, [0.0, 0.0])
    b[0] += r['MIN'] or 0; b[1] += r['CONTESTED_SHOTS_2PT'] or 0

ob = np.full(N, np.nan); db = np.full(N, np.nan); smin = np.zeros(N); uniq = np.zeros(N, bool)
conraw = np.full(N, np.nan); hmin = np.zeros(N)
for i, nm in enumerate(names):
    s = st.get(norm(nm)) or []
    if len(s) == 1:
        uniq[i] = True; ob[i] = fl(s[0]['orebPct']); db[i] = fl(s[0]['drebPct']); smin[i] = fl(s[0]['minutes']) or 0.0
    h = H.get(norm(nm)) or {}
    if len(h) == 1:
        m, c = list(h.values())[0]
        hmin[i] = m
        if m > 0:
            conraw[i] = c / m * 36
smin = np.where(np.isfinite(smin), smin, 0.0)
EP = (MIN >= 500) & uniq
sd = float(ovr0[EP].std())
ref = float(np.sqrt((pos[EP] == 'C').mean()))
no_data = [(names[i], pos[i], MIN[i]) for i in range(N) if not uniq[i] and hmin[i] <= 0]


def zstat(v, mask):
    k = mask & np.isfinite(v)
    return v[k].mean(), v[k].std()


# 尺（EP 原值）
Z = {'reb': zstat(reb, EP), 'ob': zstat(ob, EP), 'db': zstat(db, EP)}
con_c = np.where(hmin >= 200, conraw, np.nan)  # C／A 的定義
Z['con'] = zstat(con_c, EP)
MU = {k: {p: float(np.nanmean(v[EP & (pos == p) & np.isfinite(v)])) for p in POS}
      for k, v in (('reb', reb), ('ob', ob), ('db', db), ('con', con_c))}


def shrink(x, m, key):
    mu = np.array([MU[key][p] for p in pos])
    w = np.where(np.isfinite(x), m / (m + K), 0.0)
    return w * np.where(np.isfinite(x), x, 0.0) + (1 - w) * mu


def zz(v, key):
    mu, s = Z[key]
    o = (v - mu) / s
    return np.where(np.isfinite(o), o, 0.0)


def arm_from(rebc, conr, scales=None):
    rms = lambda v: float(np.sqrt((v[EP] ** 2).mean()))
    if scales is None:
        scales = (ref / rms(rebc), ref / rms(conr))
        mix = .5 * rebc * scales[0] + .5 * conr * scales[1]
        scales = scales + (ref / rms(mix),)
    mix = (.5 * rebc * scales[0] + .5 * conr * scales[1]) * scales[2]
    return LAM * sd * mix, scales


def arm_B(m_card=MIN, m_st=smin, m_h=hmin, scales=None):
    # con 原始值：hustle 有分鐘就算（取消 200 門檻）
    rebc = np.clip((zz(shrink(reb, m_card, 'reb'), 'reb') + zz(shrink(ob, m_st, 'ob'), 'ob') + zz(shrink(db, m_st, 'db'), 'db')) / 3, 0, 1.5)
    conr = np.clip(zz(shrink(conraw, m_h, 'con'), 'con'), 0, 1.5)
    b, sc = arm_from(rebc, conr, scales)
    nd = np.array([not uniq[i] and hmin[i] <= 0 for i in range(N)])
    b = np.where(nd, 0.0, b)
    return b, sc, rebc, conr


bB, scB, rebcB, conB = arm_B()
rebcC = np.clip((zz(reb, 'reb') + zz(ob, 'ob') + zz(db, 'db')) / 3, 0, 1.5)
conC = np.clip(zz(con_c, 'con'), 0, 1.5)
bC, scC = arm_from(rebcC, conC)
cand = {r['name']: r for r in csv.DictReader(open(CAND, encoding='utf-8'))}
bA = np.array([float(cand[n]['mixBonus']) for n in names])
# 檢查 C 在 EP 內重現 A（A＝C 只套 pop_of ≥500）
dAC = np.abs(bA - bC)[bA != 0]
print(f'N={N} EP={EP.sum()} sd={sd:.4f} ref={ref:.6f} | C vs A (A>0) max diff {dAC.max():.4f}; scales B {scB} C {scC}')
print('沒資料（加分 0）：', no_data)

ARMS = {'A': bA, 'B': bB, 'C': bC}


def ranks(o):
    idx = sorted(range(N), key=lambda i: (-o[i], rank0[i])); r = np.empty(N, int); r[idx] = np.arange(1, N + 1); return r


NEW = {k: np.round(ovr0 + b, 1) for k, b in ARMS.items()}
R = {k: ranks(v) for k, v in NEW.items()}
top10_0 = [names[i] for i in np.argsort(rank0)[:10]]
res = {'sources_sha256': {'card_0213a': sha(CARD), 'cand': sha(CAND), 'stats': sha(STATS), 'hustle': sha(HUST), '2k27': sha(TWOK), 'epm': sha(EPM)},
       'prereg_sha256': sha(HERE / 'preregistration.md'), 'EP_n': int(EP.sum()), 'sd': sd, 'P_ref': ref,
       'scales_B': list(scB), 'scales_C': list(scC), 'no_data': [n for n, _, _ in no_data], 'arms': {}}
assert res['prereg_sha256'] == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'

tw = {norm(r['name']): float(r['overall2k']) for r in csv.DictReader(open(TWOK, encoding='utf-8-sig')) if r['overall2k']}
ep = {norm(r['name']): (float(r['net']), float(r['poss2627'])) for r in csv.DictReader(open(EPM, encoding='utf-8'))}


def corr(o, mask, src):
    if src == '2k':
        idx = [i for i in range(N) if mask[i] and norm(names[i]) in tw]; y = [tw[norm(names[i])] for i in idx]
    else:
        idx = [i for i in range(N) if mask[i] and norm(names[i]) in ep and ep[norm(names[i])][1] >= 200]; y = [ep[norm(names[i])][0] for i in idx]
    return float(spearmanr([o[i] for i in idx], y)[0]), len(idx)


# T3：反事實與階梯
def cf(m):
    mm = np.full(N, float(m))
    return arm_B(mm, mm, mm, scales=scB)[0]


band = (MIN >= 400) & (MIN <= 600)


def step(b):
    idx = np.where(band)[0]
    X = np.column_stack([np.ones(len(idx)), MIN[idx], (MIN[idx] >= 500).astype(float)] + [(pos[idx] == p).astype(float) for p in POS[1:]])
    beta, *_ = np.linalg.lstsq(X, b[idx], rcond=None)
    return float(beta[2])


nd_mask = np.array([not uniq[i] and hmin[i] <= 0 for i in range(N)])
cfB = np.where(nd_mask, 0, np.abs(cf(501) - cf(499)))
for k in ARMS:
    b = ARMS[k]; o = NEW[k]; r = R[k]
    t10 = [names[i] for i in np.argsort(r)[:10]]
    newbig = [n for n in t10 if n not in top10_0 and pos[names.index(n)] in ('PF', 'C') and n not in OK_BIGS]
    drops = [(names[i], int(rank0[i]), int(r[i])) for i in range(N) if rank0[i] <= 30 and r[i] - rank0[i] > 10]
    cap = float(b.max())
    rc, cc = {'A': (rebcC, conC), 'B': (rebcB, conB), 'C': (rebcC, conC)}[k]
    satm = (rc >= 1.5 - 1e-9) & (cc >= 1.5 - 1e-9) & (b > 0)
    sat = int(satm.sum())
    a = {'top10': t10, 'top10_new_bigs_violating': newbig, 'top30_drops': drops, 'cap': cap, 'n_saturated': sat,
         'saturated': [names[i] for i in np.where(satm)[0]], 'n_bonus_pos': int((b > 0).sum()),
         'step_400_600': step(b),
         'rho_2k_min500': corr(o, MIN >= 500, '2k'), 'rho_epm_min500': corr(o, MIN >= 500, 'epm'),
         'rho_2k_all': corr(o, np.ones(N, bool), '2k'), 'rho_epm_all': corr(o, np.ones(N, bool), 'epm'),
         'rho_2k_bigs_min500': corr(o, (MIN >= 500) & np.isin(pos, ['PF', 'C']), '2k'),
         'pos_mean_bonus_all': {p: float(b[pos == p].mean()) for p in POS},
         'pos_mean_bonus_min500': {p: float(b[(pos == p) & (MIN >= 500)].mean()) for p in POS}}
    res['arms'][k] = a
res['rho_0213a'] = {'2k_min500': corr(ovr0, MIN >= 500, '2k'), 'epm_min500': corr(ovr0, MIN >= 500, 'epm'), '2k_all': corr(ovr0, np.ones(N, bool), '2k')}
res['arms']['A']['cf_jump_max'] = float(bA[(MIN >= 500)].max())  # A：499→501 從 0 跳到全額
res['arms']['B']['cf_jump_max'] = float(cfB.max())
diff_ep = np.abs(bB - bA)[EP]
res['B_vs_A_EP'] = {'mean_abs': float(diff_ep.mean()), 'max_abs': float(diff_ep.max()), 'mean_signed': float((bB - bA)[EP].mean())}

A, Bm = res['arms']['A'], res['arms']['B']
setA, setB = set(A['top10']), set(Bm['top10'])
swap = sorted(setA ^ setB)
T1 = (not Bm['top10_new_bigs_violating']) and len(setA - setB) <= 2 and all(pos[names.index(n)] not in ('PF', 'C') or n in OK_BIGS for n in swap)
T2 = len(Bm['top30_drops']) <= 2
T3 = Bm['cf_jump_max'] <= 0.10 and abs(Bm['step_400_600']) <= 1.0
T4 = Bm['n_saturated'] < A['n_saturated']
T5 = Bm['rho_2k_min500'][0] >= A['rho_2k_min500'][0] - .005 and Bm['rho_epm_min500'][0] >= A['rho_epm_min500'][0] - .005
res['checks'] = {'T1': bool(T1), 'T2': bool(T2), 'T3': bool(T3), 'T4': bool(T4), 'T5': bool(T5), 'top10_swap': swap}
res['pass'] = bool(T1 and T2 and T3 and T4 and T5)
res['rerun_e290_needed'] = bool(res['B_vs_A_EP']['mean_abs'] > 0.3)
res['k2_up'] = bool(Bm['rho_2k_min500'][0] > A['rho_2k_min500'][0])

SHOW = ['Ariel Hukporti', 'Trayce Jackson-Davis', 'Zach Edey', 'Khaman Maluach', 'Kevon Looney', 'Paul Reed', 'Goga Bitadze',
        'Victor Wembanyama', 'Anthony Davis', 'Rudy Gobert', 'Jarrett Allen', 'Chet Holmgren', 'Evan Mobley', 'Domantas Sabonis',
        'Devin Booker', 'Kevin Durant', 'Anthony Edwards', 'Tyrese Maxey', 'Nikola Jokić', 'Shai Gilgeous-Alexander']
res['show'] = {}
for n in SHOW:
    if n in names:
        i = names.index(n)
        res['show'][n] = {'pos': pos[i], 'MIN': MIN[i], 'rank0': int(rank0[i]), **{f'bonus_{k}': round(float(ARMS[k][i]), 2) for k in ARMS},
                          **{f'rank_{k}': int(R[k][i]) for k in ARMS}, '2k': tw.get(norm(n))}
# 400–600 分鐘帶（PF/C）逐人
res['band_bigs'] = [(names[i], pos[i], MIN[i], round(float(bA[i]), 2), round(float(bB[i]), 2)) for i in sorted(np.where(band & np.isin(pos, ['PF', 'C']))[0], key=lambda i: MIN[i])]
(HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
np.savez(HERE / 'arms.npz', names=np.array(names), bA=bA, bB=bB, bC=bC, rebcB=rebcB, conB=conB)
for k in ARMS:
    a = res['arms'][k]
    print(f"== {k}: top10 {a['top10']}\n   viol {a['top10_new_bigs_violating']} drops {a['top30_drops']} cap {a['cap']:.2f} sat {a['n_saturated']} pos>0 {a['n_bonus_pos']} "
          f"step {a['step_400_600']:+.2f} ρ2K {a['rho_2k_min500']} ρEPM {a['rho_epm_min500']} ρ2K全 {a['rho_2k_all']} ρ2K長人 {a['rho_2k_bigs_min500']}")
    print('   pos mean all', {p: round(v, 2) for p, v in a['pos_mean_bonus_all'].items()}, 'min500', {p: round(v, 2) for p, v in a['pos_mean_bonus_min500'].items()})
print('0.2.13a', res['rho_0213a'])
print('cf jump', res['arms']['A']['cf_jump_max'], res['arms']['B']['cf_jump_max'], 'B vs A EP', res['B_vs_A_EP'])
print('checks', res['checks'], 'PASS', res['pass'], 'rerun', res['rerun_e290_needed'], '2K up', res['k2_up'])
print('sat B', res['arms']['B']['saturated'])
for n, v in res['show'].items():
    print(' ', n, v)
print('band bigs', res['band_bigs'])
