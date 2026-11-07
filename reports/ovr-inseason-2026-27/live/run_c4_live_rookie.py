"""E-116 §4：run_c4_live.py 的新秀版包裝（D1：不改共用檔，讀它的原始碼、在記憶體做一處替換後執行）。

唯一替換：main() 寫 ranking.csv 那一行 → 先把「沒有先驗卡、但 bio 是 2026 新秀」的人算成一列併進去；
並把這些人從 nopr（no-prior.csv）拿掉。老將的列、統計、檢查完全沿用原程式（rank 會因新秀插入而位移，相對順序不變）。
用法同原程式：python -I -X utf8 run_c4_live_rookie.py <輸出資料夾>
也供 backtest.py 匯入：load_ns() 回傳已 exec 的命名空間（不執行 main）。
"""
import copy
import os
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rookie_defense as RD  # noqa: E402
import defense_bonus as DB  # noqa: E402
import pres_drive as PD  # noqa: E402（2026-11-01 壓迫／切入賽中解凍；UNFREEZE_PD=0 時完全不呼叫）
import win_len  # noqa: E402（E-204／R-140：四季窗口長度開關，WIN_LEN 預設 246；WIN_LEN=328 重現 0.2.12a 以前）
win_len.install()
import recent_boost  # noqa: E402（E-221／R-147：本季近期加成開關，預設開 b=3、h=20，R-150）
recent_boost.install()

HERE = Path(__file__).resolve().parent
ORIG = HERE / 'run_c4_live.py'
GRAVITY = os.environ.get('GRAVITY', '1') != '0'   # 0.2.10j（R-134）：GRAVITY=0 重現 0.2.10i（不 import gravity_live、新秀起點讀 _retired/）
TOV_POSS = os.environ.get('TOV_POSS', '1') != '0'   # 0.2.12（R-139）：TOV_POSS=0 重現 0.2.11（不 import tov_live、新秀 tovSkill 仍走 C4 的 y 更新；新秀起點讀 _retired/）
TOV_TOUCH = os.environ.get('TOV_TOUCH', '1') != '0'   # 0.2.12c（R-144，E-207）：TOV_TOUCH=0 重現 0.2.12b（新秀起點讀 _retired/rookie-prior-2026-0212b.json）
ROOKIE_JSON = HERE / ('_retired/rookie-prior-2026-0210h.json' if os.environ.get('SPLIT_DC', '1') == '0' else
                      ('rookie-prior-2026.json' if TOV_TOUCH else '_retired/rookie-prior-2026-0212b.json') if GRAVITY and TOV_POSS else '_retired/rookie-prior-2026-0211.json' if GRAVITY else '_retired/rookie-prior-2026-0210i.json')  # 換版後重解 δ（L-109）；GRAVITY=0／SPLIT_DC=0 重現舊版用當時的 δ
PS_START = os.environ.get('PS_START', '1') != '0'   # 0.2.12e（R-162，E-230）：新秀起點加季前賽位移；PS_START=0 讀 _retired/rookie-prior-2026-pre-ps.json（0.2.12d 的起點）
if not PS_START and ROOKIE_JSON == HERE / 'rookie-prior-2026.json':
    ROOKIE_JSON = HERE / '_retired/rookie-prior-2026-pre-ps.json'
if GRAVITY:
    import gravity_live as GV  # noqa: E402
if TOV_POSS:
    import tov_live as TL  # noqa: E402
G_GAMES = 82
DPOS = {'G': 'SG', 'F': 'SF', 'C': 'C'}          # D5：G／F／C → 設計矩陣用的 SG／SF／C（回測與上線同一張表）
SKIP = ('pressure', 'drive') + (('tovSkill',) if TOV_POSS else ())                     # live 凍結的兩項（同老將）
DEF_ATTRS = ('onBall', 'help')                   # 2026-10-30 使用者：新秀防守一有數據就換成當季值（w=1，rookie_defense.py）

OLD_LINE = "    C.write_csv(out_dir / 'ranking.csv', [{k: r[k] for k in head} for r in rows], head)\n"
NEW_LINE = "    _E116.write_outputs(globals(), locals(), out_dir, rows, head, nopr)\n"
# 2026-10-30 使用者：老將防守解凍，「用 TUL 類似的做法」→ onBall／help 改四季窗口逐場線性遞減（rookie_defense.veteran）
OLD_DEF = "    attrs = live_predict(delta2, rel_, undefined, frozen, diag=diag)\n"
NEW_DEF = OLD_DEF + "    _E116.vet_defense(sd26, attrs, prior_cards, pw, attrs0)\n"
# 2026-11-01 lastOVR／dOVR 基準改 window_ref（REF_W）；檢查 (a) 與 _lastCmp（對正式卡）仍用 ref。E-185：refw 的 MPG 用 mpg_ref（本季 0 場的窗口 MPG；WIN10=0 時＝mpg0）
OLD_REF = "    ref = e064_convert(ref, mpg0, anc064, r_repl064)\n"
NEW_REF = OLD_REF + "    refw = e064_convert(apply_usage(dict(_E116.REF_W), usage_d0, ucoef), mpg_ref, anc064, r_repl064)\n"   # 0.2.10g：usage_d0＝本季 0 場的窗口用人特徵（USAGE_WIN=0 時＝凍結 usage）
OLD_LAST = "                    'lastOVR': r1(ref[pid]['ovr']), 'dOVR': round(p['ovr'] - ref[pid]['ovr'], 2),\n"
NEW_LAST = "                    'lastOVR': r1(refw[pid]['ovr']), 'dOVR': round(p['ovr'] - refw[pid]['ovr'], 2),\n"
OLD_D = "                    '_ovr': p['ovr'], '_d': p['ovr'] - ref[pid]['ovr'],\n"
NEW_D = "                    '_ovr': p['ovr'], '_d': p['ovr'] - refw[pid]['ovr'],\n"
# 檢查 (a)（f=0 → 先驗卡 OVR）比的是屬性更新機制，用凍結的防守加成；live 加成只進正式輸出
OLD_A = "    o1 = pw.predict(a1)\n"
NEW_A = "    _E116.swap_bonus(pw, 'frozen')\n" + OLD_A + "    _E116.swap_bonus(pw, 'live')\n"
# 2026-11-01 壓迫、切入解凍（只在 UNFREEZE_PD=1 時替換）：presDisplay 欄改讀窗口值、meta 的 frozenAttrs 拿掉這兩項
OLD_PRES = "            row.update({'presDisplay': pc.get('presDisplay', ''), 'foulDisc': pc.get('foulDisc', '')})\n"
NEW_PRES = "            row.update({'presDisplay': _E116.pres_display(pid, pc), 'foulDisc': pc.get('foulDisc', '')})\n"
OLD_META = "        'frozenAttrs': frozen + list(IC.FROZEN_ATTRS), "
NEW_META = ("        'frozenAttrs': [a for a in frozen if a not in _E116.PD_ATTRS] + list(IC.FROZEN_ATTRS), "
            "'presDriveUnfreeze': _E116.PD_INFO, ")
OLD_NOTE = "help 照 E-123 D1 尾巴（不夾 99）；drive、onBall、pressure、presDisplay、physique、heightInches 凍結；"
NEW_NOTE = ("help 照 E-123 D1 尾巴（不夾 99）；pressure、presDisplay、drive 改四季窗口（老將，live/pres_drive.py）／本季值（新秀）；"
            "physique、heightInches 凍結；")
PD_ATTRS = ('pressure', 'drive')
GAMES_PER_SEASON = 1230
# v2（formula-gap，2026-10-31 使用者「先上線」）：新秀補卡鏈，三段都漸進放入，避免門檻一過就跳
BONUS_POSS = 2500      # 防守加成 × min(1, possW/2500)
USAGE_N = 10           # usage 層 × min(N/10, 1)


def load_ns():
    src = ORIG.read_text(encoding='utf-8')
    assert src.count(OLD_LINE) == 1, 'run_c4_live.py 的 ranking.csv 寫入行對不上'
    assert src.count(OLD_DEF) == 1, 'run_c4_live.py 的 live_predict 呼叫行對不上'
    assert src.count(OLD_A) == 1, 'run_c4_live.py 的檢查 (a) 預測行對不上'
    assert all(src.count(o) == 1 for o in (OLD_REF, OLD_LAST, OLD_D)), 'run_c4_live.py 的 ref／lastOVR 行對不上'
    src = src.replace(OLD_LINE, NEW_LINE).replace(OLD_DEF, NEW_DEF).replace(OLD_A, NEW_A)
    src = src.replace(OLD_REF, NEW_REF).replace(OLD_LAST, NEW_LAST).replace(OLD_D, NEW_D)
    if PD.ON:
        assert src.count(OLD_PRES) == 1 and src.count(OLD_META) == 1, 'run_c4_live.py 的 presDisplay／frozenAttrs 行對不上'
        src = src.replace(OLD_PRES, NEW_PRES).replace(OLD_META, NEW_META)
        if src.count(OLD_NOTE) == 1:      # README 說明文字（對不上只是說明舊，不擋）
            src = src.replace(OLD_NOTE, NEW_NOTE)
    ns = {'__name__': 'run_c4_live_exec', '__file__': str(ORIG), '_E116': sys.modules[__name__]}
    exec(compile(src, str(ORIG), 'exec'), ns)
    NS.update(ns=ns)
    return ns


# ------------------------------------------------------------------ 新秀計算
def xhat_of(ns, x0, k, rec, arm, rel, dfn=None):
    """回傳 (xhat {15 項}, w {項: w}, 取樣 n {項: n})。arm：e116（k=σ²/τ²）、frozen（k=50·nRef）、own（w=1）。
    dfn：rookie_defense.inseason() 的這個人（{'onBall','help','n3','nRim'}）；有值就直接取代 onBall／help（w=1）。"""
    C, F, IC, SA = ns['C'], ns['F'], ns['IC'], ns['SA']
    out, ws, ns_ = dict(x0), {}, {}
    if GRAVITY:                                         # 0.2.10j：x0 不含 gravity（δ 平移不動它）；本季 0 場＝ROOKIE_G0，有上場＝本季值（w=1，同防守 R-075）
        out['gravity'] = GV.rookie_g0()
        if dfn and dfn.get('gravity') is not None:
            out['gravity'] = dfn['gravity']
            ws['gravity'], ns_['gravity'] = 1.0, dfn.get('frames26')
    if TOV_POSS and dfn and dfn.get('tovRows') is not None:   # 0.2.12：新秀 tovSkill＝持球時間定義（本季整季）與起點 x0 依分鐘漸進混合（tov_live.rookie_tov）；沒有持球資料＝維持起點
        tv, tw, tm = TL.rookie_tov(dfn['tovRows'], dfn['tovPid'], dfn['tovPos'], x0['tovSkill'])
        if tv is not None:
            out['tovSkill'] = C.clip(tv)
            ws['tovSkill'], ns_['tovSkill'] = tw, tm
    for a in DEF_ATTRS:
        if dfn and dfn.get(a) is not None:
            out[a] = C.clip(dfn[a])
            ws[a], ns_[a] = 1.0, dfn.get('n3' if a == 'onBall' else 'nRim')
    for a in PD_ATTRS:                                  # UNFREEZE_PD=1：dfn 帶 pres_drive.inseason() 的本季值（w=1）
        if dfn and dfn.get(a) is not None:
            out[a] = C.clip(dfn[a])
            ws[a], ns_[a] = 1.0, dfn.get('minW')
    if rec is None:
        return out, ws, ns_
    f = min(rec['GP'] / G_GAMES, 1.0)
    card = {a: float(v) for a, v in x0.items()}

    def wt(a, n, kk, src):
        if arm == 'own':
            return 1.0
        kv = 50.0 * rel[src]['nRef'] if arm == 'frozen' else kk
        return f + (1.0 - f) * n / (n + kv)

    for a in C.UPD:
        if a in SKIP:
            continue
        n = IC.sample_of(rec, a)
        if n < SA.SEASON_MIN_SAMPLE[a]:
            continue
        y = F.y_adj_of(card, rec, a, 0.0)               # usg0＝0 → 不做用球率調整（D2）
        w = wt(a, n, k.get(a), a)
        out[a] = C.clip(x0[a] + w * (y - x0[a]))
        ws[a], ns_[a] = w, n
    a = 'foulDraw'
    if rec.get(a) is not None and IC.sample_of(rec, 'drive') >= SA.SEASON_MIN_SAMPLE['drive']:
        n = IC.sample_of(rec, 'drive')
        w = wt(a, n, k.get(a), 'drive')
        out[a] = C.clip(x0[a] + w * (float(rec[a]) - x0[a]))
        ws[a], ns_[a] = w, n
    return out, ws, ns_


def ovr_of(ns, pw, anc, r_repl, x, pos, mpg_hat, height):
    P = copy.copy(pw.pipe)
    P.pos = [DPOS[pos]]
    xx = dict(x, heightInches=float(height))      # 身高凍結（bio）
    raw = np.array([[xx[a] for a in getattr(P, 'attrs', ns['ATTRS'])]], float)
    pred0 = float(P.design(raw)[0])
    g = (pred0 - r_repl) * ns['sat_w'](mpg_hat)
    return pred0, g, ns['e064_map'](g, anc)


def team_badness(sd26):
    """爛隊程度 d（2026-10-31 使用者：用當下球隊的 +/- 混一點勝負，不看上季）。{TEAM_ID: {...}}。
    nr＝累計得失分差／(GP+10)、wp＝(W+5)／(GP+10)、s＝0.7·(0.5+0.033·nr)+0.3·wp、d＝clip((0.40−s)/0.10, 0, 1)。"""
    acc = {}
    for r in sd26['teamRows']:
        a = acc.setdefault(r['TEAM_ID'], [0, 0, 0.0])
        a[0] += 1
        a[1] += r['WL'] == 'W'
        a[2] += float(r['PLUS_MINUS'])
    out = {}
    for t, (gp, w, pm) in acc.items():
        nr, wp = pm / (gp + 10), (w + 5) / (gp + 10)
        s = 0.7 * (0.5 + 0.033 * nr) + 0.3 * wp
        out[t] = {'d': min(1.0, max(0.0, (0.40 - s) / 0.10)), 'teamGP': gp, 'nr': nr, 'wp': wp, 's': s}
    return out


def chain_rookie(ns, pw, anc, r_repl, cur, pos, n_games, dl, coef, d):
    """新秀走卡鏈（formula-gap v2）：pred0 → 防守加成（× min(1, possW/2500)）→ usage 層（× min(N/10, 1)）→ g → 錨點。
    D、possW 讀當天 def-L-live.csv，posMeanD 與老將 live 加成同一份。align／H1 上限：池化 RAPM 開季凍結（老將同），
    新秀不在池內 → poss=0 → 漸進係數 0。usage 特徵 L=log1p(MPGhat)、a=1、y=1、v=0、d＝team_badness。"""
    pred0, mh = cur['pred0'], cur['mpgHat']
    row = dl.get(cur['pid'])
    possW = float(row['poss']) if row else 0.0
    bonus = 0.0
    if possW > 0:
        mean = pw.pipe._m27_posMeanD[DPOS[pos]]
        bonus = max(0.0, 0.75 * float(row['D']) - mean) * min(1.0, possW / BONUS_POSS)
    p = pred0 + bonus
    L = float(np.log1p(mh))
    full = (coef['b0'] + coef['b1_p'] * p + coef['b2_L'] * L + coef['b3_a'] + coef['b4_y']
            + coef['b6_yL'] * L + coef['b8_ydL'] * d * L)
    pn = p + min(n_games / USAGE_N, 1.0) * (full - p)
    g = (pn - r_repl) * ns['sat_w'](mh)
    return {'bonus': bonus, 'possW': possW, 'pred': p, 'predNew': pn, 'g': g, 'ovr': ns['e064_map'](g, anc)}


def eval_rookie(ns, pw, anc, r_repl, rk, rec, arm, rel, dfn=None):
    """rk：x0、k、pos、mpg0。回傳 dict（xhat、w、pred0、mpgHat、ovr）。"""
    x, ws, _ = xhat_of(ns, rk['x0'], rk['k'], rec, arm, rel, dfn)
    m0 = rk['mpg0']
    if 'stamina' in ws and rec is not None and rec['GP'] > 0:
        mh = m0 + ws['stamina'] * (rec['MIN'] / rec['GP'] - m0)
    else:
        mh = m0
    pred0, g, ovr = ovr_of(ns, pw, anc, r_repl, x, rk['pos'], mh, rk['heightInches'])
    return {'x': x, 'w': ws, 'pred0': pred0, 'g': g, 'mpgHat': mh, 'ovr': ovr}


def fake_cards(rookies):
    return {r['playerId']: {'playerId': r['playerId'], 'name': r['name'], 'pos': DPOS[r['pos']],
                            'creation': r['x0']['creation'], 'e2': None} for r in rookies}


def rookie_windows(ns, sd, mapping, rookies, n):
    IC = ns['IC']
    received = IC.received_prior(ns['PRIOR'])
    return ns['m26_window_cards'](sd, n, mapping, fake_cards(rookies), received)


# ------------------------------------------------------------------ main() 內呼叫
VET_DEF_INFO = {}
PD_INFO = None          # UNFREEZE_PD=1 時：{'c', 'weights', 'updated'}
PD_VET = {}             # 老將窗口值 {pid: {...}}
PD_ROOK = {}            # 新秀本季值
NS = {}
BONUS = {}
REF_W = {}              # 2026-11-01 使用者「Fix ΔOVR baseline」→「也併進基準」：老將 lastOVR 基準＝今天的模型、但本季 0 場（R-112）
DEF_L_LIVE = DB.ROOT / 'data/_inseason_build/def-L-live.csv'
DEF_L_BASE = DB.ROOT / 'data/_inseason_build/def-L-base.csv'   # 同一個 c、每人拿掉自己本季 stints（基準用）


def window_ref(attrs0, posmap, pw, c):
    """lastOVR 基準＝「今天的模型、但本季 0 場」：先驗卡的 onBall／help（＋UNFREEZE_PD 時 pressure／drive）換成
    同一個 c 的四季窗口值但不讀本季資料（窗口權重隨聯盟進度移動的部分算進基準），防守加成用同一個 c、每人只拿掉自己本季 stints 的重擬合（defense_bonus.fit_loo）。
    這樣 dOVR 只剩本季比賽造成的變化：不含「單季卡 → 四季窗口」的換算差，也不含 0 場的人被窗口滑動帶動的漂移。
    要在 live_bonus 之後呼叫（BONUS['base'] 由它算）。"""
    base = copy.deepcopy(attrs0)
    vd, _ = RD.veteran(c, '2026-27', posmap, cur=False)
    pv = PD.veteran(c, cur=False)[0] if PD.ON else {}
    d0 = NS['ns']['win8_load']()['day0']       # 0.2.10：8 項屬性的基準＝窗口 day0（本季 0 場）
    for pid, x in base.items():
        for src, ks in ((vd, DEF_ATTRS), (pv, PD_ATTRS)):
            v = src.get(pid) or {}
            for a in ks:
                if v.get(a) is not None:
                    x[a] = v[a]
        if int(pid) in d0:
            x.update(d0[int(pid)])
    swap_bonus(pw, 'base')
    REF_W.clear()
    REF_W.update(pw.predict(base))
    swap_bonus(pw, 'live')


def vet_defense(sd26, attrs, prior_cards, pw, attrs0):
    """老將 onBall／help：四季窗口逐場線性遞減（rookie_defense.veteran）。c＝聯盟已賽場數／1230·82 格；算不出的人維持先驗卡。
    只改 attrs（之後 pw.predict 用）。檢查 (a) 仍用先驗卡；lastOVR／dOVR 改用 window_ref（同一個 c、本季 0 場的版本）。"""
    games = {r['GAME_ID'] for b in sd26['box'].values() for r in b['rows']}
    c = len(games) / GAMES_PER_SEASON * G_GAMES
    posmap = {p: {'PG': 'G', 'SG': 'G', 'SF': 'F', 'PF': 'F', 'C': 'C'}.get(pc.get('pos')) for p, pc in prior_cards.items()}
    vd, ww = RD.veteran(c, '2026-27', posmap)
    n = 0
    for pid, x in attrs.items():
        v = vd.get(pid)
        if not v:
            continue
        for a in DEF_ATTRS:
            if v.get(a) is not None:
                x[a] = v[a]
        n += 1
    VET_DEF_INFO.update(games=len(games), c=c, weights=ww, players=n)
    print(f'老將防守四季窗口：聯盟 {len(games)} 場（c={c:.2f} 格），權重 {ww}，更新 {n} 人', file=sys.stderr)
    if PD.ON:
        vet_pres_drive(c, attrs)
    if GRAVITY:
        vet_gravity(c, attrs, prior_cards)
    live_bonus(pw, c)
    window_ref(attrs0, posmap, pw, c)


def vet_pres_drive(c, attrs):
    """老將 pressure／drive：四季窗口（pres_drive.veteran）。算不出的人維持先驗卡。presDisplay 走 pres_display()。"""
    global PD_INFO
    vd, ww = PD.veteran(c)
    PD_VET.clear()
    cnt = {a: 0 for a in PD_ATTRS}
    for pid, x in attrs.items():
        v = vd.get(pid)
        if not v:
            continue
        PD_VET[pid] = v
        for a in PD_ATTRS:
            if v.get(a) is not None:
                x[a] = v[a]
                cnt[a] += 1
    PD_INFO = {'c': c, 'weights': ww, 'updated': cnt, 'module': 'live/pres_drive.py'}
    print(f'老將壓迫／切入四季窗口：權重 {ww}，更新 {cnt}', file=sys.stderr)


GRAV = {}               # 0.2.10j：{pid: {'gravity','raw','src','frames25','frames26'}}（老將＋新秀）
GRAV_INFO = {}


def vet_gravity(c, attrs, prior_cards):
    """0.2.10j：gravity＝2025-26／本季無球外線引力 FRAMES 加權×四季窗口季權重（gravity_live.live）；老將換進 attrs，新秀在 write_outputs 用。
    基準（window_ref）沿用 attrs0＝先驗卡 gravity（＝gravity_live cur=False 的值）。"""
    rk = json.load(open(ROOKIE_JSON, encoding='utf-8'))['players']
    pos = {p: pc.get('pos') for p, pc in prior_cards.items()}
    pos.update({r['playerId']: DPOS[r['pos']] for r in rk if r['playerId'] not in pos})
    g, info = GV.live(c, NS['ns']['DATA26'], pos, rookies=[r['playerId'] for r in rk if r['playerId'] not in prior_cards], fit_exclude=__import__('pointwise_pipeline').EXCLUDE_T)
    GRAV.clear(); GRAV.update(g)
    GRAV_INFO.clear(); GRAV_INFO.update(info)
    n = 0
    for pid, x in attrs.items():
        v = g.get(pid)
        if v is not None:
            x['gravity'] = v['gravity']
            n += 1
    print(f"引力（gravity）：權重 {info['weights']}，本季檔 {info['cur'].get('n')} 人，OLS n={info['ols']['n']}，更新 {n} 人，來源 {info['src']}", file=sys.stderr)


def pres_display(pid, pc):
    v = PD_VET.get(pid)
    return round(v['presDisplay'], 1) if v and v.get('presDisplay') is not None else pc.get('presDisplay', '')


def live_bonus(pw, c):
    """defenseBonus 解凍（2026-10-30 使用者）：E-104 D 每天重擬合，窗口 [c, 328+c]（defense_bonus.py），
    換掉 M27_DEF 對應的 def-L 檔後重算 pw.pipe 的 UL 加成；posMeanD、門檻（possW≥500／2500）、0.75 照 card 0.2.7。"""
    g = NS['ns']
    DEF_L_LIVE.parent.mkdir(exist_ok=True)
    data = DB.load_data()
    DB.write_csv(DB.fit(data, c), DEF_L_LIVE)
    key = str(g['RAPM_STAR'].resolve())
    assert key in g['M27_DEF'], key
    P = pw.pipe
    old = list(g['m27_bonus_of'](P))          # 凍結的 def-L-primary 版（檢查 (a) 用）
    P._m27_posMeanD_frozen = P._m27_posMeanD
    g['M27_DEF'][key] = DEF_L_LIVE
    if hasattr(P, '_m27_bonus'):
        del P._m27_bonus
    new = g['m27_bonus_of'](P)
    live_pm = P._m27_posMeanD
    DB.write_csv(DB.fit_loo(data, c), DEF_L_BASE)   # 基準：同一個 c，每人只拿掉自己本季的 stints
    BONUS.update(frozen=(old, P._m27_posMeanD_frozen), live=(new, live_pm), base=(base_bonus(P, live_pm), live_pm))
    moved = sum(abs(a - b) > 1e-12 for a, b in zip(old, new))
    VET_DEF_INFO.update(defL=str(DEF_L_LIVE.relative_to(DB.ROOT)), bonusChanged=moved,
                        posMeanD={k: float(v) for k, v in P._m27_posMeanD.items()})
    print(f'防守加成重擬合：c={c:.2f}，{moved} 人加成改變，posMeanD {VET_DEF_INFO["posMeanD"]}', file=sys.stderr)


def base_bonus(P, mean):
    """基準加成：同 run_c4_live.m27_ul_bonus，但 Dw／possW 讀 DEF_L_BASE（每人拿掉自己本季 stints），
    位置平均 posMeanD 用賽中版（全聯盟的量，不是他自己的比賽）。"""
    src = {int(r['playerId']): r for r in csv.DictReader(open(DEF_L_BASE, encoding='utf-8'))}
    out = []
    for p, pos in zip(P.pids, P.pos):
        r = src.get(p)
        pw_ = float(r['poss']) if r else 0.0
        out.append(max(0.0, 0.75 * float(r['D']) - mean[pos]) if r and pw_ >= 5000 * 0.5 else 0.0)
    return out


def swap_bonus(pw, which):
    pw.pipe._m27_bonus, pw.pipe._m27_posMeanD = BONUS[which]


def write_outputs(g, loc, out_dir, rows, head, nopr):
    C, ATTRS = g['C'], g['ATTRS']
    doc = json.load(open(ROOKIE_JSON, encoding='utf-8'))
    rookies = doc['players']
    assert g['SAT'] and g['USAGE_MODE'] and g['E064_MODE'] == 'G1', '新秀版只支援 027 live 設定'
    pw, anc, r_repl, sd26, team = loc['pw'], loc['anc064'], loc['r_repl064'], loc['sd26'], loc['team']
    rel = g['V2'].load_reliability()
    prior_pids = set(loc['prior_cards'])
    rookies = [r for r in rookies if r['playerId'] not in prior_pids]       # 保險：有卡的不當新秀
    wins = rookie_windows(g, sd26, C.mapping_for(g['PRIOR']), rookies, g['ALL_N'])
    dfns = RD.inseason('2026-27', {r['playerId']: r['pos'] for r in rookies})
    if PD.ON:
        PD_ROOK.clear()
        PD_ROOK.update(PD.inseason({r['playerId']: r['pos'] for r in rookies}))
        for pid, v in PD_ROOK.items():
            dfns.setdefault(pid, {}).update({a: v.get(a) for a in PD_ATTRS}, minW=v.get('minW'))
    if TOV_POSS:
        for rk in rookies:
            b_ = sd26['box'].get(rk['playerId'])
            if b_ and b_['rows']:
                dfns.setdefault(rk['playerId'], {}).update(tovRows=b_['rows'], tovPid=rk['playerId'], tovPos=DPOS[rk['pos']])
    if GRAVITY:
        for rk in rookies:
            v = GRAV.get(rk['playerId'])
            if v is not None and v['src'] != 'rookie-g0':
                dfns.setdefault(rk['playerId'], {}).update(gravity=v['gravity'], frames26=v['frames26'])
    _, coef, _ = g['load_usage']()
    dl = {int(r['playerId']): r for r in csv.DictReader(open(DEF_L_LIVE, encoding='utf-8'))}
    bad = team_badness(sd26)
    rk_rows = []
    for rk in rookies:
        pid = rk['playerId']
        b = sd26['box'].get(pid)
        gp = len(b['rows']) if b else 0
        mins = sum(r['MIN'] for r in b['rows']) if b else 0.0
        rec = wins.get(pid)
        cur = eval_rookie(g, pw, anc, r_repl, rk, rec, 'e116', rel, dfns.get(pid) if gp > 0 else None)
        base = eval_rookie(g, pw, anc, r_repl, rk, None, 'e116', rel)
        tb = bad.get(max(b['rows'], key=lambda r: r['GAME_DATE'])['TEAM_ID']) if gp > 0 else None
        ch = chain_rookie(g, pw, anc, r_repl, dict(cur, pid=pid), rk['pos'], gp, dl, coef, tb['d'] if tb else 0.0)
        cur.update(pred=ch['pred'], g=ch['g'], ovr=ch['ovr'])
        row = {k: '' for k in head}
        row.update({'ovr': g['r1'](cur['ovr']), 'name': rk['name'], 'pos': rk['pos'], 'MIN': 0,
                    'predictedPer36': round(ch['pred'], 3), 'defenseBonus': round(ch['bonus'], 3), 'align': 0.0,
                    'pred0': round(cur['pred0'], 3), 'playerId': pid, 'N': gp, 'team': team.get(pid, rk['team']),
                    'MIN26': round(mins, 1), 'lastOVR': g['r1'](base['ovr']),
                    'dOVR': round(cur['ovr'] - base['ovr'], 2), 'MPG0': round(rk['mpg0'], 2),
                    'MPGhat': round(cur['mpgHat'], 2), 'g': round(cur['g'], 3), 'ovrPer36': '',
                    'predNew': round(ch['predNew'], 4)})
        if rec is not None and rec['GP'] > 0:
            row['MPGwin'] = round(rec['MIN'] / rec['GP'], 2)
            if 'stamina' in cur['w']:
                row['wMPG'] = round(cur['w']['stamina'], 4)
        for a in ATTRS:
            row[a] = g['r1'](cur['x'][a] if a != 'heightInches' else rk['heightInches'])
        if PD.ON and gp > 0 and 'presDisplay' in row and PD_ROOK.get(pid, {}).get('presDisplay') is not None:
            row['presDisplay'] = round(PD_ROOK[pid]['presDisplay'], 1)
        row['_ovr'] = cur['ovr']
        row['_cur'], row['_base'], row['_pick'], row['_chain'] = cur, base, rk['pick'], dict(ch, d=tb['d'] if tb else None)
        rk_rows.append(row)
    loc_rookies = {r['playerId'] for r in rk_rows}
    nopr[:] = [r for r in nopr if r['playerId'] not in loc_rookies]
    # 老將列複製一份重排名次（原 rows 不動，後面的統計照舊只含老將）
    merged = [dict(r) for r in rows] + [dict(r) for r in rk_rows]
    merged.sort(key=lambda r: -r['_ovr'])
    for i, r in enumerate(merged, 1):
        r['rank'] = i
    # 沒打球的新秀（N=0）不進排名：OVR 只是先驗值，仍寫入 rookies 檔
    C.write_csv(out_dir / 'ranking.csv', [{k: r[k] for k in head} for r in merged if r['N'] > 0 or r['playerId'] not in loc_rookies], head)
    slim = []
    for r in rk_rows:
        slim.append({'playerId': r['playerId'], 'name': r['name'], 'team': r['team'], 'pick': r['_pick'],
                     'pos': r['pos'], 'N': r['N'], 'ovr': r['ovr'], 'lastOVR': r['lastOVR'],
                     'rank': next(m['rank'] for m in merged if m['playerId'] == r['playerId']),
                     'x0': r['_base']['x'], 'xhat': r['_cur']['x'], 'w': r['_cur']['w'],
                     'chain': {k: r['_chain'][k] for k in ('possW', 'bonus', 'pred', 'predNew', 'd')}})
    json.dump(slim, open(out_dir / 'rookies-detail.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if GRAVITY:     # 檢視器 GRV tooltip 用：原始引力值、來源（是否推估）
        json.dump({'meta': GRAV_INFO, 'players': {str(p): v for p, v in GRAV.items()}}, open(out_dir / 'gravity.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if PD.ON:       # 檢視器 PRES tooltip 用：窗口後的收縮分量（老將）／本季分量（有上場的新秀）
        played = {r['playerId'] for r in rk_rows if r['N'] > 0}
        side = {'meta': PD_INFO, 'players': {}}
        for src, d in (('veteran', PD_VET), ('rookie', {p: v for p, v in PD_ROOK.items() if p in played})):
            for pid, v in d.items():
                if 'shr' in v:
                    side['players'][str(pid)] = {'src': src, 'pressure': v['pressure'], 'presDisplay': v['presDisplay'],
                                                 'drive': v.get('drive'), 'force': v['force'], 'minW': v['minW'], 'shr': v['shr']}
        json.dump(side, open(out_dir / 'pres-drive.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    _ns = load_ns()
    raise SystemExit(_ns['main']())
