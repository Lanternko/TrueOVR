"""E-302：各窗口項的穩定點 M_x（2025-26 歷史季逐場表，奇偶分半；不用 2026-27）。
用法：python -I -X utf8 reports/E302-attr-anchor/e302_mx.py → reports/E302-attr-anchor/mx.json"""
import json
import sys
from pathlib import Path
import numpy as np

EXP = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP / 'live-r0'))
import window10 as W10  # noqa: E402

S = '2025-26'
W8_NAMES = ['ft', 'rebound', 'vol', 'foulDraw', 'astvol', 'pass', 'mid', 'short', 'driveVol', 'driveEff']
W10_NAMES = ['f3', 'cr', 'crJ', 'tpa']
TOP = 300


def split_half(tab):
    gi, pi, n, d = tab.gi, tab.pi, tab.n, tab.d
    order = np.lexsort((gi, pi))
    pi_s = pi[order]
    # 每人自己的第幾場（0 起）
    first = np.r_[0, np.flatnonzero(np.diff(pi_s)) + 1]
    rank = np.arange(len(pi_s)) - np.repeat(first, np.diff(np.r_[first, len(pi_s)]))
    half = rank % 2
    NP = tab.NP
    out = []
    for h in (0, 1):
        m = half == h
        out.append((np.bincount(pi_s[m], weights=n[order][m], minlength=NP),
                    np.bincount(pi_s[m], weights=d[order][m], minlength=NP)))
    return out


def mx(tab):
    (n1, d1), (n2, d2) = split_half(tab)
    dt = d1 + d2
    sel = np.argsort(-dt)[:TOP]
    sel = sel[(d1[sel] > 0) & (d2[sel] > 0)]
    r1, r2 = n1[sel] / d1[sel], n2[sel] / d2[sel]
    rho = float(np.corrcoef(r1, r2)[0, 1])
    dh = float(np.median(np.r_[d1[sel], d2[sel]]))
    M = dh * (1 - rho) / rho if rho > 0.05 else None
    return {'rho_half': round(rho, 4), 'n': int(len(sel)), 'd_half_med': round(dh, 3), 'M': None if M is None else round(M, 3),
            'lam_at_half': None if M is None else round(dh / (dh + M), 3)}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    W = W10.Win10()
    res = {}
    for a in W8_NAMES:
        tab = W.D.tab[S].get(a)
        res[a] = mx(tab) if tab is not None else None
    for a in W10_NAMES:
        tab = W.T10[S].get(a)
        res[a] = mx(tab) if tab is not None else None
    for a, v in res.items():
        print(a, v)
    json.dump({'season': S, 'top': TOP, 'mx': res}, open(EXP / 'mx.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
