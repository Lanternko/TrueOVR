"""E-207（改自 E-204）卡片端（2025-26 季末）：用線上管線的「卡片路線」（E-201 護欄 B 的做法）算 WIN_LEN 窗口下的 2025-26 卡片 ranking。
用法（repo root）：WIN_LEN=328|246 python -I -X utf8 reports/E204-window-246/card_route.py <輸出資料夾>
2025-26 整季當「本季」（g=G、c=82）；8 項 U 屬性、long、creation、MPG、用人層 L／a、防守加成走 win_len 的窗口；
onBall／help／壓迫／引力在卡片是單季值、不開窗口（維持先驗卡）。WIN_LEN=328 必須重現 reports/card-0.2.12-tov/ranking.csv 的 ovr。
補丁取自 E-201 work/e201_run.py（mode=end route=card），窗口補丁換成 live/win_len.py。
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)
sys.path.insert(0, str(LIVE))
import numpy as np  # noqa: E402
import window8 as W8  # noqa: E402
import window10 as W10  # noqa: E402
import window11 as W11  # noqa: E402
import run_c4_live_rookie as RK  # noqa: E402（載入時已 win_len.install()）
import win_len  # noqa: E402

args = type('A', (), {'mode': 'end', 'route': 'card', 'data': None})()
# --- 6. mode=end：y、v 用 2025-26 bio 年齡（card 0.2.10j 的 c=82 定義；線上 0.2.10h 起用 2026-27 開季足歲，季末一年後的年齡會對不上卡片）
if args.mode == 'end':
    def age_flags(self, pid):
        a = self.age25.get(pid)
        if a is None:
            a = self.age_cur.get(pid)
        return a, float(a is not None and a <= W11.AGE_Y), float(a is not None and a >= W11.AGE_V)
    W11.Win11.age_flags = age_flags

# --- 6b. mode=end route=card：2025-26 整季當「本季」（g=G、c=82）；窗口方法的預設季改 PRIOR；老將 onBall／help／壓迫／引力維持先驗卡（卡片端是單季值，不開窗口）
CARD_ROUTE = args.mode == 'end' and args.route == 'card'
if CARD_ROUTE:
    PR = W10.PRIOR

    def cur_tabs(self):
        t = dict(self.D.tab[PR])
        t.update(self.T10[PR])
        self.n_pbp = 0
        self.crj_cur = {}
        assert self.D.G[PR] == W10.G_TOTAL
        return t, self.D.G[PR]

    W11.Win11.cur_tabs = cur_tabs

    def dflt(name, n_pos):
        f = getattr(W11.Win11, name)

        def w(self, *a, **k):
            if len(a) <= n_pos and 'S' not in k:
                k['S'] = PR
            if len(a) <= n_pos + 1 and 'G' not in k:
                k['G'] = self.D.G[PR]
            return f(self, *a, **k)
        setattr(W11.Win11, name, w)

    for nm in ('extra_at', 'mpg_at', 'usage_at', 'tv_raw'):
        dflt(nm, 2)

    _sums = W8.Win8.sums

    def sums(self, attr, g, cur_tab, G, S=None):
        return _sums(self, attr, g, cur_tab, self.D.G[PR], PR if S is None else S)

    W8.Win8.sums = sums

    def vet_defense(sd26, attrs, prior_cards, pw, attrs0):
        posmap = {p: {'PG': 'G', 'SG': 'G', 'SF': 'F', 'PF': 'F', 'C': 'C'}.get(pc.get('pos')) for p, pc in prior_cards.items()}
        RK.live_bonus(pw, 0)
        RK.window_ref(attrs0, posmap, pw, 0)

    RK.vet_defense = vet_defense

    # 0.2.12 新增的持球分鐘窗口（tov_live.window_pm）：attrs_at 固定傳本季＝2026-27；卡片路線的本季是 2025-26（整季、c=82）
    if W8.TOV_POSS:
        import tov_live as TL
        _wpm = TL.window_pm

        def window_pm(W, g, tabs, G, S, cur_name):
            return _wpm(W, W.D.G[PR], tabs, W.D.G[PR], PR, PR)
        TL.window_pm = window_pm

        if TL.TOUCH:   # 0.2.12c：觸球窗口同樣固定在卡片的本季（2025-26）
            _wtc = TL.window_tch

            def window_tch(W, g, tabs, G, S, cur_name):
                return _wtc(W, W.D.G[PR], tabs, W.D.G[PR], PR, PR)
            TL.window_tch = window_tch

# --- 資料
if args.mode == 'live':
    DATA = Path(args.data) if args.data else DB.ROOT / 'data/defense-seventh/2026-27'
else:
    import ovr_history as OH
    DATA = OUT / 'data'
    if not (DATA / 'player-games.json').exists():
        OH.truncate('2026-10-19', DATA)               # 開季前一天：0 場
        import shutil
        shutil.copy2(OH.DATA26 / 'roster.json', DATA / 'roster.json')   # 現役名單（沒出賽的人也列，N=0）
    RK.DB.CUR_STINTS = DATA / 'stints.jsonl.absent'        # 0 場：不讀本季 stints
RK.DEF_L_LIVE = OUT / 'def-L-live.csv'
RK.DEF_L_BASE = OUT / 'def-L-base.csv'


def load_ns():
    src = RK.ORIG.read_text(encoding='utf-8')
    for o, n in ((RK.OLD_LINE, RK.NEW_LINE), (RK.OLD_DEF, RK.NEW_DEF), (RK.OLD_A, RK.NEW_A), (RK.OLD_REF, RK.NEW_REF),
                 (RK.OLD_LAST, RK.NEW_LAST), (RK.OLD_D, RK.NEW_D)):
        assert src.count(o) == 1, o
        src = src.replace(o, n)
    if RK.PD.ON:
        assert src.count(RK.OLD_PRES) == 1 and src.count(RK.OLD_META) == 1
        src = src.replace(RK.OLD_PRES, RK.NEW_PRES).replace(RK.OLD_META, RK.NEW_META)
    if args.mode == 'end':
        o = "    cutoff = max(r['GAME_DATE'] for b in sd26['box'].values() for r in b['rows'])\n"
        assert src.count(o) == 1
        src = src.replace(o, "    cutoff = max([r['GAME_DATE'] for b in sd26['box'].values() for r in b['rows']] or ['2026-10-19'])\n")
        if CARD_ROUTE:     # 季末：卡片 582 人全列（不限 2026-27 現役）
            o = "    roster = load_roster()\n"
            assert src.count(o) == 1
            src = src.replace(o, "    roster = {int(p): 'NA' for p in prior_cards}\n")
    ns = {'__name__': 'run_c4_live_exec', '__file__': str(RK.ORIG), '_E116': RK}
    exec(compile(src, str(RK.ORIG), 'exec'), ns)
    RK.NS.update(ns=ns)
    return ns


ns = load_ns()
ns['DATA26'] = DATA
sys.argv = [sys.argv[0], str(OUT)]
try:
    rc = ns['main']()
except ValueError as e:     # mode=end（0 場）：ranking.csv 寫完後 meta 統計對空集合取 min/max 會丟例外，與 ranking 無關
    if args.mode != 'end' or not (OUT / 'ranking.csv').exists():
        raise
    print('mode=end：meta 階段例外（ranking.csv 已寫出）：', e, file=sys.stderr)
    rc = 0
(OUT / 'card_route.json').write_text(json.dumps({'win': win_len.WIN_LEN, 'data': str(DATA), 'rc': rc}), encoding='utf-8')
raise SystemExit(rc)
