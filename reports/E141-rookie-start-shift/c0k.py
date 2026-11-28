"""E-141 c0k：重建 2026 屆 s=-5 起點，對 live/rookie-prior-2026.json 逐人逐項 <1e-6（硬關卡）。"""
import json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE)); sys.path.insert(0, str(ROOT / 'reports/E121-rookie-scale'))
import run_c4_live_rookie as RW
import build_2k_start as B2

def main():
    fit2k = json.load(open(ROOT / 'reports/rookie-growth/twok-by-pick.json', encoding='utf-8'))['fitRecent3']
    q, nq = B2.make_q()
    ns = RW.load_ns()
    ns['setup']()
    V2 = ns['V2']; C = ns['C']
    rel = V2.load_reliability()
    pw = ns['PW'].for_start(C, 'S*')
    anc, r_repl = ns['e064_anchors']()
    base = json.load(open(LIVE / 'rookie-prior-2026-e116.json', encoding='utf-8'))
    ref = {p['playerId']: p for p in json.load(open(LIVE / 'rookie-prior-2026.json', encoding='utf-8'))['players']}
    worst = 0.0; n = 0; bad = []
    for rk in base['players']:
        t = q(fit2k['a'] + fit2k['b_lnPick'] * math.log(rk['pick'])) - 5.0
        d, _ = B2.solve(ns, pw, anc, r_repl, rel, rk, t)
        x = B2.shifted(rk['x0'], d)
        for a, v in x.items():
            e = abs(v - ref[rk['playerId']]['x0'][a]); worst = max(worst, e); n += 1
            if e >= 1e-6: bad.append((rk['name'], a, e))
    res = {'players': len(base['players']), 'cells': n, 'maxAbsDiff': worst, 'pass': not bad and len(ref) == len(base['players'])}
    json.dump(res, open(HERE / 'c0k.json', 'w'), indent=1)
    print(res, bad[:5])

if __name__ == '__main__':
    main()
