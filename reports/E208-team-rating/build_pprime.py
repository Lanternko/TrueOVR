"""E-208 P′：用 E-175 的 U 臂（窗口）在「第 0 天」(g=0) 重算 2025-26 的窗口屬性，只用 ≤2024-25 的資料。
同一條映射鏈（card_chain arm='U'），僅把 u_sums 的本季場數強制為 0。另輸出季末版 (g=G) 供對照尺度。
python -I -X utf8 reports/E208-team-rating/build_pprime.py
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
E175 = ROOT / 'reports/E175-sliding-window-card'
sys.path.insert(0, str(E175))
import e175_lib as L, e175_card as C
D = L.Data(); inp = C.load_inputs()
orig = L.u_sums
def run(day0):
    L.u_sums = (lambda D_, attr, S, g: orig(D_, attr, S, 0)) if day0 else orig
    return C.card_chain(D, inp, 'U')
U0 = run(True); U1 = run(False); L.u_sums = orig
out = {'attrs': C.ATTRS8, 'pids': U0['pids'], 'names': U0['names'],
       'day0': {a: [float(v) for v in U0['mapped'][a]] for a in C.ATTRS8},
       'end': {a: [float(v) for v in U1['mapped'][a]] for a in C.ATTRS8}}
(Path(__file__).parent / 'pprime-day0.json').write_text(json.dumps(out), encoding='utf-8')
for a in C.ATTRS8:
    d0, e = np.array(out['day0'][a]), np.array(out['end'][a])
    print(a, 'sd0 %.2f sdE %.2f corr %.3f' % (d0.std(), e.std(), np.corrcoef(d0, e)[0, 1]))
