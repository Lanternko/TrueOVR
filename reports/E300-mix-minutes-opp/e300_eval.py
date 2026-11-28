"""E-300：MIX 加分照 OVR 分鐘曲線 W(m)＋籃板／干擾按在場對手修正。預註冊 preregistration.md（sha 見 preregistration.sha256）。
重用 E-295（公式、卡片評估）與 E-298（前瞻台結構）。
用法（repo root）：python -I -B -X utf8 reports/E300-mix-minutes-opp/e300_eval.py [--dry]
  --dry：凍結前檢查，只印暴露量、係數與 W1 的 live S1（不算候選臂）。"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
DRY = '--dry' in sys.argv
if not DRY:
    assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'

sys.argv.append('--explore')   # 只為略過 e295 自己的預註冊 sha 斷言
s = importlib.util.spec_from_file_location('e295', ROOT / 'reports/E295-mix-pos-continuous/e295_eval.py')
M = importlib.util.module_from_spec(s); sys.modules['e295'] = M; s.loader.exec_module(M)

SEED, B = 20261300, 2000
N, names, pids = M.N, M.names, M.pids
card = list(csv.DictReader(open(M.CARD, encoding='utf-8')))
MPG = np.array([float(r['mpg'] or 0) for r in card])
CW1 = M.SPEC['W1'][1]
STINTS = {'2022-23': ROOT / 'reports/defense-seventh/2022-23/stints/stints.jsonl',
          '2023-24': ROOT / 'reports/defense-seventh/2023-24/stints/stints.jsonl',
          '2024-25': ROOT / 'reports/defense-seventh/2024-25/stints/stints.jsonl',
          '2025-26': ROOT / 'reports/defense-b1/stints.jsonl'}
POOL_MIN = 500.0


def W(m):
    return np.minimum(1.0, (1 - np.exp(-np.asarray(m, float) / 15)) / (1 - np.exp(-36 / 15)))


# ================================================================ 對手修正
_ST = {}


def load_stints(season):
    if season not in _ST:
        out = []
        for line in open(STINTS[season], encoding='utf-8'):
            d = json.loads(line)
            if len(d['teams']) != 2 or d['seconds'] <= 0: continue
            out.append(d)
        _ST[season] = out
    return _ST[season]


def opp_adjust(season, ids, ob, hob, db, hdb, con, hcon, ovr=None):
    """ids: list[str]。回傳 (ob_adj, db_adj, con_adj, info)。"""
    st = load_stints(season)
    ix = {str(p): i for i, p in enumerate(ids)}
    n = len(ids)
    sec = np.zeros(n)
    for d in st:
        for t in d['teams']:
            for p in t['players']:
                j = ix.get(str(p))
                if j is not None: sec[j] += d['seconds']
    pool = sec >= POOL_MIN * 60
    mob = ob[pool & hob].mean(); mdb = db[pool & hdb].mean()
    obv = np.where(hob, ob, mob); dbv = np.where(hdb, db, mdb)
    OBm = {str(p): obv[i] for i, p in enumerate(ids)}; DBm = {str(p): dbv[i] for i, p in enumerate(ids)}
    sOB = lambda ps: sum(OBm.get(str(p), mob) for p in ps)
    sDB = lambda ps: sum(DBm.get(str(p), mdb) for p in ps)
    # 每段：防守隊 k（players_k），對手 j；teams[k].opponent＝對手 j 打 k 的進攻
    Y, X1, X2, Wt = [], [], [], []
    eOB = np.zeros(n); eDB = np.zeros(n); e2 = np.zeros(n); eO = np.zeros(n); esec = np.zeros(n)
    for d in st:
        T = d['teams']
        for k in (0, 1):
            pk, pj = T[k]['players'], T[1 - k]['players']
            o = T[k]['opponent']; ro = o['reboundOpportunities']
            if ro > 0:
                Y.append((o['oreb'] + o['teamOreb']) / ro); X1.append(sDB(pk)); X2.append(sOB(pj)); Wt.append(ro)
            a2 = o['midA'] + o['shortA']; so, sd_ = sOB(pj), sDB(pj)
            oo = np.mean([ovr.get(str(p), np.nan) for p in pj]) if ovr is not None else np.nan
            for p in pk:
                j = ix.get(str(p))
                if j is None: continue
                w = d['seconds']; esec[j] += w; eOB[j] += w * so; eDB[j] += w * sd_; e2[j] += a2
                if np.isfinite(oo): eO[j] += w * oo
    Y, X1, X2, Wt = map(np.array, (Y, X1, X2, Wt))
    A = np.column_stack([np.ones_like(Y), X1, X2]); sw = np.sqrt(Wt)
    coef = np.linalg.lstsq(A * sw[:, None], Y * sw, rcond=None)[0]
    b1, b2 = coef[1], coef[2]          # b1：防守五人 drebPct 和 → 對手 OREB%（預期負）；b2：對手 orebPct 和（預期正）
    Obar = float((Y * Wt).sum() / Wt.sum()); Dbar = 1 - Obar
    es = np.where(esec > 0, esec, 1)
    oppOB, oppDB = eOB / es, eDB / es
    opp2 = e2 / (es / 60) * 36
    oppOVR = eO / es if ovr is not None else None
    mOB, mDB = np.average(oppOB[pool], weights=esec[pool]), np.average(oppDB[pool], weights=esec[pool])
    m2 = np.average(opp2[pool], weights=esec[pool])
    has = esec > 0
    # 本隊防守籃板：對手 orebPct 和高 → 對手 OREB% 升 b2·Δ → 本隊 DREB% 降
    db_adj = np.where(has, db * Dbar / (Dbar - b2 * (oppOB - mOB)), db)
    # 本隊進攻籃板：對手 drebPct 和高 → 本隊 OREB% 變 b1·Δ（同一迴歸的防守端係數）
    ob_adj = np.where(has, ob * Obar / (Obar + b1 * (oppDB - mDB)), ob)
    con_adj = np.where(has & (opp2 > 0), con * m2 / np.where(opp2 > 0, opp2, 1), con)
    info = {'b_def_dreb': float(b1), 'b_opp_oreb': float(b2), 'Obar': Obar, 'n_seg': int(len(Y)),
            'pool_n': int(pool.sum()), 'oppOB': oppOB, 'oppDB': oppDB, 'opp2PA36': opp2, 'oppOVR': oppOVR, 'sec': esec,
            'm2': float(m2), 'mOB': float(mOB), 'mDB': float(mDB)}
    return ob_adj, db_adj, con_adj, info


# ================================================================ 卡片臂
ob0, hob = M.FEAT['ob']; db0, hdb = M.FEAT['db']; c0, hc = M.FEAT['con']
OVRMAP = {pids[i]: M.ovr0[i] for i in range(N)}
obA, dbA, cA, INF = opp_adjust('2025-26', pids, ob0, hob, db0, hdb, c0, hc, OVRMAP)
FEAT_O = {'reb': M.FEAT['reb'], 'ob': (obA, hob), 'db': (dbA, hdb), 'con': (cA, hc)}
P_O = M.build(FEAT_O, M.EPZ, *M.SPEC['W1'])[0]
BW1 = M.BON['W1']
BON = {'A': M.BON['A'], 'W1': BW1, 'M': BW1 * W(MPG), 'O': M.LAM * M.SD * P_O * M.ramp}
BON['MO'] = BON['O'] * W(MPG)
CAND = ('M', 'O', 'MO')
WATCH = ['Deni Avdija', 'Donovan Clingan', 'Robert Williams III', 'Jrue Holiday', 'Rudy Gobert', 'Nikola Jokić', 'Victor Wembanyama',
         'Anthony Davis', 'Karl-Anthony Towns', 'Joel Embiid', 'Chet Holmgren', 'Evan Mobley', 'Ivica Zubac', 'Jarrett Allen',
         'Clint Capela', 'Mitchell Robinson', 'Isaiah Hartenstein', 'Domantas Sabonis', 'Alperen Sengun', 'Bam Adebayo',
         'Jalen Duren', 'Walker Kessler', 'Daniel Gafford', 'Dereck Lively II', 'Nic Claxton', 'Onyeka Okongwu', 'Zach Edey',
         'Goga Bitadze', 'Luke Kornet', 'Scottie Barnes', 'Toumani Camara']

# ================================================================ live
LROWS = list(csv.DictReader(open(M.LIVE_RANK, encoding='utf-8')))
LMPG = {r['playerId']: float(r['MPGhat'] or r['MPG0'] or 0) for r in LROWS}
PIX = {p: i for i, p in enumerate(pids)}


def live(a):
    o0 = np.array([float(r['ovr']) - float(r['mixBonus'] or 0) for r in LROWS])
    b = np.array([float(r['mixBonus'] or 0) for r in LROWS]); mp = np.array([LMPG[r['playerId']] for r in LROWS])
    ratio = np.ones(len(LROWS))
    base = 'O' if a in ('O', 'MO') else None
    if base:
        for k, r in enumerate(LROWS):
            i = PIX.get(r['playerId'])
            if i is not None and BW1[i] > 0.05: ratio[k] = BON['O'][i] / BW1[i]
    bb = b * ratio
    if a in ('M', 'MO'): bb = bb * W(mp)
    o = np.round(o0 + bb, 1)
    order = np.argsort(-o, kind='stable'); rk = np.empty(len(LROWS), int); rk[order] = np.arange(1, len(LROWS) + 1)
    nm = [r['name'] for r in LROWS]
    return {n: (int(rk[nm.index(n)]), float(o[nm.index(n)]), round(float(bb[nm.index(n)]), 2)) for n in WATCH if n in nm}


# ================================================================ S3 目標：T·W、EPM·W
def weighted_targets():
    idx, yv = {}, {}
    for src in ('T', 'EPM'):
        k = [j for j, i in enumerate(M.idx[src]) if pids[i] in LMPG]
        ii = M.idx[src][k]; y = M.yv[src][k]
        q = np.percentile(y, 20)
        idx[src + 'W'] = ii; yv[src + 'W'] = (y - q) * W(np.array([LMPG[pids[i]] for i in ii]))
    idx['2K'], yv['2K'] = M.idx['2K'], M.yv['2K']
    return idx, yv


RAW_IDX, RAW_YV = dict(M.idx), dict(M.yv)
WI, WY = weighted_targets()


def set_targets(idx, yv, seed):
    rng = np.random.default_rng(seed)
    M.idx, M.yv = idx, yv
    M.BOOT = {k: [rng.integers(0, len(idx[k]), len(idx[k])) for _ in range(B)] for k in idx}


def ranks(o):
    order = sorted(range(N), key=lambda i: (-o[i], M.rank0[i])); r = np.empty(N, int); r[order] = np.arange(1, N + 1); return r


# ================================================================ 前瞻台
def bench():
    E290 = M.mod('e290', 'reports/E290-reb-bonus-0213a/e290_eval.py')
    E = E290.E; Q = E.Q; FOLDS, NEXT, FULL = E.FOLDS, E.NEXT, E.FULL
    D = {c: E.build(c) for c in FOLDS}
    PP, finfo = {}, {}
    for c in FOLDS:
        d = D[c]; E290.add_arms(c, d)
        stage = {r['name']: r for r in csv.DictReader(open(E290.STAGE / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
        cardS = {r['name']: r for r in csv.DictReader(open(E.CARD / f'ranking-S-{c}.csv', encoding='utf-8-sig'))}
        n = len(d['ids'])
        reb = np.array([float(stage[nm]['rebound']) for nm in d['names']])
        hgt = np.array([float(cardS[nm]['heightInches']) for nm in d['names']])
        mpg = np.array([float(cardS[nm]['mpg'] or 0) for nm in d['names']])
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
        hob_, hdb_ = np.isfinite(ob), np.isfinite(db)
        ids = [str(p) for p in d['ids']]
        oa, da, ca, inf = opp_adjust(c, ids, np.nan_to_num(ob), hob_, np.nan_to_num(db), hdb_, v, have)
        finfo[c] = {'b_def_dreb': inf['b_def_dreb'], 'b_opp_oreb': inf['b_opp_oreb'], 'n_seg': inf['n_seg']}
        feat = {'reb': (reb, np.ones(n, bool)), 'ob': (np.nan_to_num(ob), hob_), 'db': (np.nan_to_num(db), hdb_), 'con': (v, have)}
        featO = {'reb': (reb, np.ones(n, bool)), 'ob': (oa, hob_), 'db': (da, hdb_), 'con': (ca, have)}
        PIb, _, _ = M.shares_for(ids, hgt, c, M.SH)
        keep = M.REFC; M.REFC = d['P_ref']
        p1 = M.build(feat, np.ones(n, bool), PIb, PIb @ M.POSW)[0]
        pO = M.build(featO, np.ones(n, bool), PIb, PIb @ M.POSW)[0]
        M.REFC = keep
        Wm = W(mpg)
        PP[c] = {'W1': p1, 'M': p1 * Wm, 'O': pO, 'MO': pO * Wm}
    Y = {c: Q.target(D[c]['ids'], NEXT[c], 'epm') for c in FULL}; Y['2025-26'] = E.V.live_targets(D['2025-26']['ids'])['epm']
    n = {c: int(np.isfinite(Y[c]).sum()) for c in FOLDS}; w = {t: n[t] / sum(n.values()) for t in FOLDS}
    m = lambda t, o: float(Q.metrics(D[t], Y[t], o)['all'])
    base = {t: m(t, D[t]['ovr']) for t in FOLDS}
    ref = {t: m(t, E.adj(D[t], PP[t]['W1'], .5)) for t in FOLDS}
    out = {'n': n, 'fold_coef': finfo}
    for a in ('W1',) + CAND:
        v = {t: m(t, E.adj(D[t], PP[t][a], .5)) for t in FOLDS}
        out[a] = {'vs_base': float(sum(w[t] * (v[t] - base[t]) for t in FOLDS)), 'vs_W1': float(sum(w[t] * (v[t] - ref[t]) for t in FOLDS)),
                  'per_fold_vs_W1': {t: v[t] - ref[t] for t in FOLDS}, 'n_pos_vs_W1': int(sum(v[t] > ref[t] for t in FOLDS))}
        print(f"bench {a:3s} Δbase {out[a]['vs_base']:+.4f} ΔW1 {out[a]['vs_W1']:+.4f} ({out[a]['n_pos_vs_W1']}/4)")
    return out


def exposure_table():
    rows = {}
    C = np.array([r['pos'] for r in card])
    for nm in WATCH:
        if nm not in names: continue
        i = names.index(nm)
        rows[nm] = {'pos': C[i], 'mpg': float(MPG[i]), 'oppOVR': round(float(INF['oppOVR'][i]), 2),
                    'oppOB': round(float(INF['oppOB'][i]), 4), 'oppDB': round(float(INF['oppDB'][i]), 4),
                    'opp2PA36': round(float(INF['opp2PA36'][i]), 2),
                    'ob': [float(ob0[i]), round(float(obA[i]), 4)], 'db': [float(db0[i]), round(float(dbA[i]), 4)],
                    'con': [round(float(c0[i]), 3), round(float(cA[i]), 3)],
                    'bonus': {a: round(float(BON[a][i]), 2) for a in BON}}
    ep = M.EP & (INF['sec'] > 0)
    by_mpg = {}
    for lo, hi in ((0, 16), (16, 24), (24, 30), (30, 99)):
        k = ep & (MPG >= lo) & (MPG < hi)
        by_mpg[f'{lo}-{hi}'] = {'n': int(k.sum()), 'oppOVR': float(INF['oppOVR'][k].mean()), 'opp2PA36': float(INF['opp2PA36'][k].mean()),
                                'oppOB': float(INF['oppOB'][k].mean())}
    return rows, by_mpg


def main():
    rows, by_mpg = exposure_table()
    print('coef b_def_dreb %.4f b_opp_oreb %.4f Obar %.4f seg %d pool %d' % (INF['b_def_dreb'], INF['b_opp_oreb'], INF['Obar'], INF['n_seg'], INF['pool_n']))
    print('by mpg', json.dumps(by_mpg, ensure_ascii=False))
    for nm in ('Deni Avdija', 'Donovan Clingan', 'Robert Williams III', 'Rudy Gobert', 'Nikola Jokić'):
        print(' ', nm, {k: rows[nm][k] for k in ('mpg', 'oppOVR', 'oppOB', 'opp2PA36')})
    lw = live('W1')
    print('live W1', {k: lw[k] for k in ('Deni Avdija', 'Donovan Clingan', 'Robert Williams III')}, 'S1', lw['Deni Avdija'][0] < lw['Donovan Clingan'][0])
    if DRY:
        return
    rA = ranks(np.round(M.ovr0 + BON['A'], 1))
    W1o = np.round(M.ovr0 + BW1, 1)
    res = {'prereg_sha256': sha(HERE / 'preregistration.md'), 'coef': {k: INF[k] for k in ('b_def_dreb', 'b_opp_oreb', 'Obar', 'n_seg', 'pool_n', 'm2')},
           'exposure_by_mpg': by_mpg, 'exposure': rows, 'arms': {}}
    ia, ic, iw = names.index('Deni Avdija'), names.index('Donovan Clingan'), names.index('Robert Williams III')
    for a in ('W1',) + CAND:
        set_targets(WI, WY, SEED); ev, o = M.card_eval(BON[a], M.CAPB['W1'], W1o)
        r = ev.pop('_rank')
        set_targets(RAW_IDX, RAW_YV, SEED); evr, _ = M.card_eval(BON[a], M.CAPB['W1'], W1o); evr.pop('_rank')
        lv = live(a)
        S1 = bool(lv['Deni Avdija'][0] < lv['Donovan Clingan'][0])
        drops = [(names[i], int(rA[i]), int(r[i])) for i in range(N) if rA[i] <= 30 and r[i] - rA[i] > 10]
        big = [x for x in drops if CW1[names.index(x[0])] >= 0.5]
        S2 = len(drops) <= 2 and not big
        S3 = not any(v['mean'] < -0.005 and v['ci90'][1] < 0 for v in ev['drho_vs_A'].values())
        res['arms'][a] = {'S1': S1, 'S1b_avdija_over_rw3_live': bool(lv['Deni Avdija'][0] < lv['Robert Williams III'][0]), 'S2': S2, 'S3': S3,
                          'drops_vs_0214a': drops, 'rho_W': ev['rho'], 'drho_W_vs_W1': ev['drho_vs_A'],
                          'rho_raw': evr['rho'], 'drho_raw_vs_W1': evr['drho_vs_A'], 'live': lv,
                          'card_rank': {n: int(r[names.index(n)]) for n in WATCH if n in names},
                          'top20': [names[i] for i in np.argsort(r)[:20]],
                          'top_bonus': [(names[i], round(float(BON[a][i]), 2), float(MPG[i])) for i in np.argsort(-BON[a])[:12]]}
        x = res['arms'][a]
        print(f"{a:3s} S1 {S1} S2 {S2} S3 {S3} drops {drops}")
        print('    ρW', {k: round(v, 4) for k, v in ev['rho'].items()}, {k: (round(v['mean'], 4), [round(c, 4) for c in v['ci90']]) for k, v in ev['drho_vs_A'].items()})
        print('    ρraw', {k: round(v, 4) for k, v in evr['rho'].items()}, {k: round(v['mean'], 4) for k, v in evr['drho_vs_A'].items()})
        print('    live', {k: lv[k] for k in ('Deni Avdija', 'Donovan Clingan', 'Robert Williams III', 'Rudy Gobert')})
    res['bench'] = bench()
    for a in CAND:
        x = res['arms'][a]; x['S4'] = res['bench'][a]['vs_W1'] >= -0.002
        x['verdict'] = 'adopt_candidate' if all(x[g] for g in ('S1', 'S2', 'S3', 'S4')) else 'reject'
    ok = [a for a in CAND if res['arms'][a]['verdict'] == 'adopt_candidate']
    pick = None
    if ok:
        best = max(res['bench'][a]['vs_W1'] for a in ok)
        pick = next(a for a in CAND if a in ok and res['bench'][a]['vs_W1'] >= best - 0.001)
    res['pick'] = pick
    print('verdicts', {a: res['arms'][a]['verdict'] for a in CAND}, 'pick', pick)
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=lambda v: v.item() if hasattr(v, 'item') else (v.tolist() if hasattr(v, 'tolist') else str(v))), encoding='utf-8')


if __name__ == '__main__':
    main()
