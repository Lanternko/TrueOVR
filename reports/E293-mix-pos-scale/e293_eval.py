"""E-293：MIX 加分依位置縮放（預註冊 preregistration.md，sha 見 preregistration.sha256）。
臂 A／P1／P2／P3／K × λ 版本 same／aligned／bench；卡片層（T、EPM、2K 一致度、位置缺口、代表球員）＋E-290 前瞻台（只報告）。
用法（repo root）：python -I -B -X utf8 reports/E293-mix-pos-scale/e293_eval.py"""
import copy, csv, hashlib, importlib.util, json, re, sys, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr, rankdata

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


ML = mod('mix_live', 'reports/ovr-inseason-2026-27/live/mix_live.py')
CARD = ROOT / 'reports/card-0.2.13a/ranking.csv'; C14 = ROOT / 'reports/card-0.2.14/ranking.csv'
FROZEN = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214.json'
TSW = ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-08/t-swap.json'
EPM = ROOT / 'reports/impact-epm-2026-27/epm-live.csv'; TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
WPF = 0.68 / 2.80
POSW = {'PG': 0.0, 'SG': 0.0, 'SF': 0.0, 'PF': WPF, 'C': 1.0}
OK_BIGS = {'Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren', 'Evan Mobley'}
GRID = [0, .05, .1, .2, .3, .5, .75, 1.0, 1.5, 2.0]
SEED, B = 20261293, 2000
ARMS = ['A', 'P1', 'P2', 'P3', 'K']
SHOW = ['Chet Holmgren', 'Evan Mobley', 'Isaiah Hartenstein', 'Rudy Gobert', 'Jarrett Allen', 'Ivica Zubac', 'Zach Edey',
        'Victor Wembanyama', 'Anthony Davis', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Karl-Anthony Towns', 'Bam Adebayo',
        'Jaren Jackson Jr.', 'Domantas Sabonis', 'Devin Booker', 'Tyrese Maxey', 'Kevin Durant']
REF = {'Chet Holmgren': (11, 46), 'Evan Mobley': (16, 44)}   # 預註冊 L3 寫死


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s); s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return ' '.join(s.split())


def hw(h, pos, mask):
    """P3：身高 → 權重，SF/PF/C 平均身高三點線性內插，兩端截 0／1。"""
    mh = [float(h[mask & (pos == p)].mean()) for p in ('SF', 'PF', 'C')]
    return np.interp(h, mh, [0.0, WPF, 1.0]), mh


# ================================================================ 卡片
card = list(csv.DictReader(open(CARD, encoding='utf-8'))); N = len(card)
names = [r['name'] for r in card]; pos = np.array([r['pos'] for r in card])
MIN = np.array([float(r['MIN']) for r in card]); ovr0 = np.array([float(r['ovr']) for r in card])
rank0 = np.array([int(r['rank']) for r in card]); hgt = np.array([float(r['heightInches']) for r in card])
fz = json.load(open(FROZEN, encoding='utf-8')); cfg = fz['config']
pid_of = {v['name']: k for k, v in fz['players'].items()}
pids = [pid_of[n] for n in names]
ramp = np.minimum(1.0, MIN / 500.0)


def full_bonus(c):
    out = []
    for n, p in zip(names, pids):
        q = fz['players'][p]
        out.append(ML.bonus(c, q['cardRebound'], q['orebPct'], q['drebPct'], q['con2_36'], 1e9)['full'])
    return np.array(out)


A_full = full_bonus(cfg)
cK = copy.deepcopy(cfg); cK['clip'] = [0.0, 1.0]
K_full = full_bonus(cK)
c14 = {r['name']: float(r['mixBonus']) for r in csv.DictReader(open(C14, encoding='utf-8'))}
repro = float(max(abs(A_full[i] * ramp[i] - c14[n]) for i, n in enumerate(names)))
assert repro <= 0.001, repro
EP = MIN >= 500
w_h, mh_card = hw(hgt, pos, EP)
W = {'A': np.ones(N), 'P1': np.array([POSW[p] for p in pos]), 'P2': (pos == 'C').astype(float), 'P3': w_h, 'K': np.ones(N)}
SAME = {k: (K_full if k == 'K' else W[k] * A_full) * ramp for k in ARMS}
totA = SAME['A'][EP].sum()
ALIGN_C = {k: float(totA / SAME[k][EP].sum()) for k in ARMS}

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
    return {p: float(e[pp == p].mean()) for p in ('C', 'PF', 'SF', 'SG', 'PG')}


def rho(o, src, b=None):
    k = idx[src]; y = yv[src]
    if b is not None: k, y = k[b], y[b]
    return float(spearmanr(o[k], y)[0])


top10_0 = [names[i] for i in np.argsort(rank0)[:10]]


def card_eval(bonus, oA=None):
    o = np.round(ovr0 + bonus, 1); r = ranks(o)
    t10 = [names[i] for i in np.argsort(r)[:10]]
    out = {'top10': t10, 'top10_new_bigs_violating': [n for n in t10 if n not in top10_0 and pos[names.index(n)] in ('PF', 'C') and n not in OK_BIGS],
           'top30_drops': [(names[i], int(rank0[i]), int(r[i])) for i in range(N) if rank0[i] <= 30 and r[i] - rank0[i] > 10],
           'cap': float(bonus.max()), 'n_at_cap': int((bonus >= bonus.max() - 0.01).sum()) if bonus.max() > 0 else 0,
           'rho': {s: rho(o, s) for s in idx}, 'gap_T': gaps(o, 'T'), 'gap_EPM': gaps(o, 'EPM'),
           'show': {n: int(r[names.index(n)]) for n in SHOW if n in names},
           'pos_mean_bonus_min500': {p: float(bonus[EP & (pos == p)].mean()) for p in ('PG', 'SG', 'SF', 'PF', 'C')}}
    if oA is not None:
        out['drho_vs_A'] = {}
        for s in idx:
            d = np.array([rho(o, s, b) - rho(oA, s, b) for b in BOOT[s]])
            out['drho_vs_A'][s] = {'mean': out['rho'][s] - rho(oA, s), 'ci90': [float(np.percentile(d, 5)), float(np.percentile(d, 95))]}
    return out, o


# ================================================================ 前瞻台（E-290 台子）
E290 = mod('e290', 'reports/E290-reb-bonus-0213a/e290_eval.py')
E = E290.E; Q = E.Q; FOLDS, NEXT, FULL = E.FOLDS, E.NEXT, E.FULL


def bench_P(c, d):
    """回傳 {arm: P}，單位＝A（E-290 MIX，已縮放到 CPOS 均方根），P 臂＝w·MIX，K＝clip 1.0 同縮放。"""
    E290.add_arms(c, d)
    stage = {r['name']: r for r in csv.DictReader(open(E290.STAGE / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
    n = len(d['ids']); ref = d['P_ref']
    reb = np.array([float(stage[nm]['rebound']) for nm in d['names']])
    h = np.array([float(stage[nm]['heightInches']) for nm in d['names']])
    tab = E290.stats_tab(c); ob = np.full(n, np.nan); db = np.full(n, np.nan)
    for i, p in enumerate(d['ids']):
        x = tab.get(str(p))
        if x:
            if x['orebPct'] is not None: ob[i] = x['orebPct']
            if x['drebPct'] is not None: db[i] = x['drebPct']
    rz = (E290.zcol(reb) + E290.zcol(ob) + E290.zcol(db)) / 3
    js = json.loads(E.hustle_path(c).read_text(encoding='utf-8')); H = {}
    for r in js['rowSet']:
        r = dict(zip(js['headers'], r)); a = H.setdefault(int(r['PLAYER_ID']), [0.0, 0.0])
        a[0] += r['MIN'] or 0; a[1] += r['CONTESTED_SHOTS_2PT'] or 0
    v = np.zeros(n); have = np.zeros(n, bool)
    for i, p in enumerate(d['ids']):
        x = H.get(int(p))
        if x and x[0] >= 200: v[i] = x[1] / x[0] * 36; have[i] = True
    cz = np.zeros(n); cz[have] = E.zc(v[have])
    rms = lambda x: float(np.sqrt((x ** 2).mean()))
    r15, c15 = np.clip(rz, 0, 1.5), np.clip(cz, 0, 1.5)
    assert np.allclose(c15 * ref / rms(c15), d['P']['CON']), 'CON 重算不符'
    s_r, s_c = ref / rms(r15), ref / rms(c15)
    s_m = ref / rms(.5 * r15 * s_r + .5 * c15 * s_c)
    mix = (.5 * r15 * s_r + .5 * c15 * s_c) * s_m
    assert np.allclose(mix, d['P']['MIX']), 'MIX 重算不符'
    mixK = (.5 * np.clip(rz, 0, 1.0) * s_r + .5 * np.clip(cz, 0, 1.0) * s_c) * s_m
    p = d['pos']; wh, _ = hw(h, p, np.ones(n, bool))
    return {'A': mix, 'P1': np.array([POSW[x] for x in p]) * mix, 'P2': (p == 'C') * mix, 'P3': wh * mix, 'K': mixK}


def bench():
    D = {c: E.build(c) for c in FOLDS}
    PP = {c: bench_P(c, D[c]) for c in FOLDS}
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}; Y['2025-26'] = E.V.live_targets(D['2025-26']['ids'])['epm']
    YR = {c: Q.target(D[c]['ids'], NEXT[c], 'rapm') for c in FULL}
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}; w = {t: n[t] / sum(n.values()) for t in FOLDS}
    w3 = {t: n[t] / sum(n[c] for c in FULL) for t in FULL}
    m = lambda t, o, y=Y: float(Q.metrics(D[t], y[t], o)['all'])
    base = {t: m(t, D[t]['ovr']) for t in FOLDS}
    a05 = {t: m(t, E.adj(D[t], PP[t]['A'], .5)) for t in FOLDS}
    gapC0 = float(np.concatenate([E.gap(D[c], Y[c], D[c]['ovr'], 'C') for c in FOLDS]).mean())
    out = {'n': n, 'base_gap_C': gapC0, 'arms': {}}
    for arm in ARMS:
        rg = {t: {l: m(t, E.adj(D[t], PP[t][arm], l)) for l in GRID} for t in FOLDS}
        lam_s = max(GRID, key=lambda l: np.mean([rg[t][l] for t in FOLDS]))
        lofo = {t: max(GRID, key=lambda l: np.mean([rg[c][l] for c in FOLDS if c != t])) for t in FOLDS}
        r = {'lambda_star': lam_s, 'lofo_lambda': lofo,
             'd_vs_base_lofo': float(sum(w[t] * (rg[t][lofo[t]] - base[t]) for t in FOLDS)),
             'd_vs_A05_lofo': float(sum(w[t] * (rg[t][lofo[t]] - a05[t]) for t in FOLDS)),
             'd_vs_base_same05': float(sum(w[t] * (rg[t][.5] - base[t]) for t in FOLDS)),
             'fold2526_vs_base_lofo': rg['2025-26'][lofo['2025-26']] - base['2025-26'],
             'n_pos_lofo': int(sum(rg[t][lofo[t]] > base[t] for t in FOLDS)),
             'gap_C_lofo': float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], PP[t][arm], lofo[t]), 'C') for t in FOLDS]).mean()),
             'gap_PF_lofo': float(np.concatenate([E.gap(D[t], Y[t], E.adj(D[t], PP[t][arm], lofo[t]), 'PF') for t in FOLDS]).mean()),
             'rapm_vs_base_lofo': float(sum(w3[t] * (m(t, E.adj(D[t], PP[t][arm], lofo[t]), YR) - m(t, D[t]['ovr'], YR)) for t in FULL)),
             'rho_grid': {t: {str(l): v for l, v in rg[t].items()} for t in FOLDS}}
        out['arms'][arm] = r
        print(f"bench {arm}: λ*={lam_s} lofo={list(lofo.values())} Δbase={r['d_vs_base_lofo']:+.4f} ΔA05={r['d_vs_A05_lofo']:+.4f} "
              f"same0.5 Δbase={r['d_vs_base_same05']:+.4f} fold26={r['fold2526_vs_base_lofo']:+.4f} pos={r['n_pos_lofo']}/4 gapC {gapC0:+.3f}->{r['gap_C_lofo']:+.3f} PF {r['gap_PF_lofo']:+.3f} RAPM {r['rapm_vs_base_lofo']:+.4f}")
    out['gap_PF_base'] = float(np.concatenate([E.gap(D[c], Y[c], D[c]['ovr'], 'PF') for c in FOLDS]).mean())
    return out


def main():
    res = {'prereg_sha256': sha(HERE / 'preregistration.md'),
           'sources_sha256': {'card_0213a': sha(CARD), 'card_0214': sha(C14), 'mix_pool': sha(FROZEN), 't_swap': sha(TSW), 'epm': sha(EPM), '2k27': sha(TWOK)},
           'repro_A_vs_card0214_maxabs': repro, 'height_means_SF_PF_C': mh_card, 'align_c': ALIGN_C,
           'n_match': {s: int(len(idx[s])) for s in idx}}
    bn = bench(); res['bench'] = bn
    ov0, _ = card_eval(np.zeros(N)); res['card_0213a'] = ov0
    evA, oA = card_eval(SAME['A']); res['card_A'] = evA
    gap0 = ov0['gap_T']['C']
    res['card'] = {}
    for arm in ARMS:
        lam_b = bn['arms'][arm]['lambda_star']
        for var, b in (('same', SAME[arm]), ('aligned', SAME[arm] * ALIGN_C[arm]), ('bench', SAME[arm] * lam_b / 0.5)):
            ev, o = card_eval(b, oA)
            L1 = not any(v['mean'] < -0.005 and v['ci90'][1] < 0 for v in ev['drho_vs_A'].values())
            L2 = True if gap0 <= 0 else ev['gap_T']['C'] <= 0.5 * gap0
            L3 = all(REF[n][0] <= ev['show'][n] <= REF[n][1] for n in REF)
            L4 = (not ev['top10_new_bigs_violating']) and len(ev['top30_drops']) <= 2
            ev['checks'] = {'L1': L1, 'L2': L2, 'L3': L3, 'L4': L4}
            ev['verdict'] = 'control' if arm in ('A', 'K') else ('adopt_candidate' if (L1 and L2 and L3 and L4) else 'reject')
            ev['lambda'] = {'same': 0.5, 'aligned': 0.5 * ALIGN_C[arm], 'bench': lam_b}[var]
            res['card'][f'{arm}-{var}'] = ev
            print(f"{arm}-{var:7s} λ={ev['lambda']:.3f} {ev['verdict']:15s} {ev['checks']} ρ " + ' '.join(f"{s}{ev['rho'][s]:.4f}({ev['drho_vs_A'][s]['mean']:+.4f})" for s in idx)
                  + f" gapC {ev['gap_T']['C']:+.3f} PF {ev['gap_T']['PF']:+.3f} cap {ev['cap']:.2f}/{ev['n_at_cap']} drops {len(ev['top30_drops'])} viol {ev['top10_new_bigs_violating']}")
            print('    ', {k: v for k, v in ev['show'].items()})
    order = [f'{a}-{v}' for a in ('P1', 'P3', 'P2') for v in ('same', 'aligned', 'bench')]
    pick = next((k for k in order if res['card'][k]['verdict'] == 'adopt_candidate'), None)
    res['pick'] = pick
    res['ref_ranks'] = {n: {'T': rT.get(pids[names.index(n)]), 'EPM': rE.get(pids[names.index(n)]), '2K': rK.get(norm(n)),
                            'pos': pos[names.index(n)], 'h': hgt[names.index(n)], 'MIN': MIN[names.index(n)], 'rank_0213a': int(rank0[names.index(n)]),
                            'w_P3': float(w_h[names.index(n)]), 'bonus_A': float(SAME['A'][names.index(n)])} for n in SHOW if n in names}
    print('base gap T', ov0['gap_T'], 'A', evA['gap_T'], 'pick', pick)
    print('0.2.13a ρ', ov0['rho'], 'A ρ', evA['rho'])
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x)), encoding='utf-8')
    if pick:
        arm, var = pick.split('-')
        b = {'same': SAME[arm], 'aligned': SAME[arm] * ALIGN_C[arm], 'bench': SAME[arm] * bn['arms'][arm]['lambda_star'] / 0.5}[var]
        np.savez(HERE / 'bonus_pick.npz', names=np.array(names), bonus=b, pick=np.array(pick))


if __name__ == '__main__':
    main()
