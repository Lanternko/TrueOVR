"""E-304 G-live：包 run_c4_live_rookie（不改共用檔），新秀各臂（B0／H5／S5／W5）重算 OVR。
只改 (a) ovr_of 的設計矩陣位置、(b) chain_rookie 的 posMeanD；MIX 沿用線上（errata-1）。
用法（cwd＝live/）：python -X utf8 <本檔> <輸出資料夾>  -> <輸出>/ranking.csv（線上原樣）＋ <輸出>/e304_arms.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parents[0] / 'ovr-inseason-2026-27' / 'live'
sys.path.insert(0, str(LIVE))
sys.stdout.reconfigure(encoding='utf-8')
import run_c4_live_rookie as R  # noqa: E402

POS = ['PG', 'SG', 'SF', 'PF', 'C']
R.DPOS.update({p: p for p in POS if p != 'C'})
P1 = json.load(open(HERE / 'p1.json', encoding='utf-8'))['live2026']['rows']
LAB = {r['pid']: r for r in P1}
H = {r['playerId']: r['heightInches'] for r in json.load(open(R.ROOKIE_JSON, encoding='utf-8'))['players']}


def h5(h):
    return 'PG' if h <= 75 else 'SG' if h <= 78 else 'SF' if h <= 80 else 'PF' if h <= 82 else 'C'


def shares(pid, arm, gpos):
    if arm == 'B0':
        return {R.DPOS[gpos]: 1.0}
    lab = LAB.get(pid)
    if arm == 'H5' or lab is None:
        return {h5(H[pid]): 1.0}
    if arm == 'S5':
        return {lab['S5']: 1.0}
    return {p: v for p, v in lab['W5'].items() if v > 0}


orig_chain = R.chain_rookie
OUT = []


def chain(ns, pw, anc, r_repl, cur, pos, n_games, dl, coef, d):
    res = orig_chain(ns, pw, anc, r_repl, cur, pos, n_games, dl, coef, d)
    pid = cur['pid']
    row = {'pid': pid, 'name': None, 'g3': pos, 'N': n_games, 'h': H[pid], 'arms': {}}
    pm0 = pw.pipe._m27_posMeanD
    for arm in ('B0', 'H5', 'S5', 'W5'):
        s = shares(pid, arm, pos)
        p0 = sum(w * R.ovr_of(ns, pw, anc, r_repl, cur['x'], p, cur['mpgHat'], H[pid])[0] for p, w in s.items())
        key = R.DPOS[pos]
        pw.pipe._m27_posMeanD = dict(pm0, **{key: sum(w * pm0[p] for p, w in s.items())})
        try:
            r2 = orig_chain(ns, pw, anc, r_repl, dict(cur, pred0=p0), pos, n_games, dl, coef, d)
        finally:
            pw.pipe._m27_posMeanD = pm0
        row['arms'][arm] = {'shares': {p: round(w, 4) for p, w in s.items()}, 'pred0': round(p0, 4),
                            'bonus': round(r2['bonus'], 4), 'ovrPreMix': round(r2['ovr'], 3)}
    row['onlinePreMix'] = round(res['ovr'], 3)
    OUT.append(row)
    return res


R.chain_rookie = chain
ns = R.load_ns()
out_dir = sys.argv[1]
sys.argv = ['x', out_dir]
try:
    ns['main']()
finally:
    json.dump(OUT, open(Path(out_dir) / 'e304_arms.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
