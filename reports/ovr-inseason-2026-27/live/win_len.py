"""四季窗口長度開關（E-204，R-140；做法同 E-201 的 work/e201_run.py，補丁正式化）。

WIN_LEN（環境變數，預設 246）：窗口格數；328＝四季整窗（0.2.12a 以前），重現舊版。逐場線性形狀、每人正規化與下限、係數、錨點、r_repl 都不動；
預測 MPG 的窗口（MPG_L＝1 季）不在此列。
install() 在 run_c4_live_rookie.py 載入時、以及名單頁提示卡（scripts/attr_cell_tips.py）呼叫；重複呼叫無害。WIN_LEN=328 時什麼都不改（位元不變）。
補丁（皆為執行期，不改原檔）：
  1. e175_lib.WIN（window8.Win8.sums 的過去季權重與本季 u）：Win8／Win10／Win11 建構完才改成 WIN_LEN（池、映射器、收縮先驗用 328 建好；建構期間固定 328）。
  2. window10.Win10.sums10：nseas==4 時窗口＝WIN_LEN（long、creation 以外的 threeValue 原料、用人層 L／a）；nseas==1（MPG）不動。
  3. rookie_defense.WIN（老將 onBall／help、pres_drive 的壓迫／切入、gravity_live 的季權重都讀 RD.window_weights）。縮短後有人「有資料的季」權重全是 0，除以 0 → 0 權重改 1e-12。
  4. defense_bonus.WIN／positions（防守 D 重擬合）：時間軸固定 328 格座標，窗口 [c + 328 − WIN, 328 + c]。
  5. window10.Win10.tv_past_pool（threeValue 顯示欄的過去季對照池）固定 328。
"""
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

WIN_LEN = int(os.environ.get('WIN_LEN', '246'))
FULL = 328
_STATE = {'installed': False, 'depth': 0, 'on': False}


def install():
    if _STATE['installed']:
        return
    _STATE['installed'] = True
    if WIN_LEN == FULL:
        return
    import numpy as np
    import rookie_defense as RD
    import defense_bonus as DB
    import window8 as W8
    import window10 as W10
    import window11 as W11
    L = W8.L

    def wrap_init(cls):
        init = cls.__init__

        def _init(self, *a, **k):
            if _STATE['depth'] == 0:
                L.WIN, _STATE['on'] = FULL, False      # 池／映射／收縮先驗一律用 328 建
            _STATE['depth'] += 1
            try:
                init(self, *a, **k)
            finally:
                _STATE['depth'] -= 1
            if _STATE['depth'] == 0:
                L.WIN, _STATE['on'] = WIN_LEN, True
        cls.__init__ = _init
    for cls in (W8.Win8, W10.Win10, W11.Win11):
        wrap_init(cls)

    def wk(c, win, nk):
        w = {}
        for k in range(1, nk + 1):
            b = win - c - L.SLOTS * (k - 1)
            a = b - L.SLOTS
            w[k] = (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * win * L.SLOTS)
        return w

    def sums10(self, name, g, cur, G, S=W10.TARGET, nseas=4, abil=False):
        c = L.SLOTS * g / G
        win = WIN_LEN if (nseas == 4 and _STATE['on']) else nseas * L.SLOTS
        nk = math.ceil(win / L.SLOTS)
        w = wk(c, win, nk)
        base = L.SEASONS.index(S) if S in L.SEASONS else len(L.SEASONS)
        n, d = np.zeros(self.D.NP), np.zeros(self.D.NP)
        for k in range(1, nk + 1):
            i = base - k
            if i < 0 or w[k] <= 0:
                continue
            s = L.SEASONS[i]
            tab = self.T10.get(s, {}).get(name)
            if tab is None:
                continue
            nk_, dk = tab.agg()
            if abil and s in self.abil:
                nk_ = np.where(np.isnan(self.abil[s]), nk_, self.abil[s] * dk)
            n += w[k] * nk_
            d += w[k] * dk
        if g > 0:
            tab = cur[name]
            u = (win - c + L.SLOTS * (tab.gi + 0.5) / G) / win
            nc, dc = tab.agg(0, g, w=u)
            if abil and S in self.abil:
                nc = np.where(np.isnan(self.abil[S]), nc, self.abil[S] * dc)
            n += nc
            d += dc
        return n, d
    W10.Win10.sums10 = sums10

    _tpp = W10.Win10.tv_past_pool

    def tv_past_pool(self, *a, **k):
        saved = (L.WIN, _STATE['on'])
        L.WIN, _STATE['on'] = FULL, False
        try:
            return _tpp(self, *a, **k)
        finally:
            L.WIN, _STATE['on'] = saved
    W10.Win10.tv_past_pool = tv_past_pool

    RD.WIN = WIN_LEN
    _ww = RD.window_weights
    RD.window_weights = lambda c: {s: (v if v > 0 else 1e-12) for s, v in _ww(c).items()}

    def positions(D):
        us, _ = DB.F.game_u(D, DB.PAST)            # u = (k·82 + slot + 0.5)/328（四季座標）
        t = {s: us[s] * FULL - (FULL - WIN_LEN) for s in DB.PAST}
        if DB.SEASON in D.s:
            n = np.array([int(str(g)[-5:]) for g in D.s[DB.SEASON]['gid']], float)
            t[DB.SEASON] = WIN_LEN + (n - 0.5) / DB.GAMES * DB.SLOTS
        return t
    DB.WIN = WIN_LEN
    DB.positions = positions
