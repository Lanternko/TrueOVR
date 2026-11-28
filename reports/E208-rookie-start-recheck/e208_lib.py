"""E-208 共用函式：用現行 0.2.12b 管線（run_c4_live_rookie 的 eval_rookie／chain_rookie）重算歷屆真新秀。
母體＝E-141 rookie-players.csv（真新秀定義、季別不變）。本檔不寫任何線上檔；不呼叫 build_2k_start.main()。
子程序：無。"""
import sys, json, math, csv, hashlib
from pathlib import Path
from functools import lru_cache

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(ROOT / 'reports/E121-rookie-scale'))
import numpy as np  # noqa: E402
import subprocess, types  # noqa: E402

LIVE_REL = 'reports/ovr-inseason-2026-27/live'


def _pin_head(modname):
    """共用工作樹裡別的 session 正在改 live/tov_live.py（E-207／0.2.12c，未 commit）。要量的是已 commit 的 0.2.12b，
    所以 tov_live 改從 git HEAD 取原始碼（__file__ 仍指 live/，凍結檔路徑照舊）。"""
    src = subprocess.run(['git', 'show', f'HEAD:{LIVE_REL}/{modname}.py'], cwd=ROOT, capture_output=True,
                         creationflags=subprocess.CREATE_NO_WINDOW, check=True).stdout.decode('utf-8')
    m = types.ModuleType(modname)
    m.__file__ = str(LIVE / f'{modname}.py')
    sys.modules[modname] = m
    exec(compile(src, m.__file__, 'exec'), m.__dict__)
    return m


HEAD_SHA = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True,
                          creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
_pin_head('tov_live')
_pin_head('window8')
_pin_head('run_c4_live_rookie')       # 共用工作樹裡別的 session 也在改它（0.2.12c WIP）
import run_c4_live_rookie as RW  # noqa: E402


class _HeadPath(type(Path())):
    """run_c4_live.py 在共用工作樹也有別的 session 的未 commit 改動（0.2.12c WIP）→ load_ns 讀 git HEAD 版。"""
    def read_text(self, *a, **k):
        return subprocess.run(['git', 'show', f'HEAD:{LIVE_REL}/{self.name}'], cwd=ROOT, capture_output=True,
                              creationflags=subprocess.CREATE_NO_WINDOW, check=True).stdout.decode('utf-8')


RW.ORIG = _HeadPath(str(RW.ORIG))

# 同一個 session 已 stage 把 0212tov 檔搬進 live/_retired/（HEAD 版程式仍讀 live/ 原路徑）→ 讀檔時照搬後位置轉向（唯讀）
import builtins, io, os  # noqa: E402
_MOVED = {n for n in os.listdir(LIVE / '_retired')} & {'prior-2025-26-card0212-tov.json', 'usage-2025-26-card0212-tov.json',
                                                     'tov-pool-card0212.json', 'build_prior_0212tov.py', 'build_usage_0212tov.py'}
_orig_open, _orig_exists = io.open, os.path.exists


def _redir(f):
    try:
        q = Path(os.fspath(f))
    except TypeError:
        return f
    if q.name in _MOVED and q.parent == LIVE and not q.exists():
        return LIVE / '_retired' / q.name
    return f


def _open(f, *a, **k):
    return _orig_open(_redir(f), *a, **k)


io.open = builtins.open = _open
import build_2k_start as B2  # noqa: E402
import build_rookie_prior as BR  # noqa: E402
import split_dc as SD  # noqa: E402

CUR = {'season': None}      # split_creation 覆寫要知道目前是哪一季

CURVE_A, CURVE_B = B2.CURVE_A, B2.CURVE_B
SEASONS = ['Y2', 'Y3', 'Y5', 'Y6', 'D1', 'D2', 'D3']
CRJ_SEASONS = ('2022-23', '2023-24', '2024-25', '2025-26')
GROUPS = [('1', 1, 1), ('2-3', 2, 3), ('4-10', 4, 10), ('11-30', 11, 30), ('31-60', 31, 60), ('落選', 61, 99)]


def curve(pick):
    return CURVE_A - CURVE_B * math.log(pick)


def group_of(pick, kind):
    if kind == 'undrafted':
        return '落選'
    for g, lo, hi in GROUPS[:-1]:
        if lo <= pick <= hi:
            return g
    return '落選'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


class Env:
    pass


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
    _u, en.coef, _ = ns['load_usage']()
    en.bio = {}
    for p in sorted((ROOT / 'data/defense-seventh').glob('*/bio.json')):
        rs = json.load(open(p, encoding='utf-8'))['data']['resultSets'][0]
        for row in rs['rowSet']:
            rec = dict(zip(rs['headers'], row))
            en.bio[int(rec['PLAYER_ID'])] = rec
    en._sd = {}
    en._crmap = None
    return en


def target_data(en, target):
    """(sd, rowsby, gmax)；rowsby[pid]＝[(tg, row, shot, flags)] 依球隊場次排序（同 e136_lib.target_data）。"""
    if target in en._sd:
        return en._sd[target]
    C, IC = en.C, en.IC
    sd = en.sd26 if target == '2026-27' else C.load_target_season(target)
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


def make_rk(en, pid, name, pick, pos, kind, season):
    """R-096 起點：形狀沿用 E-116，15 項一起平移 δ 使無數據 OVR＝73−5.9·ln 順位（build_2k_start.solve）。"""
    b = en.bio[pid]
    h = float(b['PLAYER_HEIGHT_INCHES'])
    x0, k = x0_shape(en, pick, pos)
    rk = {'playerId': pid, 'name': name, 'pick': pick, 'pos': pos, 'heightInches': h, 'mpg0': en.mpg0, 'x0': x0, 'k': k}
    T = curve(pick)
    d, ov = B2.solve(en.ns, en.pw, en.anc, en.r_repl, en.rel, rk, T)
    rk['x0'] = B2.shifted(x0, d)
    rk.update(T=T, delta=d, start=ov, season=season, kind=kind)
    return rk


# ---- creation（現行 creationJ）：歷史季只有 2022-23 起有逐場 J 計數
def creation_map(en):
    if en._crmap is None:
        W = en.ns['win8_load']()
        en._crmap = W['creationMap']
    return en._crmap


def install_split_creation(en):
    """覆寫 run_c4_live.split_creation：歷史季用 crJ-<季> 逐場計數＋同一個 creation_map（現行映射）。
    沒有該季計數（2022-23 以前）＝回傳 None，呼叫端把 creation 視為無資料。"""
    ns = en.ns
    cm = creation_map(en)
    cache = {}
    orig = ns['split_creation']

    def split_creation(pid, games, minutes):
        s = CUR['season']
        if s == '2026-27':
            return orig(pid, games, minutes)       # 本季＝線上原函式（win8_load 的 crJ）
        if s not in CRJ_SEASONS:
            return float('nan')
        if s not in cache:
            cache[s] = SD.crj_hist(s)[0]
        n = sum(cache[s].get((g, int(pid)), 0.0) for g in games)
        return float(cm(np.array([n / max(minutes, 1.0) * 36.0]))[0])
    ns['split_creation'] = split_creation


def chain_of(en, season):
    if season == 'C26':
        return '2025-26', '2026-27'
    return en.C.CHAIN[season]['prior'], en.C.CHAIN[season]['target']


def window_recs(en, season, rks, lo_hi):
    """{pid: 視窗卡 rec}；lo_hi＝{pid: (lo, hi)} 自己上場場次切片。"""
    C, IC = en.C, en.IC
    prior, target = chain_of(en, season)
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
    sdw['box'], shots_ = box, shots
    sdw['shots'] = shots_
    fake = RW.fake_cards(rks)
    CUR['season'] = target
    return IC.window_cards(sdw, 10 ** 4, C.mapping_for(prior), fake, IC.received_prior(prior))


class mask_creation:
    """該季沒有逐場 creationJ 計數（2022-23 以前）＝creation 視為無資料（維持起點 x0）：把樣本門檻拉到無限大。"""
    def __init__(self, en, season):
        self.en, self.on = en, en.C.CHAIN[season]['target'] not in CRJ_SEASONS

    def __enter__(self):
        if self.on:
            self.old = self.en.SA.SEASON_MIN_SAMPLE['creation']
            self.en.SA.SEASON_MIN_SAMPLE['creation'] = 1e12

    def __exit__(self, *a):
        if self.on:
            self.en.SA.SEASON_MIN_SAMPLE['creation'] = self.old


def read_pop(season=None):
    rows = list(csv.DictReader(open(ROOT / 'reports/E141-rookie-start-shift/rookie-players.csv', encoding='utf-8')))
    return [r for r in rows if season is None or r['season'] == season]


def window_ovr(en, rk, rec, arm='own'):
    """前 N 場視窗卡 → 現行 eval_rookie 的 OVR（arm=own：w=1，跟 E-141 的 ans 同概念＝自己的視窗 OVR；arm=e116：線上的收縮）。
    再補 usage 層（chain_rookie，防守加成 0＝歷史季沒有 def-L-live 的 poss）→ 'ovrC'（線上公布的算法）。"""
    e = RW.eval_rookie(en.ns, en.pw, en.anc, en.r_repl, rk, rec, arm, en.rel)
    cur = {'pid': rk['playerId'], 'pred0': e['pred0'], 'mpgHat': e['mpgHat']}
    n = rec['GP'] if rec else 0
    ch = RW.chain_rookie(en.ns, en.pw, en.anc, en.r_repl, cur, rk['pos'], n, {}, en.coef, 0.0)
    e['ovrC'] = ch['ovr']
    return e
