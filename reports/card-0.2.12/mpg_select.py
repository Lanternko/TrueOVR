"""E-185（card 0.2.12）：MPG_hat 窗口長度 L（1–4 季，線性遞減）。只用 2024-25 選 L；2025-26 只報告、不參與選擇（L-026）。
切點＝聯盟已賽場數的 0%、10%、25%、46.7%、75%（÷1230，四捨五入）；母體＝切點後 GP≥10 且該 L 的窗口有預測者。
指標＝五個切點合併的 MAE。主指標用「四個 L 都有預測的共同母體」（各 L 母體不同時不能直接比 MAE）；各自母體的 MAE 一併列出。
用法：python -I -X utf8 reports/card-0.2.12/mpg_select.py"""
import json, sys
from pathlib import Path
import numpy as np
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
import window10 as W10
FR = (0.0, 0.10, 0.25, 0.467, 0.75)
W = W10.Win10()
D = W.D


def run(S):
    tab = W.T10[S]['mpg']
    G = D.G[S]
    out = {}
    for frac in FR:
        g = int(frac * 1230 + 0.5)
        mn, gp = tab.agg(g, 10 ** 9)
        ok = gp >= 10
        act = np.where(ok, mn / np.maximum(gp, 1), np.nan)
        pred = {}
        for Ln in (1, 2, 3, 4):
            n, d = W.sums10('mpg', g, W.T10[S], G, S, Ln)
            pred[Ln] = np.where(d > 0, n / np.where(d > 0, d, 1), np.nan)
        common = ok & np.all([~np.isnan(pred[k]) for k in pred], axis=0)
        out[frac] = dict(g=g, act=act, pred=pred, ok=ok, common=common)
    res = {}
    for Ln in (1, 2, 3, 4):
        ec, eo, nc, no = [], [], 0, 0
        per = {}
        for frac, o in out.items():
            e = np.abs(o['pred'][Ln] - o['act'])
            ec += list(e[o['common']]); nc += int(o['common'].sum())
            m = o['ok'] & ~np.isnan(o['pred'][Ln])
            eo += list(e[m]); no += int(m.sum())
            per[str(frac)] = {'g': o['g'], 'n_common': int(o['common'].sum()), 'mae_common': float(e[o['common']].mean()), 'n_own': int(m.sum()), 'mae_own': float(e[m].mean())}
        res[Ln] = {'mae_common': float(np.mean(ec)), 'n_common': nc, 'mae_own': float(np.mean(eo)), 'n_own': no, 'cuts': per}
    return res


R = {S: run(S) for S in ('2024-25', '2025-26')}
sel = min((1, 2, 3, 4), key=lambda k: (R['2024-25'][k]['mae_common'], -k))
res = {'rule': '只用 2024-25 的共同母體五切點合併 MAE 選 L（平手取較長）；2025-26 只報告', 'cuts_frac': FR, 'selected_L': sel,
       'selected_by_own_pop_2024-25': min((1, 2, 3, 4), key=lambda k: R['2024-25'][k]['mae_own']), 'table': {S: {str(k): v for k, v in R[S].items()} for S in R}}
(H / 'mpg-L-selection.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
for S in R:
    print(S)
    for k in (1, 2, 3, 4):
        print(f"  L={k}  共同母體 MAE {R[S][k]['mae_common']:.4f} (n={R[S][k]['n_common']})   各自母體 MAE {R[S][k]['mae_own']:.4f} (n={R[S][k]['n_own']})")
print('selected L =', sel, '| 各自母體選', res['selected_by_own_pop_2024-25'])
