"""E-302 診斷（預註冊外，只報）：各屬性逐場變動與該場 rt 的 Spearman，r0 對 ra；以及 |Δ屬性| 中位。"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import eval as E  # noqa: E402  (只用載入好的 HIST、box、gid_of)
ATTRS = ('long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'pass', 'rebound', 'creation', 'threeValue', 'predNew')
out = {}
for s in ('r0', 'ra', 'rap'):
    X, D = [], {a: [] for a in ATTRS}
    for pid, hh in E.HIST[s].items():
        pts = [(d, pt) for d, pt in hh['pts'] if pt and pt.get('predNew') is not None]
        for i in range(1, len(pts)):
            d, pt = pts[i]
            bx = E.box.get((pid, E.gid_of.get((pid, d))))
            if not bx or bx[1] < 10:
                continue
            prev = pts[i - 1][1]
            if any(pt.get(a) is None or prev.get(a) is None for a in ATTRS):
                continue
            X.append(bx[0])
            for a in ATTRS:
                D[a].append(pt[a] - prev[a])
    out[s] = {a: {'rho_rt': round(spearmanr(X, D[a]).correlation, 3), 'absd_med': round(float(np.median(np.abs(D[a]))), 3)} for a in ATTRS}
    out[s]['n'] = len(X)
for a in ATTRS:
    print(f"{a:10s}", *(f"{s}: ρ {out[s][a]['rho_rt']:+.3f} |Δ| {out[s][a]['absd_med']:.2f}" for s in ('r0', 'ra', 'rap')))
json.dump(out, open(Path(__file__).resolve().parent / 'diag_attr.json', 'w', encoding='utf-8'), indent=1)
