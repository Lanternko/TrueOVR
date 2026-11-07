"""inseason 0.2.5（R-050 起新賽季版號＝先驗正式卡版號；E-095 採用，R-052；v5 Path A C4，E-033；先驗卡 x0＝card 0.2.5／0.2.4 能力值＝card 0.2.2 能力值；OVR 為每場，R-028 / E-064 G1；E-074、E-091）的 2026-27 即時版：逐球員用自己的已打場數 N 更新能力值與 OVR。

舊版（CARD_MODE=020／022／024／025／026／027／027b／027d／028／029）見 git 歷史／live/_retired/README.md。
- c = 1 凍結；δ²、rel（σ²、nRef）沿用既有函式（c4_v5.delta2_info；只用嚴格早於 S* 的起點 Y1..Y6、D1..D3）。
- 每位球員 f = min(GP / 82, 1)，GP 是他自己在 2026-27 已出賽場數（視窗＝他的全部已打場次）。
- 沒有 2025-26 先驗卡的球員不給 OVR，列在 no-prior.csv。
- OVR 走逐點管線 pointwise_pipeline（pr、封頂 T 固定為開季先驗卡）。
- 不改 v4/v5 既有檔；本檔在記憶體裡覆寫 v4_common 的 CHAIN / 映射 / RAPM 路徑 / 目標季載入（同 pathA_common 的做法）。

用法：python -I reports/ovr-inseason-2026-27/live/run_c4_live_rookie.py [輸出資料夾名，預設用資料截止日]（本檔不能直接執行，R-107 單一入口）
輸入（唯讀）：data/defense-seventh/2026-27/{player-games,team-games}.json、pbp/；先驗卡與 2025-26 原始資料。
不得依 2026-27 結果調參數（L-026）：c、G、k、w 都是凍結值。
"""
import csv
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(REPORT / 'v5' / 'tools'))

import pathA_common as PA  # noqa: E402
from pathA_common import base as C, SA  # noqa: E402
import c4_v5 as C4  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402
import inseason_common_v4 as IC  # noqa: E402
import v2_common as V2  # noqa: E402
import pointwise_pipeline as PW  # noqa: E402
from ovr_common import ATTRS, load_json  # noqa: E402

import os  # noqa: E402
# card 0.1.2 有 16 個屬性（drive 之後多一欄 foulDraw）；ATTRS 在原地加欄，凍結管線／summary 依此順序讀係數。
if 'foulDraw' not in ATTRS:
    ATTRS.insert(ATTRS.index('drive') + 1, 'foulDraw')
import e062_switch as _E062  # noqa: E402
# 舊版機制（CARD_MODE 020～029）見 git 歷史／live/_retired/README.md
CARD_MODE = os.environ.get('CARD_MODE', '0210g')  # 只接受目前版本 0210g（card／inseason 0.2.10g＝0.2.10f＋用人層（L、a）四季滑動窗口，E-192；0.2.10f＝0.2.10e＋E-191b P1m 3PT 欄對照池，ranking／OVR 同 0.2.10e；0.2.10e＝0.2.10d 換 OVR 映射，E-188 S3：PR90→88、PR95→92；0.2.10d＝E-185 四項窗口，底 card 0.2.10c 的 KAU 重擬合）。舊版重現請 checkout 當時 commit（見 live/_retired/README.md）
if CARD_MODE != '0210g':
    raise SystemExit('CARD_MODE 只接受 0210g（舊版已淘汰，重現請 checkout 當時 commit；見 live/_retired/README.md）')
# WIN10=0：關掉 0.2.10d 新增的四項窗口（long、creation、threeValue、MPG_hat），卡／用人層／RAPM 換成 card 0.2.10c（＝card-0.2.10d/work-selfcheck 的逐位元重建，build_usage_0210d.py base10c 產 usage 與 summary），先驗讀 _retired/ 的 0.2.10 檔（屬性同）；只用來拆「0.2.10c 底」與「窗口」各占多少（報告用，不上線）
WIN10 = os.environ.get('WIN10', '1') != '0'
USAGE_WIN = WIN10 and os.environ.get('USAGE_WIN', '1') != '0'   # 0.2.10g：用人層（L、a）= 四季窗口（live/window11.py，每天用當下窗口重算；y、v 用當下年齡）；USAGE_WIN=0 重現 0.2.10f（凍結 2025-26 用人特徵，檔在 _retired/）
TV_P1M = os.environ.get('TV_P1M', '1') != '0'   # 0.2.10f：3PT 欄對照池＝近三季窗口值＋本季（E-191b P1m）；TV_P1M=0 重現 0.2.10e（只用本季窗口池）
MPG_L_FILE = ROOT / 'reports/card-0.2.12/mpg-L-selection.json'   # E-185：MPG 窗口長度 L（季），只用 2024-25 選（mpg_select.py）
MPG_L = json.loads(MPG_L_FILE.read_text(encoding='utf-8'))['selected_L'] if WIN10 else None
# 相容旗標：run_c4_live_rookie.py（assert）與舊實驗腳本（check_prereq 等）仍讀這幾個名字；029a 恆為真
M27_MODE = M26_MODE = USAGE_MODE = SAT = True
E062_MODE = 'off'   # E-062 實驗開關已淘汰（只剩 off）
_E062.install(E062_MODE)

# E-064 每場 OVR，只剩 G1（R-028）：副版（相對替補水準）、MPG_hat＝MPG0 + w·(MPG_win − MPG0)，w＝stamina 的 C4 w。
E064_MODE = os.environ.get('E064_MODE', 'G1')
if E064_MODE != 'G1':
    raise SystemExit('E064_MODE 只接受 G1（off／G0 是舊頁重現用，已淘汰）')
# 預註冊 §4.1：stamina 最小樣本 1 場（本身的能力值與 w 都用；其餘 15 屬性照 C4 現行）。
SA.SEASON_MIN_SAMPLE['stamina'] = 1
VERSION = 'inseason 0.2.12e'  # R-050／R-114：先驗卡 card 0.2.12c；0.2.12e＝防守 D 改個人場次軸（R-163，defense_bonus.py；DEF_AXIS=calendar 回退）＋復出老將補進用人層（R-164，rv_usage；RV_USAGE=0 回退），兩者都關＝0.2.12d；0.2.12d＝復出老將補卡：2025-26 沒上場的老將（Lillard、Kyrie、Haliburton 等）用 v5 舊季卡進四季窗口，其餘管線不動（live/build_returning_vet_prior.py；RETURNING_VETS=0 重現 0.2.12c）；0.2.12c＝tovSkill 的失誤率分母由持球分鐘改觸球次數（R-144，E-207，live/tov_live.py，檔名用 0212c／card-0.2.12c；TOV_TOUCH=0 重現 0.2.12b）；0.2.12b＝四季窗口由 328 格縮成 246 格（R-140，E-204，live/win_len.py；WIN_LEN=328 重現 0.2.12a）；0.2.12a＝gravity 補值依本季分鐘往進攻 EPM 收縮（gravity_live.EPM_ON；GRAVITY_EPM=0 重現 0.2.12）；0.2.12＝tovSkill 改看持球時間（R-139，E-203，live/tov_live.py，檔名用 0212／card-0.2.12-tov）；0.2.11（原標 0.2.10j，R-137 使用者升為 PATCH；檔名沿用 0210j）＝加能力值 gravity（無球外線引力，R-134／R-135，live/gravity_live.py）；0.2.10i＝drive→drive_D、creation→creationJ（R-130／R-132，live/split_dc.py）；0.2.10h＝賽中端 y、v 改用開季當天年齡（R-129，E-193），卡片端不動。 第一個字面值會被 daily_inseason_update.probe_base_version 以正規式讀取，勿改成括號／條件式開頭
CARD_VERSION = 'card 0.2.12c'   # 0.2.12c＝觸球分母（W246，reports/card-0.2.12c/；係數／RAPM 在 328 底 reports/card-0.2.12c-w328/）；TOV_TOUCH=0 回 card 0.2.12b／0.2.12。0.2.12b＝同上窗口 246（reports/card-0.2.12b/）；WIN_LEN=328 時回 card 0.2.12
AGE_START = os.environ.get('AGE_START', '1') != '0'   # 0.2.10h：y、v 用開季當天足歲（data/defense-seventh/2026-27/birthdates.json，live/window11.py）；AGE_START=0 重現 0.2.10g（本季 bio AGE）
# 0.2.10i（R-130／R-132）：切入／自主拆開。SPLIT_DC=0 重現 0.2.10h（卡 card 0.2.10g；先驗、usage 讀 _retired/；window8／window10／pres_drive 由 split_dc.ON 走舊路徑）
SPLIT_DC = os.environ.get('SPLIT_DC', '1') != '0'
if SPLIT_DC and not (WIN10 and USAGE_WIN and AGE_START):
    raise SystemExit('重現 0.2.10h 以前的版本要同時設 SPLIT_DC=0')
# 0.2.10j（R-134／R-135，E-200）：加 gravity。GRAVITY=0 重現 0.2.10i（卡 card 0.2.10i；先驗、usage、新秀起點讀 _retired/；ATTRS 不加 gravity）
GRAVITY = os.environ.get('GRAVITY', '1') != '0'
if GRAVITY and not SPLIT_DC:
    raise SystemExit('重現 0.2.10i 以前的版本要同時設 GRAVITY=0')
# 0.2.12（R-139，E-203）：tovSkill 改看持球時間。TOV_POSS=0 重現 0.2.11（卡 card 0.2.11；先驗、usage 讀 _retired/；window8／新秀不 import tov_live）
TOV_POSS = os.environ.get('TOV_POSS', '1') != '0'
TOV_TOUCH = TOV_POSS and os.environ.get('TOV_TOUCH', '1') != '0'   # 0.2.12c（R-144，E-207）：TOV_TOUCH=0 重現 0.2.12b（卡 card 0.2.12b；先驗、usage、凍結池讀 _retired/）
if TOV_POSS and not GRAVITY:
    raise SystemExit('重現 0.2.10i 以前的版本要同時設 TOV_POSS=0 GRAVITY=0')
if os.environ.get('GRAVITY_EPM', '1') == '0':
    VERSION = 'inseason 0.2.12'
if not TOV_TOUCH:
    VERSION, CARD_VERSION = 'inseason 0.2.12b', 'card 0.2.12b'
if os.environ.get('WIN_LEN', '246') == '328' and TOV_TOUCH:   # 卡片端驗證用：328 窗口的觸球版必須重現 card-0.2.12c-w328（＝E-206 KC final）
    VERSION, CARD_VERSION = 'inseason 0.2.12c-w328', 'card 0.2.12c-w328'
elif os.environ.get('WIN_LEN', '246') == '328':   # 0.2.12b（R-140，E-204）：WIN_LEN=328 重現 0.2.12a（GRAVITY_EPM=0 則 0.2.12）；win_len.install() 在 run_c4_live_rookie 載入時讀同一個環境變數
    VERSION, CARD_VERSION = ('inseason 0.2.12' if os.environ.get('GRAVITY_EPM', '1') == '0' else 'inseason 0.2.12a'), 'card 0.2.12'
if not TOV_POSS:
    VERSION, CARD_VERSION = 'inseason 0.2.11', 'card 0.2.11'
if not GRAVITY:
    VERSION, CARD_VERSION = 'inseason 0.2.10i', 'card 0.2.10i'
elif 'gravity' not in ATTRS:   # 卡片 calibrate --offBallCols gravity 接在屬性尾端；ovr_pipeline 依 ATTRS 順序取 summary 有的欄
    ATTRS.append('gravity')
if not SPLIT_DC:
    VERSION, CARD_VERSION = 'inseason 0.2.10h', 'card 0.2.10g'
if not AGE_START:
    VERSION = 'inseason 0.2.10g'
if not USAGE_WIN:   # USAGE_WIN=0：整組回 0.2.10f（先驗卡、usage 檔、summary、ranking 都用 0.2.10f 的）
    CARD_VERSION = 'card 0.2.10f'
    VERSION = 'inseason 0.2.10f'
if not WIN10:
    CARD_VERSION = 'card 0.2.10c'
_CV = (('card-0.2.12c-w246' if TOV_TOUCH else 'card-0.2.12-tov') if TOV_POSS else (('card-0.2.10j' if GRAVITY else 'card-0.2.10i') if SPLIT_DC else 'card-0.2.10d') if WIN10 else 'card-0.2.10c')   # 係數管線／RAPM 所在的卡（0.2.10e 只換 OVR 映射、0.2.10f 只換 3PT 欄對照池，沒有 cards/、rapm-T6 以外的新檔）
_OV = 'card-0.2.12-tov' if CARD_VERSION == 'card 0.2.12' else 'card-0.2.10j' if CARD_VERSION == 'card 0.2.11' else CARD_VERSION.replace('card ', 'card-')   # 0.2.11＝原標 0.2.10j（R-137），資料夾沿用 card-0.2.10j； OVR 欄與 summary 所在的卡：'card-0.2.10g'（USAGE_WIN=0 時 'card-0.2.10f'、WIN10=0 時 'card-0.2.10c'）
_SC = ROOT / 'reports/card-0.2.10d/work-selfcheck'   # card 0.2.10c 的逐位元重建（WIN10=0 的卡端檔）
_RET = HERE / '_retired'
PRIOR = '2025-26'
TARGET = '2026-27'
G_GAMES = 82
C_PARAM = 1.0
ALL_N = 99                      # 視窗＝全部已打場次
DATA26 = ROOT / 'data/defense-seventh' / TARGET
PRIOR_CARD = (((HERE / 'prior-2025-26-card0212c.json' if TOV_TOUCH else _RET / 'prior-2025-26-card0212-tov.json') if TOV_POSS else _RET / 'prior-2025-26-card0210j.json' if GRAVITY else _RET / 'prior-2025-26-card0210i.json') if SPLIT_DC else _RET / 'prior-2025-26-card0210d.json') if WIN10 else _RET / 'prior-2025-26-card0210.json'  # 0.2.10j：build_prior_0210j.py（加 gravity＝card-0.2.10j/gravity-attr.csv）  # 0.2.10i：build_prior_0210i.py（drive、creation 換 card-0.2.10i/tail-U.csv）  # build_prior_0210d.py 產出（0.2.10 先驗的 long、creation 換成 card-0.2.12/tail-U.csv；8 項是 0.2.10 的 U 窗口值）； build_prior_027b.py 產出（x0＝card 0.2.7b 產生器未四捨五入值；能力值欄 0.2.7b～0.2.9a 逐位元相同）
RETURNING_VETS = TOV_TOUCH and os.environ.get('WIN_LEN', '246') != '328' and os.environ.get('RETURNING_VETS', '1') != '0'   # 0.2.12d：復出老將補卡（build_returning_vet_prior.py；2025-26 無先驗卡、近季有 v5 卡的人，窗口跳過缺席季）；RETURNING_VETS=0 重現 0.2.12c
if VERSION == 'inseason 0.2.12e' and os.environ.get('DEF_AXIS', 'personal') == 'calendar' and os.environ.get('RV_USAGE', 'hi') == '0':
    VERSION = 'inseason 0.2.12d'
if not RETURNING_VETS and VERSION == 'inseason 0.2.12d':
    VERSION = 'inseason 0.2.12c'
if RETURNING_VETS:
    PRIOR_CARD = HERE / 'prior-2025-26-card0212c-rv.json'
    PW.EXCLUDE_T.update(r['playerId'] for r in json.load(open(PRIOR_CARD, encoding='utf-8'))['returningVets'])   # 補卡的人不進 H1 封頂表（T）與引力 OLS，既有球員的分數才不被推動
CARD_DIR = ROOT / f'reports/{_CV}/cards/K6/primary' if WIN10 else _SC / 'base-KAU-2025-26/c0/cards/K0/primary'   # 屬性迴歸／OVR 管線係數（E-164 S 臂，第一層拿掉 stamina）
CARD_SUMMARY = CARD_DIR / 'summary.json'
RAPM_STAR = ROOT / f'reports/{_CV}/rapm-T6.csv'   # align／封頂讀 E-153 K6 的 T6 換進去的 RAPM（與 card 0.2.8 起同口徑）
BIO25 = ROOT / 'data/benchmark-source/bio.json'
FORMAL_RANKING = ROOT / f'reports/{_OV}/ranking.csv'
CARD024_SUMMARY = ROOT / f'reports/{_OV}/summary.json' if WIN10 else _SC / 'summary-card0210c.json'     # 名稱沿用舊版；現為現行 card summary
CARD024_RANKING = ROOT / 'reports/card-0.2.4/ranking.csv'       # E-095 預註冊 §2：現行 ranking 的 mpg 欄必須與 card 0.2.4 相同
W_TAU, W_REF = 15.0, 36.0


def sat_w(m):
    """card 0.2.5 的分鐘權重 W(m) = (1 − e^(−m/15)) / (1 − e^(−36/15))；W(0)=0、W(36)=1。"""
    return (1.0 - math.exp(-m / W_TAU)) / (1.0 - math.exp(-W_REF / W_TAU))

USAGE_FILE = ((((HERE / 'usage-2025-26-card0212c.json' if TOV_TOUCH else _RET / 'usage-2025-26-card0212-tov.json') if TOV_POSS else _RET / 'usage-2025-26-card0210j.json' if GRAVITY else _RET / 'usage-2025-26-card0210i.json') if SPLIT_DC else _RET / 'usage-2025-26-card0210g.json') if USAGE_WIN else _RET / 'usage-2025-26-card0210f.json') if WIN10 else _SC / 'usage-2025-26-card0210c-nowin.json'     # build_usage_0210g.py 產出（0.2.10g：係數同 0.2.10d，r_repl／錨點用新池重取，features 為 2025-26 季末 c=82 窗口值）；USAGE_WIN=0 讀 _retired/ 的 0.2.10f 檔。以下為 0.2.10f 原註解：build_usage_0210f.py 產出（card 0.2.10d 的 KAU 重擬合係數／r_repl／錨點＋E-188 的 PR90／PR95，不是凍結值；WIN10=0 檔由 _retired/build_usage_0210d.py base10c 產）（係數、r_repl、錨點；b8_ydL＝0）；錨點／r_repl 也從這裡讀
POOL026 = HERE / 'pool-027b.json'                     # e128-card027b/build_pool_027b.py 產出的凍結合併池
DEF_L_PRIMARY = ROOT / 'reports/card-0.2.5+E104-defense-pergame-decay/def-L-primary.csv'   # UL 防守加成的 --defRapm
E128_RB = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a'
THREE_PRIOR = ROOT / 'reports/ovr-v62-3pt-difficulty-2025-26/new-long.json'   # abilityC（難度調整準度）＝上季先驗
THREE_K = 294.667                 # E-057：v62 方法 (c) 的 k（出手數單位）
THREE_REP_GAP = 0.03              # rep = 聯盟 3P% − 0.03
THREE_POOL_MIN = 500              # 池：合併 MIN >= 500 且有先驗卡
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


# ==== E-107 026 BEGIN ====
# CARD_MODE=026（E-107，預註冊 reports/ovr-inseason-2026-27/e107-card026/preregistration.md §2.3–2.4）專用的純函式。
# 只有 026 模式會呼叫；其他模式逐位元不變。build_pool_026.py、check_prereq.py、backtest_e107.py 讀這兩行標記之間的文字 exec 共用，
# 執行時命名空間要有 SA、IC、math、json（bisect、hashlib 本段自己 import）。尾巴常數、池門檻照 E-101（build_e101.py）凍結值。
import bisect  # noqa: E402
import hashlib  # noqa: E402
M26_CEIL, M26_K_SD, M26_Z9990 = 150.0, 1.96, 1.044
M26_PCT = ('tovSkill', 'pass', 'rebound', 'creation', 'stamina', 'foulDraw')
M26_CURVE = {'long': 'CURVE_3PT', 'mid': 'CURVE_MID', 'short': 'CURVE_SHORT', 'ft': 'CURVE_FT'}
M26 = {}      # m26_load_pool() 載入的 live/pool-026.json


def m26_zone_of(action):
    """SA.zone_of ＋ E-101 規則：有 area 且 area=='Mid-Range' 且 (shotDistance or 0) < 8 → short（同 extract_pbp_e101.py）。"""
    area = action.get('area')
    if area:
        if area == 'Mid-Range' and (action.get('shotDistance') or 0.0) < 8.0:
            return 'short'
        return 'mid' if area == 'Mid-Range' else 'short'
    x, y = action.get('xLegacy'), action.get('yLegacy')
    if x is None or y is None:
        return 'short'
    if x == 0 and y == 0:
        return 'short'
    return 'short' if (abs(x) <= 80 and y <= 138) else 'mid'


def m26_attr_of(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def m26_top_tail(d, sd):
    return 99 + (M26_CEIL - 99) * (1 - math.exp(-max(0.0, d) / (M26_K_SD * sd)))


def m26_bot_tail(d, sd):
    return 40 - 15 * (1 - math.exp(-max(0.0, d) / sd))


def m26_inverse_open(p, curve, lo, hi):
    """同 build_e101.inverse_open（= build_e090.inverse_open）。"""
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if min(y0, y1) <= p <= max(y0, y1):
            return max(lo, min(hi, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    x = curve[0][0] if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else curve[-1][0]
    return max(lo, min(hi, x))


def m26_pct(x, s):
    """小於者 + 0.5·相等者（同 ovr_common.percentile、build_e101.Pool.pct）；s 已排序。"""
    lo, hi = bisect.bisect_left(s, x), bisect.bisect_right(s, x)
    return 100 * (lo + 0.5 * (hi - lo)) / len(s)


def m26_anchors(vals):
    """同 build_e101.Pool.anchors('max')。"""
    s = sorted(float(v) for v in vals)
    n = len(s)
    r90 = min(v for v in s if m26_pct(v, s) >= 90)
    r99 = min(v for v in s if m26_pct(v, s) >= 99)
    r1 = max(v for v in s if m26_pct(v, s) <= 1)
    m = sum(s) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in s) / n)
    gap = (r99 - r90) / M26_Z9990
    return {'r90': r90, 'r99': r99, 'r1': r1, 'SD_pool': sd, 'gapScale': gap, 'S': max(gap, sd),
            'insuranceActive': bool(sd > gap), 'poolN': n}


def m26_pct_attr(x, ent):
    """百分位型（build_e101.percentile_attr_merged，mode max）：PR≥99 且開頂端→top_tail(x−r99, S)；PR≤1 且開底端→bot_tail(r1−x, SD_pool)。"""
    p = m26_pct(x, ent['sorted'])
    an = ent['anchors']
    if p >= 99 and ent['top']:
        return m26_top_tail(x - an['r99'], an['S'])
    if p <= 1 and ent['bot']:
        return m26_bot_tail(an['r1'] - x, an['SD_pool'])
    return m26_attr_of(p)


def m26_curve_attr(p, ent, curve):
    """命中率型（build_e101.build 的 curve 分支）：p > a99 且開頂端→99＋51·(1−e^(−(p−a99)/s))/(1−e^(−(1−a99)/s))，s＝1.96·S_p；否則反查曲線夾 [lo, 99]。"""
    a99, s = ent['a99'], ent['s']
    if ent['top'] and p > a99:
        return 99 + (M26_CEIL - 99) * (1 - math.exp(-(p - a99) / s)) / (1 - math.exp(-(1 - a99) / s))
    return m26_inverse_open(p, curve, ent['lo'], 99.0)


def m26_shrunk(makes, attempts, mean):
    """ovr_common.shooting 的收縮命中率（固定 100 次偽出手），還沒反查曲線。"""
    return (makes + 100 * mean) / (attempts + 100)


def m26_e2_short(base, prior_card, creation_prior, lo):
    """IC._e2_short，只把夾值 [40, 99] 換成 [lo, 150]（2025-26 先驗卡沒有 e2 → 直接回傳 base）。"""
    e2 = prior_card.get('e2') if prior_card else None
    if not e2:
        return base
    s_tilde = float(e2['sTilde'])
    pos = prior_card.get('pos')
    exempt = 0.0
    if pos in ('PF', 'C') and creation_prior is not None:
        exempt = max(0.0, min(1.0, (creation_prior - 55.0) / 10.0))
    eff = SA.E2_LAMBDA + (1 - SA.E2_LAMBDA) * exempt
    factor = s_tilde + eff * (1 - s_tilde)
    return max(lo, min(M26_CEIL, 70.0 + (base - 70.0) * factor))


def m26_foul_comp(fta, fga, mn, fz):
    """E-070 合成值，常數凍結自 2025-26（同 run_c4_live.foul_draw_y 的算式與運算順序）。"""
    z_vol = (fta / mn * 36.0 - fz['vol']['mean']) / fz['vol']['std']
    z_rate = (fta / fga - fz['rate']['mean']) / fz['rate']['std']
    return fz['wVol'] * z_vol + fz['wRate'] * z_rate


def m26_range(a):
    """026 模式各屬性的合法範圍（照開關）：百分位型 bot→25、命中率型 bot→0、否則 40；top→150、否則 99。"""
    ent = M26['attrs'][a]
    lo = (25.0 if ent['type'] == 'percentile' else 0.0) if ent['bot'] else 40.0
    return lo, (M26_CEIL if ent['top'] else 99.0)


def m26_clip(v):
    """026 模式取代 v4_common.clip：x̂ 是 x0 與 y_adj 的凸組合，兩者都在 m26_range 內，故只防數值意外；放寬到 [0, 150]。"""
    return max(0.0, min(M26_CEIL, v))


def m26_payload_sha(doc):
    body = json.dumps({k: v for k, v in doc.items() if k != 'payloadSha256'}, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'))
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def m26_load_pool(path):
    doc = json.loads(open(path, encoding='utf-8').read())
    if m26_payload_sha(doc) != doc['payloadSha256']:
        raise SystemExit(f'{path} payload sha256 不符')
    M26.clear()
    M26.update(doc)
    return doc


def m26_pass_027b(s, ast_pct100, pf, ent):
    """E-128 errata-1：視窗 pass＝百分位型映射(0.5·z(AST/MIN·36)+0.5·z(AST/astCh))；視窗不收縮；z 常數＝pool 的 passFreeze。
    pb['pass'] 是 AST%×100，÷100 回到 AST/astCh。"""
    y_vol = s['AST'] / s['MIN'] * 36.0 if s['MIN'] > 0 else 0.0
    y_rate = ast_pct100 / 100.0
    z = (pf['wVol'] * (y_vol - pf['vol']['mean']) / pf['vol']['std']
         + pf['wRate'] * (y_rate - pf['rate']['mean']) / pf['rate']['std'])
    return m26_pct_attr(z, ent)


def split_creation(pid, games, minutes):
    """0.2.10i：新秀（沒有先驗卡、走 m26_window_cards 的人）creationJ＝視窗內 J 類加權分子／視窗分鐘×36，映射＝window10 的 creation_map（同老將窗口）。"""
    import numpy as np
    W = win8_load()
    n = sum(W['crJ'].get((g, int(pid)), 0.0) for g in games)
    return float(W['creationMap'](np.array([n / max(minutes, 1.0) * 36.0]))[0])


def m26_window_cards(sd, n, mapping, prior_cards, received, season_min_sample=None):
    """IC.window_cards 的 026 版：原始值、樣本、u_proxy 逐字照抄；映射改成 pool-026 合併池＋E-101 尾巴；另帶 foulDraw 觀測值。
    命中率型的收縮先驗仍用 mapping['priors']（先驗季聯盟命中率，同 IC）；drive 照舊（凍結屬性，不進更新）。"""
    P, CV = M26['attrs'], IC.CURVES
    gm = IC.window_game_map(sd, n)
    stats = SA.aggregate(sd, gm)
    totals = SA.team_totals(sd)
    pb = SA.pass_rebound_raw(sd, gm)
    pr = mapping['priors']
    fz = M26['foulDrawConstants']
    out = {}
    for pid, s in stats.items():
        pc = prior_cards.get(pid)
        if pc is None:
            continue
        if not received:
            creation = float(pc['creation'])
        else:
            rec = received.get(pid, 0.5)
            creation = (split_creation(pid, gm[pid], s['MIN']) if SPLIT_DC
                        else m26_pct_attr((1.0 - rec) * s['FGA'] / max(s['MIN'], 1.0) * 36.0, P['creation']))
        base_short = m26_curve_attr(m26_shrunk(s['shortM'], s['shortA'], pr['short']), P['short'], CV['CURVE_SHORT'])
        onfloor = 0.0
        for r in sd['box'][pid]['rows']:
            if r['GAME_ID'] not in gm[pid]:
                continue
            t = totals.get(r['GAME_ID'], {}).get(r['TEAM_ID'])
            if t:
                onfloor += SA.team_possessions(t) * r['MIN'] / 48.0
        events = s['FGA'] + 0.44 * s['FTA'] + s['TOV']
        card = {
            'playerId': pid,
            'long': m26_curve_attr(m26_shrunk(s['FG3M'], s['FG3A'], pr['long']), P['long'], CV['CURVE_3PT']),
            'mid': m26_curve_attr(m26_shrunk(s['midM'], s['midA'], pr['mid']), P['mid'], CV['CURVE_MID']),
            'shortBase': base_short,
            'short': m26_e2_short(base_short, pc, pc.get('creation'), P['short']['lo']),
            'ft': m26_curve_attr(m26_shrunk(s['FTM'], s['FTA'], pr['ft']), P['ft'], CV['CURVE_FT']),
            'drive': IC.attr(IC.percentile(SA.safe(s['FTA'], s['FGA']), mapping['pools']['drive'])),
            'tovSkill': m26_pct_attr(-SA.safe(s['TOV'], s['possDen']), P['tovSkill']),
            'pass': (m26_pass_027b(s, pb['pass'][pid], M26['passFreeze'], P['pass']) if 'passFreeze' in M26
                     else m26_pct_attr(pb['pass'][pid], P['pass'])),
            'rebound': m26_pct_attr(pb['rebound'][pid], P['rebound']),
            'stamina': (m26_pct_attr(s['MPG'], P['stamina']) if 'stamina' in P      # 027（E-111 §1.3）：池裡沒有 stamina
                        else IC.attr(IC.percentile(s['MPG'], mapping['pools']['stamina']))),   # → 照 IC.window_cards 單季映射
            'creation': creation,
            'foulDraw': (m26_pct_attr(m26_foul_comp(s['FTA'], s['FGA'], s['MIN'], fz), P['foulDraw'])
                         if s['FGA'] > 0 and s['MIN'] > 0 else None),
            'sample': {'fg3a': s['FG3A'], 'midA': s['midA'], 'shortA': s['shortA'], 'fta': s['FTA'],
                       'fga': s['FGA'], 'possDen': s['possDen'], 'min': s['MIN'], 'gp': s['GP'],
                       'defensePossessions': 0.0},
            'MIN': s['MIN'], 'GP': s['GP'],
            'u_proxy': 100.0 * events / onfloor if onfloor > 0 else 0.0,
            'u_proxy_per36': events / max(s['MIN'], 1.0) * 36.0,
        }
        out[pid] = card
    return out
# ==== E-107 026 END ====


# ==== E-111 027 BEGIN ====
# CARD_MODE=027（E-111，預註冊 reports/ovr-inseason-2026-27/e111-card027/preregistration.md §1）專用；其他模式不呼叫。
# build_pool_027.py、check_prereq.py、backtest_e111.py 連同上面的 E-107 段一起 exec（命名空間要有 SA、IC、math、json）。
M27_AREA_PBP = {('defense-seventh', '2022-23'), ('defense-seventh', '2023-24'), ('defense-seventh', '2024-25'),
                ('defense-seventh', '2025-26'), ('data', 'defense-a-source')}     # 有 area 欄的季（2022-23～2025-26）的 PBP 目錄
M27_ZONE_DROPPED = {}       # {PBP 目錄: 被跳過的 area 缺值 2pt 出手數}
M27_DEF = {}                # {rapm.csv 絕對路徑: 該起點 UL 防守加成用的單季 D 檔（def-L）}


def m27_area_dir(path):
    """PBP 檔所在目錄若屬於有 area 欄的季，回傳該目錄字串；否則 None（2021-22 以前、2026-27 照座標規則）。"""
    from pathlib import Path as _P
    d = _P(path).resolve().parent
    if d.name != 'pbp':
        return None
    key = (d.parent.parent.name, d.parent.name)
    return d.as_posix() if key in M27_AREA_PBP else None


def m27_install_zone_filter():
    """E-111 §1.4：有 area 欄的季，area 缺值的 2pt 投籃動作在載入時丟掉（同 E-101 跳過：不算 mid 也不算 short）；
    分區規則用 m26_zone_of（Mid-Range 且 shotDistance<8 → short；沒有 area 欄的季照座標）。包 SA／IC 的 load_json，冪等。"""
    SA.zone_of = m26_zone_of
    for mod in (SA, IC):
        if getattr(mod.load_json, '_m27', False):
            continue
        orig = mod.load_json

        def lj(path, _orig=orig):
            doc = _orig(path)
            key = m27_area_dir(path)
            if key is None:
                return doc
            acts = doc['data']['game']['actions']
            keep = [a for a in acts if not (a.get('isFieldGoal') == 1 and a.get('actionType') == '2pt' and not a.get('area'))]
            if len(keep) != len(acts):
                M27_ZONE_DROPPED[key] = M27_ZONE_DROPPED.get(key, 0) + len(acts) - len(keep)
                doc['data']['game']['actions'] = keep
            return doc
        lj._m27 = True
        mod.load_json = lj


def m27_ul_bonus(pipe):
    """card 0.2.7（UL6 primary：--bonusShape none --defWindow season --defPossFactor 0.5）的防守加成，逐 pipe.pids：
    Dw／possW＝def-L 檔的 D／poss（沒有的人 Dw=NaN、possW=0）；posMeanD(pos)＝Σ MIN·0.75·Dw／Σ MIN（同 pos、possW≥500）；
    centeredD＝0.75·Dw − posMeanD（possW≥500，否則 NaN）；bonus＝max(0, centeredD)（possW≥2500 且非 NaN，否則 0），不乘 taper。
    MIN＝先驗卡 observed.MIN（= 產生器 MIN）。賽中凍結（onBall、help 凍結，D 不逐場更新）。"""
    import csv as _csv
    key = str(__import__('pathlib').Path(pipe.rapm_path).resolve())
    if key not in M27_DEF:
        raise SystemExit(f'E-111：{key} 沒有對應的 def-L 檔（M27_DEF）')
    src = {int(r['playerId']): r for r in _csv.DictReader(open(M27_DEF[key], encoding='utf-8'))}
    n = len(pipe.pids)
    dw = [float(src[p]['D']) if p in src else float('nan') for p in pipe.pids]
    pw = [float(src[p]['poss']) if p in src else 0.0 for p in pipe.pids]
    blend_w, min_w = 1000 * 0.5, 5000 * 0.5
    mean = {}
    for pos in set(pipe.pos):
        idx = [i for i in range(n) if pipe.pos[i] == pos and pw[i] >= blend_w]
        mean[pos] = sum(pipe.minutes[i] * 0.75 * dw[i] for i in idx) / sum(pipe.minutes[i] for i in idx)
    out = []
    for i in range(n):
        if pw[i] >= min_w and pw[i] >= blend_w and not math.isnan(dw[i]):
            out.append(max(0.0, 0.75 * dw[i] - mean[pipe.pos[i]]))
        else:
            out.append(0.0)
    return out, mean


def m27_bonus_of(pipe):
    if not hasattr(pipe, '_m27_bonus'):
        pipe._m27_bonus, pipe._m27_posMeanD = m27_ul_bonus(pipe)
    return pipe._m27_bonus


def m27_ovr_predict(self, attrs_by_pid):
    """OVRPipeline.predict 的 027 版：bonus 換成 m27_bonus_of（UL，不乘 taper），align（poss≥5000）、H1 封頂照舊。"""
    import numpy as np
    import ovr_pipeline as OP
    from ovr_common import ATTRS as _A
    raw = np.array([[attrs_by_pid[p][a] for a in getattr(self, 'attrs', _A)] for p in self.pids], float)   # 027d：迴歸無 physique
    pred0 = self.design(raw)
    pr_pool = sorted(pred0[i] for i in range(len(pred0)) if self.pr_mask[i])
    pr = np.array([OP.percentile_rank(v, pr_pool) for v in pred0])
    bonus = np.array(m27_bonus_of(self), float)
    align = np.zeros(len(pred0))
    for i in range(len(pred0)):
        if self.poss[i] >= OP.BONUS_MIN_POSS:
            align[i] = 0.25 * (self.r[i] - pred0[i])
    lift = bonus + align
    pred = pred0 + bonus + align
    import pointwise_pipeline as _PWX
    pool = np.array([p not in _PWX.EXCLUDE_T for p in self.pids]) if _PWX.EXCLUDE_T else None
    pred, iters = OP.cap_total_lift(pred, pred0, lift, self.allowed, pool)
    p1, p50, p99 = self.anchors
    ovr = np.where(pred <= p50, 40 + 30 * (pred - p1) / (p50 - p1), 70 + 29 * (pred - p50) / (p99 - p50))
    out = {}
    for i, p in enumerate(self.pids):
        out[p] = {'pred0': float(pred0[i]), 'bonus': float(bonus[i]), 'align': float(align[i]),
                  'pred': float(pred[i]), 'ovr': float(ovr[i]), 'pr': float(pr[i])}
    out['_capIterations'] = iters
    return out


def m27_pw_predict(self, attrs_by_pid):
    """PointwisePipeline.predict 的 027 版：bonus＝m27_bonus_of（不乘 taper，固定）；align、逐點封頂 T(A) 照舊。"""
    import numpy as np
    import ovr_pipeline as OP
    from ovr_common import ATTRS as _A
    P = self.pipe
    raw = np.array([[attrs_by_pid[p][a] for a in getattr(P, 'attrs', _A)] for p in P.pids], float)
    pred0 = P.design(raw)
    ub = m27_bonus_of(P)
    out = {}
    p1, p50, p99 = P.anchors
    for i, p in enumerate(P.pids):
        bonus, align = ub[i], 0.0
        if P.poss[i] >= OP.BONUS_MIN_POSS:
            align = 0.25 * (P.r[i] - pred0[i])
        pred = pred0[i] + bonus + align
        a = P.allowed[i]
        if a is not None and bonus + align > 0:
            pred = min(pred, max(pred0[i], self.T[a]))
        ovr = 40 + 30 * (pred - p1) / (p50 - p1) if pred <= p50 else 70 + 29 * (pred - p50) / (p99 - p50)
        out[p] = {'pred0': float(pred0[i]), 'bonus': float(bonus), 'align': float(align),
                  'pred': float(pred), 'ovr': float(ovr), 'pr': float(self.pr0[i])}
    return out


def m27_install_ul(def_by_rapm):
    """換掉 OVRPipeline.predict／PointwisePipeline.predict（類別層，只在 027 呼叫）；def_by_rapm＝{rapm.csv 絕對路徑: def-L 檔}。"""
    import ovr_pipeline as OP
    import pointwise_pipeline as PWM
    M27_DEF.update({str(__import__('pathlib').Path(k).resolve()): v for k, v in def_by_rapm.items()})
    OP.OVRPipeline.predict = m27_ovr_predict
    PWM.PointwisePipeline.predict = m27_pw_predict
    if not getattr(OP.OVRPipeline.__init__, '_m27', False):     # E-111 errata 1：RAPM 名次同分照卡片產生器
        orig_init = OP.OVRPipeline.__init__

        def init(self, summary_path, rapm_path, prior_cards):
            orig_init(self, summary_path, rapm_path, prior_cards)
            self.allowed = m27_card_allowed(self, rapm_path)
        init._m27 = True
        OP.OVRPipeline.__init__ = init


def m27_card_allowed(pipe, rapm_path):
    """E-111 errata 1：H1 封頂的 allowed（margin 0）＝card 產生器 calibrate-wing.py attach_external_ranks＋cap_allowed 的 rapmRank：
    rapm.csv 以 name 為 key（同名最後一列覆蓋、dict 保留首次出現位置）；池＝pooledPoss≥5000；依 pooledNet 降冪 stable sort（同分照列序）；
    球員以先驗卡 name 對應；poss（playerId 對應）< 5000 或名字不在池內 → None。"""
    import csv as _csv
    import ovr_pipeline as OP
    rapm = {}
    for r in _csv.DictReader(open(rapm_path, encoding='utf-8')):
        rapm[r['name']] = r
    pool = [r for r in rapm.values() if float(r['pooledPoss']) >= OP.BONUS_MIN_POSS]
    net = {r['name']: i + 1 for i, r in enumerate(sorted(pool, key=lambda x: -float(x['pooledNet'])))}
    out = []
    for i, p in enumerate(pipe.pids):
        if pipe.poss[i] < OP.BONUS_MIN_POSS:
            out.append(None)
            continue
        k = net.get(pipe.name_by_pid[p])
        out.append(max(1, int(k)) if k is not None else None)
    return out
# ==== E-111 027 END ====


# ------------------------------------------------------------------ 環境設定
def setup():
    PA.install()
    m26_load_pool(POOL026)       # 合併池映射（E-107／E-111／E-128 機制）
    SA.zone_of = m26_zone_of
    IC.window_cards = m26_window_cards
    C.clip = m26_clip
    m27_install_zone_filter()    # 有 area 欄的季 area 缺值的 2pt 跳過；OVR 層防守加成換 UL 公式
    m27_install_ul({str(RAPM_STAR.resolve()): DEF_L_PRIMARY})
    # 0) card 0.1.2：先驗卡與凍結 OVR 管線係數（不重擬合）
    C.PRIOR_PATH[PRIOR] = PRIOR_CARD
    V2.FROZEN_SUMMARY = CARD_SUMMARY
    F.CACHE.clear()
    # 1) 2025-26 凍結映射（既有檔沒有涵蓋 2025-26）：用 build_season_cards 同一套流程重建
    sd25 = IC.load_target_season()                      # 2025-26 box / shots / teamRows
    bio25 = {int(r['PLAYER_ID']): r for r in SA.result_set(BIO25)}
    dep25 = {int(r['playerId']): r for s in load_json(IC.DEPENDENCE)['seasons']
             if s['season'] == PRIOR for r in s['rows']}
    box = {p: b for p, b in sd25['box'].items() if p in bio25}
    sdm = {'season': PRIOR, 'box': box, 'bio': bio25, 'dep': dep25, 'ff': {}, 'v3': {}, 'fed': {},
           'shots': sd25['shots'], 'teamRows': sd25['teamRows']}
    stats = SA.aggregate(sdm)
    raw = SA.raw_with_box(sdm, stats)
    mapping = SA.build_mapping(sdm, stats, raw)
    cards25 = {p: {'usg': SA._f(bio25[p]['USG_PCT'])} for p in stats}
    prev_sc, prev_scc = C.season_cards, C.season_cards_cards

    def season_cards(season):
        if season == PRIOR:
            return mapping['priors'], mapping['pools']
        return prev_sc(season)

    def season_cards_cards(season):
        if season == PRIOR:
            return cards25
        return prev_scc(season)

    C.season_cards, C.season_cards_cards = season_cards, season_cards_cards
    # 1b) prior-2025-26-v5.json 由正式卡轉成，sample 沒有 midA／shortA（全是 0）→ k_eff 取上界、
    #     近框／中距離等於凍結。歷年先驗卡（2021-25）都有這兩欄，這裡用同一份 2025-26 出手分區補上。
    prior_cards, _ = F.load_prior(PRIOR)
    filled = 0
    for pid, pc in prior_cards.items():
        s = stats.get(pid)
        if s is not None and pc.get('sample') is not None:
            pc['sample']['midA'], pc['sample']['shortA'] = float(s['midA']), float(s['shortA'])
            filled += 1

    info = {'boxPlayersDroppedNoBio': len(sd25['box']) - len(box), 'poolSize': len(mapping['pool']),
            'priors': mapping['priors'], 'mappingStats': stats, 'mapping': mapping,
            'priorShotSampleFilled': filled, 'priorCards': len(prior_cards)}

    # 2) 鏈：加上 S*
    chain = dict(PA.CHAIN_U)
    chain['S*'] = {'prior': PRIOR, 'target': TARGET, 'pred': '2022-23_2025-26', 'ans': None, 'judge': False}
    C.CHAIN = chain
    C.CHAIN_BY_PRIOR = {v['prior']: v['target'] for v in chain.values()}
    prev_hfa = C.history_for_attr

    def history_for_attr(s, a):
        if s != 'S*':
            return prev_hfa(s, a)
        hs = [h for h in PA.ORDER if h in PA.BUILT]            # Y1..Y6, D1..D3（Y0 無先驗卡）
        return [h for h in hs if not (h.startswith('Y') and a in C.W_MISSING)]

    C.history_for_attr = history_for_attr

    # 3) S* 的預測 RAPM：§R.2 四季合併欄
    prev_rp = C.rapm_path
    C.rapm_path = lambda name: RAPM_STAR if name == '2022-23_2025-26' else prev_rp(name)
    C._PIPE_CACHE.clear()
    PW._CACHE.clear()

    # 4) 例行賽場數與 2026-27 目標季資料
    PA.G_SEASON[TARGET] = G_GAMES
    old = (IC.TARGET_BOX, IC.TARGET_TEAM, IC.TARGET_PBP)
    IC.TARGET_BOX, IC.TARGET_TEAM, IC.TARGET_PBP = (DATA26 / 'player-games.json',
                                                    DATA26 / 'team-games.json', DATA26 / 'pbp')
    try:
        sd26 = IC.load_target_season()
    finally:
        IC.TARGET_BOX, IC.TARGET_TEAM, IC.TARGET_PBP = old
    sd26['season'] = TARGET
    C._CACHE[('target', TARGET)] = sd26
    return sd26, info


# ------------------------------------------------------------------ threeValue（R-024，顯示用；不進 OVR）
def _gamelog_sums(path):
    out = {}
    for r in SA.result_set(path):
        d = out.setdefault(int(r['PLAYER_ID']), [0.0, 0.0, 0.0])
        d[0] += float(r['MIN'] or 0)
        d[1] += float(r['FG3M'] or 0)
        d[2] += float(r['FG3A'] or 0)
    return out


def three_value_columns(prior_ids, extra_ids=()):
    """回傳 ({pid: dict}, info)。vol＝合併 3PA/MIN×36；acc＝k 收縮（上季 abilityC 當 k 個出手的先驗＋本季原始 3PM/3PA；
    本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%−0.03；value＝vol×(acc−rep)；池內（合併 MIN>=500 且有先驗卡）百分位→attr()。"""
    s25 = _gamelog_sums(IC.TARGET_BOX)          # 2025-26
    s26 = _gamelog_sums(DATA26 / 'player-games.json')
    m_all = sum(v[1] for d in (s25, s26) for v in d.values())
    a_all = sum(v[2] for d in (s25, s26) for v in d.values())
    mu = m_all / a_all
    rep = mu - THREE_REP_GAP
    # E-128 errata-4：027b 的 threeValue 照 027 現行算法（兩季即時池、abilityC 先驗；頂端尾巴見下方，2026-10-30 起不封 99）
    prior = {int(k): v['abilityC'] for k, v in load_json(THREE_PRIOR).items()}
    if WIN10:
        # E-185：vol／acc／value 改四季窗口（window10.tv_raw：n_w＝各季 abilityC×加權 3PA（沒有的季用原始 FG3M）、a_w、min_w；本季逐場 u 權重）。
        # mu 照上面合併兩季聯盟 3P%（不改）；池＝窗口 MIN>=500 且有先驗卡；尾巴規則同下方（top 開、錨點取即時池）。
        import numpy as np
        (tn, ta, tmn), tpidx, tv_fn = win8_load()['tv']
        tvol, tacc, tval = tv_fn(tn, ta, tmn, mu)
        prior = {pid: True for pid in tpidx}

    def pct(x, arr):
        return 100 * (sum(v < x for v in arr) + .5 * sum(v == x for v in arr)) / (len(arr) or 1)

    def attr(p):
        return max(40, min(99, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))

    cols = {}
    for pid in [*prior_ids, *extra_ids]:
        mn25, m25, a25 = s25.get(pid, (0.0, 0.0, 0.0))
        mn26, m26, a26 = s26.get(pid, (0.0, 0.0, 0.0))
        mn, a = mn25 + mn26, a25 + a26
        if WIN10:
            i = tpidx.get(pid)
            mn = float(tmn[i]) if i is not None else 0.0   # 窗口 MIN（加權）
            c = {'min26': mn26, 'fg3m26': m26, 'fg3a26': a26, 'minAll': mn, 'ok': i is not None and mn > 0 and not np.isnan(tval[i])}
            if c['ok']:
                c.update(acc=float(tacc[i]), vol=float(tvol[i]), value=float(tval[i]))
            cols[pid] = c
            continue
        c = {'min26': mn26, 'fg3m26': m26, 'fg3a26': a26, 'minAll': mn, 'ok': pid in prior and mn > 0}
        if c['ok']:
            acc = (THREE_K * prior[pid] + m26) / (THREE_K + a26)
            vol = a / mn * 36
            c.update(acc=acc, vol=vol, value=vol * (acc - rep))
        cols[pid] = c
    # extra_ids（名單上還沒出賽的人）只給值、不進池，已出賽者的百分位不受影響
    pool = [c['value'] for pid, c in cols.items() if pid in prior_ids and c['ok'] and c['minAll'] >= THREE_POOL_MIN]
    n_past = 0
    if WIN10 and TV_P1M:
        # E-191b P1m（0.2.10f）：池＝近三季各自「以該季結尾的窗口值」（窗口加權 MIN>=500）＋本季窗口值（上面那批），尺度和窗口值一致
        past = [v for d in win8_load()['tvpast'].values() for v in d.values()]
        pool, n_past = past + pool, len(past)
    # 2026-10-30 使用者「3PT 不要封 99」：027b 頂端改走 E-101 百分位尾巴（同卡片 threeValue：top 開、bot 關），
    # 錨點取本季即時池（m26_anchors），不用 pool-027b 的凍結錨點（那是 E-123 難度調整值，量尺不同）
    an = m26_anchors(pool) if pool else None

    def attr_open(x):
        p = pct(x, pool)
        if an is not None and p >= 99:
            return m26_top_tail(x - an['r99'], an['S'])
        return attr(p)

    for c in cols.values():
        c['threeValue'] = attr_open(c['value']) if c['ok'] else None
    info = {'mu': mu, 'rep': rep, 'k': THREE_K, 'poolMin': THREE_POOL_MIN, 'poolSize': len(pool),
            'leagueFG3M': m_all, 'leagueFG3A': a_all, 'topTail': an}
    if WIN10 and TV_P1M:
        info['poolPast'] = n_past   # 池裡來自前三季的人數（其餘為本季）
    return cols, info


# ------------------------------------------------------------------ foulDraw（E-070 公式，CARD_MODE=022）
_FD = {}


def foul_draw_y(rec):
    """視窗觀測值：percentile_pool(0.75·z(FTA/36)+0.25·z(FTA/FGA))→attr()。常數取自 prior JSON 的 foulDrawFreeze
    （2025-26 池；card 0.2.2 建 foulDraw 時的 z 平均／標準差與池內合成值），不用 2026-27 資料重估。"""
    if not _FD:
        fz = load_json(PRIOR_CARD)['foulDrawFreeze']
        _FD.update(fz)
        _FD['ref'] = sorted(fz['poolComposite'])
    fz, smp = _FD, rec['sample']
    fta, fga, mn = float(smp['fta']), float(smp['fga']), float(smp['min'])
    z_vol = (fta / mn * 36.0 - fz['vol']['mean']) / fz['vol']['std']
    z_rate = (fta / fga - fz['rate']['mean']) / fz['rate']['std']
    comp = fz['wVol'] * z_vol + fz['wRate'] * z_rate
    ref = fz['ref']
    p = 100 * (sum(v < comp for v in ref) + .5 * sum(v == comp for v in ref)) / len(ref)
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


# ------------------------------------------------------------------ inseason 0.2.10：8 項屬性改 E-175 U 窗口（window8.py）
WIN8_ATTRS = ('drive', 'foulDraw', 'ft', 'mid', 'pass', 'rebound', 'short', 'tovSkill')
WIN8 = {}   # {'now': {pid: {8 項}}, 'day0': {pid: {8 項}}, 'games': 已賽場數, 'pbp': pbp 場數}


def _usage_window(W, f):
    """window11.usage_at 的輸出 -> {pid: {'L','a','y','v','has'}}（卡片名單內每人；L 在 has=False 時是 NaN，apply_usage 不會讀）。"""
    out = {}
    for p in W.D.pids:
        i = W.D.pidx[p]
        _, y, v = W.age_flags(int(p))
        out[int(p)] = {'L': float(f['L'][i]), 'a': float(f['a'][i]), 'y': y, 'v': v, 'has': bool(f['has'][i])}
    return out


def usage_features(frozen, win):
    """卡片用人名單（usage 檔）內的人，L、a、y、v、has 換成窗口值；d 沿用 usage 檔（b8＝0，不進模型）。沒有窗口資料的人（不在 D.pids）維持凍結值。
    win 為 None（USAGE_WIN=0）時原樣回傳。"""
    if win is None:
        return frozen
    return {pid: ({**u, **win[pid]} if pid in win else u) for pid, u in frozen.items()}


def win8_load():
    """四季滑動窗口（過去季權重 window_w(c)＋本季逐場 u 權重）算 8 項屬性；day0＝本季 0 場。載入一次。"""
    if WIN8:
        return WIN8
    saved = list(sys.path)
    try:
        import window8 as W8
        if WIN10:
            import window10 as W10
            if USAGE_WIN:
                import window11 as W11
                W = W11.Win11(DATA26)
            else:
                W = W10.Win10(DATA26)
        else:
            W = W8.Win8(DATA26)   # ovr_history 逐日重算會換掉 ns['DATA26']；窗口也要只讀截斷資料夾（不然 8 項用到未來資料）
        tabs, gd = W.cur_tabs()
        WIN8.update(now=W.attrs_at(gd, tabs), day0=W.day0(tabs), games=gd, pbp=W.n_pbp, attrs=list(W8.C.ATTRS8))
        if WIN10:
            Ls = MPG_L
            WIN8.update(mpg=W.mpg_at(gd, tabs, nseas=Ls), mpg_day0=W.mpg_at(0, tabs, nseas=Ls), mpgL=Ls,
                        tv=(W.tv_raw(gd, tabs), W.D.pidx, W10.Win10.tv_value), tvL=4)
            if TV_P1M:
                WIN8['tvpast'] = W.tv_past_pool(TARGET)
            assert W10.SD.ON == SPLIT_DC, 'SPLIT_DC 與 split_dc.ON 不一致'
            if SPLIT_DC:   # 0.2.10i：新秀 creationJ 用（split_creation）
                WIN8.update(crJ=W.crj_cur, creationMap=W.creation_map)
            if USAGE_WIN:   # 0.2.10g：用人層 L、a（四季窗口，今天與本季 0 場）＋ y、v（當下年齡）
                WIN8['usage'] = _usage_window(W, W.usage_at(gd, tabs))
                WIN8['usage_day0'] = _usage_window(W, W.usage_at(0, tabs))
                WIN8['ageFlags'] = W.age_flags
                if AGE_START and W.age_start:
                    WIN8['ageStart'] = W.age_summary()   # 0.2.10h：y、v 用開季當天年齡；沒有 DOB 的人退回 bio 年齡
    finally:
        sys.path[:] = saved
    print(f'{VERSION} 窗口：本季 {gd} 場（pbp {WIN8["pbp"]} 場），8 項 {len(WIN8["now"])} 人', file=sys.stderr)
    return WIN8


def win8_override(attrs):
    """把 8 項屬性換成窗口值（沒有窗口資料的人維持先驗＝card 0.2.10 季末值）。可重複呼叫（冪等）。"""
    now = win8_load()['now']
    n = 0
    for pid, x in attrs.items():
        v = now.get(int(pid))
        if v:
            x.update(v)
            n += 1
    return n


# ------------------------------------------------------------------ C4（逐球員 N）
def live_predict(delta2, rel, undefined=(), frozen=(), f_force=None, k_max=False, diag=None):
    prior_cards, _ = F.load_prior(PRIOR)
    _, attrs0 = C.deployment('S*')
    w, _ = F.windows_of(PRIOR, ALL_N)
    usg = C.usg_prior(PRIOR)
    out = {}
    for pid, x0 in attrs0.items():
        rec = w.get(pid)
        pc = prior_cards.get(pid)
        n_games = rec['GP'] if rec else 0
        f = f_force if f_force is not None else min(n_games / G_GAMES, 1.0)
        vals = {}
        for a in C.UPD:
            if pc is None or a in undefined or a in frozen:
                vals[a] = x0[a]
                continue
            if rec is None or IC.sample_of(rec, a) < SA.SEASON_MIN_SAMPLE[a]:
                vals[a] = x0[a]
                continue
            y = F.y_adj_of(pc, rec, a, usg.get(pid, 0.0))
            n = IC.sample_of(rec, a)
            if k_max:
                k = 50.0 * rel[a]['nRef']
            else:
                k = C_PARAM * V2.k_eff(delta2[a], rel[a]['sigma2'], V2.sample_n(pc, a), rel[a]['nRef'])
            b = n / (n + k)
            wt = f + (1.0 - f) * b
            vals[a] = C.clip(x0[a] + wt * (y - x0[a]))
            if diag is not None:
                diag.append({'pid': pid, 'attr': a, 'x0': x0[a], 'y': y, 'n': n, 'k': k, 'b': b,
                             'f': f, 'w': wt, 'xhat': vals[a]})
        # foulDraw（card 0.1.2 新欄）：觀測值已由 m26_window_cards 用 pool-027b 合併池＋尾巴算好。
        # 樣本／最小樣本／δ²／rel 沿用 drive 的；不重估。drive 本身（0.1.2 改 PBP 版）凍結。
        a = 'foulDraw'
        vals[a] = x0[a]
        if not (pc is None or 'drive' in undefined or a in frozen or rec is None
                or IC.sample_of(rec, 'drive') < SA.SEASON_MIN_SAMPLE['drive']):
            y = C.usage_adjust({a: x0[a]}, rec, a, usg.get(pid, 0.0))
            n = IC.sample_of(rec, 'drive')
            if k_max:
                k = 50.0 * rel['drive']['nRef']
            else:
                k = C_PARAM * V2.k_eff(delta2['drive'], rel['drive']['sigma2'], V2.sample_n(pc, 'drive'),
                                       rel['drive']['nRef'])
            b = n / (n + k)
            wt = f + (1.0 - f) * b
            vals[a] = C.clip(x0[a] + wt * (y - x0[a]))
            if diag is not None:
                diag.append({'pid': pid, 'attr': a, 'x0': x0[a], 'y': y, 'n': n, 'k': k, 'b': b,
                             'f': f, 'w': wt, 'xhat': vals[a]})
        out[pid] = {**x0, **vals}
    return out


# ------------------------------------------------------------------ 小工具
def git_head():
    r = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                       creationflags=NO_WINDOW)
    return r.stdout.strip()


def rel(p):
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(p).resolve().as_posix()


def e064_anchors():
    """回傳 (錨點 [PR1, PR50, PR99, PR90, PR95], r_repl)：usage 檔的 anchors／rRepl（load_usage 已核對它用的是現行 ranking.csv）；沒有 PR90／PR95 時為 None。"""
    d = load_json(USAGE_FILE)
    a = d['anchors']
    return [a['PR1'], a['PR50'], a['PR99'], a.get('PR90'), a.get('PR95')], d['rRepl']


def e064_map(g, anc):
    """E-188 S3（R-124）：PR50→70、PR90→88、PR95→92、PR99→99 分段線性；≤PR50、≥PR99 同舊兩段式；沒有 PR90／PR95 退回舊兩段式。
    同 reports/card-0.2.10a+E188-ovr-top-scale/ovr_map.py。"""
    p1, p50, p99 = anc[:3]
    if g <= p50:
        return 40 + 30 * (g - p1) / (p50 - p1)
    if g >= p99 or len(anc) < 5 or anc[3] is None:
        return 70 + 29 * (g - p50) / (p99 - p50)
    for x0, x1, y0, y1 in ((p50, anc[3], 70.0, 88.0), (anc[3], anc[4], 88.0, 92.0), (anc[4], p99, 92.0, 99.0)):
        if g <= x1:
            return y0 + (y1 - y0) * (g - x0) / (x1 - x0)


def load_usage():
    """E-091：讀 usage-2025-26-card024.json，核對 payload sha256、card 0.2.4 ranking.csv sha256、r_repl／錨點。回傳 (usage {pid: 特徵}, coef, payloadSha256)。"""
    import hashlib
    doc = load_json(USAGE_FILE)
    body = json.dumps({'coef': doc['coef'], 'rRepl': doc['rRepl'], 'anchors': doc['anchors'], 'players': doc['players']},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if hashlib.sha256(body.encode('utf-8')).hexdigest() != doc['payloadSha256']:
        raise SystemExit('usage-2025-26-card024.json payload sha256 不符')
    summ = load_json(CARD024_SUMMARY)
    if hashlib.sha256(FORMAL_RANKING.read_bytes()).hexdigest() != summ['ranking_csv_sha256']:
        raise SystemExit(f'{CARD_VERSION} ranking.csv sha256 與 summary.json 不符')
    # 0.2.7d 起沒另存錨點：build_usage 已逐人核對 582 人 OVR；這裡核對它用的是同一張卡
    # 0.2.12b（R-140，E-204）：窗口縮短不重取係數、r_repl、錨點，usage 檔仍是用 card 0.2.12（card-0.2.12-tov）建的
    usrc, usumm = _OV, summ
    if CARD_VERSION == 'card 0.2.12c':      # 0.2.12c：同上，usage 檔是用 W246 底（card-0.2.12c-w246）建的
        usrc = 'card-0.2.12c-w246'
        usumm = load_json(ROOT / 'reports/card-0.2.12c-w246/summary.json')
    if CARD_VERSION == 'card 0.2.12b':
        usrc = 'card-0.2.12-tov'
        usumm = load_json(ROOT / 'reports/card-0.2.12-tov/summary.json')
    if doc['sourceSha256'][usrc + ' ranking.csv'] != usumm['ranking_csv_sha256']:
        raise SystemExit(f'usage 檔不是用現行 {usrc} ranking.csv 建的')
    return {int(k): v for k, v in doc['players'].items()}, doc['coef'], doc['payloadSha256']


def apply_usage(entries, usage, coef):
    """E-091：predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（用人特徵凍結 2025-26，p＝賽中 C4 的 pred）；
    沒有凍結特徵（has=False 或不在 card 0.2.4）→ predNew = p。原 p 留在 predP，pred 換成 predNew 給 e064_convert。"""
    out = {}
    for pid, e in entries.items():
        if not isinstance(e, dict):      # ref 帶 '_capIterations'
            out[pid] = e
            continue
        u = usage.get(pid)
        if u is None or not u['has']:
            pn = e['pred']
        else:
            L, a, y, v, d = u['L'], u['a'], u['y'], u['v'], u['d']
            pn = (coef['b0'] + coef['b1_p'] * e['pred'] + coef['b2_L'] * L + coef['b3_a'] * a + coef['b4_y'] * y
                  + coef['b5_v'] * v + coef['b6_yL'] * y * L + coef['b7_vL'] * v * L + coef['b8_ydL'] * y * d * L)
            pn = e['pred'] + u.get('ramp', 1.0) * (pn - e['pred'])   # 復出老將 RV_USAGE=lo：同新秀 × min(N/10, 1)
        out[pid] = {**e, 'predP': e['pred'], 'pred': pn}
    return out


def team_badness(team_rows):
    """爛隊程度 d（R-097／R-098，同 run_c4_live_rookie.py:team_badness、卡 E-147）。{TEAM_ID: d}。
    nr＝累計得失分差／(GP+10)、wp＝(W+5)／(GP+10)、s＝0.7·(0.5+0.033·nr)+0.3·wp、d＝clip((0.40−s)/0.10, 0, 1)。"""
    acc = {}
    for r in team_rows:
        a = acc.setdefault(r['TEAM_ID'], [0, 0, 0.0])
        a[0] += 1
        a[1] += r['WL'] == 'W'
        a[2] += float(r['PLUS_MINUS'])
    out = {}
    for t, (gp, w, pm) in acc.items():
        s = 0.7 * (0.5 + 0.033 * pm / (gp + 10)) + 0.3 * (w + 5) / (gp + 10)
        out[t] = min(1.0, max(0.0, (0.40 - s) / 0.10))
    return out


def live_usage(usage, sd26):
    """R-098（2026-10-31 使用者「AB先上線」）：本季出賽過的人 d 換成最近一場所屬球隊的 team_badness；沒出賽的人照卡（N=0 → OVR＝先驗）。"""
    bad = team_badness(sd26['teamRows'])
    out = dict(usage)
    for pid, b in sd26['box'].items():
        u = usage.get(pid)
        if u is None or not b['rows']:
            continue
        t = max(b['rows'], key=lambda r: r['GAME_DATE'])['TEAM_ID']
        if t in bad:
            out[pid] = {**u, 'd': bad[t], 'dCard': u['d']}
    return out


RV_USAGE = os.environ.get('RV_USAGE', 'hi')   # 復出老將用人層（2026-11-04 使用者）：hi＝個人場次窗口含舊季、lo＝同新秀只看本季、0＝不套（重現 0.2.12d）


def rv_usage(usage_now, usage_d0, mpg_hat, sd26):
    """復出老將（不在 usage 檔，原本 predNew＝p）補進用人層。a＝1、d＝0（b8＝0）、y／v＝開季年齡。
    hi：MPG＝個人場次軸（R-163）加權，本季場次由新到舊、接舊季 rvGp 場（每場 rvMpg），u＝(WIN−r−0.5)/WIN；基準＝舊季 rvMpg；MPG_hat 同步換成這個值。
    lo：同新秀，L＝log1p(本季 MPG)、× min(N/10, 1)；基準不套（N＝0）。"""
    import win_len
    age = win8_load()['ageFlags']
    n = 0
    for c in json.load(open(PRIOR_CARD, encoding='utf-8'))['players']:
        pid = c['playerId']
        if c.get('rvMpg') is None or pid in usage_now:
            continue
        _, y, v = age(pid)
        cur = [float(r['MIN']) for r in sorted((sd26['box'].get(pid) or {}).get('rows', []), key=lambda r: r['GAME_DATE'], reverse=True)
               if float(r['MIN']) > 0]
        base = {'has': True, 'a': 1.0, 'y': y, 'v': v, 'd': 0.0}
        if RV_USAGE == 'lo':
            if cur:
                usage_now[pid] = {**base, 'L': math.log1p(sum(cur) / len(cur)), 'ramp': min(len(cur) / USAGE_N_RV, 1.0)}
        else:
            mins = cur + [c['rvMpg']] * int(c['sample']['gp'])
            u = [max((win_len.WIN_LEN - r - 0.5) / win_len.WIN_LEN, 0.0) for r in range(len(mins))]
            m = sum(a * b for a, b in zip(u, mins)) / sum(u)
            usage_now[pid] = {**base, 'L': math.log1p(m)}
            usage_d0[pid] = {**base, 'L': math.log1p(c['rvMpg'])}
            mpg_hat[pid] = m
        n += 1
    print(f'復出老將用人層 RV_USAGE={RV_USAGE}：{n} 人', file=sys.stderr)


USAGE_N_RV = 10   # 同 run_c4_live_rookie.USAGE_N


def e064_convert(entries, mpg_by_pid, anc, r_repl=0.0):
    """entries＝{pid: pw.predict 輸出}；回傳同結構但 ovr 改為每場 OVR（ovrPer36 保留原值）。
    g = (pred − r_repl)·W(MPG)（飽和分鐘權重，card 0.2.5 起）。"""
    out = {}
    for pid, e in entries.items():
        if not isinstance(e, dict):      # ref 帶 '_capIterations'
            out[pid] = e
            continue
        g = (e['pred'] - r_repl) * sat_w(mpg_by_pid.get(pid, 0.0))
        out[pid] = {**e, 'ovrPer36': e['ovr'], 'g': g, 'ovr': e064_map(g, anc)}
    return out


def load_roster():
    """data/.../roster.json（commonallplayers 本季現役）→ {pid: 隊}；檔案不在就回空（退回只列已出賽）。"""
    path = DATA26 / 'roster.json'
    if not path.exists():
        print('沒有 roster.json：還沒出賽的球員不列入', file=sys.stderr)
        return {}
    return {int(r['PERSON_ID']): r['TEAM_ABBREVIATION'] for r in SA.result_set(path) if r['TEAM_ABBREVIATION']}


def latest_team(path):
    out = {}
    for r in sorted(SA.result_set(path), key=lambda r: (r['GAME_DATE'], r['GAME_ID'])):
        out[int(r['PLAYER_ID'])] = r['TEAM_ABBREVIATION']
    return out


def r1(v):
    return round(float(v), 1)


def med(xs):
    return statistics.median(xs) if xs else None


def md_table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' for _ in head) + '|']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


# ------------------------------------------------------------------ 主流程
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sd26, mp = setup()
    cutoff = max(r['GAME_DATE'] for b in sd26['box'].values() for r in b['rows'])
    out_dir = HERE / (sys.argv[1] if len(sys.argv) > 1 else cutoff)
    out_dir.mkdir(parents=True, exist_ok=True)

    rel_ = V2.load_reliability()
    delta2, undefined, d_info = C4.delta2_info('S*')
    frozen = ['pressure', 'drive'] + [a for a in WIN8_ATTRS if a != 'drive'] + (['long', 'creation'] if WIN10 else [])   # 0.2.10：8 項改窗口（win8_override），C4 不再碰；pressure 凍結（UNFREEZE_PD 另算）
    prior_cards, prior_doc = F.load_prior(PRIOR)
    _, attrs0 = C.deployment('S*')
    pw = PW.for_start(C, 'S*')
    ref = pw.ref
    w26, _ = F.windows_of(PRIOR, ALL_N)

    diag = []
    attrs = live_predict(delta2, rel_, undefined, frozen, diag=diag)
    n_win8 = win8_override(attrs)
    res = pw.predict(attrs)
    usage, ucoef, usage_sha, mpg_card = {}, None, None, {}
    mpg_hat, mpg_win, w_mpg, mpg_nodata = {}, {}, {}, []
    # MPG0＝先驗卡那一季的 MIN／GP；ref（lastOVR 基準）一律用 MPG0 換成每場
    mpg0 = {pid: (float(c['observed']['MIN']) / float(c['observed']['GP']) if float(c['observed']['GP']) > 0 else 0.0)
            for pid, c in prior_cards.items()}
    anc064, r_repl064 = e064_anchors()
    # E-091：MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對）；卡裡沒有的人維持上面的舊規則（MIN／GP）
    usage, ucoef, usage_sha = load_usage()
    for r_ in C.load_csv(FORMAL_RANKING):
        mpg_card.setdefault(r_['name'], float(r_['mpg']))
    # E-095：card 0.2.5 的 mpg 欄必須與 card 0.2.4 相同（預註冊 §2）
    m24 = {}
    for r_ in C.load_csv(CARD024_RANKING):
        m24.setdefault(r_['name'], float(r_['mpg']))
    if not WIN10 and m24 != mpg_card:   # 0.2.10d 起 ranking 的 mpg 欄＝窗口 MPG（E-185），不再等於 card 0.2.4
        raise SystemExit(f'{CARD_VERSION} ranking 的 mpg 欄與 card 0.2.4 不同')
    for pid, c in prior_cards.items():
        if c['name'] in mpg_card:
            mpg0[pid] = mpg_card[c['name']]
    if RETURNING_VETS:              # 復出老將：observed.MIN＝0（不進百分位池），MPG0 改用舊季真實 MPG，不然 lastOVR 基準（MPG 窗口 L=1 蓋不到舊季）＝0 分鐘
        for c in json.load(open(PRIOR_CARD, encoding='utf-8'))['players']:
            if c.get('rvMpg') is not None:
                mpg0[c['playerId']] = c['rvMpg']
    mpg_hat = dict(mpg0)            # G0：MPG_hat＝MPG0（不更新）
    # 預註冊 §4.1：MPG_hat = MPG0 + w·(MPG_win − MPG0)；w＝stamina 的 C4 w（f＋(1−f)·n/(n+c·k_eff)）。
    # 沒有 2026-27 視窗紀錄、沒有 stamina 的 w（無先驗卡等）→ 退回 MPG0（backtest_e064.mpg_hat 同款）。
    w_mpg = {d['pid']: d['w'] for d in diag if d['attr'] == 'stamina'}
    mpg_ref = mpg0
    if WIN10:
        # E-185：MPG_hat＝窗口 MPG（Σu·MIN／Σu·GP，L 季線性遞減；window10.mpg_at）；窗口內沒出賽者退回 MPG0（＝卡的 mpg 欄）。
        wm = win8_load()
        mpg_ref = dict(mpg0)    # lastOVR 基準：同模型、本季 0 場＝窗口 day0 的 MPG
        for pid in attrs0:
            rec = w26.get(pid)
            m0 = mpg0.get(pid, 0.0)
            if rec is not None and rec['GP'] > 0:
                mpg_win[pid] = rec['MIN'] / rec['GP']
            if pid in wm['mpg']:
                mpg_hat[pid] = wm['mpg'][pid]
            else:
                mpg_hat[pid] = m0
                mpg_nodata.append(pid)
            if pid in wm['mpg_day0']:
                mpg_ref[pid] = wm['mpg_day0'][pid]
    else:
      for pid in attrs0:
        rec = w26.get(pid)
        m0 = mpg0.get(pid, 0.0)
        if pid in w_mpg and rec is not None and rec['GP'] > 0:
            mpg_win[pid] = rec['MIN'] / rec['GP']
            mpg_hat[pid] = m0 + w_mpg[pid] * (mpg_win[pid] - m0)
        else:
            mpg_hat[pid] = m0
            mpg_nodata.append(pid)
    # 0.2.10g：res 用今天的窗口用人特徵；ref（lastOVR 基準）與 o1 用本季 0 場（day0）窗口；USAGE_WIN=0 兩者都是凍結值（= 0.2.10f）
    usage_now = usage_features(usage, win8_load()['usage'] if USAGE_WIN else None)
    usage_d0 = usage_features(usage, win8_load()['usage_day0'] if USAGE_WIN else None)
    if RETURNING_VETS and USAGE_WIN and RV_USAGE != '0':
        usage_now, usage_d0 = dict(usage_now), dict(usage_d0)
        rv_usage(usage_now, usage_d0, mpg_hat, sd26)
    res = apply_usage(res, live_usage(usage_now, sd26), ucoef)   # R-098：d 用當下球隊；ref／o1 仍用卡的 d
    ref = apply_usage(ref, usage_d0, ucoef)
    res = e064_convert(res, mpg_hat, anc064, r_repl064)
    ref = e064_convert(ref, mpg0, anc064, r_repl064)

    # ---- 檢查 (a)：f=0、k 取上界 → 與上季卡逐球員 OVR 差 <0.5（c4_v5 T1）
    a1 = live_predict(delta2, rel_, undefined, frozen, f_force=0.0, k_max=True)
    o1 = pw.predict(a1)
    o1 = apply_usage(o1, usage_d0, ucoef)
    o1 = e064_convert(o1, mpg0, anc064, r_repl064)
    t1 = max(abs(o1[p]['ovr'] - ref[p]['ovr']) for p in attrs0)
    a1_ref = C4.c4_predict('S*', ALL_N, delta2, rel_, 1.0, undefined, frozen, f_force=0.0, k_max=True)
    upd_cmp = list(C.UPD)
    t1_same = max(abs(a1[p][a] - a1_ref[p][a]) for p in attrs0 for a in upd_cmp)
    a2 = live_predict(delta2, rel_, undefined, frozen, f_force=0.0)
    r2 = F.c2_predict('S*', ALL_N, delta2, rel_, undefined=undefined, frozen=frozen)
    t2 = max(abs(a2[p][a] - r2[p][a]) for p in attrs0 for a in upd_cmp)

    # ---- 映射重建是否與上季卡一致（只看僅由 box 決定的 long / ft）
    from ovr_common import CURVES, shooting
    st = mp['mappingStats']
    dl, df = [], []
    for pid, pc in prior_cards.items():
        s = st.get(pid)
        if not s or s['FG3A'] < 1:
            continue
        dl.append(abs(shooting(s['FG3M'], s['FG3A'], mp['priors']['long'], CURVES['CURVE_3PT']) - float(pc['long'])))
        if s['FTA'] >= 1:
            df.append(abs(shooting(s['FTM'], s['FTA'], mp['priors']['ft'], CURVES['CURVE_FT']) - float(pc['ft'])))

    # ---- 排名
    team = latest_team(DATA26 / 'player-games.json')
    roster = load_roster()
    team.update(roster)     # 現役名單優先（交易後還沒出賽也對）
    formal_rows = C.load_csv(FORMAL_RANKING)
    formal = {}
    for r in formal_rows:
        formal.setdefault(r['name'], float(r['ovr']))
    # 有先驗卡、在現役名單上但還沒出賽（傷兵等）：N=0，OVR＝先驗（f=0、無視窗資料）
    unplayed = [pid for pid in prior_cards if pid not in sd26['box'] and pid in roster and pid in res]
    tv_cols, tv_info = three_value_columns([pid for pid in sd26['box'] if prior_cards.get(pid) is not None], unplayed)
    rows, nopr = [], []
    boxes = list(sd26['box'].items()) + [(pid, {'name': prior_cards[pid]['name'], 'rows': []}) for pid in unplayed]
    for pid, b in boxes:
        pc = prior_cards.get(pid)
        gp = len(b['rows'])
        mins = sum(r['MIN'] for r in b['rows'])
        if pc is None:
            nopr.append({'playerId': pid, 'name': b['name'], 'team': team.get(pid, ''), 'N': gp,
                         'MIN26': round(mins, 1)})
            continue
        p = res[pid]
        row = {'ovr': r1(p['ovr']), 'name': pc['name'], 'pos': pc['pos'],
               'MIN': round(float(pc['observed']['MIN'])), 'predictedPer36': round(p.get('predP', p['pred']), 3),
               'simulatedPer36': '', 'defenseBonus': round(p['bonus'], 3), 'align': round(p['align'], 3),
               'pred0': round(p['pred0'], 3), 'pr': round(p['pr'], 2)}
        for a in ATTRS:
            row[a] = r1(attrs[pid][a])
        row.update({'MPG0': round(mpg0.get(pid, 0.0), 2), 'MPGhat': round(mpg_hat.get(pid, 0.0), 2),
                    'g': round(p['g'], 3), 'ovrPer36': r1(p['ovrPer36'])})
        row.update({'MPGwin': round(mpg_win[pid], 2) if pid in mpg_win else '',
                    'wMPG': round(w_mpg[pid], 4) if pid in w_mpg else ''})
        row['predNew'] = round(p['pred'], 4)     # E-091：用人回歸後的每 36 預測（predictedPer36 仍是屬性迴歸 p）
        if pc is not None:      # 顯示用（2025-26 先驗卡的值，賽中不更新；不進 OVR）；run_c4_live_rookie.py 以下一行的原文替換，勿改縮排／字面
            row.update({'presDisplay': pc.get('presDisplay', ''), 'foulDisc': pc.get('foulDisc', '')})
        row.update({'playerId': pid, 'N': gp, 'team': team.get(pid, ''), 'MIN26': round(mins, 1),
                    'lastOVR': r1(ref[pid]['ovr']), 'dOVR': round(p['ovr'] - ref[pid]['ovr'], 2),
                    'formalOVR': formal.get(pc['name'], ''),
                    'threeValue': '' if tv_cols[pid]['threeValue'] is None else r1(tv_cols[pid]['threeValue']),
                    'fg3a26': int(tv_cols[pid]['fg3a26']), 'fg3m26': int(tv_cols[pid]['fg3m26']),
                    'fg3Pct26': round(tv_cols[pid]['fg3m26'] / tv_cols[pid]['fg3a26'], 4) if tv_cols[pid]['fg3a26'] else '',
                    '_ovr': p['ovr'], '_d': p['ovr'] - ref[pid]['ovr'],
                    '_lastCmp': r1(ref[pid]['ovr'])})
        rows.append(row)
    rows.sort(key=lambda r: -r['_ovr'])
    for i, r in enumerate(rows, 1):
        r['rank'] = i
    head = (['rank', 'ovr', 'name', 'pos', 'MIN', 'predictedPer36', 'simulatedPer36', 'defenseBonus', 'align',
             'pred0', 'pr'] + list(ATTRS) + ['playerId', 'N', 'team', 'MIN26', 'lastOVR', 'dOVR', 'formalOVR',
             'threeValue', 'fg3a26', 'fg3m26', 'fg3Pct26'])
    head = head + ['MPG0', 'MPGhat', 'g', 'ovrPer36', 'MPGwin', 'wMPG', 'presDisplay', 'foulDisc', 'predNew']
    C.write_csv(out_dir / 'ranking.csv', [{k: r[k] for k in head} for r in rows], head)
    nopr.sort(key=lambda r: (-r['N'], -r['MIN26']))
    C.write_csv(out_dir / 'no-prior.csv', nopr, ['playerId', 'name', 'team', 'N', 'MIN26'])

    # ---- 檢查 (b)：|ΔOVR|
    ds = [r['_d'] for r in rows]
    ad = [abs(d) for d in ds]
    by_n = {}
    for r in rows:
        by_n.setdefault(r['N'], []).append(abs(r['_d']))
    ordered = sorted(rows, key=lambda r: r['_d'])
    movers = sorted(rows, key=lambda r: -abs(r['_d']))[:10]
    pid_name = {r['playerId']: r['name'] for r in rows}
    changed_attrs = {}
    for d in diag:
        if abs(d['xhat'] - d['x0']) > 1e-9:
            changed_attrs.setdefault(d['attr'], 0)
            changed_attrs[d['attr']] += 1
    big = [r for r in rows if abs(r['_d']) >= 1.0]
    prior_game_pids = {r['playerId'] for r in rows}
    not_played = [p for p in prior_cards if p not in prior_game_pids]   # 不在現役名單上（離隊、退休等）
    formal_diff = [abs(r['_lastCmp'] - r['formalOVR']) for r in rows if r['formalOVR'] != '']
    n_dist = {}
    for r in rows:
        n_dist[r['N']] = n_dist.get(r['N'], 0) + 1

    sanity = {
        'a_f0_kmax_maxAbsOvrDiff': t1, 'a_liveEqualsC4predict_maxAttrDiff': t1_same,
        'a_f0_equalsC2_maxAttrDiff': t2,
        'b_n': len(rows), 'b_median_abs': med(ad), 'b_max_abs': max(ad), 'b_mean_abs': statistics.mean(ad),
        'b_by_N': {n: {'players': len(v), 'median': med(v), 'max': max(v)} for n, v in sorted(by_n.items())},
        'b_ge_1': [(r['name'], r['N'], round(r['_d'], 3)) for r in big],
        'mapping_long_maxAbsDiff': max(dl), 'mapping_ft_maxAbsDiff': max(df),
        'pointwiseCheck': pw.check, 'lastOVR_vs_formal_maxAbs': max(formal_diff) if formal_diff else None,
        'lastOVR_vs_formal_matched': len(formal_diff),
    }

    # E-107／E-111／E-128：(L1) 卡內每人 ref OVR 對 card ranking 的 ovr；範圍檢查；UL 防守加成對 card 的 defenseBonus
    l1 = {prior_cards[p]['name']: ref[p]['ovr'] - formal[prior_cards[p]['name']] for p in attrs0
          if prior_cards[p]['name'] in formal}
    upd = [a for a in M26['attrs'] if a in C.UPD or a == 'foulDraw']
    out_of_range = [(prior_cards[p]['name'], a, attrs[p][a]) for p in attrs for a in upd
                    if not (m26_range(a)[0] - 1e-9 <= attrs[p][a] <= m26_range(a)[1] + 1e-9)]
    m26_info = {'pool027b': {'file': rel(POOL026), 'payloadSha256': M26['payloadSha256']},
                'L1_refVsCard027b': {
                    'n': len(l1), 'maxAbs': max(abs(v) for v in l1.values()),
                    'worst': sorted(l1.items(), key=lambda kv: -abs(kv[1]))[:5]},
                'rangeCheck': {'attrs': upd, 'outOfRange': out_of_range[:20], 'nOutOfRange': len(out_of_range)},
                'above99': sorted([(prior_cards[p]['name'], a, round(attrs[p][a], 2)) for p in attrs for a in upd
                                   if attrs[p][a] > 99 and p in w26], key=lambda t: -t[2])}
    pipe = pw.pipe
    ub = dict(zip(pipe.pids, m27_bonus_of(pipe)))
    fb = {r_['name']: float(r_['defenseBonus']) for r_ in formal_rows}
    dbon = [abs(round(ub[p], 3) - fb[prior_cards[p]['name']]) for p in pipe.pids if prior_cards[p]['name'] in fb]
    m26_info['ulBonus'] = {'defL': rel(DEF_L_PRIMARY), 'posMeanD': {k: float(v) for k, v in pipe._m27_posMeanD.items()},
                           'vsCard027DefenseBonus3dp': {'n': len(dbon), 'maxAbs': float(max(dbon)),
                                                        'nMismatch': int(sum(bool(d > 1e-9) for d in dbon))},
                           'refBonusEqualsUl': float(max(abs(ref[p]['bonus'] - ub[p]) for p in pipe.pids))}
    m26_info['zoneSkippedAreaMissing2pt'] = dict(M27_ZONE_DROPPED)
    m26_info['stamina'] = 'IC 單季映射（E-111 §1.3，不進合併池、不加尾巴）'

    # ---- meta.json
    inputs = {
        '2026-27 player-games': DATA26 / 'player-games.json', '2026-27 team-games': DATA26 / 'team-games.json',
        '2026-27 bio': DATA26 / 'bio.json', 'prior card': PRIOR_CARD, 'S* RAPM': RAPM_STAR,
        '2025-26 player-games': IC.TARGET_BOX, '2025-26 team-games': IC.TARGET_TEAM,
        '2025-26 bio': BIO25, 'threeValue prior (abilityC)': THREE_PRIOR, 'dependence-audit': IC.DEPENDENCE, 'formal ranking (cross-check)': FORMAL_RANKING,
        'usage features (E-091)': USAGE_FILE, 'e084 results (coef/r_repl/anchors)': USAGE_FILE, (CARD_VERSION + ' summary'): CARD024_SUMMARY,
        'pool-027b (E-128)': POOL026, 'window8.py': HERE / 'window8.py', 'card-0.2.10 frozen.json': ROOT / 'reports/card-0.2.10/frozen.json',
        'card-0.2.10 tail-U.csv': ROOT / 'reports/card-0.2.10/tail-U.csv', '2026-27 pbp (window8) first file': next(iter(sorted((DATA26 / 'pbp').glob('*.json'))), None),
        (CARD_VERSION + ' OVR summary'): CARD_SUMMARY, 'def-L primary (UL bonus)': DEF_L_PRIMARY,
        'rebase-027a cards-result.json (anchors)': E128_RB / 'work/cards-result.json',
        'reliability': V2.RELIABILITY if hasattr(V2, 'RELIABILITY') else None,
    }
    if WIN10:
        inputs.update({'window10.py': HERE / 'window10.py', 'MPG window L selection (2024-25 only)': MPG_L_FILE,
                       'card-0.2.12 tail-U.csv': ROOT / 'reports/card-0.2.12/tail-U.csv',
                       'card-0.2.12 mpg-c82.csv': ROOT / 'reports/card-0.2.12/mpg-c82.csv',
                       'card-0.2.12 three-value.csv': ROOT / 'reports/card-0.2.12/three-value.csv',
                       'abilityC by season (E-123 t_season acc)': ROOT / 'reports/card-0.2.12/abilityC-by-season.json'})
    if USAGE_WIN:
        inputs.update({'window11.py': HERE / 'window11.py', 'avail-hist-0210g.json.gz': HERE / 'avail-hist-0210g.json.gz',
                       'dnp-2025-26.json (出缺勤)': ROOT / 'data/season-source/dnp-2025-26.json'})
    sha = {k: {'path': rel(v), 'sha256': C.sha256_file(v)} for k, v in inputs.items() if v}
    pbp_files = sorted(p.stem for p in (DATA26 / 'pbp').glob('*.json'))
    games = sorted({r['GAME_ID'] for r in sd26['teamRows']})
    meta = {
        'version': VERSION, 'cardMode': CARD_MODE, 'e064Mode': E064_MODE, 'e064Anchors': anc064, 'e064RRepl': r_repl064,
        'e064MpgNoDataPlayers': len(mpg_nodata), 'priorCard': CARD_VERSION, 'dataCutoff': cutoff,
        'dataFirstDate': min(r['GAME_DATE'] for b in sd26['box'].values() for r in b['rows']),
        'games': len(games), 'pbpGames': len(pbp_files), 'missingPbp': sorted(set(games) - set(pbp_files)),
        'gitHead': git_head(), 'start': 'S*', 'prior': PRIOR, 'target': TARGET, 'c': C_PARAM, 'G': G_GAMES,
        'frozenAttrs': frozen + list(IC.FROZEN_ATTRS), 'updatableAttrs': list(C.UPD) + ['foulDraw'],
        'window10': ({'attrs': ['long', 'creation'], 'mpgL': MPG_L, 'threeValue': 'window（四季，abilityC 難度調整 acc）', 'module': 'live/window10.py',
                      'note': 'E-185：long、creation、threeValue、MPG_hat 改四季滑動窗口（線性遞減）；用人層係數／錨點／r_repl 取 card 0.2.10d 的 KAU 重擬合值（usage 檔）'} if WIN10 else None),
        'window8': {'attrs': list(WIN8_ATTRS), 'module': 'live/window8.py', 'gamesDone': WIN8['games'], 'pbpGames': WIN8['pbp'], 'players': n_win8,
                    'note': '8 項（drive,foulDraw,ft,mid,pass,rebound,short,tovSkill）＝E-175 U 臂四季滑動窗口；其餘屬性仍走 C4；lastOVR 基準＝同模型、本季 0 場（window8.day0）；係數／錨點／r_repl 取 card 0.2.10d 的重擬合值（usage 檔）'},
        'delta2Undefined': undefined, 'delta2': delta2,
        'players': {'ranked': len(rows), 'noPrior': len(nopr), 'priorCardNotPlayed': len(not_played),
                    'rosterUnplayed': len(unplayed), 'rosterFile': bool(roster)},
        'foulDrawFreeze': {k: v for k, v in load_json(PRIOR_CARD)['foulDrawFreeze'].items() if k != 'poolComposite'},
        'usageWindow': ({'on': True, 'module': 'live/window11.py', 'players': len(usage_now), 'gamesDone': WIN8['games'],
                         'note': 'E-192：L＝log1p(窗口 MIN÷窗口可出賽場次)、a＝窗口出賽÷窗口可出賽（權重同 E-175 U 臂：四季、c＝82×已賽場數/1230、本季逐場線性遞減）；y、v 用當下年齡；d 不進模型（b8＝0）。'
                                 'lastOVR 基準＝本季 0 場窗口；係數同 0.2.10d；窗口內沒有可出賽場次者 predNew＝p。本季出缺勤只含上場名單（沒有 INACTIVE 名單），可出賽場次略低估。'}
                        if USAGE_WIN else {'on': False, 'note': 'USAGE_WIN=0：用人特徵凍結在 2025-26 全季（= 0.2.10f）'}),
        'usage': {'file': rel(USAGE_FILE), 'payloadSha256': usage_sha, 'frozenAt': PRIOR, 'coef': ucoef,
                  'mpg0': ('card 0.2.10d ranking.csv mpg 欄＝窗口 MPG c=82（依名字配對；卡裡沒有的人退回 MIN／GP）；MPG_hat＝窗口 MPG（window10.mpg_at），lastOVR 基準用 day0 窗口 MPG' if WIN10 else 'card 0.2.4 ranking.csv mpg 欄（依名字配對；卡裡沒有的人退回 MIN／GP）'),
                  'mpg0FromCard': sum(1 for pid, c in prior_cards.items() if c['name'] in mpg_card),
                  'mpg0Fallback': sum(1 for pid, c in prior_cards.items() if c['name'] not in mpg_card)},
        'e128': m26_info,
        **({'ageStart': WIN8['ageStart']} if WIN8.get('ageStart') else {}),
        'inputs': sha, 'mapping2025_26': {'priors': mp['priors'], 'poolSize': mp['poolSize'],
                                          'boxPlayersDroppedNoBio': mp['boxPlayersDroppedNoBio'],
                                          'priorShotSampleFilled': [mp['priorShotSampleFilled'], mp['priorCards']]},
        'sanity': sanity,
        'threeValue': {**tv_info, 'formula': ('vol*(acc-rep); vol=四季窗口 3PA/MIN*36; acc=(n_w+k*mu)/(a_w+k)，n_w＝各季 abilityC×加權3PA（沒有 abilityC 的季用原始 FG3M）; rep=合併聯盟3P%-0.03; 池=窗口 MIN>=500且有先驗卡' + ('，加上近三季各自以該季結尾的窗口值（窗口加權 MIN>=500；E-191b P1m，0.2.10f）' if TV_P1M else '') + '; 百分位→attr() 40-99，PR≥99 走頂端尾巴（錨點＝池 r99、S）（E-185）' if WIN10 else 'vol*(acc-rep); vol=合併(2025-26+2026-27)3PA/MIN*36; acc=(k*abilityC_2025-26+FG3M_2026-27)/(k+FG3A_2026-27)'
                       '（本季無出手難度資料，用原始命中）; rep=合併聯盟3P%-0.03; 池=合併MIN>=500且有先驗卡; 百分位→attr() 40-99，027b 下 PR≥99 走頂端尾巴（錨點＝即時池 r99、S）'),
                       'note': '顯示用，不進 OVR（R-024）；long 欄仍留在 ranking.csv 並進 OVR，但表格不顯示'},
    }
    (out_dir / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    # ---- README.md
    def trow(r):
        return [r['name'], r['team'], r['N'], r['lastOVR'], r['ovr'], f"{r['_d']:+.2f}"]

    mv_detail = []
    for r in movers:
        ch = [d for d in diag if d['pid'] == r['playerId'] and abs(d['xhat'] - d['x0']) > 1e-9]
        txt = '；'.join(f"{d['attr']} {d['x0']:.1f}→{d['xhat']:.1f}（觀測 {d['y']:.1f}、n={d['n']:.0f}、k={d['k']:.0f}、w={d['w']:.3f}）"
                       for d in ch) or '（無屬性變動）'
        mv_detail.append(f"- {r['name']}（{r['team']}，N={r['N']}，ΔOVR {r['_d']:+.2f}）：{txt}")
    OVR_NOTE = (f"- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝{r_repl064:.4f}（替補水準 PR10），"
                f"映射錨點 PR1/PR50/PR99＝{anc064[0]:.4f}/{anc064[1]:.4f}/{anc064[2]:.4f}（{CARD_VERSION} summary.json 同組）"
                + (f"，PR90/PR95＝{anc064[3]:.4f}/{anc064[4]:.4f}（E-188 S3：PR50→70、PR90→88、PR95→92、PR99→99 分段線性）。" if anc064[3] is not None else "（兩段式）。")
                + (f"MPG_hat＝窗口 MPG（Σu·MIN／Σu·GP，過去 {MPG_L} 季＋本季逐場線性遞減，E-185）；lastOVR 基準＝本季 0 場的窗口 MPG；窗口內沒出賽的 {len(mpg_nodata)} 人退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。" if WIN10 else
                   f"MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；"
                   f"沒有本季視窗紀錄的 {len(mpg_nodata)} 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。"))
    ATTR_NOTE = ("- inseason 0.2.12e（R-163／R-164）：防守加成的 RAPM 窗口改用每位球員自己的出賽場次當時間軸（沒打的場次、賽季不佔窗口）；復出老將補進用人層，上場時間用同一套個人場次窗口（本季場次接上最近一季）。\n" if VERSION == "inseason 0.2.12e" else "") + (("- inseason 0.2.12d：2025-26 沒上場的復出老將（Lillard、Kyrie、Haliburton、VanVleet 等）用 v5 舊季卡補進名單，跳過受傷季走四季窗口，沒有舊季卡的人（≥800 分鐘門檻）仍不列；他們不進 H1 封頂／百分位／引力擬合池。\n" if RETURNING_VETS else "") + ("- inseason 0.2.12c（R-144，E-207）：tovSkill 的失誤率分母由持球分鐘改觸球次數＝0.5·z(−每觸球失誤，窗口加權失誤對窗口加權觸球收縮，k 乘觸球／持球分鐘換算係數)＋0.5·z(持球分鐘/36)；觸球來源同持球分鐘（NBA.com tracking TOUCHES）；池、z、0–99 映射凍結於 live/tov-pool-card0212c.json；卡片全部係數重擬合（card 0.2.12c）。\n" if TOV_TOUCH else "") + (("- inseason 0.2.12（R-139，E-203）：tovSkill 改看持球時間＝0.5·z(−每持球分鐘失誤，窗口加權失誤對窗口加權持球分鐘收縮)＋0.5·z(持球分鐘/36)；持球分鐘＝NBA.com tracking TIME_OF_POSS（過去季 handle-E069 raw、本季 data/defense-seventh/2026-27/possessions.json 每天抓整季），收縮、z、0–99 映射凍結自卡片端（live/tov-pool-card0212.json、live/tov_live.py）；新秀（不在卡片名單）用本季整季值、本季 1000 分鐘內與起點線性混合；卡片全部係數重擬合（card 0.2.12）。\n" if TOV_POSS else "")) + ("- inseason 0.2.10j（R-134／R-135）：加能力值引力（gravity）＝NBA.com 無球外線引力，2025-26 與本季依 FRAMES 加權、套四季窗口季權重；兩季都沒有的人用 OLS（3PA/36、3P%、USG%、位置）補；卡片全部係數重擬合（card 0.2.10j）。\n" if GRAVITY else "") + ("- inseason 0.2.10i（R-130／R-132）：切入（drive）只算帶球切入到 10 呎內的自主兩分（量與效率各半），自主創造（creation）改成自己創造的跳投與低位出手（不含切入上籃、補籃、空切）per36；兩項都是四季滑動窗口，卡片全部係數重擬合（card 0.2.10i）。\n" if SPLIT_DC else "") +
                (f"- inseason 0.2.10g（E-192）：用人層的 L（上場強度）、a（出賽率）也改四季滑動窗口（權重同其他窗口項；y、v 用當下年齡），每天用當下窗口重算，不再凍結在 2025-26；係數同 0.2.10d，r_repl、錨點用新池重取。\n" if USAGE_WIN else "") +
                (f"- inseason 0.2.10f（E-191b）：3PT 欄（threeValue，顯示用）的對照池改成近三季各自窗口值＋本季窗口值（窗口加權 MIN≥500），ranking／OVR／名次同 0.2.10e。\n" if WIN10 and TV_P1M else "") +
                (f"- inseason 0.2.10e（E-188，R-124）：只換 OVR 映射（PR90→88、PR95→92，名次不變），屬性、係數同 0.2.10d。\n" if WIN10 else "") +
                (f"- inseason 0.2.10d（E-185）：long、creation 也改四季滑動窗口（同 8 項的權重；long 是窗口 3PM／3PA 收縮到本季聯盟 3P%、creation 是窗口 FGA/MIN），threeValue、MPG_hat 同為窗口；係數、錨點、r_repl 用 card 0.2.10d 的 KAU 重擬合值（底 card 0.2.10c）。\n" if WIN10 else "") +
                 "- inseason 0.2.10（R-114）：drive、foulDraw、ft、mid、pass、rebound、short、tovSkill 八項＝E-175 四季滑動窗口（過去四季權重 window_w(c)，c＝82×已賽場數/1230；本季逐場線性遞減；收縮 k、先驗 m、映射皆凍結自 2025-26 U 鏈；live/window8.py），不再走 C4 的 x0+w(y−x0)；其餘屬性（stamina 等）仍走 C4。用人層係數、錨點、r_repl 取現行卡的重擬合值（usage 檔）。"
                 "- 以下為舊版 E-128 說明（其餘屬性的先驗與映射仍適用）：E-128（CARD_MODE=027b，預設）：先驗 x0＝card 0.2.7b 產生器的未四捨五入能力值（尾巴原樣、不夾 99）；屬性迴歸＝rebase-027a e123a primary 的 summary.json；"
                 "賽中觀測值對 live/pool-027b.json 的合併池映射（pass 換 E-125 量×率合成值＋合併池，視窗不收縮、z 常數凍結自 2025-26 卡片端；其餘 8 欄同 pool-027），"
                 "99 以上與 40 以下照 E-101 尾巴；help 照 E-123 D1 尾巴（不夾 99）；drive、onBall、pressure、presDisplay、physique、heightInches 凍結；防守加成＝UL 值（同 027）。")
    OVR_NOTE += (f"\n- card 0.2.4 用人層（E-091，R-044 = 用人回歸＋當季 RAPM 目標）：p＝上面屬性迴歸的每 36 預測（`predictedPer36`，C4 照常更新），"
                 f"predNew＝b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（`predNew` 欄）；"
                 + (f"L、a 與 has 旗標＝四季滑動窗口（0.2.10g，E-192，live/window11.py，每天用當下窗口重算；y、v 用當下年齡；係數、錨點、r_repl 取 `{USAGE_FILE.name}`，payload sha256 {usage_sha[:12]}…），has=False 或不在卡內者 predNew＝p；"
                    if USAGE_WIN else
                    f"L、a、y、v、d 與 has 旗標凍結在 2025-26 全季（`{USAGE_FILE.name}`，payload sha256 {usage_sha[:12]}…，年齡不加一歲），has=False 或不在卡內者 predNew＝p；") +
                 f"係數 b0={ucoef['b0']:.4f}、b1={ucoef['b1_p']:.4f}（E-084 results.json）。MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對），卡裡沒有的人退回 MIN／GP。"
                 + ("\n- E-095（CARD_MODE=025）：分鐘權重 mpg/36 改為飽和 W(mpg)=(1−e^(−mpg/15))/(1−e^(−36/15))（card 0.2.5，R-047），錨點／r_repl 取 E-089 results.json report_only.card.new。"))
    OVR_NOTE += f"\n- E-128：用人層係數、r_repl、錨點取 {rel(USAGE_FILE)}（rebase-027a e123a pipeline 重跑，錨點對 rebase-027a/work/cards-result.json 核對）；分鐘權重 W 同 card 0.2.5。"
    md = f"""# {VERSION} 2026-27 即時結果（資料截至 {cutoff}）

- OVR：賽中 C4（{VERSION}），先驗 {CARD_VERSION}（live/{PRIOR_CARD.name}）；N = 該球員 2026-27 已打場數。
- 資料：{meta['dataFirstDate']}..{cutoff}、{len(games)} 場、{len(pbp_files)} 份 PBP；缺 PBP：{', '.join(meta['missingPbp']) or '無'}。
- git HEAD：`{meta['gitHead'][:12]}`；c={C_PARAM}（凍結）、G={G_GAMES}、f = min(N/{G_GAMES}, 1)。
- 排名 {len(rows)} 人（有先驗卡且已出賽，加上在現役名單上但還沒出賽的 {len(unplayed)} 人，N=0、OVR＝先驗）；沒有先驗卡 {len(nopr)} 人（`no-prior.csv`，不給 OVR）；有先驗卡、沒出賽也不在現役名單 {len(not_played)} 人（不列入）。
- N 分布：{', '.join(f'N={n}: {c} 人' for n, c in sorted(n_dist.items()))}。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k={THREE_K}（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（{tv_info['mu']:.4f}）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 {tv_info['poolSize']} 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
{ATTR_NOTE}
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線、本季 0 場（8 項屬性＝窗口 day0）算出的 OVR（ΔOVR 的基準，R-112）；`formalOVR` = {CARD_VERSION} `ranking.csv` 同名球員的 OVR（只供對照）。
{OVR_NOTE}

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \\|OVR 差\\| 最大值（門檻 <0.5） | {t1:.6f} → {'通過' if t1 < 0.5 else '失敗'} |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | {t1_same:.3e} |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | {t2:.3e} |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | {pw.check:.2e} |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | {max(dl):.3f} ／ {max(df):.3f} |
| lastOVR vs 正式卡 OVR（同名 {len(formal_diff)} 人）最大差 | {max(formal_diff) if formal_diff else 'n/a'} |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 {len(rows)}；\\|ΔOVR\\| 中位數 {sanity['b_median_abs']:.3f}、平均 {sanity['b_mean_abs']:.3f}、最大 {sanity['b_max_abs']:.3f}。
- \\|ΔOVR\\| >= 1.0 的人：{len(big)} 人{('：' + '、'.join(f"{n}（N={k}，{d:+.2f}）" for n, k, d in sanity['b_ge_1'])) if big else ''}。
- 有屬性被更新的（屬性：人次）：{', '.join(f'{a} {c}' for a, c in sorted(changed_attrs.items(), key=lambda kv: -kv[1])) or '無'}。

依 N 分組的 \\|ΔOVR\\|：

{md_table(['N', '人數', '中位數', '最大'], [[n, v['players'], f"{v['median']:.3f}", f"{v['max']:.3f}"] for n, v in sanity['b_by_N'].items()])}

ΔOVR 最高 10 人：

{md_table(['球員', '隊', 'N', 'lastOVR', 'OVR', 'ΔOVR'], [trow(r) for r in ordered[::-1][:10]])}

ΔOVR 最低 10 人：

{md_table(['球員', '隊', 'N', 'lastOVR', 'OVR', 'ΔOVR'], [trow(r) for r in ordered[:10]])}

\\|ΔOVR\\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

{chr(10).join(mv_detail)}
"""
    (out_dir / 'README.md').write_text(md, encoding='utf-8')
    print(json.dumps({'out': rel(out_dir), 'ranked': len(rows), 'noPrior': len(nopr), 'sanity': {
        k: v for k, v in sanity.items() if k != 'b_by_N'}}, ensure_ascii=False, indent=1, default=str))
    return 0 if (t1 < 0.5 and t1_same < 1e-9 and t2 < 1e-9) else 4


if __name__ == '__main__':
    # 單一入口：新賽季的反事實與版本比較只走 run_c4_live_rookie.py（包裝器 exec 本檔，__name__ 不是 __main__）。
    # 直接跑本檔會漏掉新秀先驗等包裝層，數字會和頁面不同（L-088、L-090）。
    raise SystemExit('run_c4_live.py 不能直接執行：請改跑 run_c4_live_rookie.py（見 live/CURRENT.json、live/README.md）')
