"""E-141 errata-2 c0k：shape / target / solve 三項硬關卡。"""
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
    base = json.load(open(LIVE / 'rookie-prior-2026-e116.json', encoding='utf-8'))
    ref = {p['playerId']: p for p in json.load(open(LIVE / 'rookie-prior-2026.json', encoding='utf-8'))['players']}
    ns = RW.load_ns(); ns['setup']()
    rel = ns['V2'].load_reliability(); pw = ns['PW'].for_start(ns['C'], 'S*')
    anc, r_repl = ns['e064_anchors']()
    shape_w = 0.0; shape_d = 0.0; tgt_w = 0.0; solve_w = 0.0; dd = 0.0; dov = 0.0; rows = []
    for rk in base['players']:
        o = ref[rk['playerId']]
        diffs = [o['x0'][a] - rk['x0'][a] for a in rk['x0'] if 1e-9 < rk['x0'][a] < 150 - 1e-9 and 1e-9 < o['x0'][a] < 150 - 1e-9]
        sw = max(diffs) - min(diffs); shape_w = max(shape_w, sw)
        c = sum(diffs) / len(diffs); shape_d = max(shape_d, abs(c - o['e121']['delta']))
        t = q(fit2k['a'] + fit2k['b_lnPick'] * math.log(rk['pick'])) - 5.0
        tgt_w = max(tgt_w, abs(t - o['e121']['target']))
        d, _ = B2.solve(ns, pw, anc, r_repl, rel, rk, t)
        x = B2.shifted(rk['x0'], d)
        ov = RW.eval_rookie(ns, pw, anc, r_repl, dict(rk, x0=x), None, 'e116', rel)['ovr']
        solve_w = max(solve_w, abs(ov - t))
        rows.append((rk['name'], d, o['e121']['delta'], d - o['e121']['delta']))
        dov = max(dov, abs(RW.eval_rookie(ns, pw, anc, r_repl, dict(rk, x0=o['x0']), None, 'e116', rel)['ovr'] - ov))
        dd = max(dd, abs(d - o['e121']['delta']))
    res = {'players': len(base['players']),
           'shape_within_player_spread_max': shape_w, 'shape_vs_stored_delta_max': shape_d,
           'target_vs_stored_max': tgt_w, 'delta_old_new_maxdiff': dd,
           'shape_pass': shape_w < 1e-9 and shape_d <= 5e-4, 'target_pass': tgt_w <= 5e-3,
           'solve_opening_ovr_minus_T_max': solve_w, 'solve_pass': solve_w < 1e-6, 'ovr_old_vs_new_maxdiff_listed_only': dov}
    res['pass'] = res['shape_pass'] and res['target_pass'] and res['solve_pass']
    json.dump(res, open(HERE / 'c0k2.json', 'w'), indent=1)
    print(res)
    print(rows[:3])
if __name__ == '__main__':
    main()
