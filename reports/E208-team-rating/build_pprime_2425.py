"""E-208 追加 P″：同 build_pprime.py，但第 0 天改成 2024-25 開季（u_sums 用 S='2024-25'、g=0，窗口只含 ≤2023-24）。
映射鏈（池、先驗、尺度）仍是 2025-26 的 card_chain —— 這是污染來源之一（見預註冊）。end 沿用 pprime-day0.json 的 end（2025-26 季末同一窗口）。
python -I -X utf8 reports/E208-team-rating/build_pprime_2425.py
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
L.u_sums = lambda D_, attr, S, g: orig(D_, attr, '2024-25', 0)
U0 = C.card_chain(D, inp, 'U'); L.u_sums = orig
old = json.loads((Path(__file__).parent / 'pprime-day0.json').read_text(encoding='utf-8'))
assert old['pids'] == U0['pids']
out = {'attrs': C.ATTRS8, 'pids': U0['pids'], 'names': U0['names'], 'day0': {a: [float(v) for v in U0['mapped'][a]] for a in C.ATTRS8}, 'end': old['end'], 'day0_2526': old['day0']}
(Path(__file__).parent / 'pprime-day0-2425.json').write_text(json.dumps(out), encoding='utf-8')
for a in C.ATTRS8:
    d0, e, d1 = np.array(out['day0'][a]), np.array(out['end'][a]), np.array(out['day0_2526'][a])
    print(a, 'sd0 %.2f sdE %.2f corr(d0,end) %.3f corr(d0_2425,d0_2526) %.3f meanDelta %.2f sdDelta %.2f' % (d0.std(), e.std(), np.corrcoef(d0, e)[0, 1], np.corrcoef(d0, d1)[0, 1], (d0 - e).mean(), (d0 - e).std()))
