"""E-211 量測線 H：在「某個版本的 worktree」裡用該版本自己的 live/ 程式算歷屆真新秀前 20 場視窗 OVR（只資料，不含 usage 層）。
＝E-208 的 e208_lib／run_A 做法（eval_rookie arm=own，w=1），但不釘 git HEAD，改成 E211_ROOT 指向的 worktree。
起點曲線 START=R096（73−5.9·ln 順位，build_2k_start.solve 重解 δ）或 R073（E-141 的 2K 曲線 −5，用 E-141 的 fit2k）。
子程序：無。"""
import sys, os, json, math, csv
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(os.environ['E211_ROOT'])
HERE = Path(__file__).resolve().parent
sys.path.insert(0, 'D:/Projects/CODING/_wt')
import fallback  # noqa: E402,F401
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(ROOT / 'reports/E121-rookie-scale'))
import numpy as np  # noqa: E402
import run_c4_live_rookie as RW  # noqa: E402
import build_2k_start as B2  # noqa: E402
import build_rookie_prior as BR  # noqa: E402
try:
    import split_dc as SD  # noqa: E402
except Exception:
    SD = None

START = os.environ.get('E211_START', 'R096')
SEASONS = ['Y2', 'Y3', 'Y5', 'Y6', 'D1', 'D2', 'D3']
CRJ_SEASONS = ('2022-23', '2023-24', '2024-25', '2025-26')
CUR = {'season': None}


class Env:
    pass


def curve(pick):
    return 73.0 - 5.9 * math.log(pick)       # R-096（HEAD 的 B2.CURVE_A／B 同值）


def init():
    en = Env()
    en.ns = ns = RW.load_ns()
    en.sd26, en.mp = ns['setup']()
    en.C, en.F, en.IC, en.SA, en.V2 = (ns[k] for k in ('C', 'F', 'IC', 'SA', 'V2'))
    en.rel = en.V2.load_reliability()
    en.pw = ns['PW'].for_start(en.C, 'S*')
    en.anc, en.r_repl = ns['e064_anchors']()
    en.fit116 = json.load(open(ROOT / 'reports/E116-rookie-prior/fit.json', encoding='utf-8'))
    en.mpg0 = en.fit116['medians']['mpg0']
    en.bio = {}
    for p in sorted((ROOT / 'data/defense-seventh').glob('*/bio.json')):
        rs = json.load(open(p, encoding='utf-8'))['data']['resultSets'][0]
        for row in rs['rowSet']:
            rec = dict(zip(rs['headers'], row))
            en.bio[int(rec['PLAYER_ID'])] = rec
    en._sd = {}
    en._crmap = None
    if START == 'R073':
        en.fit2k = json.load(open(ROOT / 'reports/rookie-growth/twok-by-pick.json', encoding='utf-8'))['fitRecent3']
        en.q, _ = B2.make_q()
    return en


def target_data(en, target):
    if target in en._sd:
        return en._sd[target]
    C, IC = en.C, en.IC
    sd = C.load_target_season(target)
    idx = IC.team_game_index(sd)
    rowsby = {}
    for pid, b in sd['box'].items():
        lst = []
        for r in b['rows']:
            tg = idx.get((r['TEAM_ID'], r['GAME_ID']))
            if tg is None:
                continue
            lst.append((tg, r, sd['shots'].get((pid, r['GAME_ID'])), {'min': r['MIN'] > 0}))
        lst.sort(key=lambda t: (t[0], str(t[1]['GAME_ID'])))
        rowsby[pid] = lst
    en._sd[target] = (sd, rowsby, max(idx.values()))
    return en._sd[target]


def own_list(rowsby, pid):
    return [t for t in rowsby.get(pid, ()) if t[3]['min']]


def x0_shape(en, pick, pos):
    x = BR.design(pick, pos)
    out, k = {}, {}
    for a in BR.ABIL:
        f = en.fit116['abilities'][a]
        v = f['b0'] + f['b1_lnPick'] * x[1] + f['gF'] * x[2] + f['gC'] * x[3]
        out[a] = min(max(v, BR.LO), BR.HI)
        if f['k'] is not None:
            k[a] = f['k']
    return out, k


def make_rk(en, pid, name, pick, pos, season):
    h = float(en.bio[pid]['PLAYER_HEIGHT_INCHES'])
    x0, k = x0_shape(en, pick, pos)
    rk = {'playerId': pid, 'name': name, 'pick': pick, 'pos': pos, 'heightInches': h, 'mpg0': en.mpg0, 'x0': x0, 'k': k}
    if START == 'R073':
        T = en.q(en.fit2k['a'] + en.fit2k['b_lnPick'] * math.log(pick)) - 5.0
    else:
        T = curve(pick)
    d, ov = B2.solve(en.ns, en.pw, en.anc, en.r_repl, en.rel, rk, T)
    rk['x0'] = B2.shifted(x0, d)
    rk.update(T=T, delta=d, start=ov)
    return rk


def install_split_creation(en):
    """歷史季 creation：有 split_dc 的版本用 crJ 逐場計數＋creation_map（同 E-208）；沒有就不動。"""
    ns = en.ns
    if SD is None or 'split_creation' not in ns or 'win8_load' not in ns:
        return False
    cm = ns['win8_load']()['creationMap']
    cache = {}
    orig = ns['split_creation']

    def split_creation(pid, games, minutes):
        s = CUR['season']
        if s == '2026-27':
            return orig(pid, games, minutes)
        if s not in CRJ_SEASONS:
            return float('nan')
        if s not in cache:
            cache[s] = SD.crj_hist(s)[0]
        n = sum(cache[s].get((g, int(pid)), 0.0) for g in games)
        return float(cm(np.array([n / max(minutes, 1.0) * 36.0]))[0])
    ns['split_creation'] = split_creation
    return True


def window_recs(en, season, rks, lo_hi):
    C, IC = en.C, en.IC
    prior, target = C.CHAIN[season]['prior'], C.CHAIN[season]['target']
    sd, rowsby, gmax = target_data(en, target)
    box, shots = {}, {}
    for rk in rks:
        pid = rk['playerId']
        lo, hi = lo_hi[pid]
        seg = own_list(rowsby, pid)[lo:hi]
        if not seg:
            continue
        box[pid] = {**sd['box'][pid], 'rows': [dict(t[1]) for t in seg]}
        for (tg, r, sh, fl) in seg:
            if sh:
                shots[(pid, r['GAME_ID'])] = sh
    sdw = dict(sd)
    sdw['box'], sdw['shots'] = box, shots
    fake = RW.fake_cards(rks)
    CUR['season'] = target
    return IC.window_cards(sdw, 10 ** 4, C.mapping_for(prior), fake, IC.received_prior(prior))


class mask_creation:
    def __init__(self, en, season, active):
        self.en, self.on = en, active and en.C.CHAIN[season]['target'] not in CRJ_SEASONS

    def __enter__(self):
        if self.on:
            self.old = self.en.SA.SEASON_MIN_SAMPLE['creation']
            self.en.SA.SEASON_MIN_SAMPLE['creation'] = 1e12

    def __exit__(self, *a):
        if self.on:
            self.en.SA.SEASON_MIN_SAMPLE['creation'] = self.old


def read_pop():
    return list(csv.DictReader(open('D:/Projects/CODING/basketball-autochess/reports/E141-rookie-start-shift/rookie-players.csv', encoding='utf-8')))
