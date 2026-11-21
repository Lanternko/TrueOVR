"""E-294：MIX 加分改同位置比較＋軟上限（預註冊 preregistration.md，sha 見 preregistration.sha256）。
因子：z 的尺 {L 全聯盟, P 同位置} × 飽和 {clip 硬上限 1.5, soft 1.5·tanh(z⁺/1.5)} × 位置權重 {1, w(pos) C=1 PF=0.243 其他 0}。
  A=L-clip-1（現行 0.2.14）、K=L-soft-1、P1=L-clip-w（E-293）、KW=L-soft-w、S1=P-clip-1、S4=P-soft-1、S2=P-clip-w、S3=P-soft-w。
每臂兩種 λ：same（0.5）、aligned（MIN≥500 總加分量＝A）。500 分鐘以下 × MIN/500（E-292）。
用法（repo root）：python -I -B -X utf8 reports/E294-mix-pos-z-soft/e294_eval.py [--explore]"""
import csv, hashlib, importlib.util, json, re, sys, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr, rankdata

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
EXPLORE = '--explore' in sys.argv
if not EXPLORE:
    assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


CARD = ROOT / 'reports/card-0.2.13a/ranking.csv'; C14 = ROOT / 'reports/card-0.2.14/ranking.csv'
FROZEN = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214.json'
STATS25 = ROOT / 'reports/E227-lineup-transformer-r2/data/stats-2025-26.csv'
TSW = ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-08/t-swap.json'
EPM = ROOT / 'reports/impact-epm-2026-27/epm-live.csv'; TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
WPF = 0.68 / 2.80
POSW = {'PG': 0.0, 'SG': 0.0, 'SF': 0.0, 'PF': WPF, 'C': 1.0}
POSL = ('PG', 'SG', 'SF', 'PF', 'C')
HI = 1.5
ARMS = {'A': ('L', 'clip', '1'), 'K': ('L', 'soft', '1'), 'P1': ('L', 'clip', 'w'), 'KW': ('L', 'soft', 'w'),
        'S1': ('P', 'clip', '1'), 'S4': ('P', 'soft', '1'), 'S2': ('P', 'clip', 'w'), 'S3': ('P', 'soft', 'w'),
        'H': ('H.5', 'soft', 'w'), 'H1': ('H.5', 'soft', '1'), 'Hq': ('H.25', 'soft', 'w'), 'H3q': ('H.75', 'soft', 'w')}
CAND = ('S3', 'S2', 'H', 'H1')                     # 可產卡的臂（優先序）；其他是對照／敏感度
SEED, B = 20261294, 2000
GRID = [0, .05, .1, .2, .3, .5, .75, 1.0, 1.5, 2.0]
SHOW = ['Chet Holmgren', 'Evan Mobley', 'Joel Embiid', 'Anthony Davis', 'Karl-Anthony Towns', 'Domantas Sabonis', 'Ivica Zubac',
        'Rudy Gobert', 'Jarrett Allen', 'Isaiah Hartenstein', 'Zach Edey', 'Victor Wembanyama', 'Nikola Jokić', 'Giannis Antetokounmpo',
        'Bam Adebayo', 'Alperen Sengun', 'Jaren Jackson Jr.', 'Devin Booker', 'Tyrese Maxey']
KEEP_C = ['Rudy Gobert', 'Jarrett Allen', 'Isaiah Hartenstein', 'Ivica Zubac', 'Zach Edey', 'Victor Wembanyama']
TOP_REB = ['Rudy Gobert', 'Jarrett Allen', 'Domantas Sabonis']
REF = {'Chet Holmgren': (11, 46), 'Evan Mobley': (16, 44)}   # 同 E-293 L3


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s); s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return ' '.join(s.split())


def sat(x, kind):
    x = np.maximum(x, 0.0)
    return np.minimum(x, HI) if kind == 'clip' else HI * np.tanh(x / HI)


def zfeat(v, have, pool, pos, mode):
    """v 原始值；have 有值；pool 算尺的人群；mode L＝全聯盟、P＝同位置、H.a＝全聯盟尺但位置平均只留 a 倍
    （z_H＝a·m_pos＋(z_L−m_pos)，m_pos＝該位置在 pool 的全聯盟 z 平均）。沒值記 0（H 臂沒值記 a·m_pos）。"""
    z = np.zeros(len(v))
    if mode.startswith('H'):
        a = float(mode[1:]); zl = zfeat(v, have, pool, pos, 'L'); out = zl.copy()
        for p in POSL:
            g = pos == p; mp = zl[pool & have & g].mean()
            out[g & have] = zl[g & have] - (1 - a) * mp
            out[g & ~have] = a * mp
        return out
    groups = [np.ones(len(v), bool)] if mode == 'L' else [pos == p for p in POSL]
    for g in groups:
        k = pool & have & g
        mu, s = v[k].mean(), v[k].std()
        m = have & g
        z[m] = (v[m] - mu) / s
    return z


def build_P(feat, pool, pos, ref, zmode, kind, wmode):
    """回傳 (P, capP)：P＝0.5·REBc·s_reb＋0.5·CON·s_con 再 ×s_mix，均方根縮放在 pool 上對到 ref；再 × 位置權重。"""
    reb, ob, db, con = feat['reb'], feat['ob'], feat['db'], feat['con']
    zr = (zfeat(reb[0], reb[1], pool, pos, zmode) + zfeat(ob[0], ob[1], pool, pos, zmode) + zfeat(db[0], db[1], pool, pos, zmode)) / 3
    zc = zfeat(con[0], con[1], pool, pos, zmode)
    r, c = sat(zr, kind), sat(zc, kind)
    rms = lambda x: float(np.sqrt((x[pool] ** 2).mean()))
    s_r, s_c = ref / rms(r), ref / rms(c)
    mix0 = .5 * r * s_r + .5 * c * s_c
    s_m = ref / rms(mix0)
    w = np.array([POSW[p] for p in pos]) if wmode == 'w' else np.ones(len(pos))
    capP = (.5 * HI * s_r + .5 * HI * s_c) * s_m * w
    return mix0 * s_m * w, capP, {'zr': zr, 'zc': zc, 'rebc': r, 'con': c}


# ================================================================ 卡片
card = list(csv.DictReader(open(CARD, encoding='utf-8'))); N = len(card)
names = [r['name'] for r in card]; pos = np.array([r['pos'] for r in card])
MIN = np.array([float(r['MIN']) for r in card]); ovr0 = np.array([float(r['ovr']) for r in card])
rank0 = np.array([int(r['rank']) for r in card])
fz = json.load(open(FROZEN, encoding='utf-8')); cfg = fz['config']
pid_of = {v['name']: k for k, v in fz['players'].items()}
pids = [pid_of[n] for n in names]
cnt = {}
for r in csv.DictReader(open(STATS25, encoding='utf-8')):
    cnt[norm(r['name'])] = cnt.get(norm(r['name']), 0) + 1
uniq = np.array([cnt.get(norm(n), 0) == 1 for n in names])
EPZ = (MIN >= 500) & uniq            # 算尺人群（同 mix_live.freeze）
EP = MIN >= 500                      # 報告人群（同 E-293）
assert EPZ.sum() == fz['epN'], (EPZ.sum(), fz['epN'])


def arr(key):
    v = np.array([np.nan if fz['players'][p][key] is None else fz['players'][p][key] for p in pids], float)
    return (np.nan_to_num(v), np.isfinite(v))


FEAT = {'reb': (np.array([fz['players'][p]['cardRebound'] for p in pids], float), np.ones(N, bool)),
        'ob': arr('orebPct'), 'db': arr('drebPct'), 'con': arr('con2_36')}
ramp = np.minimum(1.0, MIN / 500.0)
LAM, SD, REFC = cfg['lambda'], cfg['sd'], cfg['ref']
PC, CAPC, PARTS = {}, {}, {}
for a, (zm, kd, wm) in ARMS.items():
    PC[a], CAPC[a], PARTS[a] = build_P(FEAT, EPZ, pos, REFC, zm, kd, wm)
c14 = {r['name']: float(r['mixBonus']) for r in csv.DictReader(open(C14, encoding='utf-8'))}
repro = float(max(abs(LAM * SD * PC['A'][i] * ramp[i] - c14[n]) for i, n in enumerate(names)))
assert repro <= 0.001, repro
SAME = {a: LAM * SD * PC[a] * ramp for a in ARMS}
totA = SAME['A'][EP].sum()
ALIGN_C = {a: float(totA / SAME[a][EP].sum()) for a in ARMS}
BON = {}
CAPB = {}
for a in ARMS:
    BON[(a, 'same')] = SAME[a]; CAPB[(a, 'same')] = LAM * SD * CAPC[a]
    BON[(a, 'aligned')] = SAME[a] * ALIGN_C[a]; CAPB[(a, 'aligned')] = LAM * SD * CAPC[a] * ALIGN_C[a]

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


def pct(v):
    return (rankdata(v) - 0.5) / len(v)


def gaps(o, src):
    k = idx[src]; e = pct(yv[src]) - pct(o[k]); pp = pos[k]
    return {p: float(e[pp == p].mean()) for p in POSL}


def rho(o, src, b=None):
    k = idx[src]; y = yv[src]
    if b is not None: k, y = k[b], y[b]
    return float(spearmanr(o[k], y)[0])


def ties50(o, r):
    top = np.round(o[r <= 50], 1)
    v, c = np.unique(top, return_counts=True)
    return int((c >= 2).sum()), int(c[c >= 2].sum())


def disc(bonus, cap):
    m = EP & (cap > 0)
    near = m & (bonus >= cap - 0.2)
    cb = bonus[EP & (pos == 'C')]
    pf = bonus[EP & (pos == 'PF')]
    q = lambda x, p: float(np.percentile(x, p))
    top30 = np.sort(bonus[EP])[::-1][:30]
    _, cnts = np.unique(np.round(top30, 1), return_counts=True)
    return {'n_near_cap': int(near.sum()), 'near_cap_names': [names[i] for i in np.where(near)[0]],
            'cap_C': float(cap[pos == 'C'].max()), 'max_bonus': float(bonus.max()),
            'C_sd': float(cb.std()), 'C_iqr': q(cb, 75) - q(cb, 25), 'C_p10_p90': [q(cb, 10), q(cb, 90)], 'C_mean': float(cb.mean()),
            'PF_mean': float(pf.mean()), 'n_pos_bonus_min500': int((EP & (bonus > 0.05)).sum()),
            'max_same_bonus_group': int(cnts.max()) if len(cnts) else 0,
            'top10_bonus': [(names[i], pos[i], round(float(bonus[i]), 2)) for i in np.argsort(-bonus)[:10]],
            'pos_mean_min500': {p: float(bonus[EP & (pos == p)].mean()) for p in POSL}}


top10_0 = [names[i] for i in np.argsort(rank0)[:10]]


def card_eval(bonus, cap, oA=None):
    o = np.round(ovr0 + bonus, 1); r = ranks(o)
    t10 = [names[i] for i in np.argsort(r)[:10]]
    out = {'top10': [(n, pos[names.index(n)]) for n in t10],
           'top10_nPFC': int(sum(pos[names.index(n)] in ('PF', 'C') for n in t10)),
           'rank11_20': [(names[i], pos[i], int(r[i])) for i in np.argsort(r)[10:20]],
           'top30_drops': [(names[i], int(rank0[i]), int(r[i])) for i in range(N) if rank0[i] <= 30 and r[i] - rank0[i] > 10],
           'ties50': ties50(o, r), 'rho': {s: rho(o, s) for s in idx}, 'gap_T': gaps(o, 'T'), 'gap_EPM': gaps(o, 'EPM'),
           'show': {n: {'rank': int(r[names.index(n)]), 'bonus': round(float(bonus[names.index(n)]), 2)} for n in SHOW if n in names},
           'disc': disc(bonus, cap)}
    if oA is not None:
        out['drho_vs_A'] = {}
        for s in idx:
            d = np.array([rho(o, s, b) - rho(oA, s, b) for b in BOOT[s]])
            out['drho_vs_A'][s] = {'mean': out['rho'][s] - rho(oA, s), 'ci90': [float(np.percentile(d, 5)), float(np.percentile(d, 95))]}
    return out, o


# ================================================================ 前瞻台（E-290 台子，只報告）
def bench():
    E290 = mod('e290', 'reports/E290-reb-bonus-0213a/e290_eval.py')
    E = E290.E; Q = E.Q; FOLDS, NEXT, FULL = E.FOLDS, E.NEXT, E.FULL
    D = {c: E.build(c) for c in FOLDS}
    PP = {}
    for c in FOLDS:
        d = D[c]; E290.add_arms(c, d)
        stage = {r['name']: r for r in csv.DictReader(open(E290.STAGE / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
        n = len(d['ids'])
        reb = np.array([float(stage[nm]['rebound']) for nm in d['names']])
        tab = E290.stats_tab(c); ob = np.full(n, np.nan); db = np.full(n, np.nan)
        for i, p in enumerate(d['ids']):
            x = tab.get(str(p))
            if x:
                if x['orebPct'] is not None: ob[i] = x['orebPct']
                if x['drebPct'] is not None: db[i] = x['drebPct']
        js = json.loads(E.hustle_path(c).read_text(encoding='utf-8')); H = {}
        for r in js['rowSet']:
            r = dict(zip(js['headers'], r)); a = H.setdefault(int(r['PLAYER_ID']), [0.0, 0.0])
            a[0] += r['MIN'] or 0; a[1] += r['CONTESTED_SHOTS_2PT'] or 0
        v = np.zeros(n); have = np.zeros(n, bool)
        for i, p in enumerate(d['ids']):
            x = H.get(int(p))
            if x and x[0] >= 200: v[i] = x[1] / x[0] * 36; have[i] = True
        feat = {'reb': (reb, np.ones(n, bool)), 'ob': (np.nan_to_num(ob), np.isfinite(ob)), 'db': (np.nan_to_num(db), np.isfinite(db)),
                'con': (v, have)}
        allp = np.ones(n, bool)
        PP[c] = {a: build_P(feat, allp, d['pos'], d['P_ref'], *ARMS[a])[0] for a in ARMS}
        assert np.allclose(PP[c]['A'], d['P']['MIX']), 'MIX 重算不符'
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}; Y['2025-26'] = E.V.live_targets(D['2025-26']['ids'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}; w = {t: n[t] / sum(n.values()) for t in FOLDS}
    m = lambda t, o: float(Q.metrics(D[t], Y[t], o)['all'])
    base = {t: m(t, D[t]['ovr']) for t in FOLDS}
    a05 = {t: m(t, E.adj(D[t], PP[t]['A'], .5)) for t in FOLDS}
    out = {'n': n, 'arms': {}}
    for a in ARMS:
        rg = {t: {l: m(t, E.adj(D[t], PP[t][a], l)) for l in GRID} for t in FOLDS}
        lofo = {t: max(GRID, key=lambda l: np.mean([rg[c][l] for c in FOLDS if c != t])) for t in FOLDS}
        r = {'lofo_lambda': lofo,
             'same05_vs_base': float(sum(w[t] * (rg[t][.5] - base[t]) for t in FOLDS)),
             'same05_vs_A05': float(sum(w[t] * (rg[t][.5] - a05[t]) for t in FOLDS)),
             'lofo_vs_base': float(sum(w[t] * (rg[t][lofo[t]] - base[t]) for t in FOLDS)),
             'n_pos_same05_vs_A05': int(sum(rg[t][.5] > a05[t] for t in FOLDS)),
             'gap_C_same05': float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], PP[t][a], .5), 'C') for t in FOLDS]).mean()),
             'gap_PF_same05': float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], PP[t][a], .5), 'PF') for t in FOLDS]).mean())}
        out['arms'][a] = r
        print(f"bench {a:3s} same0.5 Δbase={r['same05_vs_base']:+.4f} ΔA={r['same05_vs_A05']:+.4f} ({r['n_pos_same05_vs_A05']}/4) lofo={list(lofo.values())} Δbase={r['lofo_vs_base']:+.4f} gapC {r['gap_C_same05']:+.3f} PF {r['gap_PF_same05']:+.3f}")
    out['gap_C_base'] = float(np.concatenate([E.gap(D[c], Y[c], D[c]['ovr'], 'C') for c in FOLDS]).mean())
    out['gap_PF_base'] = float(np.concatenate([E.gap(D[c], Y[c], D[c]['ovr'], 'PF') for c in FOLDS]).mean())
    return out


def ok_big(n):
    """R-182／R-007：新進前十的 PF/C 至少一個參考名次對得上（T≤50 或 EPM≤50 或 2K≤30）；吃餅長人（三者都對不上）不行。"""
    i = names.index(n); t, e, k = rT.get(pids[i]), rE.get(pids[i]), rK.get(norm(n))
    return (t is not None and t <= 50) or (e is not None and e <= 50) or (k is not None and k <= 30)


def checks(ev, evA, ev0):
    dsc = ev['disc']; sh = ev['show']; b = lambda n: sh[n]['bonus']
    G1 = (dsc['n_near_cap'] <= 5 and ev['ties50'][0] <= evA['ties50'][0] and dsc['max_same_bonus_group'] <= 3
          and dsc['C_sd'] >= evA['disc']['C_sd'])
    G2 = not any(v['mean'] < -0.005 and v['ci90'][1] < 0 for v in ev['drho_vs_A'].values())
    G3a = all(sh[n]['rank'] < ev0['show'][n]['rank'] for n in KEEP_C)
    G3b = min(b(n) for n in TOP_REB) >= b('Joel Embiid') + 1.0 and b('Rudy Gobert') >= b('Karl-Anthony Towns') + 1.0
    G4 = (all(evA['show'][n]['rank'] + 3 <= sh[n]['rank'] <= REF[n][1] for n in REF)
          and b('Joel Embiid') <= evA['show']['Joel Embiid']['bonus'] - 2.0)
    new_bigs = [n for n, p in ev['top10'] if n not in top10_0 and p in ('PF', 'C')]
    G5 = all(ok_big(n) for n in new_bigs) and len(ev['top30_drops']) <= 2
    return {'G1': G1, 'G2': G2, 'G3': G3a and G3b, 'G3a': G3a, 'G3b': G3b, 'G4': G4, 'G5': G5, 'new_bigs_top10': new_bigs}


def main():
    res = {'sources_sha256': {'card_0213a': sha(CARD), 'card_0214': sha(C14), 'mix_pool': sha(FROZEN), 't_swap': sha(TSW), 'epm': sha(EPM), '2k27': sha(TWOK)},
           'repro_A_vs_card0214_maxabs': repro, 'align_c': ALIGN_C, 'n_match': {s: int(len(idx[s])) for s in idx}}
    if not EXPLORE:
        res['prereg_sha256'] = sha(HERE / 'preregistration.md')
        res['bench'] = bench()
    ev0, _ = card_eval(np.zeros(N), np.zeros(N)); res['card_0213a'] = ev0
    evA, oA = card_eval(BON[('A', 'same')], CAPB[('A', 'same')]); res['card_A'] = evA
    print('0.2.13a rank11-20', ev0['rank11_20']); print('A top10', evA['top10']); print('A 11-20', evA['rank11_20'])
    print('A ties50', evA['ties50'], '0213a ties50', ev0['ties50'])
    res['card'] = {}
    for a in ARMS:
        for var in ('same', 'aligned'):
            ev, o = card_eval(BON[(a, var)], CAPB[(a, var)], oA)
            ev['checks'] = checks(ev, evA, ev0)
            ev['verdict'] = 'control' if a not in CAND else ('adopt_candidate' if all(ev['checks'][g] for g in ('G1', 'G2', 'G3', 'G4', 'G5')) else 'reject')
            ev['lambda'] = LAM * (1 if var == 'same' else ALIGN_C[a])
            res['card'][f'{a}-{var}'] = ev
            d = ev['disc']
            print(f"\n{a}-{var:7s} λ={ev['lambda']:.3f} {ev['verdict']} {ev['checks']}")
            print(f"  near_cap {d['n_near_cap']} maxsame {d['max_same_bonus_group']} capC {d['cap_C']:.2f} C sd {d['C_sd']:.2f} iqr {d['C_iqr']:.2f} Cmean {d['C_mean']:.2f} PFmean {d['PF_mean']:.2f} ties50 {ev['ties50']} nPFC10 {ev['top10_nPFC']} drops {len(ev['top30_drops'])}")
            print('  ρ', {s: round(ev['rho'][s], 4) for s in idx}, {s: round(ev['drho_vs_A'][s]['mean'], 4) for s in idx})
            print('  top10', [x[0] for x in ev['top10']])
            print('  show', {k: (v['rank'], v['bonus']) for k, v in ev['show'].items()})
            print('  topbonus', d['top10_bonus'])
    order = [f'{a}-{v}' for a in CAND for v in ('same', 'aligned')]
    pick = next((k for k in order if res['card'][k]['verdict'] == 'adopt_candidate'), None)
    res['pick'] = pick
    res['ref_ranks'] = {n: {'T': rT.get(pids[names.index(n)]), 'EPM': rE.get(pids[names.index(n)]), '2K': rK.get(norm(n)),
                            'pos': pos[names.index(n)], 'MIN': MIN[names.index(n)], 'rank_0213a': int(rank0[names.index(n)])} for n in SHOW if n in names}
    print('pick', pick)
    out = HERE / ('explore.json' if EXPLORE else 'results.json')
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x)), encoding='utf-8')
    if pick and not EXPLORE:
        a, v = pick.split('-')
        np.savez(HERE / 'bonus_pick.npz', names=np.array(names), bonus=BON[(a, v)], pick=np.array(pick))


if __name__ == '__main__':
    main()
