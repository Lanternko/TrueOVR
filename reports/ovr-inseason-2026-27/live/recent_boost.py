"""本季近期加成開關（E-221，R-147；做法同 win_len.py：執行期補丁，不改原檔，RECENT_BOOST=0 或 RB_B=0 時線上行為與舊版位元相同）。

RECENT_BOOST（環境變數，預設 1＝開，b=3、h=20；2026-11-03 使用者裁定 R-150 上線；RECENT_BOOST=0 或 RB_B=0 回到舊版）：1＝開。RB_B（b，加成幅度）、RB_H（h，指數衰減長度，單位＝球隊場次）。
只改本季逐場權重，過去季不動：本季第 i 場（league 場次序號 gi）在聯盟已賽 g 場時的權重 u_i 改成
    u'_i = u_i × (1 + b_eff · exp(−(g − 1 − gi)·(SLOTS/G) / h))
    b_eff = b × clip((G − g)/(0.2·G), 0, 1)          # 最後 20% 季線性淡出，g＝G 時 b_eff＝0.0（季末＝單季卡）
(g−1−gi) 是聯盟場數，乘 SLOTS/G（82/1230）換成球隊場次。
實作點：e175_lib.Tab.agg(lo=0, hi=g, w=u)——所有本季逐場窗口和（window8.sums、window10.sums10〔含 window11.usage_at 的 mpg／ap／pl〕、
tov_live 的窗口分鐘占比、e175 u_sums）都以 `tab.agg(0, g, w=u)` 呼叫，在這裡統一乘上 factor。b=0 時 factor 是 1.0 整列，
w×1.0 與原式逐位元相同。
pres_drive 的 drive（本季逐場出手 `_cur_drive_shots()`、逐場分鐘）另外在 PD.drive_counts 的本季分支乘同一個 factor（errata-1 §A1 更正；g＝本季 player-games 的場數、
gi＝(GAME_DATE, GAME_ID) 排序後的序號；失手權重 pu 不加權；gp 欄不加權）。b=0 時 factor 是 1.0，x×1.0 與原式逐位元相同。
沒有逐場資料的本季累計表（rookie_defense 的 onBall／help、pres_drive 的壓迫 hustle、gravity_live）不在補丁範圍，維持季累計（errata-1）。
install() 在 run_c4_live_rookie.py 載入時呼叫；重複呼叫無害。G 可用 RB_G 覆寫（回放不同季長度用）；SLOTS 固定 82（球隊場次換算）。
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ON = os.environ.get('RECENT_BOOST', '1') == '1'
B = float(os.environ.get('RB_B', '3'))
H = float(os.environ.get('RB_H', '20'))
G_TOTAL = int(os.environ.get('RB_G', '1230'))
SLOTS = 82
_STATE = {'installed': False}


def factor(gi, g, b=None, h=None, G=None):
    """逐列加成倍數（長度同 gi）。g＝聯盟已賽場數。"""
    import numpy as np
    b = B if b is None else b
    h = H if h is None else h
    G = G_TOTAL if G is None else G
    b_eff = b * min(max((G - g) / (0.2 * G), 0.0), 1.0)
    age = np.maximum(g - 1 - np.asarray(gi, float), 0.0) * (SLOTS / G)
    return 1.0 + b_eff * np.exp(-age / h)


def install():
    if _STATE['installed']:
        return
    _STATE['installed'] = True
    if not ON:
        return
    import numpy as np
    import window8 as W8
    L = W8.L
    _agg = L.Tab.agg

    def agg(self, lo=0, hi=10 ** 9, w=None):
        if w is not None and lo == 0 and 0 < hi < 10 ** 9:
            w = np.asarray(w, float) * factor(self.gi, hi)
        return _agg(self, lo, hi, w)
    L.Tab.agg = agg

    import pres_drive as PD
    _dc = PD.drive_counts

    def drive_counts(season, half=None, pu_half=None):
        if season != PD.SEASON:
            return _dc(season, half, pu_half)
        shots, gids = PD._cur_drive_shots()
        games = PD._cur_games()
        order = sorted({(r['GAME_DATE'], r['GAME_ID']) for r in games})
        gi_of = {g: i for i, (_, g) in enumerate(order)}
        gsum = len(order)
        rows = [r for r in games if r['GAME_ID'] in gids]
        fac = lambda gid: float(factor([gi_of[gid]], gsum)[0])
        pu = PD._pu(shots)
        out = {}
        get = lambda p: out.setdefault(p, [0.0, 0.0, 0.0, 0.0, 0])
        for r in rows:
            x = get(int(r['PLAYER_ID']))
            x[1] += float(r['MIN'] or 0) * fac(r['GAME_ID'])
            x[4] += 1
        for s_ in shots:
            if s_['assisted']:
                continue
            f = fac(s_['gid'])
            w = (1.0 if s_['made'] else pu.get(s_['cls'], 1.0)) * f
            x = get(s_['pid'])
            x[0] += w
            x[3] += w
            if s_['made']:
                x[2] += (2 + s_['ftmade']) * f
        return out
    PD.drive_counts = drive_counts
