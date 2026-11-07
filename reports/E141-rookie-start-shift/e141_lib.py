"""E-141 共用函式：歷史季真新秀層（errata-1：照 E-139 預註冊 §0.5、c0b 的文字自己實作，不 import e139-prior-weight）。
線上規則一律 import（RW.eval_rookie／ovr_of、B2.solve／shifted／make_q、BR.design／height_pos／pick_of）。
本檔沒有子程序。"""
import sys, json, math, time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = ROOT / 'reports/ovr-inseason-2026-27'
sys.path.insert(0, str(R / 'e138-recent-form-display'))
import e138_lib as X  # noqa: E402
sys.path.insert(0, str(R / 'live'))
sys.path.insert(0, str(ROOT / 'reports/E121-rookie-scale'))
import run_c4_live_rookie as RW  # noqa: E402
import build_2k_start as B2  # noqa: E402
import build_rookie_prior as BR  # noqa: E402

C, F, IC, SA, E95, B = X.C, X.F, X.IC, X.SA, X.E95, X.B
CANDS = {'B0r': -5.0, 'S25': -2.5, 'S0': 0.0, 'S+25': 2.5}
BASE = 'B0r'
SEASONS = ['Y2', 'Y3', 'Y5', 'Y6', 'D1', 'D2', 'D3']
TRAIN = ['Y2', 'Y3', 'Y5', 'Y6']
TEST = ['D1', 'D2']
NCHK = [0, 5, 10]
AHEAD = 20
MIN_TOT, MIN_GAMES = 500.0, 30


class Ctx:
    pass


def init():
    ctx = Ctx()
    t0 = time.time()
    ctx.en = X.setup_env(t0, with_ctx=False)
    ctx.ns = RW.load_ns()                       # 不呼叫 ns['setup']()：不動 IC／C 的猴子補丁
    ctx.fit2k = json.load(open(ROOT / 'reports/rookie-growth/twok-by-pick.json', encoding='utf-8'))['fitRecent3']
    ctx.q, _ = B2.make_q()
    ctx.f116 = json.load(open(ROOT / 'reports/E116-rookie-prior/fit.json', encoding='utf-8'))
    ctx.mpg0 = ctx.f116['medians']['mpg0']
    ctx.bio_all = {}
    ctx.bio_by_season = {}
    for p in sorted((ROOT / 'data/defense-seventh').glob('*/bio.json')):
        rs = json.load(open(p, encoding='utf-8'))['data']['resultSets'][0]
        h = rs['headers']
        d = {}
        for row in rs['rowSet']:
            rec = dict(zip(h, row))
            d[int(rec['PLAYER_ID'])] = rec
            ctx.bio_all[int(rec['PLAYER_ID'])] = rec
        ctx.bio_by_season[p.parent.name] = d
    ctx.rel = ctx.en.rel_
    ctx.pw = {}
    ctx.cache = {}
    return ctx


def target_of(ctx, pick, s_shift):
    return ctx.q(ctx.fit2k['a'] + ctx.fit2k['b_lnPick'] * math.log(pick)) + s_shift


def x0_of(ctx, pick, pos):
    x = BR.design(pick, pos)
    out, k = {}, {}
    for a in BR.ABIL:
        f = ctx.f116['abilities'][a]
        v = f['b0'] + f['b1_lnPick'] * x[1] + f['gF'] * x[2] + f['gC'] * x[3]
        out[a] = min(max(v, BR.LO), BR.HI)
        if f['k'] is not None:
            k[a] = f['k']
    return out, k


def season_env(ctx, s):
    if s not in ctx.pw:
        ctx.pw[s] = X.T.PW.for_start(C, s)
    return ctx.pw[s]


def own_list(rowsby, gmax, pid):
    return [t for t in rowsby.get(pid, ()) if t[3]['min'] and t[0] <= gmax]


def population(ctx, s):
    """真新秀與其他沒有上季卡的人（E-139 §0.5 文字）。回傳 (rookies 全部, others, info)。"""
    prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
    y0 = int(target[:4])
    sd, idx, rowsby, gmax = X.target_data(target)
    cards_prior, _ = C.load_card(prior)
    sdp = C.load_target_season(prior)
    prior_games = {pid for pid, b in sdp['box'].items() if any(r['MIN'] > 0 for r in b['rows'])}
    bio_t = ctx.bio_by_season.get(target, {})
    rook, others = [], []
    for pid in sd['box']:
        if pid in cards_prior:
            continue
        lst = own_list(rowsby, gmax, pid)
        if not lst:
            continue
        b = bio_t.get(pid) or ctx.bio_all.get(pid)
        tot = sum(float(t[1]['MIN']) for t in lst)
        dy = None
        if b is not None:
            try:
                dy = int(b.get('DRAFT_YEAR'))
            except (TypeError, ValueError):
                dy = None
        teams = {int(t[1]['TEAM_ID']) for t in lst}
        rec = {'playerId': pid, 'name': (b or {}).get('PLAYER_NAME', str(pid)), 'ownGames': len(lst), 'minTot': tot,
               'draftYear': dy, 'nTeams': len(teams), 'firstTeamGame': int(lst[0][0]),
               'hasPriorGames': pid in prior_games, 'hasBio': b is not None}
        if b is None:
            rec['why'] = 'noBio'
            others.append(rec)
        elif dy == y0:
            rec['kind'] = 'drafted'
            rook.append(rec)
        elif dy is None and pid not in prior_games:
            rec['kind'] = 'undrafted'
            rook.append(rec)
        else:
            rec['why'] = 'draftedEarlier' if dy is not None else 'undraftedWithPriorGames'
            others.append(rec)
        if b is not None and rec.get('kind'):
            rec['pick'] = BR.pick_of(b)
            rec['heightInches'] = float(b['PLAYER_HEIGHT_INCHES'])
    return rook, others, {'y0': y0, 'cardsPrior': len(cards_prior)}


def build_rookies(ctx, s):
    """合格真新秀（MIN>=500、自己>=30 場）＋ x0、各候選 δ 與開季 OVR。"""
    if ('rk', s) in ctx.cache:
        return ctx.cache[('rk', s)]
    rook, others, info = population(ctx, s)
    pw = season_env(ctx, s)
    en, ns = ctx.en, ctx.ns
    anc, rr = en.AR, en.RREPL
    qual = []
    for r in rook:
        if r['minTot'] < MIN_TOT or r['ownGames'] < MIN_GAMES:
            continue
        pos = BR.height_pos(r['heightInches'])
        x0, k = x0_of(ctx, r['pick'], pos)
        rk = {'playerId': r['playerId'], 'name': r['name'], 'pick': r['pick'], 'pos': pos,
              'heightInches': r['heightInches'], 'mpg0': ctx.mpg0, 'x0': x0, 'k': k}
        rk['cand'] = {}
        for c, sh in CANDS.items():
            T = target_of(ctx, r['pick'], sh)
            d, ov = B2.solve(ns, pw, anc, rr, ctx.rel, rk, T)
            rk['cand'][c] = {'T': T, 'delta': d, 'open': ov, 'x0': B2.shifted(x0, d)}
        rk['meta'] = r
        qual.append(rk)
    ctx.cache[('rk', s)] = (qual, rook, others, info)
    return ctx.cache[('rk', s)]


def _window_cards(ctx, s, rks, lo, hi, fake):
    prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
    sd, idx, rowsby, gmax = X.target_data(target)
    box, shots, mm = {}, {}, {}
    for rk in rks:
        pid = rk['playerId']
        lst = own_list(rowsby, gmax, pid)
        seg = lst[lo:hi]
        if len(seg) < (hi - lo):
            continue
        box[pid] = {**sd['box'][pid], 'rows': [dict(t[1]) for t in seg]}
        for (tg, r, sh, fl) in seg:
            if sh:
                shots[(pid, r['GAME_ID'])] = sh
        mm[pid] = sum(float(t[1]['MIN']) for t in seg) / len(seg)
    sdw = dict(sd)
    sdw['box'], sdw['shots'] = box, shots
    cards = IC.window_cards(sdw, 10 ** 4, C.mapping_for(prior), fake, IC.received_prior(prior))
    return cards, mm


def _mask_undefined(rec, undefined):
    """prediction 側：該季沒有資料的屬性（fit[s]['undefined']）讓樣本歸零，eval_rookie 就會跳過（x0 不動）。"""
    if rec is None:
        return None
    rec = dict(rec)
    rec['sample'] = dict(rec['sample'])
    key = {'long': 'fg3a', 'mid': 'midA', 'short': 'shortA', 'ft': 'fta', 'drive': 'fga', 'tovSkill': 'possDen',
           'pass': 'min', 'rebound': 'min', 'stamina': 'gp', 'creation': 'min', 'pressure': 'defensePossessions'}
    for a in undefined:
        if a in key:
            rec['sample'][key[a]] = 0.0
    return rec


def predictions(ctx, s, qual):
    """{cand: {pid: {N: ovr}}}（N=0 即開季 OVR）。"""
    pw = season_env(ctx, s)
    en, ns = ctx.en, ctx.ns
    undefined = ctx.en.fit[s]['undefined']
    fake = RW.fake_cards([dict(rk, x0=rk['cand'][BASE]['x0']) for rk in qual])
    out = {c: {rk['playerId']: {} for rk in qual} for c in CANDS}
    recs = {0: {rk['playerId']: None for rk in qual}}
    for N in NCHK:
        if N == 0:
            continue
        cards, _ = _window_cards(ctx, s, qual, 0, N, fake)
        recs[N] = {rk['playerId']: _mask_undefined(cards.get(rk['playerId']), undefined) for rk in qual}
    for c in CANDS:
        for rk in qual:
            rkc = dict(rk, x0=rk['cand'][c]['x0'])
            for N in NCHK:
                out[c][rk['playerId']][N] = RW.eval_rookie(ns, pw, en.AR, en.RREPL, rkc, recs[N][rk['playerId']], 'e116', ctx.rel)['ovr']
    return out


def answers(ctx, s, qual, cand=BASE):
    """答案：自己第 N+1..N+20 場視窗卡，上季卡位置＝B0r 的 x0 假卡（與 cand 無關；cand 參數只為 c0a 重算）。
    回傳 {pid: {N: (ovr, attrs, mm)}}。"""
    pw = season_env(ctx, s)
    en, ns = ctx.en, ctx.ns
    undefined = en.fit[s]['undefined']
    frozen = [] if en.fit[s]['pressureOpen'] else ['pressure']
    base = {rk['playerId']: rk['cand'][BASE]['x0'] for rk in qual}
    fake = RW.fake_cards([dict(rk, x0=base[rk['playerId']]) for rk in qual])
    pcs = {pid: {**base[pid], **fake[pid]} for pid in base}       # 屬性值＋fake 的 creation／e2
    res = {rk['playerId']: {} for rk in qual}
    old = SA.SEASON_MIN_SAMPLE['stamina']
    SA.SEASON_MIN_SAMPLE['stamina'] = 1
    try:
        for N in NCHK:
            cards, mm = _window_cards(ctx, s, qual, N, N + AHEAD, fake)
            for rk in qual:
                pid = rk['playerId']
                if pid not in mm:
                    continue
                rec = cards.get(pid)
                vals = {}
                if rec is not None:
                    for a in C.UPD:
                        if a in undefined or a in frozen:
                            continue
                        if IC.sample_of(rec, a) < SA.SEASON_MIN_SAMPLE[a]:
                            continue
                        vals[a] = C.clip(F.y_adj_of(pcs[pid], rec, a, 0.0))
                x = {**base[pid], **vals}
                pred0, g, ovr = RW.ovr_of(ns, pw, en.AR, en.RREPL, x, rk['pos'], mm[pid], rk['heightInches'])
                res[pid][N] = (ovr, vals, mm[pid])
    finally:
        SA.SEASON_MIN_SAMPLE['stamina'] = old
    return res
