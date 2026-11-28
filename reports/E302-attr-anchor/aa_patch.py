"""E-302 能力值錨點（AA）補丁：本季份量照「本季證據 vs 各項穩定點 M_x」決定，不再只看窗口位置（預註冊 prereg.md）。

執行期補丁（同 win_len／recent_boost 做法），在快照的 run_c4_live_rookie.py 於 recent_boost.install() 之後呼叫 install()。
只改 S＝2026-27、g>0 的窗口和；名單：
  window8.Win8.sums：ft、rebound、vol、foulDraw、astvol、pass、mid、short、driveVol、driveEff
  window10.Win10.sums10（nseas＝4）：f3、cr、crJ、tpa
做法（每人逐項）：
  過去季 (n_p, d_p)＝同一函式、本季給空表；本季 (n_c, d_c)＝總和 − 過去（含 win_len 窗口、recent_boost b=3／h=20 加成）。
  s_win＝d_c／(d_p＋d_c)
  d_ev＝Σ_{本季 gi<g} d·exp(−age／20)，age＝(g−1−gi)·82／G
  λ0＝d_ev／(d_ev＋M_x)；fade＝clip((G−g)／(0.2G), 0, 1)
  MODE='max'：s*＝s_win＋fade·max(0, λ0−s_win)；MODE='pure'：s*＝s_win＋fade·(λ0−s_win)
  n′＝D·[(1−s*)·n_p／d_p＋s*·n_c／d_c]，d′＝D＝d_p＋d_c（分母不變＝收縮量不變）
  d_p 或 d_c 為 0、fade＝0、或 s*＝s_win 的人：n 原值不動（逐位元）。
M_x 讀同資料夾的 mx.json（e302_mx.py，2025-26 奇偶分半）。
"""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
MODE = 'max'          # 快照各自寫死：live-ra＝'max'（主臂），live-rap＝'pure'
H_EV = 20.0
SLOTS = 82
AA8 = ('ft', 'rebound', 'vol', 'foulDraw', 'astvol', 'pass', 'mid', 'short', 'driveVol', 'driveEff')
AA10 = ('f3', 'cr', 'crJ', 'tpa')
_STATE = {'installed': False}


def load_mx(path=None):
    doc = json.loads(Path(path or HERE / 'mx.json').read_text(encoding='utf-8'))['mx']
    return {k: (float('inf') if v is None or v.get('M') is None else float(v['M'])) for k, v in doc.items()}


def d_ev(tab, g, G, NP):
    gi, pi, d = np.asarray(tab.gi), np.asarray(tab.pi), np.asarray(tab.d, float)
    m = gi < g
    age = np.maximum(g - 1 - gi[m], 0) * (SLOTS / G)
    return np.bincount(pi[m], weights=d[m] * np.exp(-age / H_EV), minlength=NP)


def rewrite(n, d, n_p, d_p, ev, g, G, M, mode=None):
    """回傳新的 n（d 不變）。"""
    mode = MODE if mode is None else mode
    fade = min(max((G - g) / (0.2 * G), 0.0), 1.0)
    if fade <= 0 or not np.isfinite(M):
        return n
    n_c, d_c = n - n_p, d - d_p
    ok = (d_p > 1e-9) & (d_c > 1e-9)
    if not ok.any():
        return n
    D = d_p + d_c
    s_win = np.where(ok, d_c / np.where(ok, D, 1.0), 0.0)
    lam = ev / (ev + M)
    gap = lam - s_win
    if mode == 'max':
        gap = np.maximum(gap, 0.0)
    elif mode != 'pure':
        raise ValueError(mode)
    s = s_win + fade * gap
    chg = ok & (s != s_win)
    safe_p, safe_c = np.where(ok, d_p, 1.0), np.where(ok, d_c, 1.0)
    n_new = D * ((1 - s) * n_p / safe_p + s * n_c / safe_c)
    return np.where(chg, n_new, n)


def install():
    if _STATE['installed']:
        return
    _STATE['installed'] = True
    import window8 as W8
    import window10 as W10
    L = W8.L
    MX = load_mx()
    _s8 = W8.Win8.sums
    _s10 = W10.Win10.sums10
    empty = lambda NP: L.Tab([], [], [], [], NP)

    def sums(self, attr, g, cur_tab, G, S=W8.TARGET):
        n, d = _s8(self, attr, g, cur_tab, G, S)
        if attr not in AA8 or S != W8.TARGET or g <= 0:
            return n, d
        n_p, d_p = _s8(self, attr, g, empty(self.D.NP), G, S)
        return rewrite(n, d, n_p, d_p, d_ev(cur_tab, g, G, self.D.NP), g, G, MX[attr]), d
    W8.Win8.sums = sums

    def sums10(self, name, g, cur, G, S=W10.TARGET, nseas=4, abil=False):
        n, d = _s10(self, name, g, cur, G, S, nseas, abil)
        if name not in AA10 or nseas != 4 or S != W10.TARGET or g <= 0:
            return n, d
        n_p, d_p = _s10(self, name, g, {name: empty(self.D.NP)}, G, S, nseas, abil)
        return rewrite(n, d, n_p, d_p, d_ev(cur[name], g, G, self.D.NP), g, G, MX[name]), d
    W10.Win10.sums10 = sums10
